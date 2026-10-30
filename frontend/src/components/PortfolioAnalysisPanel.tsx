import { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, money, onPortfolioChanged, PortfolioAnalysis } from '../services/api';
import { OrderModal } from './OrderModal';
import { useI18n } from '../context';
import { fill } from '../i18n';

function Bars({ data }: { data: Record<string, number> }) {
  return (
    <div className="space-y-1">
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="text-xs">
          <div className="flex justify-between"><span>{k}</span><b>{v} %</b></div>
          <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800"><div className="h-full rounded-full bg-sky-600" style={{ width: `${Math.min(100, v)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

export function PortfolioAnalysisPanel({ version, onOpen }: { version: number; onOpen: (s: string) => void }) {
  const { t, lang } = useI18n();
  const [data, setData] = useState<PortfolioAnalysis | null>(null);
  const [order, setOrder] = useState<PortfolioAnalysis['diversification']['rebalance']['actions'][number] | null>(null);
  useEffect(() => {
    const load = () => api.portfolioAnalysis().then(setData).catch(() => {});
    load();
    const id = setInterval(load, 60000);
    const off = onPortfolioChanged(load);
    return () => { clearInterval(id); off(); };
  }, [version]);
  if (!data || (!Object.keys(data.diversification.sectors).length && !data.diversification.rebalance.actions.length)) return null;
  const d = data.diversification;
  const rb = d.rebalance;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="card p-4 space-y-3">
        <h2 className="font-bold">{t.diversification}</h2>
        <div className="label">{t.bySector}</div><Bars data={d.sectors} />
        <div className="label">{t.byCountry}</div><Bars data={d.countries} />
      </div>
      <div className="card p-4 space-y-3 lg:col-span-2 lg:row-span-2">
        {order && <OrderModal symbol={order.symbol} side={order.side} onClose={() => setOrder(null)}
          initialAmount={order.side === 'buy' ? order.amount : undefined} initialQuantity={order.side !== 'buy' ? order.quantity : undefined} />}
        <h2 className="font-bold">{t.rebalance}</h2>
        <p className="text-xs muted">{t.rbHelp}</p>
        {d.warnings.map((w, i) => <p key={i} className="text-sm text-amber-600 dark:text-amber-400">⚠ {fill(t[`w_${w.code}` as 'w_few_lines'] ?? w.code, w)}</p>)}
        {!rb.actions.length ? <p className="text-sm muted">{t.rbEmpty}</p> : (
          <div className="space-y-1.5">
            {rb.actions.map((a) => (
              <div key={a.symbol} className="flex flex-wrap items-center gap-2 text-sm p-2 rounded-lg border border-slate-200 dark:border-slate-800">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${a.side === 'buy' ? 'bg-emerald-500/15 up' : 'bg-rose-500/15 down'}`}>{t[`side_${a.side}`]}</span>
                <b className="font-mono cursor-pointer hover:text-sky-500" onClick={() => onOpen(a.symbol)}>{a.quantity} × {a.symbol}</b>
                <span className="muted">≈ {money(a.amount, lang)} · {a.current_weight} % → {a.target_weight} %</span>
                <span className="text-xs muted flex-1">{a.reasons.map((r) => t[`r_${r}` as 'r_new_line'] ?? r).join(' · ')}</span>
                {a.blocked ? <span className="text-xs text-amber-500">{t.rbBlocked}</span>
                  : <button className="btn" onClick={() => setOrder(a)}>{t.rbPrepare}</button>}
              </div>
            ))}
            <p className="text-xs muted">{t.rbCashAfter} : {money(rb.cash_after, lang)}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div><div className="label">{t.rbBefore}</div><Bars data={rb.before} /></div>
          <div><div className="label">{t.rbAfter}</div><Bars data={rb.after} /></div>
        </div>
      </div>
      <div className="card p-4">
        <h2 className="font-bold mb-2">{t.benchmark}</h2>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.benchmark.series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#64748b" strokeOpacity={0.2} vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#64748b' }} minTickGap={50}
                tickFormatter={(d) => new Date(d).toLocaleDateString(lang, { month: 'short', year: '2-digit' })} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={35} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12, color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line dataKey="portfolio" name={t.pfTitle} stroke="#0ea5e9" dot={false} strokeWidth={2} isAnimationActive={false} />
              <Line dataKey="index" name="CAC 40" stroke="#94a3b8" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
