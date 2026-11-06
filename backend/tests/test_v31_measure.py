"""v3.1 : actualités structurées et étude d'événements, archive des comptes, précision mesurée de l'IA, retenues à la source."""
import json
import time

import pytest

import store
from conftest import DAY, START, make_fin, make_hist
from services import accounts, ai_store, ensemble, events, financials, fundamentals, taxes
import catalog


def test_event_classification_closed_list():
    cases = {"LVMH beats estimates": "earnings_beat", "Kering déçoit au troisième trimestre": "earnings_miss",
             "TotalEnergies relève ses objectifs annuels": "guidance_up", "Stellantis cuts guidance": "guidance_down",
             "Air Liquide annonce un rachat d'actions": "buyback", "Bayer suspends dividend": "dividend_cut",
             "Remy Cointreau lance un avertissement sur ses résultats": "profit_warning", "Shares rise on Monday": None}
    for h, t in cases.items():
        assert events.classify(h) == t, h
    assert events.classify("Shares rise", json.dumps({"type": "buyback"})) == "buyback"      # type de l'IA prioritaire
    assert events.classify("LVMH beats estimates", json.dumps({"type": "moon"})) == "earnings_beat"


def test_abnormal_return_and_study():
    stock = [{"ts": START + i * DAY, "close": 100.0 * (1.10 if i >= 100 else 1.0), "adj": 100.0 * (1.10 if i >= 100 else 1.0)} for i in range(300)]
    bench = [{"ts": START + i * DAY, "close": 100.0, "adj": 100.0} for i in range(300)]
    ab = events.abnormal(stock, bench, START + 100 * DAY)
    assert ab["d0"] == pytest.approx(10.0) and ab["d20"] == pytest.approx(0.0)
    with store.connect() as conn:
        for i, h in enumerate(["ACME beats estimates", "ACME beats expectations again", "ACME raises its guidance"]):
            conn.execute("INSERT INTO articles (symbol, headline, summary, url, source, timestamp, sentiment_score) VALUES ('ACME', ?, '', ?, 'R', ?, 0)",
                         (h, f"https://ex/acme{i}", int(time.time()) - (30 - i) * 86400))
    evs = events.detected("ACME")
    assert [e["type"] for e in evs] == ["earnings_beat", "guidance_up"]               # doublon du même événement ignoré
    res = events.study(lambda s: stock, lambda s: bench, since_days=60)
    assert res["events"] >= 2


def test_for_symbol_flags_ignored_good_news(monkeypatch):
    ts = int(time.time()) - 10 * 86400
    with store.connect() as conn:
        conn.execute("INSERT INTO articles (symbol, headline, summary, url, source, timestamp, sentiment_score) VALUES ('GOOD', 'GOOD raises guidance', '', 'https://ex/g', 'R', ?, 0)", (ts,))
    days = [ts - (60 - i) * 86400 for i in range(80)]
    stock = [{"ts": d, "close": 100.0 - (2 if d >= ts - 6 * 3600 else 0)} for d in days]  # cours en baisse le jour de l'annonce
    bench = [{"ts": d, "close": 100.0} for d in days]
    e = events.for_symbol("GOOD", stock, bench)[0]
    assert e["type"] == "guidance_up" and e["reaction"] < 0 and e["note"] == "good_news_ignored"


def test_accounts_archive_grows_beyond_source_window(monkeypatch):
    first = make_fin(start_year=2018, years=4)["annual"]
    later = make_fin(start_year=2020, years=4)["annual"]
    calls = iter([first, later])
    monkeypatch.setattr(financials, "_fetch_annual", lambda s: next(calls))
    monkeypatch.setattr(financials, "_fetch_dividends", lambda s: [])
    financials.raw("ARCH", fetch=True)
    store.set_setting("fin:ARCH", "")  # cache expiré : nouvelle récupération (fenêtre de 4 ans décalée)
    data = financials.raw("ARCH", fetch=True)
    assert [y["date"][:4] for y in data["annual"]] == ["2018", "2019", "2020", "2021", "2022", "2023"]


def test_brier_and_measured_shrink(monkeypatch):
    assert ai_store.measured_shrink(0.5) == 0.5                                     # aucune échéance : correction par défaut
    old = int(time.time()) - 400 * 86400
    hist = lambda up: [{"ts": old - 10 * 86400 + i * 86400, "close": 100.0 * (1 + (0.002 if up else -0.002)) ** i} for i in range(420)]  # noqa: E731
    with store.connect() as conn:
        for i in range(40):
            sym = f"UP{i}" if i % 2 else f"DN{i}"
            prob = 90 if sym.startswith("UP") else 10                                # l'IA avait raison à chaque fois
            conn.execute("INSERT INTO ai_analyses (symbol, created_at, kind, runs, verdict, score, confidence, price, currency, engine, lang, payload)"
                         " VALUES (?, ?, 'single', 1, 'BUY', 10, 'low', ?, 'EUR', 'groq', 'fr', ?)",
                         (sym, old, hist(sym.startswith("UP"))[10]["close"], json.dumps({"outlook": {"prob_outperform": prob}})))
    flat = [{"ts": old - 10 * 86400 + i * 86400, "close": 100.0} for i in range(420)]
    b = ai_store.brier(fetch_hist=lambda s: flat if s == "CW8.PA" else hist(s.startswith("UP")))
    assert b["n"] == 40 and b["brier"] == pytest.approx(0.01)
    monkeypatch.setattr(ai_store, "brier", lambda: b)
    assert ai_store.measured_shrink(0.5) == 1.0                                     # IA précise : son avis compte pleinement
    monkeypatch.setattr(ai_store, "brier", lambda: {"n": 40, "brier": 0.26, "coin": 0.25})
    assert ai_store.measured_shrink(0.5) == 0.0                                     # pas mieux que pile ou face : ignorée


def test_withholding_by_country_and_envelope():
    ch = taxes.withholding("CH")
    assert ch["default"] == 35.0 and ch["treaty"] == 15.0 and ch["reclaimable"] == 20.0 and ch["credit"] == 12.8
    assert taxes.withholding("DE")["default"] == pytest.approx(26.375) and taxes.withholding("XX") is None
    assert "abattement" in taxes.rates()["av_note"]
    env = accounts.envelope(catalog.lookup("AAPL"), "AAPL")
    assert env["withholding"]["form"] == "W-8BEN"


def test_ensemble_capped_at_ten():
    for n in (25, 50, 100):
        with pytest.raises(ValueError):
            ensemble.start("MC.PA", n)
    assert ensemble.SIZES == (1, 5, 10)


def test_finnhub_surprises_revisions_insiders(monkeypatch):
    def fake(url, **p):
        if url.endswith("/earnings"):
            return [{"period": "2026-06-30", "actual": 1.2, "estimate": 1.0}]
        if url.endswith("/recommendation"):
            return [{"period": "2026-10-01", "strongBuy": 10, "buy": 5}, {}, {}, {"period": "2026-07-01", "strongBuy": 6, "buy": 5}]
        return {"data": [{"change": 1000}, {"change": -200}]}
    monkeypatch.setattr(fundamentals, "_get", fake)
    x = fundamentals._finnhub_extras("k", "AAPL")
    assert x["surprises"][0]["surprise_pct"] == 20.0 and x["recommendations"]["now"]["strongBuy"] == 10
    assert x["recommendations"]["before"]["strongBuy"] == 6 and x["insiders"] == {"bought": 1000, "sold": 200, "transactions": 2, "days": 90}
