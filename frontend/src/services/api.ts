import axios from 'axios';

// Même origine quand l'interface est servie par le backend (application installée), sinon backend local (Vite dev)
const isServedByBackend = window.location.protocol.startsWith('http') && window.location.port !== '5173';
const API_BASE_URL = isServedByBackend ? '/api' : 'http://127.0.0.1:8000/api';

export const apiClient = axios.create({ baseURL: API_BASE_URL });

export type Lang = 'en' | 'fr' | 'es' | 'zh';
export type Verdict = 'STRONG_BUY' | 'BUY' | 'HOLD' | 'REDUCE' | 'SELL';

export interface Quote {
  symbol: string;
  name: string;
  short_name: string;
  currency: string;
  exchange: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  day_high: number;
  day_low: number;
  year_high: number;
  year_low: number;
  error?: boolean;
}

export interface HistoryPoint {
  timestamp: string;
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Article {
  id: number;
  headline: string;
  summary: string;
  url: string;
  source: string;
  timestamp: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  sentiment_score: number | null;
  ai_sentiment: string | null;
}

export interface PriceEvent {
  date: string;
  change: number;
  kind: 'drop' | 'jump';
  after_20d: number | null;
  headlines: string[];
}

export interface Advice {
  symbol: string;
  name: string;
  verdict: Verdict;
  verdict_label: string;
  score: number;
  confidence: 'low' | 'medium' | 'high';
  horizon: string | null;
  summary: string;
  opportunities: string[];
  threats: string[];
  patterns: string[];
  catalysts: string[];
  technicals: Record<string, number | boolean | null>;
  events: PriceEvent[];
  engine: string;
  ai_error: string | null;
  generated_at: number;
  articles_analyzed: number;
}

export interface Favorite {
  symbol: string;
  name: string;
  advice: { verdict: Verdict; score: number; generated_at: number } | null;
}

export interface AiSettings {
  provider: 'local' | 'gemini' | 'groq';
  has_key: boolean;
  key_hint: string;
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

const get = async <T,>(url: string, params?: object): Promise<T> => (await apiClient.get<T>(url, { params })).data;

export const api = {
  quote: (symbol: string) => get<Quote>(`/market/quote/${encodeURIComponent(symbol)}`),
  quotes: (symbols: string[]) => get<Quote[]>('/market/quotes', { symbols: symbols.join(',') }),
  history: (symbol: string, period: string) =>
    get<{ data: HistoryPoint[] }>(`/market/history/${encodeURIComponent(symbol)}`, { period }).then((r) => r.data),
  search: (q: string) => get<SearchResult[]>('/market/search', { q }),
  news: (symbol: string, refresh = false) =>
    get<{ articles: Article[]; backfilling: boolean }>(`/market/news/${encodeURIComponent(symbol)}`, { refresh }),
  advice: (symbol: string, lang: Lang, refresh = false, ai = true) =>
    get<Advice>(`/advice/${encodeURIComponent(symbol)}`, { lang, refresh, ai }),
  favorites: () => get<Favorite[]>('/favorites'),
  addFavorite: async (symbol: string, name: string) => (await apiClient.post<Favorite[]>('/favorites', { symbol, name })).data,
  removeFavorite: async (symbol: string) => (await apiClient.delete<Favorite[]>(`/favorites/${encodeURIComponent(symbol)}`)).data,
  reorderFavorites: async (symbols: string[]) => (await apiClient.put<Favorite[]>('/favorites/order', symbols)).data,
  aiSettings: () => get<AiSettings>('/settings/ai'),
  saveAiSettings: async (provider: string, key: string) => (await apiClient.put<AiSettings>('/settings/ai', { provider, key })).data,
};

export const errorMessage = (e: unknown): string =>
  axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e);

export const formatPrice = (value: number, currency: string, lang: Lang) => {
  try {
    return new Intl.NumberFormat(lang, { style: 'currency', currency, maximumFractionDigits: value < 10 ? 4 : 2 }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
};
