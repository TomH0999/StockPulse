import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, HistoryPoint } from '../services/api';
import { useI18n } from '../context';

const PERIODS: [string, number][] = [['1d', 1], ['1w', 7], ['1mo', 31], ['3mo', 92], ['6mo', 183], ['1y', 366], ['5y', 1830], ['max', Infinity]];

interface Props {
  symbol: string;
  currency: string;
  highlightTs: number | null;
}

export function ChartPanel({ symbol, currency, highlightTs }: Props) {
  const { t, lang } = useI18n();
  const [period, setPeriod] = useState('1y');
  const [data, setData] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Choisit automatiquement une période qui contient la date de l'article ciblé
  useEffect(() => {
    if (!highlightTs) return;
    const ageDays = (Date.now() / 1000 - highlightTs) / 86400;
    const current = PERIODS.find(([p]) => p === period)![1];
    if (ageDays > current - 1) setPeriod(PERIODS.find(([, d]) => d > ageDays + 1)![0]);
  }, [highlightTs]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    api.history(symbol, period)
      .then((d) => alive && setData(d))
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [symbol, period]);

  const intraday = period === '1d' || period === '1w';
  const fmt = useMemo(() => new Intl.DateTimeFormat(lang, intraday
    ? { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short', year: period === '1mo' || period === '3mo' ? undefined : '2-digit' }), [lang, intraday, period]);

  const highlightX = useMemo(() => {
    if (!highlightTs || !data.length) return null;
    let best = data[0];
    for (const p of data) if (Math.abs(p.ts - highlightTs) < Math.abs(best.ts - highlightTs)) best = p;
    return Math.abs(best.ts - highlightTs) < 8 * 86400 ? best.ts : null;
  }, [highlightTs, data]);

  const first = data[0]?.close ?? 0;
  const last = data[data.length - 1]?.close ?? 0;
  const up = last >= first;
  const color = up ? '#10b981' : '#f43f5e';
  const perf = first ? ((last / first - 1) * 100).toFixed(2) : '0';

  return (
    <div className="card p-5 space-y-3">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div className="flex items-baseline gap-3">
          <h2 className="font-bold">{symbol}</h2>
          {data.length > 0 && <span className={`text-sm font-semibold ${up ? 'up' : 'down'}`}>{up ? '+' : ''}{perf}%</span>}
          {highlightTs && <span className="text-xs text-amber-500 font-mono">🎯 {t.targeted} {new Date(highlightTs * 1000).toLocaleDateString(lang)}</span>}
        </div>
        <div className="flex gap-1 p-1 rounded-lg border border-slate-200 dark:border-slate-800">
          {PERIODS.map(([p]) => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md cursor-pointer ${period === p ? 'bg-sky-600 text-white' : 'muted hover:text-sky-500'}`}>
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="h-[360px] relative">
        {loading && <div className="absolute inset-0 z-10 flex items-center justify-center"><div className="animate-spin h-8 w-8 rounded-full border-b-2 border-sky-500" /></div>}
        {error ? <div className="h-full flex items-center justify-center text-rose-500 text-sm">{t.chartError}</div> : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#64748b" strokeOpacity={0.2} vertical={false} />
              <XAxis dataKey="ts" type="number" scale="time" domain={['dataMin', 'dataMax']} tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(v) => fmt.format(new Date(v * 1000))} minTickGap={40} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} width={60} tickFormatter={(v) => v.toFixed(v < 10 ? 2 : 0)} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12, color: '#e2e8f0' }}
                labelFormatter={(v) => fmt.format(new Date(Number(v) * 1000))}
                formatter={(v: number) => [`${v.toFixed(2)} ${currency}`, t.price]} />
              <Area type="monotone" dataKey="close" stroke={color} strokeWidth={2} fill="url(#fill)" isAnimationActive={false} />
              {highlightX && <ReferenceLine x={highlightX} stroke="#f59e0b" strokeWidth={2} strokeDasharray="4 3" />}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
