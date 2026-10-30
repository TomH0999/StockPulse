import { useEffect, useState } from 'react';
import { Copy, X } from 'lucide-react';
import { api, errorMessage, notifyPortfolioChanged, OrderPlan } from '../services/api';
import { useI18n } from '../context';
import { fill } from '../i18n';
import { VerdictBadge } from './VerdictBadge';

interface Props { symbol: string; side: 'buy' | 'sell' | 'reduce'; onClose: () => void; initialAmount?: number; initialQuantity?: number }

export function OrderModal({ symbol, side, onClose, initialAmount, initialQuantity }: Props) {
  const { t, lang } = useI18n();
  const [plan, setPlan] = useState<OrderPlan | null>(null);
  const [amount, setAmount] = useState('');
  const [exec, setExec] = useState({ quantity: '', price: '', fees: '' });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = (a?: number) => api.orderPlan(symbol, side, a ?? initialAmount, side === 'buy' ? undefined : initialQuantity).then((p) => {
    setPlan(p); setError(null);
    if (!amount && side === 'buy') setAmount(String(Math.round(p.amount + p.fees)));
    setExec({ quantity: String(p.quantity), price: String(p.limit), fees: String(p.fees) });
  }).catch((e) => setError(errorMessage(e)));
  useEffect(() => { load(); }, [symbol, side]); // eslint-disable-line react-hooks/exhaustive-deps

  const n = (v: number) => v.toLocaleString(lang, { maximumFractionDigits: 4 });
  const sellSide = side !== 'buy';
  const steps = plan ? [
    t.step_account,
    fill(t.step_find, { isin: plan.isin ?? '—', symbol: plan.symbol.split('.')[0] }),
    sellSide ? t.step_side_sell : t.step_side_buy,
    fill(t.step_qty, { quantity: n(plan.quantity) }),
    fill(t.step_type, { limit: n(plan.limit), currency: plan.currency }),
    t.step_validity,
    fill(t.step_check, { amount: plan.currency === 'EUR' ? n(plan.amount) : `${n(plan.amount_native)} ${plan.currency} ≈ ${n(plan.amount)}`, currency: '€', fees: n(plan.fees) })
      + (plan.costs && (plan.costs.ttf || plan.costs.fx) ? ` (${fill(t.feesDetail, { b: n(plan.costs.broker), t: n(plan.costs.ttf), f: n(plan.costs.fx) })})` : ''),
    t.step_validate,
    ...(!sellSide && plan.stop_loss ? [fill(t.step_stop, { stop: n(plan.stop_loss), target: n(plan.target!), currency: plan.currency })] : []),
  ] : [];
  const num = (v: string) => Number(v.replace(',', '.'));

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="card !bg-white dark:!bg-slate-900 w-full max-w-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">{t[`orderTitle_${side}`]} — {symbol}</h2>
          <button onClick={onClose} className="muted hover:text-rose-500 cursor-pointer"><X className="w-5 h-5" /></button>
        </div>
        {error && <p className="text-sm down">{error}</p>}
        {plan && (
          <>
            <div className="flex items-center gap-2 text-sm"><span className="font-semibold">{plan.name}</span><VerdictBadge advice={plan.advice} /></div>
            {plan.warnings.map((w) => <p key={w} className="text-sm text-amber-600 dark:text-amber-400">⚠ {t[`ow_${w}` as 'ow_not_pea'] ?? w}</p>)}
            {side === 'buy' && (
              <div className="flex gap-2 items-end">
                <div className="flex-1"><label className="label">{t.orderAmount}</label>
                  <input className="input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
                <button className="btn !py-2" onClick={() => load(num(amount))}>{t.refresh}</button>
              </div>
            )}
            <div>
              <div className="label">{t.orderSteps}</div>
              <ol className="list-decimal pl-5 space-y-1 text-sm">
                {steps.map((s, i) => (
                  <li key={i} className="group">{s}
                    <button className="ml-2 opacity-0 group-hover:opacity-100 muted hover:text-sky-500 cursor-pointer align-middle" title={t.copy}
                      onClick={() => navigator.clipboard?.writeText(s.split(': ').slice(1).join(': ') || s)}><Copy className="w-3 h-3 inline" /></button>
                  </li>
                ))}
              </ol>
            </div>
            {sellSide && plan.realized_pnl !== undefined && (
              <p className="text-sm">{t.realizedPnl} : <b className={plan.realized_pnl >= 0 ? 'up' : 'down'}>{n(plan.realized_pnl)} €</b></p>
            )}
            <p className="text-xs muted">{t.peaTax}</p>
            <div className="border-t border-slate-200 dark:border-slate-800 pt-3 space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <div><label className="label">{t.executedQty}</label><input className="input" inputMode="decimal" value={exec.quantity} onChange={(e) => setExec({ ...exec, quantity: e.target.value })} /></div>
                <div><label className="label">{t.executedPrice}</label><input className="input" inputMode="decimal" value={exec.price} onChange={(e) => setExec({ ...exec, price: e.target.value })} /></div>
                <div><label className="label">{t.feesPaid}</label><input className="input" inputMode="decimal" value={exec.fees} onChange={(e) => setExec({ ...exec, fees: e.target.value })} /></div>
              </div>
              <button className="btn-primary w-full justify-center !py-2" disabled={saved || !num(exec.quantity) || !num(exec.price)}
                onClick={() => api.executeOrder(symbol, side, num(exec.quantity), num(exec.price), num(exec.fees) || 0)
                  .then(() => { setSaved(true); notifyPortfolioChanged(); }).catch((e) => setError(errorMessage(e)))}>
                {saved ? `✓ ${t.orderSaved}` : t.orderDone}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
