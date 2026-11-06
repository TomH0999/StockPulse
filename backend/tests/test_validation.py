"""Mesure de fiabilité en coupe transversale : un modèle qui classe bien est détecté, un modèle au hasard reste « gris »."""
import random

from conftest import DAY, START, make_fin
from services import validation


def _hist(drift, n=3600, seed=0):
    rnd = random.Random(seed)
    price, out = 100.0, []
    for i in range(n):
        price *= 1 + drift + rnd.gauss(0, 0.01)
        out.append({"ts": START + i * DAY, "timestamp": "2020-01-01T00:00:00Z", "close": price, "adj": price, "open": price,
                    "high": price, "low": price, "volume": 1})
    return out


def test_rank_ic_and_ci_status():
    assert validation.rank_ic([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == 1.0
    assert validation.rank_ic([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.0
    assert validation.status(validation._ci([0.1] * 36 + [0.12] * 12)) == "positive"
    assert validation.status(validation._ci([0.3, -0.3] * 18)) == "inconclusive"
    assert validation.status(validation._ci([-0.1] * 36)) == "negative" and validation.status(None) == "unknown"


def test_cross_section_detects_a_trend_following_universe():
    # univers où les tendances persistent : les valeurs qui montent continuent ; le moteur (tendance + momentum) doit le voir
    world = _hist(0.0003, seed=99)
    universe = [{"symbol": f"S{i}", "hist": _hist(-0.0012 + 0.00008 * i, seed=i), "raw": make_fin(start_year=2010, years=14),
                 "sector": "Industrials", "currency": "EUR"} for i in range(35)]
    res = validation.run(universe, world)
    assert res["months"] > 10 and res["universe"] == 35
    assert res["ic"]["mean"] > 0.2 and res["status"] == "positive"
    assert res["quintile_spread"]["mean"] > 0 and res["components"]["trend"]["mean"] > 0
    assert set(res["by_verdict"]) and all("excess_vs_universe" in v for v in res["by_verdict"].values())
