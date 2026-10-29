"""Fondamentaux (PER, marge, dette, rentabilité) et calendrier (résultats, dividendes) via des clés gratuites.
Fournisseurs essayés dans l'ordre des clés enregistrées ; résultat mis en cache 7 jours par valeur."""
import json
import time
import uuid
from datetime import date, timedelta

import requests

import store

PROVIDERS = {
    "fmp": "https://site.financialmodelingprep.com/developer/docs/dashboard",
    "finnhub": "https://finnhub.io/dashboard",
    "alphavantage": "https://www.alphavantage.co/support/#api-key",
}
CACHE_SECONDS = 7 * 86400


def keys() -> list[dict]:
    raw = store.get_secret("data_keys")
    return json.loads(raw) if raw else []


def public_keys() -> list[dict]:
    return [{"id": k["id"], "provider": k["provider"], "hint": f"…{k['key'][-4:]}"} for k in keys()]


def add_key(provider: str, key: str):
    if provider not in PROVIDERS:
        raise ValueError("Fournisseur inconnu")
    entry = {"id": uuid.uuid4().hex[:8], "provider": provider, "key": key.strip()}
    if not _fetch(entry, "AAPL"):
        raise ValueError("La clé ne renvoie aucune donnée (clé invalide ou quota atteint)")
    store.set_secret("data_keys", json.dumps([k for k in keys() if k["key"] != entry["key"]] + [entry]))


def remove_key(key_id: str):
    store.set_secret("data_keys", json.dumps([k for k in keys() if k["id"] != key_id]))


def _num(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _first(d: dict, *names):
    return next((_num(d[n]) for n in names if d.get(n) not in (None, "None", "-")), None)


def _get(url, **params):
    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    return res.json()


def _fmp(key, sym):
    base = "https://financialmodelingprep.com/stable"
    ratios = (_get(f"{base}/ratios-ttm", symbol=sym, apikey=key) or [{}])[0]
    metrics = (_get(f"{base}/key-metrics-ttm", symbol=sym, apikey=key) or [{}])[0]
    if not ratios and not metrics:
        return None
    today = date.today().isoformat()
    earnings = [e for e in _get(f"{base}/earnings", symbol=sym, apikey=key) or [] if e.get("date", "") >= today]
    divs = [d for d in _get(f"{base}/dividends", symbol=sym, apikey=key) or [] if d.get("date", "") >= today]
    return {
        "pe": _first(ratios, "priceToEarningsRatioTTM", "peRatioTTM"),
        "net_margin": _pct(_first(ratios, "netProfitMarginTTM")),
        "debt_to_equity": _first(ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM"),
        "roe": _pct(_first(metrics, "returnOnEquityTTM", "roeTTM")),
        "next_earnings": min((e["date"] for e in earnings), default=None),
        "next_dividend": min(({"date": d["date"], "amount": d.get("dividend")} for d in divs), key=lambda d: d["date"], default=None),
    }


def _finnhub(key, sym):
    m = (_get("https://finnhub.io/api/v1/stock/metric", symbol=sym, metric="all", token=key) or {}).get("metric") or {}
    if not m:
        return None
    cal = _get("https://finnhub.io/api/v1/calendar/earnings", symbol=sym, token=key,
               **{"from": date.today().isoformat(), "to": (date.today() + timedelta(days=120)).isoformat()}) or {}
    return {
        "pe": _first(m, "peTTM", "peBasicExclExtraTTM"),
        "net_margin": _first(m, "netProfitMarginTTM"),
        "debt_to_equity": _first(m, "totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"),
        "roe": _first(m, "roeTTM"),
        "next_earnings": min((e["date"] for e in cal.get("earningsCalendar") or []), default=None),
        "next_dividend": None,
    }


def _alphavantage(key, sym):
    o = _get("https://www.alphavantage.co/query", function="OVERVIEW", symbol=sym, apikey=key) or {}
    if not o.get("Symbol"):
        return None
    return {"pe": _first(o, "PERatio"), "net_margin": _pct(_first(o, "ProfitMargin")), "debt_to_equity": None,
            "roe": _pct(_first(o, "ReturnOnEquityTTM")), "next_earnings": None, "next_dividend": None}


def _pct(v):
    """Ratio (0,25) -> pourcentage (25,0)."""
    return round(v * 100, 2) if v is not None and abs(v) <= 5 else v


FETCHERS = {"fmp": _fmp, "finnhub": _finnhub, "alphavantage": _alphavantage}


def _fetch(entry, sym):
    try:
        return FETCHERS[entry["provider"]](entry["key"], sym)
    except Exception as e:
        print(f"Fondamentaux {entry['provider']} {sym} : {e}")
        return None


def get(sym: str, force: bool = False, fetch: bool = True) -> dict | None:
    """Fondamentaux d'une valeur (cache 7 jours). fetch=False : cache seulement (préserve les quotas gratuits)."""
    sym = sym.upper()
    cache_key = f"fund:{sym}"
    raw = store.get_setting(cache_key)
    if raw and not force:
        cached = json.loads(raw)
        if time.time() - cached["fetched_at"] < CACHE_SECONDS or not fetch:
            return cached
    if not fetch:
        return None
    for entry in keys():  # symbole exact uniquement : « MC » sans suffixe serait une autre société
        data = _fetch(entry, sym)
        if data and any(v is not None for v in data.values()):
            data.update(source=entry["provider"], fetched_at=int(time.time()))
            store.set_setting(cache_key, json.dumps(data))
            return data
    return None
