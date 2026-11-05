import { useEffect, useState } from 'react';
import { api, errorMessage, Thesis } from '../services/api';
import { useI18n } from '../context';

/** Journal de thèse d'une ligne : pourquoi j'achète, combien vaut l'entreprise selon moi, quand je vendrais. */
export function ThesisEditor({ symbol, price, onSaved }: { symbol: string; price?: number; onSaved?: (t: Thesis | null) => void }) {
  const { t, lang } = useI18n();
  const [cur, setCur] = useState<Thesis | null>(null);
  const [text, setText] = useState('');
  const [fair, setFair] = useState('');
  const [sellIf, setSellIf] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    api.thesis(symbol).then((x) => {
      setCur(x);
      setText(x?.thesis ?? '');
      setFair(x?.fair_value != null ? String(x.fair_value) : '');
      setSellIf(x?.sell_if ?? '');
    }).catch(() => {});
  }, [symbol]);

  const fv = parseFloat(fair.replace(',', '.'));
  const margin = price && fv > 0 ? ((fv / price - 1) * 100) : null;
  const save = () => api.saveThesis(symbol, text, fv > 0 ? fv : null, sellIf)
    .then((x) => { setCur(x); setMsg(t.thesisSaved); onSaved?.(x); })
    .catch((e) => setMsg(errorMessage(e)));

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 space-y-2 text-sm">
      <div className="flex justify-between items-baseline">
        <b>{t.thesisTitle}</b>
        {cur && <span className={`text-[11px] ${cur.next_review <= new Date().toISOString().slice(0, 10) ? 'text-amber-500 font-semibold' : 'muted'}`}>
          {t.thesisReview} {new Date(cur.next_review).toLocaleDateString(lang)}</span>}
      </div>
      <textarea className="input min-h-[80px]" value={text} onChange={(e) => setText(e.target.value)} placeholder={t.thesisPlaceholder} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <label className="text-xs">{t.thesisFair}
          <input className="input mt-0.5" inputMode="decimal" value={fair} onChange={(e) => setFair(e.target.value)} />
          {margin !== null && <span className={`text-[11px] ${margin >= 0 ? 'up' : 'down'}`}>{t.thesisMargin} {margin > 0 ? '+' : ''}{margin.toFixed(0)} %</span>}
        </label>
        <label className="text-xs">{t.thesisSellIf}
          <input className="input mt-0.5" value={sellIf} onChange={(e) => setSellIf(e.target.value)} placeholder={t.thesisSellIfPh} />
        </label>
      </div>
      <div className="flex items-center gap-2">
        <button className="btn-primary" onClick={save}>{cur ? t.thesisConfirm : t.save}</button>
        {cur && <button className="btn" onClick={() => api.deleteThesis(symbol).then(() => { setCur(null); setText(''); setFair(''); setSellIf(''); onSaved?.(null); })}>{t.remove}</button>}
        {msg && <span className="text-xs muted">{msg}</span>}
      </div>
      <p className="text-[11px] muted">{t.thesisHelp}</p>
    </div>
  );
}
