"""Fiabilité du modèle, mesurée comme les gérants quantitatifs valident un facteur : en coupe transversale.

À chaque fin de mois, toutes les valeurs de l'univers sont notées par le moteur affiché (avec les seuls comptes publiés à
cette date), puis comparées à leur rendement total des 12 mois suivants :
- corrélation de rang (IC) entre le score et le rendement suivant, chaque mois ;
- écart de rendement entre le quintile le mieux noté et le moins bien noté ;
- rendement du quintile du haut face à l'univers, au STOXX Europe 600 (sélection) et au MSCI World / CW8 (actions ou ETF ?).
Les fenêtres de 12 mois se chevauchent : l'intervalle de confiance compte une observation indépendante par an.
État : vert si tout l'intervalle est positif, rouge s'il est entièrement négatif, gris (« non mesurable ») sinon."""
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import catalog
import store

HORIZON = 252          # 12 mois de bourse
STEP = 21              # un classement par mois
MIN_UNIVERSE = 30      # valeurs notées au minimum pour qu'un mois compte
SEED = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "..", "catalog_sources", "model_validation.json")
if not os.path.exists(SEED):
    SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "catalog_sources", "model_validation.json")
COMPONENTS = ("valuation", "momentum", "strength", "growth", "quality", "trend")


def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):  # rangs moyens pour les ex aequo (scores entiers)
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def rank_ic(x, y):
    if len(x) < 5:
        return None
    rx, ry = _ranks(x), _ranks(y)
    try:
        return statistics.correlation(rx, ry)
    except statistics.StatisticsError:
        return None


# Quantiles de Student à 97,5 % : avec 2 ou 3 périodes indépendantes, un intervalle « ±1,96 écart-type » serait trompeur
T975 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23, 15: 2.13, 20: 2.09, 30: 2.04}


def _t(df: float) -> float:
    d = max(1, int(df))
    return T975.get(d) or next((v for k, v in sorted(T975.items()) if k >= d), 1.96)


def _ci(values, months_per_obs=12):
    """Moyenne et intervalle de confiance à 95 % : les fenêtres de 12 mois se chevauchent, on ne compte qu'une observation
    indépendante par an (loi de Student sur ce nombre réduit)."""
    vals = [v for v in values if v is not None]
    if len(vals) < 3:
        return None
    m = statistics.mean(vals)
    n_eff = max(1.0, len(vals) / months_per_obs)
    half = _t(n_eff - 1) * statistics.pstdev(vals) / math.sqrt(n_eff)
    return {"mean": round(m, 3), "low": round(m - half, 3), "high": round(m + half, 3), "months": len(vals), "independent": round(n_eff, 1)}


def status(ci) -> str:
    if not ci:
        return "unknown"
    return "positive" if ci["low"] > 0 else "negative" if ci["high"] < 0 else "inconclusive"


def _series_at(hist):
    from services.advisor import _series_at as at
    return at(hist)


def load_universe(symbols, fetch=True, workers=8):
    """Historique 10 ans, comptes et secteur de chaque valeur (cache local de 7 jours pour les comptes)."""
    from services import financials, yahoo

    def one(sym):
        e = catalog.lookup(sym) or {}
        try:
            h = yahoo.daily_history(sym)
            q = yahoo.quote(sym)
            raw = financials.raw(sym, fetch=fetch)
        except Exception:
            return None
        if len(h) < 600:
            return None
        return {"symbol": sym, "hist": h, "raw": raw, "sector": e.get("sector"), "currency": q.get("currency")}
    with ThreadPoolExecutor(workers) as pool:
        return [u for u in pool.map(one, symbols) if u]


def collect(universe: list[dict], world: list[dict]) -> dict[int, list]:
    """Notes du moteur affiché pour chaque valeur à chaque fin de mois (comptes connus à la date) et rendement à 12 mois."""
    import bisect
    from services import advisor, financials
    dates = [p["ts"] for p in world][::STEP]
    by_date: dict[int, list] = {d: [] for d in dates}
    for u in universe:
        h = u["hist"]
        ts_list = [p["ts"] for p in h]
        adj = [p.get("adj") or p["close"] for p in h]
        for d in dates:
            t = bisect.bisect_right(ts_list, d) - 1
            if t < 260 or t + HORIZON >= len(h) or d - ts_list[t] > 10 * 86400:
                continue
            m = financials.metrics(u["raw"], h[t]["close"], u["sector"], h[: t + 1], as_of=d, currency=u["currency"]) if u["raw"] else None
            if not m or not m.get("years"):
                continue  # le modèle complet n'est mesuré que là où les comptes étaient publiés
            r = advisor.local_advice(u["symbol"], "en", {"name": u["symbol"]}, h[: t + 1], [], now=d, fin=m, bench=world)
            by_date[d].append({"symbol": u["symbol"], "score": r["score"], "fwd": (adj[t + HORIZON] / adj[t] - 1) * 100,
                               "verdict": r["verdict"], "comps": r["components"]})
    return by_date


def evaluate(by_date: dict[int, list], world: list[dict], stoxx: list[dict] | None = None, weights: dict | None = None,
             date_from: int = 0, date_to: int = 2**40, universe_size: int | None = None) -> dict:
    """Mesures sur 12 mois à partir des notes collectées (weights : multiplicateurs par groupe, pour la calibration)."""
    w_at, s_at = _series_at(world), (_series_at(stoxx) if stoxx else None)
    ics, spreads, top_vs_univ, top_vs_world, top_vs_stoxx, comp_ics = [], [], [], [], [], {k: [] for k in COMPONENTS}
    verdict_rows: dict[str, list] = {}
    months, first, ic_dates = 0, None, []
    for d, rows in sorted(by_date.items()):
        if len(rows) < MIN_UNIVERSE or not date_from <= d < date_to:
            continue
        months += 1
        first = first or d
        score = (lambda r: sum(v * weights.get(k, 1.0) for k, v in r["comps"].items())) if weights else (lambda r: r["score"])
        scores, fwd = [score(r) for r in rows], [r["fwd"] for r in rows]
        ics.append(rank_ic(scores, fwd))
        ic_dates.append(d)
        for k in COMPONENTS:
            comp_ics[k].append(rank_ic([r["comps"].get(k, 0) for r in rows], fwd))
        srt = sorted(zip(scores, fwd))
        q = max(1, len(srt) // 5)
        top, bottom = [f for _, f in srt[-q:]], [f for _, f in srt[:q]]
        univ = statistics.mean(fwd)
        spreads.append(statistics.mean(top) - statistics.mean(bottom))
        top_vs_univ.append(statistics.mean(top) - univ)
        d_end = d + int(HORIZON * 365.25 / 252 * 86400)
        w0, w1 = w_at(d), w_at(d_end)
        if w0 and w1:
            top_vs_world.append(statistics.mean(top) - (w1 / w0 - 1) * 100)
        if s_at:
            s0, s1 = s_at(d), s_at(d_end)
            if s0 and s1:
                top_vs_stoxx.append(statistics.mean(top) - (s1 / s0 - 1) * 100)
        for r in rows:
            verdict_rows.setdefault(r["verdict"], []).append(r["fwd"] - univ)
    ic = _ci(ics)
    return {
        "computed_at": int(time.time()), "universe": universe_size, "months": months, "horizon_months": 12, "first": first,
        "ic": ic, "status": status(ic), "ic_series": [[d, round(v, 3)] for d, v in zip(ic_dates, ics) if v is not None],
        "quintile_spread": _ci(spreads), "top_vs_universe": _ci(top_vs_univ), "top_vs_world": _ci(top_vs_world),
        "top_vs_stoxx600": _ci(top_vs_stoxx),
        "components": {k: _ci(v) for k, v in comp_ics.items()},
        "by_verdict": {v: {"n": len(x), "excess_vs_universe": round(statistics.mean(x), 2), "beat_share": round(sum(e > 0 for e in x) / len(x) * 100)}
                       for v, x in verdict_rows.items() if x},
        "engine_version": None,
    }


def run(universe: list[dict], world: list[dict], stoxx: list[dict] | None = None, weights: dict | None = None,
        date_from: int = 0, date_to: int = 2**40) -> dict:
    return evaluate(collect(universe, world), world, stoxx, weights, date_from, date_to, len(universe))


def latest() -> dict | None:
    """Dernière mesure : calculée sur cette installation, sinon celle fournie avec la version."""
    raw = store.get_setting("model_validation")
    if raw:
        return json.loads(raw)
    try:
        return json.load(open(SEED, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def refresh(max_symbols: int = 300) -> dict:
    """Recalcul complet (tâche de fond hebdomadaire) sur les principales valeurs éligibles au PEA."""
    from services import advisor, yahoo
    syms = [e["symbol"] for e in catalog.entries() if e["core"] and e["kind"] == "stock" and e["pea"] and not e["status"]][:max_symbols]
    universe = load_universe(syms)
    res = run(universe, yahoo.daily_history(advisor.BENCHMARK), yahoo.daily_history("^STOXX"))
    res["engine_version"] = advisor.ENGINE_VERSION
    store.set_setting("model_validation", json.dumps(res))
    return res
