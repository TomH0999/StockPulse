"""Analyses IA enregistrées (simples ou groupées) et indice de renouvellement.

L'indice vaut 1 quand l'analyse doit être refaite : il combine son âge, la variation du cours depuis et le nombre
d'articles parus depuis. Au-delà de 0,7 elle est « à surveiller », au-delà de 1 « à renouveler »."""
import json
import time

import store

MAX_AGE_DAYS = {"single": 30, "ensemble": 45}   # une analyse groupée, plus robuste, vieillit moins vite
PRICE_MOVE = 10.0                               # % de variation qui rend l'analyse caduque
NEW_ARTICLES = 25                               # articles parus depuis qui rendent l'analyse caduque


def save(symbol: str, kind: str, result: dict, price: float | None, currency: str | None, lang: str, runs: int = 1) -> int:
    with store.connect() as conn:
        cur = conn.execute(
            "INSERT INTO ai_analyses (symbol, created_at, kind, runs, verdict, score, confidence, price, currency, engine, lang, payload)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol.upper(), int(time.time()), kind, runs, result.get("verdict"), result.get("score"), result.get("confidence"),
             price, currency, result.get("engine"), lang, json.dumps(result, ensure_ascii=False)))
        return cur.lastrowid


def renewal(row: dict, price: float | None, now: float | None = None) -> dict:
    now = now or time.time()
    age = (now - row["created_at"]) / 86400
    with store.connect() as conn:
        new_arts = conn.execute("SELECT COUNT(*) FROM articles WHERE symbol = ? AND timestamp > ?",
                                (row["symbol"], row["created_at"])).fetchone()[0]
    move = (price / row["price"] - 1) * 100 if price and row.get("price") else None
    parts = {"age": age / MAX_AGE_DAYS.get(row["kind"], 30), "price": abs(move or 0) / PRICE_MOVE, "news": new_arts / NEW_ARTICLES}
    index = round(max(parts.values()), 2)
    return {"index": index, "status": "renew" if index >= 1 else "watch" if index >= 0.7 else "ok",
            "reason": max(parts, key=parts.get), "age_days": round(age, 1),
            "price_move": round(move, 1) if move is not None else None, "new_articles": new_arts}


def list_for(symbol: str, price: float | None = None, limit: int = 50) -> list[dict]:
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM ai_analyses WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                                              (symbol.upper(), limit))]
    for r in rows:
        r["payload"] = json.loads(r["payload"])
        r["renewal"] = renewal(r, price)
    return rows


def delete(analysis_id: int):
    with store.connect() as conn:
        conn.execute("DELETE FROM ai_analyses WHERE id = ?", (analysis_id,))


# --- Précision mesurée de l'IA (score de Brier) -----------------------------------------------------------------------
# On ne peut pas tester l'IA sur le passé (le modèle connaît la suite) : seule la mesure en temps réel vaut. Chaque
# probabilité « battre son indice à 12 mois » enregistrée est comparée, à l'échéance, à ce qui s'est passé face à CW8.
BRIER_COIN = 0.25        # score d'une probabilité toujours égale à 50 %
MIN_BRIER_SAMPLES = 30   # avant : correction par défaut (moitié du chemin vers 50 %)
_brier_cache: dict = {}


def brier(now: float | None = None, fetch_hist=None) -> dict:
    """Score de Brier des probabilités de l'IA arrivées à échéance (plus bas = meilleur ; 0,25 = pile ou face)."""
    now = now or time.time()
    if _brier_cache.get("at", 0) > now - 3600 and fetch_hist is None:
        return _brier_cache["value"]
    if fetch_hist is None:
        from services import yahoo
        fetch_hist = yahoo.daily_history
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT symbol, created_at, price, payload FROM ai_analyses WHERE kind = 'single' AND created_at <= ?",
                                              (int(now - 365 * 86400),))]
    pairs = []
    try:
        world = fetch_hist("CW8.PA")
    except Exception:
        world = []
    from services.advisor import _series_at
    w_at = _series_at(world) if world else None
    for r in rows:
        p = ((json.loads(r["payload"]).get("outlook") or {}).get("prob_outperform"))
        if p is None or not r["price"] or not w_at:
            continue
        try:
            at = _series_at(fetch_hist(r["symbol"]))
        except Exception:
            continue
        s1, w0, w1 = at(r["created_at"] + 365 * 86400), w_at(r["created_at"]), w_at(r["created_at"] + 365 * 86400)
        if not (s1 and w0 and w1):
            continue
        outcome = 1.0 if s1 / r["price"] > w1 / w0 else 0.0
        pairs.append((p / 100, outcome))
    value = {"n": len(pairs), "brier": round(sum((p - o) ** 2 for p, o in pairs) / len(pairs), 4) if pairs else None,
             "coin": BRIER_COIN}
    _brier_cache.update(at=now, value=value)
    return value


def measured_shrink(default: float = 0.5) -> float:
    """Part de l'avis de l'IA conservée : réglée sur sa précision mesurée dès qu'il y a assez d'échéances."""
    b = brier()
    if not b["brier"] or b["n"] < MIN_BRIER_SAMPLES:
        return default
    skill = 1 - b["brier"] / BRIER_COIN  # 0 = pas mieux que pile ou face ; 1 = parfait
    return round(max(0.0, min(1.0, skill * 4)), 2)
