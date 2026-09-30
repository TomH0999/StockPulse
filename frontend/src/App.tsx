import React, { useState } from 'react';
import { DashboardView } from './components/DashboardView';
import { PortfolioManager } from './components/PortfolioManager';
import { BarChart3, Briefcase, Activity } from 'lucide-react';

// Dictionnaire de traduction pour l'en-tête, les onglets et le pied de page
const translations = {
  en: {
    subtitle: "Professional Desktop Market Intelligence",
    dashboardTab: "Market Dashboard",
    portfoliosTab: "Portfolios",
    footerText: "StockPulse Desktop Application • Real-time data powered by Yahoo Finance • 100% Production Ready"
  },
  fr: {
    subtitle: "Intelligence de marché de bureau professionnelle",
    dashboardTab: "Tableau de bord du marché",
    portfoliosTab: "Portefeuilles",
    footerText: "Application de bureau StockPulse • Données en temps réel propulsées par Yahoo Finance • 100% Prêt pour la production"
  },
  es: {
    subtitle: "Inteligencia de mercado de escritorio profesional",
    dashboardTab: "Panel de Mercado",
    portfoliosTab: "Carteras",
    footerText: "Aplicación de escritorio StockPulse • Datos en tiempo real proporcionados por Yahoo Finance • 100% Listo para producción"
  },
  zh: {
    subtitle: "专业桌面市场情报系统",
    dashboardTab: "市场仪表盘",
    portfoliosTab: "投资组合",
    footerText: "StockPulse 桌面应用程序 • 实时数据由 Yahoo Finance 提供驱动 • 100% 生产就绪"
  }
};

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'portfolios'>('dashboard');
  
  // États globaux demandés : Langue et Mode Sombre/Clair
  const [lang, setLang] = useState<'en' | 'fr' | 'es' | 'zh'>('en');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

  const t = translations[lang];

  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${
      isDarkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
    }`}>
      {/* Top Navigation Bar */}
      <header className={`border-b px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4 transition-colors ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-600 rounded-xl text-white shadow-lg shadow-sky-600/20">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">StockPulse</h1>
            <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              {t.subtitle}
            </p>
          </div>
        </div>

        {/* Navigation & Contrôles Globaux (Langue + Mode Sombre/Clair) */}
        <div className="flex items-center gap-3 flex-wrap justify-center">
          <nav className="flex gap-2">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition cursor-pointer ${
                activeTab === 'dashboard' 
                  ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/20' 
                  : isDarkMode ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              {t.dashboardTab}
            </button>
            <button 
              onClick={() => setActiveTab('portfolios')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition cursor-pointer ${
                activeTab === 'portfolios' 
                  ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/20' 
                  : isDarkMode ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Briefcase className="w-4 h-4" />
              {t.portfoliosTab}
            </button>
          </nav>

          <div className="flex items-center gap-2 pl-2 border-l border-slate-700/50">
            {/* Sélecteur de langue global (4 langues) */}
            <select 
              value={lang}
              onChange={(e) => setLang(e.target.value as any)}
              className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border cursor-pointer focus:outline-none ${
                isDarkMode 
                  ? 'bg-slate-950 border-slate-800 text-white' 
                  : 'bg-slate-100 border-slate-300 text-slate-800'
              }`}
            >
              <option value="en">🇺🇸 English</option>
              <option value="fr">🇫🇷 Français</option>
              <option value="es">🇪🇸 Español</option>
              <option value="zh">🇨🇳 中文</option>
            </select>

            {/* Bouton Mode Clair / Sombre avec Icône */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`p-2 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center justify-center ${
                isDarkMode 
                  ? 'bg-slate-950 border-slate-800 text-amber-400 hover:border-slate-700' 
                  : 'bg-slate-100 border-slate-300 text-amber-600 hover:bg-slate-200'
              }`}
              title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content View (Transmet les états globaux isDarkMode et lang aux enfants) */}
      <main className="flex-grow p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'dashboard' ? (
          <DashboardView isDarkMode={isDarkMode} lang={lang} />
        ) : (
          <PortfolioManager isDarkMode={isDarkMode} lang={lang} />
        )}
      </main>

      {/* Footer */}
      <footer className={`py-3 px-6 text-center text-xs border-t transition-colors ${
        isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-500' : 'bg-white border-slate-200 text-slate-500'
      }`}>
        {t.footerText}
      </footer>
    </div>
  );
}

export default App;