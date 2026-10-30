import { useEffect, useState } from 'react';
import { Briefcase } from 'lucide-react';
import { api, money, onPortfolioChanged, pct, Portfolio, PortfolioLine } from '../services/api';
import { fill } from '../i18n';
import { emptyMove, JournalPanel, MoveForm } from './JournalPanel';
import { PerformancePanel } from './PerformancePanel';
import { ObjectivesPanel } from './ObjectivesPanel';
import { useI18n } from '../context';
import { VerdictBadge } from './VerdictBadge';
import { PortfolioAnalysisPanel } from './PortfolioAnalysisPanel';

export function usePortfolio() {
  const [data, setData] = useState<Portfolio | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.portfolio().then((d) => alive && setData(d)).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    const off = onPortfolioChanged(load);
    return () => { alive = false; clearInterval(id); off(); };
  }, []);
  return [data, setData] as const;
}

export function AlertTags({ line }: { line: PortfolioLine }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-1">
      {line.alerts.map((a) => (
        <span key={a} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold whitespace-nowrap">
          {t[`alert_${a}` as 'alert_big_drop'] ?? a}
        </span>
      ))}
    </div>
  );
}

export function PortfolioView({ onOpen }: { onOpen: (symbol: string) => void }) {
  const { t, lang } = useI18n();
  const [data] = usePortfolio();
  const [tab, setTab] = useState<'overview' | 'performance' | 'journal' | 'objectives'>('overview');
  const [form, setForm] = useState<MoveForm>(emptyMove());
  const trade = (type: 'buy' | 'sell', l: PortfolioLine) => {
    setForm({ ...emptyMove(type, l.symbol), quantity: type === 'sell' ? String(l.quantity) : '' });
    setTab('journal');
  };

  const up = (v: number) => (v >= 0 ? 'up' : 'down');
  const card = (label: string, value: React.ReactNode, sub?: React.ReactNode) => (
    <div className="card p-4"><div className="label">{label}</div><div className="text-xl font-bold">{value}</div>{sub && <div className="text-xs mt-1">{sub}</div>}</div>
  );
  const th = 'px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400';
  const TABS = [['overview', t.tabOverview], ['performance', t.tabPerformance], ['journal', t.tabJournal], ['objectives', t.tabObjectives]] as const;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Briefcase className="w-6 h-6 text-sky-500" />{t.pfTitle}</h1>
        <div className="flex gap-1 p-1 rounded-lg border border-slate-200 dark:border-slate-800">
          {TABS.map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)} className={`px-3 py-1.5 text-sm rounded-md cursor-pointer ${tab === k ? 'bg-sky-600 text-white' : 'muted hover:text-sky-500'}`}>{label}</button>
          ))}
        </div>
      </div>
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {card(t.pfTotal, money(data.total, lang), data.performance !== null && <span className={up(data.gain)}>{money(data.gain, lang)} ({pct(data.performance)})</span>)}
          {card(t.pfValue, money(data.value, lang), <span className={up(data.day_change)}>{t.pfDay} : {money(data.day_change, lang)}</span>)}
          {card(t.pfCash, money(data.cash, lang), <span className="muted">{t.pfCashAuto}</span>)}
          {card(t.pfPnl, <span className={up(data.pnl)}>{money(data.pnl, lang)}</span>, <span className={up(data.pnl)}>{pct(data.pnl_percent)}</span>)}
          {card(t.pfRealized, <span className={up(data.realized)}>{money(data.realized, lang)}</span>, <span className="muted">{t.pfDividends} : {money(data.dividends, lang)}</span>)}
          {card(t.pfCeiling, `${money(data.deposits, lang)}`,
            <><span className="muted">{t.pfCeilingLeft} : {money(data.ceiling_left, lang)}</span>
              <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 mt-1"><div className="h-full rounded-full bg-sky-600" style={{ width: `${Math.min(100, (data.deposits / data.ceiling) * 100)}%` }} /></div></>)}
          {card(t.fiveYears, data.opened ? (data.mature ? '✓' : new Date(data.five_years!).toLocaleDateString(lang)) : '–',
            data.opened ? <span className="muted">{data.mature ? t.fiveYearsDone : fill(t.fiveYearsLeft, { d: data.days_to_five_years })}
              {data.tax_if_withdrawn !== null && <><br />{t.taxIfWithdrawn} : {money(data.tax_if_withdrawn, lang)}</>}</span>
              : <button className="text-sky-600 dark:text-sky-400 hover:underline cursor-pointer" onClick={() => setTab('objectives')}>{t.objOpened} →</button>)}
        </div>
      )}

      {tab === 'overview' && (
        <>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800">
                  <th className={`${th} text-left`}>{t.col_name}</th><th className={`${th} text-right`}>{t.pfQty}</th>
                  <th className={`${th} text-right`}>{t.pfPruAuto}</th><th className={`${th} text-right`}>{t.col_price}</th>
                  <th className={`${th} text-right`}>{t.pfValue}</th><th className={`${th} text-right`}>{t.pfPnl}</th>
                  <th className={`${th} text-right`}>{t.pfRealized}</th><th className={`${th} text-right`}>{t.pfWeight}</th>
                  <th className={`${th} text-right`}>{t.col_advice}</th><th className={`${th} text-left`}>{t.pfAlerts}</th><th />
                </tr>
              </thead>
              <tbody>
                {!data?.lines.length && <tr><td colSpan={11} className="px-3 py-4 muted">{data ? t.pfEmpty : t.loading}</td></tr>}
                {data?.lines.map((l) => (
                  <tr key={l.id} className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-3 py-2 cursor-pointer" onClick={() => onOpen(l.symbol)}>
                      <div className="font-mono font-bold">{l.symbol}</div><div className="text-xs muted truncate max-w-[200px]">{l.name} · {t.pfSince} {new Date(l.since).toLocaleDateString(lang)}</div>
                    </td>
                    <td className="px-3 py-2 text-right">{l.quantity}</td>
                    <td className="px-3 py-2 text-right">{l.avg_price.toFixed(2)} €</td>
                    <td className="px-3 py-2 text-right">{l.price.toFixed(2)}{l.currency !== 'EUR' && <span className="muted text-xs"> {l.currency}</span>} <span className={`text-xs ${up(l.change_percent ?? 0)}`}>{pct(l.change_percent)}</span></td>
                    <td className="px-3 py-2 text-right">{money(l.value, lang)}</td>
                    <td className={`px-3 py-2 text-right ${up(l.pnl)}`}>{money(l.pnl, lang)}<div className="text-xs">{pct(l.pnl_percent)}</div></td>
                    <td className={`px-3 py-2 text-right ${up(l.realized)}`}>{l.realized ? money(l.realized, lang) : '–'}</td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">{l.weight !== null ? `${l.weight} %` : '–'}</td>
                    <td className="px-3 py-2 text-right"><VerdictBadge advice={l.advice} /></td>
                    <td className="px-3 py-2"><AlertTags line={l} /></td>
                    <td className="px-3 py-2 whitespace-nowrap text-right space-x-1">
                      <button className="btn !px-2 !py-1" onClick={() => trade('buy', l)}>{t.side_buy}</button>
                      <button className="btn !px-2 !py-1" onClick={() => trade('sell', l)}>{t.side_sell}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PortfolioAnalysisPanel version={0} onOpen={onOpen} />
        </>
      )}
      {tab === 'performance' && <PerformancePanel />}
      {tab === 'journal' && <JournalPanel form={form} setForm={setForm} />}
      {tab === 'objectives' && <ObjectivesPanel portfolio={data} />}
    </div>
  );
}
