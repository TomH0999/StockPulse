import { useEffect, useState } from 'react';
import { Pencil, Trash2, Upload } from 'lucide-react';
import { api, errorMessage, ImportRow, money, Movement, notifyPortfolioChanged, onPortfolioChanged, Portfolio } from '../services/api';
import { useI18n } from '../context';
import { fill } from '../i18n';
import { StockSearchSelector } from './StockSearchSelector';

type MoveType = Movement['type'];
const today = () => new Date().toISOString().slice(0, 10);
export const emptyMove = (type: MoveType = 'deposit', symbol = '') => ({ type, day: today(), symbol, quantity: '', price: '', fees: '', amount: '' });
export type MoveForm = ReturnType<typeof emptyMove> & { id?: number };
const num = (v: string) => Number(String(v).replace(',', '.').replace(/\s/g, ''));

export function JournalPanel({ form, setForm }: { form: MoveForm; setForm: (f: MoveForm) => void }) {
  const { t, lang } = useI18n();
  const [moves, setMoves] = useState<Movement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [costs, setCosts] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ content: string; rows: ImportRow[]; valid: number; columns: Record<string, string> } | null>(null);
  const [imported, setImported] = useState<string | null>(null);

  useEffect(() => {
    const load = () => api.movements().then(setMoves).catch(() => {});
    load();
    return onPortfolioChanged(load);
  }, []);

  const run = (p: Promise<Portfolio>, after?: () => void) =>
    p.then(() => { setError(null); notifyPortfolioChanged(); after?.(); }).catch((e) => setError(errorMessage(e)));
  const trade = form.type === 'buy' || form.type === 'sell';
  const payload = {
    day: form.day, symbol: form.symbol || null, fees: num(form.fees) || 0,
    ...(trade ? { quantity: num(form.quantity), price: num(form.price) } : { amount: num(form.amount) }),
  };
  const submit = () => run(form.id ? api.updateMovement(form.id, payload) : api.addMovement({ type: form.type, ...payload }),
    () => { setForm(emptyMove(form.type)); setCosts(null); });
  const canSubmit = trade ? form.symbol && num(form.quantity) > 0 && num(form.price) > 0 : num(form.amount) > 0;
  const estimate = () => api.orderCosts(form.symbol, form.type, num(form.quantity), num(form.price)).then((c) => {
    setForm({ ...form, fees: String(c.total) });
    setCosts(fill(t.feesDetail, { b: c.broker, t: c.ttf, f: c.fx }));
  }).catch((e) => setError(errorMessage(e)));
  const edit = (m: Movement) => setForm({
    id: m.id, type: m.type, day: m.day, symbol: m.symbol ?? '', quantity: m.quantity ? String(m.quantity) : '', price: m.price ? String(m.price) : '',
    fees: m.fees ? String(m.fees) : '', amount: m.amount ? String(m.amount) : '',
  });

  const loadFile = (file: File) => file.text().then((content) =>
    api.importCsv(content, false).then((r) => { setPreview({ content, ...r }); setImported(null); setError(null); }).catch((e) => setError(errorMessage(e))));
  const confirmImport = () => preview && api.importCsv(preview.content, true).then((r) => {
    setImported(fill(t.importDone, { n: r.added ?? 0 })); setPreview({ ...preview, ...r }); notifyPortfolioChanged();
  }).catch((e) => setError(errorMessage(e)));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div className="space-y-4">
        <div className="card p-4 space-y-3">
          <h2 className="font-bold">{form.id ? `${t.edit} — ${t[`mv_${form.type}`]}` : t.mvNew}</h2>
          <p className="text-xs muted">{t.mvHelp}</p>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="w-36"><label className="label">{t.mvType}</label>
              <select className="input" value={form.type} disabled={!!form.id} onChange={(e) => setForm({ ...form, type: e.target.value as MoveType })}>
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
                <div className="w-32"><label className="label">{t.mvPrice}</label><input className="input" inputMode="decimal" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
                <div className="w-24"><label className="label">{t.mvFees}</label><input className="input" inputMode="decimal" value={form.fees} onChange={(e) => setForm({ ...form, fees: e.target.value })} /></div>
                <button className="btn !py-2" disabled={!form.symbol || !num(form.quantity) || !num(form.price)} onClick={estimate}>{t.feesAuto}</button>
              </>
            ) : (
              <div className="w-36"><label className="label">{t.mvAmount}</label><input className="input" inputMode="decimal" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
            )}
            <button className="btn-primary !py-2" disabled={!canSubmit} onClick={submit}>{t.save}</button>
            {form.id && <button className="btn !py-2" onClick={() => setForm(emptyMove())}>{t.cancel}</button>}
          </div>
          {costs && <p className="text-xs muted">{costs}</p>}
          {error && <p className="text-sm down">{error}</p>}
        </div>

        <div className="card p-4 space-y-3">
          <h2 className="font-bold">{t.importTitle}</h2>
          <p className="text-xs muted">{t.importHelp}</p>
          <label className="btn cursor-pointer w-fit"><Upload className="w-3.5 h-3.5" />{t.importFile}
            <input type="file" accept=".csv,text/csv,.txt" className="hidden" onChange={(e) => e.target.files?.[0] && loadFile(e.target.files[0])} /></label>
          {preview && (
            <>
              <p className="text-xs muted">{t.importCols} : {Object.entries(preview.columns).map(([k, v]) => `${v} → ${k}`).join(' · ')}</p>
              <div className="max-h-64 overflow-y-auto text-xs">
                <table className="w-full">
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.line} className={`border-b border-slate-100 dark:border-slate-800/60 ${r.error ? 'down' : ''}`}>
                        <td className="py-1">{r.day ?? '?'}</td><td>{r.type ? t[`mv_${r.type}` as 'mv_buy'] : r.raw_type}</td>
                        <td className="font-mono">{r.symbol ?? r.label ?? ''}</td>
                        <td className="text-right">{r.quantity ? `${r.quantity} × ${r.price}` : r.amount ?? ''}</td>
                        <td className="pl-2">{r.error ?? '✓'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {imported ? <p className="text-sm up">{imported}</p>
                : <button className="btn-primary" disabled={!preview.valid} onClick={confirmImport}>{fill(t.importConfirm, { n: preview.valid })}</button>}
            </>
          )}
        </div>
      </div>

      <div className="card p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">{t.mvJournal}</h2>
          <button className="text-xs text-rose-500 hover:underline cursor-pointer" onClick={() => window.confirm(t.resetPeaConfirm) && run(api.resetPortfolio())}>{t.resetPea}</button>
        </div>
        <div className="max-h-[560px] overflow-y-auto">
          <table className="w-full text-xs">
            <tbody>
              {!moves.length && <tr><td className="muted py-2">{t.mvEmpty}</td></tr>}
              {[...moves].reverse().map((m) => (
                <tr key={m.id} className={`border-b border-slate-100 dark:border-slate-800/60 ${form.id === m.id ? 'bg-sky-500/10' : ''}`}>
                  <td className="py-1.5 font-mono">{new Date(m.day).toLocaleDateString(lang)}</td>
                  <td className="py-1.5 font-semibold">{t[`mv_${m.type}`]}</td>
                  <td className="py-1.5 font-mono">{m.symbol ?? ''}</td>
                  <td className="py-1.5 text-right">{m.quantity ? `${m.quantity} × ${m.price}` : money(m.amount ?? 0, lang)}</td>
                  <td className="py-1.5 text-right muted">{m.fees ? `${t.mvFees} ${m.fees}` : ''}</td>
                  <td className="py-1.5 text-right whitespace-nowrap">
                    <button className="muted hover:text-sky-500 cursor-pointer mr-2" title={t.edit} onClick={() => edit(m)}><Pencil className="w-3.5 h-3.5" /></button>
                    <button className="muted hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => run(api.deleteMovement(m.id))}><Trash2 className="w-3.5 h-3.5" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
