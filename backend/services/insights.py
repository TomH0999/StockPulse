"""Éléments qui rendent le conseil plus fiable que la seule direction prévue du cours :

- risque (prévisible, contrairement au sens du cours) : volatilité, baisses passées, bêta, taille de ligne conseillée ;
- force relative : performance face à l'indice de référence et classement dans le secteur (tendance 12 mois hors dernier mois) ;
- fiabilité : le conseil n'est présenté comme un signal que si ses verdicts passés (rejoués sur 5 ans et réellement émis
  dans l'app) ont été justes nettement plus souvent que le hasard ;
- santé financière : notation simple des chiffres de l'entreprise (rentabilité, croissance, dette, valorisation)."""
import math
import statistics
import time

import store

RELIABLE_HIT = 55       # % de conseils justes à 6 mois au-delà duquel le signal est jugé fiable
MIN_SAMPLES = 20        # nombre minimal de conseils rejoués pour juger
MAX_LINE = 20.0         # plafond d'une ligne dans le PEA (%)
REFERENCE_VOL = 20.0    # volatilité d'un grand indice actions (%) : une valeur deux fois plus volatile = ligne deux fois plus petite
EU_SUFFIXES = (".DE", ".AS", ".MI", ".MC", ".BR", ".LS", ".IR", ".HE", ".VI", ".ST", ".CO", ".OL", ".WA", ".F", ".SW", ".L")


def benchmark(sym: str) -> tuple[str, str]:
    s = sym.upper()
    if s.endswith(".PA"):
        return "^FCHI", "CAC 40"
    if s.endswith(EU_SUFFIXES):
        return "^STOXX", "STOXX Europe 600"
    return "^GSPC", "S&P 500"


def _closes_by_day(hist):
    return {int(p["ts"] // 86400): p["close"] for p in hist}


def _at(series_days: list[int], closes: dict, day: int):
    """Dernier cours connu à une date (ou juste avant)."""
    lo, hi = 0, len(series_days) - 1
    if hi < 0 or series_days[0] > day:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if series_days[mid] <= day:
            lo = mid
        else:
            hi = mid - 1
    return closes[series_days[lo]]


def risk(hist, bench_hist=None) -> dict:
    c = [p["close"] for p in hist]
    if len(c) < 260:
        return {}
    rets = [b / a - 1 for a, b in zip(c[:-1], c[1:]) if a]
    year = rets[-252:]
    vol = statistics.pstdev(year) * math.sqrt(252) * 100
    down = [r for r in year if r < 0]
    down_vol = math.sqrt(sum(r * r for r in down) / len(year)) * math.sqrt(252) * 100 if down else 0.0
    window = c[-1260:]
    peak, mdd = window[0], 0.0
    for x in window:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    yearly = sorted((c[i] / c[i - 252] - 1) * 100 for i in range(252, len(c), 21))
    bad_year = yearly[max(0, int(len(yearly) * 0.1) - 1)] if yearly else None
    monthly = [(c[i] / c[i - 21] - 1) * 100 for i in range(21, len(c), 21)]
    beta = None
    if bench_hist:
        days, closes = sorted(_closes_by_day(bench_hist)), _closes_by_day(bench_hist)
        pairs = []
        for a, b in zip(hist[-253:-1], hist[-252:]):
            ba, bb = _at(days, closes, int(a["ts"] // 86400)), _at(days, closes, int(b["ts"] // 86400))
            if ba and bb and a["close"]:
                pairs.append((b["close"] / a["close"] - 1, bb / ba - 1))
        if len(pairs) > 100:
            ma, mb = statistics.mean(x for x, _ in pairs), statistics.mean(y for _, y in pairs)
            var = statistics.pvariance([y for _, y in pairs])
            if var:
                beta = round(sum((x - ma) * (y - mb) for x, y in pairs) / len(pairs) / var, 2)
    max_weight = round(max(2.0, min(MAX_LINE, MAX_LINE * REFERENCE_VOL / max(vol, 1))), 1)
    level = "low" if vol < 20 else "medium" if vol < 30 else "high" if vol < 45 else "very_high"
    return {"volatility": round(vol, 1), "downside_volatility": round(down_vol, 1), "max_drawdown_5y": round(mdd * 100, 1),
            "bad_year": round(bad_year, 1) if bad_year is not None else None, "worst_month": round(min(monthly), 1) if monthly else None,
            "beta": beta, "level": level, "max_weight": max_weight}


def relative(sym: str, hist, bench_hist, sector: str | None, snapshot: dict) -> dict:
    """Performance face à l'indice et rang dans le secteur (momentum 12-1, le plus robuste des signaux de tendance)."""
    c = [p["close"] for p in hist]
    out = {"benchmark": benchmark(sym)[1]}
    if bench_hist and len(c) > 253:
        days, closes = sorted(_closes_by_day(bench_hist)), _closes_by_day(bench_hist)
        now_b = _at(days, closes, int(hist[-1]["ts"] // 86400))
        for label, n in (("6m", 126), ("12m", 252)):
            then_b = _at(days, closes, int(hist[-1 - n]["ts"] // 86400))
            if now_b and then_b:
                out[f"excess_{label}"] = round(((c[-1] / c[-1 - n]) - (now_b / then_b)) * 100, 1)
    if len(c) > 253:
        out["momentum_12_1"] = round((c[-22] / c[-253] - 1) * 100, 1)
    if sector and snapshot:
        from catalog import entries  # import tardif : évite une dépendance circulaire au chargement
        peers = []
        for e in entries():
            r = snapshot.get(e["symbol"]) or {}
            if e.get("sector") == sector and e.get("kind", "stock") == "stock" and r.get("chg_1y") is not None and r.get("chg_1m") is not None:
                peers.append(((1 + r["chg_1y"] / 100) / (1 + r["chg_1m"] / 100) - 1) * 100)
        mine = out.get("momentum_12_1")
        if mine is not None and len(peers) >= 5:
            out["sector_rank"] = round(sum(p < mine for p in peers) / len(peers) * 100)
            out["sector_peers"] = len(peers)
            out["sector_median"] = round(statistics.median(peers), 1)
    return out


def live_record(sym: str, hist) -> dict:
    """Conseils réellement émis dans l'app (un par jour) comparés à l'évolution réelle du cours ensuite."""
    with store.connect() as conn:
        rows = conn.execute("SELECT day, verdict, price FROM advice_history WHERE symbol = ? AND price > 0", (sym.upper(),)).fetchall()
    if not rows or not hist:
        return {"n": 0}
    days, closes = sorted(_closes_by_day(hist)), _closes_by_day(hist)
    last_day = days[-1]
    out = {}
    for label, d in (("1m", 30), ("3m", 91), ("6m", 182)):
        n = hits = 0
        for day, verdict, price in rows:
            start = int(time.mktime(time.strptime(day, "%Y-%m-%d")) // 86400)
            if start + d > last_day:
                continue
            later = _at(days, closes, start + d)
            if not later:
                continue
            ret = (later / price - 1) * 100
            n += 1
            hits += (ret > 0) if verdict in ("BUY", "STRONG_BUY") else (ret < 0) if verdict in ("SELL", "REDUCE") else abs(ret) < 10
        out[label] = {"n": n, "hit_rate": round(hits / n * 100) if n else None}
    out["n"] = len(rows)
    return out


def reliability(track: dict | None, live: dict | None, risk_info: dict) -> dict:
    """Le conseil n'est un signal que si ses verdicts passés battent nettement le hasard ; sinon on le dit."""
    t6 = (track or {}).get("6m") or {}
    l6 = (live or {}).get("6m") or {}
    reasons = []
    if (t6.get("n") or 0) < MIN_SAMPLES:
        level = "insufficient"
        reasons.append("history_short")
    else:
        hit = t6["hit_rate"]
        if l6.get("n", 0) >= 10 and l6.get("hit_rate") is not None:
            hit = (hit * t6["n"] + l6["hit_rate"] * l6["n"] * 2) / (t6["n"] + l6["n"] * 2)  # le réel compte double
            reasons.append("live_included")
        level = "reliable" if hit >= RELIABLE_HIT else "weak" if hit >= 45 else "contrarian"
        reasons.append(f"hit_{round(hit)}")
    if risk_info.get("level") == "very_high":
        reasons.append("very_volatile")
    return {"level": level, "signal": level == "reliable", "reasons": reasons, "threshold": RELIABLE_HIT}


def health(f: dict | None) -> dict | None:
    """Notation de 0 à 100 par critère (rentabilité, croissance, solidité, valorisation) à partir des chiffres disponibles."""
    if not f:
        return None
    def band(v, lo, hi, reverse=False):
        if v is None:
            return None
        x = (v - lo) / (hi - lo)
        x = 1 - x if reverse else x
        return round(max(0.0, min(1.0, x)) * 100)
    scores = {
        "profitability": _avg(band(f.get("net_margin"), 0, 20), band(f.get("roe"), 0, 25), band(f.get("operating_margin"), 0, 25)),
        "growth": _avg(band(f.get("revenue_growth"), -5, 15), band(f.get("earnings_growth"), -10, 20)),
        "solidity": band(f.get("debt_to_equity"), 0.3, 2.5, reverse=True),
        "valuation": None if f.get("pe") is None else 0 if f["pe"] <= 0 else band(f["pe"], 10, 40, reverse=True),
    }
    known = [v for v in scores.values() if v is not None]
    return {**scores, "overall": round(sum(known) / len(known)) if known else None, "criteria": len(known)}


def _avg(*xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs)) if xs else None
