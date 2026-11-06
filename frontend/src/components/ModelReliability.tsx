import { useEffect, useState } from 'react';
import { api, ModelValidation } from '../services/api';
import { useI18n, VERDICT_LABEL } from '../context';

const COLOR = { positive: 'border-emerald-500/50 bg-emerald-500/5', negative: 'border-rose-500/50 bg-rose-500/5',
  inconclusive: 'border-slate-400/50 bg-slate-500/5', unknown: 'border-slate-400/50 bg-slate-500/5' };
const DOT = { positive: 'bg-emerald-500', negative: 'bg-rose-500', inconclusive: 'bg-slate-400', unknown: 'bg-slate-400' };
const fmt = (v: number | null | undefined, d = 2) => (v === null || v === undefined ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(d)}`);

let cache: Promise<Awaited<ReturnType<typeof api.modelValidation>>> | null = null;
export const loadModelValidation = () => (cache ??= api.modelValidation().catch((e) => { cache = null; throw e; }));

/** Fiabilité du modèle mesurée en coupe transversale : un seul chiffre pour tout le modèle, avec son intervalle de confiance. */
export function ModelReliability({ compact = false }: { compact?: boolean }) {
  const { t, lang } = useI18n();
  const [d, setD] = useState<Awaited<ReturnType<typeof api.modelValidation>> | null>(null);
  useEffect(() => { loadModelValidation().then(setD).catch(() => {}); }, []);
  const m: ModelValidation | null | undefined = d?.model;
  if (!m) return <p className="text-sm muted">{t.mvNone}</p>;
  const st = m.status ?? 'unknown';
  const ci = (x: ModelValidation['ic']) => (x ? `${fmt(x.mean)} [${fmt(x.low)} ; ${fmt(x.high)}]` : '–');
  const pts = (x: ModelValidation['ic']) => (x ? `${fmt(x.mean, 1)} pts [${fmt(x.low, 1)} ; ${fmt(x.high, 1)}]` : '–');
  return (
    <div className={`rounded-lg border p-3 space-y-2 text-sm ${COLOR[st]}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`w-2.5 h-2.5 rounded-full ${DOT[st]}`} />
        <b>{t[`mv_${st}`]}</b>
        <span className="muted text-xs">IC {ci(m.ic)} · {m.universe} {t.mvStocks} · {m.months} {t.mvMonths} · {m.ic?.independent} {t.mvIndependent}</span>
      </div>
      <p className="text-xs">{t[`mv_${st}_long`]}</p>
      {!compact && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs">
            <span>{t.mvSpread} : <b>{pts(m.quintile_spread)}</b></span>
            <span>{t.mvTopUniverse} : <b>{pts(m.top_vs_universe)}</b></span>
            <span>{t.mvTopStoxx} : <b>{pts(m.top_vs_stoxx600)}</b></span>
            <span>{t.mvTopWorld} : <b>{pts(m.top_vs_world)}</b></span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="muted text-right"><th className="text-left">{t.mvComponent}</th><th>IC</th><th>{t.mvInterval}</th></tr></thead>
              <tbody>
                {Object.entries(m.components).map(([k, v]) => v && (
                  <tr key={k} className="border-t border-slate-200 dark:border-slate-800 text-right">
                    <td className="text-left py-0.5">{t[`grp_${k}` as 'grp_valuation'] ?? k}</td>
                    <td className={v.mean >= 0 ? 'up' : 'down'}>{fmt(v.mean)}</td><td className="muted">[{fmt(v.low)} ; {fmt(v.high)}]</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="muted text-right"><th className="text-left">{t.mvVerdict}</th><th>{t.btSamples}</th><th>{t.mvExcessUniverse}</th><th>{t.mvBeat}</th></tr></thead>
              <tbody>
                {(['STRONG_BUY', 'BUY', 'HOLD', 'REDUCE', 'SELL'] as const).map((v) => m.by_verdict[v] && (
                  <tr key={v} className="border-t border-slate-200 dark:border-slate-800 text-right">
                    <td className="text-left py-0.5">{VERDICT_LABEL[lang]?.[v] ?? v}</td><td>{m.by_verdict[v].n}</td>
                    <td className={m.by_verdict[v].excess_vs_universe >= 0 ? 'up' : 'down'}>{fmt(m.by_verdict[v].excess_vs_universe, 1)} pts</td>
                    <td>{m.by_verdict[v].beat_share} %</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] muted">{t.mvMethod} {m.computed_at ? `· ${new Date(m.computed_at * 1000).toLocaleDateString(lang)}` : ''}</p>
          {d?.ai && <p className="text-[11px] muted">{d.ai.n >= 30 && d.ai.brier !== null
            ? t.mvAiBrier.replace('{b}', d.ai.brier.toFixed(3)).replace('{n}', String(d.ai.n)).replace('{s}', String(d.ai_shrink))
            : t.mvAiPending.replace('{n}', String(d.ai.n))}</p>}
        </>
      )}
    </div>
  );
}
