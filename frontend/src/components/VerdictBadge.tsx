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
