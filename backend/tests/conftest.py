"""Environnement de test isolé : dossier de données temporaire, aucun accès réseau (sources simulées)."""
import math
import os
import sys
import tempfile

os.environ["STOCKPULSE_DATA_DIR"] = tempfile.mkdtemp(prefix="stockpulse-test-")
os.environ["STOCKPULSE_NO_SCHEDULER"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

import store  # noqa: E402

store.init()
DAY = 86400
START = 1_600_000_000


def make_hist(n=1500, drift=0.0005, shocks=(), seed=1, start=100.0):
    """Historique quotidien synthétique : tendance + oscillation + chocs {index: variation}."""
    price, out = start, []
    for i in range(n):
        price *= 1 + drift + 0.01 * math.sin(i * 0.7 + seed) + shocks.get(i, 0) if isinstance(shocks, dict) else 1 + drift
        out.append({"ts": START + i * DAY, "timestamp": f"2020-01-01T00:00:00Z", "close": round(price, 4),
                    "open": price, "high": price, "low": price, "volume": 1000})
    return out


def fake_quote(sym, price=100.0, currency="EUR", change=1.0):
    return {"symbol": sym.upper(), "name": f"{sym} SA", "short_name": sym, "currency": currency, "exchange": "Paris", "price": price,
            "change": change, "change_percent": change / price * 100, "volume": 1, "day_high": price, "day_low": price,
            "year_high": price * 1.2, "year_low": price * 0.8, "market_time": 2_000_000_000}


@pytest.fixture(autouse=True)
def clean_db():
    with store.connect() as conn:
        for table in ("articles", "favorites", "settings", "advice_cache", "holdings", "advice_history", "price_alerts",
                      "notified", "orders_log", "pea_movements"):
            conn.execute(f"DELETE FROM {table}")
    yield


@pytest.fixture
def market(monkeypatch):
    """Cours simulés : prices[sym] = prix ; currency[sym] = devise."""
    from services import yahoo
    prices, currency, changes = {"MC.PA": 400.0, "AI.PA": 180.0, "AAPL": 300.0}, {"AAPL": "USD"}, {}

    def quote(sym):
        sym = sym.upper()
        if sym not in prices:
            raise yahoo.YahooError(f"Symbole '{sym}' introuvable")
        return fake_quote(sym, prices[sym], currency.get(sym, "EUR"), changes.get(sym, 1.0))

    monkeypatch.setattr(yahoo, "quote", quote)
    monkeypatch.setattr(yahoo, "quotes", lambda syms: [quote(s) if s.upper() in prices else {"symbol": s, "error": True} for s in syms])
    monkeypatch.setattr(yahoo, "daily_history", lambda s, years=10: make_hist(shocks={300: -0.12, 700: 0.1, 1100: -0.15}))
    monkeypatch.setattr(yahoo, "history", lambda s, p="1y", ttl=60: make_hist(260))
    monkeypatch.setattr(yahoo, "dividend_yield", lambda s, p: 3.5)
    from services import news
    monkeypatch.setattr(news, "refresh", lambda *a, **k: None)
    return {"prices": prices, "currency": currency, "changes": changes}
