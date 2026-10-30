"""Dividendes : reçus (journal), à venir (estimés d'après l'historique de versement de chaque ligne) et rendement."""
import time
from datetime import date, datetime, timedelta, timezone

from services import fundamentals, fx, portfolio, yahoo


def _history(symbol: str) -> list[dict]:
    try:
        res = yahoo._session.get(yahoo.CHART_URL.format(sym=symbol), params={"range": "3y", "interval": "1mo", "events": "div"}, timeout=10)
        divs = ((res.json()["chart"]["result"] or [{}])[0].get("events") or {}).get("dividends") or {}
    except Exception:
        return []
    return sorted(({"date": datetime.fromtimestamp(d["date"], timezone.utc).date(), "amount": d["amount"]} for d in divs.values()),
                  key=lambda d: d["date"])


def calendar() -> dict:
    summary = portfolio.summary()
    received = [{"day": m["day"], "symbol": m["symbol"], "amount": m["amount"]} for m in portfolio.movements() if m["type"] == "dividend"]
    upcoming, trailing_income = [], 0.0
    today = date.today()
    for line in summary["lines"]:
        hist = _history(line["symbol"])
        rate = fx.rate(line["currency"]) or 1.0
        last_year = [d for d in hist if d["date"] >= today - timedelta(days=365)]
        trailing_income += sum(d["amount"] for d in last_year) * line["quantity"] * rate
        known = (fundamentals.get(line["symbol"], fetch=False) or {}).get("next_dividend")
        if known and known.get("date") and known["date"] >= today.isoformat():
            upcoming.append({"symbol": line["symbol"], "date": known["date"], "per_share": known.get("amount"),
                             "amount": round((known.get("amount") or 0) * line["quantity"] * rate, 2), "estimated": False})
            continue
        for d in last_year:  # même calendrier que l'an dernier
            nxt = d["date"] + timedelta(days=365)
            if today <= nxt <= today + timedelta(days=365):
                upcoming.append({"symbol": line["symbol"], "date": nxt.isoformat(), "per_share": d["amount"],
                                 "amount": round(d["amount"] * line["quantity"] * rate, 2), "estimated": True})
    upcoming.sort(key=lambda u: u["date"])
    value = summary["value"]
    return {"received": sorted(received, key=lambda r: r["day"], reverse=True), "upcoming": upcoming,
            "received_total": round(sum(r["amount"] for r in received), 2),
            "next_12m": round(sum(u["amount"] for u in upcoming), 2),
            "yield": round(trailing_income / value * 100, 2) if value else None, "computed_at": int(time.time())}
