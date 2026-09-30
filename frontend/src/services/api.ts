import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap?: number;
  last_updated: string;
}

export interface HistoryPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface NewsItem {
  headline: string;
  summary: string;
  url: string;
  source: string;
  published_at: string;
  sentiment: 'Buy' | 'Hold' | 'Sell';
}

export interface Transaction {
  id: number;
  type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  timestamp: string;
}

export interface Asset {
  id: number;
  symbol: string;
  quantity: number;
  average_price: number;
  last_updated: string;
  transactions: Transaction[];
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
  assets: Asset[];
}

export const marketApi = {
  getQuote: async (symbol: string): Promise<Quote> => {
    const response = await apiClient.get<Quote>(`/market/quote/${symbol}`);
    return response.data;
  },
  getHistory: async (symbol: string, period: string = '1mo'): Promise<{ symbol: string; period: string; data: HistoryPoint[] }> => {
    const response = await apiClient.get(`/market/history/${symbol}?period=${period}`);
    return response.data;
  },
  // Mis à jour : accepte le paramètre period
  getNews: async (symbol: string, period: string = '1mo'): Promise<NewsItem[]> => {
    const response = await apiClient.get<NewsItem[]>(`/market/news/${symbol}?period=${period}`);
    return response.data;
  }
};

export const portfolioApi = {
  getPortfolios: async (): Promise<Portfolio[]> => {
    const response = await apiClient.get<Portfolio[]>('/portfolio/');
    return response.data;
  },
  createPortfolio: async (name: string): Promise<Portfolio> => {
    const response = await apiClient.post<Portfolio>('/portfolio/', { name });
    return response.data;
  },
  addTransaction: async (portfolioId: number, symbol: string, type: 'BUY' | 'SELL', quantity: number, price: number): Promise<Asset> => {
    const response = await apiClient.post<Asset>(`/portfolio/${portfolioId}/transaction`, {
      symbol,
      type,
      quantity,
      price
    });
    return response.data;
  },
  getSentiment: async (portfolioId: number): Promise<{ overall: string; score: number; details: Record<string, any> }> => {
    const response = await apiClient.get(`/portfolio/${portfolioId}/sentiment`);
    return response.data;
  },
  downloadReportUrl: (portfolioId: number): string => {
    return `${API_BASE_URL}/portfolio/${portfolioId}/report`;
  }
};