import { CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';
import { HealthReport } from '../services/api';
import { useI18n } from '../context';

export const HEALTH_COLOR = { ok: 'text-emerald-500', warn: 'text-amber-500', error: 'text-rose-500' };
const ICON = { ok: CheckCircle2, warn: AlertTriangle, error: XCircle };

export function HealthList({ report, onRecheck, busy }: { report: HealthReport | null; onRecheck: () => void; busy: boolean }) {
  const { t, lang } = useI18n();
  if (!report) return <p className="text-sm muted">{t.loading}</p>;
  const Overall = ICON[report.overall];
  return (
    <div className="space-y-3">
      <div className={`flex items-center gap-2 font-bold ${HEALTH_COLOR[report.overall]}`}>
        <Overall className="w-5 h-5" />{t[`health_${report.overall}`]}
      </div>
      <ul className="space-y-1.5">
        {report.checks.map((c) => {
          const Icon = ICON[c.status];
          return (
            <li key={c.id} className="flex gap-2 text-sm">
              <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${HEALTH_COLOR[c.status]}`} />
              <span><b>{t[`hc_${c.id}` as 'hc_quotes'] ?? c.id}</b> <span className="muted">— {c.detail}</span></span>
            </li>
          );
        })}
      </ul>
      <div className="flex justify-between items-center text-xs muted">
        <span>v{report.version} · {new Date(report.checked_at * 1000).toLocaleTimeString(lang)}</span>
        <button className="btn" onClick={onRecheck} disabled={busy}><RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} />{t.recheck}</button>
      </div>
    </div>
  );
}
