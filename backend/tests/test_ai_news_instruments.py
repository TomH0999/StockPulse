import time
from datetime import date

import pytest

import catalog
import store
from services import ai_store, ensemble, headlines


def _r(v, s, opp=("Croissance du cloud",), thr=("Concurrence accrue",)):
    return {"verdict": v, "score": s, "confidence": "medium", "summary": f"{v} {s}", "opportunities": list(opp),
            "threats": list(thr), "catalysts": [], "engine": "groq"}


def test_ensemble_aggregate_frequencies():
    runs = [_r("BUY", 40)] * 7 + [_r("HOLD", 5)] * 2 + [_r("SELL", -50, opp=(), thr=("Dette élevée",))]
    a = ensemble.aggregate(runs)
    assert a["runs"] == 10 and a["majority"] == "BUY" and a["agreement"] == 70
    assert a["distribution"]["BUY"] == 70.0 and a["distribution"]["SELL"] == 10.0
    assert a["score"] == round((7 * 40 + 2 * 5 - 50) / 10) and a["score_min"] == -50
    assert a["verdict"] == "BUY" and a["bullish_share"] == 70 and a["bearish_share"] == 10
    assert a["opportunities"][0] == {"text": "Croissance du cloud", "frequency": 90}
    assert a["threats"][0]["frequency"] == 90 and a["threats"][1]["frequency"] == 10
    assert a["strength"] in ("moderate", "weak")  # 70 % d'accord mais forte dispersion des scores


def test_ensemble_split_is_weak_and_single_is_single():
    split = [_r("BUY", 30)] * 4 + [_r("HOLD", 0)] * 3 + [_r("REDUCE", -30)] * 3
    assert ensemble.aggregate(split)["strength"] == "weak"
    assert ensemble.aggregate([_r("BUY", 30)])["strength"] == "single"
    strong = [_r("BUY", 40 + i % 3) for i in range(25)]
    assert ensemble.aggregate(strong)["strength"] == "strong"


def test_ensemble_rejects_bad_size_and_no_keys():
    with pytest.raises(ValueError):
        ensemble.start("MC.PA", 7)
    with pytest.raises(ValueError):
        ensemble.start("MC.PA", 10)  # aucune clé configurée dans les tests


def test_saved_analysis_renewal_index():
    aid = ai_store.save("TEST.PA", "single", {"verdict": "BUY", "score": 30, "confidence": "high", "engine": "groq"}, 100.0, "EUR", "fr")
    fresh = ai_store.list_for("TEST.PA", 101.0)[0]
    assert fresh["id"] == aid and fresh["renewal"]["status"] == "ok" and fresh["payload"]["verdict"] == "BUY"
    assert ai_store.list_for("TEST.PA", 112.0)[0]["renewal"]["status"] == "renew"          # cours +12 %
    with store.connect() as conn:
        conn.execute("UPDATE ai_analyses SET created_at = ? WHERE id = ?", (int(time.time()) - 25 * 86400, aid))
    r = ai_store.list_for("TEST.PA", 100.0)[0]["renewal"]
    assert r["status"] == "watch" and r["reason"] == "age"                                   # 25 j / 30
    ai_store.delete(aid)
    assert not ai_store.list_for("TEST.PA")


def test_news_periods():
    d = date(2026, 11, 5)  # jeudi
    assert headlines.bounds("day", today=d) == (d, d)
    assert headlines.bounds("week", today=d) == (date(2026, 11, 2), d)
    assert headlines.bounds("month", today=d) == (date(2026, 11, 1), d)
    assert headlines.bounds("year", today=d) == (date(2026, 1, 1), d)
    assert headlines.bounds("custom", 2024, 2, today=d) == (date(2024, 2, 1), date(2024, 2, 29))
    assert headlines.bounds("custom", 2023, today=d) == (date(2023, 1, 1), date(2023, 12, 31))
    with pytest.raises(ValueError):
        headlines.bounds("custom")


def test_news_report_clusters_and_topics():
    ts = int(time.time()) - 3600
    rows = [("_MARKET", "La BCE baisse ses taux directeurs", "Le Monde"), ("_MARKET", "BCE : baisse des taux directeurs de 0,25 point", "Les Echos"),
            ("_TOP", "Taux directeurs : la BCE baisse encore", "BFM"), ("NVDA", "Nvidia publie des résultats record", "Reuters"),
            ("_MARKET", "Résultats record pour Nvidia", "Boursorama"), ("_MARKET", "Le pétrole recule légèrement", "Zonebourse")]
    with store.connect() as conn:
        for i, (sym, h, src) in enumerate(rows):
            conn.execute("INSERT INTO articles (symbol, headline, summary, url, source, timestamp, sentiment_score) VALUES (?, ?, '', ?, ?, ?, 0)",
                         (sym, h, f"https://ex/{i}", src, ts + i))
    r = headlines.report("day", fetch=False)
    top = r["stories"][0]
    assert top["source_count"] == 3 and top["headline_page"] and top["headline"].startswith("Taux directeurs")
    assert r["stories"][1]["symbols"] == ["NVDA"] and r["stories"][1]["source_count"] == 2
    assert r["topics"][0]["term"] in ("taux directeur", "bce baisse") and r["topics"][0]["count"] == 3


def test_catalog_instrument_kinds():
    kinds = {e["kind"] for e in catalog.entries()}
    assert {"stock", "etf", "index", "commodity", "fx", "crypto"} <= kinds
    assert catalog.lookup("^FCHI")["kind"] == "index" and catalog.lookup("BTC-EUR")["pea"] is False
    assert catalog.lookup("MC.PA")["kind"] == "stock" and catalog.lookup("CW8.PA")["kind"] == "etf"


def test_ensemble_job_runs_saves_and_stops_on_quota(market, monkeypatch):
    from services import ai_pool
    calls = []

    def fake(prompt, max_wait=0, background=False, temperature=0.3):
        calls.append(temperature)
        if len(calls) > 8:
            raise ai_pool.NoCapacity("groq : quota du jour atteint")
        return {"verdict": "BUY" if len(calls) % 4 else "HOLD", "score": 30, "confidence": "medium", "summary": "ok",
                "opportunities": ["Demande solide"], "threats": ["Valorisation élevée"]}, "groq"
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    monkeypatch.setattr(ai_pool, "complete_json", fake)
    job = ensemble.start("MC.PA", 10)
    for _ in range(100):
        if ensemble.status(job["id"])["finished"]:
            break
        time.sleep(0.05)
    st = ensemble.status(job["id"])
    res = st["result"]
    assert res and res["partial"] and res["runs"] == 8 and "quota" in res["stopped_reason"]
    assert set(calls) == {0.7} and res["distribution"]["BUY"] == 75.0
    saved = ai_store.list_for("MC.PA")[0]
    assert saved["kind"] == "ensemble" and saved["runs"] == 8 and saved["payload"]["majority"] == "BUY"
