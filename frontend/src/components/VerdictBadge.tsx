import { AdviceSummary } from '../services/api';
import { useI18n, VERDICT_LABEL, VERDICT_STYLE } from '../context';

export function VerdictBadge({ advice }: { advice: AdviceSummary | null | undefined }) {
  const { lang } = useI18n();
  if (!advice) return <span className="text-[10px] muted">–</span>;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold whitespace-nowrap ${VERDICT_STYLE[advice.verdict]}`}
      title={`${advice.score > 0 ? '+' : ''}${advice.score}/100 · ${advice.engine}`}>
      {VERDICT_LABEL[lang][advice.verdict]}{advice.engine !== 'local' && ' ✦'}
    </span>
  );
}

export function StatusBadge({ status, isNew }: { status?: string | null; isNew?: boolean }) {
  const { t } = useI18n();
  if (status) {
    return <span className={`text-[9px] px-1 rounded font-bold ${status === 'delisted' ? 'bg-rose-600 text-white' : 'bg-amber-500/20 text-amber-600 dark:text-amber-400'}`}
      title={status === 'delisted' ? t.st_delisted_help : undefined}>{t[`st_${status}` as 'st_suspended']}</span>;
  }
  return isNew ? <span className="text-[9px] px-1 rounded font-bold bg-violet-500/20 text-violet-600 dark:text-violet-400">{t.isNew}</span> : null;
}
