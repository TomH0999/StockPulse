from fastapi import APIRouter, Path, Query
from schemas import QuoteResponse, HistoryResponse, NewsItem
from services.market_data import fetch_quote, fetch_history
from services.news_aggregator import fetch_news
from typing import List
import time
from datetime import datetime
import requests
from fastapi import APIRouter

router = APIRouter(prefix="/api/market", tags=["Market Data"])
router = APIRouter(prefix="/api/market", tags=["market"])

# En-têtes pour éviter les blocages de Yahoo Finance
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

@router.get("/news/{symbol}")
def get_market_news(symbol: str, period: str = "1mo"):
    try:
        sym = symbol.upper().strip()
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={sym}&newsCount=40"
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            return []
            
        data = res.json()
        raw_news = data.get('news', [])
        
        # Filtrage temporel précis selon la période demandée (1w, 1mo, 3mo, 1y)
        now = time.time()
        if period == '1w':
            threshold = now - (7 * 24 * 3600)
        elif period == '1mo':
            threshold = now - (30 * 24 * 3600)
        elif period == '3mo':
            threshold = now - (90 * 24 * 3600)
        elif period == '1y':
            threshold = now - (365 * 24 * 3600)
        else:
            threshold = now - (30 * 24 * 3600)
            
        filtered_news = []
        for item in raw_news:
            pub_time = item.get('providerPublishTime', now)
            # On ne garde que les articles qui entrent dans la fenêtre temporelle
            if pub_time >= threshold:
                pub_date = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                filtered_news.append({
                    "headline": item.get('title', 'Titre indisponible'),
                    "summary": item.get('summary', 'Aucun résumé disponible pour cet article.'),
                    "url": item.get('link', '#'),
                    "source": item.get('publisher', 'Yahoo Finance'),
                    "published_at": pub_date,
                    "sentiment": "Neutral" # Prêt pour votre future IA locale
                })
                
        return filtered_news
    except Exception as e:
        print(f"Erreur de récupération des news pour {symbol}: {str(e)}")
        return []

@router.get("/quote/{symbol}", response_model=QuoteResponse)
def get_quote(symbol: str = Path(..., description="The stock ticker symbol (e.g., AAPL)")):
    return fetch_quote(symbol)

@router.get("/history/{symbol}", response_model=HistoryResponse)
def get_history(
    symbol: str = Path(..., description="The stock ticker symbol"),
    period: str = Query("1mo", description="Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: str = Query("1d", description="Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo")
):
    return fetch_history(symbol, period, interval)

@router.get("/news/{symbol}", response_model=List[NewsItem])
def get_news(symbol: str = Path(..., description="The stock ticker symbol")):
    return fetch_news(symbol)