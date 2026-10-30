"""Calibre les pondérations du modèle local sur l'historique réel (aucune IA).
1. Rejoue l'analyse locale chaque mois sur 5 ans pour un échantillon de valeurs PEA et note les composantes du score.
2. Cherche les pondérations qui relient le mieux le score à la performance 6 mois plus tard (corrélation de rang),
   sur la période d'apprentissage (60 % des dates les plus anciennes).
3. Vérifie sur la période de test (40 % les plus récentes) et n'enregistre que si le test s'améliore.
Usage : python tools/calibrate.py [nb_valeurs]"""
import json
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import catalog  # noqa: E402
from services import advisor, yahoo  # noqa: E402

HORIZON = 126
GRID = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "model_weights.json")


def samples(sym):
    try:
        hist = yahoo.daily_history(sym)
        q = yahoo.quote(sym)
    except Exception:
        return []
    out = []
    for t in range(260, len(hist) - HORIZON, 21):
        r = advisor.local_advice(sym, "en", {**q, "dividend_yield": None, "fundamentals": None}, hist[: t + 1], [], now=hist[t]["ts"])
        out.append({"ts": hist[t]["ts"], "parts": r["components"], "ret": (hist[t + HORIZON]["close"] / hist[t]["close"] - 1) * 100})
    return out


def rank_ic(rows, w):
    if len(rows) < 30:
        return 0.0
    scores = [sum(v * w.get(k, 1.0) for k, v in r["parts"].items()) for r in rows]
    rs = _ranks(scores)
    rr = _ranks([r["ret"] for r in rows])
    return statistics.correlation(rs, rr) if len(set(rs)) > 1 else 0.0


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    for pos, i in enumerate(order):
        r[i] = pos
    return r


def hit(rows, w):
    n = h = 0
    for r in rows:
        s = sum(v * w.get(k, 1.0) for k, v in r["parts"].items())
        v = "BUY" if s >= 15 else "SELL" if s <= -15 else "HOLD"
        n += 1
        h += advisor._hit(v, r["ret"])
    return round(h / n * 100, 1) if n else None


def main(n=60):
    advisor.WEIGHTS = {k: 1.0 for k in advisor.NEW_COMPONENTS}  # collecte des composantes brutes
    syms = [e["symbol"] for e in catalog.entries() if e["pea"] and e["core"] and not e["status"] and e["market"] != "etf"][:n]
    with ThreadPoolExecutor(6) as pool:
        rows = [r for rs in pool.map(samples, syms) for r in rs]
    rows.sort(key=lambda r: r["ts"])
    cut = int(len(rows) * 0.6)
    train, test = rows[:cut], rows[cut:]
    keys = sorted({k for r in rows for k in r["parts"]})
    base = {k: (0.0 if k in advisor.NEW_COMPONENTS else 1.0) for k in keys}
    w = {k: 1.0 if k in advisor.NEW_COMPONENTS else 1.0 for k in keys}
    for _ in range(3):  # descente par coordonnées
        for k in keys:
            w[k] = max(GRID, key=lambda g: rank_ic(train, {**w, k: g}))
    report = {"samples": len(rows), "symbols": len(syms), "horizon_days": HORIZON,
              "before": {"train_ic": round(rank_ic(train, base), 3), "test_ic": round(rank_ic(test, base), 3), "test_hit": hit(test, base)},
              "after": {"train_ic": round(rank_ic(train, w), 3), "test_ic": round(rank_ic(test, w), 3), "test_hit": hit(test, w)}}
    print(json.dumps({"weights": w, **report}, indent=1))
    if report["after"]["test_ic"] > report["before"]["test_ic"]:
        json.dump({"weights": w, **report}, open(OUT, "w"), indent=1)
        print("Pondérations enregistrées :", OUT)
    else:
        print("Pas d'amélioration sur la période de test : pondérations inchangées")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
