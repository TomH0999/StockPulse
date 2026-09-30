import React, { useState, useEffect, useCallback } from 'react';
import { usePolling } from '../hooks/usePolling';
import { marketApi, Quote } from '../services/api';
import { StockSearchSelector } from '../components/StockSearchSelector';
import { IndependentChartPanel } from '../components/IndependentChartPanel';
import { IndependentNewsPanel } from '../components/IndependentNewsPanel';

interface DashboardViewProps {
    isDarkMode: boolean;
    lang: 'en' | 'fr' | 'es' | 'zh';
}

export function DashboardView({ isDarkMode, lang }: DashboardViewProps) {
    const [symbol, setSymbol] = useState<string>('AAPL');
    const [highlightDate, setHighlightDate] = useState<string | null>(null);
    const [quote, setQuote] = useState<Quote | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [lastSynced, setLastSynced] = useState<string>('');

    const fetchQuoteData = useCallback(async (isBackground = false) => {
        try {
            if (!isBackground) setLoading(true);
            const quoteData = await marketApi.getQuote(symbol);
            setQuote(quoteData);
            setLastSynced(new Date().toLocaleTimeString());
        } catch (err) {
            console.error("Erreur de récupération du cours :", err);
        } finally {
            if (!isBackground) setLoading(false);
        }
    }, [symbol]);

    useEffect(() => {
        fetchQuoteData(false);
        setHighlightDate(null); // Réinitialise le highlight au changement d'action
    }, [symbol, fetchQuoteData]);

    useEffect(() => {
        const interval = setInterval(() => {
            fetchQuoteData(true);
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchQuoteData]);

    return (
        <div className={`p-6 space-y-6 max-w-7xl mx-auto transition-colors ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>
            {/* Barre de recherche et Titre */}
            <div className={`flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-4 rounded-xl border transition-colors ${
                isDarkMode ? 'bg-slate-900/40 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
            }`}>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Market Intelligence & Quotes</h1>
                    <p className={`text-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {lang === 'fr' ? "Suivi financier en temps réel et croisement historique des actualités." :
                         lang === 'es' ? "Seguimiento financiero en tiempo real y cruce histórico de noticias." :
                         lang === 'zh' ? "实时金融监控与历史新闻交叉分析。" :
                         "Real-time financial tracking and historical news cross-referencing."}
                    </p>
                </div>

                <div className="w-full md:w-auto">
                    <StockSearchSelector onSelectStock={(selectedSymbol) => setSymbol(selectedSymbol)} />
                </div>
            </div>

            {/* Cartes KPI */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`p-5 rounded-xl border shadow-md transition-colors ${
                    isDarkMode ? 'bg-slate-900/60 border-slate-800/80' : 'bg-white border-slate-200'
                }`}>
                    <span className={`text-xs font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {lang === 'fr' ? "Cours Actuel" : lang === 'es' ? "Precio Actual" : lang === 'zh' ? "当前价格" : "Current Price"}
                    </span>
                    <div className="mt-2 flex items-baseline gap-2">
                        <span className={`text-3xl font-extrabold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                            ${quote?.price?.toFixed(2) ?? '0.00'}
                        </span>
                    </div>
                    {quote && (
                        <div className={`mt-2 inline-flex items-center text-xs font-bold px-2 py-0.5 rounded ${quote.change >= 0 ? 'text-emerald-400 bg-emerald-950/40' : 'text-rose-400 bg-rose-950/40'}`}>
                            {quote.change >= 0 ? '+' : ''}{quote.change} ({quote.change_percent}%)
                        </div>
                    )}
                </div>

                <div className={`p-5 rounded-xl border shadow-md transition-colors ${
                    isDarkMode ? 'bg-slate-900/60 border-slate-800/80' : 'bg-white border-slate-200'
                }`}>
                    <span className={`text-xs font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {lang === 'fr' ? "Volume d'échange" : lang === 'es' ? "Volumen de negociación" : lang === 'zh' ? "交易量" : "Volume"}
                    </span>
                    <div className={`mt-2 text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                        {quote?.volume ? quote.volume.toLocaleString() : 'N/A'}
                    </div>
                    <span className={`text-xs mt-2 block ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                        {lang === 'fr' ? "Volume journalier" : lang === 'es' ? "Volumen diario" : lang === 'zh' ? "日交易量" : "Daily volume"}
                    </span>
                </div>

                <div className={`p-5 rounded-xl border shadow-md transition-colors ${
                    isDarkMode ? 'bg-slate-900/60 border-slate-800/80' : 'bg-white border-slate-200'
                }`}>
                    <span className={`text-xs font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {lang === 'fr' ? "Capitalisation Boursière" : lang === 'es' ? "Capitalización de mercado" : lang === 'zh' ? "市值" : "Market Cap"}
                    </span>
                    <div className={`mt-2 text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                        {quote?.market_cap ? `$${(quote.market_cap / 1e9).toFixed(2)}B` : 'N/A'}
                    </div>
                    <span className={`text-xs mt-2 block ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                        {lang === 'fr' ? "Valeur globale estimée" : lang === 'es' ? "Valor global estimado" : lang === 'zh' ? "估计总价值" : "Estimated total value"}
                    </span>
                </div>

                <div className={`p-5 rounded-xl border shadow-md relative overflow-hidden transition-colors ${
                    isDarkMode ? 'bg-slate-900/60 border-slate-800/80' : 'bg-white border-slate-200'
                }`}>
                    <div className="absolute top-3 right-3 flex items-center gap-1.5">
                        <span className="relative flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                        </span>
                        <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">Live</span>
                    </div>
                    <span className={`text-xs font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {lang === 'fr' ? "Dernière synchro" : lang === 'es' ? "Última sincronización" : lang === 'zh' ? "最后同步" : "Last synced"}
                    </span>
                    <div className={`mt-2 text-xl font-mono font-semibold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                        {lastSynced || '--:--:--'}
                    </div>
                    <span className={`text-xs mt-2 block ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                        {lang === 'fr' ? "Mise à jour auto (5s)" : lang === 'es' ? "Actualización automática (5s)" : lang === 'zh' ? "自动更新 (5s)" : "Auto update (5s)"}
                    </span>
                </div>
            </div>

            {/* Graphique indépendant */}
            <IndependentChartPanel 
                symbol={symbol} 
                highlightDate={highlightDate} 
                isDarkMode={isDarkMode}
                lang={lang}
            />

            {/* Panneau d'actualités unifié */}
            <IndependentNewsPanel 
                symbol={symbol} 
                isDarkMode={isDarkMode}
                lang={lang}
                onHighlightDate={(dateStr) => setHighlightDate(dateStr)} 
            />
        </div>
    );
}

export default DashboardView;