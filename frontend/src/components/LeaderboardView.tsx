import { useMemo, useState } from 'react';
import { Trophy } from 'lucide-react';
import { pct, ScreenerRow } from '../services/api';
import { useI18n } from '../context';
import { useScreener } from '../hooks/useScreener';
import { Sparkline } from './Sparkline';
import { VerdictBadge } from './VerdictBadge';
import { applyFilters, Filters, MarketFilters } from './MarketFilters';

const PERIODS = ['1d', '1w', '1m', '3m', 'ytd', '1y'] as const;
type Period = typeof PERIODS[number];
const CONF = { low: 0, medium: 1, high: 2 };

interface Board {
  key: string;
  value: (r: ScreenerRow, p: Period) => number | null | undefined;
  desc: boolean;
  show: (r: ScreenerRow, p: Period) => string;
  filter?: (r: ScreenerRow) => boolean;
}

const chg = (r: ScreenerRow, p: Period) => r[`chg_${p}` as keyof ScreenerRow] as number | null | undefined;
const score = (r: ScreenerRow) => (r.advice ? `${r.advice.score > 0 ? '+' : ''}${r.advice.score}` : '–');

const BOARDS: Board[] = [
  { key: 'b_gainers', value: chg, desc: true, show: (r, p) => pct(chg(r, p)) },
  { key: 'b_losers', value: chg, desc: false, show: (r, p) => pct(chg(r, p)) },
  { key: 'b_score', value: (r) => r.advice?.score, desc: true, show: score },
  { key: 'b_confident', value: (r) => r.advice && CONF[r.advice.confidence] * 1000 + r.advice.score, desc: true, show: score,
    filter: (r) => !!r.advice && r.advice.score > 0 },
  { key: 'b_dip', value: (r) => r.from_high, desc: false, show: (r) => pct(r.from_high), filter: (r) => (r.advice?.score ?? 0) >= 15 },
  { key: 'b_lowvol', value: (r) => r.volatility, desc: false, show: (r) => (r.volatility ? `${r.volatility}%` : '–') },
  { key: 'b_sell', value: (r) => r.advice?.score, desc: false, show: score, filter: (r) => !!r.advice && r.advice.score < 0 },
  // prix comparés en euros (devises différentes)
  { key: 'b_cheapest', value: (r) => r.price_eur, desc: false, show: (r) => `${r.price_eur?.toFixed(2)} €` },
  { key: 'b_dearest', value: (r) => r.price_eur, desc: true, show: (r) => `${r.price_eur?.toFixed(2)} €` },
];

export function LeaderboardView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const { rows, updated, loading } = useScreener();
  const [period, setPeriod] = useState<Period>('1d');
  const [filters, setFilters] = useState<Filters>({ pea: false, country: '' });

  const boards = useMemo(() => {
    const base = applyFilters(rows, filters).filter((r) => r.price && !r.status);
    return BOARDS.map((b) => {
      const list = base.filter((r) => (!b.filter || b.filter(r)) && b.value(r, period) !== null && b.value(r, period) !== undefined)
        .sort((x, y) => ((b.value(x, period) as number) - (b.value(y, period) as number)) * (b.desc ? -1 : 1))
        .slice(0, 10);
      return { b, list };
    });
  }, [rows, filters, period]);

  return (
    <div className="space-y-5">
      <div className="card p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Trophy className="w-6 h-6 text-amber-400" />{t.lbTitle}</h1>
          <p className="text-sm muted">{t.lbSubtitle}</p>
          {updated > 0 && <p className="text-xs muted mt-1">{t.updatedAt} : {new Date(updated * 1000).toLocaleTimeString(lang)}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1 p-1 rounded-lg border border-slate-200 dark:border-slate-800">
            {PERIODS.map((p) => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md cursor-pointer ${period === p ? 'bg-sky-600 text-white' : 'muted hover:text-sky-500'}`}>
                {t[`p_${p}`]}
              </button>
            ))}
          </div>
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
                        <span className={`w-20 text-right text-sm font-semibold ${b.key.startsWith('b_ch') || b.key === 'b_dearest' || b.key === 'b_lowvol' ? '' : (b.value(r, period) ?? 0) >= 0 ? 'up' : 'down'}`}>
                          {b.show(r, period)}
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
