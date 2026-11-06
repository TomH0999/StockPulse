import { ReactNode, useEffect, useState } from 'react';
import {
  Activity, Bot, Building2, CalendarClock, History, Landmark, Layers3, Newspaper, NotebookPen, RefreshCw, Repeat, ShieldCheck,
  Sparkles, Target, TrendingDown, TrendingUp, Zap,
} from 'lucide-react';
import { Advice, AiView, api, bigMoney, Envelope, errorMessage, Financials, HealthScores, onPortfolioChanged, pct } from '../services/api';
import { useI18n, VERDICT_STYLE } from '../context';
import { OrderModal } from './OrderModal';
import { EnsemblePanel, notifyAiSaved, SavedAnalysesPanel } from './AiAnalysesPanel';
import { ThesisEditor } from './ThesisEditor';
import { ModelReliability } from './ModelReliability';

type Tab = 'company' | 'risk' | 'reliability' | 'ai' | 'ensemble' | 'saved' | 'events' | 'news';
const TABS: [Tab, typeof Building2][] = [['company', Building2], ['risk', Activity], ['reliability', ShieldCheck], ['ai', Bot],
  ['ensemble', Layers3], ['saved', History], ['events', Zap], ['news', Newspaper]];
const readTab = (): Tab => { try { return (localStorage.getItem('stockpulse:analysisTab') as Tab) || 'company'; } catch { return 'company'; } };
const HORIZONS = ['1y', '3y', '5y'] as const;

interface Props {
  symbol: string;
  chart: ReactNode;
  news: ReactNode;
  onAdvice: (a: Advice) => void;
  onShowDate: (ts: number) => void;
}

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

function Stat({ label, value, sub, cls = '', hint }: { label: string; value: ReactNode; sub?: ReactNode; cls?: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2.5" title={hint}>
      <div className="text-[11px] muted">{label}</div>
      <div className={`text-base font-bold ${cls}`}>{value}</div>
      {sub && <div className="text-[11px] muted">{sub}</div>}
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number | null | undefined }) {
  const v = value ?? null;
  const color = v === null ? '' : v >= 66 ? 'bg-emerald-500' : v >= 33 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="text-xs">
      <div className="flex justify-between"><span>{label}</span><b>{v === null ? '–' : `${v}/100`}</b></div>
      <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 mt-0.5">{v !== null && <div className={`h-full rounded-full ${color}`} style={{ width: `${v}%` }} />}</div>
    </div>
  );
}

/** Onglet « Entreprise » : récapitulatif et chiffres publiés (comptes annuels, sans clé). */
function CompanyTab({ a }: { a: Advice }) {
  const { t, lang } = useI18n();
  const f: Financials | null | undefined = a.financials;
  const cur = f?.currency ?? undefined;
  const h: HealthScores | null | undefined = a.health;
  const n = (v: number | null | undefined, d = 1, u = '') => (v === null || v === undefined ? '–' : `${v.toLocaleString(lang, { maximumFractionDigits: d })}${u}`);
  const money = (v: number | null | undefined) => bigMoney(v, lang, cur ?? 'EUR');
  const dv = f?.dividends;
  const key = a.fundamentals;
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <div className="space-y-4">
        <p className="text-sm leading-relaxed">{a.summary}</p>
        {a.components && (
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            {(['valuation', 'strength', 'growth', 'quality', 'trend', 'momentum'] as const).map((g) => (
              <span key={g} className="px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-700">
                {t[`grp_${g}`]} <b className={tone(a.components![g])}>{a.components![g] !== undefined ? `${a.components![g] > 0 ? '+' : ''}${a.components![g]}` : '–'}</b>
                <span className="muted">/{{ valuation: 18, strength: 15, growth: 15, quality: 25, trend: 15, momentum: 12 }[g]}</span>
              </span>
            ))}
          </div>
        )}
        <List icon={<TrendingUp className="w-3.5 h-3.5" />} title={t.opportunities} items={a.opportunities} color="up" />
        <List icon={<TrendingDown className="w-3.5 h-3.5" />} title={t.threats} items={a.threats} color="down" />
        <List icon={<Repeat className="w-3.5 h-3.5" />} title={t.patterns} items={a.patterns} color="text-sky-600 dark:text-sky-400" />
        <List icon={<CalendarClock className="w-3.5 h-3.5" />} title={t.catalysts} items={a.catalysts} color="text-violet-600 dark:text-violet-400" />
      </div>
      <div className="space-y-4">
        <div className="flex justify-between items-baseline">
          <h3 className="font-bold">{t.keyFigures}</h3>
          {f?.years ? <span className="text-[11px] muted">{t.finSource} · {f.first_year}–{f.last_year} ({f.years} {t.finYears})</span> : null}
        </div>
        {!f?.years ? <p className="text-sm muted">{a.kind && a.kind !== 'stock' ? t.finNotStock : t.finMissing}</p> : (
          <>
            <div className="text-xs font-semibold muted uppercase tracking-wider">{t.finValuation}</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Stat label={t.f_fcf_yield} value={n(f.fcf_yield, 1, ' %')} cls={tone((f.fcf_yield ?? 0) - 3)} hint={t.h_fcf_yield} />
              <Stat label={t.f_pe} value={f.pe_loss ? t.f_loss : n(f.pe, 1)}
                sub={f.pe_history_median ? `${t.f_pe_hist} ${n(f.pe_history_median, 1)}` : undefined} />
              <Stat label={t.f_ev_ebit} value={n(f.ev_ebit, 1)} />
              <Stat label={t.f_cap} value={money(f.market_cap)} />
              <Stat label={t.f_div_yield} value={n(f.dividend_yield, 2, ' %')} sub={f.payout_ratio != null ? `${t.f_payout} ${n(f.payout_ratio, 0, ' %')}` : undefined} />
              <Stat label={t.f_buyback} value={n(f.buyback_yield, 2, ' %')} />
            </div>
            <div className="text-xs font-semibold muted uppercase tracking-wider">{t.finQuality}</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {f.financial_sector
                ? <Stat label={t.f_roe} value={n(f.roe_avg, 1, ' %')} sub={t.f_avg} />
                : <Stat label={t.f_roic} value={n(f.roic_avg, 1, ' %')} sub={f.roic_min != null ? `${t.f_min} ${n(f.roic_min, 1, ' %')}` : undefined} hint={t.h_roic} />}
              <Stat label={t.f_op_margin} value={n(f.operating_margin, 1, ' %')} sub={f.op_margin_std != null ? `${t.f_std} ${n(f.op_margin_std, 1)} pt` : undefined} />
              <Stat label={t.f_fcf_margin} value={n(f.fcf_margin, 1, ' %')} sub={`${f.fcf_positive_years ?? 0}/${f.years} ${t.f_fcf_pos}`} />
              <Stat label={t.f_dilution} value={sign(f.dilution_pa)} cls={tone(-(f.dilution_pa ?? 0))} sub={t.f_per_year} />
              <Stat label={t.f_net_debt_ebitda} value={f.financial_sector ? t.f_na_bank : n(f.net_debt_ebitda, 2)} />
              <Stat label={t.f_coverage} value={f.financial_sector ? t.f_na_bank : n(f.interest_coverage, 1, ' ×')} />
            </div>
            <div className="text-xs font-semibold muted uppercase tracking-wider">{t.finGrowth}</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Stat label={t.f_revenue_cagr} value={sign(f.revenue_cagr)} cls={tone(f.revenue_cagr)} sub={t.f_per_year} />
              <Stat label={t.f_eps_cagr} value={sign(f.eps_cagr)} cls={tone(f.eps_cagr)} sub={t.f_per_year} />
              <Stat label={t.f_div_growth} value={sign(dv?.growth_5y)} cls={tone(dv?.growth_5y)}
                sub={dv?.growth_10y != null ? `10 ${t.f_years_short} ${sign(dv.growth_10y)}` : undefined} />
              <Stat label={t.f_div_streak} value={dv?.years_paid ? `${dv.years_without_cut ?? 0} ${t.f_years_short}` : '–'}
                sub={dv?.years_paid ? `${dv.years_paid} ${t.f_years_paid}` : undefined} />
            </div>
            {!!f.annual?.length && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="muted text-right"><th className="text-left py-1">{t.f_year}</th><th>{t.f_revenue}</th><th>{t.f_op_income}</th>
                    <th>{t.f_net_income}</th><th>{t.f_fcf}</th><th>{t.f_eps}</th>{!f.financial_sector && <th>ROIC</th>}</tr></thead>
                  <tbody>
                    {f.annual.map((y) => (
                      <tr key={y.year} className="border-t border-slate-200 dark:border-slate-800 text-right">
                        <td className="text-left py-1 font-mono">{y.year}</td><td>{money(y.revenue)}</td><td>{money(y.operating_income)}</td>
                        <td className={tone(y.net_income)}>{money(y.net_income)}</td><td className={tone(y.free_cash_flow)}>{money(y.free_cash_flow)}</td>
                        <td>{n(y.eps, 2)}</td>{!f.financial_sector && <td>{n(y.roic, 1, ' %')}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-[11px] muted">{t.finLimit}</p>
          </>
        )}
        {key && (key.surprises?.length || key.recommendations || key.insiders) && (
          <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 text-xs space-y-1">
            <b className="text-sm">{t.analystsTitle}</b>
            {!!key.surprises?.length && <div>{t.surprisesLabel} : {key.surprises.map((x) => x.surprise_pct == null ? null : (
              <span key={x.period} className={`mr-2 ${x.surprise_pct >= 0 ? 'up' : 'down'}`}>{x.period?.slice(0, 7)} {x.surprise_pct > 0 ? '+' : ''}{x.surprise_pct} %</span>))}</div>}
            {key.recommendations && <div>{t.revisionsLabel} : {Number(key.recommendations.now.strongBuy ?? 0) + Number(key.recommendations.now.buy ?? 0)} {t.buyRatings}
              <span className="muted"> ({t.vs3m} {Number(key.recommendations.before.strongBuy ?? 0) + Number(key.recommendations.before.buy ?? 0)})</span></div>}
            {key.insiders && <div>{t.insidersLabel} : <span className="up">+{key.insiders.bought.toLocaleString(lang)}</span> / <span className="down">−{key.insiders.sold.toLocaleString(lang)}</span> {t.sharesLabel} ({key.insiders.days} j)</div>}
          </div>
        )}
        {!key && <p className="text-[11px] muted">{t.analystsNeedKey}</p>}
        {key && (key.next_earnings || key.target_price) && (
          <div className="text-xs grid grid-cols-2 gap-2">
            <span>{t.f_earnings} : <b>{key.next_earnings ? new Date(key.next_earnings).toLocaleDateString(lang) : '–'}</b></span>
            <span>{t.f_target} : <b>{n(key.target_price, 2)}</b></span>
          </div>
        )}
        {h && h.overall !== null && (
          <div className="space-y-1.5 rounded-lg border border-slate-200 dark:border-slate-800 p-3">
            <div className="flex justify-between text-sm"><b>{t.healthScore}</b><b>{h.overall}/100</b></div>
            <Bar label={t.h_profitability} value={h.profitability} />
            <Bar label={t.h_growth} value={h.growth} />
            <Bar label={t.h_solidity} value={h.solidity} />
            <Bar label={t.h_valuation} value={h.valuation} />
            <Bar label={t.h_regularity} value={h.regularity} />
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
  const tr = a.track_record ?? {};
  const live = a.live_record;
  const rel = a.reliability;
  return (
    <div className="space-y-4">
      <h3 className="font-bold">{t.mvTitle}</h3>
      <ModelReliability />
      <h3 className="font-bold pt-2">{t.stockReplayTitle}</h3>
      <p className="text-xs muted">{t.stockReplayHelp}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="muted text-xs text-right"><th className="text-left py-1">{t.btHorizon}</th><th>{t.btSamples}</th><th>{t.btBase}</th>
            <th>{t.btBuyHit}</th><th>{t.btSellHit}</th><th>{t.btEdge}</th><th>{t.btExcess}</th></tr></thead>
          <tbody>
            {HORIZONS.map((h) => {
              const s = tr[h];
              return (
                <tr key={h} className="border-t border-slate-200 dark:border-slate-800 text-right">
                  <td className="text-left py-1.5">{t[`hz_${h}`]} {s?.engine === 'trend_only' && <span className="text-[10px] muted">({t.btTrendOnly})</span>}</td>
                  <td>{s?.n ?? 0}</td><td>{s?.base != null ? `${s.base} %` : '–'}</td>
                  <td>{s?.buy_hit != null ? `${s.buy_hit} % (${s.buy_n})` : '–'}</td>
                  <td>{s?.sell_hit != null ? `${s.sell_hit} % (${s.sell_n})` : '–'}</td>
                  <td className={s?.edge == null ? '' : s.edge >= 5 ? 'up font-bold' : s.edge <= -5 ? 'down font-bold' : ''}>{s?.edge != null ? `${s.edge > 0 ? '+' : ''}${s.edge} pts` : '–'}</td>
                  <td className={tone(s?.avg_excess_buy)}>{sign(s?.avg_excess_buy)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs muted">{t.btHelp}</p>
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 text-sm space-y-1">
        <b>{t.liveRecord}</b>
        {live && live.n > 0 ? (['3m', '6m', '1y'] as const).map((h) => (
          <div key={h} className="flex justify-between"><span>{t[`hz_${h}`]}</span>
            <span>{live[h]?.hit_rate != null ? <><b>{live[h]!.hit_rate} %</b> {t.liveBeat} <span className="muted">({live[h]!.n})</span></> : <span className="muted">{t.liveWaiting}</span>}</span></div>
        )) : <p className="muted">{t.liveEmpty}</p>}
        <p className="text-[11px] muted">{t.liveHelp}</p>
      </div>
      <p className="text-xs muted">{t.reliaMethod}</p>
    </div>
  );
}

/** Lecture de l'IA : une explication à part, qui ne modifie jamais le verdict calculé. */
function AiTab({ a, loading, onAi }: { a: Advice; loading: boolean; onAi: () => void }) {
  const { t, lang } = useI18n();
  const v: AiView | undefined = a.ai_view;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <p className="text-sm muted max-w-3xl">{t.aiRoleHelp}</p>
        <button className="btn-primary" onClick={onAi} disabled={loading}><Sparkles className="w-3.5 h-3.5" />{t.aiAnalyze}</button>
      </div>
      {a.ai_error && <p className="text-sm text-amber-500">{t.aiError} {a.ai_error}</p>}
      {!v ? <p className="text-sm muted">{t.aiNone}</p> : (
        <div className="space-y-3">
          <div className="flex items-center gap-3 flex-wrap text-sm">
            <span>{t.aiOpinion} :</span>
            <span className={`font-bold px-2 py-0.5 rounded ${VERDICT_STYLE[v.verdict]}`}>{v.verdict_label}</span>
            <span className="muted">({v.score > 0 ? '+' : ''}{v.score}) · {v.provider} · {new Date(v.generated_at * 1000).toLocaleString(lang)}</span>
            {v.verdict !== a.verdict && <span className="text-xs text-amber-600 dark:text-amber-400">{t.aiDiffers}</span>}
          </div>
          <p className="text-sm leading-relaxed">{v.summary}</p>
          {v.outlook && (
            <div className="rounded-lg p-3 border border-violet-500/30 bg-violet-500/5 text-sm space-y-1">
              <div className="flex gap-3 text-xs flex-wrap">
                {(['bear', 'base', 'bull'] as const).map((k) => (
                  <span key={k}>{t[`sc_${k}`]} <b className={tone(v.outlook!.scenarios[k].return_12m)}>{sign(v.outlook!.scenarios[k].return_12m, 0)}</b> <span className="muted">({v.outlook!.scenarios[k].probability} %)</span></span>
                ))}
              </div>
              <div className="text-xs">{t.aiExpected} <b>{sign(v.outlook.expected_12m_adjusted)}</b> <span className="muted">({t.aiRaw} {sign(v.outlook.expected_12m)})</span>
                {v.outlook.prob_outperform_adjusted !== null && <> · {t.aiProbBeat} <b>{v.outlook.prob_outperform_adjusted} %</b></>}</div>
              <div className="text-[11px] muted">{t.aiShrinkHelp}</div>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <List icon={<TrendingUp className="w-3.5 h-3.5" />} title={t.opportunities} items={v.opportunities} color="up" />
            <List icon={<TrendingDown className="w-3.5 h-3.5" />} title={t.threats} items={v.threats} color="down" />
          </div>
          {v.verification && (
            <div className={`text-xs rounded-lg p-2 border ${v.verification.status === 'verified' ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-amber-500/40 bg-amber-500/5'}`}>
              <b className={v.verification.status === 'verified' ? 'up' : 'text-amber-600 dark:text-amber-400'}>{v.verification.status === 'verified' ? `✓ ${t.verified}` : `⚠ ${t.toVerify}`}</b>
              <span className="muted"> ({v.verification.checked})</span>
              {v.verification.notes.map((n) => (
                <div key={n}>{t[`note_${n}` as 'note_verdict_score_mismatch'].replace('{s}', `${v.verification!.local_score > 0 ? '+' : ''}${v.verification!.local_score}`)}</div>
              ))}
              {v.verification.unverified.length > 0 && (
                <div className="mt-1"><span className="muted">{t.unverifiedClaims} :</span><ul className="list-disc pl-4">{v.verification.unverified.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EventsTab({ a, onShowDate }: { a: Advice; onShowDate: (ts: number) => void }) {
  const { t, lang } = useI18n();
  const ne = a.news_events ?? [];
  const prior = (p: { mean: number; n: number; low: number | null; high: number | null } | null) =>
    !p ? '–' : `${p.mean > 0 ? '+' : ''}${p.mean.toFixed(1)} pts (${p.n}${p.n < 20 ? ` · ${t.evFew}` : ''})`;
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold">{t.evNewsTitle}</h3>
        <p className="text-xs muted">{t.evNewsHelp}</p>
        {!ne.length ? <p className="text-sm muted mt-1">{t.evNone}</p> : (
          <div className="overflow-x-auto mt-1">
            <table className="w-full text-xs">
              <thead><tr className="muted text-right"><th className="text-left py-1">{t.evWhat}</th><th>{t.evReaction}</th><th>{t.evPrior0}</th><th>{t.evPrior60}</th><th className="text-left pl-3">{t.evReading}</th></tr></thead>
              <tbody>
                {ne.map((e, i) => (
                  <tr key={i} className="border-t border-slate-200 dark:border-slate-800 text-right align-top">
                    <td className="text-left py-1.5 max-w-md">
                      <span className={`font-semibold ${e.direction > 0 ? 'up' : e.direction < 0 ? 'down' : ''}`}>{t[`ev_t_${e.type}` as 'ev_t_buyback'] ?? e.type}</span>
                      <span className="muted"> · {new Date(e.timestamp * 1000).toLocaleDateString(lang)} · {e.source}</span>
                      <a href={e.url} target="_blank" rel="noreferrer" className="block hover:text-sky-500 truncate">{e.headline}</a>
                      {e.ai && (e.ai.magnitude || e.ai.durable || e.ai.moat) && <span className="muted">{e.ai.magnitude ?? ''}{e.ai.durable ? ` · ${t.evDurable}` : ''}{e.ai.moat ? ` · ${t.evMoat}` : ''}</span>}
                    </td>
                    <td className={(e.reaction ?? 0) >= 0 ? 'up' : 'down'}>{e.reaction != null ? `${e.reaction > 0 ? '+' : ''}${e.reaction} %` : '–'}</td>
                    <td>{prior(e.prior_d0)}</td><td>{prior(e.prior_d60)}</td>
                    <td className="text-left pl-3">{e.note ? t[`evn_${e.note}` as 'evn_priced_as_usual'] : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {a.events.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-bold">{t.evShocksTitle}</h3>
          <p className="text-xs muted">{t.eventsHelp}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {a.events.map((e) => (
              <button key={e.date} onClick={() => onShowDate(Date.parse(e.date) / 1000)}
                className="text-left text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-amber-400 cursor-pointer">
                <div className="flex justify-between gap-2">
                  <span className="font-mono">{new Date(e.date).toLocaleDateString(lang)}</span>
                  <span className={e.change >= 0 ? 'up font-bold' : 'down font-bold'}>{e.change > 0 ? '+' : ''}{e.change}%</span>
                </div>
                {e.headlines[0] && <div className="muted truncate mt-0.5">{e.headlines[0]}</div>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** Carte de décision : verdict calculé, fiabilité mesurée, taille de ligne, enveloppe conseillée, thèse et ordres. */
function DecisionCard({ a, symbol, loading, held, weight, envelope, onRefresh, onOrder }: {
  a: Advice | null; symbol: string; loading: boolean; held: boolean; weight: number | null; envelope: Envelope | null;
  onRefresh: () => void; onOrder: (s: 'buy' | 'sell' | 'reduce') => void;
}) {
  const { t, lang } = useI18n();
  const [thesis, setThesis] = useState(false);
  const rel = a?.reliability;
  const risk = a?.risk && 'max_weight' in a.risk ? a.risk : null;
  const notStock = a?.kind && a.kind !== 'stock';
  return (
    <div className="card p-5 space-y-4 h-full">
      <div className="flex justify-between items-center gap-2">
        <h2 className="font-bold flex items-center gap-2"><Target className="w-4 h-4 text-sky-500" />{t.decisionTitle}</h2>
        <button className="btn" onClick={onRefresh} disabled={loading}><RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />{t.refresh}</button>
      </div>
      {!a ? <p className="text-sm muted animate-pulse">{t.analyzing}</p> : (
        <div className={`space-y-4 ${loading ? 'opacity-50' : ''}`}>
          {a.leveraged && <div className="rounded-lg p-2 text-xs bg-rose-500/10 text-rose-600 dark:text-rose-400 font-semibold">⚠ {t.leveragedWarn}</div>}
          {notStock ? (
            <div className="rounded-lg p-3 border border-slate-300 dark:border-slate-700"><div className="font-bold">{t[`kind_${a.kind ?? 'etf'}`]}</div><div className="text-xs muted">{t.etfNoVerdict}</div></div>
          ) : rel && !rel.signal ? (
            <div className={`rounded-lg p-3 border ${rel.level === 'contrarian' ? 'border-rose-500/50 bg-rose-500/5' : 'border-slate-300 dark:border-slate-700 bg-slate-500/5'}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`font-bold px-2 py-0.5 rounded ${VERDICT_STYLE[a.verdict]} opacity-80`}>{a.verdict_label}</span>
                <span className="text-xs muted">({a.score > 0 ? '+' : ''}{a.score}/100)</span>
              </div>
              <div className={`text-xs mt-1 ${rel.level === 'contrarian' ? 'down font-semibold' : 'muted'}`}>{t[`relia_${rel.level}`]}</div>
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
          {!notStock && (a.coverage ?? 0) < 0.5 && <p className="text-xs text-amber-600 dark:text-amber-400">{t.lowCoverage}</p>}
          {risk && (
            <div className="rounded-lg p-3 bg-sky-500/5 border border-sky-500/30 text-sm">
              <div>{t.positionMax} <b>{risk.max_weight} %</b> {t.positionOfAccount}
                {held && weight !== null && <span className={weight > risk.max_weight ? 'down font-semibold' : 'muted'}> · {t.positionNow} {weight.toFixed(1)} %</span>}</div>
              <div className="text-[11px] muted">{t.positionHelp.replace('{v}', String(risk.volatility)).replace('{l}', t[`risk_${risk.level}`].toLowerCase())}</div>
            </div>
          )}
          {envelope && (
            <div className="text-xs flex items-start gap-2"><Landmark className="w-3.5 h-3.5 mt-0.5 text-sky-500 shrink-0" />
              <span>{t.envelopeBest} <b>{envelope.label}</b>{!envelope.have && <span className="muted"> ({t.envelopeNotOpen})</span>}
                {' — '}{envelope.reasons.map((r) => t[`env_${r}` as 'env_pea_eligible']).filter(Boolean).join(' ')}
                {envelope.withholding && envelope.withholding.default > 0 && <span className="muted"> {t.whNote.replace('{d}', String(envelope.withholding.default))
                  .replace('{t}', String(envelope.withholding.treaty)).replace('{r}', String(envelope.withholding.reclaimable)).replace('{f}', envelope.withholding.form ?? '–')}</span>}</span>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button className={rel?.signal && a.score >= 15 ? 'btn-primary' : 'btn'} onClick={() => onOrder('buy')}>{t.prepareBuy}</button>
            {held && <button className="btn" onClick={() => onOrder('reduce')}>{t.prepareReduce}</button>}
            {held && <button className="btn" onClick={() => onOrder('sell')}>{t.prepareSell}</button>}
            <button className="btn" onClick={() => setThesis(!thesis)}><NotebookPen className="w-3.5 h-3.5" />{t.thesisBtn}</button>
          </div>
          {thesis && <ThesisEditor symbol={symbol} price={a.technicals.price as number | undefined} />}
          <div className="text-[11px] muted border-t border-slate-200 dark:border-slate-800 pt-2 space-y-1">
            <p>{t.engineLong} · {new Date(a.generated_at * 1000).toLocaleString(lang)}</p>
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
  const [envelope, setEnvelope] = useState<Envelope | null>(null);
  const [tab, setTab] = useState<Tab>(readTab);
  const choose = (x: Tab) => { setTab(x); try { localStorage.setItem('stockpulse:analysisTab', x); } catch { /* indisponible */ } };

  useEffect(() => {
    const check = () => api.portfolio().then((p) => {
      const line = p.lines.find((l) => l.symbol === symbol);
      setHeld(!!line);
      setWeight(line ? line.weight : null);
    }).catch(() => {});
    check();
    api.envelope(symbol).then(setEnvelope).catch(() => setEnvelope(null));
    return onPortfolioChanged(check);
  }, [symbol]);

  const load = (refresh = false, ai = false) => {
    setLoading(true);
    setError(null);
    api.advice(symbol, lang, refresh, ai)
      .then((a) => { setAdvice(a); onAdvice(a); if (ai && a.ai_view) notifyAiSaved(); })
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
          <DecisionCard a={advice} symbol={symbol} loading={loading} held={held} weight={weight} envelope={envelope}
            onRefresh={() => load(true)} onOrder={setOrder} />
          {error && <p className="text-sm text-rose-500 mt-2">{error}</p>}
        </div>
      </div>

      <div className="card">
        <div className="flex overflow-x-auto border-b border-slate-200 dark:border-slate-800 px-2">
          {TABS.map(([k, Icon]) => (
            <button key={k} onClick={() => choose(k)}
              className={`flex items-center gap-1.5 px-3 py-3 text-sm whitespace-nowrap cursor-pointer border-b-2 -mb-px ${tab === k ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-semibold' : 'border-transparent muted hover:text-slate-900 dark:hover:text-white'}`}>
              <Icon className="w-4 h-4" />{t[`tab_${k}`]}
              {k === 'reliability' && advice?.reliability && <span className={`w-2 h-2 rounded-full ${advice.reliability.signal ? 'bg-emerald-500'
                : advice.reliability.level === 'contrarian' ? 'bg-rose-500' : 'bg-slate-400'}`} />}
            </button>
          ))}
        </div>
        <div className="p-5">
          {!advice && ['company', 'risk', 'reliability', 'ai', 'events'].includes(tab) ? <p className="text-sm muted animate-pulse">{t.analyzing}</p> : (
            <>
              {tab === 'company' && advice && <CompanyTab a={advice} />}
              {tab === 'risk' && advice && <RiskTab a={advice} />}
              {tab === 'reliability' && advice && <ReliabilityTab a={advice} />}
              {tab === 'ai' && advice && <AiTab a={advice} loading={loading} onAi={() => load(true, true)} />}
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
