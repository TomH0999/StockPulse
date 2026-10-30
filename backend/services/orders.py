"""Générateur d'ordres : prépare l'ordre à saisir chez le courtier (achat, renforcement, allègement, vente),
puis met à jour Mon PEA une fois l'ordre passé."""
import math
from datetime import date

import catalog
import store
from services import advisor, objectives, portfolio, screener, yahoo
from services import fx as fxmod

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


TTF_RATE = 0.004  # taxe sur les transactions financières (achats d'actions françaises de plus d'1 Md€ de capitalisation)


def costs(symbol: str, side: str, gross_eur: float, currency: str = "EUR") -> dict:
    """Frais d'une opération en euros : courtage + TTF (achat d'une grande valeur française) + change (hors euro)."""
    obj = objectives.get()
    info = catalog.lookup(symbol)
    ttf = round(gross_eur * TTF_RATE, 2) if (obj["ttf"] and side == "buy" and (info.get("isin") or "").startswith("FR")
                                             and info.get("core") and info.get("market") != "etf") else 0.0
    fx_fee = round(gross_eur * obj["fx_fee_pct"] / 100, 2) if currency != "EUR" else 0.0
    broker = fee(gross_eur)
    return {"broker": broker, "ttf": ttf, "fx": fx_fee, "total": round(broker + ttf + fx_fee, 2)}


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
    info = catalog.lookup(sym)
    pf = portfolio.summary()
    line = next((l for l in pf["lines"] if l["symbol"] == sym), None)
    held = sum(l["quantity"] for l in pf["lines"] if l["symbol"] == sym)
    adv = advisor.cached_verdicts().get(sym)
    fx = fxmod.rate(q.get("currency")) or 1.0  # euros pour 1 unité de devise
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
        quantity = max(0, math.floor((amount - fee(amount)) / (limit * fx)))
        if quantity == 0:
            warnings.append("amount_too_small")
        gross = round(quantity * limit * fx, 2)  # en euros
        after = ((line["value"] if line else 0) + gross) / max(pf["total"] or gross, 1) * 100
        if after > MAX_LINE:
            warnings.append("line_heavy")
        c = costs(sym, "buy", gross, q["currency"])
        return {"symbol": sym, "side": side, "name": q["name"], "isin": info.get("isin"), "price": price, "currency": q["currency"], "fx": fx,
                "amount_native": round(quantity * limit, 2), "alternatives": info.get("alternatives", []), "costs": c,
                "quantity": quantity, "limit": limit, "amount": gross, "fees": c["total"], "total": round(gross + c["total"], 2),
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
    gross = round(quantity * limit * fx, 2)  # en euros
    pru = line["avg_price"] if line else price * fx  # PRU en euros
    return {"symbol": sym, "side": side, "name": q["name"], "isin": info.get("isin"), "price": price, "currency": q["currency"], "fx": fx,
            "amount_native": round(quantity * limit, 2), "costs": costs(sym, side, gross, q["currency"]),
            "quantity": quantity, "held": held, "limit": limit, "amount": gross,
            "fees": costs(sym, side, gross, q["currency"])["total"], "total": round(gross - costs(sym, side, gross, q["currency"])["total"], 2),
            "realized_pnl": round(gross - pru * quantity - costs(sym, side, gross, q["currency"])["total"], 2), "avg_price": pru,
            "advice": adv, "warnings": warnings, "fees_settings": fees_settings()}


def execute(symbol: str, side: str, quantity: float, price: float, fees: float, day: str | None = None) -> dict:
    """Enregistre un ordre exécuté dans le journal du PEA (prix de revient, liquidités et plus-values recalculés)."""
    if side not in ("buy", "sell", "reduce"):
        raise ValueError("Sens d'ordre inconnu")
    pf = portfolio.add_movement("buy" if side == "buy" else "sell", day or date.today().isoformat(), symbol, quantity, price, fees)
    with store.connect() as conn:
        conn.execute("INSERT INTO orders_log (symbol, side, quantity, price, fees) VALUES (?, ?, ?, ?, ?)", (symbol.upper(), side, quantity, price, fees))
    return pf


def journal() -> list[dict]:
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM orders_log ORDER BY at DESC LIMIT 200")]
