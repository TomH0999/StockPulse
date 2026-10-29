import os
import sys
import threading

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import store
from services import advisor, news, yahoo

store.init()
threading.Thread(target=news.migrate, daemon=True).start()

app = FastAPI(title="StockPulse Backend", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
def health():
    return {"status": "ok"}


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
    return _yahoo(advisor.advise, symbol, lang, refresh, ai)


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


@app.get("/api/settings/ai")
def get_ai_settings():
    provider, key = advisor.ai_settings()
    return {"provider": provider, "has_key": bool(key), "key_hint": f"…{key[-4:]}" if key else ""}


@app.put("/api/settings/ai")
def set_ai_settings(provider: str = Body(...), key: str = Body("")):
    if provider not in ("local", "gemini", "groq"):
        raise HTTPException(400, "Fournisseur inconnu")
    if provider != "local":
        key = key.strip() or advisor.ai_settings()[1]
        try:
            advisor.test_ai(provider, key)
        except Exception as e:
            raise HTTPException(400, f"Clé refusée par {provider} : {str(e)[:200]}")
    store.set_setting("ai_provider", provider)
    if key:
        store.set_setting("ai_key", key)
    with store.connect() as conn:
        conn.execute("DELETE FROM advice_cache")
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
