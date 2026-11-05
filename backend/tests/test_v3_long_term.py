"""v3 : plusieurs comptes, fiscalité 2026, TRI et comparaison au MSCI World, journal de thèse, ETF vus de l'intérieur."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import catalog
import main
import store
from conftest import make_hist
from services import accounts, alerts, etf_exposure, history, orders, portfolio, taxes, theses

client = TestClient(main.app, base_url="http://127.0.0.1")


@pytest.fixture(autouse=True)
def clean():
    yield
    with store.connect() as conn:
        conn.execute("DELETE FROM pea_movements")
        conn.execute("DELETE FROM theses")
    store.set_setting("accounts", "")
    accounts.use("pea")


def test_accounts_are_isolated_and_cto_accepts_us_stocks(market):
    cto = accounts.create("CTO", "Compte-titres Boursorama")
    assert cto["id"].startswith("compte-titres") and len(accounts.all_accounts()) == 2
    portfolio.add_movement("deposit", "2026-01-02", amount=1000)                 # PEA
    accounts.use(cto["id"])
    portfolio.add_movement("deposit", "2026-01-02", amount=5000)
    s = portfolio.add_movement("buy", "2026-01-03", "AAPL", 2, 300)              # action américaine : autorisée en CTO
    assert s["account"]["type"] == "CTO" and "not_pea" not in s["lines"][0]["alerts"] and s["ceiling_left"] is None
    assert s["xirr"] is None or isinstance(s["xirr"], float)
    accounts.use("pea")
    assert portfolio.summary()["cash"] == 1000 and portfolio.summary()["lines"] == []
    assert "not_pea" in orders.plan("AAPL", "buy", 500)["warnings"]
    with pytest.raises(ValueError):
        accounts.create("PEA", "Deuxième PEA")                                    # un seul PEA par personne
    with pytest.raises(ValueError):
        accounts.delete(cto["id"])                                                # compte non vide


def test_api_account_parameter(market):
    cto = client.post("/api/accounts", json={"type": "CTO", "name": "CTO"}).json()
    assert client.post("/api/portfolio/movements", params={"account": cto["id"]},
                       json={"type": "deposit", "day": "2026-01-02", "amount": 700}).json()["cash"] == 700
    assert client.get("/api/portfolio").json()["cash"] == 0                       # PEA par défaut
    assert client.get("/api/portfolio", params={"account": cto["id"]}).json()["account"]["type"] == "CTO"
    lst = client.get("/api/accounts").json()
    assert {a["type"] for a in lst["accounts"]} == {"PEA", "CTO"} and lst["types"]["PEA_PME"] == "PEA-PME"


def test_pea_pme_ceiling_is_shared_with_pea(market):
    pme = accounts.create("PEA_PME", "PEA-PME")
    portfolio.add_movement("deposit", "2026-01-02", amount=150_000)
    with pytest.raises(ValueError):
        portfolio.add_movement("deposit", "2026-01-03", amount=1)                # PEA plein
    accounts.use(pme["id"])
    assert accounts.ceiling_left() == 75_000
    with pytest.raises(ValueError):
        portfolio.add_movement("deposit", "2026-01-03", amount=80_000)            # 225 000 € cumulés


def test_tax_rates_2026_and_cto_loss_carry_forward():
    assert taxes.PFU == 31.4 and taxes.PS == 18.6 and taxes.PS_AV == 17.2 and "2025-1403" in taxes.SOURCE
    opened_6y = (date.today() - timedelta(days=6 * 366)).isoformat()
    assert taxes.withdrawal("PEA", 1000, opened_6y)["tax"] == 186.0
    assert taxes.withdrawal("PEA", 1000, date.today().isoformat())["tax"] == 314.0
    assert taxes.withdrawal("AV", 1000, opened_6y)["rate"] == pytest.approx(30.0)
    assert taxes.withdrawal("PEA", 1000, None)["note"] == "pea_no_date"
    y = date.today().year
    r = taxes.cto_year({y - 2: -3000, y - 1: 1000, y: 5000}, {y: 200}, y)
    assert r["taxable_gains"] == 3000 and r["dividends"] == 200 and r["tax"] == pytest.approx(3200 * 0.314)
    old = taxes.cto_year({y - 12: -3000, y: 1000}, {}, y)
    assert old["taxable_gains"] == 1000 and old["losses_carried"] == []          # moins-value de plus de 10 ans : perdue
    keep = taxes.cto_year({y - 1: -3000, y: 1000}, {}, y)
    assert keep["taxable_gains"] == 0 and keep["losses_carried"][0]["amount"] == 2000


def test_cto_summary_reports_taxes(market):
    cto = accounts.create("CTO", "CTO")
    accounts.use(cto["id"])
    portfolio.add_movement("deposit", "2026-01-02", amount=5000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 5, 300)
    portfolio.add_movement("sell", "2026-01-05", "MC.PA", 5, 400)
    portfolio.add_movement("dividend", "2026-01-06", amount=50)
    t = portfolio.summary()["cto_tax"]
    assert t["year"] == date.today().year and (t["taxable_gains"] == pytest.approx(500) or t["year"] != 2026)


def test_xirr_and_world_comparison():
    assert history.xirr([("2024-01-01", -1000)], 1100, "2025-01-01") == pytest.approx(10.0, abs=0.1)
    assert history.xirr([("2024-01-01", -1000), ("2024-07-01", -1000)], 2000, "2025-01-01") == pytest.approx(0, abs=0.01)
    assert history.xirr([("2025-01-01", -1000)], 1000, "2025-01-10") is None     # moins d'un mois
    closes = {"2024-01-01": 100.0, "2024-07-01": 125.0, "2025-01-01": 150.0}
    assert history.world_value([("2024-01-01", -1000), ("2024-07-01", -500)], closes) == pytest.approx(1500 + 600)


def test_thesis_journal_and_annual_review(market):
    t = theses.save("MC.PA", "Marques de luxe sans équivalent, pouvoir de prix.", 700, "Si la marge opérationnelle passe sous 20 %")
    assert t["fair_value"] == 700 and t["next_review"] > date.today().isoformat() and not theses.due()
    with store.connect() as conn:
        conn.execute("UPDATE theses SET next_review = ?", ((date.today() - timedelta(days=1)).isoformat(),))
    assert [x["symbol"] for x in theses.due()] == ["MC.PA"]
    assert any(e["type"] == "thesis" for e in alerts.pending())
    with pytest.raises(ValueError):
        theses.save("MC.PA", "  ")
    assert client.get("/api/theses/MC.PA").json()["thesis"].startswith("Marques")


def test_etf_look_through_and_world_only_portfolio(market):
    cw8 = catalog.lookup("CW8.PA")
    assert etf_exposure.is_broad(cw8) and etf_exposure.exposure(cw8)["countries"]["US"] > 60
    lev = catalog.lookup("LQQ.PA")
    assert lev["leveraged"] and not etf_exposure.is_broad(lev) and accounts.eligible("PEA", lev) is False
    market["prices"]["CW8.PA"] = 500.0
    portfolio.add_movement("deposit", "2026-01-02", amount=10_000)
    portfolio.add_movement("buy", "2026-01-03", "CW8.PA", 19, 500)
    d = portfolio.diversification(portfolio.summary())
    codes = {w["code"] for w in d["warnings"]}
    assert "few_lines" not in codes and "line_heavy" not in codes                # 100 % MSCI World : déjà diversifié
    assert d["look_through"] and d["countries"]["US"] > 60 and "Technology" in d["sectors"]


def test_envelope_advice():
    assert accounts.envelope(catalog.lookup("MC.PA"), "MC.PA")["recommended"] == "PEA"
    us = accounts.envelope(catalog.lookup("AAPL"), "AAPL")
    assert us["recommended"] == "CTO" and "us_w8ben" in us["reasons"]
    assert "leveraged" in accounts.envelope(catalog.lookup("LQQ.PA"), "LQQ.PA")["reasons"]


def test_safe_tick_sizes():
    assert orders._tick(15) == 0.1 and orders._tick(75) == 1.0 and orders._tick(3) == 0.02 and orders._tick(0.7) == 0.01
    for p in (0.37, 3.3, 47.1, 152.3, 733.0):
        lim = orders._round(p * 1.003, up=True)
        assert lim >= p and abs(round(lim / orders._tick(p)) * orders._tick(p) - lim) < 1e-9


def test_liechtenstein_not_assumed_eligible():
    assert "LI" not in catalog.EEA and "NO" in catalog.EEA and "IS" in catalog.EEA
