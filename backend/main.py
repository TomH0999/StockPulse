from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import math
import requests
from datetime import datetime
import sqlite3
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import re
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base
import models
from routers import portfolio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockPulse Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "..", "market_news.db")
FRONTEND_DIST = os.path.join(BASE_DIR, "..", "frontend", "dist")

app.include_router(portfolio.router)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            headline TEXT,
            summary TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            timestamp INTEGER,
            sentiment TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def clean_float(val, default=0.0) -> float:
    try:
        if val is None or math.isnan(float(val)):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r'[^a-z0-9]', '', title.lower())

@app.get("/api/market/quote/{symbol}")
def get_quote(symbol: str):
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
                    q_result = q_res.json().get('quoteResponse', {}).get('result', [])
                    if q_result:
                        market_cap = q_result[0].get('marketCap')
            except Exception:
                pass 

        return {
            "symbol": sym,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": volume,
            "market_cap": market_cap,
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/history/{symbol}")
def get_history(symbol: str, period: str = Query("1mo")):
    try:
        sym = symbol.upper().strip()
        period_lower = period.lower()
        
        range_map = {"1w": "5d", "1mo": "1mo", "3mo": "3mo", "1y": "1y"}
        yf_range = range_map.get(period_lower, "1mo")
        interval = '1d' if period_lower in ['1mo', '3mo', '1y'] else '60m'
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={yf_range}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="Not found")
            
        data = res.json()
        result = data.get('chart', {}).get('result')
        if not result:
            raise HTTPException(status_code=404, detail="Not found")
            
        timestamps = result[0].get('timestamp', [])
        quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
        
        opens, highs, lows = quotes.get('open', []), quotes.get('high', []), quotes.get('low', [])
        closes, volumes = quotes.get('close', []), quotes.get('volume', [])
        
        history_points = []
        for i, ts in enumerate(timestamps):
            dt = datetime.utcfromtimestamp(ts).isoformat() + "Z"
            history_points.append({
                "timestamp": dt,
                "open": clean_float(opens[i]) if i < len(opens) else 0,
                "high": clean_float(highs[i]) if i < len(highs) else 0,
                "low": clean_float(lows[i]) if i < len(lows) else 0,
                "close": clean_float(closes[i]) if i < len(closes) else 0,
                "volume": int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
            })
            
        return {"symbol": sym, "period": period, "data": history_points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/news/{symbol}")
def get_news(symbol: str):
    try:
        sym = symbol.upper().strip()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT headline FROM articles WHERE symbol = ?", (sym,))
        existing_normalized_titles = set(normalize_title(row[0]) for row in cursor.fetchall())

        # Alimentation massive multi-sources
        search_queries = [sym, f"{sym} stock", f"{sym} earnings", f"{sym} news", f"{sym} financial market"]
        for query_term in search_queries:
            try:
                url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query_term}&newsCount=150"
                res = requests.get(url, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    raw_news = res.json().get('news', [])
                    for item in raw_news:
                        title = item.get('title', 'Titre indisponible')
                        norm_title = normalize_title(title)
                        if norm_title in existing_normalized_titles:
                            continue
                        
                        pub_time = item.get('providerPublishTime', 0)
                        if pub_time:
                            pub_date = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                            try:
                                cursor.execute('''
                                    INSERT OR IGNORE INTO articles (symbol, headline, summary, url, source, published_at, timestamp, sentiment)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    sym,
                                    title,
                                    item.get('summary', ''),
                                    item.get('link', '#'),
                                    item.get('publisher', 'Yahoo Finance'),
                                    pub_date,
                                    pub_time,
                                    'Neutral'
                                ))
                                existing_normalized_titles.add(norm_title)
                            except Exception:
                                pass
            except Exception as e:
                print(f"Erreur source Yahoo ({query_term}) : {e}")

        # Google News RSS
        try:
            rss_url = f"https://news.google.com/rss/search?q={sym}+stock+market&hl=en-US&gl=US&ceid=US:en"
            res = requests.get(rss_url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                for item in items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    desc_elem = item.find('description')

                    title = title_elem.text if title_elem is not None else 'Titre indisponible'
                    norm_title = normalize_title(title)
                    if norm_title in existing_normalized_titles:
                        continue

                    url = link_elem.text if link_elem is not None else '#'
                    source = source_elem.text if source_elem is not None else 'Google News'
                    summary = desc_elem.text if desc_elem is not None else ''
                    summary = re.sub(r'<[^>]+>', '', summary)

                    pub_time = int(datetime.now().timestamp())
                    pub_date = datetime.now().strftime('%Y-%m-%d %H:%M')
                    if pub_elem is not None and pub_elem.text:
                        try:
                            dt_obj = parsedate_to_datetime(pub_elem.text)
                            pub_time = int(dt_obj.timestamp())
                            pub_date = dt_obj.strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            pass

                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO articles (symbol, headline, summary, url, source, published_at, timestamp, sentiment)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            sym,
                            title,
                            summary,
                            url,
                            source,
                            pub_date,
                            pub_time,
                            'Neutral'
                        ))
                        existing_normalized_titles.add(norm_title)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Erreur source Google RSS : {e}")

        conn.commit()

        # Restitution de TOUT l'historique sans restriction de période (géré par la pagination frontend)
        cursor.execute('''
            SELECT headline, summary, url, source, published_at, sentiment 
            FROM articles 
            WHERE symbol = ? 
            ORDER BY timestamp DESC
        ''', (sym,))

        rows = cursor.fetchall()
        conn.close()

        articles = []
        for row in rows:
            articles.append({
                "headline": row[0],
                "summary": row[1],
                "url": row[2],
                "source": row[3],
                "published_at": row[4],
                "sentiment": row[5]
            })

        return articles
    except Exception as e:
        print(f"Erreur agrégation news pour {symbol}: {str(e)}")
        return []

# Sert l'interface web compilée (frontend/dist) pour un déploiement en un seul service
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))