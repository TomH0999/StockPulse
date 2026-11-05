import { useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { api, CatalogEntry, InstrumentKind, KINDS, loadCatalog, SearchResult } from '../services/api';
import { useI18n } from '../context';

const YAHOO_KIND: Record<string, InstrumentKind> = {
  EQUITY: 'stock', ETF: 'etf', MUTUALFUND: 'etf', INDEX: 'index', FUTURE: 'commodity', CURRENCY: 'fx', CRYPTOCURRENCY: 'crypto',
  stock: 'stock', etf: 'etf', index: 'index', commodity: 'commodity', fx: 'fx', crypto: 'crypto',
};

export function StockSearchSelector({ onSelectStock }: { onSelectStock: (symbol: string, name: string) => void }) {
  const { t } = useI18n();
  const [term, setTerm] = useState('');
  const [open, setOpen] = useState(false);
  const [remote, setRemote] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [kind, setKind] = useState<InstrumentKind | ''>('');
  useEffect(() => { loadCatalog().then(setCatalog).catch(() => {}); }, []);

  const local = useMemo(() => {
    const q = term.trim().toLowerCase();
    if (!q) return [];
    return catalog.filter((s) => (!kind || (s.kind ?? 'stock') === kind) && (s.symbol.toLowerCase().startsWith(q) || s.name.toLowerCase().includes(q)))
      .sort((a, b) => Number(b.symbol.toLowerCase() === q) - Number(a.symbol.toLowerCase() === q))
      .slice(0, 6)
      .map((s) => ({ symbol: s.symbol, name: s.name, exchange: s.country, type: s.kind ?? 'stock' }));
  }, [term, catalog, kind]);

  // Recherche élargie à tous les marchés via Yahoo Finance (anti-rebond 300 ms)
  useEffect(() => {
    const q = term.trim();
    if (q.length < 2) return setRemote([]);
    setSearching(true);
    const id = setTimeout(() => {
      api.search(q).then(setRemote).catch(() => setRemote([])).finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(id);
  }, [term]);

  useEffect(() => {
    const close = (e: MouseEvent) => !boxRef.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const results = useMemo(() => {
    const seen = new Set<string>();
    return [...local, ...remote.filter((r) => !kind || YAHOO_KIND[r.type] === kind)]
      .filter((r) => !seen.has(r.symbol) && seen.add(r.symbol)).slice(0, 12);
  }, [local, remote, kind]);

  const select = (r: { symbol: string; name: string }) => {
    onSelectStock(r.symbol, r.name);
    setTerm('');
    setOpen(false);
  };

  return (
    <div ref={boxRef} className="relative w-full md:w-[30rem] flex gap-2">
      <select className="input !w-auto !py-1.5 text-xs" value={kind} onChange={(e) => setKind(e.target.value as InstrumentKind | '')} aria-label={t.kind_filter}>
        <option value="">{t.kind_all}</option>
        {KINDS.map((k) => <option key={k} value={k}>{t[`kind_${k}`]}</option>)}
      </select>
      <div className="relative flex-1">
      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 muted" />
      <input
        className="input pl-9"
        value={term}
        placeholder={t.searchPlaceholder}
        onChange={(e) => { setTerm(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && results[0]) select(results[0]);
          else if (e.key === 'Enter' && term.trim()) select({ symbol: term.trim().toUpperCase(), name: '' });
        }}
      />
      </div>
      {open && term.trim() && (
        <div className="card absolute z-30 mt-1 top-full w-full max-h-80 overflow-y-auto shadow-xl !bg-white dark:!bg-slate-900">
          {results.map((r) => (
            <button key={r.symbol} onClick={() => select(r)}
              className="w-full text-left px-3 py-2 flex justify-between items-center gap-3 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer">
              <span className="truncate text-sm">{r.name}{YAHOO_KIND[r.type] && YAHOO_KIND[r.type] !== 'stock' && <span className="ml-2 text-[9px] px-1 rounded bg-slate-500/15 muted">{t[`kind_${YAHOO_KIND[r.type]}`]}</span>}</span>
              <span className="text-xs font-mono font-bold text-sky-600 dark:text-sky-400 whitespace-nowrap">
                {r.symbol}{r.exchange && <span className="muted font-normal"> · {r.exchange}</span>}
              </span>
            </button>
          ))}
          {!results.length && <div className="px-3 py-2 text-sm muted">{searching ? t.searching : `${t.noResults} « ${term} »`}</div>}
        </div>
      )}
    </div>
  );
}
