"""Moteur de conseil long terme : fondamentaux et valorisation (60), qualité (25), tendance de fond (15) ;
backtest face au MSCI World ; l'IA explique sans décider."""
import pytest

import store
from conftest import DAY, START, fake_quote, make_fin, make_hist
from services import advisor, ai_pool, financials


def arts(scores, start_ts):
    return [{"id": i, "headline": "Company beats estimates" if s > 0 else "Company plunges on probe", "summary": "", "source": "R",
             "timestamp": start_ts - i * 3600, "sentiment_score": s, "ai_sentiment": None} for i, s in enumerate(scores)]


def _metrics(raw, price=100.0, sector="Industrials", hist=None):
    return financials.metrics(raw, price, sector, hist, as_of=2_000_000_000)


def test_technicals_total_return_and_bounds():
    up, down = make_hist(600, drift=0.002), make_hist(600, drift=-0.002)
    tu, td = advisor.technicals(up), advisor.technicals(down)
    assert tu["price"] > tu["sma200"] and td["price"] < td["sma200"]
    assert tu["ret_1y"] > 0 > td["ret_1y"] and td["max_drawdown"] < -50 and advisor.technicals(make_hist(10)) == {}
    divs = [{**p, "adj": p["close"] * (1 + 0.0002 * i)} for i, p in enumerate(make_hist(600))]  # dividendes réinvestis
    assert advisor.technicals(divs)["cagr"] > advisor.technicals(make_hist(600))["cagr"]


def test_events_detect_shocks_and_link_articles():
    h = make_hist(800, shocks={400: -0.2, 600: 0.15})
    evs, stats = advisor.events(h, arts([-0.9], h[400]["ts"]))
    drop = next(e for e in evs if e["change"] < -15)
    assert drop["headlines"] and drop["after_20d"] is not None and any(e["change"] > 10 for e in evs) and stats["drop"]


def test_trend_is_capped_and_news_rsi_seasonality_do_not_score():
    h = make_hist(1500, drift=0.002, shocks={300: -0.12, 700: 0.1})
    now = h[-1]["ts"]
    quiet = advisor.local_advice("X", "fr", fake_quote("X"), h, [], now=now)
    noisy = advisor.local_advice("X", "fr", fake_quote("X"), h, arts([0.9] * 30, now), now=now)
    assert quiet["score"] == noisy["score"] <= 15            # actualités : information seulement ; tendance plafonnée
    assert set(quiet["components"]) == {"trend"} and quiet["coverage"] == 0 and quiet["confidence"] == "low"
    text = " ".join(quiet["patterns"] + quiet["opportunities"] + quiet["threats"])
    assert "RSI" not in text and "rebondi" not in text and "novembre" not in text.lower()
    assert any("Comptes de l'entreprise indisponibles" in p for p in quiet["patterns"])


def test_quality_company_scores_high_and_weak_company_low():
    h = make_hist(1500)
    now = h[-1]["ts"]
    good = _metrics(make_fin(growth=0.10, margin=0.22, fcf_margin=0.2, net_debt=-50), price=60.0, hist=h)
    bad = _metrics(make_fin(growth=-0.05, margin=0.02, fcf_margin=-0.05, net_debt=900, shares=100), price=60.0, hist=h)
    g = advisor.local_advice("X", "fr", fake_quote("X"), h, [], now=now, fin=good)
    b = advisor.local_advice("X", "fr", fake_quote("X"), h, [], now=now, fin=bad)
    assert g["score"] > 40 > b["score"] and g["verdict"] in ("BUY", "STRONG_BUY") and b["verdict"] in ("SELL", "REDUCE", "HOLD")
    assert g["components"]["valuation"] <= 30 and g["components"]["quality"] <= 25 and g["coverage"] == 1
    assert any("free cash-flow" in t for t in g["opportunities"]) and any("Endettement" in t for t in b["threats"])
    assert any("ROIC" in t for t in g["opportunities"])


def test_financial_sector_uses_roe_not_debt():
    m = _metrics(make_fin(net_debt=5000, margin=0.15), sector="Financial Services")
    assert m["financial_sector"] and m["net_debt_ebitda"] is None and m["roic"] is None and m["roe_avg"] is not None
    r = advisor.local_advice("X", "fr", fake_quote("X"), make_hist(600), [], fin=m)
    assert "strength" not in r["components"] and not any("Endettement" in t for t in r["threats"])


def test_valuation_against_company_history():
    h = make_hist(2600, drift=0.0)  # cours stable sur 7 ans : le PER baisse quand les bénéfices montent
    raw = make_fin(start_year=2021, growth=0.15)
    m = financials.metrics(raw, h[-1]["close"], "Industrials", h, as_of=h[-1]["ts"] + 400 * DAY)
    assert m["pe_history_n"] >= 1 and m["pe"] < m["pe_history_median"]


def test_point_in_time_accounts():
    raw = make_fin(start_year=2020)
    assert financials.metrics(raw, 100, None, None, as_of=1_577_836_800) is None or \
        financials.metrics(raw, 100, None, None, as_of=1_577_836_800)["years"] == 0   # 01/01/2020 : aucun compte publié
    m21 = financials.metrics(raw, 100, None, None, as_of=1_625_097_600)                    # 01/07/2021 : 2020 publié seulement
    assert m21["years"] == 1 and m21["last_year"] == "2020"


def test_dividend_record():
    import calendar
    june = lambda y: calendar.timegm((y, 6, 1, 0, 0, 0))
    divs = [(june(2015 + i), 1.0 + 0.1 * i) for i in range(10)]          # 2015 à 2024, en hausse chaque année
    rec = financials.dividend_record(divs, june(2025))
    assert rec["years_paid"] == 10 and rec["years_without_cut"] == 9 and rec["growth_5y"] > 0 and rec["paid_last_year"]
    cut = financials.dividend_record(divs[:-1] + [(june(2024), 0.5)], june(2025))
    assert cut["years_without_cut"] == 0 and financials.dividend_record([], june(2025)) == {"years_paid": 0}


def test_etf_and_leveraged_have_no_buy_sell_verdict():
    h = make_hist(1500, drift=0.003)
    r = advisor.local_advice("CW8.PA", "fr", fake_quote("CW8.PA"), h, [], kind="etf")
    assert r["verdict"] == "HOLD" and abs(r["score"]) < 15 and any("ETF" in p for p in r["patterns"])
    lev = advisor.local_advice("LQQ.PA", "fr", fake_quote("LQQ.PA"), h, [], kind="etf", leveraged=True)
    assert "levier" in lev["threats"][0]


def test_backtest_vs_world_base_rate():
    h = make_hist(3000, drift=0.0006)
    world = make_hist(3000, drift=0.0003)
    tr = advisor.backtest("X", fake_quote("X"), h, None, None, "stock", world)
    assert set(tr) == {"1y", "3y", "5y"}
    one = tr["1y"]
    assert one["n"] > 30 and one["engine"] == "trend_only" and one["base"] > 50   # la valeur a souvent battu le monde
    if one["buy_hit"] is not None:
        assert one["edge"] == pytest.approx(one["buy_hit"] - one["base"], abs=0.2) or one["sell_n"]
    assert advisor.backtest("X", fake_quote("X"), h, None) == {}


def test_verify_detects_invented_figures():
    h = make_hist(1500)
    r = advisor.local_advice("X", "en", fake_quote("X"), h, [], now=h[-1]["ts"])
    known = advisor._known_values(r, fake_quote("X"))
    good = {"summary": f"The stock trades at {r['technicals']['price']:.2f} €.", "opportunities": [], "threats": [], "patterns": []}
    bad = {"summary": "Revenue grew 987.6% and the target is 12345 €.", "opportunities": [], "threats": [], "patterns": []}
    assert advisor.verify({**r}, good, r["score"], known)["status"] == "verified"
    v = advisor.verify({**r}, bad, r["score"], known)
    assert v["status"] == "warning" and len(v["unverified"]) == 2
    assert "diverges_from_local" in advisor.verify({**r, "score": 90, "verdict": "STRONG_BUY"}, good, -30, known)["notes"]


def test_ai_explains_but_never_decides(market, monkeypatch):
    market["fin"]["MC.PA"] = make_fin()
    r = advisor.advise("MC.PA", "fr")
    assert r["engine"] == "local" and r["financials"]["years"] == 4 and set(r["track_record"]) == {"1y", "3y", "5y"}
    assert advisor.history_log("MC.PA")[0]["verdict"] == r["verdict"]
    assert advisor.advise("MC.PA", "fr")["generated_at"] == r["generated_at"]  # cache
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    monkeypatch.setattr(ai_pool, "complete_json", lambda p, *a, **k: ({"verdict": "SELL", "score": -90, "confidence": "high", "summary": "Vendez",
                                                                   "opportunities": [], "threats": ["b"], "catalysts": ["c"]}, "groq"))
    ai = advisor.advise("MC.PA", "fr")
    assert ai["verdict"] == r["verdict"] and ai["score"] == r["score"]          # le verdict reste celui du calcul
    assert ai["ai_view"]["verdict"] == "SELL" and ai["ai_view"]["provider"] == "groq" and ai["ai_view"]["verification"]
    assert "diverges_from_local" in ai["ai_view"]["verification"]["notes"] or r["score"] < 0

    def boom(p, *a, **k):
        raise ai_pool.NoCapacity("quota")
    monkeypatch.setattr(ai_pool, "complete_json", boom)
    fallback = advisor.advise("MC.PA", "fr", force=True)
    assert "ai_view" not in fallback and "quota" in fallback["ai_error"]


def test_invalid_ai_verdict_is_ignored(market, monkeypatch):
    monkeypatch.setattr(ai_pool, "has_keys", lambda: True)
    monkeypatch.setattr(ai_pool, "complete_json", lambda p, *a, **k: ({"verdict": "MOON", "score": 999}, "groq"))
    r = advisor.advise("AI.PA", "en", force=True)
    assert r["ai_view"]["verdict"] in advisor.VERDICTS and r["ai_view"]["score"] == 100


def test_cached_verdicts_summary(market):
    market["fin"]["AI.PA"] = make_fin()
    advisor.advise("AI.PA", "fr")
    v = advisor.cached_verdicts()["AI.PA"]
    assert {"verdict", "score", "edge_1y", "fcf_yield", "roic_avg", "quality", "valuation", "div_streak"} <= set(v)
    assert v["fcf_yield"] is not None and v["quality"] is not None
