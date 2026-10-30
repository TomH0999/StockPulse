"""Analyses automatiques en arrière-plan : analyse locale de tout le catalogue, puis analyse IA selon la capacité des clés."""
import threading
import time

import catalog
import store
from services import advisor, ai_pool, portfolio, screener

LOCAL_MAX_AGE = 6 * 3600
status = {"local_done": 0, "last_error": None}


def settings() -> dict:
    return {"enabled": store.get_setting("auto_enabled", "1") == "1"}


def _lang() -> str:
    return store.get_setting("ui_lang", "fr")


def _favorites() -> list[str]:
    """Lignes du PEA puis favoris : analysés en priorité."""
    with store.connect() as conn:
        favs = [r[0] for r in conn.execute("SELECT symbol FROM favorites ORDER BY position")]
    held = portfolio.symbols()
    return held + [s for s in favs if s not in held]


def _queue() -> list[str]:
    """Analyse locale à rafraîchir, par priorité : PEA et favoris, puis plus fortes variations du jour."""
    now = time.time()
    cache = advisor.cached_verdicts()
    snap, _ = screener.snapshot(max_age=3600)
    favs = _favorites()
    order = favs + sorted((s for s in catalog.core_symbols() if s not in favs), key=lambda s: -abs((snap.get(s) or {}).get("chg_1d") or 0))
    # une analyse IA (faite à la demande) est conservée tant qu'elle a moins d'un jour
    return [s for s in order if not (c := cache.get(s))
            or now - c["generated_at"] > (LOCAL_MAX_AGE if c["engine"] == "local" else 86400)]


def _local_loop():
    while True:
        try:
            if settings()["enabled"]:
                for s in _queue()[:20]:
                    advisor.advise(s, _lang(), force=True, use_ai=False, backfill=s in _favorites(), fetch_fundamentals=s in _favorites())
                    status["local_done"] += 1
                    time.sleep(1)
        except Exception as e:
            status["last_error"] = str(e)[:200]
        time.sleep(30)


def _snapshot_loop():
    while True:
        try:
            screener.refresh()
        except Exception as e:
            status["last_error"] = str(e)[:200]
        time.sleep(screener.REFRESH_SECONDS)


def _catalog_loop():
    """Mise à jour quotidienne du catalogue (sources publiques, aucun jeton IA)."""
    time.sleep(120)
    while True:
        try:
            if catalog.needs_update():
                status["catalog"] = catalog.refresh_from_sources()
        except Exception as e:
            status["last_error"] = f"Catalogue : {str(e)[:150]}"
        time.sleep(3600)


def start():
    # Analyse IA uniquement à la demande de l'utilisateur (quotas gratuits) : pas de boucle IA automatique
    for target in (_snapshot_loop, _local_loop, _catalog_loop):
        threading.Thread(target=target, daemon=True).start()


def progress() -> dict:
    cache = advisor.cached_verdicts()
    core = set(catalog.core_symbols()) | set(_favorites())
    total = len(core)
    analysed = sum(1 for s in core if s in cache)
    return {**settings(), **status, "total": total, "analysed": analysed,
            "keys_available": ai_pool.available_count(), "keys": len(ai_pool.keys())}
