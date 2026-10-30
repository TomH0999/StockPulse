"""Mon PEA : journal des mouvements (versements, achats, ventes, dividendes) d'où sont déduits liquidités, lignes,
prix de revient et plus-values ; valorisation en direct, conseil et alertes par ligne, plafond de versements."""
import re
from datetime import date

import catalog
import store
from services import advisor, fx, objectives, rebalance, yahoo

PEA_CEILING = 150_000


TYPES = ("deposit", "withdrawal", "buy", "sell", "dividend")
EPS = 1e-9


# --- Journal du PEA : toutes les valeurs (liquidités, quantités, PRU, plus-values) en sont déduites ---

def movements() -> list[dict]:
    _migrate_legacy()
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT id, day, type, symbol, quantity, price, fees, amount, fx FROM pea_movements ORDER BY day, id")]
    missing = [m for m in rows if m["type"] in ("buy", "sell") and m["fx"] is None]
    if missing:  # mouvements des versions précédentes : taux de change actuel
        for m in missing:
            m["fx"] = _rate_for(m["symbol"])
        with store.connect() as conn:
            for m in missing:
                conn.execute("UPDATE pea_movements SET fx = ? WHERE id = ?", (m["fx"], m["id"]))
    return rows


def ledger(rows: list[dict] | None = None) -> dict:
    """Rejoue le journal dans l'ordre chronologique. Tout est tenu en euros : prix × taux de change du jour du mouvement,
    frais (en euros) inclus dans le prix de revient (usage courtier)."""
    rows = movements() if rows is None else sorted(rows, key=lambda m: (m["day"], m.get("id") or 0))
    pos: dict[str, dict] = {}
    led = {"cash": 0.0, "deposits": 0.0, "withdrawals": 0.0, "realized": 0.0, "dividends": 0.0, "fees": 0.0, "positions": pos}
    for m in rows:
        t, fees = m["type"], m.get("fees") or 0.0
        led["fees"] += fees
        if t == "deposit":
            led["cash"] += m["amount"]
            led["deposits"] += m["amount"]
        elif t == "withdrawal":
            led["cash"] -= m["amount"]
            led["withdrawals"] += m["amount"]
        elif t == "dividend":
            led["cash"] += m["amount"]
            led["dividends"] += m["amount"]
            if m.get("symbol"):
                pos.setdefault(m["symbol"], _new_pos(m["day"]))["dividends"] += m["amount"]
        elif t == "buy":
            p = pos.setdefault(m["symbol"], _new_pos(m["day"]))
            if p["quantity"] < EPS:
                p["since"] = m["day"]
            p["last_buy"] = m["day"]
            gross = m["quantity"] * m["price"] * (m.get("fx") or 1.0)
            p["quantity"] += m["quantity"]
            p["cost"] += gross + fees
            led["cash"] -= gross + fees
        elif t == "sell":
            p = pos.setdefault(m["symbol"], _new_pos(m["day"]))
            if m["quantity"] > p["quantity"] + EPS:
                raise ValueError(f"Vente de {m['quantity']} {m['symbol']} le {m['day']} supérieure à la quantité détenue ({p['quantity']:g})")
            pru = p["cost"] / p["quantity"]
            gross = m["quantity"] * m["price"] * (m.get("fx") or 1.0)
            gain = gross - m["quantity"] * pru - fees
            p["realized"] += gain
            led["realized"] += gain
            p["quantity"] -= m["quantity"]
            p["cost"] -= m["quantity"] * pru
            if p["quantity"] < EPS:
                p["quantity"], p["cost"] = 0.0, 0.0
            led["cash"] += gross - fees
        if led["cash"] < -0.005:
            raise ValueError(f"Liquidités insuffisantes le {m['day']} : faites d'abord un versement")
    return led


def _new_pos(day):
    return {"quantity": 0.0, "cost": 0.0, "realized": 0.0, "dividends": 0.0, "since": day, "last_buy": day}


def _rate_for(symbol: str | None) -> float:
    """Taux de conversion vers l'euro de la devise de cotation d'une valeur (1 si euro ou inconnu)."""
    if not symbol:
        return 1.0
    try:
        ccy = yahoo.quote(symbol).get("currency") or "EUR"
    except Exception:
        return 1.0
    return _fx({ccy}).get(ccy) or 1.0


def add_movement(type: str, day: str, symbol: str | None = None, quantity: float | None = None, price: float | None = None,
                 fees: float = 0.0, amount: float | None = None, fx: float | None = None) -> dict:
    """Achat / vente : prix dans la devise de cotation, frais en euros ; fx = euros pour 1 unité de devise (taux du jour par défaut)."""
    if type not in TYPES:
        raise ValueError("Type de mouvement inconnu")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day or "") or day > date.today().isoformat():
        raise ValueError("Date invalide (AAAA-MM-JJ, pas dans le futur)")
    fees = fees or 0.0
    if fees < 0:
        raise ValueError("Frais négatifs")
    if type in ("buy", "sell"):
        if not symbol or not quantity or quantity <= 0 or not price or price <= 0:
            raise ValueError("Valeur, quantité et prix doivent être renseignés et positifs")
        amount = None
    elif not amount or amount <= 0:
        raise ValueError("Montant positif requis")
    trade = type in ("buy", "sell")
    if trade and fx is None:
        fx = _rate_for(symbol)
    if trade and (not fx or fx <= 0):
        raise ValueError("Taux de change invalide")
    m = {"day": day, "type": type, "symbol": symbol.upper() if symbol else None, "quantity": quantity if trade else None,
         "price": price if trade else None, "fees": fees, "amount": amount, "fx": fx if trade else None}
    led = ledger(movements() + [{**m, "id": 10**12}])  # refuse un mouvement qui rendrait le journal incohérent
    if type == "deposit" and led["deposits"] > PEA_CEILING + 0.005:
        raise ValueError(f"Plafond de versements du PEA dépassé ({PEA_CEILING:,.0f} €)".replace(",", " "))
    with store.connect() as conn:
        conn.execute("INSERT INTO pea_movements (day, type, symbol, quantity, price, fees, amount, fx) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (m["day"], m["type"], m["symbol"], m["quantity"], m["price"], m["fees"], m["amount"], m["fx"]))
    return summary()


def update_movement(movement_id: int, **fields) -> dict:
    """Modifie un mouvement : le journal entier est revalidé avant enregistrement."""
    rows = movements()
    cur = next((m for m in rows if m["id"] == movement_id), None)
    if not cur:
        raise ValueError("Mouvement introuvable")
    new = {**cur, **{k: v for k, v in fields.items() if k in ("day", "symbol", "quantity", "price", "fees", "amount", "fx") and v is not None}}
    if new.get("symbol"):
        new["symbol"] = new["symbol"].upper()
    if new["type"] in ("buy", "sell") and ((new.get("quantity") or 0) <= 0 or (new.get("price") or 0) <= 0):
        raise ValueError("Quantité et prix doivent être positifs")
    if new["type"] not in ("buy", "sell") and (new.get("amount") or 0) <= 0:
        raise ValueError("Montant positif requis")
    if (new.get("fees") or 0) < 0 or new["day"] > date.today().isoformat():
        raise ValueError("Frais ou date invalides")
    led = ledger([new if m["id"] == movement_id else m for m in rows])
    if led["deposits"] > PEA_CEILING + 0.005:
        raise ValueError("Plafond de versements du PEA dépassé")
    with store.connect() as conn:
        conn.execute("UPDATE pea_movements SET day = ?, symbol = ?, quantity = ?, price = ?, fees = ?, amount = ?, fx = ? WHERE id = ?",
                     (new["day"], new.get("symbol"), new.get("quantity"), new.get("price"), new.get("fees") or 0, new.get("amount"),
                      new.get("fx"), movement_id))
    return summary()


def delete_movement(movement_id: int) -> dict:
    ledger([m for m in movements() if m["id"] != movement_id])  # ex. supprimer un versement qui a financé un achat : refusé
    with store.connect() as conn:
        conn.execute("DELETE FROM pea_movements WHERE id = ?", (movement_id,))
    return summary()


def reset() -> dict:
    """Remet le PEA à zéro : mouvements, ordres et anciennes lignes (l'historique se recalcule depuis le journal)."""
    with store.connect() as conn:
        for table in ("pea_movements", "orders_log", "holdings"):
            conn.execute(f"DELETE FROM {table}")
    return summary()


def _migrate_legacy():
    """Versions < 2.1 : lignes et liquidités saisies à la main, converties en versement + achats."""
    if store.get_setting("ledger_migrated"):
        return
    with store.connect() as conn:
        old = [dict(r) for r in conn.execute("SELECT symbol, quantity, avg_price FROM holdings")]
    cost = sum(h["quantity"] * h["avg_price"] for h in old)
    cash = float(store.get_setting("pea_cash", "0") or 0)
    deposits = max(float(store.get_setting("pea_deposits", "0") or 0), cost + cash)
    today = date.today().isoformat()
    with store.connect() as conn:
        if deposits > 0:
            conn.execute("INSERT INTO pea_movements (day, type, amount, fees) VALUES (?, 'deposit', ?, 0)", (today, round(deposits, 2)))
        for h in old:
            conn.execute("INSERT INTO pea_movements (day, type, symbol, quantity, price, fees, fx) VALUES (?, 'buy', ?, ?, ?, 0, 1)",
                         (today, h["symbol"], h["quantity"], h["avg_price"]))  # ancien PRU saisi en euros
        conn.execute("DELETE FROM holdings")
    store.set_setting("ledger_migrated", "1")


def lines() -> list[dict]:
    return [{"id": s, "symbol": s, "quantity": round(p["quantity"], 6), "avg_price": round(p["cost"] / p["quantity"], 4), "since": p["since"]}
            for s, p in sorted(ledger()["positions"].items()) if p["quantity"] > EPS]


def symbols() -> list[str]:
    return [l["symbol"] for l in lines()]


def _fx(currencies: set[str]) -> dict[str, float | None]:
    return fx.rates(currencies)


def summary() -> dict:
    led = ledger()
    held = {s: p for s, p in led["positions"].items() if p["quantity"] > EPS}
    quotes = {q["symbol"]: q for q in yahoo.quotes(list(held))} if held else {}
    rates = _fx({(quotes.get(s) or {}).get("currency") or "EUR" for s in held})
    verdicts = advisor.cached_verdicts()
    info = {s: catalog.lookup(s) for s in held}
    out, value_total, cost_total, day_change = [], 0.0, 0.0, 0.0
    for s, p in sorted(held.items()):
        q = quotes.get(s, {})
        ccy = q.get("currency") or "EUR"
        rate = rates.get(ccy)
        price = q.get("price") or 0
        qty, cost = p["quantity"], p["cost"]
        value = qty * price * (rate or 0)
        cost_eur = cost  # prix de revient tenu en euros (taux du jour de chaque achat)
        adv = verdicts.get(s)
        eligible = (info.get(s) or {}).get("pea", "." in s and s.rsplit(".", 1)[-1] in ("PA", "DE", "AS", "MC", "MI", "BR", "LS", "IR", "HE", "ST", "CO", "OL", "VI"))
        alerts = []
        if adv and adv["verdict"] in ("REDUCE", "SELL"):
            alerts.append(f"verdict_{adv['verdict'].lower()}")
        if (q.get("change_percent") or 0) <= -5:
            alerts.append("big_drop")
        if cost and price and value / cost_eur - 1 <= -0.15:
            alerts.append("loss_15")
        if not eligible:
            alerts.append("not_pea")
        if q.get("error") or not price or rate is None:
            alerts.append("no_quote")
        value_total += value
        cost_total += cost_eur
        day_change += qty * (q.get("change") or 0) * (rate or 0)
        out.append({"id": s, "symbol": s, "name": q.get("short_name") or (info.get(s) or {}).get("name", s), "currency": ccy, "fx": rate,
                    "quantity": round(qty, 6), "avg_price": round(cost / qty, 4), "price": price, "change_percent": q.get("change_percent"),
                    "value": round(value, 2), "cost": round(cost_eur, 2), "pnl": round(value - cost_eur, 2),
                    "pnl_percent": round((value / cost_eur - 1) * 100, 2) if cost_eur else 0.0,
                    "realized": round(p["realized"], 2), "dividends": round(p["dividends"], 2), "since": p["since"], "last_buy": p["last_buy"],
                    "advice": adv, "alerts": alerts, "in_total": True})
    cash = round(led["cash"], 2)
    total = value_total + cash
    for l in out:
        l["weight"] = round(l["value"] / total * 100, 1) if total else None  # poids dans le PEA entier (titres + liquidités)
    net = led["deposits"] - led["withdrawals"]
    gain = total - net
    opened = objectives.get()["opened"]
    five = None
    if opened:
        o = date.fromisoformat(opened)
        try:
            five = o.replace(year=o.year + 5)
        except ValueError:  # 29 février
            five = o.replace(year=o.year + 5, day=28)
    mature = bool(five and date.today() >= five)
    tax_rate = 0.172 if mature else 0.30  # après 5 ans : prélèvements sociaux seuls ; avant : PFU 30 % et clôture du plan
    return {
        "opened": opened, "five_years": five.isoformat() if five else None, "mature": mature,
        "days_to_five_years": (five - date.today()).days if five and not mature else 0,
        "tax_rate": tax_rate if opened else None, "tax_if_withdrawn": round(max(0.0, gain) * tax_rate, 2) if opened else None,
        "lines": out, "value": round(value_total, 2), "cost": round(cost_total, 2), "pnl": round(value_total - cost_total, 2),
        "pnl_percent": round((value_total / cost_total - 1) * 100, 2) if cost_total else 0.0,
        "realized": round(led["realized"], 2), "dividends": round(led["dividends"], 2), "fees": round(led["fees"], 2),
        "day_change": round(day_change, 2), "cash": cash, "deposits": round(led["deposits"], 2),
        "withdrawals": round(led["withdrawals"], 2), "ceiling": PEA_CEILING, "ceiling_left": round(PEA_CEILING - led["deposits"], 2),
        "total": round(total, 2), "gain": round(total - net, 2),
        "performance": round((total - net) / net * 100, 2) if net > 0 else None,
    }


MAX_LINE, MAX_SECTOR, MIN_LINES = 20, 35, 5


def diversification(summary: dict) -> dict:
    """Répartition par secteur / pays, risques de concentration et suggestions de rééquilibrage."""
    info = {l["symbol"]: catalog.lookup(l["symbol"]) for l in summary["lines"]}  # cotations secondaires comprises
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
    rate = {s: fx.rate(yahoo.quote(s).get("currency")) or 1.0 for s in qty}
    values = [sum(qty[s] * series[s][d] * rate[s] for s in qty) for d in days]
    return {"index": index, "series": [{"day": d, "portfolio": round(v / values[0] * 100, 2), "index": round(idx[d] / idx[days[0]] * 100, 2)}
                                       for d, v in zip(days, values)]}


def context(symbol: str) -> dict:
    """Situation personnelle transmise à l'agent IA : position sur la valeur et état du PEA."""
    sm = summary()
    line = next((l for l in sm["lines"] if l["symbol"] == symbol.upper()), None)
    div = diversification(sm) if sm["lines"] else {"sectors": {}}
    return {
        "pea_total_eur": sm["total"], "cash_eur": sm["cash"], "deposits_eur": sm["deposits"], "ceiling_left_eur": sm["ceiling_left"],
        "lines": len(sm["lines"]), "sector_weights_pct": div["sectors"],
        "position": None if not line else {k: line[k] for k in ("quantity", "avg_price", "price", "pnl_percent", "weight", "since", "realized")},
    }
