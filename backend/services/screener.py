"""Instantané de marché pour tout le catalogue (requêtes groupées Yahoo « spark »), base du classement."""
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import catalog
from services.yahoo import _session

REFRESH_SECONDS = 600
_lock = threading.Lock()
_snapshot: dict[str, dict] = {}
_updated = 0.0


def _batch(symbols: list[str]) -> list[dict]:
    res = _session.get("https://query1.finance.yahoo.com/v7/finance/spark",
                       params={"symbols": ",".join(symbols), "range": "1y", "interval": "1d"}, timeout=20)
    res.raise_for_status()
    out = []
    for item in res.json().get("spark", {}).get("result") or []:
        try:
            r = item["response"][0]
            meta = r["meta"]
            pairs = [(t, c) for t, c in zip(r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or []) if c]
            out.append(_metrics(item["symbol"], meta, pairs))
        except (KeyError, IndexError, TypeError, ZeroDivisionError):
            continue
    return out


def _metrics(sym, meta, pairs):
    price = meta.get("regularMarketPrice") or (pairs[-1][1] if pairs else 0)
    closes = [c for _, c in pairs]

    def back(days):
        cutoff = time.time() - days * 86400
        old = next((c for t, c in pairs if t >= cutoff), None)
        return round((price / old - 1) * 100, 2) if old else None

    year_start = datetime(datetime.now().year, 1, 1, tzinfo=timezone.utc).timestamp()
    ytd_base = next((c for t, c in pairs if t >= year_start), None)
    rets = [b / a - 1 for a, b in zip(closes[-64:-1], closes[-63:]) if a]
    high, low = meta.get("fiftyTwoWeekHigh") or max(closes or [price]), meta.get("fiftyTwoWeekLow") or min(closes or [price])
    return {
        "symbol": sym, "currency": meta.get("currency", ""), "price": price,
        "chg_1d": round(meta.get("regularMarketChangePercent") or 0, 2),
        "chg_1w": back(7), "chg_1m": back(30), "chg_3m": back(91), "chg_6m": back(182), "chg_1y": back(365),
        "chg_ytd": round((price / ytd_base - 1) * 100, 2) if ytd_base else None,
        "volatility": round(statistics.pstdev(rets) * (252 ** 0.5) * 100, 1) if len(rets) > 20 else None,
        "from_high": round((price / high - 1) * 100, 2) if high else None,
        "range_pos": round((price - low) / (high - low) * 100, 1) if high > low else None,
        "spark": [round(c, 4) for c in closes[-60:]],
        "market_time": meta.get("regularMarketTime"),
    }


def refresh():
    global _updated
    syms = catalog.symbols()
    batches = [syms[i:i + 20] for i in range(0, len(syms), 20)]
    rows = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in [pool.submit(_batch, b) for b in batches]:
            try:
                rows.update({r["symbol"]: r for r in fut.result()})
            except Exception as e:
                print(f"Instantané de marché partiel : {e}")
    with _lock:
        _snapshot.update(rows)
        _updated = time.time()


def snapshot(max_age: int = REFRESH_SECONDS) -> tuple[dict[str, dict], float]:
    if time.time() - _updated > max_age:
        refresh()
    return _snapshot, _updated
