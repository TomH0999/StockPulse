"""Historique quotidien du PEA reconstitué à partir du journal et des cours de clôture, et performance réelle
(rendement pondéré dans le temps, qui neutralise les versements) comparée au CAC 40 et au MSCI World."""
from datetime import date, datetime, timezone

from services import fx, portfolio, yahoo

BENCHMARKS = {"CAC 40": "^FCHI", "MSCI World": "CW8.PA"}


def _closes(symbol: str) -> dict[str, float]:
    try:
        return {datetime.fromtimestamp(p["ts"], timezone.utc).strftime("%Y-%m-%d"): p["close"] for p in yahoo.daily_history(symbol, years=10)}
    except Exception:
        return {}


def series() -> dict:
    moves = portfolio.movements()
    if not moves:
        return {"points": [], "benchmarks": list(BENCHMARKS)}
    start = moves[0]["day"]
    symbols = sorted({m["symbol"] for m in moves if m["symbol"] and m["type"] in ("buy", "sell")})
    closes = {s: _closes(s) for s in symbols}
    rates = {s: fx.rate(yahoo.quote(s).get("currency")) or 1.0 for s in symbols}  # taux actuel (approximation)
    bench = {name: _closes(sym) for name, sym in BENCHMARKS.items()}
    days = sorted(d for d in bench["CAC 40"] if d >= start) or sorted({m["day"] for m in moves})
    if date.today().isoformat() not in days:
        days.append(date.today().isoformat())
    last = {s: None for s in symbols}
    points, prev_value, twr, i = [], None, 1.0, 0
    bench_base = {name: None for name in bench}
    bench_last = {name: None for name in bench}
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
        if prev_value:
            twr *= (value - flow) / prev_value
        prev_value = value if value > 0 else None
        point = {"day": d, "value": round(value, 2), "invested": round(led["deposits"] - led["withdrawals"], 2),
                 "pea": round(twr * 100, 2)}
        for name, c in bench.items():
            bench_last[name] = c.get(d, bench_last[name])
            if bench_last[name] and bench_base[name] is None:
                bench_base[name] = bench_last[name]
            point[name] = round(bench_last[name] / bench_base[name] * 100, 2) if bench_base[name] else None
        points.append(point)
    return {"points": points, "benchmarks": list(BENCHMARKS),
            "performance": round((twr - 1) * 100, 2),
            "benchmark_performance": {n: (points[-1][n] - 100 if points[-1].get(n) else None) for n in BENCHMARKS}}
