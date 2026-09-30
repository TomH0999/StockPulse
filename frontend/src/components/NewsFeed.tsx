import React from 'react';
import { NewsItem } from '../services/api';
import { ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface NewsFeedProps {
  news: NewsItem[];
  symbol: string;
}

export const NewsFeed: React.FC<NewsFeedProps> = ({ news, symbol }) => {
  if (!news || news.length === 0) {
    return (
      <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 text-slate-400 text-center">
        No recent market news found for {symbol}.
      </div>
    );
  }

  return (
    <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow-xl space-y-4">
      <h3 className="text-lg font-semibold text-slate-200">Live Sentiment & News Feed ({symbol})</h3>
      <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
        {news.map((item, idx) => {
          let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
          let Icon = Minus;
          if (item.sentiment === 'Buy') {
            badgeColor = 'bg-emerald-950 text-emerald-400 border-emerald-800';
            Icon = TrendingUp;
          } else if (item.sentiment === 'Sell') {
            badgeColor = 'bg-rose-950 text-rose-400 border-rose-800';
            Icon = TrendingDown;
          }

          return (
            <div key={idx} className="p-4 bg-slate-950 rounded-lg border border-slate-800/80 hover:border-slate-700 transition">
              <div className="flex justify-between items-start gap-2 mb-2">
                <a 
                  href={item.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="font-medium text-slate-100 hover:text-sky-400 transition flex items-center gap-1.5 text-sm"
                >
                  {item.headline}
                  <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 text-slate-500" />
                </a>
                <span className={`text-xs px-2.5 py-0.5 rounded-full border flex items-center gap-1 font-medium flex-shrink-0 ${badgeColor}`}>
                  <Icon className="w-3 h-3" />
                  {item.sentiment}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span className="font-semibold text-slate-400">{item.source}</span>
                <span>{new Date(item.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};