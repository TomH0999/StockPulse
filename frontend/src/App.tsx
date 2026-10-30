import { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, Briefcase, Building2, LayoutDashboard, Moon, Settings, Sun, Trophy } from 'lucide-react';
import { DashboardView } from './components/DashboardView';
import { SettingsModal } from './components/SettingsModal';
import { LeaderboardView } from './components/LeaderboardView';
import { CatalogView } from './components/CatalogView';
import { HomeView } from './components/HomeView';
import { PortfolioView } from './components/PortfolioView';
import { HEALTH_COLOR, HealthList } from './components/HealthPanel';
import { api, HealthReport } from './services/api';
import { I18nContext } from './context';
import { translations } from './i18n';
import type { Lang } from './services/api';
import { X } from 'lucide-react';

const read = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* stockage indisponible */ } };

type View = 'home' | 'analysis' | 'leaderboard' | 'companies' | 'portfolio';
const NAV: [View, typeof BarChart3][] = [['home', LayoutDashboard], ['analysis', BarChart3], ['leaderboard', Trophy], ['companies', Building2], ['portfolio', Briefcase]];

export function App() {
  const [lang, setLang] = useState<Lang>(() => read('stockpulse:lang', 'fr') as Lang);
  const [dark, setDark] = useState(() => read('stockpulse:theme', 'dark') === 'dark');
  const [showSettings, setShowSettings] = useState(false);
  const [settingsVersion, setSettingsVersion] = useState(0);
  const [view, setView] = useState<View>('home');
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [checking, setChecking] = useState(false);
  const [showHealth, setShowHealth] = useState(false);

  // Vérificateur d'état : résumé au lancement (fermé automatiquement si tout va bien), puis contrôle toutes les 5 min
  const checkHealth = (refresh = false) => {
    setChecking(true);
    return api.health(refresh).then((r) => { setHealth(r); return r; }).finally(() => setChecking(false));
  };
  useEffect(() => {
    checkHealth(true).then((r) => {
      setShowHealth(true);
      if (r.overall !== 'error') setTimeout(() => setShowHealth(false), r.overall === 'ok' ? 5000 : 12000);  // reste ouvert seulement en cas de problème
    }).catch(() => setShowHealth(true));
    const id = setInterval(() => checkHealth().catch(() => {}), 300000);
    return () => clearInterval(id);
  }, []);
  const [symbol, setSymbol] = useState(() => read('stockpulse:lastSymbol', 'AAPL'));
  const open = (s: string) => { setSymbol(s); write('stockpulse:lastSymbol', s); setView('analysis'); window.scrollTo({ top: 0 }); };
  const t = translations[lang];
  const ctx = useMemo(() => ({ lang, t }), [lang, t]);

  useEffect(() => { write('stockpulse:lang', lang); document.documentElement.lang = lang; }, [lang]);
  useEffect(() => { write('stockpulse:theme', dark ? 'dark' : 'light'); document.documentElement.classList.toggle('dark', dark); }, [dark]);

  return (
    <I18nContext.Provider value={ctx}>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-3 flex justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-sky-600 rounded-xl text-white"><Activity className="w-5 h-5" /></div>
            <div>
              <h1 className="text-lg font-bold leading-tight">StockPulse</h1>
              <p className="text-xs muted">{t.subtitle}</p>
            </div>
          </div>
          <nav className="flex gap-1">
            {NAV.map(([v, Icon]) => (
              <button key={v} onClick={() => setView(v)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium cursor-pointer ${view === v ? 'bg-sky-600 text-white' : 'muted hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                <Icon className="w-4 h-4" /><span className="hidden md:inline">{t[`nav_${v}`]}</span>
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <button className="btn !p-2" onClick={() => setShowHealth(true)} title={t.healthTitle} aria-label={t.healthTitle}>
              <Activity className={`w-4 h-4 ${health ? HEALTH_COLOR[health.overall] : 'muted'}`} />
            </button>
            <select className="input !w-auto !py-1.5 text-xs" value={lang} onChange={(e) => setLang(e.target.value as Lang)} aria-label={t.language}>
              <option value="fr">🇫🇷 FR</option><option value="en">🇬🇧 EN</option><option value="es">🇪🇸 ES</option><option value="zh">🇨🇳 中文</option>
            </select>
            <button className="btn !p-2" onClick={() => setDark(!dark)} aria-label={t.theme}>
              {dark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>
            <button className="btn !p-2" onClick={() => setShowSettings(true)} aria-label={t.settings} title={t.settings}>
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </header>

        <main className="flex-grow p-4 md:p-6 max-w-[1500px] mx-auto w-full">
          {view === 'home' && <HomeView health={health} onRecheck={() => checkHealth(true)} checking={checking} onOpen={open} onNavigate={setView} />}
          {view === 'portfolio' && <PortfolioView onOpen={open} />}
          {view === 'analysis' && <DashboardView symbol={symbol} onSelect={open} settingsVersion={settingsVersion} />}
          {view === 'leaderboard' && <LeaderboardView onOpen={open} />}
          {view === 'companies' && <CatalogView onOpen={open} />}
        </main>

        <footer className="py-3 px-6 text-center text-xs muted border-t border-slate-200 dark:border-slate-800">{t.footer}</footer>
      </div>
      {showHealth && (
        <div className="fixed top-16 right-4 z-40 card !bg-white dark:!bg-slate-900 shadow-2xl p-4 w-[380px] max-w-[calc(100vw-2rem)]">
          <div className="flex justify-between items-center mb-2">
            <h2 className="font-bold">{t.healthTitle}</h2>
            <button onClick={() => setShowHealth(false)} className="muted hover:text-rose-500 cursor-pointer"><X className="w-4 h-4" /></button>
          </div>
          <HealthList report={health} onRecheck={() => checkHealth(true)} busy={checking} />
        </div>
      )}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} lang={lang} setLang={setLang} dark={dark} setDark={setDark}
          onSaved={() => setSettingsVersion((v) => v + 1)} />
      )}
    </I18nContext.Provider>
  );
}

export default App;
