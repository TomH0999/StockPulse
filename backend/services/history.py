"""Historique quotidien du compte reconstitué à partir du journal et des cours de clôture, et performance réelle :
- rendement pondéré dans le temps (qualité des choix, indépendamment des dates de versement) ;
- TRI / XIRR (rendement réellement obtenu compte tenu des dates de versement) ;
- comparaison honnête : la même suite de versements placée sur un ETF MSCI World dividendes réinvestis (CW8).
  C'est la question utile : « est-ce que je fais mieux que si j'avais tout mis sur CW8 ? »."""
from datetime import date, datetime, timezone

from services import fx, yahoo

WORLD = "CW8.PA"  # Amundi MSCI World, capitalisant (dividendes réinvestis), éligible PEA
BENCHMARKS = {"MSCI World": WORLD, "CAC 40": "^FCHI"}  # CAC 40 : indice de prix, hors dividendes


def _closes(symbol: str) -> dict[str, float]:
    try:
        return {datetime.fromtimestamp(p["ts"], timezone.utc).strftime("%Y-%m-%d"): p["close"] for p in yahoo.daily_history(symbol, years=10)}
    except Exception:
        return {}


def _flows(moves) -> list[tuple[str, float]]:
    """Flux de l'investisseur : versement = sortie d'argent (négatif), retrait = entrée (positif)."""
    return [(m["day"], -m["amount"] if m["type"] == "deposit" else m["amount"]) for m in moves if m["type"] in ("deposit", "withdrawal")]


def xirr(flows: list[tuple[str, float]], final: float, end: str | None = None) -> float | None:
    """Taux annuel r tel que la somme des flux actualisés (et de la valeur finale) soit nulle (en %)."""
    end = end or date.today().isoformat()
    cf = [(date.fromisoformat(d), v) for d, v in flows] + [(date.fromisoformat(end), final)]
    if not any(v < 0 for _, v in cf) or not any(v > 0 for _, v in cf):
        return None
    t0 = min(d for d, _ in cf)
    if (date.fromisoformat(end) - t0).days < 30:
        return None  # moins d'un mois : un taux annualisé n'aurait pas de sens
    npv = lambda r: sum(v / (1 + r) ** ((d - t0).days / 365.25) for d, v in cf)
    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2 * 100, 2)


def world_value(flows: list[tuple[str, float]], closes: dict[str, float] | None = None) -> float | None:
    """Valeur aujourd'hui de la même suite de versements / retraits placée sur CW8 (au cours de clôture du jour)."""
    closes = _closes(WORLD) if closes is None else closes
    if not closes:
        return None
    days = sorted(closes)
    units = 0.0
    for d, v in flows:
        price = next((closes[x] for x in days if x >= d), closes[days[-1]])
        units += -v / price
    return round(units * closes[days[-1]], 2)


def money_weighted(moves: list[dict], total: float) -> dict:
    flows = _flows(moves)
    if not flows:
        return {"xirr": None, "world": None}
    try:
        wv = world_value(flows)
    except Exception:
        wv = None
    mine = xirr(flows, total)
    world = {"value": wv, "xirr": xirr(flows, wv) if wv else None, "difference": round(total - wv, 2) if wv else None} if wv else None
    return {"xirr": mine, "world": world}


def series() -> dict:
    from services import portfolio  # import tardif : le module portefeuille utilise aussi celui-ci
    moves = portfolio.movements()
    if not moves:
        return {"points": [], "benchmarks": list(BENCHMARKS)}
    start = moves[0]["day"]
    symbols = sorted({m["symbol"] for m in moves if m["symbol"] and m["type"] in ("buy", "sell")})
    closes = {s: _closes(s) for s in symbols}
    rates = {s: fx.rate(yahoo.quote(s).get("currency")) or 1.0 for s in symbols}  # taux actuel (approximation)
    bench = {name: _closes(sym) for name, sym in BENCHMARKS.items()}
    days = sorted(d for d in bench["MSCI World"] if d >= start) or sorted({m["day"] for m in moves})
    if date.today().isoformat() not in days:
        days.append(date.today().isoformat())
    last = {s: None for s in symbols}
    points, prev_value, twr, i = [], None, 1.0, 0
    bench_base = {name: None for name in bench}
    bench_last = {name: None for name in bench}
    world_units, world_last = 0.0, None
    for d in days:
        while i < len(moves) and moves[i]["day"] <= d:
            i += 1
        led = portfolio.ledger(moves[:i])
        flow = sum((m["amount"] if m["type"] == "deposit" else -m["amount"]) for m in moves[:i]
                   if m["day"] == d and m["type"] in ("deposit", "withdrawal"))
        value = led["cash"]
        for s, p in led["positions"].items():
            if p["quantity"] > 0:
                last[s] = closes.get(s, {}).get(d, last.get(s))
                value += p["quantity"] * (last[s] or p["cost"] / p["quantity"] / rates.get(s, 1.0)) * rates.get(s, 1.0)
        world_last = bench["MSCI World"].get(d, world_last)
        if flow and world_last:
            world_units += flow / world_last  # même versement placé sur CW8 le même jour
        if prev_value:
            twr *= (value - flow) / prev_value
        prev_value = value if value > 0 else None
        point = {"day": d, "value": round(value, 2), "invested": round(led["deposits"] - led["withdrawals"], 2),
                 "pea": round(twr * 100, 2), "world_value": round(world_units * world_last, 2) if world_last else None}
        for name, c in bench.items():
            bench_last[name] = c.get(d, bench_last[name])
            if bench_last[name] and bench_base[name] is None:
                bench_base[name] = bench_last[name]
            point[name] = round(bench_last[name] / bench_base[name] * 100, 2) if bench_base[name] else None
        points.append(point)
    mw = money_weighted(moves, points[-1]["value"])
    return {"points": points, "benchmarks": list(BENCHMARKS), "xirr": mw["xirr"], "world": mw["world"],
            "performance": round((twr - 1) * 100, 2),
            "benchmark_performance": {n: (points[-1][n] - 100 if points[-1].get(n) else None) for n in BENCHMARKS}}
