import { useEffect, useState } from 'react';
import { RefreshCw, Sparkles, TrendingDown, TrendingUp, Repeat, CalendarClock, Zap } from 'lucide-react';
import { Advice, api, errorMessage } from '../services/api';
import { useI18n, VERDICT_STYLE } from '../context';

interface Props {
  symbol: string;
  onAdvice: (a: Advice) => void;
  onShowDate: (ts: number) => void;
}

function Section({ icon, title, items, tone }: { icon: React.ReactNode; title: string; items: string[]; tone: string }) {
  if (!items.length) return null;
  return (
    <div>
      <div className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-1.5 ${tone}`}>{icon}{title}</div>
      <ul className="space-y-1 text-sm">
        {items.map((x, i) => <li key={i} className="pl-3 border-l-2 border-slate-200 dark:border-slate-700">{x}</li>)}
      </ul>
    </div>
  );
}

export function AdvicePanel({ symbol, onAdvice, onShowDate }: Props) {
  const { t, lang } = useI18n();
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = (refresh = false) => {
    setLoading(true);
    setError(null);
    api.advice(symbol, lang, refresh)
      .then((a) => { setAdvice(a); onAdvice(a); })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setAdvice(null);
    load();
  }, [symbol, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const gauge = advice ? (advice.score + 100) / 2 : 50;

  return (
    <div className="card p-5 space-y-4 h-full">
      <div className="flex justify-between items-center gap-2">
        <h2 className="font-bold flex items-center gap-2"><Sparkles className="w-4 h-4 text-sky-500" />{t.adviceTitle}</h2>
        <button className="btn" onClick={() => load(true)} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />{t.refresh}
        </button>
      </div>

      {loading && !advice && <p className="text-sm muted animate-pulse">{t.analyzing}</p>}
      {error && <p className="text-sm text-rose-500">{error}</p>}

      {advice && (
        <div className={`space-y-4 ${loading ? 'opacity-50' : ''}`}>
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`text-lg font-extrabold px-3 py-1 rounded-lg ${VERDICT_STYLE[advice.verdict]}`}>{advice.verdict_label}</span>
            <div className="text-xs muted space-y-0.5">
              <div>Score <b className={advice.score >= 0 ? 'up' : 'down'}>{advice.score > 0 ? '+' : ''}{advice.score}</b>/100 · {t.confidence} {t[`conf_${advice.confidence}` as 'conf_low']}</div>
              {advice.horizon && <div>{t.horizon} : {advice.horizon}</div>}
            </div>
          </div>
          <div className="h-2 rounded-full bg-gradient-to-r from-rose-500 via-slate-400 to-emerald-500 relative">
            <div className="absolute -top-1 w-1.5 h-4 rounded bg-slate-900 dark:bg-white shadow" style={{ left: `calc(${gauge}% - 3px)` }} />
          </div>
          <p className="text-sm leading-relaxed">{advice.summary}</p>

          <Section icon={<TrendingUp className="w-3.5 h-3.5" />} title={t.opportunities} items={advice.opportunities} tone="up" />
          <Section icon={<TrendingDown className="w-3.5 h-3.5" />} title={t.threats} items={advice.threats} tone="down" />
          <Section icon={<Repeat className="w-3.5 h-3.5" />} title={t.patterns} items={advice.patterns} tone="text-sky-600 dark:text-sky-400" />
          <Section icon={<CalendarClock className="w-3.5 h-3.5" />} title={t.catalysts} items={advice.catalysts} tone="text-violet-600 dark:text-violet-400" />

          {advice.events.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-1.5 text-amber-600 dark:text-amber-400">
                <Zap className="w-3.5 h-3.5" />{t.events}
              </div>
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                {advice.events.map((e) => (
                  <button key={e.date} onClick={() => onShowDate(Date.parse(e.date) / 1000)}
                    className="w-full text-left text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-amber-400 cursor-pointer">
                    <div className="flex justify-between gap-2">
                      <span className="font-mono">{new Date(e.date).toLocaleDateString(lang)}</span>
                      <span className={e.change >= 0 ? 'up font-bold' : 'down font-bold'}>{e.change > 0 ? '+' : ''}{e.change}%</span>
                      {e.after_20d !== null && <span className="muted">{t.after20d} : <b className={e.after_20d >= 0 ? 'up' : 'down'}>{e.after_20d > 0 ? '+' : ''}{e.after_20d}%</b></span>}
                    </div>
                    {e.headlines[0] && <div className="muted truncate mt-0.5">{e.headlines[0]}</div>}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="text-[11px] muted border-t border-slate-200 dark:border-slate-800 pt-2 space-y-1">
            {advice.ai_error && <p className="text-amber-500">{t.aiError} {advice.ai_error}</p>}
            <p>{advice.engine === 'local' ? t.engineLocal : `${t.engineAI} (${advice.engine})`} · {advice.articles_analyzed} {t.articlesAnalyzed} · {new Date(advice.generated_at * 1000).toLocaleString(lang)}</p>
            {advice.engine === 'local' && <p>{t.enableAi}</p>}
            <p>{t.disclaimer}</p>
          </div>
        </div>
      )}
    </div>
  );
}
