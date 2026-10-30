import pytest

import store
from services import alerts, orders, portfolio


TODAY = "2026-01-15"


def deposit(amount, day="2026-01-02"):
    return portfolio.add_movement("deposit", day, amount=amount)


def hold(sym, qty, pru, fees=0.0, extra_cash=0.0, day="2026-01-05"):
    """Versement exact puis achat : la ligne a le PRU voulu (frais inclus)."""
    deposit(qty * pru + fees + extra_cash)
    return portfolio.add_movement("buy", day, sym, qty, pru, fees)


def test_ledger_cash_pru_realized_by_hand(market):
    deposit(10000)
    portfolio.add_movement("buy", "2026-01-03", "MC.PA", 10, 300, 5)       # coût 3 005
    portfolio.add_movement("buy", "2026-01-04", "MC.PA", 10, 340, 5)       # coût 3 405 -> 20 titres, coût 6 410
    s = portfolio.add_movement("sell", "2026-01-05", "MC.PA", 5, 400, 4)   # PRU 320,5 -> gain 5*(400-320,5)-4 = 393,5
    line = s["lines"][0]
    assert line["quantity"] == 15 and line["avg_price"] == pytest.approx(320.5)
    assert s["realized"] == pytest.approx(393.5)
    assert s["cash"] == pytest.approx(10000 - 3005 - 3405 + 2000 - 4)
    s = portfolio.add_movement("dividend", "2026-01-06", "MC.PA", amount=60)
    assert s["cash"] == pytest.approx(5646) and s["dividends"] == 60 and s["lines"][0]["dividends"] == 60
    # valeur au cours de 400 : 6 000 ; coût restant 15 * 320,5 = 4 807,5
    assert line["value"] == 6000 and line["cost"] == pytest.approx(4807.5) and line["pnl"] == pytest.approx(1192.5)
    assert line["pnl_percent"] == pytest.approx(24.81, abs=0.01)
    assert s["total"] == pytest.approx(6000 + 5646) and s["deposits"] == 10000
    assert s["lines"][0]["weight"] == pytest.approx(round(6000 / 11646 * 100, 1))
    assert s["gain"] == pytest.approx(11646 - 10000) and s["performance"] == pytest.approx(16.46)
    assert s["ceiling_left"] == 140000


def test_ledger_rejects_inconsistent_movements(market):
    with pytest.raises(ValueError, match="Liquidités insuffisantes"):
        portfolio.add_movement("buy", "2026-01-05", "MC.PA", 1, 400)
    deposit(1000)
    with pytest.raises(ValueError, match="supérieure"):
        portfolio.add_movement("sell", "2026-01-05", "MC.PA", 1, 400)
    with pytest.raises(ValueError):
        portfolio.add_movement("withdrawal", "2026-01-05", amount=5000)
    with pytest.raises(ValueError, match="Plafond"):
        portfolio.add_movement("deposit", "2026-01-05", amount=150000)
    with pytest.raises(ValueError, match="Date"):
        portfolio.add_movement("deposit", "2999-01-01", amount=1)
    for bad in [dict(type="buy", day=TODAY, symbol="MC.PA", quantity=0, price=1), dict(type="deposit", day=TODAY, amount=-5),
                dict(type="gift", day=TODAY, amount=5), dict(type="deposit", day=TODAY, amount=5, fees=-1)]:
        with pytest.raises(ValueError):
            portfolio.add_movement(**bad)
    s = portfolio.add_movement("buy", "2026-01-05", "MC.PA", 2, 400)
    dep = next(m for m in portfolio.movements() if m["type"] == "deposit")
    with pytest.raises(ValueError):
        portfolio.delete_movement(dep["id"])  # le versement finance l'achat
    buy = next(m for m in portfolio.movements() if m["type"] == "buy")
    assert portfolio.delete_movement(buy["id"])["cash"] == 1000


def test_backdated_sell_before_buy_is_rejected(market):
    deposit(1000)
    portfolio.add_movement("buy", "2026-01-10", "AI.PA", 2, 180)
    with pytest.raises(ValueError):
        portfolio.add_movement("sell", "2026-01-09", "AI.PA", 1, 180)


def test_summary_alerts_and_currency(market):
    market["changes"]["AI.PA"] = -12.0
    market["prices"]["USDEUR=X"] = 0.9
    hold("MC.PA", 10, 500)
    hold("AI.PA", 5, 150)
    hold("AAPL", 2, 200, extra_cash=300)
    s = portfolio.summary()
    by = {l["symbol"]: l for l in s["lines"]}
    assert by["MC.PA"]["value"] == 4000 and by["MC.PA"]["pnl_percent"] == -20 and "loss_15" in by["MC.PA"]["alerts"]
    assert "big_drop" in by["AI.PA"]["alerts"]
    aapl = by["AAPL"]
    assert "not_pea" in aapl["alerts"] and aapl["value"] == pytest.approx(2 * 300 * 0.9) and aapl["cost"] == pytest.approx(400 * 0.9)
    assert s["cash"] == pytest.approx(340)  # versement 700 € - achat 2 × 200 $ × 0,9
    assert s["total"] == pytest.approx(4000 + 900 + 540 + 340)
    assert sum(l["weight"] for l in s["lines"]) + s["cash"] / s["total"] * 100 == pytest.approx(100, abs=0.2)
    assert s["day_change"] == pytest.approx(10 * 1 + 5 * -12 + 2 * 1 * 0.9)


def test_legacy_data_is_migrated():
    import store
    store.set_setting("ledger_migrated", "")
    with store.connect() as conn:
        conn.execute("INSERT INTO holdings (symbol, quantity, avg_price) VALUES ('MC.PA', 2, 300)")
    store.set_setting("pea_deposits", "1000")
    store.set_setting("pea_cash", "500")
    led = portfolio.ledger()
    assert led["deposits"] == pytest.approx(1100) and led["cash"] == pytest.approx(500)
    assert led["positions"]["MC.PA"]["quantity"] == 2 and portfolio.movements()[0]["type"] == "deposit"


def test_diversification_and_rebalance(market):
    hold("MC.PA", 10, 400)
    d = portfolio.diversification(portfolio.summary())
    codes = {w["code"] for w in d["warnings"]}
    assert {"few_lines", "line_heavy"} <= codes
    assert "rebalance" in d


def test_benchmark_base_100(market):
    hold("MC.PA", 1, 400)
    b = portfolio.benchmark()
    assert b["series"][0]["portfolio"] == 100 and b["series"][0]["index"] == 100


def test_order_buy_plan_and_execute(market):
    deposit(2000)
    p = orders.plan("AI.PA", "buy", amount=1000)
    assert p["quantity"] == 5 and p["limit"] >= 180 and p["fees"] == pytest.approx(max(1.99, p["amount"] * 0.005), abs=0.01)
    assert p["stop_loss"] < 180 < p["target"]
    s = orders.execute("AI.PA", "buy", 5, 180, 4.5, day="2026-01-03")
    line = next(l for l in s["lines"] if l["symbol"] == "AI.PA")
    assert line["quantity"] == 5 and line["avg_price"] == pytest.approx(180.9)
    assert s["cash"] == pytest.approx(2000 - 904.5)
    s = orders.execute("AI.PA", "buy", 5, 200, 0, day="2026-01-04")
    assert next(l for l in s["lines"] if l["symbol"] == "AI.PA")["avg_price"] == pytest.approx((904.5 + 1000) / 10)


def test_order_warnings(market):
    assert "not_pea" in orders.plan("AAPL", "buy", 1000)["warnings"]
    assert "amount_too_small" in orders.plan("MC.PA", "buy", 50)["warnings"]
    assert "no_cash_data" in orders.plan("MC.PA", "buy")["warnings"]


def test_order_sell_reduce_and_errors(market):
    hold("MC.PA", 10, 300)
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
    assert not s["lines"] and s["cash"] == pytest.approx(3998) and s["realized"] == pytest.approx(998)
    assert len(orders.journal()) == 1


def test_fees_settings():
    orders.set_fees(0.1, 1)
    assert orders.fee(100) == 1 and orders.fee(5000) == 5 and orders.fee(0) == 0
    with pytest.raises(ValueError):
        orders.set_fees(10, 1)


def test_alerts_price_drop_verdict_once(market):
    hold("MC.PA", 1, 400)
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
    deposit(5000)
    p = orders.plan("AI.PA", "buy")
    assert p["amount"] <= 1000 and p["weight_after"] <= 20 and "line_heavy" not in p["warnings"]


def _verdicts(monkeypatch, data):
    from services import advisor, rebalance, screener
    monkeypatch.setattr(advisor, "cached_verdicts", lambda: {s: {"verdict": v, "score": sc, "confidence": "high", "engine": "local",
                                                                  "generated_at": 0} for s, (v, sc) in data.items()})
    monkeypatch.setattr(screener, "snapshot", lambda max_age=0: ({s: {"price": 100.0, "volatility": 25.0} for s in data}, 0))
    return rebalance


def test_rebalance_sells_trims_and_diversifies(market, monkeypatch):
    rb = _verdicts(monkeypatch, {"MC.PA": ("SELL", -60), "AI.PA": ("BUY", 30), "OR.PA": ("STRONG_BUY", 60),
                                 "SAP.DE": ("BUY", 40), "TTE.PA": ("BUY", 35), "BNP.PA": ("BUY", 30)})
    hold("MC.PA", 10, 400)
    hold("AI.PA", 40, 150, extra_cash=2000)
    p = rb.plan(portfolio.summary())
    by = {a["symbol"]: a for a in p["actions"]}
    assert by["MC.PA"]["side"] == "sell" and by["MC.PA"]["quantity"] == 10 and "verdict_sell" in by["MC.PA"]["reasons"]
    assert by["AI.PA"]["side"] == "reduce" and "over_line_cap" in by["AI.PA"]["reasons"]
    buys = [a for a in p["actions"] if a["side"] == "buy"]
    assert len(buys) >= 3 and all(a["target_weight"] <= 20.1 for a in p["actions"])
    assert p["actions"][0]["side"] != "buy"  # ventes avant achats
    assert sum(a["amount"] for a in buys) <= 2000 + 4000 + 40 * 180  # financés par liquidités + ventes
    assert max(p["after"].values()) <= 35.5


def test_rebalance_adapts_to_advice(market, monkeypatch):
    hold("MC.PA", 5, 400)
    hold("AI.PA", 10, 180)
    up = _verdicts(monkeypatch, {"MC.PA": ("STRONG_BUY", 70), "AI.PA": ("HOLD", 0)}).plan(portfolio.summary())
    down = _verdicts(monkeypatch, {"MC.PA": ("HOLD", 0), "AI.PA": ("STRONG_BUY", 70)}).plan(portfolio.summary())
    assert up["target"]["MC.PA"] > up["target"]["AI.PA"] and down["target"]["AI.PA"] > down["target"]["MC.PA"]


def test_rebalance_skips_tiny_trades_and_empty_pea(market, monkeypatch):
    rb = _verdicts(monkeypatch, {"MC.PA": ("HOLD", 0)})
    assert rb.plan(portfolio.summary())["actions"] == []
    hold("MC.PA", 1, 400)
    assert all(a["amount"] >= 150 or a["side"] == "sell" for a in rb.plan(portfolio.summary())["actions"])


def test_reduce_plan_quantity_override(market):
    hold("MC.PA", 10, 300)
    assert orders.plan("MC.PA", "reduce", quantity=3)["quantity"] == 3
    assert orders.plan("MC.PA", "reduce", quantity=50)["quantity"] == 10


def test_cap_respects_limits_and_budget():
    from services import rebalance
    sectors = {"A": "S1", "B": "S1", "C": "S2", "D": "S3", "E": "S4", "F": "S5"}
    w = rebalance._cap({"A": 10, "B": 9, "C": 1, "D": 1, "E": 1, "F": 0.5}, sectors, 0.97)
    assert all(v <= 0.2 + 1e-6 for v in w.values()) and sum(w.values()) <= 0.97 + 1e-6
    assert w["A"] + w["B"] <= 0.35 + 1e-6
    two = rebalance._cap({"A": 3, "C": 1}, sectors, 0.97)  # trop peu de lignes : pas de vente forcée en liquidités
    assert sum(two.values()) == pytest.approx(0.97) and two["A"] > two["C"]


def test_foreign_currency_buy_debits_euros(market):
    """Cas réel : 5 actions cotées 169 NOK ≈ 82 € ; les liquidités doivent baisser d'environ 82 €, pas de 845 €."""
    market["prices"]["CMBTO.OL"] = 169.0
    market["currency"]["CMBTO.OL"] = "NOK"
    market["prices"]["NOKEUR=X"] = 0.0973
    deposit(5000)
    s = portfolio.add_movement("buy", "2026-01-05", "CMBTO.OL", 5, 170.4, 7)
    line = s["lines"][0]
    assert s["cash"] == pytest.approx(5000 - 5 * 170.4 * 0.0973 - 7)
    assert line["value"] == pytest.approx(5 * 169 * 0.0973, abs=0.01) and line["cost"] == pytest.approx(5 * 170.4 * 0.0973 + 7, abs=0.01)
    assert line["avg_price"] == pytest.approx((5 * 170.4 * 0.0973 + 7) / 5, abs=1e-3)  # PRU en euros
    plan = orders.plan("CMBTO.OL", "buy", amount=1000)
    assert plan["quantity"] == pytest.approx((1000 - orders.fee(1000)) // (plan["limit"] * 0.0973))
    assert plan["amount"] == pytest.approx(plan["quantity"] * plan["limit"] * 0.0973, abs=0.01) and "currency" in plan["warnings"]
    s = portfolio.add_movement("sell", "2026-01-06", "CMBTO.OL", 5, 180, 0, fx=0.1)
    assert s["realized"] == pytest.approx(5 * 180 * 0.1 - (5 * 170.4 * 0.0973 + 7), abs=0.01)


def test_catalog_prefers_euro_listing():
    import catalog
    syms = set(catalog.symbols())
    assert "CMBT.BR" in syms and "CMBTO.OL" not in syms and "STLAP.PA" in syms and "STLAM.MI" not in syms
    assert "CMBTO.OL" in next(e for e in catalog.entries() if e["symbol"] == "CMBT.BR")["alternatives"]
