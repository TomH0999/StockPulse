"""Chiffres de l'entreprise (chiffre d'affaires, bénéfices, marges, croissance, valorisation, dette) et calendrier
(résultats, dividendes) via des clés gratuites. Fournisseurs essayés dans l'ordre des clés enregistrées ;
résultat mis en cache 7 jours par valeur. Champs absents chez un fournisseur : None (jamais inventés)."""
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
VERSION = 3  # cache des versions précédentes (moins de champs) rechargé
FIELDS = ("pe", "forward_pe", "pb", "net_margin", "gross_margin", "operating_margin", "roe", "debt_to_equity",
          "revenue", "net_income", "revenue_growth", "earnings_growth", "eps", "market_cap", "dividend_yield", "beta",
          "target_price", "currency", "next_earnings", "next_dividend", "annual", "surprises", "recommendations", "insiders")


def _full(d: dict) -> dict:
    return {k: d.get(k) for k in FIELDS}


def _annual(rows, year, revenue, net, gross, op, eps) -> list[dict]:
    """Comptes annuels (les 4 derniers exercices, du plus ancien au plus récent)."""
    out = []
    for r in (rows or [])[:4]:
        out.append({"year": str(r.get(year) or "")[:4], "revenue": _num(r.get(revenue)), "net_income": _num(r.get(net)),
                    "gross_profit": _num(r.get(gross)), "operating_income": _num(r.get(op)), "eps": _num(r.get(eps)) if eps else None})
    return [a for a in out if a["year"]][::-1]


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
    all_earnings = _get(f"{base}/earnings", symbol=sym, apikey=key) or []
    earnings = [e for e in all_earnings if e.get("date", "") >= today]
    past = [e for e in all_earnings if e.get("date", "") < today and _num(e.get("epsActual")) is not None][:4]
    divs = [d for d in _get(f"{base}/dividends", symbol=sym, apikey=key) or [] if d.get("date", "") >= today]
    profile = (_get(f"{base}/profile", symbol=sym, apikey=key) or [{}])[0]
    income = _get(f"{base}/income-statement", symbol=sym, limit=5, apikey=key) or []
    annual = _annual(income, "date", "revenue", "netIncome", "grossProfit", "operatingIncome", "eps")
    last, prev = (annual[-1] if annual else {}), (annual[-2] if len(annual) > 1 else {})
    growth = lambda k: round((last[k] / prev[k] - 1) * 100, 1) if last.get(k) and prev.get(k) and prev[k] > 0 else None
    return _full({
        "pe": _first(ratios, "priceToEarningsRatioTTM", "peRatioTTM"),
        "pb": _first(ratios, "priceToBookRatioTTM"),
        "net_margin": _pct(_first(ratios, "netProfitMarginTTM")),
        "gross_margin": _pct(_first(ratios, "grossProfitMarginTTM")),
        "operating_margin": _pct(_first(ratios, "operatingProfitMarginTTM")),
        "debt_to_equity": _first(ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM"),
        "roe": _pct(_first(metrics, "returnOnEquityTTM", "roeTTM")),
        "dividend_yield": _pct(_first(ratios, "dividendYieldTTM")),
        "eps": last.get("eps"), "revenue": last.get("revenue"), "net_income": last.get("net_income"),
        "revenue_growth": growth("revenue"), "earnings_growth": growth("net_income"),
        "market_cap": _first(profile, "marketCap", "mktCap"), "beta": _first(profile, "beta"),
        "currency": (income[0].get("reportedCurrency") if income else None) or profile.get("currency"), "annual": annual,
        "next_earnings": min((e["date"] for e in earnings), default=None),
        "next_dividend": min(({"date": d["date"], "amount": d.get("dividend")} for d in divs), key=lambda d: d["date"], default=None),
        "surprises": [_surprise(e.get("date"), _num(e.get("epsActual")), _num(e.get("epsEstimated"))) for e in past],
    })


def _surprise(period, actual, estimate):
    """Surprise de résultats : BPA publié contre BPA attendu par les analystes."""
    pct = round((actual - estimate) / abs(estimate) * 100, 1) if actual is not None and estimate not in (None, 0) else None
    return {"period": period, "actual": actual, "estimate": estimate, "surprise_pct": pct}


def _finnhub_extras(key, sym) -> dict:
    """Surprises de résultats, évolution des recommandations d'analystes (révisions) et achats / ventes des dirigeants."""
    out = {}
    try:
        out["surprises"] = [_surprise(e.get("period"), _num(e.get("actual")), _num(e.get("estimate")))
                            for e in (_get("https://finnhub.io/api/v1/stock/earnings", symbol=sym, token=key) or [])[:4]]
    except Exception:
        pass
    try:
        rec = _get("https://finnhub.io/api/v1/stock/recommendation", symbol=sym, token=key) or []
        pick = lambda r: {k: r.get(k) for k in ("period", "strongBuy", "buy", "hold", "sell", "strongSell")}  # noqa: E731
        if rec:
            out["recommendations"] = {"now": pick(rec[0]), "before": pick(rec[min(3, len(rec) - 1)])}
    except Exception:
        pass
    try:
        since = (date.today() - timedelta(days=90)).isoformat()
        tx = (_get("https://finnhub.io/api/v1/stock/insider-transactions", symbol=sym, token=key, **{"from": since}) or {}).get("data") or []
        buys = sum(t.get("change") or 0 for t in tx if (t.get("change") or 0) > 0)
        sells = -sum(t.get("change") or 0 for t in tx if (t.get("change") or 0) < 0)
        out["insiders"] = {"bought": buys, "sold": sells, "transactions": len(tx), "days": 90}
    except Exception:
        pass
    return out


def _finnhub(key, sym):
    m = (_get("https://finnhub.io/api/v1/stock/metric", symbol=sym, metric="all", token=key) or {}).get("metric") or {}
    if not m:
        return None
    cal = _get("https://finnhub.io/api/v1/calendar/earnings", symbol=sym, token=key,
               **{"from": date.today().isoformat(), "to": (date.today() + timedelta(days=120)).isoformat()}) or {}
    cap = _first(m, "marketCapitalization")
    return _full({
        "pe": _first(m, "peTTM", "peBasicExclExtraTTM"), "pb": _first(m, "pbQuarterly", "pbAnnual"),
        "net_margin": _first(m, "netProfitMarginTTM"), "gross_margin": _first(m, "grossMarginTTM"),
        "operating_margin": _first(m, "operatingMarginTTM"),
        "debt_to_equity": _first(m, "totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"),
        "roe": _first(m, "roeTTM"), "eps": _first(m, "epsTTM", "epsBasicExclExtraItemsTTM"),
        "revenue_growth": _first(m, "revenueGrowthTTMYoy"), "earnings_growth": _first(m, "epsGrowthTTMYoy"),
        "market_cap": cap * 1e6 if cap else None,  # Finnhub : en millions
        "dividend_yield": _first(m, "currentDividendYieldTTM", "dividendYieldIndicatedAnnual"), "beta": _first(m, "beta"),
        "next_earnings": min((e["date"] for e in cal.get("earningsCalendar") or []), default=None),
        **_finnhub_extras(key, sym),
    })


def _alphavantage(key, sym):
    o = _get("https://www.alphavantage.co/query", function="OVERVIEW", symbol=sym, apikey=key) or {}
    if not o.get("Symbol"):
        return None
    revenue, margin = _first(o, "RevenueTTM"), _first(o, "ProfitMargin")
    gross = _first(o, "GrossProfitTTM")
    try:
        inc = _get("https://www.alphavantage.co/query", function="INCOME_STATEMENT", symbol=sym, apikey=key) or {}
    except Exception:
        inc = {}
    return _full({
        "pe": _first(o, "PERatio", "TrailingPE"), "forward_pe": _first(o, "ForwardPE"), "pb": _first(o, "PriceToBookRatio"),
        "net_margin": _pct(margin), "operating_margin": _pct(_first(o, "OperatingMarginTTM")),
        "gross_margin": round(gross / revenue * 100, 2) if gross and revenue else None,
        "roe": _pct(_first(o, "ReturnOnEquityTTM")), "eps": _first(o, "EPS"),
        "revenue": revenue, "net_income": revenue * margin if revenue and margin is not None else None,
        "revenue_growth": _pct(_first(o, "QuarterlyRevenueGrowthYOY")), "earnings_growth": _pct(_first(o, "QuarterlyEarningsGrowthYOY")),
        "market_cap": _first(o, "MarketCapitalization"), "dividend_yield": _pct(_first(o, "DividendYield")),
        "beta": _first(o, "Beta"), "target_price": _first(o, "AnalystTargetPrice"), "currency": o.get("Currency"),
        "annual": _annual(inc.get("annualReports"), "fiscalDateEnding", "totalRevenue", "netIncome", "grossProfit", "operatingIncome", None),
    })


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
        if (time.time() - cached["fetched_at"] < CACHE_SECONDS and cached.get("v") == VERSION) or not fetch:
            return cached
    if not fetch:
        return None
    for entry in keys():  # symbole exact uniquement : « MC » sans suffixe serait une autre société
        data = _fetch(entry, sym)
        if data and any(v not in (None, []) for v in data.values()):
            data.update(source=entry["provider"], fetched_at=int(time.time()), v=VERSION)
            store.set_setting(cache_key, json.dumps(data))
            return data
    return None
