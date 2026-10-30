import { useEffect, useState } from 'react';
import { Briefcase, Trash2 } from 'lucide-react';
import { api, errorMessage, money, Movement, notifyPortfolioChanged, onPortfolioChanged, pct, Portfolio, PortfolioLine } from '../services/api';
import { useI18n } from '../context';
import { StockSearchSelector } from './StockSearchSelector';
import { VerdictBadge } from './VerdictBadge';
import { PortfolioAnalysisPanel } from './PortfolioAnalysisPanel';

export function usePortfolio() {
  const [data, setData] = useState<Portfolio | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.portfolio().then((d) => alive && setData(d)).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    const off = onPortfolioChanged(load);
    return () => { alive = false; clearInterval(id); off(); };
  }, []);
  return [data, setData] as const;
}

export function AlertTags({ line }: { line: PortfolioLine }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-1">
      {line.alerts.map((a) => (
        <span key={a} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold whitespace-nowrap">
          {t[`alert_${a}` as 'alert_big_drop'] ?? a}
        </span>
      ))}
    </div>
  );
}

type MoveType = Movement['type'];
const today = () => new Date().toISOString().slice(0, 10);
const empty = (type: MoveType = 'deposit', symbol = '') => ({ type, day: today(), symbol, quantity: '', price: '', fees: '', amount: '' });

export function PortfolioView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const [data, setData] = usePortfolio();
  const [moves, setMoves] = useState<Movement[]>([]);
  const [form, setForm] = useState(empty());
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const load = () => api.movements().then(setMoves).catch(() => {});
    load();
    return onPortfolioChanged(load);
  }, []);

  const num = (v: string) => Number(v.replace(',', '.').replace(/\s/g, ''));
  const run = (p: Promise<Portfolio>, after?: () => void) =>
    p.then((d) => { setData(d); setError(null); setVersion((v) => v + 1); notifyPortfolioChanged(); after?.(); }).catch((e) => setError(errorMessage(e)));
  const trade = form.type === 'buy' || form.type === 'sell';
  const submit = () => run(api.addMovement({
    type: form.type, day: form.day, symbol: form.symbol || null, fees: num(form.fees) || 0,
    ...(trade ? { quantity: num(form.quantity), price: num(form.price) } : { amount: num(form.amount) }),
  }), () => setForm(empty(form.type)));
  const canSubmit = trade ? form.symbol && num(form.quantity) > 0 && num(form.price) > 0 : num(form.amount) > 0;

  const up = (v: number) => (v >= 0 ? 'up' : 'down');
  const card = (label: string, value: React.ReactNode, sub?: React.ReactNode) => (
    <div className="card p-4"><div className="label">{label}</div><div className="text-xl font-bold">{value}</div>{sub && <div className="text-xs mt-1">{sub}</div>}</div>
  );
  const th = 'px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400';

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold flex items-center gap-2"><Briefcase className="w-6 h-6 text-sky-500" />{t.pfTitle}</h1>
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {card(t.pfTotal, money(data.total, lang), data.performance !== null && <span className={up(data.gain)}>{money(data.gain, lang)} ({pct(data.performance)})</span>)}
          {card(t.pfValue, money(data.value, lang), <span className={up(data.day_change)}>{t.pfDay} : {money(data.day_change, lang)}</span>)}
          {card(t.pfCash, money(data.cash, lang), <span className="muted">{t.pfCashAuto}</span>)}
          {card(t.pfPnl, <span className={up(data.pnl)}>{money(data.pnl, lang)}</span>, <span className={up(data.pnl)}>{pct(data.pnl_percent)}</span>)}
          {card(t.pfRealized, <span className={up(data.realized)}>{money(data.realized, lang)}</span>, <span className="muted">{t.pfDividends} : {money(data.dividends, lang)}</span>)}
          {card(t.pfCeiling, `${money(data.deposits, lang)}`,
            <><span className="muted">{t.pfCeilingLeft} : {money(data.ceiling_left, lang)}</span>
              <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 mt-1"><div className="h-full rounded-full bg-sky-600" style={{ width: `${Math.min(100, (data.deposits / data.ceiling) * 100)}%` }} /></div></>)}
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800">
              <th className={`${th} text-left`}>{t.col_name}</th><th className={`${th} text-right`}>{t.pfQty}</th>
              <th className={`${th} text-right`}>{t.pfPruAuto}</th><th className={`${th} text-right`}>{t.col_price}</th>
              <th className={`${th} text-right`}>{t.pfValue}</th><th className={`${th} text-right`}>{t.pfPnl}</th>
              <th className={`${th} text-right`}>{t.pfRealized}</th><th className={`${th} text-right`}>{t.pfWeight}</th>
              <th className={`${th} text-right`}>{t.col_advice}</th><th className={`${th} text-left`}>{t.pfAlerts}</th><th />
            </tr>
          </thead>
          <tbody>
            {!data?.lines.length && <tr><td colSpan={11} className="px-3 py-4 muted">{data ? t.pfEmpty : t.loading}</td></tr>}
            {data?.lines.map((l) => (
              <tr key={l.id} className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-3 py-2 cursor-pointer" onClick={() => onOpen(l.symbol)}>
                  <div className="font-mono font-bold">{l.symbol}</div><div className="text-xs muted truncate max-w-[200px]">{l.name} · {t.pfSince} {new Date(l.since).toLocaleDateString(lang)}</div>
                </td>
                <td className="px-3 py-2 text-right">{l.quantity}</td>
                <td className="px-3 py-2 text-right">{l.avg_price.toFixed(2)} €</td>
                <td className="px-3 py-2 text-right">{l.price.toFixed(2)}{l.currency !== 'EUR' && <span className="muted text-xs"> {l.currency}</span>} <span className={`text-xs ${up(l.change_percent ?? 0)}`}>{pct(l.change_percent)}</span></td>
                <td className="px-3 py-2 text-right">{money(l.value, lang)}</td>
                <td className={`px-3 py-2 text-right ${up(l.pnl)}`}>{money(l.pnl, lang)}<div className="text-xs">{pct(l.pnl_percent)}</div></td>
                <td className={`px-3 py-2 text-right ${up(l.realized)}`}>{l.realized ? money(l.realized, lang) : '–'}</td>
                <td className="px-3 py-2 text-right">{l.weight !== null ? `${l.weight} %` : '–'}</td>
                <td className="px-3 py-2 text-right"><VerdictBadge advice={l.advice} /></td>
                <td className="px-3 py-2"><AlertTags line={l} /></td>
                <td className="px-3 py-2 whitespace-nowrap text-right space-x-1">
                  <button className="btn !px-2 !py-1" onClick={() => setForm(empty('buy', l.symbol))}>{t.side_buy}</button>
                  <button className="btn !px-2 !py-1" onClick={() => setForm({ ...empty('sell', l.symbol), quantity: String(l.quantity) })}>{t.side_sell}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <PortfolioAnalysisPanel version={version} onOpen={onOpen} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4 space-y-3">
          <h2 className="font-bold">{t.mvNew}</h2>
          <p className="text-xs muted">{t.mvHelp}</p>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="w-36"><label className="label">{t.mvType}</label>
              <select className="input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as MoveType })}>
                {(['deposit', 'withdrawal', 'buy', 'sell', 'dividend'] as const).map((k) => <option key={k} value={k}>{t[`mv_${k}`]}</option>)}
              </select></div>
            <div className="w-40"><label className="label">{t.mvDate}</label>
              <input type="date" className="input" value={form.day} max={today()} onChange={(e) => setForm({ ...form, day: e.target.value })} /></div>
            {(trade || form.type === 'dividend') && (
              <div className="flex-1 min-w-[200px]"><label className="label">{t.col_name}</label>
                {form.symbol ? <button className="input text-left font-mono font-bold" onClick={() => setForm({ ...form, symbol: '' })}>{form.symbol} ✕</button>
                  : <StockSearchSelector onSelectStock={(s) => setForm({ ...form, symbol: s })} />}</div>
            )}
            {trade ? (
              <>
                <div className="w-24"><label className="label">{t.pfQty}</label><input className="input" inputMode="decimal" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></div>
                <div className="w-28"><label className="label">{t.mvPrice}</label><input className="input" inputMode="decimal" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
                <div className="w-24"><label className="label">{t.mvFees}</label><input className="input" inputMode="decimal" value={form.fees} onChange={(e) => setForm({ ...form, fees: e.target.value })} /></div>
              </>
            ) : (
              <div className="w-36"><label className="label">{t.mvAmount}</label><input className="input" inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
            )}
            <button className="btn-primary !py-2" disabled={!canSubmit} onClick={submit}>{t.save}</button>
          </div>
          {error && <p className="text-sm down">{error}</p>}
        </div>

        <div className="card p-4 space-y-2">
          <h2 className="font-bold">{t.mvJournal}</h2>
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-xs">
              <tbody>
                {!moves.length && <tr><td className="muted py-2">{t.mvEmpty}</td></tr>}
                {[...moves].reverse().map((m) => (
                  <tr key={m.id} className="border-b border-slate-100 dark:border-slate-800/60">
                    <td className="py-1.5 font-mono">{new Date(m.day).toLocaleDateString(lang)}</td>
                    <td className="py-1.5 font-semibold">{t[`mv_${m.type}`]}</td>
                    <td className="py-1.5 font-mono">{m.symbol ?? ''}</td>
                    <td className="py-1.5 text-right">{m.quantity ? `${m.quantity} × ${m.price}` : money(m.amount ?? 0, lang)}</td>
                    <td className="py-1.5 text-right muted">{m.fees ? `${t.mvFees} ${m.fees}` : ''}</td>
                    <td className="py-1.5 text-right">
                      <button className="muted hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => run(api.deleteMovement(m.id))}><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
