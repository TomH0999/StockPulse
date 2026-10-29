import { useEffect, useMemo, useState } from 'react';
import { Activity, Moon, Settings, Sun } from 'lucide-react';
import { DashboardView } from './components/DashboardView';
import { SettingsModal } from './components/SettingsModal';
import { I18nContext } from './context';
import { translations } from './i18n';
import type { Lang } from './services/api';

const read = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* stockage indisponible */ } };

export function App() {
  const [lang, setLang] = useState<Lang>(() => read('stockpulse:lang', 'fr') as Lang);
  const [dark, setDark] = useState(() => read('stockpulse:theme', 'dark') === 'dark');
  const [showSettings, setShowSettings] = useState(false);
  const [settingsVersion, setSettingsVersion] = useState(0);
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
          <div className="flex items-center gap-2">
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
          <DashboardView settingsVersion={settingsVersion} />
        </main>

        <footer className="py-3 px-6 text-center text-xs muted border-t border-slate-200 dark:border-slate-800">{t.footer}</footer>
      </div>
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} lang={lang} setLang={setLang} dark={dark} setDark={setDark}
          onSaved={() => setSettingsVersion((v) => v + 1)} />
      )}
    </I18nContext.Provider>
  );
}

export default App;
