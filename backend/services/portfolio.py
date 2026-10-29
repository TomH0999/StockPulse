"""Mon PEA : lignes détenues, valorisation en direct, conseil et alertes par ligne, plafond de versements."""
import catalog
import store
from services import advisor, yahoo

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
