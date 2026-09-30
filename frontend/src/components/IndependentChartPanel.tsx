import React, { useState, useEffect } from 'react';
import { marketApi, HistoryPoint } from '../services/api';
import { StockChart } from './StockChart';

interface IndependentChartPanelProps {
    symbol: string;
    highlightDate?: string | null;
    isDarkMode: boolean;
    lang: 'en' | 'fr' | 'es' | 'zh';
}

const translations = {
    en: {
        title: "Price Action",
        targetedArticle: "Targeted Article:",
        errorLoading: "Unable to load price history."
    },
    fr: {
        title: "Action sur les prix",
        targetedArticle: "Article ciblé :",
        errorLoading: "Impossible de charger l'historique."
    },
    es: {
        title: "Acción de precios",
        targetedArticle: "Artículo seleccionado:",
        errorLoading: "No se pudo cargar el historial."
    },
    zh: {
        title: "价格走势",
        targetedArticle: "目标文章：",
        errorLoading: "无法加载历史价格。"
    }
};

export function IndependentChartPanel({ symbol, highlightDate, isDarkMode, lang }: IndependentChartPanelProps) {
    const [period, setPeriod] = useState<string>('1y');
    const [history, setHistory] = useState<HistoryPoint[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const t = translations[lang];

    useEffect(() => {
        let isMounted = true;
        const fetchHistory = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await marketApi.getHistory(symbol, period);
                if (isMounted) {
                    setHistory(data.data || []);
                }
            } catch (err) {
                console.error("Erreur graphique :", err);
                if (isMounted) setError(t.errorLoading);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchHistory();
        return () => { isMounted = false; };
    }, [symbol, period, t.errorLoading]);

    return (
        <div className={`p-6 rounded-xl shadow-lg space-y-4 border transition-colors duration-200 ${
            isDarkMode 
                ? 'bg-slate-900/60 border-slate-800/80 text-white' 
                : 'bg-white border-slate-200 text-slate-900 shadow-xl'
        }`}>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                        {symbol} - {t.title}
                    </h2>
                    {highlightDate && (
                        <p className={`text-xs mt-1 flex items-center gap-1 font-mono ${isDarkMode ? 'text-amber-400' : 'text-amber-600'}`}>
                            🎯 {t.targetedArticle} {highlightDate}
                        </p>
                    )}
                </div>

                <div className={`flex gap-1 p-1 rounded-lg border ${
                    isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-300'
                }`}>
                    {['1w', '1mo', '3mo', '1y'].map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                                period === p 
                                    ? 'bg-blue-600 text-white shadow' 
                                    : isDarkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'
                            }`}
                        >
                            {p.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-[400px] w-full relative">
                {loading && (
                    <div className={`absolute inset-0 z-10 rounded-xl flex items-center justify-center backdrop-blur-sm ${
                        isDarkMode ? 'bg-slate-900/50' : 'bg-white/50'
                    }`}>
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
                    </div>
                )}
                
                {error ? (
                    <div className="flex h-full items-center justify-center text-red-500 text-sm">
                        {error}
                    </div>
                ) : (
                    <StockChart data={history} symbol={symbol} highlightDate={highlightDate} isDarkMode={isDarkMode} />
                )}
            </div>
        </div>
    );
}

export default IndependentChartPanel;