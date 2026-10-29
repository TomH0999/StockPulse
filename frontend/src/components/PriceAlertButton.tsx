import { useEffect, useState } from 'react';
import { Bell, Trash2 } from 'lucide-react';
import { api, errorMessage, PriceAlert } from '../services/api';
import { useI18n } from '../context';

export function PriceAlertButton({ symbol, price }: { symbol: string; price?: number }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<PriceAlert[]>([]);
  const [direction, setDirection] = useState<'above' | 'below'>('below');
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (open) api.alerts().then((a) => setList(a.price_alerts)).catch(() => {}); }, [open]);
  useEffect(() => { setValue(price ? price.toFixed(2) : ''); }, [price, open]);
  const mine = list.filter((a) => a.symbol === symbol);

  return (
    <div className="relative">
      <button className="btn !p-2" title={t.priceAlert} onClick={() => setOpen(!open)}>
        <Bell className={`w-4 h-4 ${mine.some((a) => !a.triggered_at) ? 'text-amber-400 fill-amber-400' : ''}`} />
      </button>
      {open && (
        <div className="card !bg-white dark:!bg-slate-900 absolute z-30 mt-2 w-72 p-3 space-y-2 shadow-xl">
          <div className="font-bold text-sm">{t.priceAlert} — {symbol}</div>
          <div className="flex gap-2">
            <select className="input !py-1" value={direction} onChange={(e) => setDirection(e.target.value as 'above' | 'below')}>
              <option value="below">{t.below}</option><option value="above">{t.above}</option>
            </select>
            <input className="input !py-1 w-24" inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} />
          </div>
          <button className="btn-primary w-full justify-center" onClick={() =>
            api.addAlert(symbol, direction, Number(value.replace(',', '.'))).then((l) => { setList(l); setError(null); }).catch((e) => setError(errorMessage(e)))}>
            {t.add}
          </button>
          {error && <p className="text-xs down">{error}</p>}
          {mine.map((a) => (
            <div key={a.id} className="flex justify-between text-xs">
              <span>{a.direction === 'above' ? t.above : t.below} {a.price}{a.triggered_at && <span className="muted"> · {t.triggered}</span>}</span>
              <button className="muted hover:text-rose-500 cursor-pointer" onClick={() => api.removeAlert(a.id).then(setList)}><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
