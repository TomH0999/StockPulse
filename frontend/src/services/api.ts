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
  fundamentals: Fundamentals | null;
  track_record: Record<'1m' | '3m' | '6m', { n: number; hit_rate: number | null; avg_after_buy: number | null; avg_after_sell: number | null }> | null;
  verification: { status: 'verified' | 'warning'; checked: number; unverified: string[]; notes: string[]; local_score: number } | null;
  generated_at: number;
  articles_analyzed: number;
}

export interface AdviceSummary {
  verdict: Verdict;
  score: number;
  confidence: 'low' | 'medium' | 'high';
  engine: string;
  generated_at: number;
}

export interface Favorite {
  symbol: string;
  name: string;
  advice: AdviceSummary | null;
}

export interface CatalogEntry {
  isin?: string | null;
  status?: 'suspended' | 'delisted' | null;
  new?: boolean;
  symbol: string;
  name: string;
  market: string;
  country: string;
  pea: boolean;
  sector: string | null;
}

export interface ScreenerRow extends CatalogEntry {
  currency?: string;
  price?: number;
  chg_1d?: number;
  chg_1w?: number | null;
  chg_1m?: number | null;
  chg_3m?: number | null;
  chg_6m?: number | null;
  chg_ytd?: number | null;
  chg_1y?: number | null;
  volatility?: number | null;
  from_high?: number | null;
  range_pos?: number | null;
  spark?: number[];
  advice: AdviceSummary | null;
}

export interface AiKey {
  id: string;
  provider: string;
  hint: string;
  model: string | null;
  ok: number;
  errors: number;
  last_error: string | null;
  cooldown: number;
  reason: 'daily' | 'rate' | null;
  used_today: number;
  budget: number;
}

export interface AiSettings {
  providers: string[];
  keys: AiKey[];
  auto: {
    enabled: boolean;
    ai_hours: number;
    ai_all: boolean;
    total: number;
    analysed: number;
    ai_analysed: number;
    keys_available: number;
    last_error: string | null;
  };
}

export interface HealthReport {
  overall: 'ok' | 'warn' | 'error';
  checks: { id: string; status: 'ok' | 'warn' | 'error'; detail: string }[];
  checked_at: number;
  version: string;
}

export interface PortfolioLine {
  id: number;
  symbol: string;
  name: string;
  quantity: number;
  avg_price: number;
  currency: string;
  price: number;
  change_percent: number | null;
  value: number;
  cost: number;
  pnl: number;
  pnl_percent: number;
  weight: number | null;
  advice: AdviceSummary | null;
  alerts: string[];
}

export interface Portfolio {
  lines: PortfolioLine[];
  value: number;
  cost: number;
  pnl: number;
  pnl_percent: number;
  day_change: number;
  cash: number;
  deposits: number;
  ceiling: number;
  total: number;
  performance: number | null;
}

export interface Fundamentals {
  pe: number | null; net_margin: number | null; debt_to_equity: number | null; roe: number | null;
  next_earnings: string | null; next_dividend: { date: string; amount: number | null } | null; source: string; fetched_at: number;
}

export interface OrderPlan {
  symbol: string; side: 'buy' | 'sell' | 'reduce'; name: string; isin: string | null; price: number; currency: string;
  quantity: number; held?: number; limit: number; amount: number; fees: number; total: number;
  stop_loss?: number; target?: number; weight_after?: number; realized_pnl?: number; avg_price?: number;
  advice: AdviceSummary | null; warnings: string[]; fees_settings: { pct: number; min: number };
}

export interface PriceAlert { id: number; symbol: string; direction: 'above' | 'below'; price: number; triggered_at: number | null }
export interface AlertEvent { key: string; type: 'price' | 'drop' | 'verdict'; symbol: string; [k: string]: unknown }
export interface PortfolioAnalysis {
  diversification: {
    sectors: Record<string, number>;
    countries: Record<string, number>;
    warnings: { code: string; [k: string]: unknown }[];
    actions: { code: string; symbol: string; [k: string]: unknown }[];
  };
  benchmark: { index: string; series: { day: string; portfolio: number; index: number }[] };
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
  catalog: () => get<CatalogEntry[]>('/catalog'),
  health: (refresh = false) => get<HealthReport>('/health/full', { refresh }),
  portfolio: () => get<Portfolio>('/portfolio'),
  orderPlan: (symbol: string, side: string, amount?: number) => get<OrderPlan>('/orders/plan', { symbol, side, amount }),
  executeOrder: async (symbol: string, side: string, quantity: number, price: number, fees: number) =>
    (await apiClient.post<Portfolio>('/orders/execute', { symbol, side, quantity, price, fees })).data,
  setFees: async (pct: number, minimum: number) => (await apiClient.put('/orders/fees', { pct, minimum })).data,
  dataSettings: () => get<{ providers: Record<string, string>; keys: { id: string; provider: string; hint: string }[]; catalog_updated: number }>('/settings/data'),
  addDataKey: async (provider: string, key: string) => (await apiClient.post('/settings/data/keys', { provider, key })).data,
  removeDataKey: async (id: string) => (await apiClient.delete(`/settings/data/keys/${id}`)).data,
  portfolioAnalysis: (period = '1y') => get<PortfolioAnalysis>('/portfolio/analysis', { period }),
  trackRecord: () => get<Record<string, { symbols: number; n: number; hit_rate: number | null }>>('/track-record'),
  alerts: () => get<{ price_alerts: PriceAlert[]; events: AlertEvent[] }>('/alerts'),
  addAlert: async (symbol: string, direction: string, price: number) => (await apiClient.post<PriceAlert[]>('/alerts', { symbol, direction, price })).data,
  removeAlert: async (id: number) => (await apiClient.delete<PriceAlert[]>(`/alerts/${id}`)).data,
  addLine: async (symbol: string, quantity: number, avg_price: number) => (await apiClient.post<Portfolio>('/portfolio/lines', { symbol, quantity, avg_price })).data,
  editLine: async (id: number, symbol: string, quantity: number, avg_price: number) => (await apiClient.put<Portfolio>(`/portfolio/lines/${id}`, { symbol, quantity, avg_price })).data,
  deleteLine: async (id: number) => (await apiClient.delete<Portfolio>(`/portfolio/lines/${id}`)).data,
  setAccount: async (deposits: number, cash: number) => (await apiClient.put<Portfolio>('/portfolio/account', { deposits, cash })).data,
  screener: () => get<{ updated: number; rows: ScreenerRow[] }>('/screener'),
  aiSettings: () => get<AiSettings>('/settings/ai'),
  addAiKey: async (provider: string, key: string) => (await apiClient.post<AiSettings>('/settings/ai/keys', { provider, key })).data,
  removeAiKey: async (id: string) => (await apiClient.delete<AiSettings>(`/settings/ai/keys/${id}`)).data,
  setAuto: async (enabled: boolean, ai_hours: number, ai_all = false) => (await apiClient.put<AiSettings>('/settings/auto', { enabled, ai_hours, ai_all })).data,
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

let catalogPromise: Promise<CatalogEntry[]> | null = null;
export const loadCatalog = () => (catalogPromise ??= api.catalog().catch((e) => { catalogPromise = null; throw e; }));

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`);

export const money = (v: number, lang: Lang, currency = 'EUR') => {
  try { return new Intl.NumberFormat(lang, { style: 'currency', currency }).format(v); } catch { return `${v.toFixed(2)} ${currency}`; }
};
