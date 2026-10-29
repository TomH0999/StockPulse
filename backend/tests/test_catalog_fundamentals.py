import json
import time

import pytest

import catalog
import store
from services import catalog_updater, fundamentals


def test_base_catalog_integrity():
    e = catalog.entries()
    syms = [x["symbol"] for x in e]
    assert len(e) > 2000 and len(syms) == len(set(syms))
    assert len(catalog.core_symbols()) > 500
    by = {x["symbol"]: x for x in e}
    assert by["MC.PA"]["pea"] and by["MC.PA"]["isin"].startswith("FR")
    assert not by["AAPL"]["pea"] and by["AAPL"]["country"] == "US"
    assert not by["2020.OL"]["pea"]  # cotée à Oslo mais siège aux Bermudes
    assert by["CW8.PA"]["pea"]  # ETF éligible


@pytest.mark.parametrize("entry,pea,country", [
    ({"symbol": "X.PA", "name": "x", "isin": "LU0000000000"}, True, "LU"),
    ({"symbol": "X.PA", "name": "x", "isin": "US0000000000"}, False, "US"),
    ({"symbol": "X.DE", "name": "x"}, True, "DE"),
    ({"symbol": "X.L", "name": "x"}, False, "GB"),
    ({"symbol": "X.SW", "name": "x"}, False, "CH"),
    ({"symbol": "XYZ", "name": "x"}, False, "US"),
    ({"symbol": "X.PA", "name": "x", "pea": True, "isin": "IE0000000000"}, True, "IE"),
])
def test_pea_rules(entry, pea, country):
    e = catalog._make(entry, "europe")
    assert e["pea"] is pea and e["country"] == country


def test_update_detects_new_suspended_delisted(monkeypatch):
    now = time.time()
    monkeypatch.setattr(catalog_updater, "candidates", lambda: {
        "NEW.PA": {"symbol": "NEW.PA", "name": "New SA", "isin": "FR0000000001", "file": "europe"},
        "OLD.PA": {"symbol": "OLD.PA", "name": "Old", "file": "europe"},
    })
    monkeypatch.setattr(catalog_updater, "quotes_meta", lambda syms: {
        "NEW.PA": {"name": "New SA", "time": now}, "OK.PA": {"name": "Ok", "time": now}, "OLD.PA": {"name": "Old", "time": now - 90 * 86400}})
    monkeypatch.setattr(catalog_updater, "sectors", lambda syms: {s: "Technology" for s in syms})
    r = catalog_updater.update({"OK.PA": {}, "OLD.PA": {}, "GONE.PA": {}})
    assert [a["symbol"] for a in r["added"]] == ["NEW.PA"] and r["added"][0]["sector"] == "Technology"
    assert r["status"]["OLD.PA"]["status"] == "suspended" and r["status"]["GONE.PA"]["status"] == "delisted"
    assert "OK.PA" not in r["status"]


def test_refresh_merges_updates(monkeypatch):
    monkeypatch.setattr(catalog_updater, "update", lambda known: {
        "added": [{"symbol": "ZZNEW.PA", "name": "Zz New", "isin": "FR0000000002", "file": "europe"}],
        "status": {"MC.PA": {"status": "delisted"}}, "updated_at": int(time.time())})
    catalog._entries = None
    try:
        assert catalog.refresh_from_sources() == {"added": 1, "flagged": 1}
        by = {e["symbol"]: e for e in catalog.entries()}
        assert by["ZZNEW.PA"]["new"] and by["ZZNEW.PA"]["pea"]
        assert by["MC.PA"]["status"] == "delisted" and "MC.PA" not in catalog.core_symbols()
        assert not catalog.needs_update()
    finally:
        import os
        os.remove(catalog.UPDATES_PATH)
        catalog._entries = None


FMP = {"ratios-ttm": [{"priceToEarningsRatioTTM": 25.5, "netProfitMarginTTM": 0.24, "debtToEquityRatioTTM": 1.5}],
       "key-metrics-ttm": [{"returnOnEquityTTM": 1.5}],
       "earnings": [{"date": "2099-01-30"}, {"date": "2000-01-01"}],
       "dividends": [{"date": "2099-02-10", "dividend": 0.26}]}


def test_fmp_parsing(monkeypatch):
    monkeypatch.setattr(fundamentals, "_get", lambda url, **p: FMP[url.rsplit("/", 1)[-1]])
    d = fundamentals._fmp("k", "AAPL")
    assert d["pe"] == 25.5 and d["net_margin"] == 24.0 and d["roe"] == 150.0 and d["debt_to_equity"] == 1.5
    assert d["next_earnings"] == "2099-01-30" and d["next_dividend"] == {"date": "2099-02-10", "amount": 0.26}


def test_finnhub_and_alphavantage_parsing(monkeypatch):
    monkeypatch.setattr(fundamentals, "_get", lambda url, **p: {"metric": {"peTTM": 30, "netProfitMarginTTM": 20, "roeTTM": 40}}
                        if "metric" in url else {"earningsCalendar": [{"date": "2099-03-01"}]})
    d = fundamentals._finnhub("k", "AAPL")
    assert d["pe"] == 30 and d["next_earnings"] == "2099-03-01"
    monkeypatch.setattr(fundamentals, "_get", lambda url, **p: {"Symbol": "IBM", "PERatio": "None", "ProfitMargin": "0.1"})
    d = fundamentals._alphavantage("k", "IBM")
    assert d["pe"] is None and d["net_margin"] == 10.0


def test_get_cache_and_exact_symbol(monkeypatch):
    calls = []
    store.set_secret("data_keys", json.dumps([{"id": "1", "provider": "fmp", "key": "k"}]))

    def fake(entry, sym):
        calls.append(sym)
        return {"pe": 10.0} if sym == "MC.PA" else None
    monkeypatch.setattr(fundamentals, "_fetch", fake)
    assert fundamentals.get("MC.PA")["pe"] == 10.0
    assert fundamentals.get("MC.PA")["pe"] == 10.0 and calls == ["MC.PA"]  # cache
    assert fundamentals.get("SAP.DE", fetch=False) is None and calls == ["MC.PA"]  # pas d'appel en mode cache
    assert fundamentals.get("SAP.DE") is None and "SAP" not in calls  # jamais le symbole sans suffixe


def test_add_data_key_validation(monkeypatch):
    monkeypatch.setattr(fundamentals, "_fetch", lambda e, s: None)
    with pytest.raises(ValueError):
        fundamentals.add_key("fmp", "bad")
    with pytest.raises(ValueError):
        fundamentals.add_key("nope", "k")
