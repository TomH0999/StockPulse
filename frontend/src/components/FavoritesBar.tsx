import { X, Star } from 'lucide-react';
import { Favorite, Quote } from '../services/api';
import { useI18n, VERDICT_LABEL, VERDICT_STYLE } from '../context';

interface Props {
  favorites: Favorite[];
  quotes: Record<string, Quote>;
  active: string;
  onSelect: (symbol: string) => void;
  onRemove: (symbol: string) => void;
  onReorder: (symbols: string[]) => void;
}

export function FavoritesBar({ favorites, quotes, active, onSelect, onRemove, onReorder }: Props) {
  const { t, lang } = useI18n();
  // Réorganisation par glisser-déposer
  const drop = (from: string, to: string) => {
    if (from === to) return;
    const order = favorites.map((f) => f.symbol).filter((s) => s !== from);
    order.splice(order.indexOf(to) + (favorites.findIndex((f) => f.symbol === from) < favorites.findIndex((f) => f.symbol === to) ? 1 : 0), 0, from);
    onReorder(order);
  };
  return (
    <div className="card p-3">
      <div className="flex items-center gap-2 mb-2">
        <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
        <span className="label !mb-0">{t.favorites}</span>
      </div>
      {!favorites.length ? (
        <p className="text-sm muted">{t.noFavorites}</p>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {favorites.map((f) => {
            const q = quotes[f.symbol];
            const up = (q?.change_percent ?? 0) >= 0;
            return (
              <div key={f.symbol} role="button" tabIndex={0} onClick={() => onSelect(f.symbol)}
                onKeyDown={(e) => e.key === 'Enter' && onSelect(f.symbol)}
                draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', f.symbol)}
                onDragOver={(e) => e.preventDefault()} onDrop={(e) => drop(e.dataTransfer.getData('text/plain'), f.symbol)}
                className={`group relative shrink-0 min-w-[150px] px-3 py-2 rounded-lg border cursor-pointer transition ${
                  active === f.symbol ? 'border-sky-500 bg-sky-500/10' : 'border-slate-200 dark:border-slate-800 hover:border-sky-400'
                }`}>
                <button title={t.removeFav} onClick={(e) => { e.stopPropagation(); onRemove(f.symbol); }}
                  className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 muted hover:text-rose-500 cursor-pointer">
                  <X className="w-3.5 h-3.5" />
                </button>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm">{f.symbol}</span>
                  {f.advice && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${VERDICT_STYLE[f.advice.verdict]}`}>
                      {VERDICT_LABEL[lang][f.advice.verdict]}
                    </span>
                  )}
                </div>
                <div className="text-[11px] muted truncate max-w-[160px]">{f.name || q?.short_name}</div>
                {q && !q.error && (
                  <div className="text-xs mt-0.5 flex gap-2">
                    <span className="font-semibold">{q.price.toFixed(2)}</span>
                    <span className={up ? 'up' : 'down'}>{up ? '+' : ''}{q.change_percent.toFixed(2)}%</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
