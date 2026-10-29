import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"

_session = requests.Session()
_session.headers.update(HEADERS)
_cache: dict = {}


class YahooError(Exception):
    pass


def _num(val, default=0.0) -> float:
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _chart(sym: str, rng: str, interval: str, ttl: int) -> dict:
    key = (sym, rng, interval)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    res = _session.get(CHART_URL.format(sym=sym), params={"range": rng, "interval": interval}, timeout=10)
    result = (res.json().get("chart", {}).get("result") or [None])[0] if res.ok else None
    if not result:
        raise YahooError(f"Symbole '{sym}' introuvable")
    _cache[key] = (time.time(), result)
    return result


def quote(symbol: str) -> dict:
    sym = symbol.upper().strip()
    meta = _chart(sym, "1d", "1d", 4)["meta"]
    price = _num(meta.get("regularMarketPrice"))
    prev = _num(meta.get("chartPreviousClose") or meta.get("previousClose"), price)
    change = price - prev
    return {
        "symbol": sym,
        "name": meta.get("longName") or meta.get("shortName") or sym,
        "short_name": meta.get("shortName") or sym,
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "",
        "price": round(price, 4),
        "change": round(change, 4),
        "change_percent": round(change / prev * 100, 2) if prev else 0.0,
        "volume": int(_num(meta.get("regularMarketVolume"))),
        "day_high": _num(meta.get("regularMarketDayHigh")),
        "day_low": _num(meta.get("regularMarketDayLow")),
        "year_high": _num(meta.get("fiftyTwoWeekHigh")),
        "year_low": _num(meta.get("fiftyTwoWeekLow")),
        "market_time": meta.get("regularMarketTime"),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def quotes(symbols: list[str]) -> list[dict]:
    def safe(s):
        try:
            return quote(s)
        except Exception:
            return {"symbol": s.upper(), "error": True}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(safe, symbols))


PERIODS = {
    "1d": ("1d", "5m"), "1w": ("5d", "30m"), "1mo": ("1mo", "1d"), "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"), "1y": ("1y", "1d"), "5y": ("5y", "1wk"), "max": ("max", "1mo"),
}


def history(symbol: str, period: str = "1y", ttl: int = 60) -> list[dict]:
    rng, interval = PERIODS.get(period.lower(), PERIODS["1y"])
    return _history(symbol, rng, interval, ttl)


def _history(symbol: str, rng: str, interval: str, ttl: int) -> list[dict]:
    result = _chart(symbol.upper().strip(), rng, interval, ttl)
    q = (result.get("indicators", {}).get("quote") or [{}])[0]
    points = []
    for i, ts in enumerate(result.get("timestamp") or []):
        close = q.get("close", [None])[i] if i < len(q.get("close", [])) else None
        if close is None:
            continue
        points.append({
            "timestamp": datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z"),
            "ts": ts,
            "open": _num(q["open"][i], close), "high": _num(q["high"][i], close),
            "low": _num(q["low"][i], close), "close": _num(close),
            "volume": int(_num(q["volume"][i])),
        })
    return points


def daily_history(symbol: str, years: int = 10) -> list[dict]:
    """Historique quotidien long, utilisé par l'analyse (rebondissements, tendances)."""
    return _history(symbol, f"{years}y", "1d", 3600)


def search(query: str) -> list[dict]:
    res = _session.get("https://query1.finance.yahoo.com/v1/finance/search",
                       params={"q": query, "quotesCount": 10, "newsCount": 0}, timeout=8)
    if not res.ok:
        return []
    return [
        {"symbol": q["symbol"], "name": q.get("longname") or q.get("shortname") or q["symbol"],
         "exchange": q.get("exchDisp", ""), "type": q.get("quoteType", "")}
        for q in res.json().get("quotes", [])
        if q.get("symbol") and q.get("quoteType") in ("EQUITY", "ETF", "INDEX", "MUTUALFUND", "CRYPTOCURRENCY", "FUTURE", "CURRENCY")
    ]


def dividend_yield(symbol: str, price: float | None) -> float | None:
    """Rendement du dividende sur 12 mois glissants, à partir de l'historique des versements."""
    if not price:
        return None
    try:
        res = _session.get(CHART_URL.format(sym=symbol.upper()), params={"range": "2y", "interval": "1mo", "events": "div"}, timeout=10)
        divs = ((res.json()["chart"]["result"] or [{}])[0].get("events") or {}).get("dividends") or {}
    except Exception:
        return None
    cutoff = time.time() - 365 * 86400
    total = sum(d["amount"] for d in divs.values() if d.get("date", 0) >= cutoff)
    return round(total / price * 100, 2) if total else None
