import React, { useState, useEffect } from 'react';
import { portfolioApi, Portfolio } from '../services/api';
import { Briefcase, Plus, FileText } from 'lucide-react';

interface PortfolioManagerProps {
    isDarkMode: boolean;
    lang: 'en' | 'fr' | 'es' | 'zh';
}

const translations = {
    en: {
        title: "Portfolio Command Center",
        subtitle: "Manage assets, track cost basis, analyze sentiment, and export PDF reports.",
        exportPdf: "Export PDF",
        newPortfolioPlaceholder: "New portfolio name (e.g., Retirement Fund)...",
        createPortfolioBtn: "Create Portfolio",
        holdingsTitle: "Holdings in",
        symbolCol: "Symbol",
        sharesCol: "Shares",
        avgPriceCol: "Avg Price",
        costBasisCol: "Cost Basis",
        noAssets: "No assets in this portfolio yet.",
        executeOrderTitle: "Execute Order",
        tickerLabel: "Ticker Symbol",
        tickerPlaceholder: "e.g., AAPL",
        orderTypeLabel: "Order Type",
        buy: "BUY",
        sell: "SELL",
        quantityLabel: "Quantity",
        priceLabel: "Execution Price ($)",
        confirmOrderBtn: "Confirm Order",
        portfolioSentiment: "Portfolio Sentiment",
        sentimentDesc: "Aggregate sentiment score across all holdings.",
        noPortfolio: "No portfolio selected. Create one above to begin.",
        defaultError: "Failed to create portfolio.",
        orderError: "Transaction failed."
    },
    fr: {
        title: "Centre de Commande des Portefeuilles",
        subtitle: "Gérez vos actifs, suivez le prix de revient, analysez le sentiment et exportez des rapports PDF.",
        exportPdf: "Exporter en PDF",
        newPortfolioPlaceholder: "Nom du nouveau portefeuille (ex: Fonds Retraite)...",
        createPortfolioBtn: "Créer un portefeuille",
        holdingsTitle: "Actifs dans",
        symbolCol: "Symbole",
        sharesCol: "Actions",
        avgPriceCol: "Prix Moyen",
        costBasisCol: "Coût Total",
        noAssets: "Aucun actif dans ce portefeuille pour l'instant.",
        executeOrderTitle: "Exécuter un ordre",
        tickerLabel: "Symbole boursier",
        tickerPlaceholder: "ex: AAPL",
        orderTypeLabel: "Type d'ordre",
        buy: "ACHAT",
        sell: "VENTE",
        quantityLabel: "Quantité",
        priceLabel: "Prix d'exécution ($)",
        confirmOrderBtn: "Confirmer l'ordre",
        portfolioSentiment: "Sentiment du Portefeuille",
        sentimentDesc: "Score de sentiment global de l'ensemble des positions.",
        noPortfolio: "Aucun portefeuille sélectionné. Créez-en un ci-dessus pour commencer.",
        defaultError: "Échec de la création du portefeuille.",
        orderError: "Échec de la transaction."
    },
    es: {
        title: "Centro de Comando de Carteras",
        subtitle: "Administre activos, realice un seguimiento de los costos, analice el sentimiento y exporte informes en PDF.",
        exportPdf: "Exportar PDF",
        newPortfolioPlaceholder: "Nombre de la nueva cartera (ej., Fondo de Retiro)...",
        createPortfolioBtn: "Crear Cartera",
        holdingsTitle: "Activos en",
        symbolCol: "Símbolo",
        sharesCol: "Acciones",
        avgPriceCol: "Precio Promedio",
        costBasisCol: "Costo Base",
        noAssets: "Aún no hay activos en esta cartera.",
        executeOrderTitle: "Ejecutar Orden",
        tickerLabel: "Símbolo Ticker",
        tickerPlaceholder: "ej., AAPL",
        orderTypeLabel: "Tipo de Orden",
        buy: "COMPRA",
        sell: "VENTA",
        quantityLabel: "Cantidad",
        priceLabel: "Precio de Ejecución ($)",
        confirmOrderBtn: "Confirmar Orden",
        portfolioSentiment: "Sentimiento de la Cartera",
        sentimentDesc: "Puntuación de sentimiento agregada en todas las tenencias.",
        noPortfolio: "Ninguna cartera seleccionada. Cree una arriba para comenzar.",
        defaultError: "Error al crear la cartera.",
        orderError: "La transacción falló."
    },
    zh: {
        title: "投资组合指挥中心",
        subtitle: "管理资产、追踪成本基础、分析市场情绪并导出PDF报告。",
        exportPdf: "导出PDF",
        newPortfolioPlaceholder: "新投资组合名称（例如：退休基金）...",
        createPortfolioBtn: "创建投资组合",
        holdingsTitle: "持仓于",
        symbolCol: "代码",
        sharesCol: "份额",
        avgPriceCol: "平均价格",
        costBasisCol: "成本基础",
        noAssets: "该投资组合中暂无资产。",
        executeOrderTitle: "执行订单",
        tickerLabel: "股票代码",
        tickerPlaceholder: "例如：AAPL",
        orderTypeLabel: "订单类型",
        buy: "买入",
        sell: "卖出",
        quantityLabel: "数量",
        priceLabel: "执行价格 ($)",
        confirmOrderBtn: "确认订单",
        portfolioSentiment: "投资组合情绪",
        sentimentDesc: "所有持仓的综合情绪评分。",
        noPortfolio: "未选择投资组合。请在上方创建一个以开始。",
        defaultError: "创建投资组合失败。",
        orderError: "交易失败。"
    }
};

export const PortfolioManager: React.FC<PortfolioManagerProps> = ({ isDarkMode, lang }) => {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [newPortfolioName, setNewPortfolioName] = useState('');
  const [sentiment, setSentiment] = useState<{ overall: string; score: number; details: Record<string, any> } | null>(null);

  // Transaction form state
  const [symbol, setSymbol] = useState('');
  const [type, setType] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [error, setError] = useState<string | null>(null);

  const t = translations[lang];

  const loadPortfolios = async () => {
    try {
      const data = await portfolioApi.getPortfolios();
      setPortfolios(data);
      if (data.length > 0 && !selectedPortfolio) {
        setSelectedPortfolio(data[0]);
      }
    } catch (err) {
      console.error("Failed to load portfolios", err);
    }
  };

  useEffect(() => {
    loadPortfolios();
  }, []);

  useEffect(() => {
    if (selectedPortfolio) {
      portfolioApi.getSentiment(selectedPortfolio.id)
        .then(res => setSentiment(res))
        .catch(err => console.error("Failed to fetch sentiment", err));
    }
  }, [selectedPortfolio]);

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPortfolioName.trim()) return;
    try {
      const created = await portfolioApi.createPortfolio(newPortfolioName.trim());
      setPortfolios([...portfolios, created]);
      setSelectedPortfolio(created);
      setNewPortfolioName('');
    } catch (err: any) {
      setError(err.response?.data?.detail || t.defaultError);
    }
  };

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPortfolio || !symbol || !quantity || !price) return;
    setError(null);
    try {
      await portfolioApi.addTransaction(
        selectedPortfolio.id,
        symbol.toUpperCase(),
        type,
        parseFloat(quantity),
        parseFloat(price)
      );
      const updatedList = await portfolioApi.getPortfolios();
      setPortfolios(updatedList);
      const updatedCurrent = updatedList.find(p => p.id === selectedPortfolio.id);
      if (updatedCurrent) setSelectedPortfolio(updatedCurrent);

      setSymbol('');
      setQuantity('');
      setPrice('');
    } catch (err: any) {
      setError(err.response?.data?.detail || t.orderError);
    }
  };

  const handleDownloadReport = () => {
    if (!selectedPortfolio) return;
    window.open(portfolioApi.downloadReportUrl(selectedPortfolio.id), '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header & Portfolio Selector */}
      <div className={`p-6 rounded-xl border shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 transition-colors ${
        isDarkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900 shadow-sm'
      }`}>
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Briefcase className="w-7 h-7 text-sky-500" />
            {t.title}
          </h2>
          <p className={`text-sm ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{t.subtitle}</p>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <select 
            value={selectedPortfolio?.id || ''}
            onChange={(e) => {
              const found = portfolios.find(p => p.id === Number(e.target.value));
              if (found) setSelectedPortfolio(found);
            }}
            className={`rounded-lg px-4 py-2 focus:outline-none focus:border-sky-500 border cursor-pointer ${
              isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-100 border-slate-300 text-slate-900'
            }`}
          >
            {portfolios.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {selectedPortfolio && (
            <button 
              onClick={handleDownloadReport}
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition flex-shrink-0 cursor-pointer"
            >
              <FileText className="w-4 h-4" />
              {t.exportPdf}
            </button>
          )}
        </div>
      </div>

      {/* Create Portfolio Form */}
      <form onSubmit={handleCreatePortfolio} className={`p-4 rounded-xl border flex gap-2 transition-colors ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <input 
          type="text" 
          value={newPortfolioName}
          onChange={(e) => setNewPortfolioName(e.target.value)}
          placeholder={t.newPortfolioPlaceholder}
          className={`flex-grow rounded-lg px-4 py-2 focus:outline-none focus:border-sky-500 border ${
            isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100 placeholder-slate-500' : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400'
          }`}
        />
        <button type="submit" className="bg-sky-600 hover:bg-sky-500 text-white px-5 py-2 rounded-lg font-medium flex items-center gap-1 transition cursor-pointer">
          <Plus className="w-4 h-4" /> {t.createPortfolioBtn}
        </button>
      </form>

      {error && (
        <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-200 rounded-xl">
          {error}
        </div>
      )}

      {selectedPortfolio ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Asset Holdings Table */}
          <div className={`p-6 rounded-xl border shadow-xl space-y-4 lg:col-span-2 transition-colors ${
            isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
          }`}>
            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-slate-200' : 'text-slate-900'}`}>
              {t.holdingsTitle} {selectedPortfolio.name}
            </h3>
            <div className="overflow-x-auto">
              <table className={`w-full text-left text-sm ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                <thead className={`uppercase text-xs ${isDarkMode ? 'bg-slate-950 text-slate-400' : 'bg-slate-100 text-slate-600'}`}>
                  <tr>
                    <th className="p-3">{t.symbolCol}</th>
                    <th className="p-3">{t.sharesCol}</th>
                    <th className="p-3">{t.avgPriceCol}</th>
                    <th className="p-3">{t.costBasisCol}</th>
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDarkMode ? 'divide-slate-800' : 'divide-slate-200'}`}>
                  {selectedPortfolio.assets && selectedPortfolio.assets.length > 0 ? (
                    selectedPortfolio.assets.map((asset) => (
                      <tr key={asset.id} className={`transition-colors ${isDarkMode ? 'hover:bg-slate-950/50' : 'hover:bg-slate-50'}`}>
                        <td className={`p-3 font-bold ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>{asset.symbol}</td>
                        <td className="p-3">{asset.quantity.toFixed(4)}</td>
                        <td className="p-3">${asset.average_price.toFixed(2)}</td>
                        <td className="p-3">${(asset.quantity * asset.average_price).toFixed(2)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="p-6 text-center text-slate-500">{t.noAssets}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Transaction Form */}
          <div className={`p-6 rounded-xl border shadow-xl space-y-4 transition-colors ${
            isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
          }`}>
            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-slate-200' : 'text-slate-900'}`}>{t.executeOrderTitle}</h3>
            <form onSubmit={handleAddTransaction} className="space-y-4">
              <div>
                <label className={`block text-xs font-medium mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{t.tickerLabel}</label>
                <input 
                  type="text" 
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  placeholder={t.tickerPlaceholder}
                  required
                  className={`w-full rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500 border ${
                    isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={`block text-xs font-medium mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{t.orderTypeLabel}</label>
                  <select 
                    value={type} 
                    onChange={(e) => setType(e.target.value as 'BUY' | 'SELL')}
                    className={`w-full rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500 border cursor-pointer ${
                      isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  >
                    <option value="BUY">{t.buy}</option>
                    <option value="SELL">{t.sell}</option>
                  </select>
                </div>
                <div>
                  <label className={`block text-xs font-medium mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{t.quantityLabel}</label>
                  <input 
                    type="number" 
                    step="any" 
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="10"
                    required
                    className={`w-full rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500 border ${
                      isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>
              <div>
                <label className={`block text-xs font-medium mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{t.priceLabel}</label>
                <input 
                  type="number" 
                  step="any" 
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="175.50"
                  required
                  className={`w-full rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500 border ${
                    isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                />
              </div>
              <button type="submit" className="w-full bg-sky-600 hover:bg-sky-500 text-white py-2.5 rounded-lg font-medium transition cursor-pointer">
                {t.confirmOrderBtn}
              </button>
            </form>

            {/* Portfolio Sentiment Banner */}
            {sentiment && (
              <div className={`mt-6 p-4 rounded-lg border space-y-2 transition-colors ${
                isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex justify-between items-center">
                  <span className={`text-xs font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{t.portfolioSentiment}</span>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${sentiment.overall === 'Bullish' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : sentiment.overall === 'Bearish' ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-slate-800 text-slate-300'}`}>
                    {sentiment.overall}
                  </span>
                </div>
                <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{t.sentimentDesc}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className={`p-12 rounded-xl border text-center transition-colors ${
          isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500 shadow-sm'
        }`}>
          {t.noPortfolio}
        </div>
      )}
    </div>
  );
};

export default PortfolioManager;