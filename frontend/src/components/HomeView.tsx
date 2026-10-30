import { useEffect, useMemo, useState } from 'react';
import { Activity, Bell, Briefcase, Flame, Gauge, Sparkles, Star } from 'lucide-react';
import { AlertEvent, api, Favorite, HealthReport, money, onPortfolioChanged, pct, ScreenerRow } from '../services/api';
import { fill } from '../i18n';
import { useI18n } from '../context';
import { useScreener } from '../hooks/useScreener';
import { HealthList } from './HealthPanel';
import { AlertTags, usePortfolio } from './PortfolioView';
import { Sparkline } from './Sparkline';
import { VerdictBadge } from './VerdictBadge';

interface Props {
  health: HealthReport | null;
  onRecheck: () => void;
  checking: boolean;
  onOpen: (symbol: string) => void;
  onNavigate: (view: 'portfolio' | 'leaderboard') => void;
}

function Panel({ icon, title, action, children }: { icon: React.ReactNode; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-4 space-y-3">
      <div className="flex justify-between items-center"><h2 className="font-bold flex items-center gap-2">{icon}{title}</h2>{action}</div>
      {children}
    </div>
  );
}

function Row({ r, value, onOpen }: { r: ScreenerRow; value: React.ReactNode; onOpen: (s: string) => void }) {
  return (
    <button onClick={() => onOpen(r.symbol)} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer text-left">
      <span className="flex-1 min-w-0"><span className="font-mono font-bold text-sm">{r.symbol}</span><span className="block text-[11px] muted truncate">{r.name}</span></span>
      <Sparkline data={r.spark?.slice(-30)} width={60} height={22} />
      <VerdictBadge advice={r.advice} />
      <span className="w-20 text-right text-sm font-semibold">{value}</span>
    </button>
  );
}

export function HomeView({ health, onRecheck, checking, onOpen, onNavigate }: Props) {
  const { t, lang } = useI18n();
  const { rows } = useScreener();
  const [pf] = usePortfolio();
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [reliability, setReliability] = useState<Record<string, { symbols: number; n: number; hit_rate: number | null }>>({});
  useEffect(() => {
    const load = () => {
      api.favorites().then(setFavorites).catch(() => {});
      api.alerts().then((a) => setEvents(a.events)).catch(() => {});
      api.trackRecord().then(setReliability).catch(() => {});
    };
    load();
    const id = setInterval(load, 120000);
    const off = onPortfolioChanged(load);
    return () => { clearInterval(id); off(); };
  }, []);

  const pea = useMemo(() => rows.filter((r) => r.pea && r.price), [rows]);
  const opportunities = useMemo(() => pea.filter((r) => (r.advice?.score ?? 0) >= 15)
    .sort((a, b) => b.advice!.score - a.advice!.score).slice(0, 6), [pea]);
  const movers = useMemo(() => {
    const s = [...pea].sort((a, b) => (b.chg_1d ?? 0) - (a.chg_1d ?? 0));
    return [...s.slice(0, 3), ...s.slice(-3).reverse()];
  }, [pea]);
  const favRows = useMemo(() => favorites.map((f) => rows.find((r) => r.symbol === f.symbol)).filter(Boolean) as ScreenerRow[], [favorites, rows]);
  const alerts = pf?.lines.filter((l) => l.alerts.length) ?? [];
  const up = (v: number) => (v >= 0 ? 'up' : 'down');
  const seeAll = (v: 'portfolio' | 'leaderboard') => <button className="text-xs text-sky-600 dark:text-sky-400 hover:underline cursor-pointer" onClick={() => onNavigate(v)}>{t.seeAll}</button>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
      <Panel icon={<Briefcase className="w-4 h-4 text-sky-500" />} title={t.pfTitle} action={seeAll('portfolio')}>
        {!pf ? <p className="text-sm muted">{t.loading}</p> : !pf.lines.length ? <p className="text-sm muted">{t.pfEmpty}</p> : (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><div className="label">{t.pfTotal}</div><div className="text-2xl font-bold">{money(pf.total, lang)}</div></div>
            <div><div className="label">{t.pfPnl}</div><div className={`text-xl font-bold ${up(pf.pnl)}`}>{money(pf.pnl, lang)} <span className="text-sm">{pct(pf.pnl_percent)}</span></div></div>
            <div><div className="label">{t.pfDay}</div><div className={`font-bold ${up(pf.day_change)}`}>{money(pf.day_change, lang)}</div></div>
            <div><div className="label">{t.pfCeiling}</div><div className="font-bold">{Math.round((pf.deposits / pf.ceiling) * 100)} %</div></div>
          </div>
        )}
      </Panel>

      <Panel icon={<Bell className="w-4 h-4 text-amber-500" />} title={t.homeAlerts}>
        {events.map((e) => (
          <p key={e.key} className="text-sm cursor-pointer text-amber-600 dark:text-amber-400" onClick={() => onOpen(e.symbol)}>
            🔔 {fill(t[`ev_${e.type}` as 'ev_price'], e)}
          </p>
        ))}
        {!alerts.length && !events.length ? <p className="text-sm muted">{t.noAlerts}</p> : (
          <ul className="space-y-2">
            {alerts.map((l) => (
              <li key={l.id} className="flex items-center gap-2 cursor-pointer" onClick={() => onOpen(l.symbol)}>
                <span className="font-mono font-bold text-sm w-20">{l.symbol}</span><AlertTags line={l} />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel icon={<Activity className="w-4 h-4 text-emerald-500" />} title={t.healthTitle}>
        <HealthList report={health} onRecheck={onRecheck} busy={checking} />
      </Panel>

      <Panel icon={<Sparkles className="w-4 h-4 text-sky-500" />} title={t.homeOpportunities} action={seeAll('leaderboard')}>
        {opportunities.map((r) => <Row key={r.symbol} r={r} onOpen={onOpen} value={<span className="up">+{r.advice!.score}</span>} />)}
        {!opportunities.length && <p className="text-sm muted">–</p>}
      </Panel>

      <Panel icon={<Flame className="w-4 h-4 text-rose-500" />} title={t.homeMovers} action={seeAll('leaderboard')}>
        {movers.map((r) => <Row key={r.symbol} r={r} onOpen={onOpen} value={<span className={up(r.chg_1d ?? 0)}>{pct(r.chg_1d)}</span>} />)}
      </Panel>

      <Panel icon={<Gauge className="w-4 h-4 text-violet-500" />} title={t.globalReliability}>
        <p className="text-xs muted">{t.trackRecord}</p>
        <div className="grid grid-cols-3 gap-2 text-center">
          {(['1m', '3m', '6m'] as const).map((h) => {
            const r = reliability[h];
            return (
              <div key={h}>
                <div className={`text-2xl font-bold ${!r?.hit_rate ? 'muted' : r.hit_rate >= 55 ? 'up' : r.hit_rate < 45 ? 'down' : ''}`}>{r?.hit_rate ?? '–'} %</div>
                <div className="text-xs muted">{h === '6m' ? '6 m' : t[`p_${h}` as 'p_1m']} · {r?.symbols ?? 0} val.</div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel icon={<Star className="w-4 h-4 text-amber-400" />} title={t.favorites}>
        {!favRows.length ? <p className="text-sm muted">{t.noFavorites}</p> :
          favRows.map((r) => <Row key={r.symbol} r={r} onOpen={onOpen} value={<span className={up(r.chg_1d ?? 0)}>{pct(r.chg_1d)}</span>} />)}
      </Panel>
    </div>
  );
}
