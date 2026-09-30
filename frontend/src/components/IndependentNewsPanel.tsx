import React, { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../services/api';

interface NewsItem {
    headline: string;
    summary: string;
    url: string;
    source: string;
    published_at: string;
    sentiment: string;
}

interface IndependentNewsPanelProps {
    symbol: string;
    onHighlightDate?: (dateStr: string) => void;
    isDarkMode: boolean;
    lang: 'en' | 'fr' | 'es' | 'zh';
}

// Dictionnaire de traduction complet (sans les heures)
const translations = {
    en: {
        title: "Historical Articles Database",
        subtitle: "Explore the complete archive page by page with granular filters and chart analysis.",
        filtersBtn: "Calendar Filters & Sort",
        themeLabel: "Theme / Keywords",
        themePlaceholder: "e.g., earnings, AI, CEO...",
        sourceLabel: "Source",
        allSources: "All sources",
        sortByLabel: "Sort by & Order",
        sortDate: "Date & Time",
        sortRelevance: "Relevance",
        sortPopularity: "Popularity",
        calendarLabel: "Granular Calendar (Filter by precise period)",
        allYears: "All years",
        allMonths: "All months",
        allDays: "All days",
        dayLabel: "Day",
        months: [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ],
        noSummary: "No summary available",
        analyzeBtn: "Analyze on chart",
        readLink: "Read →",
        prevBtn: "← Previous",
        nextBtn: "Next →",
        noResults: "No articles match the selected filters or calendar period.",
        articlesFound: "articles found"
    },
    fr: {
        title: "Base d'Articles Historiques",
        subtitle: "Explorez l'archive complète page par page avec filtres granulaires et analyse graphique.",
        filtersBtn: "Filtres Calendrier & Tri",
        themeLabel: "Thème / Mots-clés",
        themePlaceholder: "ex: earnings, AI, CEO...",
        sourceLabel: "Source",
        allSources: "Toutes les sources",
        sortByLabel: "Trier par & Ordre",
        sortDate: "Date & Heure",
        sortRelevance: "Pertinence",
        sortPopularity: "Popularité",
        calendarLabel: "Calendrier Granulaire (Affiner par période précise)",
        allYears: "Toutes les années",
        allMonths: "Tous les mois",
        allDays: "Tous les jours",
        dayLabel: "Jour",
        months: [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ],
        noSummary: "Aucun résumé disponible",
        analyzeBtn: "Analyser sur le graphique",
        readLink: "Lire →",
        prevBtn: "← Précédent",
        nextBtn: "Suivant →",
        noResults: "Aucun article ne correspond aux filtres ou à la période du calendrier sélectionnée.",
        articlesFound: "articles trouvés"
    },
    es: {
        title: "Base de Datos de Artículos Históricos",
        subtitle: "Explore el archivo completo página por página con filtros granulares y análisis de gráficos.",
        filtersBtn: "Filtros de Calendario y Orden",
        themeLabel: "Tema / Palabras clave",
        themePlaceholder: "ej: earnings, IA, CEO...",
        sourceLabel: "Fuente",
        allSources: "Todas las fuentes",
        sortByLabel: "Ordenar por y Orden",
        sortDate: "Fecha y Hora",
        sortRelevance: "Relevancia",
        sortPopularity: "Popularidad",
        calendarLabel: "Calendario Granular (Filtrar por período preciso)",
        allYears: "Todos los años",
        allMonths: "Todos los meses",
        allDays: "Todos los días",
        dayLabel: "Día",
        months: [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ],
        noSummary: "No hay resumen disponible",
        analyzeBtn: "Analizar en gráfico",
        readLink: "Leer →",
        prevBtn: "← Anterior",
        nextBtn: "Siguiente →",
        noResults: "Ningún artículo coincide con los filtros o el período de calendario seleccionado.",
        articlesFound: "artículos encontrados"
    },
    zh: {
        title: "历史文章数据库",
        subtitle: "通过细粒度过滤器和图表分析逐页浏览完整档案。",
        filtersBtn: "日历筛选与排序",
        themeLabel: "主题 / 关键词",
        themePlaceholder: "例如：财报, 人工智能, CEO...",
        sourceLabel: "来源",
        allSources: "所有来源",
        sortByLabel: "排序方式与顺序",
        sortDate: "日期与时间",
        sortRelevance: "相关性",
        sortPopularity: "热度",
        calendarLabel: "细粒度日历（按精确时期筛选）",
        allYears: "所有年份",
        allMonths: "所有月份",
        allDays: "所有天数",
        dayLabel: "日",
        months: [
            "一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"
        ],
        noSummary: "暂无摘要",
        analyzeBtn: "在图表上分析",
        readLink: "阅读 →",
        prevBtn: "← 上一页",
        nextBtn: "下一页 →",
        noResults: "没有文章符合所选的筛选条件或日历时间段。",
        articlesFound: "条文章"
    }
};

export function IndependentNewsPanel({ symbol, onHighlightDate, isDarkMode, lang }: IndependentNewsPanelProps) {
    const [news, setNews] = useState<NewsItem[]>([]);
    const [loading, setLoading] = useState<boolean>(false);

    const t = translations[lang];

    // États des filtres et du tri
    const [showFilters, setShowFilters] = useState<boolean>(false);
    const [themeQuery, setThemeQuery] = useState<string>('');
    const [selectedSource, setSelectedSource] = useState<string>('ALL');

    // Sélecteur de date granulaire (Année, Mois, Jour)
    const [filterYear, setFilterYear] = useState<string>('');
    const [filterMonth, setFilterMonth] = useState<string>('');
    const [filterDay, setFilterDay] = useState<string>('');

    const [sortBy, setSortBy] = useState<'date' | 'relevance' | 'popularity'>('date');
    const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

    // Pagination style Google
    const [currentPage, setCurrentPage] = useState<number>(1);
    const itemsPerPage = 12;

    useEffect(() => {
        let isMounted = true;
        const fetchNewsFromDB = async () => {
            if (!symbol) return;
            setLoading(true);
            try {
                const response = await apiClient.get(`/market/news/${symbol}`);
                if (isMounted) {
                    setNews(response.data || []);
                }
            } catch (err) {
                console.error("Error loading news database:", err);
                if (isMounted) setNews([]);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchNewsFromDB();
        return () => { isMounted = false; };
    }, [symbol]);

    useEffect(() => {
        setCurrentPage(1);
    }, [themeQuery, selectedSource, filterYear, filterMonth, filterDay, sortBy, sortOrder]);

    const availableSources = useMemo(() => {
        return Array.from(new Set(news.map(item => item.source))).sort();
    }, [news]);

    const availableYears = useMemo(() => {
        const years = new Set<string>();
        news.forEach(item => {
            const yearPart = item.published_at.substring(0, 4);
            if (/^\d{4}$/.test(yearPart)) years.add(yearPart);
        });
        return Array.from(years).sort().reverse();
    }, [news]);

    const dateQueryPrefix = useMemo(() => {
        let prefix = filterYear;
        if (filterMonth) prefix += `-${filterMonth}`;
        if (filterMonth && filterDay) prefix += `-${filterDay}`;
        return prefix;
    }, [filterYear, filterMonth, filterDay]);

    const processedNews = useMemo(() => {
        let result = [...news];

        if (selectedSource !== 'ALL') {
            result = result.filter(item => item.source === selectedSource);
        }

        if (dateQueryPrefix.trim()) {
            result = result.filter(item => item.published_at.toLowerCase().includes(dateQueryPrefix.toLowerCase().trim()));
        }

        const queryTerms = themeQuery.toLowerCase().trim().split(/\s+/).filter(Boolean);

        const scoredResults = result.map(item => {
            let relevanceScore = 0;
            const textToSearch = `${item.headline} ${item.summary}`.toLowerCase();

            if (queryTerms.length > 0) {
                let matchedAll = true;
                queryTerms.forEach(term => {
                    if (textToSearch.includes(term)) {
                        relevanceScore += (textToSearch.match(new RegExp(term, 'g')) || []).length;
                    } else {
                        matchedAll = false;
                    }
                });
                if (!matchedAll && queryTerms.length > 1) {
                    relevanceScore = 0;
                }
            } else {
                relevanceScore = 1;
            }

            const majorSources = ['Bloomberg', 'Reuters', 'Wall Street Journal', 'Financial Times', 'Yahoo Finance'];
            const sourceBoost = majorSources.includes(item.source) ? 10 : 3;
            const popularityScore = sourceBoost + Math.min((item.summary || '').length / 20, 15);

            let timestamp = 0;
            try {
                timestamp = new Date(item.published_at.replace(' ', 'T')).getTime();
                if (isNaN(timestamp)) timestamp = 0;
            } catch {
                timestamp = 0;
            }

            return {
                item,
                relevanceScore,
                popularityScore,
                timestamp
            };
        });

        const filteredByTheme = queryTerms.length > 0 
            ? scoredResults.filter(r => r.relevanceScore > 0)
            : scoredResults;

        filteredByTheme.sort((a, b) => {
            let comparison = 0;
            if (sortBy === 'date') {
                comparison = a.timestamp - b.timestamp;
            } else if (sortBy === 'relevance') {
                comparison = a.relevanceScore - b.relevanceScore;
            } else if (sortBy === 'popularity') {
                comparison = a.popularityScore - b.popularityScore;
            }
            if (comparison === 0) {
                comparison = a.item.url.localeCompare(b.item.url);
            }
            return sortOrder === 'desc' ? -comparison : comparison;
        });

        return filteredByTheme.map(r => r.item);
    }, [news, selectedSource, dateQueryPrefix, themeQuery, sortBy, sortOrder]);

    const totalPages = Math.ceil(processedNews.length / itemsPerPage) || 1;
    const paginatedNews = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return processedNews.slice(start, start + itemsPerPage);
    }, [processedNews, currentPage]);

    return (
        <div className={`p-6 rounded-xl shadow-lg space-y-4 border transition-colors duration-200 ${
            isDarkMode 
                ? 'bg-slate-900/60 border-slate-800/80 text-white' 
                : 'bg-white border-slate-200 text-slate-900 shadow-xl'
        }`}>
            {/* Barre supérieure : Titre + Bouton de bascule des filtres */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-lg font-bold flex items-center gap-2">
                        📰 {t.title} ({symbol}) - {processedNews.length} {t.articlesFound}
                    </h2>
                    <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {t.subtitle}
                    </p>
                </div>

                <div className="flex items-center gap-2.5">
                    <button 
                        onClick={() => setShowFilters(!showFilters)}
                        className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5 cursor-pointer ${
                            showFilters 
                                ? 'bg-blue-600 border-blue-500 text-white' 
                                : isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700' : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
                        }`}
                    >
                        ⚙️ {t.filtersBtn} {showFilters ? '▲' : '▼'}
                    </button>
                </div>
            </div>

            {/* Menu des Filtres et Calendrier Granulaire */}
            {showFilters && (
                <div className={`p-4 rounded-xl space-y-4 border transition-colors ${
                    isDarkMode ? 'bg-slate-950/80 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="space-y-1">
                            <label className={`text-[11px] font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                                {t.themeLabel}
                            </label>
                            <input 
                                type="text" 
                                placeholder={t.themePlaceholder} 
                                value={themeQuery}
                                onChange={(e) => setThemeQuery(e.target.value)}
                                className={`w-full px-3 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 border ${
                                    isDarkMode ? 'bg-slate-900 border-slate-800 text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                                }`}
                            />
                        </div>

                        <div className="space-y-1">
                            <label className={`text-[11px] font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                                {t.sourceLabel}
                            </label>
                            <select 
                                value={selectedSource}
                                onChange={(e) => setSelectedSource(e.target.value)}
                                className={`w-full px-3 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 border cursor-pointer ${
                                    isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-300 text-slate-900'
                                }`}
                            >
                                <option value="ALL">{t.allSources} ({news.length})</option>
                                {availableSources.map((src) => (
                                    <option key={src} value={src}>{src}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-1">
                            <label className={`text-[11px] font-semibold uppercase tracking-wider ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                                {t.sortByLabel}
                            </label>
                            <div className="flex gap-2">
                                <select 
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value as any)}
                                    className={`w-full px-2 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 border cursor-pointer ${
                                        isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-300 text-slate-900'
                                    }`}
                                >
                                    <option value="date">{t.sortDate}</option>
                                    <option value="relevance">{t.sortRelevance}</option>
                                    <option value="popularity">{t.sortPopularity}</option>
                                </select>
                                <button
                                    onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold text-blue-400 border transition-colors cursor-pointer ${
                                        isDarkMode ? 'bg-slate-900 border-slate-800 hover:border-slate-700' : 'bg-white border-slate-300 hover:bg-slate-100'
                                    }`}
                                >
                                    {sortOrder === 'desc' ? 'Desc ▼' : 'Asc ▲'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className={`pt-3 border-t ${isDarkMode ? 'border-slate-800/60' : 'border-slate-200'}`}>
                        <label className="text-[11px] font-semibold text-amber-500 uppercase tracking-wider block mb-2">
                            {t.calendarLabel}
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                            {/* Année */}
                            <select 
                                value={filterYear}
                                onChange={(e) => { setFilterYear(e.target.value); if(!e.target.value) { setFilterMonth(''); setFilterDay(''); } }}
                                className={`px-3 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 border cursor-pointer ${
                                    isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-300 text-slate-900'
                                }`}
                            >
                                <option value="">{t.allYears}</option>
                                {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
                            </select>

                            {/* Mois traduits dynamiquement */}
                            <select 
                                value={filterMonth}
                                disabled={!filterYear}
                                onChange={(e) => { setFilterMonth(e.target.value); if(!e.target.value) { setFilterDay(''); } }}
                                className={`px-3 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 disabled:opacity-40 border cursor-pointer ${
                                    isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-300 text-slate-900'
                                }`}
                            >
                                <option value="">{t.allMonths}</option>
                                {t.months.map((mName, index) => {
                                    const mVal = String(index + 1).padStart(2, '0');
                                    return <option key={mVal} value={mVal}>{mName}</option>;
                                })}
                            </select>

                            {/* Jours traduits dynamiquement */}
                            <select 
                                value={filterDay}
                                disabled={!filterMonth}
                                onChange={(e) => setFilterDay(e.target.value)}
                                className={`px-3 py-1.5 rounded-lg text-xs focus:outline-none focus:border-blue-500 disabled:opacity-40 border cursor-pointer ${
                                    isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-300 text-slate-900'
                                }`}
                            >
                                <option value="">{t.allDays}</option>
                                {Array.from({length: 31}, (_, i) => {
                                    const dVal = String(i + 1).padStart(2, '0');
                                    const dLabel = lang === 'zh' ? `${i + 1}${t.dayLabel}` : `${t.dayLabel} ${i + 1}`;
                                    return <option key={dVal} value={dVal}>{dLabel}</option>;
                                })}
                            </select>
                        </div>
                    </div>
                </div>
            )}

            {/* Liste des articles paginée */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
            ) : paginatedNews.length > 0 ? (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {paginatedNews.map((item) => (
                            <div key={item.url || `${item.headline}-${item.published_at}`} className={`p-4 rounded-lg border transition-all flex flex-col justify-between ${
                                isDarkMode 
                                    ? 'bg-slate-950/50 border-slate-800/60 hover:border-slate-700' 
                                    : 'bg-slate-50 border-slate-200 hover:border-slate-300 shadow-sm'
                            }`}>
                                <div>
                                    <div className="flex justify-between items-center text-xs mb-1">
                                        <span className="font-semibold text-blue-500">{item.source}</span>
                                        <span className={`font-mono px-2 py-0.5 rounded ${isDarkMode ? 'text-amber-400 bg-amber-950/40' : 'text-amber-700 bg-amber-100'}`}>
                                            📅 {item.published_at}
                                        </span>
                                    </div>
                                    <a 
                                        href={item.url} 
                                        target="_blank" 
                                        rel="noopener noreferrer" 
                                        className={`text-sm font-bold hover:text-blue-500 transition-colors line-clamp-2 block mb-2 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}
                                    >
                                        {item.headline}
                                    </a>
                                    <p className={`text-xs line-clamp-3 italic ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                                        {item.summary && item.summary.trim() ? item.summary : t.noSummary}
                                    </p>
                                </div>
                                <div className={`mt-3 pt-2 border-t flex justify-between items-center ${isDarkMode ? 'border-slate-800/40' : 'border-slate-200'}`}>
                                    <button
                                        onClick={() => onHighlightDate?.(item.published_at)}
                                        className="px-2.5 py-1 bg-blue-600/30 hover:bg-blue-600 text-blue-300 hover:text-white text-xs font-semibold rounded transition-colors flex items-center gap-1 cursor-pointer"
                                    >
                                        🎯 {t.analyzeBtn}
                                    </button>
                                    <a 
                                        href={item.url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-xs text-blue-500 hover:underline font-medium"
                                    >
                                        {t.readLink}
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Barre de Pagination style Google */}
                    {totalPages > 1 && (
                        <div className={`flex justify-center items-center gap-2 pt-4 border-t ${isDarkMode ? 'border-slate-800/60' : 'border-slate-200'}`}>
                            <button
                                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                disabled={currentPage === 1}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border disabled:opacity-30 cursor-pointer ${
                                    isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700' : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
                                }`}
                            >
                                {t.prevBtn}
                            </button>

                            <div className="flex items-center gap-1">
                                {Array.from({ length: totalPages }, (_, i) => i + 1)
                                    .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
                                    .map((page, idx, arr) => {
                                        const showEllipsisBefore = idx > 0 && page - arr[idx - 1] > 1;
                                        return (
                                            <React.Fragment key={page}>
                                                {showEllipsisBefore && <span className="text-slate-500 px-1 text-xs">...</span>}
                                                <button
                                                    onClick={() => setCurrentPage(page)}
                                                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer border ${
                                                        currentPage === page 
                                                            ? 'bg-blue-600 text-white border-blue-500' 
                                                            : isDarkMode ? 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white' : 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200'
                                                    }`}
                                                >
                                                    {page}
                                                </button>
                                            </React.Fragment>
                                        );
                                    })}
                            </div>

                            <button
                                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                disabled={currentPage === totalPages}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border disabled:opacity-30 cursor-pointer ${
                                    isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700' : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
                                }`}
                            >
                                {t.nextBtn}
                            </button>
                        </div>
                    )}
                </div>
            ) : (
                <div className={`p-8 text-center text-sm rounded-lg border ${
                    isDarkMode ? 'bg-slate-950/30 border-slate-800/40 text-slate-500' : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}>
                    {t.noResults}
                </div>
            )}
        </div>
    );
}

export default IndependentNewsPanel;