import { useEffect, useState } from 'react';
import { Briefcase, Pencil, Trash2 } from 'lucide-react';
import { api, errorMessage, money, pct, Portfolio, PortfolioLine } from '../services/api';
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
    return () => { alive = false; clearInterval(id); };
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

export function PortfolioView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const [data, setData] = usePortfolio();
  const [form, setForm] = useState<{ id?: number; symbol: string; quantity: string; price: string }>({ symbol: '', quantity: '', price: '' });
  const [account, setAccount] = useState<{ deposits: string; cash: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (data && !account) setAccount({ deposits: String(data.deposits || ''), cash: String(data.cash || '') });
  }, [data, account]);

  const run = (p: Promise<Portfolio>, after?: () => void) =>
    p.then((d) => { setData(d); setError(null); setVersion((v) => v + 1); after?.(); }).catch((e) => setError(errorMessage(e)));

  const submit = () => {
    const q = Number(form.quantity.replace(',', '.')), pr = Number(form.price.replace(',', '.'));
    run(form.id ? api.editLine(form.id, form.symbol, q, pr) : api.addLine(form.symbol, q, pr), () => setForm({ symbol: '', quantity: '', price: '' }));
  };

  const up = (v: number) => (v >= 0 ? 'up' : 'down');
  const card = (label: string, value: React.ReactNode, sub?: React.ReactNode) => (
    <div className="card p-4"><div className="label">{label}</div><div className="text-xl font-bold">{value}</div>{sub && <div className="text-xs mt-1">{sub}</div>}</div>
  );

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold flex items-center gap-2"><Briefcase className="w-6 h-6 text-sky-500" />{t.pfTitle}</h1>
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {card(t.pfValue, money(data.value, lang))}
          {card(t.pfPnl, <span className={up(data.pnl)}>{money(data.pnl, lang)}</span>, <span className={up(data.pnl)}>{pct(data.pnl_percent)}</span>)}
          {card(t.pfDay, <span className={up(data.day_change)}>{money(data.day_change, lang)}</span>)}
          {card(t.pfTotal, money(data.total, lang), data.performance !== null && <span className={up(data.performance)}>{t.pfPerf} : {pct(data.performance)}</span>)}
          {card(t.pfCeiling, `${money(data.deposits, lang)} / ${money(data.ceiling, lang)}`,
            <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 mt-1"><div className="h-full rounded-full bg-sky-600" style={{ width: `${Math.min(100, (data.deposits / data.ceiling) * 100)}%` }} /></div>)}
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
              <th className="px-3 py-2 text-left">{t.col_name}</th><th className="px-3 py-2 text-right">{t.pfQty}</th>
              <th className="px-3 py-2 text-right">{t.pfPru}</th><th className="px-3 py-2 text-right">{t.col_price}</th>
              <th className="px-3 py-2 text-right">{t.pfValue}</th><th className="px-3 py-2 text-right">{t.pfPnl}</th>
              <th className="px-3 py-2 text-right">{t.pfWeight}</th><th className="px-3 py-2 text-right">{t.col_advice}</th>
              <th className="px-3 py-2 text-left">{t.pfAlerts}</th><th />
            </tr>
          </thead>
          <tbody>
            {!data?.lines.length && <tr><td colSpan={10} className="px-3 py-4 muted">{data ? t.pfEmpty : t.loading}</td></tr>}
            {data?.lines.map((l) => (
              <tr key={l.id} className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-3 py-2 cursor-pointer" onClick={() => onOpen(l.symbol)}>
                  <div className="font-mono font-bold">{l.symbol}</div><div className="text-xs muted truncate max-w-[200px]">{l.name}</div>
                </td>
                <td className="px-3 py-2 text-right">{l.quantity}</td>
                <td className="px-3 py-2 text-right">{l.avg_price.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{l.price.toFixed(2)} <span className={`text-xs ${up(l.change_percent ?? 0)}`}>{pct(l.change_percent)}</span></td>
                <td className="px-3 py-2 text-right">{money(l.value, lang, l.currency)}</td>
                <td className={`px-3 py-2 text-right ${up(l.pnl)}`}>{money(l.pnl, lang, l.currency)}<div className="text-xs">{pct(l.pnl_percent)}</div></td>
                <td className="px-3 py-2 text-right">{l.weight !== null ? `${l.weight} %` : '–'}</td>
                <td className="px-3 py-2 text-right"><VerdictBadge advice={l.advice} /></td>
                <td className="px-3 py-2"><AlertTags line={l} /></td>
                <td className="px-3 py-2 whitespace-nowrap text-right">
                  <button className="muted hover:text-sky-500 cursor-pointer mr-2" title={t.edit}
                    onClick={() => setForm({ id: l.id, symbol: l.symbol, quantity: String(l.quantity), price: String(l.avg_price) })}><Pencil className="w-3.5 h-3.5" /></button>
                  <button className="muted hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => run(api.deleteLine(l.id))}><Trash2 className="w-3.5 h-3.5" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <PortfolioAnalysisPanel version={version} onOpen={onOpen} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 space-y-3 lg:col-span-2">
          <h2 className="font-bold">{form.id ? `${t.edit} ${form.symbol}` : t.pfAdd}</h2>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[220px]">
              <label className="label">{t.col_name}</label>
              {form.symbol ? (
                <button className="input text-left font-mono font-bold" onClick={() => setForm({ ...form, symbol: '' })}>{form.symbol} ✕</button>
              ) : <StockSearchSelector onSelectStock={(s) => setForm({ ...form, symbol: s })} />}
            </div>
            <div className="w-28"><label className="label">{t.pfQty}</label><input className="input" inputMode="decimal" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></div>
            <div className="w-44"><label className="label">{t.pfPru}</label><input className="input" inputMode="decimal" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
            <button className="btn-primary !py-2" disabled={!form.symbol || !form.quantity || !form.price} onClick={submit}>{t.save}</button>
            {form.id && <button className="btn !py-2" onClick={() => setForm({ symbol: '', quantity: '', price: '' })}>{t.cancel}</button>}
          </div>
          {error && <p className="text-sm down">{error}</p>}
        </div>
        {account && (
          <div className="card p-4 space-y-3">
            <div><label className="label">{t.pfDeposits}</label><input className="input" inputMode="decimal" value={account.deposits} onChange={(e) => setAccount({ ...account, deposits: e.target.value })} /></div>
            <div><label className="label">{t.pfCash}</label><input className="input" inputMode="decimal" value={account.cash} onChange={(e) => setAccount({ ...account, cash: e.target.value })} /></div>
            <button className="btn-primary" onClick={() => run(api.setAccount(Number(account.deposits.replace(',', '.')) || 0, Number(account.cash.replace(',', '.')) || 0))}>{t.save}</button>
          </div>
        )}
      </div>
    </div>
  );
}
