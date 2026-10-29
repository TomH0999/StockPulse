import json
import os
import sys
import threading

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import catalog
import store
from services import advisor, ai_pool, alerts, health, news, portfolio, scheduler, screener, yahoo

store.init()
threading.Thread(target=news.migrate, daemon=True).start()
scheduler.start()

app = FastAPI(title="StockPulse Backend", version="1.0.0")
# API réservée à l'application : seule l'interface de développement Vite peut l'appeler depuis une autre origine,
# et l'en-tête Host est vérifié (protection contre le « DNS rebinding » depuis un site web malveillant)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.environ.get("STOCKPULSE_FRONTEND") or os.path.join(BASE_DIR, "..", "frontend", "dist")


def _yahoo(fn, *args):
    try:
        return fn(*args)
    except yahoo.YahooError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, f"Source de données indisponible : {e}")


@app.get("/api/health")
def ping():
    return {"status": "ok"}


@app.get("/api/health/full")
def health_full(refresh: bool = False):
    return health.run(refresh)


@app.get("/api/market/quote/{symbol}")
def get_quote(symbol: str):
    return _yahoo(yahoo.quote, symbol)


@app.get("/api/market/quotes")
def get_quotes(symbols: str):
    return yahoo.quotes([s for s in symbols.split(",") if s.strip()][:50])


@app.get("/api/market/history/{symbol}")
def get_history(symbol: str, period: str = Query("1y")):
    return {"symbol": symbol.upper(), "period": period, "data": _yahoo(yahoo.history, symbol, period)}


@app.get("/api/market/search")
def search(q: str):
    return _yahoo(yahoo.search, q)


@app.get("/api/market/news/{symbol}")
def get_news(symbol: str, refresh: bool = False):
    sym = symbol.upper()
    try:
        name = yahoo.quote(sym).get("name", "")
    except Exception:
        name = ""
    news.refresh(sym, name, force=refresh)
    return {"symbol": sym, "backfilling": news.is_backfilling(sym), "articles": news.articles(sym)}


@app.get("/api/advice/{symbol}")
def get_advice(symbol: str, lang: str = "fr", refresh: bool = False, ai: bool = True):
    if store.get_setting("ui_lang") != lang:
        store.set_setting("ui_lang", lang)
    return _yahoo(advisor.advise, symbol, lang, refresh, ai)


@app.get("/api/advice/{symbol}/history")
def get_advice_history(symbol: str):
    return advisor.history_log(symbol.upper())


@app.get("/api/track-record")
def track_record():
    """Fiabilité moyenne des conseils (analyse locale rejouée sur 5 ans) sur toutes les valeurs analysées."""
    agg = {}
    with store.connect() as conn:
        for (payload,) in conn.execute("SELECT payload FROM advice_cache"):
            tr = json.loads(payload).get("track_record") or {}
            for h, v in tr.items():
                a = agg.setdefault(h, {"n": 0, "hits": 0, "symbols": 0})
                if v["n"] and v["hit_rate"] is not None:
                    a["n"] += v["n"]
                    a["hits"] += v["hit_rate"] * v["n"] / 100
                    a["symbols"] += 1
    return {h: {"symbols": a["symbols"], "n": a["n"], "hit_rate": round(a["hits"] / a["n"] * 100) if a["n"] else None} for h, a in agg.items()}


@app.get("/api/alerts")
def get_alerts():
    return {"price_alerts": alerts.price_alerts(), "events": alerts.events()}


@app.get("/api/alerts/pending")
def pending_alerts():
    return alerts.pending()


@app.post("/api/alerts")
def add_alert(symbol: str = Body(...), direction: str = Body(...), price: float = Body(...)):
    try:
        alerts.add(symbol, direction, price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return alerts.price_alerts()


@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int):
    alerts.remove(alert_id)
    return alerts.price_alerts()


@app.get("/api/catalog")
def get_catalog():
    return catalog.entries()


@app.get("/api/screener")
def get_screener():
    """Toutes les entreprises du catalogue avec performances, volatilité et dernier conseil (classement, liste)."""
    snap, updated = screener.snapshot()
    cache = advisor.cached_verdicts()
    rows = [{**e, **snap.get(e["symbol"], {}), "advice": cache.get(e["symbol"])} for e in catalog.entries()]
    return {"updated": int(updated), "rows": rows}


@app.get("/api/favorites")
def get_favorites():
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT symbol, name FROM favorites ORDER BY position, added_at")]
    verdicts = advisor.cached_verdicts()
    for r in rows:
        r["advice"] = verdicts.get(r["symbol"])
    return rows


@app.post("/api/favorites")
def add_favorite(symbol: str = Body(...), name: str = Body("")):
    with store.connect() as conn:
        pos = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM favorites").fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO favorites (symbol, name, position) VALUES (?, ?, ?)", (symbol.upper(), name, pos))
    return get_favorites()


@app.delete("/api/favorites/{symbol}")
def remove_favorite(symbol: str):
    with store.connect() as conn:
        conn.execute("DELETE FROM favorites WHERE symbol = ?", (symbol.upper(),))
    return get_favorites()


@app.put("/api/favorites/order")
def reorder_favorites(symbols: list[str] = Body(...)):
    with store.connect() as conn:
        for i, s in enumerate(symbols):
            conn.execute("UPDATE favorites SET position = ? WHERE symbol = ?", (i, s.upper()))
    return get_favorites()


@app.get("/api/portfolio")
def get_portfolio():
    return portfolio.summary()


@app.get("/api/portfolio/analysis")
def portfolio_analysis(period: str = "1y"):
    return {"diversification": portfolio.diversification(portfolio.summary()), "benchmark": portfolio.benchmark(period)}


@app.post("/api/portfolio/lines")
def add_line(symbol: str = Body(...), quantity: float = Body(...), avg_price: float = Body(...)):
    _yahoo(yahoo.quote, symbol)  # refuse un symbole inconnu
    try:
        portfolio.upsert(symbol, quantity, avg_price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return portfolio.summary()


@app.put("/api/portfolio/lines/{line_id}")
def edit_line(line_id: int, symbol: str = Body(...), quantity: float = Body(...), avg_price: float = Body(...)):
    try:
        portfolio.upsert(symbol, quantity, avg_price, line_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return portfolio.summary()


@app.delete("/api/portfolio/lines/{line_id}")
def delete_line(line_id: int):
    portfolio.delete(line_id)
    return portfolio.summary()


@app.put("/api/portfolio/account")
def set_account(deposits: float = Body(...), cash: float = Body(...)):
    try:
        portfolio.set_account(deposits, cash)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return portfolio.summary()


@app.get("/api/settings/ai")
def get_ai_settings():
    return {"providers": list(ai_pool.PROVIDERS), "keys": ai_pool.public_keys(), "auto": scheduler.progress()}


@app.post("/api/settings/ai/keys")
def add_ai_key(provider: str = Body(...), key: str = Body(...)):
    try:
        ai_pool.add_key(provider, key)
    except Exception as e:
        raise HTTPException(400, f"Clé refusée par {provider} : {str(e)[:200]}")
    return get_ai_settings()


@app.delete("/api/settings/ai/keys/{key_id}")
def remove_ai_key(key_id: str):
    ai_pool.remove_key(key_id)
    return get_ai_settings()


@app.put("/api/settings/auto")
def set_auto(enabled: bool = Body(...), ai_hours: float = Body(12)):
    store.set_setting("auto_enabled", "1" if enabled else "0")
    store.set_setting("auto_ai_hours", str(max(1.0, min(168.0, ai_hours))))
    return get_ai_settings()


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
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
