"""Générateur d'ordres : prépare l'ordre à saisir chez le courtier (achat, renforcement, allègement, vente),
puis met à jour Mon PEA une fois l'ordre passé."""
import math

import catalog
import store
from services import advisor, portfolio, screener, yahoo

MAX_LINE = 20  # % maximum d'une ligne dans le PEA


def fees_settings() -> dict:
    return {"pct": float(store.get_setting("fee_pct", "0.5")), "min": float(store.get_setting("fee_min", "1.99"))}


def set_fees(pct: float, minimum: float):
    if not (0 <= pct <= 5 and 0 <= minimum <= 50):
        raise ValueError("Frais invalides")
    store.set_setting("fee_pct", str(pct))
    store.set_setting("fee_min", str(minimum))


def fee(amount: float) -> float:
    f = fees_settings()
    return round(max(f["min"], amount * f["pct"] / 100), 2) if amount > 0 else 0.0


def _tick(price: float) -> float:
    return 0.0001 if price < 1 else 0.001 if price < 10 else 0.01 if price < 100 else 0.05


def _round(price: float, up: bool) -> float:
    t = _tick(price)
    return round((math.ceil if up else math.floor)(price / t) * t, 4)


def plan(symbol: str, side: str, amount: float | None = None, quantity: float | None = None) -> dict:
    sym = symbol.upper()
    quantity_req = quantity
    if side not in ("buy", "sell", "reduce"):
        raise ValueError("Sens d'ordre inconnu")
    q = yahoo.quote(sym)
    price = q["price"]
    if not price:
        raise ValueError("Pas de cours disponible")
    info = next((e for e in catalog.entries() if e["symbol"] == sym), {})
    pf = portfolio.summary()
    line = next((l for l in pf["lines"] if l["symbol"] == sym), None)
    held = sum(l["quantity"] for l in pf["lines"] if l["symbol"] == sym)
    adv = advisor.cached_verdicts().get(sym)
    vol = (screener.snapshot(max_age=86400)[0].get(sym) or {}).get("volatility") or 30.0
    move = min(0.20, max(0.05, 1.5 * vol / 100 / math.sqrt(12)))  # 1,5 écart-type mensuel, borné 5-20 %
    warnings = []
    if info.get("status"):
        warnings.append(f"status_{info['status']}")
    if q.get("currency") != "EUR":
        warnings.append("currency")

    if side == "buy":
        if not info.get("pea", False):
            warnings.append("not_pea")
        if adv and adv["verdict"] not in ("BUY", "STRONG_BUY"):
            warnings.append(f"verdict_{adv['verdict'].lower()}")
        if amount is None:
            # une ligne ne doit pas dépasser 20 % du PEA (titres + liquidités), y compris pour un PEA tout juste ouvert
            room = max(0.0, MAX_LINE / 100 * pf["total"] - (line["value"] if line else 0))
            amount = min(pf["cash"], room) if pf["cash"] else room
            if not pf["total"]:
                amount = 1000.0
                warnings.append("no_cash_data")
        if pf["cash"] and amount > pf["cash"]:
            warnings.append("cash_insufficient")
        limit = _round(price * 1.003, up=True)
        quantity = max(0, math.floor((amount - fee(amount)) / limit))
        if quantity == 0:
            warnings.append("amount_too_small")
        gross = round(quantity * limit, 2)
        after = ((line["value"] if line else 0) + gross) / max(pf["total"] or gross, 1) * 100
        if after > MAX_LINE:
            warnings.append("line_heavy")
        return {"symbol": sym, "side": side, "name": q["name"], "isin": info.get("isin"), "price": price, "currency": q["currency"],
                "quantity": quantity, "limit": limit, "amount": gross, "fees": fee(gross), "total": round(gross + fee(gross), 2),
                "stop_loss": _round(price * (1 - move), up=False), "target": _round(price * (1 + 2 * move), up=True),
                "weight_after": round(after, 1), "advice": adv, "warnings": warnings, "fees_settings": fees_settings()}

    if not held:
        raise ValueError("Vous ne détenez pas cette valeur dans Mon PEA")
    if side == "sell":
        quantity = held
    else:
        target_qty = held * MAX_LINE / line["weight"] if line and line.get("weight") and line["weight"] > MAX_LINE else held / 2
        quantity = max(1, math.floor(held - target_qty) if line and (line.get("weight") or 0) > MAX_LINE else math.floor(held / 2))
    if quantity_override := quantity_req:
        quantity = quantity_override
    quantity = min(quantity, held)
    if adv and adv["verdict"] in ("BUY", "STRONG_BUY"):
        warnings.append(f"verdict_{adv['verdict'].lower()}")
    limit = _round(price * 0.997, up=False)
    gross = round(quantity * limit, 2)
    pru = line["avg_price"] if line else price
    return {"symbol": sym, "side": side, "name": q["name"], "isin": info.get("isin"), "price": price, "currency": q["currency"],
            "quantity": quantity, "held": held, "limit": limit, "amount": gross, "fees": fee(gross), "total": round(gross - fee(gross), 2),
            "realized_pnl": round((limit - pru) * quantity - fee(gross), 2), "avg_price": pru,
            "advice": adv, "warnings": warnings, "fees_settings": fees_settings()}


def execute(symbol: str, side: str, quantity: float, price: float, fees: float) -> dict:
    """Enregistre un ordre exécuté : met à jour la ligne (quantité, prix de revient) et les liquidités."""
    sym = symbol.upper()
    if quantity <= 0 or price <= 0 or fees < 0:
        raise ValueError("Quantité, prix et frais doivent être positifs")
    lines = [l for l in portfolio.lines() if l["symbol"] == sym]
    held = sum(l["quantity"] for l in lines)
    cost = held and sum(l["quantity"] * l["avg_price"] for l in lines) / held
    cash = float(store.get_setting("pea_cash", "0") or 0)
    with store.connect() as conn:
        for l in lines[1:]:
            conn.execute("DELETE FROM holdings WHERE id = ?", (l["id"],))
    if side == "buy":
        new_qty = held + quantity
        new_pru = (held * cost + quantity * price + fees) / new_qty
        portfolio.upsert(sym, new_qty, round(new_pru, 4), lines[0]["id"] if lines else None)
        cash = max(0.0, cash - quantity * price - fees)
    elif side in ("sell", "reduce"):
        if quantity > held + 1e-9:
            raise ValueError(f"Quantité supérieure à la position détenue ({held})")
        remaining = held - quantity
        if remaining <= 1e-9:
            portfolio.delete(lines[0]["id"])
        else:
            portfolio.upsert(sym, remaining, cost, lines[0]["id"])
        cash += quantity * price - fees
    else:
        raise ValueError("Sens d'ordre inconnu")
    store.set_setting("pea_cash", str(round(cash, 2)))
    with store.connect() as conn:
        conn.execute("INSERT INTO orders_log (symbol, side, quantity, price, fees) VALUES (?, ?, ?, ?, ?)", (sym, side, quantity, price, fees))
    return portfolio.summary()


def journal() -> list[dict]:
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM orders_log ORDER BY at DESC LIMIT 200")]
