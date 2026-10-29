import { useEffect, useMemo, useState } from 'react';
import { ArrowDownWideNarrow, ArrowUpNarrowWide, ExternalLink, Newspaper, RefreshCw, Target } from 'lucide-react';
import { api, Article } from '../services/api';
import { useI18n } from '../context';

const PAGE_SIZE = 10;
const STOP = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'stock', 'stocks', 'shares', 'les', 'des', 'une', 'pour', 'dans', 'sur', 'avec']);

type SortKey = 'date' | 'relevance' | 'popularity' | 'sentiment';

const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const tokens = (s: string) => new Set(fold(s).split(/[^a-z0-9]+/).filter((w) => w.length > 3 && !STOP.has(w)));
export const articleScore = (a: Article) => (a.ai_sentiment !== null ? Number(a.ai_sentiment) : a.sentiment_score ?? 0);
const sentimentOf = (a: Article) => { const s = articleScore(a); return s >= 0.15 ? 'Bullish' : s <= -0.15 ? 'Bearish' : 'Neutral'; };

interface Props {
  symbol: string;
  companyName: string;
  onShowOnChart: (ts: number) => void;
}

export function NewsPanel({ symbol, companyName, onShowOnChart }: Props) {
  const { t, lang } = useI18n();
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [keywords, setKeywords] = useState('');
  const [source, setSource] = useState('');
  const [sentiment, setSentiment] = useState('');
  const [year, setYear] = useState('');
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('date');
  const [desc, setDesc] = useState(true);
  const [page, setPage] = useState(1);

  const load = (refresh = false) => {
    setLoading(true);
    return api.news(symbol, refresh)
      .then((r) => { setArticles(r.articles); setBackfilling(r.backfilling); })
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setArticles([]);
    setKeywords(''); setSource(''); setSentiment(''); setYear(''); setMonth(''); setDay(''); setPage(1);
    load();
  }, [symbol]); // eslint-disable-line react-hooks/exhaustive-deps

  // Recharge pendant la constitution de l'archive historique
  useEffect(() => {
    if (!backfilling) return;
    const id = setInterval(() => api.news(symbol).then((r) => { setArticles(r.articles); setBackfilling(r.backfilling); }), 15000);
    return () => clearInterval(id);
  }, [backfilling, symbol]);

  useEffect(() => setPage(1), [keywords, source, sentiment, year, month, day, sortBy, desc]);

  // Couverture médiatique : nombre d'articles traitant du même sujet à ±36 h (titres proches)
  const coverage = useMemo(() => {
    const sorted = [...articles].sort((a, b) => a.timestamp - b.timestamp);
    const toks = sorted.map((a) => tokens(a.headline));
    const out = new Map<number, number>();
    sorted.forEach((a, i) => {
      let n = 0;
      for (let j = i - 1; j >= 0 && a.timestamp - sorted[j].timestamp < 129600; j--) n += similar(toks[i], toks[j]);
      for (let j = i + 1; j < sorted.length && sorted[j].timestamp - a.timestamp < 129600; j++) n += similar(toks[i], toks[j]);
      out.set(a.id, n);
    });
    return out;
  }, [articles]);

  const sources = useMemo(() => {
    const counts = new Map<string, number>();
    articles.forEach((a) => counts.set(a.source, (counts.get(a.source) ?? 0) + 1));
    return [...counts].sort((a, b) => b[1] - a[1]);
  }, [articles]);

  const dated = useMemo(() => articles.map((a) => ({ a, d: new Date(a.timestamp * 1000) })), [articles]);
  const years = useMemo(() => [...new Set(dated.map(({ d }) => d.getFullYear()))].sort((a, b) => b - a), [dated]);
  const months = useMemo(() => [...new Set(dated.filter(({ d }) => String(d.getFullYear()) === year).map(({ d }) => d.getMonth()))].sort((a, b) => a - b), [dated, year]);
  const days = useMemo(() => [...new Set(dated.filter(({ d }) => String(d.getFullYear()) === year && String(d.getMonth()) === month).map(({ d }) => d.getDate()))].sort((a, b) => a - b), [dated, year, month]);

  const results = useMemo(() => {
    const terms = fold(keywords).split(/[\s,]+/).filter(Boolean);
    const nameTerms = [fold(symbol.split('.')[0]), ...fold(companyName).split(/[^a-z0-9]+/).filter((w) => w.length > 2 && !['inc', 'corp', 'corporation', 'company', 'group', 'holdings'].includes(w)).slice(0, 2)];
    const rows = dated.flatMap(({ a, d }) => {
      if (source && a.source !== source) return [];
      if (sentiment && sentimentOf(a) !== sentiment) return [];
      if (year && String(d.getFullYear()) !== year) return [];
      if (month && String(d.getMonth()) !== month) return [];
      if (day && String(d.getDate()) !== day) return [];
      const head = fold(a.headline);
      const body = fold(`${a.summary} ${a.source}`);
      let relevance = 0;
      if (terms.length) {
        for (const term of terms) {
          const inHead = head.includes(term), inBody = body.includes(term);
          if (!inHead && !inBody) return [];
          relevance += (inHead ? 3 : 0) + (inBody ? 1 : 0);
        }
      } else {
        relevance = nameTerms.reduce((s, n) => s + (n && head.includes(n) ? 2 : 0), 0);
      }
      return [{ a, relevance }];
    });
    const key = (r: { a: Article; relevance: number }) =>
      sortBy === 'date' ? r.a.timestamp
        : sortBy === 'relevance' ? r.relevance
        : sortBy === 'popularity' ? coverage.get(r.a.id) ?? 0
        : articleScore(r.a);
    rows.sort((x, y) => (key(x) - key(y) || x.a.timestamp - y.a.timestamp) * (desc ? -1 : 1));
    return rows.map((r) => r.a);
  }, [dated, keywords, source, sentiment, year, month, day, sortBy, desc, coverage, symbol, companyName]);

  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const shown = results.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const reset = () => { setKeywords(''); setSource(''); setSentiment(''); setYear(''); setMonth(''); setDay(''); setSortBy('date'); setDesc(true); };
  const fmt = new Intl.DateTimeFormat(lang, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <div className="card p-5 space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <h2 className="font-bold flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-sky-500" />{t.newsTitle} — {symbol}
          <span className="text-xs font-normal muted">({results.length} / {articles.length} {t.articles})</span>
        </h2>
        <div className="flex items-center gap-2">
          {backfilling && <span className="text-xs text-amber-500 animate-pulse">{t.backfilling}</span>}
          <button className="btn" onClick={() => load(true)} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />{t.refresh}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 items-end">
        <div className="col-span-2">
          <label className="label">{t.keyword}</label>
          <input className="input" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder={t.keywordPlaceholder} />
        </div>
        <div>
          <label className="label">{t.source}</label>
          <select className="input" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">{t.allSources}</option>
            {sources.map(([s, n]) => <option key={s} value={s}>{s} ({n})</option>)}
          </select>
        </div>
        <div>
          <label className="label">{t.sentiment}</label>
          <select className="input" value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
            <option value="">{t.all}</option>
            {(['Bullish', 'Neutral', 'Bearish'] as const).map((s) => <option key={s} value={s}>{t[s]}</option>)}
          </select>
        </div>
        <div>
          <label className="label">{t.year}</label>
          <select className="input" value={year} onChange={(e) => { setYear(e.target.value); setMonth(''); setDay(''); }}>
            <option value="">{t.all}</option>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div>
          <label className="label">{t.month}</label>
          <select className="input" value={month} disabled={!year} onChange={(e) => { setMonth(e.target.value); setDay(''); }}>
            <option value="">{t.all}</option>
            {months.map((m) => <option key={m} value={m}>{t.months[m]}</option>)}
          </select>
        </div>
        <div>
          <label className="label">{t.day}</label>
          <select className="input" value={day} disabled={!month} onChange={(e) => setDay(e.target.value)}>
            <option value="">{t.all}</option>
            {days.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="label">{t.sortBy}</label>
          <div className="flex gap-1">
            <select className="input" value={sortBy} onChange={(e) => setSortBy(e.target.value as SortKey)}>
              {(['date', 'relevance', 'popularity', 'sentiment'] as const).map((k) => <option key={k} value={k}>{t[`sort_${k}`]}</option>)}
            </select>
            <button className="btn !px-2" onClick={() => setDesc(!desc)} title={desc ? '↓' : '↑'}>
              {desc ? <ArrowDownWideNarrow className="w-4 h-4" /> : <ArrowUpNarrowWide className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
      <button className="text-xs text-sky-600 dark:text-sky-400 hover:underline cursor-pointer" onClick={reset}>{t.reset}</button>

      {loading && !articles.length ? <p className="text-sm muted">{t.loading}</p> : !shown.length ? <p className="text-sm muted">{t.noArticles}</p> : (
        <ul className="divide-y divide-slate-200 dark:divide-slate-800">
          {shown.map((a) => {
            const s = sentimentOf(a);
            return (
              <li key={a.id} className="py-3 space-y-1">
                <div className="flex flex-wrap items-center gap-2 text-xs muted">
                  <span className="font-mono">{fmt.format(new Date(a.timestamp * 1000))}</span>
                  <span>·</span><span className="font-semibold">{a.source}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${s === 'Bullish' ? 'bg-emerald-500/15 up' : s === 'Bearish' ? 'bg-rose-500/15 down' : 'bg-slate-500/15'}`}>
                    {t[s]}{a.ai_sentiment !== null && ' · IA'}
                  </span>
                  {(coverage.get(a.id) ?? 0) > 0 && <span>· {coverage.get(a.id)}× 📣</span>}
                </div>
                <a href={a.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-sky-500 inline-flex gap-1 items-start">
                  {a.headline}<ExternalLink className="w-3 h-3 mt-1 shrink-0 opacity-50" />
                </a>
                {a.summary && <p className="text-sm muted line-clamp-2">{a.summary}</p>}
                <button className="text-xs text-amber-600 dark:text-amber-400 hover:underline inline-flex items-center gap-1 cursor-pointer" onClick={() => onShowOnChart(a.timestamp)}>
                  <Target className="w-3 h-3" />{t.analyzeOnChart}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {pages > 1 && (
        <div className="flex justify-between items-center text-sm">
          <button className="btn" disabled={current <= 1} onClick={() => setPage(current - 1)}>{t.prev}</button>
          <span className="muted">{t.page} {current} / {pages}</span>
          <button className="btn" disabled={current >= pages} onClick={() => setPage(current + 1)}>{t.next}</button>
        </div>
      )}
    </div>
  );
}

function similar(a: Set<string>, b: Set<string>) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  a.forEach((w) => { if (b.has(w)) inter++; });
  return inter / (a.size + b.size - inter) >= 0.25 ? 1 : 0;
}
