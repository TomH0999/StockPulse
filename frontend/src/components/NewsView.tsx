import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink, Flame, Newspaper, RefreshCw } from 'lucide-react';
import { api, errorMessage, NewsReport } from '../services/api';
import { useI18n } from '../context';

type Period = 'day' | 'week' | 'month' | 'year' | 'custom';
const PERIODS: Period[] = ['day', 'week', 'month', 'year', 'custom'];
const THIS_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 15 }, (_, i) => THIS_YEAR - i);

export function NewsView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const [period, setPeriod] = useState<Period>('day');
  const [year, setYear] = useState(THIS_YEAR - 1);
  const [month, setMonth] = useState(0);  // 0 = toute l'année
  const [report, setReport] = useState<NewsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api.topNews(period, period === 'custom' ? year : undefined, period === 'custom' && month ? month : undefined)
      .then((r) => { setReport(r); setTopic(null); setOpen(null); })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [period, year, month]); // eslint-disable-line react-hooks/exhaustive-deps

  const months = Array.from({ length: 12 }, (_, i) => new Date(2000, i, 1).toLocaleString(lang, { month: 'long' }));
  const fmt = (d: string) => new Date(d).toLocaleDateString(lang, { day: 'numeric', month: 'short', year: 'numeric' });
  const stories = (report?.stories ?? []).filter((s) => !topic || [s.headline, ...s.related.map((r) => r.headline)].some((h) => h.toLowerCase().includes(topic.split(' ')[0])));

  return (
    <div className="space-y-5">
      <div className="card p-4 space-y-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2"><Newspaper className="w-6 h-6 text-sky-500" />{t.nwTitle}</h1>
            <p className="text-sm muted">{t.nwSubtitle}</p>
          </div>
          <button className="btn" onClick={load} disabled={loading}><RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />{t.refresh}</button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg overflow-hidden border border-slate-300 dark:border-slate-700">
            {PERIODS.map((p) => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-sm cursor-pointer ${period === p ? 'bg-sky-600 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>{t[`nw_${p}`]}</button>
            ))}
          </div>
          {period === 'custom' && (
            <>
              <select className="input !w-auto !py-1.5" value={year} onChange={(e) => setYear(Number(e.target.value))} aria-label={t.nwYear}>
                {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
              <select className="input !w-auto !py-1.5" value={month} onChange={(e) => setMonth(Number(e.target.value))} aria-label={t.nwMonth}>
                <option value={0}>{t.nwWholeYear}</option>
                {months.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </>
          )}
          {report && <span className="text-xs muted">{fmt(report.start)} → {fmt(report.end)} · {report.articles} {t.nwArticles} · {report.sources} {t.nwSources}</span>}
        </div>
        {loading && <p className="text-xs muted animate-pulse">{period === 'custom' || period === 'year' ? t.nwLoadingHistory : t.loading}</p>}
        {error && <p className="text-sm text-rose-500">{error}</p>}
      </div>

      {report && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="card p-4 space-y-2 h-fit">
            <h2 className="font-bold flex items-center gap-2"><Flame className="w-4 h-4 text-amber-500" />{t.nwTopics}</h2>
            <p className="text-[11px] muted">{t.nwTopicsHelp}</p>
            {!report.topics.length && <p className="text-sm muted">{t.nwEmpty}</p>}
            <div className="space-y-1">
              {report.topics.map((x) => {
                const max = report.topics[0].count;
                return (
                  <button key={x.term} onClick={() => setTopic(topic === x.term ? null : x.term)}
                    className={`w-full text-left text-sm px-2 py-1 rounded cursor-pointer relative overflow-hidden ${topic === x.term ? 'ring-2 ring-sky-500' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                    <div className="absolute inset-y-0 left-0 bg-sky-500/10" style={{ width: `${(x.count / max) * 100}%` }} />
                    <span className="relative flex justify-between gap-2"><b className="capitalize">{x.term}</b>
                      <span className="text-xs muted">{x.count} {t.nwArticles} · {x.sources} {t.nwSources}</span></span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="card p-4 space-y-2 xl:col-span-2">
            <h2 className="font-bold">{t.nwStories}{topic && <span className="muted font-normal"> · « {topic} » <button className="text-sky-500 cursor-pointer" onClick={() => setTopic(null)}>×</button></span>}</h2>
            <p className="text-[11px] muted">{t.nwStoriesHelp}</p>
            {!stories.length && <p className="text-sm muted">{t.nwEmpty}</p>}
            <ol className="space-y-1.5">
              {stories.map((s, i) => (
                <li key={s.url + i} className="rounded-lg border border-slate-200 dark:border-slate-800">
                  <div className="p-2 flex gap-3 items-start">
                    <span className="font-mono text-sm font-bold muted w-6 text-right shrink-0">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <a href={s.url} target="_blank" rel="noreferrer" className="text-sm font-semibold hover:text-sky-500 inline-flex gap-1 items-start">
                        {s.headline}<ExternalLink className="w-3 h-3 shrink-0 mt-1 opacity-60" />
                      </a>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] muted mt-0.5">
                        <span>{s.source}</span>
                        <span>{new Date(s.timestamp * 1000).toLocaleString(lang, { dateStyle: 'short', timeStyle: 'short' })}</span>
                        <span className="font-semibold text-sky-600 dark:text-sky-400">{s.source_count} {t.nwSources}</span>
                        {s.headline_page && <span className="px-1 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-bold">{t.nwFront}</span>}
                        <span className={s.sentiment > 0.15 ? 'up' : s.sentiment < -0.15 ? 'down' : ''}>{s.sentiment > 0.15 ? t.positive : s.sentiment < -0.15 ? t.negative : t.neutral}</span>
                        {s.symbols.map((sym) => <button key={sym} onClick={() => onOpen(sym)} className="font-mono font-bold text-sky-600 dark:text-sky-400 hover:underline cursor-pointer">{sym}</button>)}
                      </div>
                    </div>
                    {s.related.length > 0 && (
                      <button className="text-[11px] muted flex items-center gap-0.5 cursor-pointer shrink-0" onClick={() => setOpen(open === i ? null : i)}>
                        {open === i ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}+{s.count - 1}
                      </button>
                    )}
                  </div>
                  {open === i && (
                    <ul className="border-t border-slate-200 dark:border-slate-800 p-2 pl-11 space-y-1 text-xs">
                      {s.related.map((r) => (
                        <li key={r.url}><a href={r.url} target="_blank" rel="noreferrer" className="hover:text-sky-500">{r.headline}</a>
                          <span className="muted"> · {r.source} · {new Date(r.timestamp * 1000).toLocaleDateString(lang)}</span></li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
