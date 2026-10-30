import { useEffect, useState } from 'react';
import { api, errorMessage, money, notifyPortfolioChanged, Objectives, Portfolio, RebalanceAction } from '../services/api';
import { useI18n } from '../context';
import { fill } from '../i18n';

export function ObjectivesPanel({ portfolio }: { portfolio: Portfolio | null }) {
  const { t, lang } = useI18n();
  const [obj, setObj] = useState<Objectives | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [amount, setAmount] = useState('');
  const [plan, setPlan] = useState<RebalanceAction[] | null>(null);
  useEffect(() => { api.objectives().then((o) => { setObj(o); setAmount(o.monthly_deposit ? String(o.monthly_deposit) : '500'); }).catch(() => {}); }, []);
  if (!obj) return null;
  const set = (k: keyof Objectives, v: string | number | boolean | null) => setObj({ ...obj, [k]: v });
  const save = () => api.saveObjectives(obj).then((o) => { setObj(o); setStatus({ ok: true, msg: t.saved }); notifyPortfolioChanged(); })
    .catch((e) => setStatus({ ok: false, msg: errorMessage(e) }));
  const field = (k: keyof Objectives, label: string) => (
    <div><label className="label">{label}</label>
      <input className="input" inputMode="decimal" value={String(obj[k] ?? '')} onChange={(e) => set(k, e.target.value)} /></div>
  );
  const months = portfolio && obj.monthly_deposit > 0 ? Math.ceil(portfolio.ceiling_left / obj.monthly_deposit) : null;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div className="card p-4 space-y-3">
        <h2 className="font-bold">{t.objTitle}</h2>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">{t.objOpened}</label>
            <input type="date" className="input" value={obj.opened ?? ''} onChange={(e) => set('opened', e.target.value || null)} /></div>
          {field('monthly_deposit', t.objMonthly)}
          {field('etf_share', t.objEtfShare)}
          {field('etf_symbol', t.objEtf)}
          {field('max_line', t.objMaxLine)}
          {field('max_sector', t.objMaxSector)}
          {field('cash_reserve', t.objCash)}
          {field('fx_fee_pct', t.objFxFee)}
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" className="accent-sky-600" checked={obj.ttf} onChange={(e) => set('ttf', e.target.checked)} />{t.objTtf}
        </label>
        <button className="btn-primary" onClick={save}>{t.save}</button>
        {status && <p className={`text-sm ${status.ok ? 'up' : 'down'}`}>{status.msg}</p>}
        {months !== null && <p className="text-xs muted">{fill(t.ceilingReach, { m: months })}</p>}
      </div>
      <div className="card p-4 space-y-3">
        <h2 className="font-bold">{t.depositPlanTitle}</h2>
        <p className="text-xs muted">{t.depositPlanHelp}</p>
        <div className="flex gap-2 items-end">
          <div className="w-40"><label className="label">{t.depositPlanAmount}</label>
            <input className="input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
          <button className="btn !py-2" onClick={() => api.depositPlan(Number(amount.replace(',', '.'))).then((r) => setPlan(r.actions)).catch(() => setPlan([]))}>{t.refresh}</button>
        </div>
        {plan && (!plan.length ? <p className="text-sm muted">{t.planEmpty}</p> : (
          <ul className="text-sm space-y-1">
            {plan.map((a) => <li key={a.symbol}><b className="font-mono">{a.quantity} × {a.symbol}</b> <span className="muted">≈ {money(a.amount, lang)} · {a.reasons.map((r) => t[`r_${r}` as 'r_new_line'] ?? r).join(', ')}</span></li>)}
          </ul>
        ))}
      </div>
    </div>
  );
}
