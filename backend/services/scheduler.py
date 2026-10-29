"""Analyses automatiques en arrière-plan : analyse locale de tout le catalogue, puis analyse IA selon la capacité des clés."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import catalog
import store
from services import advisor, ai_pool, portfolio, screener

LOCAL_MAX_AGE = 6 * 3600
status = {"local_done": 0, "ai_done": 0, "ai_running": 0, "last_error": None}


def settings() -> dict:
    return {"enabled": store.get_setting("auto_enabled", "1") == "1",
            "ai_hours": float(store.get_setting("auto_ai_hours", "12"))}


def _lang() -> str:
    return store.get_setting("ui_lang", "fr")


def _favorites() -> list[str]:
    """Lignes du PEA puis favoris : analysés en priorité."""
    with store.connect() as conn:
        favs = [r[0] for r in conn.execute("SELECT symbol FROM favorites ORDER BY position")]
    held = portfolio.symbols()
    return held + [s for s in favs if s not in held]


def _queue(ai: bool) -> list[str]:
    """Symboles à analyser, par priorité : favoris, puis plus fortes variations du jour, puis le reste."""
    now = time.time()
    cache = advisor.cached_verdicts()
    snap, _ = screener.snapshot(max_age=3600)
    favs = _favorites()
    order = favs + sorted((s for s in catalog.core_symbols() if s not in favs), key=lambda s: -abs((snap.get(s) or {}).get("chg_1d") or 0))
    max_ai_age = settings()["ai_hours"] * 3600
    out = []
    for s in order:
        c = cache.get(s)
        if ai:
            if not c or c["engine"] == "local" or now - c["generated_at"] > max_ai_age:
                out.append(s)
        elif not c or (c["engine"] == "local" and now - c["generated_at"] > LOCAL_MAX_AGE):
            out.append(s)
    return out


def _local_loop():
    while True:
        try:
            if settings()["enabled"]:
                for s in _queue(ai=False)[:20]:
                    advisor.advise(s, _lang(), force=True, use_ai=False, backfill=s in _favorites())
                    status["local_done"] += 1
                    time.sleep(1)
        except Exception as e:
            status["last_error"] = str(e)[:200]
        time.sleep(30)


def _ai_one(sym: str) -> bool:
    status["ai_running"] += 1
    try:
        r = advisor.advise(sym, _lang(), force=True, use_ai=True, max_wait=0, backfill=False)
        if r["engine"] != "local":
            status["ai_done"] += 1
            return True
        status["last_error"] = r.get("ai_error")
        return False
    finally:
        status["ai_running"] -= 1


def _ai_loop():
    while True:
        try:
            workers = ai_pool.available_count()
            if settings()["enabled"] and workers:
                batch = _queue(ai=True)[:workers]
                if batch:
                    with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                        if any(pool.map(_ai_one, batch)):
                            continue
        except Exception as e:
            status["last_error"] = str(e)[:200]
        time.sleep(20)


def _snapshot_loop():
    while True:
        try:
            screener.refresh()
        except Exception as e:
            status["last_error"] = str(e)[:200]
        time.sleep(screener.REFRESH_SECONDS)


def start():
    for target in (_snapshot_loop, _local_loop, _ai_loop):
        threading.Thread(target=target, daemon=True).start()


def progress() -> dict:
    cache = advisor.cached_verdicts()
    core = set(catalog.core_symbols()) | set(_favorites())
    total = len(core)
    analysed = sum(1 for s in core if s in cache)
    ai = sum(1 for s in core if s in cache and cache[s]["engine"] != "local")
    return {**settings(), **status, "total": total, "analysed": analysed, "ai_analysed": ai,
            "keys_available": ai_pool.available_count(), "keys": len(ai_pool.keys())}
