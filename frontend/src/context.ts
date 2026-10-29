import { createContext, useContext } from 'react';
import { translations, T } from './i18n';
import type { Lang } from './services/api';

export const I18nContext = createContext<{ lang: Lang; t: T }>({ lang: 'fr', t: translations.fr });
export const useI18n = () => useContext(I18nContext);

export const VERDICT_STYLE: Record<string, string> = {
  STRONG_BUY: 'bg-emerald-600 text-white',
  BUY: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40',
  HOLD: 'bg-slate-500/15 text-slate-600 dark:text-slate-300 border border-slate-500/40',
  REDUCE: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/40',
  SELL: 'bg-rose-600 text-white',
};

export const VERDICT_LABEL: Record<string, Record<string, string>> = {
  fr: { STRONG_BUY: 'Achat fort', BUY: 'Achat', HOLD: 'Conserver', REDUCE: 'Alléger', SELL: 'Vendre' },
  en: { STRONG_BUY: 'Strong buy', BUY: 'Buy', HOLD: 'Hold', REDUCE: 'Reduce', SELL: 'Sell' },
  es: { STRONG_BUY: 'Compra fuerte', BUY: 'Comprar', HOLD: 'Mantener', REDUCE: 'Reducir', SELL: 'Vender' },
  zh: { STRONG_BUY: '强烈买入', BUY: '买入', HOLD: '持有', REDUCE: '减持', SELL: '卖出' },
};
