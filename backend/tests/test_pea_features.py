from datetime import date, timedelta

import pytest

from conftest import make_hist
from services import dividends, history, importer, objectives, orders, portfolio


def test_update_movement_revalidates(market):
    portfolio.add_movement("deposit", "2026-01-02", amount=1000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 2, 400, 2)
    buy = next(m for m in portfolio.movements() if m["type"] == "buy")
    s = portfolio.update_movement(buy["id"], quantity=1, price=380)
    assert s["lines"][0]["quantity"] == 1 and s["cash"] == pytest.approx(1000 - 382)
    with pytest.raises(ValueError):
        portfolio.update_movement(buy["id"], quantity=5)  # 2 000 € > 1 000 € versés
    dep = next(m for m in portfolio.movements() if m["type"] == "deposit")
    with pytest.raises(ValueError):
        portfolio.update_movement(dep["id"], amount=100)


@pytest.mark.parametrize("years_ago,rate,mature", [(2, 0.30, False), (6, 0.172, True)])
def test_opening_date_and_tax(market, years_ago, rate, mature):
    opened = (date.today() - timedelta(days=365 * years_ago + 2)).isoformat()
    objectives.update({"opened": opened})
    portfolio.add_movement("deposit", "2026-01-02", amount=1000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 2, 300)  # cours simulé 400 -> +200 €
    s = portfolio.summary()
    assert s["mature"] is mature and s["tax_rate"] == rate
    assert s["tax_if_withdrawn"] == pytest.approx(200 * rate)
    assert (s["days_to_five_years"] > 0) is (not mature)
    objectives.update({"opened": None})


def test_objectives_validation():
    with pytest.raises(ValueError):
        objectives.update({"max_line": 1})
    o = objectives.update({"etf_share": 40, "monthly_deposit": 300})
    assert o["etf_share"] == 40 and o["monthly_deposit"] == 300
    objectives.update({"etf_share": 0, "monthly_deposit": 0})


def test_costs_ttf_and_fx(market):
    objectives.update({"fx_fee_pct": 0.25})
    market["currency"]["AAPL"] = "USD"
    c_fr, c_us = orders.costs("AI.PA", "buy", 1000), orders.costs("AAPL", "buy", 1000, "USD")
    assert c_fr["ttf"] == 4.0 and c_fr["fx"] == 0
    assert c_us["ttf"] == 0 and c_us["fx"] == 2.5
    assert orders.costs("AI.PA", "sell", 1000)["ttf"] == 0  # la TTF ne s'applique qu'aux achats
    objectives.update({"fx_fee_pct": 0})


BOURSORAMA = """Date opération;Libellé;Type d'opération;Code ISIN;Quantité;Cours;Frais;Montant net
02/01/2026;VIREMENT;Versement;;;;;"5 000,00"
05/01/2026;LVMH;Achat;FR0000121014;2;"350,00";"1,99";"-701,99"
06/01/2026;AIR LIQUIDE;Achat comptant;FR0000120073;3;"170,50";"1,99";"-513,49"
10/01/2026;LVMH;Vente;FR0000121014;1;"400,00";"1,99";"398,01"
15/01/2026;AIR LIQUIDE;Dividende;FR0000120073;;;;"9,30"
16/01/2026;INCONNU;Opération bizarre;;;;;"1,00"
"""
TRADE_REPUBLIC = """date,type,isin,name,shares,price,fee,amount
2026-01-02,Deposit,,,,,,"2000.00"
2026-01-03,Buy,FR0000120073,Air Liquide,4,178.0,1.0,-713.0
"""


def test_import_boursorama_style(market):
    preview = importer.run(BOURSORAMA)
    assert preview["valid"] == 5 and preview["errors"] == 1 and "added" not in preview
    by = [r for r in preview["rows"] if not r["error"]]
    assert [r["type"] for r in by] == ["deposit", "buy", "buy", "sell", "dividend"]
    assert by[1]["symbol"] == "MC.PA" and by[1]["price"] == 350 and by[1]["fees"] == 1.99
    done = importer.run(BOURSORAMA, commit=True)
    assert done["added"] == 5
    s = portfolio.summary()
    lines = {l["symbol"]: l for l in s["lines"]}
    assert lines["MC.PA"]["quantity"] == 1 and lines["AI.PA"]["quantity"] == 3
    assert s["cash"] == pytest.approx(5000 - 701.99 - 513.49 + 398.01 + 9.30) and s["dividends"] == 9.30


def test_import_trade_republic_style(market):
    done = importer.run(TRADE_REPUBLIC, commit=True)
    assert done["added"] == 2 and portfolio.summary()["lines"][0]["quantity"] == 4


def test_import_rejects_unknown_format():
    with pytest.raises(ValueError):
        importer.run("foo;bar\n1;2\n")


def test_history_twr_neutralises_deposits(market, monkeypatch):
    days = [(date.today() - timedelta(days=10 - i)).isoformat() for i in range(11)]
    flat = {d: 100.0 for d in days}
    monkeypatch.setattr(history, "_closes", lambda s: flat if s != "MC.PA" else {d: 100.0 + i for i, d in enumerate(days)})
    portfolio.add_movement("deposit", days[0], amount=1000)
    portfolio.add_movement("buy", days[0], "MC.PA", 10, 100.0)
    portfolio.add_movement("deposit", days[5], amount=5000)  # gros versement : ne doit pas gonfler la performance
    h = history.series()
    assert h["points"][-1]["invested"] == 6000
    # rendement pondéré dans le temps : +5 % avant le versement, puis 6 050 € -> 6 100 € : 1,05 × 6100/6050 - 1
    assert h["performance"] == pytest.approx((1.05 * 6100 / 6050 - 1) * 100, abs=0.05)
    assert h["benchmark_performance"]["CAC 40"] == 0


def test_dividend_calendar(market, monkeypatch):
    portfolio.add_movement("deposit", "2026-01-02", amount=1000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 2, 400)
    portfolio.add_movement("dividend", "2026-01-04", "MC.PA", amount=10)
    last = date.today() - timedelta(days=200)
    monkeypatch.setattr(dividends, "_history", lambda s: [{"date": last, "amount": 7.5}])
    cal = dividends.calendar()
    assert cal["received_total"] == 10 and cal["upcoming"][0]["amount"] == 15 and cal["upcoming"][0]["estimated"]
    assert cal["yield"] == pytest.approx(15 / 800 * 100, abs=0.01)


def test_reset_portfolio(market):
    portfolio.add_movement("deposit", "2026-01-02", amount=1000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 1, 400, 2)
    s = portfolio.reset()
    assert not portfolio.movements() and not s["lines"] and s["cash"] == 0
