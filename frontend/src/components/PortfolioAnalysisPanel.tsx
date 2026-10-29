import { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, PortfolioAnalysis } from '../services/api';
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
  useEffect(() => { api.portfolioAnalysis().then(setData).catch(() => {}); }, [version]);
  if (!data || !Object.keys(data.diversification.sectors).length) return null;
  const d = data.diversification;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="card p-4 space-y-3">
        <h2 className="font-bold">{t.diversification}</h2>
        <div className="label">{t.bySector}</div><Bars data={d.sectors} />
        <div className="label">{t.byCountry}</div><Bars data={d.countries} />
      </div>
      <div className="card p-4 space-y-2">
        <h2 className="font-bold">{t.rebalance}</h2>
        {d.warnings.map((w, i) => <p key={i} className="text-sm text-amber-600 dark:text-amber-400">⚠ {fill(t[`w_${w.code}` as 'w_few_lines'] ?? w.code, w)}</p>)}
        {d.actions.map((a, i) => (
          <p key={i} className="text-sm cursor-pointer hover:text-sky-500" onClick={() => onOpen(a.symbol)}>→ {fill(t[`a_${a.code}` as 'a_trim'] ?? a.code, a)}</p>
        ))}
        {!d.warnings.length && !d.actions.length && <p className="text-sm muted">{t.noAlerts}</p>}
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
