import { ReactNode, useEffect, useState } from 'react';
import {
  Activity, Building2, CalendarClock, History, Layers3, Newspaper, RefreshCw, Repeat, ShieldCheck, Sparkles, Target,
  TrendingDown, TrendingUp, Zap,
} from 'lucide-react';
import { Advice, api, bigMoney, errorMessage, Fundamentals, HealthScores, onPortfolioChanged, pct } from '../services/api';
import { useI18n, VERDICT_STYLE } from '../context';
import { OrderModal } from './OrderModal';
import { EnsemblePanel, notifyAiSaved, SavedAnalysesPanel } from './AiAnalysesPanel';

type Tab = 'company' | 'risk' | 'reliability' | 'ensemble' | 'saved' | 'events' | 'news';
const TABS: [Tab, typeof Building2][] = [['company', Building2], ['risk', Activity], ['reliability', ShieldCheck], ['ensemble', Layers3],
  ['saved', History], ['events', Zap], ['news', Newspaper]];
const readTab = (): Tab => { try { return (localStorage.getItem('stockpulse:analysisTab') as Tab) || 'company'; } catch { return 'company'; } };

interface Props {
  symbol: string;
  chart: ReactNode;
  news: ReactNode;
  onAdvice: (a: Advice) => void;
  onShowDate: (ts: number) => void;
}

const HORIZON = { '1m': '1 m', '3m': '3 m', '6m': '6 m' } as const;
const sign = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(d)} %`);
const tone = (v: number | null | undefined) => (v === null || v === undefined ? '' : v >= 0 ? 'up' : 'down');

function List({ icon, title, items, color }: { icon: ReactNode; title: string; items: string[]; color: string }) {
  if (!items.length) return null;
  return (
    <div>
      <div className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-1.5 ${color}`}>{icon}{title}</div>
      <ul className="space-y-1 text-sm">{items.map((x, i) => <li key={i} className="pl-3 border-l-2 border-slate-200 dark:border-slate-700">{x}</li>)}</ul>
    </div>
  );
}

function Stat({ label, value, sub, cls = '' }: { label: string; value: ReactNode; sub?: ReactNode; cls?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2.5">
      <div className="text-[11px] muted">{label}</div>
      <div className={`text-base font-bold ${cls}`}>{value}</div>
      {sub && <div className="text-[11px] muted">{sub}</div>}
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number | null }) {
  const color = value === null ? '' : value >= 66 ? 'bg-emerald-500' : value >= 33 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="text-xs">
      <div className="flex justify-between"><span>{label}</span><b>{value === null ? '–' : `${value}/100`}</b></div>
      <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 mt-0.5">{value !== null && <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />}</div>
    </div>
  );
}

/** Onglet « Entreprise » : récapitulatif (résumé, opportunités, menaces…) et chiffres de l'entreprise. */
function CompanyTab({ a }: { a: Advice }) {
  const { t, lang } = useI18n();
  const f: Fundamentals | null = a.fundamentals;
  const cur = f?.currency ?? 'USD';
  const h: HealthScores | null | undefined = a.health;
  const num = (v: number | null | undefined, d = 1, u = '') => (v === null || v === undefined ? '–' : `${v.toLocaleString(lang, { maximumFractionDigits: d })}${u}`);
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <p className="text-sm leading-relaxed">{a.summary}</p>
        <List icon={<TrendingUp className="w-3.5 h-3.5" />} title={t.opportunities} items={a.opportunities} color="up" />
        <List icon={<TrendingDown className="w-3.5 h-3.5" />} title={t.threats} items={a.threats} color="down" />
        <List icon={<Repeat className="w-3.5 h-3.5" />} title={t.patterns} items={a.patterns} color="text-sky-600 dark:text-sky-400" />
        <List icon={<CalendarClock className="w-3.5 h-3.5" />} title={t.catalysts} items={a.catalysts} color="text-violet-600 dark:text-violet-400" />
      </div>
      <div className="space-y-4">
        <div className="flex justify-between items-baseline">
          <h3 className="font-bold">{t.keyFigures}</h3>
          {f && <span className="text-[11px] muted">{f.source} · {new Date(f.fetched_at * 1000).toLocaleDateString(lang)}</span>}
        </div>
        {!f ? <p className="text-sm muted">{t.fundNeedKey}</p> : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Stat label={t.f_revenue} value={bigMoney(f.revenue, lang, cur)} sub={f.revenue_growth != null && <span className={tone(f.revenue_growth)}>{sign(f.revenue_growth)} {t.f_yoy}</span>} />
              <Stat label={t.f_net_income} value={bigMoney(f.net_income, lang, cur)} sub={f.earnings_growth != null && <span className={tone(f.earnings_growth)}>{sign(f.earnings_growth)} {t.f_yoy}</span>} />
              <Stat label={t.f_cap} value={bigMoney(f.market_cap, lang, cur)} />
              <Stat label={t.f_margin} value={num(f.net_margin, 1, ' %')} cls={tone(f.net_margin)} />
              <Stat label={t.f_op_margin} value={num(f.operating_margin, 1, ' %')} />
              <Stat label={t.f_gross_margin} value={num(f.gross_margin, 1, ' %')} />
              <Stat label={t.f_roe} value={num(f.roe, 1, ' %')} />
              <Stat label={t.f_pe} value={num(f.pe, 1)} sub={f.forward_pe != null && `${t.f_forward} ${num(f.forward_pe, 1)}`} />
              <Stat label={t.f_eps} value={num(f.eps, 2)} />
              <Stat label={t.f_debt} value={num(f.debt_to_equity, 2)} />
              <Stat label={t.f_div_yield} value={num(f.dividend_yield ?? (a.technicals.dividend_yield as number | null), 2, ' %')} />
              <Stat label={t.f_target} value={num(f.target_price, 2)} />
            </div>
            <div className="text-xs grid grid-cols-2 gap-2">
              <span>{t.f_earnings} : <b>{f.next_earnings ? new Date(f.next_earnings).toLocaleDateString(lang) : '–'}</b></span>
              <span>{t.f_dividend} : <b>{f.next_dividend ? `${new Date(f.next_dividend.date).toLocaleDateString(lang)} (${f.next_dividend.amount ?? '?'})` : '–'}</b></span>
            </div>
            {!!f.annual?.length && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="muted text-right"><th className="text-left py-1">{t.f_year}</th><th>{t.f_revenue}</th><th>{t.f_op_income}</th><th>{t.f_net_income}</th><th>{t.f_margin}</th></tr></thead>
                  <tbody>
                    {f.annual.map((y) => (
                      <tr key={y.year} className="border-t border-slate-200 dark:border-slate-800 text-right">
                        <td className="text-left py-1 font-mono">{y.year}</td><td>{bigMoney(y.revenue, lang, cur)}</td><td>{bigMoney(y.operating_income, lang, cur)}</td>
                        <td className={tone(y.net_income)}>{bigMoney(y.net_income, lang, cur)}</td>
                        <td>{y.revenue && y.net_income != null ? `${((y.net_income / y.revenue) * 100).toFixed(1)} %` : '–'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
        {h && h.overall !== null && (
          <div className="space-y-1.5 rounded-lg border border-slate-200 dark:border-slate-800 p-3">
            <div className="flex justify-between text-sm"><b>{t.healthScore}</b><b>{h.overall}/100</b></div>
            <Bar label={t.h_profitability} value={h.profitability} />
            <Bar label={t.h_growth} value={h.growth} />
            <Bar label={t.h_solidity} value={h.solidity} />
            <Bar label={t.h_valuation} value={h.valuation} />
            <p className="text-[11px] muted">{t.healthHelp}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function RiskTab({ a }: { a: Advice }) {
  const { t } = useI18n();
  const r = a.risk && 'volatility' in a.risk ? a.risk : null;
  const rel = a.relative;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-3">
        <h3 className="font-bold">{t.riskTitle}</h3>
        {!r ? <p className="text-sm muted">{t.notEnoughHistory}</p> : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Stat label={t.riskLevel} value={t[`risk_${r.level}`]} cls={r.level === 'low' ? 'up' : r.level === 'very_high' ? 'down' : ''} />
              <Stat label={t.r_vol} value={`${r.volatility} %`} sub={t.r_vol_sub} />
              <Stat label={t.r_beta} value={r.beta ?? '–'} sub={rel?.benchmark} />
              <Stat label={t.r_mdd} value={`${r.max_drawdown_5y} %`} cls="down" />
              <Stat label={t.r_bad_year} value={sign(r.bad_year)} cls={tone(r.bad_year)} sub={t.r_bad_year_sub} />
              <Stat label={t.r_worst_month} value={sign(r.worst_month)} cls="down" />
            </div>
            <p className="text-xs muted">{t.riskHelp}</p>
          </>
        )}
      </div>
      <div className="space-y-3">
        <h3 className="font-bold">{t.relTitle}</h3>
        {!rel || rel.excess_12m === undefined ? <p className="text-sm muted">{t.notEnoughHistory}</p> : (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Stat label={`${t.rel_vs} ${rel.benchmark} · 6 m`} value={sign(rel.excess_6m)} cls={tone(rel.excess_6m)} />
              <Stat label={`${t.rel_vs} ${rel.benchmark} · 12 m`} value={sign(rel.excess_12m)} cls={tone(rel.excess_12m)} />
              <Stat label={t.rel_mom} value={sign(rel.momentum_12_1)} cls={tone(rel.momentum_12_1)} />
              <Stat label={t.rel_rank} value={rel.sector_rank !== undefined ? `${rel.sector_rank}/100` : '–'}
                sub={rel.sector_peers ? `${rel.sector_peers} ${t.rel_peers} · ${t.rel_median} ${sign(rel.sector_median)}` : t.rel_no_peers} />
            </div>
            <p className="text-xs muted">{t.relHelp}</p>
          </>
        )}
      </div>
    </div>
  );
}

function ReliabilityTab({ a }: { a: Advice }) {
  const { t } = useI18n();
  const tr = a.track_record;
  const live = a.live_record;
  const rel = a.reliability;
  return (
    <div className="space-y-4">
      {rel && <p className="text-sm">{t[`relia_${rel.level}_long`].replace('{t}', String(rel.threshold))}</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 text-sm space-y-1">
          <b>{t.trackRecord}</b>
          {tr ? (['1m', '3m', '6m'] as const).map((h) => tr[h].hit_rate !== null && (
            <div key={h} className="flex justify-between"><span>{HORIZON[h]}</span>
              <span><b className={tr[h].hit_rate! >= 55 ? 'up' : tr[h].hit_rate! < 45 ? 'down' : ''}>{tr[h].hit_rate} %</b> {t.trHit} <span className="muted">({tr[h].n})</span>
                {tr[h].avg_after_buy !== null && <span className="muted"> · {t.trAfterBuy} {pct(tr[h].avg_after_buy)}</span>}</span></div>
          )) : <p className="muted">{t.notEnoughHistory}</p>}
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 text-sm space-y-1">
          <b>{t.liveRecord}</b>
          {live && live.n > 0 ? (['1m', '3m', '6m'] as const).map((h) => (
            <div key={h} className="flex justify-between"><span>{HORIZON[h]}</span>
              <span>{live[h]?.hit_rate != null ? <><b>{live[h]!.hit_rate} %</b> {t.trHit} <span className="muted">({live[h]!.n})</span></> : <span className="muted">{t.liveWaiting}</span>}</span></div>
          )) : <p className="muted">{t.liveEmpty}</p>}
          <p className="text-[11px] muted">{t.liveHelp}</p>
        </div>
      </div>
      {a.verification && (
        <div className={`text-xs rounded-lg p-2 border ${a.verification.status === 'verified' ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-amber-500/40 bg-amber-500/5'}`}>
          <b className={a.verification.status === 'verified' ? 'up' : 'text-amber-600 dark:text-amber-400'}>{a.verification.status === 'verified' ? `✓ ${t.verified}` : `⚠ ${t.toVerify}`}</b>
          <span className="muted"> ({a.verification.checked})</span>
          {a.verification.notes.map((n) => (
            <div key={n}>{t[`note_${n}` as 'note_verdict_score_mismatch'].replace('{s}', `${a.verification!.local_score > 0 ? '+' : ''}${a.verification!.local_score}`)}</div>
          ))}
          {a.verification.unverified.length > 0 && (
            <div className="mt-1"><span className="muted">{t.unverifiedClaims} :</span><ul className="list-disc pl-4">{a.verification.unverified.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
          )}
        </div>
      )}
      <p className="text-xs muted">{t.reliaMethod}</p>
    </div>
  );
}

function EventsTab({ a, onShowDate }: { a: Advice; onShowDate: (ts: number) => void }) {
  const { t, lang } = useI18n();
  if (!a.events.length) return <p className="text-sm muted">{t.notEnoughHistory}</p>;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
      {a.events.map((e) => (
        <button key={e.date} onClick={() => onShowDate(Date.parse(e.date) / 1000)}
          className="text-left text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-amber-400 cursor-pointer">
          <div className="flex justify-between gap-2">
            <span className="font-mono">{new Date(e.date).toLocaleDateString(lang)}</span>
            <span className={e.change >= 0 ? 'up font-bold' : 'down font-bold'}>{e.change > 0 ? '+' : ''}{e.change}%</span>
            {e.after_20d !== null && <span className="muted">{t.after20d} : <b className={e.after_20d >= 0 ? 'up' : 'down'}>{e.after_20d > 0 ? '+' : ''}{e.after_20d}%</b></span>}
          </div>
          {e.headlines[0] && <div className="muted truncate mt-0.5">{e.headlines[0]}</div>}
        </button>
      ))}
    </div>
  );
}

/** Carte de décision : verdict, fiabilité du signal, taille de ligne conseillée, scénarios IA et ordres. */
function DecisionCard({ a, loading, held, weight, onRefresh, onAi, onOrder }: {
  a: Advice | null; loading: boolean; held: boolean; weight: number | null;
  onRefresh: () => void; onAi: () => void; onOrder: (s: 'buy' | 'sell' | 'reduce') => void;
}) {
  const { t, lang } = useI18n();
  const rel = a?.reliability;
  const risk = a?.risk && 'max_weight' in a.risk ? a.risk : null;
  const o = a?.outlook;
  return (
    <div className="card p-5 space-y-4 h-full">
      <div className="flex justify-between items-center gap-2">
        <h2 className="font-bold flex items-center gap-2"><Target className="w-4 h-4 text-sky-500" />{t.decisionTitle}</h2>
        <div className="flex gap-2">
          <button className="btn" onClick={onRefresh} disabled={loading} title={t.engineLocal}><RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />{t.refresh}</button>
          <button className="btn-primary" onClick={onAi} disabled={loading}><Sparkles className="w-3.5 h-3.5" />{t.aiAnalyze}</button>
        </div>
      </div>
      {!a ? <p className="text-sm muted animate-pulse">{t.analyzing}</p> : (
        <div className={`space-y-4 ${loading ? 'opacity-50' : ''}`}>
          {rel && !rel.signal ? (
            <div className="rounded-lg p-3 border border-slate-300 dark:border-slate-700">
              <div className="text-lg font-extrabold">{t.noSignal}</div>
              <div className="text-xs muted">{t[`relia_${rel.level}`]} · {t.rawVerdict} : <span className={`px-1.5 rounded ${VERDICT_STYLE[a.verdict]}`}>{a.verdict_label}</span> ({a.score > 0 ? '+' : ''}{a.score})</div>
            </div>
          ) : (
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`text-lg font-extrabold px-3 py-1 rounded-lg ${VERDICT_STYLE[a.verdict]}`}>{a.verdict_label}</span>
              <div className="text-xs muted space-y-0.5">
                <div>Score <b className={a.score >= 0 ? 'up' : 'down'}>{a.score > 0 ? '+' : ''}{a.score}</b>/100 · {t.confidence} {t[`conf_${a.confidence}` as 'conf_low']}</div>
                {rel && <div className="up font-semibold">✓ {t.relia_reliable}</div>}
              </div>
            </div>
          )}
          <div className="h-2 rounded-full bg-gradient-to-r from-rose-500 via-slate-400 to-emerald-500 relative">
            <div className="absolute -top-1 w-1.5 h-4 rounded bg-slate-900 dark:bg-white shadow" style={{ left: `calc(${(a.score + 100) / 2}% - 3px)` }} />
          </div>
          {risk && (
            <div className="rounded-lg p-3 bg-sky-500/5 border border-sky-500/30 text-sm">
              <div>{t.positionMax} <b>{risk.max_weight} %</b> {t.positionOfPea}
                {held && weight !== null && <span className={weight > risk.max_weight ? 'down font-semibold' : 'muted'}> · {t.positionNow} {weight.toFixed(1)} %</span>}</div>
              <div className="text-[11px] muted">{t.positionHelp.replace('{v}', String(risk.volatility)).replace('{l}', t[`risk_${risk.level}`].toLowerCase())}</div>
            </div>
          )}
          {o && (
            <div className="rounded-lg p-3 border border-violet-500/30 bg-violet-500/5 text-sm space-y-1">
              <div className="font-semibold">{t.aiOutlook}</div>
              <div className="flex gap-3 text-xs flex-wrap">
                {(['bear', 'base', 'bull'] as const).map((k) => (
                  <span key={k}>{t[`sc_${k}`]} <b className={tone(o.scenarios[k].return_12m)}>{sign(o.scenarios[k].return_12m, 0)}</b> <span className="muted">({o.scenarios[k].probability} %)</span></span>
                ))}
              </div>
              <div className="text-xs">{t.aiExpected} <b>{sign(o.expected_12m_adjusted)}</b> <span className="muted">({t.aiRaw} {sign(o.expected_12m)})</span>
                {o.prob_outperform_adjusted !== null && <> · {t.aiProbBeat} <b>{o.prob_outperform_adjusted} %</b> <span className="muted">({t.aiRaw} {o.prob_outperform} %)</span></>}</div>
              <div className="text-[11px] muted">{t.aiShrinkHelp}</div>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button className={rel?.signal && a.score >= 15 ? 'btn-primary' : 'btn'} onClick={() => onOrder('buy')}>{t.prepareBuy}</button>
            {held && <button className={a.verdict === 'REDUCE' ? 'btn-primary' : 'btn'} onClick={() => onOrder('reduce')}>{t.prepareReduce}</button>}
            {held && <button className={a.verdict === 'SELL' ? 'btn-primary' : 'btn'} onClick={() => onOrder('sell')}>{t.prepareSell}</button>}
          </div>
          <div className="text-[11px] muted border-t border-slate-200 dark:border-slate-800 pt-2 space-y-1">
            {a.ai_error && <p className="text-amber-500">{t.aiError} {a.ai_error}</p>}
            <p>{a.engine === 'local' ? t.engineLocal : `${t.engineAI} (${a.engine})`} · {a.articles_analyzed} {t.articlesAnalyzed} · {new Date(a.generated_at * 1000).toLocaleString(lang)}</p>
            {a.engine === 'local' && <p>{t.aiManualHelp}</p>}
            <p>{t.disclaimer}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function AnalysisSection({ symbol, chart, news, onAdvice, onShowDate }: Props) {
  const { t, lang } = useI18n();
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<'buy' | 'sell' | 'reduce' | null>(null);
  const [held, setHeld] = useState(false);
  const [weight, setWeight] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>(readTab);
  const choose = (x: Tab) => { setTab(x); try { localStorage.setItem('stockpulse:analysisTab', x); } catch { /* indisponible */ } };

  useEffect(() => {
    const check = () => api.portfolio().then((p) => {
      const line = p.lines.find((l) => l.symbol === symbol);
      setHeld(!!line);
      setWeight(line ? line.weight : null);
    }).catch(() => {});
    check();
    return onPortfolioChanged(check);
  }, [symbol]);

  const load = (refresh = false, ai = false) => {
    setLoading(true);
    setError(null);
    api.advice(symbol, lang, refresh, ai)
      .then((a) => { setAdvice(a); onAdvice(a); if (ai && a.engine !== 'local') notifyAiSaved(); })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  };
  useEffect(() => { setAdvice(null); load(); }, [symbol, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {order && <OrderModal symbol={symbol} side={order} onClose={() => setOrder(null)} />}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2">{chart}</div>
        <div>
          <DecisionCard a={advice} loading={loading} held={held} weight={weight}
            onRefresh={() => load(true)} onAi={() => load(true, true)} onOrder={setOrder} />
          {error && <p className="text-sm text-rose-500 mt-2">{error}</p>}
        </div>
      </div>

      <div className="card">
        <div className="flex overflow-x-auto border-b border-slate-200 dark:border-slate-800 px-2">
          {TABS.map(([k, Icon]) => (
            <button key={k} onClick={() => choose(k)}
              className={`flex items-center gap-1.5 px-3 py-3 text-sm whitespace-nowrap cursor-pointer border-b-2 -mb-px ${tab === k ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-semibold' : 'border-transparent muted hover:text-slate-900 dark:hover:text-white'}`}>
              <Icon className="w-4 h-4" />{t[`tab_${k}`]}
              {k === 'reliability' && advice?.reliability && <span className={`w-2 h-2 rounded-full ${advice.reliability.signal ? 'bg-emerald-500' : 'bg-amber-500'}`} />}
            </button>
          ))}
        </div>
        <div className="p-5">
          {!advice && ['company', 'risk', 'reliability', 'events'].includes(tab) ? <p className="text-sm muted animate-pulse">{t.analyzing}</p> : (
            <>
              {tab === 'company' && advice && <CompanyTab a={advice} />}
              {tab === 'risk' && advice && <RiskTab a={advice} />}
              {tab === 'reliability' && advice && <ReliabilityTab a={advice} />}
              {tab === 'events' && advice && <EventsTab a={advice} onShowDate={onShowDate} />}
            </>
          )}
          {tab === 'ensemble' && <EnsemblePanel symbol={symbol} bare />}
          {tab === 'saved' && <SavedAnalysesPanel symbol={symbol} bare />}
          {tab === 'news' && news}
        </div>
      </div>
    </>
  );
}
