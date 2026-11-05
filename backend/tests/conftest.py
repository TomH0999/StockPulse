"""Environnement de test isolé : dossier de données temporaire, aucun accès réseau (sources simulées)."""
import math
import os
import time
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
    from services import financials, news
    monkeypatch.setattr(news, "refresh", lambda *a, **k: None)
    fin = {}  # comptes simulés par valeur (aucun par défaut : pas d'accès réseau)
    monkeypatch.setattr(financials, "raw", lambda s, fetch=True: fin.get(s.upper()))
    return {"prices": prices, "currency": currency, "changes": changes, "fin": fin}


def make_fin(start_year=2016, years=4, revenue=1000.0, growth=0.08, margin=0.2, fcf_margin=0.18, net_debt=200.0,
             shares=100.0, eps_growth=None, dps=2.0, div_growth=0.05):
    """Comptes annuels simulés au format de services.financials.raw (montants en millions)."""
    annual = []
    for i in range(years):
        rev = revenue * (1 + growth) ** i
        ni = rev * margin
        annual.append({"date": f"{start_year + i}-12-31", "TotalRevenue": rev, "GrossProfit": rev * 0.5, "OperatingIncome": rev * margin * 1.3,
                       "EBIT": rev * margin * 1.3, "EBITDA": rev * margin * 1.6, "NetIncome": ni, "DilutedEPS": ni / shares,
                       "OrdinarySharesNumber": shares, "FreeCashFlow": rev * fcf_margin, "NetDebt": net_debt,
                       "InvestedCapital": rev * 0.8, "InterestExpense": rev * 0.01, "TaxRateForCalcs": 0.25,
                       "CashDividendsPaid": -dps * shares, "StockholdersEquity": rev})
    divs = [[int(time.mktime((y, 6, 1, 0, 0, 0, 0, 0, 0))), dps * (1 + div_growth) ** (y - 2005)] for y in range(2005, start_year + years)]
    return {"annual": annual, "dividends": divs, "fetched_at": int(time.time()), "v": 1}
