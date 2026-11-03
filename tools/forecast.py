"""Test de prédiction à long terme : Groq vs Claude vs simple marché.

  python tools/forecast.py snapshot           # choisit 200 grandes valeurs + données du jour (forecasts/<date>/snapshot.json)
  GROQ_KEY=... python tools/forecast.py groq  # prédictions Groq (forecasts/<date>/groq.json)
  python tools/forecast.py evaluate           # compare chaque prédiction arrivée à échéance (forecasts/REPORT.md)

Horizons : 6, 12, 18 et 24 mois. Rendement prix en devise locale (hors dividendes).
La clé n'est jamais écrite sur disque."""
import json, math, os, statistics, sys, time
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("STOCKPULSE_NO_SCHEDULER", "1")
import requests  # noqa: E402
import catalog  # noqa: E402
from services import fx, yahoo  # noqa: E402

DIR = os.path.join(ROOT, "forecasts")
HORIZONS = [6, 12, 18, 24]
EUROPE = (".PA", ".DE", ".AS", ".MI", ".MC", ".BR", ".OL", ".ST", ".CO", ".HE", ".VI", ".WA", ".LS", ".IR", ".L", ".SW")


def _latest(name):
    runs = sorted(d for d in os.listdir(DIR) if os.path.exists(os.path.join(DIR, d, name)))
    return os.path.join(DIR, runs[-1]) if runs else None


def _stats(sym):
    h = yahoo.daily_history(sym, 5)
    c = [p["close"] for p in h]
    if len(c) < 260:
        return None
    meta = yahoo._chart(sym, "5y", "1d", 3600)["meta"]
    vol = statistics.pstdev([math.log(c[i] / c[i - 1]) for i in range(len(c) - 250, len(c)) if c[i - 1]]) * math.sqrt(252)
    traded = statistics.median(p["close"] * p["volume"] for p in h[-60:]) * (fx.rate(meta.get("currency")) or 0)
    r = lambda n: round((c[-1] / c[-1 - n] - 1) * 100, 1) if len(c) > n else None
    return {"price": round(c[-1], 4), "currency": meta.get("currency"), "ret_6m": r(126), "ret_1y": r(252), "ret_3y": r(756),
            "vol_1y": round(vol * 100, 1), "from_52w_high": round((c[-1] / max(c[-252:]) - 1) * 100, 1),
            "traded_eur": round(traded)}


def snapshot():
    from concurrent.futures import ThreadPoolExecutor
    cands = [e for e in catalog.entries() if e["core"] and e["market"] != "etf" and not e.get("status")]
    with ThreadPoolExecutor(10) as pool:
        stats = list(pool.map(lambda e: (e, _safe(_stats, e["symbol"])), cands))
    rows = [{"symbol": e["symbol"], "name": e["name"], "sector": e.get("sector"), "pea": e["pea"], **s} for e, s in stats if s]
    eu = sorted((r for r in rows if r["symbol"].endswith(EUROPE)), key=lambda r: -r["traded_eur"])[:100]
    world = sorted((r for r in rows if not r["symbol"].endswith(EUROPE)), key=lambda r: -r["traded_eur"])[:100]
    out = os.path.join(DIR, date.today().isoformat())
    os.makedirs(out, exist_ok=True)
    json.dump({"date": date.today().isoformat(), "horizons_months": HORIZONS,
               "selection": "100 valeurs européennes + 100 valeurs mondiales les plus échangées (montant quotidien médian en €)",
               "companies": eu + world}, open(os.path.join(out, "snapshot.json"), "w"), indent=1, ensure_ascii=False)
    print(out, len(eu), len(world))


def _safe(f, *a):
    try:
        return f(*a)
    except Exception:
        return None


PROMPT = """Tu es analyste actions long terme. Date : {day}. Pour chaque entreprise ci-dessous, prédis le rendement du COURS (en %, devise locale, hors dividendes) à 6, 12, 18 et 24 mois à partir d'aujourd'hui.
Données (prix, rendements passés en %, volatilité annuelle %, écart au plus haut 52 semaines %) :
{rows}
Réponds UNIQUEMENT en JSON : {{"predictions": [{{"symbol": "...", "r6": <nombre>, "r12": <nombre>, "r18": <nombre>, "r24": <nombre>, "confidence": "low|medium|high"}}]}}"""


def _row(c):
    return f'{c["symbol"]} | {c["name"]} | {c["sector"] or "?"} | {c["price"]} {c["currency"]} | 6m {c["ret_6m"]} | 1a {c["ret_1y"]} | 3a {c["ret_3y"]} | vol {c["vol_1y"]} | vs haut {c["from_52w_high"]}'


def groq():
    key = os.environ["GROQ_KEY"]
    run = _latest("snapshot.json")
    snap = json.load(open(os.path.join(run, "snapshot.json")))
    path = os.path.join(run, "groq.json")
    done = json.load(open(path)) if os.path.exists(path) else {"model": None, "predictions": {}}
    head = {"Authorization": f"Bearer {key}"}
    models = [m["id"] for m in requests.get("https://api.groq.com/openai/v1/models", headers=head, timeout=20).json()["data"]]
    model = next(m for m in ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3-32b") if m in models)
    done["model"], done["date"] = model, snap["date"]
    todo = [c for c in snap["companies"] if c["symbol"] not in done["predictions"]]
    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        prompt = PROMPT.format(day=snap["date"], rows="\n".join(map(_row, batch)))
        for attempt in range(5):
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=head, timeout=120, json={
                "model": model, "temperature": 0.2, "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}]})
            if res.status_code == 429:
                time.sleep(min(float(res.headers.get("retry-after", 20)), 120)); continue
            res.raise_for_status()
            preds = json.loads(res.json()["choices"][0]["message"]["content"])["predictions"]
            syms = {c["symbol"] for c in batch}
            for p in preds:
                if p.get("symbol") in syms:
                    done["predictions"][p["symbol"]] = {k: p.get(k) for k in ("r6", "r12", "r18", "r24", "confidence")}
            break
        json.dump(done, open(path, "w"), indent=1)
        print(len(done["predictions"]), "/", len(snap["companies"]))
        time.sleep(3)


def _price_on(sym, day):
    ts = datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()
    after = [p for p in yahoo.daily_history(sym, 10) if p["ts"] >= ts - 3 * 86400]
    return after[0]["close"] if after and after[0]["ts"] <= ts + 10 * 86400 else None


def _add_months(day, m):
    d = date.fromisoformat(day)
    y, mo = divmod(d.month - 1 + m, 12)
    return date(d.year + y, mo + 1, min(d.day, 28)).isoformat()


def _rank_ic(a, b):
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
        for k, i in enumerate(o): r[i] = k
        return r
    ra, rb = ranks(a), ranks(b)
    return round(statistics.correlation(ra, rb), 3) if len(a) > 2 else None


def evaluate():
    lines = ["# Bilan des prédictions long terme", "",
             "Rendement du cours en devise locale, hors dividendes. **Direction** = signe juste ; **IC** = corrélation de rang "
             "(capacité à classer les valeurs, 0 = hasard) ; **Écart** = erreur absolue moyenne en points ; "
             "**Top 20** = rendement moyen réel des 20 valeurs jugées les meilleures vs moyenne des 200.", ""]
    for run in sorted(d for d in os.listdir(DIR) if os.path.isdir(os.path.join(DIR, d))):
        rd = os.path.join(DIR, run)
        if not os.path.exists(os.path.join(rd, "snapshot.json")):
            continue
        snap = json.load(open(os.path.join(rd, "snapshot.json")))
        sources = {n.split(".")[0]: json.load(open(os.path.join(rd, n)))["predictions"] for n in ("groq.json", "claude.json")
                   if os.path.exists(os.path.join(rd, n))}
        lines += [f"## Prédictions du {snap['date']}", "", "| Horizon | Source | N | Direction | IC | Écart | Top 20 | Moyenne |", "|---|---|---|---|---|---|---|---|"]
        for h in HORIZONS:
            due = _add_months(snap["date"], h)
            if due > date.today().isoformat():
                lines.append(f"| {h} mois | à évaluer le {due} | | | | | | |"); continue
            real = {}
            for c in snap["companies"]:
                p = _safe(_price_on, c["symbol"], due)
                if p:
                    real[c["symbol"]] = (p / c["price"] - 1) * 100
            avg = statistics.mean(real.values()) if real else 0
            for src, preds in sources.items():
                pairs = [(float(preds[s][f"r{h}"]), r) for s, r in real.items() if s in preds and preds[s].get(f"r{h}") is not None]
                if not pairs:
                    continue
                p, r = zip(*pairs)
                hit = sum((a > 0) == (b > 0) for a, b in pairs) / len(pairs) * 100
                top = [b for a, b in sorted(pairs, key=lambda x: -x[0])[:20]]
                lines.append(f"| {h} mois | {src} | {len(pairs)} | {hit:.0f} % | {_rank_ic(p, r)} | {statistics.mean(abs(a - b) for a, b in pairs):.1f} | "
                             f"{statistics.mean(top):+.1f} % | {avg:+.1f} % |")
            json.dump({"due": due, "returns": {k: round(v, 2) for k, v in real.items()}}, open(os.path.join(rd, f"actual_{h}m.json"), "w"), indent=1)
        lines.append("")
    open(os.path.join(DIR, "REPORT.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    {"snapshot": snapshot, "groq": groq, "evaluate": evaluate}[sys.argv[1]]()
