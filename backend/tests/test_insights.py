import math

import pytest

import store
from conftest import DAY, START, make_hist
from services import advisor, ai_pool, insights


def _series(daily_returns, n=1300, start=100.0):
    price, out = start, []
    for i in range(n):
        price *= 1 + daily_returns(i)
        out.append({"ts": START + i * DAY, "timestamp": "2020-01-01T00:00:00Z", "close": price, "open": price, "high": price, "low": price, "volume": 1})
    return out


def test_risk_volatility_beta_and_position_size():
    bench = _series(lambda i: 0.01 * math.sin(i * 1.3))
    calm = _series(lambda i: 0.005 * math.sin(i * 1.3))          # moitié des mouvements de l'indice
    wild = _series(lambda i: 0.05 * math.sin(i * 1.3))           # cinq fois les mouvements
    rc, rw = insights.risk(calm, bench), insights.risk(wild, bench)
    assert rc["beta"] == pytest.approx(0.5, abs=0.05) and rw["beta"] == pytest.approx(5.0, abs=0.3)
    assert rc["volatility"] < rw["volatility"] and rc["level"] == "low" and rw["level"] == "very_high"
    assert rc["max_weight"] == insights.MAX_LINE and rw["max_weight"] < 10       # ligne plus petite si plus risquée
    assert rw["max_drawdown_5y"] < rc["max_drawdown_5y"] <= 0
    assert insights.risk(calm[:100]) == {}


def test_relative_strength_vs_benchmark_and_sector():
    bench = _series(lambda i: 0.0002)
    strong = _series(lambda i: 0.001)
    r = insights.relative("MC.PA", strong, bench, None, {})
    assert r["benchmark"] == "CAC 40" and r["excess_12m"] > 15 and r["momentum_12_1"] > 20
    assert insights.benchmark("SAP.DE")[1] == "STOXX Europe 600" and insights.benchmark("AAPL")[0] == "^GSPC"


def test_reliability_levels():
    risk = {"level": "medium"}
    assert insights.reliability(None, None, risk)["level"] == "insufficient"
    good = {"6m": {"n": 50, "hit_rate": 62}}
    assert insights.reliability(good, None, risk)["signal"] is True
    coin = {"6m": {"n": 50, "hit_rate": 50}}
    assert insights.reliability(coin, None, risk)["level"] == "weak"
    # les conseils réellement émis comptent double : un vrai historique mauvais fait tomber le signal
    assert insights.reliability(good, {"6m": {"n": 40, "hit_rate": 40}}, risk)["level"] == "weak"
    assert insights.reliability({"6m": {"n": 50, "hit_rate": 30}}, None, risk)["level"] == "contrarian"


def test_live_record_uses_real_past_advice():
    hist = _series(lambda i: 0.001, n=400)
    day0 = hist[100]["ts"]
    import time as _t
    d = _t.strftime("%Y-%m-%d", _t.localtime(day0 + 43200))
    with store.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO advice_history (symbol, day, verdict, score, price, engine) VALUES ('LIVE', ?, 'BUY', 30, ?, 'local')",
                     (d, hist[100]["close"]))
        conn.execute("INSERT OR REPLACE INTO advice_history (symbol, day, verdict, score, price, engine) VALUES ('LIVE', ?, 'SELL', -30, ?, 'local')",
                     (_t.strftime("%Y-%m-%d", _t.localtime(hist[150]["ts"] + 43200)), hist[150]["close"]))
    r = insights.live_record("LIVE", hist)
    assert r["n"] == 2 and r["1m"]["n"] == 2 and r["1m"]["hit_rate"] == 50   # l'achat juste, la vente fausse (cours en hausse)


def test_financial_health_scores():
    h = insights.health({"net_margin": 25, "roe": 30, "operating_margin": 30, "revenue_growth": 20, "earnings_growth": 25,
                         "debt_to_equity": 0.2, "pe": 12})
    assert h["profitability"] == 100 and h["growth"] == 100 and h["solidity"] == 100 and h["valuation"] > 90
    bad = insights.health({"net_margin": -5, "pe": -3, "debt_to_equity": 4})
    assert bad["profitability"] == 0 and bad["valuation"] == 0 and bad["solidity"] == 0 and bad["growth"] is None
    assert insights.health(None) is None


def test_outlook_shrinks_towards_market():
    o = advisor.outlook({"prob_outperform_12m": 90, "scenarios": {"bear": {"return_12m": -20, "probability": 20},
                         "base": {"return_12m": 15, "probability": 50}, "bull": {"return_12m": 40, "probability": 30}}})
    assert o["expected_12m"] == 15.5 and o["expected_12m_adjusted"] == pytest.approx(7 + 0.5 * 8.5, abs=0.06)
    assert o["prob_outperform_adjusted"] == 70
    assert advisor.outlook({"scenarios": {"bear": {}}}) is None


def test_advise_includes_insights_and_ai_outlook(market, monkeypatch):
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    seen = {}

    def fake(prompt, *a, **k):
        seen.update(prompt=prompt, effort=k.get("effort"))
        return {"verdict": "BUY", "score": 20, "confidence": "medium", "summary": "ok", "prob_outperform_12m": 60,
                "scenarios": {"bear": {"return_12m": -10, "probability": 25}, "base": {"return_12m": 8, "probability": 50},
                              "bull": {"return_12m": 25, "probability": 25}}}, "groq"
    monkeypatch.setattr(ai_pool, "complete_json", fake)
    r = advisor.advise("MC.PA", "fr", force=True)
    assert r["risk"]["volatility"] > 0 and "max_weight" in r["risk"] and r["reliability"]["level"] in ("reliable", "weak", "contrarian", "insufficient")
    assert r["relative"]["benchmark"] == "CAC 40" and r["outlook"]["prob_outperform_adjusted"] == 55
    assert seen["effort"] == "medium" and "LOCAL QUANTITATIVE PRIOR" in seen["prompt"] and "RISK (computed)" in seen["prompt"]
