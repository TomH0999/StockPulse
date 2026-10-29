import { useCallback, useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { Advice, api, Favorite, formatPrice, Quote } from '../services/api';
import { useI18n } from '../context';
import { StockSearchSelector } from './StockSearchSelector';
import { FavoritesBar } from './FavoritesBar';
import { ChartPanel } from './ChartPanel';
import { AdvicePanel } from './AdvicePanel';
import { NewsPanel } from './NewsPanel';

interface Props {
  symbol: string;
  onSelect: (symbol: string) => void;
  settingsVersion: number;
}

export function DashboardView({ symbol, onSelect, settingsVersion }: Props) {
  const { t, lang } = useI18n();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteError, setQuoteError] = useState(false);
  const [lastSync, setLastSync] = useState('');
  const [highlightTs, setHighlightTs] = useState<number | null>(null);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [favQuotes, setFavQuotes] = useState<Record<string, Quote>>({});

  const select = (s: string) => {
    onSelect(s.toUpperCase());
    setHighlightTs(null);
  };

  const fetchQuote = useCallback(() => {
    api.quote(symbol)
      .then((q) => { setQuote(q); setQuoteError(false); setLastSync(new Date().toLocaleTimeString(lang)); })
      .catch(() => setQuoteError(true));
  }, [symbol, lang]);

  useEffect(() => {
    setQuote(null);
    fetchQuote();
    const id = setInterval(fetchQuote, 10000);
    return () => clearInterval(id);
  }, [fetchQuote]);

  const refreshFavorites = useCallback(() => api.favorites().then(setFavorites).catch(() => {}), []);
  useEffect(() => { refreshFavorites(); }, [refreshFavorites, settingsVersion]);

  // Cours des favoris (toutes les 30 s)
  const favKey = favorites.map((f) => f.symbol).join(',');
  useEffect(() => {
    if (!favKey) return;
    const load = () => api.quotes(favKey.split(',')).then((qs) => setFavQuotes(Object.fromEntries(qs.map((q) => [q.symbol, q])))).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [favKey]);

  // Calcule en arrière-plan le conseil des favoris qui n'en ont pas encore
  useEffect(() => {
    const missing = favorites.filter((f) => !f.advice).map((f) => f.symbol);
    if (!missing.length) return;
    let cancelled = false;
    (async () => {
      for (const s of missing) {
        if (cancelled) return;
        await api.advice(s, lang, false, false).catch(() => {});
      }
      if (!cancelled) refreshFavorites();
    })();
    return () => { cancelled = true; };
  }, [favKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const isFav = favorites.some((f) => f.symbol === symbol);
  const toggleFav = () =>
    (isFav ? api.removeFavorite(symbol) : api.addFavorite(symbol, quote?.short_name ?? '')).then(setFavorites);

  const onAdvice = (a: Advice) => {
    if (isFav) setFavorites((fs) => fs.map((f) => (f.symbol === a.symbol ? { ...f, advice: { verdict: a.verdict, score: a.score, confidence: a.confidence, engine: a.engine, generated_at: a.generated_at } } : f)));
  };

  const up = (quote?.change ?? 0) >= 0;
  const cur = quote?.currency ?? 'USD';
  const kpi = (label: string, value: React.ReactNode, sub?: React.ReactNode) => (
    <div className="card p-4">
      <div className="label">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      {sub && <div className="text-xs mt-1">{sub}</div>}
    </div>
  );

  return (
    <div className="space-y-5">
      <FavoritesBar favorites={favorites} quotes={favQuotes} active={symbol} onSelect={select}
        onRemove={(s) => api.removeFavorite(s).then(setFavorites)}
        onReorder={(order) => api.reorderFavorites(order).then(setFavorites)} />

      <div className="card p-4 flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={toggleFav} title={isFav ? t.removeFav : t.addFav} className="cursor-pointer">
            <Star className={`w-7 h-7 transition ${isFav ? 'text-amber-400 fill-amber-400' : 'muted hover:text-amber-400'}`} />
          </button>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold truncate">{quote?.name ?? symbol}</h1>
            <p className="text-sm muted font-mono">{symbol}{quote?.exchange && ` · ${quote.exchange}`}{quote && ` · ${cur}`}</p>
          </div>
        </div>
        <StockSearchSelector onSelectStock={(s) => select(s)} />
      </div>

      {quoteError && !quote ? (
        <div className="card p-4 text-rose-500 text-sm">{t.noResults} « {symbol} »</div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {kpi(t.price, quote ? formatPrice(quote.price, cur, lang) : '…',
            quote && <span className={`font-bold ${up ? 'up' : 'down'}`}>{up ? '+' : ''}{quote.change.toFixed(2)} ({up ? '+' : ''}{quote.change_percent.toFixed(2)}%)</span>)}
          {kpi(t.volume, quote ? quote.volume.toLocaleString(lang) : '…',
            quote && <span className="muted">{t.dayRange} : {quote.day_low.toFixed(2)} – {quote.day_high.toFixed(2)}</span>)}
          {kpi(t.yearRange, quote ? `${quote.year_low.toFixed(2)} – ${quote.year_high.toFixed(2)}` : '…',
            quote && quote.year_high > quote.year_low && (
              <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 relative mt-2">
                <div className="absolute -top-0.5 w-2.5 h-2.5 rounded-full bg-sky-500"
                  style={{ left: `calc(${((quote.price - quote.year_low) / (quote.year_high - quote.year_low)) * 100}% - 5px)` }} />
              </div>))}
          {kpi(t.lastSync, <span className="font-mono">{lastSync || '--:--:--'}</span>, <span className="muted">{t.autoUpdate}</span>)}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2">
          <ChartPanel symbol={symbol} currency={cur} highlightTs={highlightTs} />
        </div>
        <AdvicePanel key={`${symbol}-${settingsVersion}`} symbol={symbol} onAdvice={onAdvice} onShowDate={setHighlightTs} />
      </div>

      <NewsPanel symbol={symbol} companyName={quote?.name ?? ''} onShowOnChart={(ts) => { setHighlightTs(ts); window.scrollTo({ top: 0, behavior: 'smooth' }); }} />
    </div>
  );
}
