import React, { useState, useMemo } from 'react';
import { STOCKS_DATABASE, StockItem } from '../data/stocksDatabase';

interface StockSearchSelectorProps {
    onSelectStock: (symbol: string) => void;
    isDarkMode?: boolean;
    lang?: 'en' | 'fr' | 'es' | 'zh';
}

const translations = {
    en: {
        placeholder: "Search by name or ticker (e.g., AAPL, Apple)...",
        noResults: "No companies found for"
    },
    fr: {
        placeholder: "Rechercher par nom ou acronyme (ex: AAPL, Apple)...",
        noResults: "Aucune entreprise trouvée pour"
    },
    es: {
        placeholder: "Buscar por nombre o ticker (ej., AAPL, Apple)...",
        noResults: "No se encontraron empresas para"
    },
    zh: {
        placeholder: "按名称或代码搜索（例如：AAPL, Apple）...",
        noResults: "未找到相关公司"
    }
};

export function StockSearchSelector({ onSelectStock, isDarkMode = true, lang = 'en' }: StockSearchSelectorProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [isOpen, setIsOpen] = useState(false);

    const t = translations[lang] || translations.en;

    // Filtrage dynamique en fonction de la saisie (sur le symbole ou le nom)
    const filteredStocks = useMemo(() => {
        if (!searchTerm.trim()) return [];
        const term = searchTerm.toLowerCase();
        return STOCKS_DATABASE.filter(
            stock => 
                stock.symbol.toLowerCase().includes(term) || 
                stock.name.toLowerCase().includes(term)
        ).slice(0, 10); // Limite l'affichage à 10 résultats pour garder l'UI fluide
    }, [searchTerm]);

    const handleSelect = (stock: StockItem) => {
        onSelectStock(stock.symbol);
        setSearchTerm(stock.symbol);
        setIsOpen(false);
    };

    return (
        <div className="relative w-full max-w-md">
            {/* Barre de recherche */}
            <div className="relative">
                <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => {
                        setSearchTerm(e.target.value);
                        setIsOpen(true);
                    }}
                    onFocus={() => setIsOpen(true)}
                    placeholder={t.placeholder}
                    className={`w-full px-4 py-2 rounded-lg text-sm focus:outline-none focus:border-blue-500 border transition-colors ${
                        isDarkMode 
                            ? 'bg-slate-950 border-slate-700 text-white placeholder-slate-500' 
                            : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 shadow-sm'
                    }`}
                />
            </div>

            {/* Liste déroulante des résultats filtrés */}
            {isOpen && filteredStocks.length > 0 && (
                <div className={`absolute z-50 w-full mt-2 rounded-xl shadow-2xl max-h-60 overflow-y-auto border ${
                    isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-300'
                }`}>
                    {filteredStocks.map((stock) => (
                        <div
                            key={stock.symbol}
                            onClick={() => handleSelect(stock)}
                            className={`px-4 py-3 cursor-pointer transition-colors border-b last:border-none ${
                                isDarkMode 
                                    ? 'hover:bg-slate-800 border-slate-800/50' 
                                    : 'hover:bg-slate-100 border-slate-200'
                            }`}
                        >
                            {/* Nom de l'entreprise */}
                            <div className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                                {stock.name}
                            </div>
                            {/* Acronyme affiché en dessous de la recherche en cours */}
                            <div className="text-xs font-mono text-blue-400 mt-0.5 tracking-wider">
                                {stock.symbol}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {isOpen && searchTerm.trim() && filteredStocks.length === 0 && (
                <div className={`absolute z-50 w-full mt-2 rounded-xl p-4 text-center text-sm border shadow-lg ${
                    isDarkMode ? 'bg-slate-900 border-slate-700 text-slate-400' : 'bg-white border-slate-300 text-slate-600'
                }`}>
                    {t.noResults} "{searchTerm}"
                </div>
            )}
        </div>
    );
}

export default StockSearchSelector;