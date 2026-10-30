import { Fragment, useEffect, useMemo, useState } from 'react';
import { Building2, Search, Star } from 'lucide-react';
import { api, pct, priceWithEur, ScreenerRow } from '../services/api';
import { useI18n, VERDICT_LABEL } from '../context';
import { useScreener } from '../hooks/useScreener';
import { Sparkline } from './Sparkline';
import { StatusBadge, VerdictBadge } from './VerdictBadge';
import { applyFilters, Filters, MarketFilters } from './MarketFilters';

type Col = 'name' | 'price' | 'chg_1d' | 'chg_1m' | 'chg_ytd' | 'chg_1y' | 'volatility' | 'from_high' | 'score';
const COLS: Col[] = ['name', 'price', 'chg_1d', 'chg_1m', 'chg_ytd', 'chg_1y', 'volatility', 'from_high', 'score'];
const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export function CatalogView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const { rows, loading } = useScreener();
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<Filters>({ pea: false, country: '' });
  const [verdict, setVerdict] = useState('');
  const [sort, setSort] = useState<{ col: Col; desc: boolean }>({ col: 'name', desc: false });
  const [open, setOpen] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const PAGE = 100;

  const label: Record<Col, string> = {
    name: t.col_name, price: t.col_price, chg_1d: t.p_1d, chg_1m: t.p_1m, chg_ytd: t.p_ytd, chg_1y: t.p_1y,
    volatility: t.col_vol, from_high: t.col_from_high, score: t.col_advice,
  };

  const list = useMemo(() => {
    const q = fold(query.trim());
    const val = (r: ScreenerRow): number | string =>
      sort.col === 'name' ? r.name : sort.col === 'score' ? r.advice?.score ?? -999 : sort.col === 'price' ? r.price_eur ?? -999 : (r[sort.col] as number | null) ?? -999;
    return applyFilters(rows, filters)
      .filter((r) => (!q || fold(`${r.symbol} ${r.name}`).includes(q)) && (!verdict || r.advice?.verdict === verdict))
      .sort((a, b) => {
        const x = val(a), y = val(b);
        const c = typeof x === 'string' ? x.localeCompare(y as string) : x - (y as number);
        return sort.desc ? -c : c;
      });
  }, [rows, query, filters, verdict, sort]);

  const pages = Math.max(1, Math.ceil(list.length / PAGE));
  const current = Math.min(page, pages);
  useEffect(() => setPage(1), [query, filters, verdict, sort]);
  const toggleSort = (col: Col) => setSort((s) => ({ col, desc: s.col === col ? !s.desc : col !== 'name' }));
  const addFav = (r: ScreenerRow) => api.addFavorite(r.symbol, r.name).then(() => setAdded((s) => new Set(s).add(r.symbol)));

  return (
    <div className="space-y-5">
      <div className="card p-4 space-y-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Building2 className="w-6 h-6 text-sky-500" />{t.coTitle} <span className="text-base muted font-normal">({list.length})</span></h1>
          <p className="text-sm muted">{t.coSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 muted" />
            <input className="input pl-9" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t.searchPlaceholder} />
          </div>
          <MarketFilters rows={rows} value={filters} onChange={setFilters} />
          <select className="input !w-auto !py-1.5" value={verdict} onChange={(e) => setVerdict(e.target.value)} aria-label={t.verdict}>
            <option value="">{t.allVerdicts}</option>
            {Object.entries(VERDICT_LABEL[lang]).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>

      <div className="card overflow-x-auto">
        {loading ? <p className="p-4 muted text-sm">{t.loading}</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                {COLS.map((c) => (
                  <th key={c} onClick={() => toggleSort(c)}
                    className={`px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 cursor-pointer select-none whitespace-nowrap ${c === 'name' ? 'text-left' : 'text-right'}`}>
                    {label[c]}{sort.col === c && (sort.desc ? ' ↓' : ' ↑')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.slice((current - 1) * PAGE, current * PAGE).map((r) => (
                <Fragment key={r.symbol}>
                  <tr onClick={() => setOpen(open === r.symbol ? null : r.symbol)}
                    className={`border-b border-slate-100 dark:border-slate-800/60 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 ${open === r.symbol ? 'bg-sky-500/5' : ''}`}>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold">{r.symbol}</span>
                        {r.pea && <span className="text-[9px] px-1 rounded bg-sky-500/15 text-sky-600 dark:text-sky-400 font-bold">PEA</span>}
                        <StatusBadge status={r.status} isNew={r.new} />
                        <span className="text-[10px] muted">{r.country}{r.sector && ` · ${r.sector}`}</span>
                      </div>
                      <div className="text-xs muted truncate max-w-[260px]">{r.name}</div>
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">{r.price ? priceWithEur(r.price, r.currency, r.price_eur, lang) : '–'}</td>
                    {(['chg_1d', 'chg_1m', 'chg_ytd', 'chg_1y'] as const).map((c) => (
                      <td key={c} className={`px-3 py-2 text-right ${(r[c] ?? 0) >= 0 ? 'up' : 'down'}`}>{pct(r[c])}</td>
                    ))}
                    <td className="px-3 py-2 text-right">{r.volatility ? `${r.volatility}%` : '–'}</td>
                    <td className="px-3 py-2 text-right down">{pct(r.from_high)}</td>
                    <td className="px-3 py-2 text-right"><VerdictBadge advice={r.advice} /></td>
                  </tr>
                  {open === r.symbol && (
                    <tr className="bg-sky-500/5">
                      <td colSpan={COLS.length} className="px-3 py-3">
                        <div className="flex flex-wrap items-center gap-6">
                          <Sparkline data={r.spark} width={240} height={60} />
                          <div className="grid grid-cols-3 gap-x-6 gap-y-1 text-xs">
                            <span className="muted">{t.p_1w}</span><span className="muted">{t.p_3m}</span><span className="muted">{t.yearRange}</span>
                            <b className={(r.chg_1w ?? 0) >= 0 ? 'up' : 'down'}>{pct(r.chg_1w)}</b>
                            <b className={(r.chg_3m ?? 0) >= 0 ? 'up' : 'down'}>{pct(r.chg_3m)}</b>
                            <b>{r.range_pos ?? '–'} %</b>
                          </div>
                          <div className="text-xs">
                            {r.advice ? (
                              <span>{t.verdict} : <VerdictBadge advice={r.advice} /> {r.advice.score > 0 ? '+' : ''}{r.advice.score}/100 · {t.confidence} {t[`conf_${r.advice.confidence}`]}
                                <span className="muted"> · {new Date(r.advice.generated_at * 1000).toLocaleString(lang)}</span></span>
                            ) : <span className="muted">{t.notAnalysed}</span>}
                          </div>
                          <div className="flex gap-2 ml-auto">
                            <button className="btn" onClick={() => addFav(r)} disabled={added.has(r.symbol)}>
                              <Star className={`w-3.5 h-3.5 ${added.has(r.symbol) ? 'fill-amber-400 text-amber-400' : ''}`} />{t.addFav}
                            </button>
                            <button className="btn-primary" onClick={() => onOpen(r.symbol)}>{t.openAnalysis} →</button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
        {pages > 1 && (
          <div className="flex justify-between items-center text-sm p-3">
            <button className="btn" disabled={current <= 1} onClick={() => setPage(current - 1)}>{t.prev}</button>
            <span className="muted">{t.page} {current} / {pages}</span>
            <button className="btn" disabled={current >= pages} onClick={() => setPage(current + 1)}>{t.next}</button>
          </div>
        )}
      </div>
    </div>
  );
}
