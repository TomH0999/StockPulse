import json
import time

import pytest

import store
from conftest import DAY, START, fake_quote, make_hist
from services import advisor, ai_pool


def arts(scores, start_ts):
    return [{"id": i, "headline": "Company beats estimates" if s > 0 else "Company plunges on probe", "summary": "", "source": "R",
             "timestamp": start_ts - i * 3600, "sentiment_score": s, "ai_sentiment": None} for i, s in enumerate(scores)]


def test_technicals_up_down_and_rsi_bounds():
    up, down = make_hist(600, drift=0.002), make_hist(600, drift=-0.002)
    tu, td = advisor.technicals(up), advisor.technicals(down)
    assert tu["price"] > tu["sma200"] and td["price"] < td["sma200"]
    assert tu["ret_1y"] > 0 > td["ret_1y"]
    assert 0 <= tu["rsi14"] <= 100 and 0 <= td["rsi14"] <= 100
    assert td["max_drawdown"] < -50 and advisor.technicals(make_hist(10)) == {}


def test_events_detect_shocks_and_link_articles():
    h = make_hist(800, shocks={400: -0.2, 600: 0.15})
    a = arts([-0.9], h[400]["ts"])
    evs, stats = advisor.events(h, a)
    kinds = {e["date"]: e for e in evs}
    assert any(e["change"] < -15 and e["kind"] == "drop" for e in evs)
    assert any(e["change"] > 10 and e["kind"] == "jump" for e in evs)
    drop = next(e for e in evs if e["change"] < -15)
    assert drop["headlines"] and drop["after_20d"] is not None
    assert stats["drop"] and stats["jump"] and kinds


@pytest.mark.parametrize("drift,news,expect_positive", [(0.002, 0.8, True), (-0.002, -0.8, False)])
def test_local_advice_direction(drift, news, expect_positive):
    h = make_hist(1500, drift=drift)
    now = h[-1]["ts"]
    r = advisor.local_advice("X", "fr", fake_quote("X"), h, arts([news] * 20, now), now=now)
    assert -100 <= r["score"] <= 100 and r["verdict"] in advisor.VERDICTS
    assert (r["score"] > 0) == expect_positive
    assert r["summary"] and r["confidence"] in ("low", "medium", "high")


@pytest.mark.parametrize("lang", ["fr", "en", "es", "zh"])
def test_all_languages(lang):
    h = make_hist(1500, shocks={300: -0.12, 700: 0.1, 1100: -0.15})
    r = advisor.local_advice("X", lang, {**fake_quote("X"), "dividend_yield": 4}, h, [], now=h[-1]["ts"])
    assert r["verdict_label"] and all(isinstance(x, str) for x in r["opportunities"] + r["threats"] + r["patterns"])


def test_fundamentals_effect():
    h = make_hist(1500)
    base = advisor.local_advice("X", "fr", fake_quote("X"), h, [], now=h[-1]["ts"])
    bad = advisor.local_advice("X", "fr", {**fake_quote("X"), "fundamentals": {"pe": -5, "debt_to_equity": 3}}, h, [], now=h[-1]["ts"])
    good = advisor.local_advice("X", "fr", {**fake_quote("X"), "fundamentals": {"pe": 10, "net_margin": 25, "roe": 20}}, h, [], now=h[-1]["ts"])
    assert bad["score"] < base["score"] < good["score"]
    assert any("PER" in t for t in bad["threats"])


@pytest.mark.parametrize("verdict,ret,hit", [("BUY", 5, True), ("BUY", -5, False), ("STRONG_BUY", 1, True), ("SELL", -3, True),
                                             ("REDUCE", 4, False), ("HOLD", 5, True), ("HOLD", -15, False)])
def test_hit_rules(verdict, ret, hit):
    assert advisor._hit(verdict, ret) is hit


def test_backtest_structure():
    h = make_hist(1500, shocks={300: -0.12, 700: 0.1})
    tr = advisor.backtest("X", fake_quote("X"), h, [])
    for k in ("1m", "3m", "6m"):
        assert tr[k]["n"] > 30 and 0 <= tr[k]["hit_rate"] <= 100


def test_verify_detects_invented_figures():
    h = make_hist(1500)
    r = advisor.local_advice("X", "en", fake_quote("X"), h, [], now=h[-1]["ts"])
    known = advisor._known_values(r, fake_quote("X"))
    good = {"summary": f"The stock trades at {r['technicals']['price']:.2f} €.", "opportunities": [], "threats": [], "patterns": []}
    bad = {"summary": "Revenue grew 987.6% and the target is 12345 €.", "opportunities": [], "threats": [], "patterns": []}
    assert advisor.verify({**r}, good, r["score"], known)["status"] == "verified"
    v = advisor.verify({**r}, bad, r["score"], known)
    assert v["status"] == "warning" and len(v["unverified"]) == 2
    assert "verdict_score_mismatch" in advisor.verify({**r, "verdict": "SELL", "score": 80}, good, 80, known)["notes"]
    assert "diverges_from_local" in advisor.verify({**r, "score": 90, "verdict": "STRONG_BUY"}, good, -30, known)["notes"]


def test_advise_full_path_cache_and_ai(market, monkeypatch):
    r = advisor.advise("MC.PA", "fr")
    assert r["engine"] == "local" and r["track_record"]["6m"]["n"] > 0 and r["technicals"]["dividend_yield"] == 3.5
    assert advisor.history_log("MC.PA")[0]["verdict"] == r["verdict"]
    assert advisor.advise("MC.PA", "fr")["generated_at"] == r["generated_at"]  # cache
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    monkeypatch.setattr(ai_pool, "complete_json", lambda p, *a: ({"verdict": "BUY", "score": 30, "confidence": "high", "summary": "OK",
                                                                   "opportunities": ["a"], "threats": ["b"], "patterns": [], "catalysts": ["c"],
                                                                   "article_sentiments": []}, "groq"))
    ai = advisor.advise("MC.PA", "fr")  # le cache local est ignoré quand une IA est disponible
    assert ai["engine"] == "groq" and ai["verdict"] == "BUY" and ai["verification"]["status"] in ("verified", "warning")

    def boom(p, *a):
        raise ai_pool.NoCapacity("quota")
    monkeypatch.setattr(ai_pool, "complete_json", boom)
    fallback = advisor.advise("MC.PA", "fr", force=True)
    assert fallback["engine"] == "local" and "quota" in fallback["ai_error"]


def test_invalid_ai_verdict_is_ignored(market, monkeypatch):
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    monkeypatch.setattr(ai_pool, "complete_json", lambda p, *a: ({"verdict": "MOON", "score": 999}, "groq"))
    r = advisor.advise("AI.PA", "en", force=True)
    assert r["verdict"] in advisor.VERDICTS and r["score"] == 100


def test_cached_verdicts_summary(market):
    advisor.advise("AI.PA", "fr")
    v = advisor.cached_verdicts()["AI.PA"]
    assert {"verdict", "score", "confidence", "engine", "generated_at", "hit_6m", "cagr", "volatility"} == set(v)
