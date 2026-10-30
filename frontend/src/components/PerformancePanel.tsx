import { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, money, onPortfolioChanged, pct } from '../services/api';
import { useI18n } from '../context';

const COLORS = ['#0ea5e9', '#94a3b8', '#a78bfa'];

export function PerformancePanel() {
  const { t, lang } = useI18n();
  const [hist, setHist] = useState<Awaited<ReturnType<typeof api.peaHistory>> | null>(null);
  const [div, setDiv] = useState<Awaited<ReturnType<typeof api.dividends>> | null>(null);
  useEffect(() => {
    const load = () => { api.peaHistory().then(setHist).catch(() => {}); api.dividends().then(setDiv).catch(() => {}); };
    load();
    return onPortfolioChanged(load);
  }, []);
  const series = ['pea', ...(hist?.benchmarks ?? [])];
  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div className="card p-4 space-y-2 xl:col-span-2">
        <h2 className="font-bold">{t.histTitle}</h2>
        <p className="text-xs muted">{t.histHelp}</p>
        {!hist?.points.length ? <p className="text-sm muted">{hist ? t.histEmpty : t.loading}</p> : (
          <>
            <div className="flex flex-wrap gap-4 text-sm">
              <span>{t.pfTitle} : <b className={(hist.performance ?? 0) >= 0 ? 'up' : 'down'}>{pct(hist.performance)}</b></span>
              {Object.entries(hist.benchmark_performance ?? {}).map(([k, v]) => <span key={k}>{k} : <b>{pct(v)}</b></span>)}
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hist.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#64748b" strokeOpacity={0.2} vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#64748b' }} minTickGap={50}
                    tickFormatter={(d) => new Date(d).toLocaleDateString(lang, { day: '2-digit', month: 'short', year: '2-digit' })} />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={40} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12, color: '#e2e8f0' }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {series.map((k, i) => <Line key={k} dataKey={k} name={k === 'pea' ? t.pfTitle : k} stroke={COLORS[i]} dot={false} strokeWidth={k === 'pea' ? 2 : 1.5} isAnimationActive={false} connectNulls />)}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
      <div className="card p-4 space-y-3">
        <h2 className="font-bold">{t.divTitle}</h2>
        {div && (
          <>
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <div><div className="label">{t.divReceived}</div><b>{money(div.received_total, lang)}</b></div>
              <div><div className="label">{t.divUpcoming}</div><b>{money(div.next_12m, lang)}</b></div>
              <div><div className="label">{t.divYield}</div><b>{div.yield ?? '–'} %</b></div>
            </div>
            <ul className="text-xs space-y-1 max-h-64 overflow-y-auto">
              {div.upcoming.map((u, i) => (
                <li key={i} className="flex justify-between gap-2">
                  <span className="font-mono">{new Date(u.date).toLocaleDateString(lang)} · {u.symbol}</span>
                  <span>{money(u.amount, lang)}{u.estimated && <span className="muted"> ({t.divEstimated})</span>}</span>
                </li>
              ))}
              {div.received.map((r, i) => (
                <li key={`r${i}`} className="flex justify-between gap-2 muted">
                  <span className="font-mono">{new Date(r.day).toLocaleDateString(lang)} · {r.symbol ?? ''}</span><span>✓ {money(r.amount, lang)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
