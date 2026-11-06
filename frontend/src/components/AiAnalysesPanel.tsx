import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight, History, Layers3, Trash2, X } from 'lucide-react';
import { api, EnsembleJob, EnsembleResult, errorMessage, SavedAnalysis, Theme, Verdict } from '../services/api';
import { useI18n, VERDICT_LABEL, VERDICT_STYLE } from '../context';

const SIZES = [1, 5, 10];
const ORDER: Verdict[] = ['STRONG_BUY', 'BUY', 'HOLD', 'REDUCE', 'SELL'];
const BAR: Record<Verdict, string> = { STRONG_BUY: 'bg-emerald-600', BUY: 'bg-emerald-400', HOLD: 'bg-slate-400', REDUCE: 'bg-amber-500', SELL: 'bg-rose-500' };
const SAVED_EVENT = 'stockpulse:ai-saved';
export const notifyAiSaved = () => window.dispatchEvent(new Event(SAVED_EVENT));

function Themes({ title, items, tone }: { title: string; items: Theme[]; tone: string }) {
  if (!items.length) return null;
  return (
    <div>
      <div className={`text-xs font-bold uppercase tracking-wider mb-1 ${tone}`}>{title}</div>
      <ul className="space-y-1 text-xs">
        {items.map((x, i) => (
          <li key={i} className="flex gap-2 items-start">
            <span className="font-mono font-bold w-10 shrink-0 text-right">{x.frequency} %</span>
            <span>{x.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Synthèse d'une analyse groupée : répartition des verdicts, dispersion et idées qui reviennent. */
export function EnsembleSummary({ r }: { r: EnsembleResult }) {
  const { t, lang } = useI18n();
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`text-lg font-extrabold px-3 py-1 rounded-lg ${VERDICT_STYLE[r.verdict]}`}>{VERDICT_LABEL[lang]?.[r.verdict] ?? r.verdict_label}</span>
        <div className="text-xs muted space-y-0.5">
          <div>{t.ensAvgScore} <b className={r.score >= 0 ? 'up' : 'down'}>{r.score > 0 ? '+' : ''}{r.score}</b>/100
            {r.ci95 && <> · {t.ensCi} [{r.ci95[0]} ; {r.ci95[1]}]</>} · σ {r.score_std}</div>
          <div>{t.ensAgreement} <b>{r.agreement} %</b> ({VERDICT_LABEL[lang]?.[r.majority]}) · {r.runs} {t.ensRuns}
            {r.partial && <span className="text-amber-500"> / {r.requested}</span>}</div>
        </div>
        <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded ${r.strength === 'strong' ? 'bg-emerald-500/15 up' : r.strength === 'weak' ? 'bg-rose-500/15 down' : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'}`}>
          {t[`ens_${r.strength}`]}
        </span>
      </div>
      <div>
        <div className="flex h-3 rounded-full overflow-hidden">
          {ORDER.map((v) => r.distribution[v] > 0 && <div key={v} className={BAR[v]} style={{ width: `${r.distribution[v]}%` }} title={`${VERDICT_LABEL[lang]?.[v]} ${r.distribution[v]} %`} />)}
        </div>
        <div className="flex flex-wrap gap-x-3 text-[11px] mt-1">
          {ORDER.map((v) => <span key={v}><span className={`inline-block w-2 h-2 rounded-sm mr-1 ${BAR[v]}`} />{VERDICT_LABEL[lang]?.[v]} <b>{r.distribution[v]} %</b></span>)}
        </div>
      </div>
      <p className="text-xs">{t[`ensRead_${r.strength}`].replace('{b}', String(r.bullish_share)).replace('{s}', String(r.bearish_share))}
        {' '}{t.ensLocal.replace('{s}', `${r.local_score > 0 ? '+' : ''}${r.local_score}`)}
        {r.runs > 1 && r.score_max - r.score_min > 60 && <> {t.ensRange.replace('{a}', String(r.score_min)).replace('{b}', String(r.score_max))}</>}</p>
      {r.runs >= 5 && (
        <p className={`text-xs font-semibold ${r.retained ? 'up' : 'text-amber-600 dark:text-amber-400'}`}>{r.retained ? `✓ ${t.ensRetained}` : `⚠ ${t.ensUncertain}`}</p>
      )}
      {r.outlook && r.outlook.expected_12m_adjusted !== null && (
        <p className="text-xs">{t.aiExpected} <b>{r.outlook.expected_12m_adjusted > 0 ? '+' : ''}{r.outlook.expected_12m_adjusted} %</b>
          {r.outlook.prob_outperform_adjusted !== null && <> · {t.aiProbBeat} <b>{r.outlook.prob_outperform_adjusted} %</b></>}
          <span className="muted"> ({t.ensAvgOf} {r.outlook.n})</span></p>
      )}
      {r.partial && r.stopped_reason && <p className="text-xs text-amber-500">{t.ensPartial} {r.stopped_reason}</p>}
      <p className="text-sm leading-relaxed">{r.summary}</p>
      <Themes title={t.opportunities} items={r.opportunities} tone="up" />
      <Themes title={t.threats} items={r.threats} tone="down" />
      <Themes title={t.catalysts} items={r.catalysts} tone="text-violet-600 dark:text-violet-400" />
      <p className="text-[11px] muted">{t.ensFreqHelp} · {Object.entries(r.engines).map(([k, v]) => `${k} ×${v}`).join(', ')}</p>
    </div>
  );
}

export function EnsemblePanel({ symbol, bare = false }: { symbol: string; bare?: boolean }) {
  const { t, lang } = useI18n();
  const [runs, setRuns] = useState(10);
  const [job, setJob] = useState<EnsembleJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number>();
  useEffect(() => { setJob(null); setError(null); return () => window.clearInterval(timer.current); }, [symbol]);

  const start = () => {
    setError(null);
    api.startEnsemble(symbol, runs, lang).then((j) => {
      setJob(j);
      window.clearInterval(timer.current);
      timer.current = window.setInterval(() => api.ensembleStatus(j.id).then((s) => {
        setJob(s);
        if (s.finished) { window.clearInterval(timer.current); if (s.result) notifyAiSaved(); }
      }).catch(() => window.clearInterval(timer.current)), 1500);
    }).catch((e) => setError(errorMessage(e)));
  };
  const running = job && !job.finished;

  return (
    <div className={bare ? 'space-y-3' : 'card p-5 space-y-3'}>
      {!bare && <h2 className="font-bold flex items-center gap-2"><Layers3 className="w-4 h-4 text-sky-500" />{t.ensTitle}</h2>}
      <p className="text-xs muted">{t.ensHelp}</p>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-700">
          {SIZES.map((n) => (
            <button key={n} disabled={!!running} onClick={() => setRuns(n)}
              className={`px-3 py-1.5 text-sm cursor-pointer ${runs === n ? 'bg-sky-600 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>{n}</button>
          ))}
        </div>
        {running ? (
          <button className="btn" onClick={() => job && api.cancelEnsemble(job.id)}><X className="w-3.5 h-3.5" />{t.cancel}</button>
        ) : <button className="btn-primary" onClick={start}>{t.ensRun.replace('{n}', String(runs))}</button>}
        <span className="text-[11px] muted">{t.ensCost.replace('{n}', String(runs))}</span>
      </div>
      {error && <p className="text-sm text-rose-500">{error}</p>}
      {running && (
        <div>
          <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div className="h-full bg-sky-500 transition-all" style={{ width: `${(job.done / job.total) * 100}%` }} />
          </div>
          <p className="text-xs muted mt-1">{job.done} / {job.total}{job.failed > 0 && ` · ${job.failed} ${t.ensFailed}`}</p>
        </div>
      )}
      {job?.finished && !job.result && <p className="text-sm text-rose-500">{job.error || job.last_error}</p>}
      {job?.result && <EnsembleSummary r={job.result} />}
    </div>
  );
}

function RenewalBadge({ a }: { a: SavedAnalysis }) {
  const { t } = useI18n();
  const r = a.renewal;
  if (r.status === 'ok') return null;  // rien à signaler
  const why = r.reason === 'price' ? t.renewPrice.replace('{p}', `${(r.price_move ?? 0) > 0 ? '+' : ''}${r.price_move}`)
    : r.reason === 'news' ? t.renewNews.replace('{n}', String(r.new_articles)) : t.renewAge.replace('{d}', String(Math.round(r.age_days)));
  return (
    <span title={`${t.renewIndex} ${r.index}`} className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded ${r.status === 'renew' ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400' : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'}`}>
      <AlertTriangle className="w-3 h-3" />{r.status === 'renew' ? t.renewNow : t.renewSoon} · {why}
    </span>
  );
}

function SingleDetails({ p }: { p: Record<string, unknown> }) {
  const { t } = useI18n();
  const list = (k: string) => (Array.isArray(p[k]) ? (p[k] as string[]) : []);
  return (
    <div className="space-y-2 text-xs">
      {typeof p.summary === 'string' && <p className="text-sm leading-relaxed">{p.summary}</p>}
      {p.horizon != null && <p className="muted">{t.horizon} : {String(p.horizon)}</p>}
      {([['opportunities', 'up'], ['threats', 'down'], ['patterns', 'text-sky-600 dark:text-sky-400'], ['catalysts', 'text-violet-600 dark:text-violet-400']] as const).map(([k, tone]) => list(k).length > 0 && (
        <div key={k}>
          <div className={`font-bold uppercase tracking-wider mb-0.5 ${tone}`}>{t[k]}</div>
          <ul className="space-y-0.5">{list(k).map((x, i) => <li key={i} className="pl-2 border-l-2 border-slate-200 dark:border-slate-700">{x}</li>)}</ul>
        </div>
      ))}
    </div>
  );
}

export function SavedAnalysesPanel({ symbol, bare = false }: { symbol: string; bare?: boolean }) {
  const { t, lang } = useI18n();
  const [items, setItems] = useState<SavedAnalysis[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const load = () => api.savedAnalyses(symbol).then(setItems).catch(() => {});
  useEffect(() => {
    setOpen(null);
    load();
    window.addEventListener(SAVED_EVENT, load);
    return () => window.removeEventListener(SAVED_EVENT, load);
  }, [symbol]); // eslint-disable-line react-hooks/exhaustive-deps
  const latest = items[0];

  return (
    <div className={bare ? 'space-y-3' : 'card p-5 space-y-3'}>
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="font-bold flex items-center gap-2"><History className="w-4 h-4 text-sky-500" />{t.savedTitle} <span className="muted font-normal text-sm">({items.length})</span></h2>
        {latest && latest.renewal.status === 'renew' && <span className="ml-auto text-xs text-rose-500 font-semibold">{t.renewLatest}</span>}
      </div>
      {!items.length && <p className="text-sm muted">{t.savedEmpty}</p>}
      <div className="space-y-1.5 max-h-[520px] overflow-y-auto pr-1">
        {items.map((a) => (
          <div key={a.id} className="rounded-lg border border-slate-200 dark:border-slate-800">
            <button onClick={() => setOpen(open === a.id ? null : a.id)} className="w-full text-left p-2 flex items-center gap-2 flex-wrap cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40">
              {open === a.id ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              <span className="text-xs font-mono">{new Date(a.created_at * 1000).toLocaleString(lang, { dateStyle: 'short', timeStyle: 'short' })}</span>
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${VERDICT_STYLE[a.verdict]}`}>{VERDICT_LABEL[lang]?.[a.verdict] ?? a.verdict}</span>
              <span className="text-xs"><b className={a.score >= 0 ? 'up' : 'down'}>{a.score > 0 ? '+' : ''}{Math.round(a.score)}</b></span>
              <span className="text-[10px] muted">{a.kind === 'ensemble' ? `${t.savedEnsemble} ×${a.runs}` : a.engine}{a.price != null && ` · ${a.price} ${a.currency ?? ''}`}</span>
              <RenewalBadge a={a} />
            </button>
            {open === a.id && (
              <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
                {a.kind === 'ensemble' ? <EnsembleSummary r={a.payload as unknown as EnsembleResult} /> : <SingleDetails p={a.payload} />}
                <div className="flex justify-between items-center text-[11px] muted pt-1">
                  <span>{t.renewIndex} {a.renewal.index} · {Math.round(a.renewal.age_days)} j · {a.renewal.price_move != null ? `${a.renewal.price_move > 0 ? '+' : ''}${a.renewal.price_move} %` : '–'} · {a.renewal.new_articles} {t.renewArticles}</span>
                  <button className="hover:text-rose-500 cursor-pointer" title={t.remove} onClick={() => api.deleteSaved(a.id).then(load)}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-[11px] muted">{t.renewHelp}</p>
    </div>
  );
}
