"""Vérificateur d'état : chaque contrôle renvoie ok / warn / error avec un détail lisible."""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

import catalog
import store
from services import advisor, ai_pool, screener, yahoo
from services.yahoo import _session

APP_VERSION = os.environ.get("STOCKPULSE_VERSION", "dev")
RELEASES_URL = "https://api.github.com/repos/TomH0999/StockPulse/releases/latest"
RANK = {"ok": 0, "warn": 1, "error": 2}
_cache: dict = {}


def _check(id_, fn):
    try:
        status, detail = fn()
    except Exception as e:
        status, detail = "error", str(e)[:200]
    return {"id": id_, "status": status, "detail": detail}


def _quotes():
    q = yahoo.quote("AAPL")
    age_days = (time.time() - (q.get("market_time") or 0)) / 86400
    if age_days > 4:
        return "warn", f"Dernier cours vieux de {age_days:.0f} jours"
    return "ok", f"AAPL {q['price']} {q['currency']}"


def _snapshot():
    snap, updated = screener.snapshot(max_age=1800)
    total = len(catalog.symbols())
    missing = [s for s in catalog.symbols() if not (snap.get(s) or {}).get("price")]
    age = (time.time() - updated) / 60
    if len(missing) > total * 0.1:
        return "error", f"{len(missing)}/{total} entreprises sans cours"
    if missing:
        return "warn", f"Sans cours : {', '.join(missing[:8])}"
    return "ok", f"{total} entreprises, mis à jour il y a {age:.0f} min"


def _news():
    def probe(url):
        return _session.get(url, timeout=8).ok
    urls = {"Yahoo": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
            "Google News": "https://news.google.com/rss/search?q=Apple+stock&hl=en-US&gl=US&ceid=US:en"}
    with ThreadPoolExecutor(2) as pool:
        res = dict(zip(urls, pool.map(probe, urls.values())))
    down = [k for k, ok in res.items() if not ok]
    return ("error" if len(down) == len(res) else "warn" if down else "ok"), (f"Indisponible : {', '.join(down)}" if down else "Yahoo et Google News joignables")


def _ai():
    keys = ai_pool.public_keys()
    if not keys:
        return "warn", "Aucune clé IA : analyse locale uniquement"
    broken = [k["provider"] for k in keys if k["last_error"] and not k["ok"]]
    if len(broken) == len(keys):
        return "error", f"Toutes les clés échouent ({', '.join(broken)})"
    return ("warn" if broken else "ok"), f"{len(keys) - len(broken)}/{len(keys)} clés fonctionnelles"


def _database():
    with store.connect() as conn:
        res = conn.execute("PRAGMA quick_check").fetchone()[0]
        n = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    return ("ok", f"Intègre, {n} articles") if res == "ok" else ("error", f"Base endommagée : {res}")


def _freshness():
    cache = advisor.cached_verdicts()
    syms = catalog.symbols()
    fresh = sum(1 for s in syms if s in cache and time.time() - cache[s]["generated_at"] < 86400)
    ratio = fresh / len(syms)
    return ("ok" if ratio > 0.8 else "warn"), f"{fresh}/{len(syms)} analyses de moins de 24 h"


def _verification():
    with store.connect() as conn:
        rows = conn.execute("SELECT symbol, payload FROM advice_cache").fetchall()
    flagged = sorted({r[0] for r in rows if '"verification": {"status": "warning"' in r[1]})
    if flagged:
        return "warn", f"Analyses IA à vérifier : {', '.join(flagged[:10])}{'…' if len(flagged) > 10 else ''}"
    return "ok", "Aucune incohérence détectée dans les analyses IA"


def _version():
    if APP_VERSION == "dev":
        return "ok", "Version de développement"
    hit = _cache.get("release")
    if not hit or time.time() - hit[0] > 6 * 3600:
        hit = (time.time(), requests.get(RELEASES_URL, timeout=10).json().get("tag_name", ""))
        _cache["release"] = hit
    latest = hit[1].lstrip("v")
    if latest and tuple(map(int, latest.split("."))) > tuple(map(int, APP_VERSION.split("."))):
        return "warn", f"Version {latest} disponible (installée : {APP_VERSION})"
    return "ok", f"À jour ({APP_VERSION})"


CHECKS = {"quotes": _quotes, "snapshot": _snapshot, "news": _news, "ai": _ai, "database": _database,
          "freshness": _freshness, "verification": _verification, "version": _version}


def run(force: bool = False) -> dict:
    hit = _cache.get("report")
    if hit and not force and time.time() - hit["checked_at"] < 120:
        return hit
    with ThreadPoolExecutor(len(CHECKS)) as pool:
        results = list(pool.map(lambda kv: _check(*kv), CHECKS.items()))
    overall = max((r["status"] for r in results), key=RANK.get)
    report = {"overall": overall, "checks": results, "checked_at": int(time.time()), "version": APP_VERSION}
    _cache["report"] = report
    return report
