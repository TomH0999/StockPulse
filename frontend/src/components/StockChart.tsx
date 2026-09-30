import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';
import { HistoryPoint } from '../services/api';

interface StockChartProps {
    data: HistoryPoint[];
    symbol: string;
    highlightDate?: string | null;
    isDarkMode: boolean;
}

export function StockChart({ data, symbol, highlightDate, isDarkMode }: StockChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className={`flex h-full items-center justify-center text-sm ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                Aucune donnée graphique disponible.
            </div>
        );
    }

    const formattedData = data.map(item => ({
        ...item,
        displayDate: new Date(item.timestamp).toLocaleDateString('fr-FR', {
            month: 'short',
            day: 'numeric',
            hour: item.timestamp.includes('T') ? '2-digit' : undefined,
            minute: item.timestamp.includes('T') ? '2-digit' : undefined,
        }),
        rawDate: item.timestamp.substring(0, 10)
    }));

    // Recherche de la correspondance pour le highlight
    let matchedX = undefined;
    if (highlightDate) {
        const targetDay = highlightDate.substring(0, 10);
        const found = formattedData.find(d => d.rawDate === targetDay || d.timestamp.includes(targetDay));
        if (found) {
            matchedX = found.displayDate;
        }
    }

    return (
        <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                <defs>
                    <linearGradient id={`colorPrice-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                    </linearGradient>
                </defs>
                <CartesianGrid 
                    strokeDasharray="3 3" 
                    stroke={isDarkMode ? '#1e293b' : '#e2e8f0'} 
                    vertical={false} 
                />
                <XAxis 
                    dataKey="displayDate" 
                    stroke={isDarkMode ? '#64748b' : '#94a3b8'} 
                    fontSize={11} 
                    tickLine={false} 
                />
                <YAxis 
                    stroke={isDarkMode ? '#64748b' : '#94a3b8'} 
                    fontSize={11} 
                    domain={['auto', 'auto']} 
                    tickLine={false}
                    tickFormatter={(val) => `$${val.toFixed(0)}`}
                />
                <Tooltip 
                    contentStyle={{ 
                        backgroundColor: isDarkMode ? '#0f172a' : '#ffffff', 
                        borderColor: isDarkMode ? '#334155' : '#cbd5e1', 
                        borderRadius: '0.5rem', 
                        color: isDarkMode ? '#fff' : '#0f172a',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                    }}
                    formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Prix']}
                    labelStyle={{ color: isDarkMode ? '#94a3b8' : '#64748b', fontWeight: 'bold' }}
                />
                <Area 
                    type="monotone" 
                    dataKey="close" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill={`url(#colorPrice-${symbol})`} 
                />
                {matchedX && (
                    <ReferenceLine 
                        x={matchedX} 
                        stroke="#f59e0b" 
                        strokeWidth={2.5} 
                        strokeDasharray="4 4"
                        label={{ value: '🎯 Événement', fill: '#f59e0b', position: 'top', fontSize: 12, fontWeight: 'bold' }} 
                    />
                )}
            </AreaChart>
        </ResponsiveContainer>
    );
}

export default StockChart;