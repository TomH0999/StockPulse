"""Alertes : seuils de prix, changements de verdict et fortes baisses sur les favoris / lignes du PEA."""
import time
from datetime import date

import store
from services import portfolio, yahoo


def price_alerts() -> list[dict]:
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM price_alerts ORDER BY symbol")]


def add(symbol: str, direction: str, price: float):
    if direction not in ("above", "below") or price <= 0:
        raise ValueError("Alerte invalide")
    with store.connect() as conn:
        conn.execute("INSERT INTO price_alerts (symbol, direction, price) VALUES (?, ?, ?)", (symbol.upper(), direction, price))


def remove(alert_id: int):
    with store.connect() as conn:
        conn.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))


def _watched() -> list[str]:
    with store.connect() as conn:
        favs = [r[0] for r in conn.execute("SELECT symbol FROM favorites")]
    return sorted(set(favs) | set(portfolio.symbols()))


def events() -> list[dict]:
    """Événements en cours (non filtrés par l'historique des notifications)."""
    out = []
    active = [a for a in price_alerts() if not a["triggered_at"]]
    held = set(portfolio.symbols())
    syms = sorted({a["symbol"] for a in active} | held)
    quotes = {q["symbol"]: q for q in yahoo.quotes(syms)} if syms else {}
    today = date.today().isoformat()
    for a in active:
        p = (quotes.get(a["symbol"]) or {}).get("price")
        if p and ((a["direction"] == "above" and p >= a["price"]) or (a["direction"] == "below" and p <= a["price"])):
            with store.connect() as conn:
                conn.execute("UPDATE price_alerts SET triggered_at = ? WHERE id = ?", (int(time.time()), a["id"]))
            out.append({"key": f"price:{a['id']}", "type": "price", "symbol": a["symbol"], "direction": a["direction"],
                        "threshold": a["price"], "price": p})
    # Pas d'alerte sur les variations du jour ni sur les changements de verdict : une thèse long terme ne change pas
    # d'une heure à l'autre. Seules restent les alertes de prix choisies par l'utilisateur et les revues de thèse.
    from services import theses
    for t in theses.due():
        out.append({"key": f"thesis:{t['id']}:{t['next_review']}", "type": "thesis", "symbol": t["symbol"], "account": t["account"]})
    return out


def pending() -> list[dict]:
    """Nouveaux événements à notifier (une seule fois chacun)."""
    new = []
    with store.connect() as conn:
        done = {r[0] for r in conn.execute("SELECT key FROM notified")}
        for e in events():
            if e["key"] not in done:
                conn.execute("INSERT OR IGNORE INTO notified (key, at) VALUES (?, ?)", (e["key"], int(time.time())))
                new.append(e)
    return new
