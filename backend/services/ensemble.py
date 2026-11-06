"""Analyses groupées : N analyses IA indépendantes d'une même valeur, puis synthèse des fréquences.

Chaque analyse reçoit les mêmes données mais une température un peu plus élevée : la dispersion des réponses
mesure la solidité du conseil. Un verdict retenu par 80 % des analyses est fiable ; un partage 40/30/30 signifie
que l'IA hésite et que le conseil ne vaut pas plus que le hasard."""
import re
import statistics
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from services import advisor, ai_pool, ai_store, news, portfolio, yahoo

# 10 au plus : des réponses répétées du même modèle mesurent sa constance (« stabilité »), pas sa justesse ;
# au-delà, on dépense du quota pour une fausse impression de solidité
SIZES = (1, 5, 10)
VERDICT_VALUE = {"STRONG_BUY": 2, "BUY": 1, "HOLD": 0, "REDUCE": -1, "SELL": -2}
_jobs: dict[str, dict] = {}
_STOP = set("""a au aux avec ce ces dans de des du en et est il la le les leur leurs mais ne ou par pas pour plus qui que sa se ses
son sur un une the and for with from that this its are was will has have been their more than into over under after amid
of to in on by at as an or be is it not""".split())


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zà-ÿ0-9]{3,}", text.lower()) if w not in _STOP}


def themes(lists: list[list[str]], runs: int, top: int = 6) -> list[dict]:
    """Regroupe les idées proches (mots en commun) et compte dans combien d'analyses elles reviennent."""
    groups: list[dict] = []
    for run, items in enumerate(lists):
        for text in items or []:
            if not isinstance(text, str) or not text.strip():
                continue
            w = _words(text)
            best = max(groups, key=lambda g: len(w & g["words"]) / (len(w | g["words"]) or 1), default=None)
            if best and len(w & best["words"]) / (len(w | best["words"]) or 1) >= 0.25:
                best["runs"].add(run)
                best["words"] |= w
                best["texts"].append(text)
            else:
                groups.append({"words": set(w), "runs": {run}, "texts": [text]})
    groups.sort(key=lambda g: -len(g["runs"]))
    return [{"text": min(g["texts"], key=len) if len(g["texts"]) > 2 else g["texts"][0],
             "frequency": round(len(g["runs"]) / runs * 100)} for g in groups[:top]]


def aggregate(results: list[dict], lang: str = "fr") -> dict:
    n = len(results)
    verdicts = Counter(r["verdict"] for r in results)
    scores = [r["score"] for r in results]
    mean = statistics.mean(scores)
    std = statistics.pstdev(scores) if n > 1 else 0.0
    majority, count = verdicts.most_common(1)[0]
    agreement = count / n * 100
    # Verdict de synthèse : moyenne des verdicts (pondérée), arrondie vers le verdict le plus proche
    avg_value = statistics.mean(VERDICT_VALUE[r["verdict"]] for r in results)
    consensus = min(VERDICT_VALUE, key=lambda v: abs(VERDICT_VALUE[v] - avg_value))
    if n == 1:
        strength = "single"
    elif agreement >= 70 and std <= 15:
        strength = "strong"
    elif agreement >= 50 and std <= 25:
        strength = "moderate"
    else:
        strength = "weak"
    direction = sum(1 for r in results if VERDICT_VALUE[r["verdict"]] > 0) / n * 100
    L = advisor.T.get(lang, advisor.T["en"])
    return {
        "runs": n, "verdict": consensus, "verdict_label": L["v"][consensus], "majority": majority, "agreement": round(agreement),
        "score": round(mean), "score_median": round(statistics.median(scores)), "score_std": round(std, 1),
        "score_min": min(scores), "score_max": max(scores),
        "ci95": [round(mean - 1.96 * std / n ** 0.5), round(mean + 1.96 * std / n ** 0.5)] if n > 1 else None,
        "bullish_share": round(direction), "bearish_share": round(sum(1 for r in results if VERDICT_VALUE[r["verdict"]] < 0) / n * 100),
        "distribution": {v: round(verdicts.get(v, 0) / n * 100, 1) for v in VERDICT_VALUE},
        "confidence_distribution": {c: round(v / n * 100) for c, v in Counter(r.get("confidence", "low") for r in results).items()},
        "strength": strength, "confidence": {"strong": "high", "moderate": "medium"}.get(strength, "low"),
        "opportunities": themes([r.get("opportunities") for r in results], n),
        "threats": themes([r.get("threats") for r in results], n),
        "catalysts": themes([r.get("catalysts") for r in results], n, 4),
        "summary": min((r for r in results if r["verdict"] == majority), key=lambda r: abs(r["score"] - mean)).get("summary", ""),
        "engines": dict(Counter(r["engine"] for r in results)),
        # Lecture stable si au moins 5 analyses et 70 % d'accord ; la justesse, elle, ne se mesure qu'à l'échéance
        "retained": n >= 5 and agreement >= 70,
        "outlook": _outlook([r.get("outlook") for r in results]),
    }


def _outlook(items: list) -> dict | None:
    items = [o for o in items if o]
    if not items:
        return None
    mean = lambda k: round(statistics.mean(o[k] for o in items if o.get(k) is not None), 1) if any(o.get(k) is not None for o in items) else None
    return {"expected_12m": mean("expected_12m"), "expected_12m_adjusted": mean("expected_12m_adjusted"),
            "prob_outperform": mean("prob_outperform"), "prob_outperform_adjusted": mean("prob_outperform_adjusted"), "n": len(items)}


def _one(prompt: str, i: int) -> dict:
    ai, provider = ai_pool.complete_json(prompt + f"\n(Independent analysis #{i + 1}.)", max_wait=60, temperature=0.7)
    v = ai.get("verdict") if ai.get("verdict") in VERDICT_VALUE else "HOLD"
    try:
        score = int(max(-100, min(100, float(ai.get("score", 0)))))
    except (TypeError, ValueError):
        score = 0
    return {"verdict": v, "score": score, "confidence": ai.get("confidence") if ai.get("confidence") in ("low", "medium", "high") else "low",
            "summary": str(ai.get("summary") or ""), "opportunities": ai.get("opportunities") or [], "threats": ai.get("threats") or [],
            "catalysts": ai.get("catalysts") or [], "engine": provider, "outlook": advisor.outlook(ai)}


def _run(job: dict, sym: str, n: int, lang: str):
    try:
        quote = yahoo.quote(sym)
        news.refresh(sym, quote.get("name", ""), backfill=False)
        hist, arts = yahoo.daily_history(sym), news.articles(sym)
        info = advisor.catalog.lookup(sym) or {}
        fin = advisor.financials.metrics(advisor.financials.raw(sym), quote.get("price"), info.get("sector"), hist, currency=quote.get("currency"))
        base = advisor.local_advice(sym, lang, quote, hist, arts, fin=fin, kind=info.get("kind", "stock"), leveraged=bool(info.get("leveraged")))
        try:
            pea = portfolio.context(sym)
        except Exception:
            pea = None
        prompt = advisor._prompt(base, arts[:20], lang, pea, compact=True)
        results, lock = [], threading.Lock()

        def work(i):
            if job["cancel"] or job.get("error"):
                return
            try:
                r = _one(prompt, i)
                with lock:
                    results.append(r)
                    job["done"] = len(results)
            except ai_pool.NoCapacity as e:
                job["error"] = str(e)
            except Exception as e:
                job["failed"] += 1
                job["last_error"] = str(e)[:200]

        with ThreadPoolExecutor(min(4, n)) as pool:
            list(pool.map(work, range(n)))
        if not results:
            raise RuntimeError(job.get("error") or job.get("last_error") or "Aucune analyse obtenue")
        agg = aggregate(results, lang)
        agg.update({"symbol": sym, "name": base["name"], "requested": n, "engine": "ensemble", "generated_at": int(time.time()),
                    "local_score": base["score"], "local_verdict": base["verdict"], "articles_analyzed": min(20, len(arts)),
                    "partial": len(results) < n, "stopped_reason": job.get("error")})
        agg["id"] = ai_store.save(sym, "ensemble", agg, quote.get("price"), quote.get("currency"), lang, runs=len(results))
        job["result"] = agg
    except Exception as e:
        job["error"] = str(e)[:300]
    finally:
        job["finished"] = True


def start(sym: str, n: int, lang: str = "fr") -> dict:
    if n not in SIZES:
        raise ValueError(f"Nombre d'analyses autorisé : {', '.join(map(str, SIZES))}")
    if not ai_pool.has_keys():
        raise ValueError("Aucune clé IA : ajoutez-en une dans Paramètres → Clés IA")
    if any(j["symbol"] == sym.upper() and not j["finished"] for j in _jobs.values()):
        raise ValueError("Une analyse groupée est déjà en cours pour cette valeur")
    job = {"id": uuid.uuid4().hex[:12], "symbol": sym.upper(), "total": n, "done": 0, "failed": 0, "finished": False,
           "cancel": False, "error": None, "result": None, "started_at": int(time.time())}
    _jobs[job["id"]] = job
    threading.Thread(target=_run, args=(job, sym.upper(), n, lang), daemon=True).start()
    return status(job["id"])


def status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        raise KeyError(job_id)
    return {k: v for k, v in job.items() if k != "cancel"}


def cancel(job_id: str):
    if job_id in _jobs:
        _jobs[job_id]["cancel"] = True
