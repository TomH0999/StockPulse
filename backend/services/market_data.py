import math
import time
import re
from collections import Counter
import requests
from datetime import datetime, timedelta
from fastapi import HTTPException
from schemas import QuoteResponse, HistoryResponse, HistoryPoint

# En-têtes pour simuler un navigateur moderne
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def clean_float(val, default=0.0) -> float:
    try:
        if val is None or math.isnan(float(val)):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def fetch_quote(symbol: str) -> QuoteResponse:
    try:
        sym = symbol.upper().strip()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")
            
        data = res.json()
        result = data.get('chart', {}).get('result')
        if not result:
            raise HTTPException(status_code=404, detail=f"No data for symbol '{symbol}'.")
            
        meta = result[0].get('meta', {})
        price = clean_float(meta.get('regularMarketPrice') or meta.get('chartPreviousClose'))
        prev_close = clean_float(meta.get('chartPreviousClose') or price)
        
        indicators = result[0].get('indicators', {}).get('quote', [{}])[0]
        closes = [c for c in indicators.get('close', []) if c is not None]
        volumes = [v for v in indicators.get('volume', []) if v is not None]
        
        if price == 0.0 and closes:
            price = clean_float(closes[-1])
                
        if len(closes) >= 2 and prev_close == price:
            prev_close = clean_float(closes[-2])
        
        change = price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close > 0 else 0.0
        volume = int(volumes[-1]) if volumes else int(meta.get('regularMarketVolume', 0))
        
        market_cap = meta.get('marketCap')
        if not market_cap:
            try:
                q_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={sym}"
                q_res = requests.get(q_url, headers=HEADERS, timeout=5)
                if q_res.status_code == 200:
                    q_data = q_res.json()
                    q_result = q_data.get('quoteResponse', {}).get('result', [])
                    if q_result:
                        market_cap = q_result[0].get('marketCap')
            except Exception:
                pass 

        return QuoteResponse(
            symbol=sym,
            price=round(price, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=volume,
            market_cap=market_cap,
            last_updated=datetime.utcnow().isoformat() + "Z"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote for {symbol}: {str(e)}")


def fetch_history(symbol: str, period: str = "1mo", interval: str = "1d") -> HistoryResponse:
    try:
        sym = symbol.upper().strip()
        
        range_map = {
            "1w": "5d",
            "1mo": "1mo",
            "3mo": "3mo",
            "1y": "1y"
        }
        yf_range = range_map.get(period, "1mo")
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={yf_range}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}'.")
            
        data = res.json()
        result = data.get('chart', {}).get('result')
        if not result:
            raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}'.")
            
        timestamps = result[0].get('timestamp', [])
        indicators = result[0].get('indicators', {}).get('quote', [{}])[0]
        
        opens = indicators.get('open', [])
        highs = indicators.get('high', [])
        lows = indicators.get('low', [])
        closes = indicators.get('close', [])
        volumes = indicators.get('volume', [])
        
        points = []
        for i, ts in enumerate(timestamps):
            if i >= len(closes) or closes[i] is None:
                continue
            
            dt = datetime.utcfromtimestamp(ts)
            c_val = clean_float(closes[i])
            
            points.append(HistoryPoint(
                timestamp=dt.isoformat() + "Z",
                open=round(clean_float(opens[i] if i < len(opens) else c_val, c_val), 2),
                high=round(clean_float(highs[i] if i < len(highs) else c_val, c_val), 2),
                low=round(clean_float(lows[i] if i < len(lows) else c_val, c_val), 2),
                close=round(c_val, 2),
                volume=int(clean_float(volumes[i] if i < len(volumes) and volumes[i] is not None else 0, 0))
            ))
            
        if not points:
            raise HTTPException(status_code=404, detail=f"No historical points found for '{symbol}'.")
            
        return HistoryResponse(symbol=sym, period=period, data=points)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history for {symbol}: {str(e)}")


def fetch_news(symbol: str, period: str = "1mo") -> list:
    try:
        sym = symbol.upper().strip()
        
        # --- ⚠️ REMPLACEZ PAR VOTRE CLÉ API FINNHUB (GRATUITE) ---
        FINNHUB_API_KEY = "dau6se1r01qkvn4ob6igdau6se1r01qkvn4ob6j0"
        # ---------------------------------------------------------
        
        # 1. Calcul strict des fenêtres temporelles
        now = datetime.now()
        end_date = now.strftime("%Y-%m-%d")
        
        if period == '1w':
            start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        elif period == '1mo':
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        elif period == '3mo':
            start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        elif period == '1y':
            start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
        else:
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            
        # 🟢 DEBUG : Lisez ceci dans le terminal de votre serveur backend !
        print(f"\n[NEWS DEBUG] Fetching news for {sym} | Période reçue: '{period}' | De {start_date} à {end_date}")
            
        if FINNHUB_API_KEY == "VOTRE_CLE_API_FINNHUB_ICI":
            print("[NEWS ERREUR] La clé API Finnhub n'est pas configurée.")
            return []

        url = f"https://finnhub.io/api/v1/company-news?symbol={sym}&from={start_date}&to={end_date}&token={FINNHUB_API_KEY}"
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200:
            return []
            
        raw_news = res.json()
        if not raw_news:
            return []

        filtered_news = []
        for item in raw_news:
            pub_time = item.get('datetime', 0)
            pub_date = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
            filtered_news.append({
                "headline": item.get('headline', 'Titre indisponible'),
                "summary": item.get('summary', 'Aucun résumé.'),
                "url": item.get('url', '#'),
                "source": item.get('source', 'Inconnu'),
                "published_at": pub_date,
                "timestamp": pub_time,
                "sentiment": "Neutral"
            })

        # 2. ALGORITHME DE CALCUL DE "BUZZ"
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'is', 'are', 'was', 'were', 'has', 'have', 'will'}
        
        all_words = []
        for item in filtered_news:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', item['headline'].lower())
            all_words.extend([w for w in words if w not in stop_words])
        
        word_frequencies = Counter(all_words)
        impact_keywords = {'earnings', 'revenue', 'profit', 'loss', 'guidance', 'acquisition', 'merger', 'sec', 'fda', 'lawsuit', 'ceo', 'upgrade', 'downgrade', 'dividend', 'split', 'record'}
        tier1_sources = ['bloomberg', 'reuters', 'wsj', 'cnbc', 'forbes', 'dow jones', 'financial times']

        # 3. ÉVALUATION COMPARATIVE
        for item in filtered_news:
            score = 0.0
            title_lower = item['headline'].lower()
            source_lower = item['source'].lower()

            # A: Source Premium (+5)
            if any(t1 in source_lower for t1 in tier1_sources):
                score += 5.0
            
            # B: Mots à fort impact boursier (+3 par mot)
            for kw in impact_keywords:
                if kw in title_lower:
                    score += 3.0
            
            # C: Facteur de Buzz sur la période ciblée
            words = re.findall(r'\b[a-zA-Z]{4,}\b', title_lower)
            buzz_score = sum((word_frequencies[w] * 0.2) for w in words if w not in stop_words)
            
            score += buzz_score
            item['relevance_score'] = round(score, 2)
        
        # 4. TRI INTELLIGENT (Les articles au plus fort impact en premier)
        filtered_news.sort(key=lambda x: (x['relevance_score'], x['timestamp']), reverse=True)
        
        # On ne renvoie que le TOP 50 le plus pertinent pour l'IA
        top_50 = filtered_news[:50]
        
        for item in top_50:
            item.pop('timestamp', None)
            
        return top_50
    except Exception as e:
        print(f"Erreur news pour {symbol}: {str(e)}")
        return []