"""Validation et calibration walk-forward du moteur de conseil, en coupe transversale.

  python tools/validate.py [nombre_de_valeurs]     (300 par défaut)

1. Mesure le moteur actuel sur les principales valeurs éligibles au PEA (corrélation de rang à 12 mois, quintiles, face à
   l'univers, au STOXX Europe 600 et au MSCI World) et écrit backend/catalog_sources/model_validation.json (fourni avec l'app).
2. Calibration walk-forward : pour chaque groupe du score, essaie des multiplicateurs sur la 1re moitié de la période
   (apprentissage) et mesure le meilleur jeu sur la 2de moitié (test, hors échantillon). Les pondérations ne sont changées
   dans le code que si le test s'améliore : à relancer avant chaque modification de pondération."""
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("STOCKPULSE_NO_SCHEDULER", "1")
import catalog  # noqa: E402
from services import advisor, validation, yahoo  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
syms = [e["symbol"] for e in catalog.entries() if e["core"] and e["kind"] == "stock" and e["pea"] and not e["status"]][:n]
universe = validation.load_universe(syms)
world, stoxx = yahoo.daily_history(advisor.BENCHMARK), yahoo.daily_history("^STOXX")
print(f"{len(universe)} valeurs chargées")

by_date = validation.collect(universe, world)
res = validation.evaluate(by_date, world, stoxx, universe_size=len(universe))
res["engine_version"] = advisor.ENGINE_VERSION
json.dump(res, open(os.path.join(ROOT, "backend", "catalog_sources", "model_validation.json"), "w"), indent=1)
print(json.dumps({k: res[k] for k in ("months", "universe", "ic", "status", "quintile_spread", "top_vs_universe", "top_vs_world",
                                      "top_vs_stoxx600", "components", "by_verdict")}, indent=1, ensure_ascii=False))

# Walk-forward : apprentissage sur la 1re moitié des dates, test sur la 2de
dates = sorted({p["ts"] for p in world})
first = res["first"] or dates[0]
last_usable = dates[-1] - 366 * 86400
mid = first + (last_usable - first) // 2
grid = [0.0, 0.5, 1.0, 1.5]
groups = ("valuation", "momentum", "quality", "trend")
best, best_ic = None, -9
for combo in itertools.product(grid, repeat=len(groups)):
    w = dict(zip(groups, combo), strength=1.0, growth=1.0)
    if not any(combo):
        continue
    r = validation.evaluate(by_date, world, weights=w, date_to=mid)
    if r["ic"] and r["ic"]["mean"] > best_ic:
        best, best_ic = w, r["ic"]["mean"]
base_train = validation.evaluate(by_date, world, date_to=mid)
base_test = validation.evaluate(by_date, world, date_from=mid)
test = validation.evaluate(by_date, world, weights=best, date_from=mid)
print("\nWalk-forward (IC à 12 mois)")
print(f"  pondérations actuelles : apprentissage {base_train['ic']}  test {base_test['ic']}")
print(f"  meilleur jeu {best} : apprentissage {best_ic:.3f}  test {test['ic']}")
print("  -> à appliquer seulement si le test s'améliore nettement (sinon : surajustement)")
