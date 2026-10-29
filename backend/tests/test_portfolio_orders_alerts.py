import pytest

import store
from services import alerts, orders, portfolio


def test_summary_math_alerts_and_currency(market):
    market["changes"]["AI.PA"] = -12.0  # -6,7 % sur la séance
    portfolio.upsert("MC.PA", 10, 500)
    portfolio.upsert("AI.PA", 5, 150)
    portfolio.upsert("AAPL", 2, 200)
    portfolio.set_account(8000, 300)
    s = portfolio.summary()
    mc = next(l for l in s["lines"] if l["symbol"] == "MC.PA")
    assert mc["value"] == 4000 and mc["pnl"] == -1000 and mc["pnl_percent"] == -20 and "loss_15" in mc["alerts"]
    ai = next(l for l in s["lines"] if l["symbol"] == "AI.PA")
    assert "big_drop" in ai["alerts"]
    aapl = next(l for l in s["lines"] if l["symbol"] == "AAPL")
    assert "not_pea" in aapl["alerts"] and aapl["weight"] is None  # hors euro : exclu des totaux
    assert s["value"] == 4900 and s["total"] == 5200 and s["performance"] == pytest.approx(-35.0)
    assert sum(l["weight"] for l in s["lines"] if l["weight"]) == pytest.approx(100, abs=0.2)


@pytest.mark.parametrize("q,p", [(0, 10), (-1, 10), (5, 0)])
def test_invalid_lines(q, p):
    with pytest.raises(ValueError):
        portfolio.upsert("MC.PA", q, p)


def test_account_validation():
    with pytest.raises(ValueError):
        portfolio.set_account(-1, 0)


def test_diversification_and_rebalance(market):
    portfolio.upsert("MC.PA", 10, 400)
    d = portfolio.diversification(portfolio.summary())
    codes = {w["code"] for w in d["warnings"]}
    assert {"few_lines", "line_heavy"} <= codes
    assert any(a["code"] == "trim" for a in d["actions"])


def test_benchmark_base_100(market):
    portfolio.upsert("MC.PA", 1, 400)
    b = portfolio.benchmark()
    assert b["series"][0]["portfolio"] == 100 and b["series"][0]["index"] == 100


def test_order_buy_plan_and_execute(market):
    portfolio.set_account(10000, 2000)
    p = orders.plan("AI.PA", "buy", amount=1000)
    assert p["quantity"] == 5 and p["limit"] >= 180 and p["fees"] == pytest.approx(max(1.99, p["amount"] * 0.005), abs=0.01)
    assert p["stop_loss"] < 180 < p["target"]
    s = orders.execute("AI.PA", "buy", 5, 180, 4.5)
    line = next(l for l in s["lines"] if l["symbol"] == "AI.PA")
    assert line["quantity"] == 5 and line["avg_price"] == pytest.approx(180.9)
    assert s["cash"] == pytest.approx(2000 - 904.5)
    s = orders.execute("AI.PA", "buy", 5, 200, 0)
    assert next(l for l in s["lines"] if l["symbol"] == "AI.PA")["avg_price"] == pytest.approx((904.5 + 1000) / 10)


def test_order_warnings(market):
    assert "not_pea" in orders.plan("AAPL", "buy", 1000)["warnings"]
    assert "amount_too_small" in orders.plan("MC.PA", "buy", 50)["warnings"]
    assert "no_cash_data" in orders.plan("MC.PA", "buy")["warnings"]


def test_order_sell_reduce_and_errors(market):
    portfolio.upsert("MC.PA", 10, 300)
    r = orders.plan("MC.PA", "reduce")
    assert 1 <= r["quantity"] <= 10 and r["realized_pnl"] > 0
    assert orders.plan("MC.PA", "sell")["quantity"] == 10
    with pytest.raises(ValueError):
        orders.plan("AI.PA", "sell")
    with pytest.raises(ValueError):
        orders.plan("MC.PA", "short")
    with pytest.raises(ValueError):
        orders.execute("MC.PA", "sell", 11, 400, 0)
    s = orders.execute("MC.PA", "sell", 10, 400, 2)
    assert not s["lines"] and s["cash"] == pytest.approx(3998)
    assert len(orders.journal()) == 1


def test_fees_settings():
    orders.set_fees(0.1, 1)
    assert orders.fee(100) == 1 and orders.fee(5000) == 5 and orders.fee(0) == 0
    with pytest.raises(ValueError):
        orders.set_fees(10, 1)


def test_alerts_price_drop_verdict_once(market):
    portfolio.upsert("MC.PA", 1, 400)
    alerts.add("MC.PA", "below", 450)
    alerts.add("AI.PA", "above", 999)
    market["changes"]["MC.PA"] = -30.0
    with store.connect() as conn:
        conn.execute("INSERT INTO advice_history VALUES ('MC.PA', '2026-01-01', 'BUY', 20, 1, 'local')")
        conn.execute("INSERT INTO advice_history VALUES ('MC.PA', '2026-01-02', 'SELL', -50, 1, 'local')")
    types = sorted(e["type"] for e in alerts.pending())
    assert types == ["drop", "price", "verdict"]
    assert alerts.pending() == []  # une seule notification par événement
    assert next(a for a in alerts.price_alerts() if a["symbol"] == "MC.PA")["triggered_at"]
    with pytest.raises(ValueError):
        alerts.add("MC.PA", "sideways", 1)


def test_buy_plan_respects_line_limit_on_new_pea(market):
    portfolio.set_account(5000, 5000)
    p = orders.plan("AI.PA", "buy")
    assert p["amount"] <= 1000 and p["weight_after"] <= 20 and "line_heavy" not in p["warnings"]
