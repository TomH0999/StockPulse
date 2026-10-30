"""Mon PEA : lignes détenues, valorisation en direct, conseil et alertes par ligne, plafond de versements."""
import catalog
import store
from services import advisor, rebalance, yahoo

PEA_CEILING = 150_000


def lines() -> list[dict]:
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT id, symbol, quantity, avg_price FROM holdings ORDER BY symbol")]


def symbols() -> list[str]:
    return sorted({l["symbol"] for l in lines()})


def upsert(symbol: str, quantity: float, avg_price: float, line_id: int | None = None):
    if quantity <= 0 or avg_price <= 0:
        raise ValueError("Quantité et prix de revient doivent être positifs")
    with store.connect() as conn:
        if line_id:
            conn.execute("UPDATE holdings SET symbol = ?, quantity = ?, avg_price = ? WHERE id = ?", (symbol.upper(), quantity, avg_price, line_id))
        else:
            conn.execute("INSERT INTO holdings (symbol, quantity, avg_price) VALUES (?, ?, ?)", (symbol.upper(), quantity, avg_price))


def delete(line_id: int):
    with store.connect() as conn:
        conn.execute("DELETE FROM holdings WHERE id = ?", (line_id,))


def summary() -> dict:
    rows = lines()
    quotes = {q["symbol"]: q for q in yahoo.quotes([r["symbol"] for r in rows])} if rows else {}
    verdicts = advisor.cached_verdicts()
    info = {e["symbol"]: e for e in catalog.entries()}
    out, total_value, total_cost, day_change = [], 0.0, 0.0, 0.0
    for r in rows:
        q = quotes.get(r["symbol"], {})
        price = q.get("price") or 0
        cost = r["quantity"] * r["avg_price"]
        value = r["quantity"] * price
        adv = verdicts.get(r["symbol"])
        eligible = info.get(r["symbol"], {}).get("pea", r["symbol"].rsplit(".", 1)[-1] in ("PA", "DE", "AS", "MC", "MI", "BR", "LS", "IR", "HE", "ST", "CO"))
        alerts = []
        if adv and adv["verdict"] in ("REDUCE", "SELL"):
            alerts.append(f"verdict_{adv['verdict'].lower()}")
        if (q.get("change_percent") or 0) <= -5:
            alerts.append("big_drop")
        if cost and value / cost - 1 <= -0.15:
            alerts.append("loss_15")
        if not eligible:
            alerts.append("not_pea")
        if q.get("error") or not price:
            alerts.append("no_quote")
        same_ccy = q.get("currency", "EUR") == "EUR"
        if same_ccy:
            total_value += value
            total_cost += cost
            day_change += r["quantity"] * (q.get("change") or 0)
        out.append({**r, "name": q.get("short_name") or info.get(r["symbol"], {}).get("name", r["symbol"]),
                    "currency": q.get("currency", "EUR"), "price": price, "change_percent": q.get("change_percent"),
                    "value": round(value, 2), "cost": round(cost, 2), "pnl": round(value - cost, 2),
                    "pnl_percent": round((value / cost - 1) * 100, 2) if cost else 0, "advice": adv, "alerts": alerts,
                    "in_total": same_ccy})
    for l in out:
        l["weight"] = round(l["value"] / total_value * 100, 1) if total_value and l["in_total"] else None
    deposits = float(store.get_setting("pea_deposits", "0") or 0)
    cash = float(store.get_setting("pea_cash", "0") or 0)
    return {
        "lines": out, "value": round(total_value, 2), "cost": round(total_cost, 2), "pnl": round(total_value - total_cost, 2),
        "pnl_percent": round((total_value / total_cost - 1) * 100, 2) if total_cost else 0,
        "day_change": round(day_change, 2), "cash": cash, "deposits": deposits, "ceiling": PEA_CEILING,
        "total": round(total_value + cash, 2),
        "performance": round((total_value + cash - deposits) / deposits * 100, 2) if deposits else None,
    }


def set_account(deposits: float, cash: float):
    if deposits < 0 or cash < 0:
        raise ValueError("Montants négatifs")
    store.set_setting("pea_deposits", str(deposits))
    store.set_setting("pea_cash", str(cash))


MAX_LINE, MAX_SECTOR, MIN_LINES = 20, 35, 5


def diversification(summary: dict) -> dict:
    """Répartition par secteur / pays, risques de concentration et suggestions de rééquilibrage."""
    info = {e["symbol"]: e for e in catalog.entries()}
    lines = [l for l in summary["lines"] if l["weight"]]
    sectors, countries = {}, {}
    for l in lines:
        e = info.get(l["symbol"], {})
        sectors[e.get("sector") or "?"] = sectors.get(e.get("sector") or "?", 0) + l["weight"]
        countries[e.get("country") or "?"] = countries.get(e.get("country") or "?", 0) + l["weight"]
    warnings = []
    if 0 < len(lines) < MIN_LINES:
        warnings.append({"code": "few_lines", "n": len(lines)})
    for l in lines:
        if l["weight"] > MAX_LINE and l["price"]:
            warnings.append({"code": "line_heavy", "symbol": l["symbol"], "weight": l["weight"]})
    for sec, w in sectors.items():
        if w > MAX_SECTOR and sec != "?":
            warnings.append({"code": "sector_heavy", "sector": sec, "weight": round(w, 1)})
    return {"sectors": {k: round(v, 1) for k, v in sorted(sectors.items(), key=lambda kv: -kv[1])},
            "countries": {k: round(v, 1) for k, v in sorted(countries.items(), key=lambda kv: -kv[1])},
            "warnings": warnings, "rebalance": rebalance.plan(summary)}


def benchmark(period: str = "1y", index: str = "^FCHI") -> dict:
    """Portefeuille actuel rejoué sur la période, comparé à l'indice (base 100)."""
    rows = [l for l in lines()]
    if not rows:
        return {"series": [], "index": index}
    series = {r["symbol"]: {p["timestamp"][:10]: p["close"] for p in yahoo.history(r["symbol"], period, ttl=3600)} for r in rows}
    idx = {p["timestamp"][:10]: p["close"] for p in yahoo.history(index, period, ttl=3600)}
    days = sorted(d for d in idx if all(d in s for s in series.values()))
    if not days:
        return {"series": [], "index": index}
    qty = {}
    for r in rows:
        qty[r["symbol"]] = qty.get(r["symbol"], 0) + r["quantity"]
    values = [sum(qty[s] * series[s][d] for s in qty) for d in days]
    return {"index": index, "series": [{"day": d, "portfolio": round(v / values[0] * 100, 2), "index": round(idx[d] / idx[days[0]] * 100, 2)}
                                       for d, v in zip(days, values)]}
