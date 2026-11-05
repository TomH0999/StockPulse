import { useMemo, useState } from 'react';
import { Trophy } from 'lucide-react';
import { ScreenerRow } from '../services/api';
import { useI18n } from '../context';
import { useScreener } from '../hooks/useScreener';
import { Sparkline } from './Sparkline';
import { VerdictBadge } from './VerdictBadge';
import { applyFilters, Filters, MarketFilters } from './MarketFilters';

/** Classements d'investisseur long terme (qualité, valorisation, solidité, dividende) : pas de « plus fortes hausses du jour ». */
interface Board {
  key: string;
  value: (r: ScreenerRow) => number | null | undefined;
  desc: boolean;
  show: (r: ScreenerRow) => string;
  filter?: (r: ScreenerRow) => boolean;
}

const num = (v: number | null | undefined, u = '', d = 1) => (v === null || v === undefined ? '–' : `${v.toFixed(d)}${u}`);
const peRel = (r: ScreenerRow) => (r.advice?.pe && r.advice.pe_history_median ? r.advice.pe / r.advice.pe_history_median : null);

const BOARDS: Board[] = [
  { key: 'b_quality', value: (r) => r.advice?.quality, desc: true, show: (r) => `${num(r.advice?.quality, '', 0)}/25` },
  { key: 'b_fcf', value: (r) => r.advice?.fcf_yield, desc: true, show: (r) => num(r.advice?.fcf_yield, ' %'),
    filter: (r) => (r.advice?.fcf_yield ?? 0) < 40 },
  { key: 'b_cheap_hist', value: peRel, desc: false, show: (r) => `${num(r.advice?.pe, '', 0)} / ${num(r.advice?.pe_history_median, '', 0)}`,
    filter: (r) => (r.advice?.quality ?? -99) > 0 },
  { key: 'b_roic', value: (r) => r.advice?.roic_avg, desc: true, show: (r) => num(r.advice?.roic_avg, ' %'), filter: (r) => (r.advice?.roic_avg ?? 0) < 200 },
  { key: 'b_div', value: (r) => r.advice?.div_streak, desc: true, show: (r) => `${r.advice?.div_streak ?? '–'} ans` },
  { key: 'b_solid', value: (r) => r.advice?.net_debt_ebitda, desc: false, show: (r) => num(r.advice?.net_debt_ebitda, '', 2) },
  { key: 'b_reliable', value: (r) => r.advice?.edge_1y, desc: true, show: (r) => `+${num(r.advice?.edge_1y, ' pts', 0)}`,
    filter: (r) => !!r.advice?.reliable },
  { key: 'b_score', value: (r) => r.advice?.score, desc: true, show: (r) => (r.advice ? `${r.advice.score > 0 ? '+' : ''}${r.advice.score}` : '–'),
    filter: (r) => (r.advice?.coverage ?? 0) >= 0.75 },
  { key: 'b_lowvol', value: (r) => r.volatility, desc: false, show: (r) => (r.volatility ? `${r.volatility}%` : '–') },
];

export function LeaderboardView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const { rows, updated, loading } = useScreener();
  const [filters, setFilters] = useState<Filters>({ pea: false, country: '' });

  const boards = useMemo(() => {
    const base = applyFilters(rows, filters).filter((r) => r.price && !r.status);
    return BOARDS.map((b) => {
      const list = base.filter((r) => (!b.filter || b.filter(r)) && b.value(r) !== null && b.value(r) !== undefined)
        .sort((x, y) => ((b.value(x) as number) - (b.value(y) as number)) * (b.desc ? -1 : 1))
        .slice(0, 10);
      return { b, list };
    });
  }, [rows, filters]);

  return (
    <div className="space-y-5">
      <div className="card p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Trophy className="w-6 h-6 text-amber-400" />{t.lbTitle}</h1>
          <p className="text-sm muted">{t.lbSubtitle}</p>
          {updated > 0 && <p className="text-xs muted mt-1">{t.updatedAt} : {new Date(updated * 1000).toLocaleTimeString(lang)}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <MarketFilters rows={rows} value={filters} onChange={setFilters} />
        </div>
      </div>

      {loading ? <p className="muted text-sm">{t.loading}</p> : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {boards.map(({ b, list }) => (
            <div key={b.key} className="card p-4">
              <h2 className="font-bold mb-2">{t[b.key as 'b_gainers']}</h2>
              {!list.length ? <p className="text-sm muted">–</p> : (
                <ol className="space-y-0.5">
                  {list.map((r, i) => (
                    <li key={r.symbol}>
                      <button onClick={() => onOpen(r.symbol)}
                        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer text-left">
                        <span className="w-5 text-xs muted font-mono">{i + 1}</span>
                        <span className="flex-1 min-w-0">
                          <span className="font-mono font-bold text-sm">{r.symbol}</span>
                          <span className="block text-[11px] muted truncate">{r.name}</span>
                        </span>
                        <Sparkline data={r.spark?.slice(-30)} width={60} height={22} />
                        <VerdictBadge advice={r.advice} />
                        <span className="w-24 text-right text-sm font-semibold">
                          {b.show(r)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
