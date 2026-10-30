import { useEffect, useState } from 'react';
import { api, money, onPortfolioChanged, PortfolioAnalysis, RebalanceAction } from '../services/api';
import { useI18n } from '../context';
import { fill } from '../i18n';
import { OrderModal } from './OrderModal';

export function Bars({ data }: { data: Record<string, number> }) {
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

const SIDE_STYLE: Record<string, string> = { buy: 'bg-emerald-500/15 up', hold: 'bg-slate-500/15', reduce: 'bg-amber-500/15 text-amber-600 dark:text-amber-400', sell: 'bg-rose-500/15 down' };

export function PortfolioAnalysisPanel({ version, onOpen }: { version: number; onOpen: (s: string) => void }) {
  const { t, lang } = useI18n();
  const [data, setData] = useState<PortfolioAnalysis | null>(null);
  const [order, setOrder] = useState<RebalanceAction | null>(null);
  useEffect(() => {
    const load = () => api.portfolioAnalysis().then(setData).catch(() => {});
    load();
    const id = setInterval(load, 60000);
    const off = onPortfolioChanged(load);
    return () => { clearInterval(id); off(); };
  }, [version]);
  if (!data) return null;
  const d = data.diversification;
  const rb = d.rebalance;
  const reasons = (rs: string[]) => rs.map((r) => t[`r_${r}` as 'r_new_line'] ?? r).join(' · ');

  return (
    <div className="space-y-4">
      {order && <OrderModal symbol={order.symbol} side={order.side} onClose={() => setOrder(null)}
        initialAmount={order.side === 'buy' ? order.amount : undefined} initialQuantity={order.side !== 'buy' ? order.quantity : undefined} />}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="card p-4 space-y-3 xl:col-span-2">
          <h2 className="font-bold">{t.planTitle}</h2>
          <p className="text-xs muted">{t.planHelp}</p>
          {d.warnings.map((w, i) => <p key={i} className="text-sm text-amber-600 dark:text-amber-400">⚠ {fill(t[`w_${w.code}` as 'w_few_lines'] ?? w.code, w)}</p>)}
          {!rb.actions.length ? <p className="text-sm muted">{t.planEmpty}</p> : (
            <div className="space-y-1.5">
              {rb.actions.map((a) => (
                <div key={a.symbol} className="flex flex-wrap items-center gap-2 text-sm p-2 rounded-lg border border-slate-200 dark:border-slate-800">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${SIDE_STYLE[a.side]}`}>{t[`side_${a.side}`]}</span>
                  <b className="font-mono cursor-pointer hover:text-sky-500" onClick={() => onOpen(a.symbol)}>{a.quantity} × {a.symbol}</b>
                  <span className="muted">≈ {money(a.amount, lang)} · {a.current_weight} % → {a.target_weight} %</span>
                  <span className="text-xs muted flex-1">{reasons(a.reasons)}</span>
                  <button className="btn" onClick={() => setOrder(a)}>{t.rbPrepare}</button>
                </div>
              ))}
              <p className="text-xs muted">{t.rbCashAfter} : {money(rb.cash_after, lang)} · {t.planTurnover} : {rb.turnover} %</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div><div className="label">{t.rbBefore}</div><Bars data={rb.before} /></div>
            <div><div className="label">{t.rbAfter}</div><Bars data={rb.after} /></div>
          </div>
        </div>
        <div className="card p-4 space-y-3">
          <h2 className="font-bold">{t.diversification}</h2>
          <div className="label">{t.bySector}</div><Bars data={d.sectors} />
          <div className="label">{t.byCountry}</div><Bars data={d.countries} />
        </div>
      </div>

      {rb.lines.length > 0 && (
        <div className="card p-4 space-y-2">
          <h2 className="font-bold">{t.lineTitle}</h2>
          <p className="text-xs muted">{t.lineHelp}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {rb.lines.map((l) => (
              <div key={l.symbol} className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 text-sm space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${SIDE_STYLE[l.advice]}`}>{t[`la_${l.advice}`]}{l.quantity ? ` ${l.quantity}` : ''}</span>
                  <b className="font-mono cursor-pointer hover:text-sky-500" onClick={() => onOpen(l.symbol)}>{l.symbol}</b>
                  <span className="muted text-xs truncate">{l.name}</span>
                </div>
                <div className="text-xs muted">{l.weight} % → {l.target_weight} % · {fill(t.heldDays, { d: l.days_held })} · {l.pnl_percent > 0 ? '+' : ''}{l.pnl_percent} %</div>
                <div className="text-xs">{reasons(l.reasons)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
