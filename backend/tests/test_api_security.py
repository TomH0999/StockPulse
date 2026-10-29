import pytest
from fastapi.testclient import TestClient

import main
from services import ai_pool, fundamentals, health, screener

client = TestClient(main.app, base_url="http://127.0.0.1")


def test_ping_and_host_protection():
    assert client.get("/api/health").json() == {"status": "ok"}
    assert TestClient(main.app, base_url="http://evil.example").get("/api/health").status_code == 400


def test_cors_only_for_dev_origin():
    bad = client.options("/api/favorites", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers
    ok = client.options("/api/favorites", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_quote_errors(market):
    assert client.get("/api/market/quote/MC.PA").json()["price"] == 400
    assert client.get("/api/market/quote/NOPE").status_code == 404


def test_favorites_crud_and_order(market):
    client.post("/api/favorites", json={"symbol": "mc.pa", "name": "LVMH"})
    client.post("/api/favorites", json={"symbol": "AI.PA", "name": "Air Liquide"})
    client.post("/api/favorites", json={"symbol": "AI.PA", "name": "dup"})
    assert [f["symbol"] for f in client.get("/api/favorites").json()] == ["MC.PA", "AI.PA"]
    assert [f["symbol"] for f in client.put("/api/favorites/order", json=["AI.PA", "MC.PA"]).json()] == ["AI.PA", "MC.PA"]
    assert [f["symbol"] for f in client.delete("/api/favorites/AI.PA").json()] == ["MC.PA"]


def test_portfolio_and_orders_api(market):
    assert client.post("/api/portfolio/lines", json={"symbol": "NOPE", "quantity": 1, "avg_price": 1}).status_code == 404
    assert client.post("/api/portfolio/lines", json={"symbol": "MC.PA", "quantity": -1, "avg_price": 1}).status_code == 400
    s = client.post("/api/portfolio/lines", json={"symbol": "MC.PA", "quantity": 2, "avg_price": 350}).json()
    lid = s["lines"][0]["id"]
    assert client.put(f"/api/portfolio/lines/{lid}", json={"symbol": "MC.PA", "quantity": 3, "avg_price": 350}).json()["lines"][0]["quantity"] == 3
    assert client.put("/api/portfolio/account", json={"deposits": 5000, "cash": 1000}).json()["cash"] == 1000
    assert client.put("/api/portfolio/account", json={"deposits": -5, "cash": 0}).status_code == 400
    plan = client.get("/api/orders/plan", params={"symbol": "AI.PA", "side": "buy"}).json()
    assert plan["quantity"] > 0
    assert client.get("/api/orders/plan", params={"symbol": "AI.PA", "side": "sell"}).status_code == 400
    assert client.post("/api/orders/execute", json={"symbol": "MC.PA", "side": "sell", "quantity": 99, "price": 1}).status_code == 400
    s = client.post("/api/orders/execute", json={"symbol": "MC.PA", "side": "sell", "quantity": 3, "price": 400, "fees": 2}).json()
    assert s["lines"] == [] and client.get("/api/orders").json()[0]["side"] == "sell"
    assert client.put("/api/orders/fees", json={"pct": 50, "minimum": 1}).status_code == 400
    client.post("/api/portfolio/lines", json={"symbol": "MC.PA", "quantity": 1, "avg_price": 400})
    a = client.get("/api/portfolio/analysis").json()
    assert "diversification" in a and a["benchmark"]["series"]
    assert client.delete(f"/api/portfolio/lines/{client.get('/api/portfolio').json()['lines'][0]['id']}").json()["lines"] == []


def test_alerts_api(market):
    assert client.post("/api/alerts", json={"symbol": "MC.PA", "direction": "up", "price": 1}).status_code == 400
    lst = client.post("/api/alerts", json={"symbol": "MC.PA", "direction": "above", "price": 1}).json()
    assert client.get("/api/alerts/pending").json()[0]["type"] == "price"
    assert client.delete(f"/api/alerts/{lst[0]['id']}").json() == []


def test_advice_endpoints(market):
    r = client.get("/api/advice/MC.PA", params={"lang": "en"}).json()
    assert r["verdict"] and r["track_record"]
    assert client.get("/api/advice/MC.PA/history").json()[0]["verdict"] == r["verdict"]
    assert client.get("/api/track-record").json()["6m"]["symbols"] == 1
    assert client.get("/api/advice/NOPE").status_code == 404


def test_settings_endpoints(monkeypatch):
    monkeypatch.setattr(ai_pool, "_request", lambda e, p, max_tokens=4000: "{}")
    s = client.post("/api/settings/ai/keys", json={"provider": "groq", "key": "gsk_secret_value"}).json()
    assert s["keys"][0]["hint"] == "…alue" and "gsk_secret_value" not in str(s)
    assert client.post("/api/settings/ai/keys", json={"provider": "bad", "key": "x"}).status_code == 400
    assert client.put("/api/settings/auto", json={"enabled": False, "ai_hours": 9999}).json()["auto"]["ai_hours"] == 168
    assert client.delete(f"/api/settings/ai/keys/{s['keys'][0]['id']}").json()["keys"] == []
    monkeypatch.setattr(fundamentals, "_fetch", lambda e, s: None)
    assert client.post("/api/settings/data/keys", json={"provider": "fmp", "key": "x"}).status_code == 400
    assert client.get("/api/settings/data").json()["keys"] == []


def test_screener_and_catalog(monkeypatch):
    monkeypatch.setattr(screener, "snapshot", lambda max_age=0: ({"MC.PA": {"price": 1, "chg_1d": 2}}, 1))
    rows = client.get("/api/screener").json()["rows"]
    assert len(rows) > 2000 and next(r for r in rows if r["symbol"] == "MC.PA")["chg_1d"] == 2
    assert len(client.get("/api/catalog").json()) == len(rows)


def test_health_report(market, monkeypatch):
    monkeypatch.setattr(screener, "snapshot", lambda max_age=0: ({}, 0))
    monkeypatch.setattr(health, "_news", lambda: ("ok", "fake"))
    monkeypatch.setattr(health, "APP_VERSION", "dev")
    r = client.get("/api/health/full", params={"refresh": True}).json()
    ids = {c["id"]: c["status"] for c in r["checks"]}
    assert set(ids) == {"catalog", "quotes", "snapshot", "news", "ai", "database", "freshness", "verification", "version"}
    assert ids["snapshot"] == "error" and ids["database"] == "ok" and r["overall"] == "error"


@pytest.mark.parametrize("installed,latest,status", [("1.5.0", "v1.6.0", "warn"), ("1.6.0", "v1.6.0", "ok"), ("1.10.0", "v1.9.0", "ok")])
def test_version_check(monkeypatch, installed, latest, status):
    import time
    monkeypatch.setattr(health, "APP_VERSION", installed)
    health._cache["release"] = (time.time(), latest)
    assert health._version()[0] == status
