"""Chiffres financiers d'une entreprise pour l'investisseur long terme, sans clé : comptes annuels publiés
(Yahoo Finance, 4 derniers exercices) et historique complet des dividendes.

Indicateurs calculés : free cash-flow et rendement FCF, ROIC, marges et leur régularité, croissance du chiffre
d'affaires / BPA / dividende, dette nette / EBITDA, couverture des intérêts, dilution et rachats, taux de distribution,
années sans baisse du dividende, valorisation actuelle comparée à celle de la société les années précédentes.
Limite : les comptes gratuits couvrent 4 exercices (pas 10). Un indicateur incalculable vaut None, jamais une estimation."""
import json
import statistics
import time
from datetime import datetime, timezone

import store
from services.yahoo import _session

URL = "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{sym}"
CACHE_SECONDS = 7 * 86400
VERSION = 2
TYPES = ["TotalRevenue", "GrossProfit", "OperatingIncome", "EBIT", "EBITDA", "NetIncome", "DilutedEPS", "DilutedAverageShares",
         "OrdinarySharesNumber", "FreeCashFlow", "OperatingCashFlow", "CapitalExpenditure", "TotalDebt", "CashAndCashEquivalents",
         "NetDebt", "StockholdersEquity", "InvestedCapital", "InterestExpense", "CashDividendsPaid", "RepurchaseOfCapitalStock",
         "TaxRateForCalcs"]
# Secteurs où la dette fait partie du métier (banques, assurances, foncières) : ROE au lieu du ROIC, pas de ratio de dette
FINANCIAL_SECTORS = ("financial", "bank", "insurance", "real estate", "reit", "finance")
REPORT_LAG = 90 * 86400  # comptes publiés environ 3 mois après la clôture : pas d'information « du futur » dans le backtest


def is_financial(sector: str | None) -> bool:
    return bool(sector) and any(w in sector.lower() for w in FINANCIAL_SECTORS)


def _fetch_annual(sym: str) -> list[dict]:
    now = int(time.time())
    res = _session.get(URL.format(sym=sym), timeout=15,
                       params={"type": ",".join("annual" + t for t in TYPES), "period1": now - 12 * 365 * 86400, "period2": now})
    res.raise_for_status()
    years: dict[str, dict] = {}
    for item in res.json().get("timeseries", {}).get("result") or []:
        t = item["meta"]["type"][0]
        for v in item.get(t) or []:
            if v and v.get("reportedValue"):
                y = years.setdefault(v["asOfDate"], {"date": v["asOfDate"]})
                y[t[len("annual"):]] = v["reportedValue"]["raw"]
                if v.get("currencyCode") and t != "annualDilutedEPS":
                    y["currency"] = v["currencyCode"]
    return [years[d] for d in sorted(years)]


def _fetch_dividends(sym: str) -> list[tuple[int, float]]:
    res = _session.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", timeout=15,
                       params={"range": "max", "interval": "1mo", "events": "div"})
    res.raise_for_status()
    divs = (((res.json()["chart"]["result"] or [{}])[0].get("events") or {}).get("dividends") or {})
    return sorted((int(v["date"]), float(v["amount"])) for v in divs.values())


def raw(sym: str, fetch: bool = True) -> dict | None:
    """Comptes annuels + dividendes, en cache 7 jours."""
    sym = sym.upper()
    key = f"fin:{sym}"
    cached = store.get_setting(key)
    if cached:
        data = json.loads(cached)
        if (time.time() - data["fetched_at"] < CACHE_SECONDS and data.get("v") == VERSION) or not fetch:
            return data
    if not fetch:
        return None
    try:
        annual = _fetch_annual(sym)
    except Exception as e:
        print(f"Comptes {sym} : {e}")
        annual = []
    try:
        divs = _fetch_dividends(sym)
    except Exception as e:
        print(f"Dividendes {sym} : {e}")
        divs = []
    data = {"annual": annual, "dividends": divs, "fetched_at": int(time.time()), "v": VERSION}
    store.set_setting(key, json.dumps(data))
    return data


def _g(y: dict, k: str):
    v = y.get(k)
    return float(v) if isinstance(v, (int, float)) else None


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _cagr(first, last, years):
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


def _ts(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _price_at(hist: list[dict], ts: int) -> float | None:
    best = None
    for p in hist:
        if p["ts"] <= ts:
            best = p["close"]
        else:
            break
    return best


def dividend_record(divs: list[tuple[int, float]], as_of: float) -> dict:
    """Dividende par action par année civile complète, croissance sur 5 / 10 ans et années consécutives sans baisse."""
    year_now = datetime.fromtimestamp(as_of, timezone.utc).year
    by_year: dict[int, float] = {}
    for ts, amount in divs:
        if ts <= as_of:
            y = datetime.fromtimestamp(ts, timezone.utc).year
            by_year[y] = by_year.get(y, 0.0) + amount
    full = {y: v for y, v in by_year.items() if y < year_now}
    if not full:
        return {"years_paid": 0}
    last = max(full)
    streak = 0
    y = last
    while y - 1 in full and full[y] >= full[y - 1] * 0.98:  # tolérance de 2 % (arrondis, change)
        streak += 1
        y -= 1
    return {"years_paid": len(full), "last_year": last, "dps_last": round(full[last], 4),
            "growth_5y": _cagr(full.get(last - 5), full[last], 5), "growth_10y": _cagr(full.get(last - 10), full[last], 10),
            "years_without_cut": streak, "paid_last_year": last == year_now - 1}


def metrics(data: dict | None, price: float | None, sector: str | None = None, hist: list[dict] | None = None,
            as_of: float | None = None, currency: str | None = None) -> dict | None:
    """Indicateurs long terme à une date donnée (as_of) : seuls les comptes publiés à cette date sont utilisés.
    currency : devise de cotation ; les cours sont convertis dans la devise des comptes avant tout ratio."""
    if not data:
        return None
    report_ccy = next((y.get("currency") for y in reversed(data.get("annual") or []) if y.get("currency")), None)
    conv = 1.0
    if currency and report_ccy and currency != report_ccy:
        from services import fx  # import tardif
        rq, rr = fx.rate(currency), fx.rate(report_ccy)
        conv = rq / rr if rq and rr else None
        if conv is None:
            return None  # change inconnu : mieux vaut aucun ratio qu'un ratio faux
    price = price * conv if price else price
    if hist and conv != 1.0:
        hist = [{**p, "close": p["close"] * conv} for p in hist]
    as_of = as_of or time.time()
    years = [y for y in data.get("annual") or [] if _ts(y["date"]) + REPORT_LAG <= as_of
             and (y.get("TotalRevenue") is not None or y.get("NetIncome") is not None)]  # exercices incomplets ignorés
    divs = dividend_record([tuple(d) for d in data.get("dividends") or []], as_of)
    if not years:
        return {"years": 0, "dividends": divs, "financial_sector": is_financial(sector)} if divs.get("years_paid") else None
    fin = is_financial(sector)
    last, first = years[-1], years[0]
    n = len(years) - 1
    shares = _g(last, "OrdinarySharesNumber") or _g(last, "DilutedAverageShares")
    cap = price * shares if price and shares else None
    rev, ni, fcf = _g(last, "TotalRevenue"), _g(last, "NetIncome"), _g(last, "FreeCashFlow")
    ebit, ebitda = _g(last, "EBIT") or _g(last, "OperatingIncome"), _g(last, "EBITDA")
    net_debt = _g(last, "NetDebt")
    if net_debt is None and _g(last, "TotalDebt") is not None:
        net_debt = _g(last, "TotalDebt") - (_g(last, "CashAndCashEquivalents") or 0)

    def roic(y):
        e, ic, tax = _g(y, "EBIT") or _g(y, "OperatingIncome"), _g(y, "InvestedCapital"), _g(y, "TaxRateForCalcs")
        return e * (1 - (tax if tax is not None and 0 <= tax < 0.6 else 0.25)) / ic * 100 if e is not None and ic and ic > 0 else None

    def roe(y):
        return _div(_g(y, "NetIncome"), _g(y, "StockholdersEquity"))

    roics = [r for r in (roic(y) for y in years) if r is not None]
    roes = [r * 100 for r in (roe(y) for y in years) if r is not None]
    op_margins = [m * 100 for m in (_div(_g(y, "OperatingIncome"), _g(y, "TotalRevenue")) for y in years) if m is not None]
    eps_first, eps_last = _g(first, "DilutedEPS"), _g(last, "DilutedEPS")
    sh_first = _g(first, "OrdinarySharesNumber") or _g(first, "DilutedAverageShares")
    dividends_paid = abs(_g(last, "CashDividendsPaid") or 0) or None
    buybacks = abs(_g(last, "RepurchaseOfCapitalStock") or 0) or None
    interest = abs(_g(last, "InterestExpense") or 0) or None

    # Valorisation comparée à l'historique de la société : PER à chaque clôture d'exercice passée
    hist_pe = []
    if hist:
        for y in years[:-1] if len(years) > 1 else []:
            p, e = _price_at(hist, _ts(y["date"])), _g(y, "DilutedEPS")
            if p and e and e > 0:
                hist_pe.append(p / e)
    pe = price / eps_last if price and eps_last and eps_last > 0 else None
    ev = cap + (net_debt or 0) if cap else None
    out = {
        "years": len(years), "first_year": first["date"][:4], "last_year": last["date"][:4], "financial_sector": fin,
        "currency": report_ccy or currency,
        "revenue": rev, "net_income": ni, "free_cash_flow": fcf, "ebitda": ebitda, "market_cap": cap, "net_debt": net_debt,
        "eps": eps_last, "shares": shares,
        "gross_margin": _pct(_div(_g(last, "GrossProfit"), rev)), "operating_margin": _pct(_div(_g(last, "OperatingIncome"), rev)),
        "net_margin": _pct(_div(ni, rev)), "fcf_margin": _pct(_div(fcf, rev)),
        "fcf_yield": _pct(_div(fcf, cap)), "pe": round(pe, 1) if pe else None, "pe_loss": bool(eps_last is not None and eps_last <= 0),
        "pe_history_median": round(statistics.median(hist_pe), 1) if hist_pe else None, "pe_history_n": len(hist_pe),
        "ev_ebit": round(ev / ebit, 1) if ev and ebit and ebit > 0 and not fin else None,
        "roic": round(roics[-1], 1) if roics and not fin else None, "roic_avg": round(statistics.mean(roics), 1) if roics and not fin else None,
        "roic_min": round(min(roics), 1) if roics and not fin else None,
        "roe": round(roes[-1], 1) if roes else None, "roe_avg": round(statistics.mean(roes), 1) if roes else None,
        "op_margin_std": round(statistics.pstdev(op_margins), 1) if len(op_margins) >= 3 else None,
        "revenue_cagr": _r(_cagr(_g(first, "TotalRevenue"), rev, n)), "eps_cagr": _r(_cagr(eps_first, eps_last, n)),
        "fcf_positive_years": sum(1 for y in years if (_g(y, "FreeCashFlow") or 0) > 0),
        "net_debt_ebitda": round(net_debt / ebitda, 2) if net_debt is not None and ebitda and ebitda > 0 and not fin else None,
        "interest_coverage": round(ebit / interest, 1) if ebit and interest and not fin else None,
        "dilution_pa": _r(_cagr(sh_first, shares, n)) if sh_first and shares else None,
        "buyback_yield": _pct(_div(buybacks, cap)),
        "payout_ratio": _pct(_div(dividends_paid, ni)) if ni and ni > 0 else None,
        "payout_fcf": _pct(_div(dividends_paid, fcf)) if fcf and fcf > 0 else None,
        "dividend_yield": _pct(_div(divs.get("dps_last"), price)) if divs.get("paid_last_year") else None,
        "dividends": divs,
        "annual": [{"year": y["date"][:4], "revenue": _g(y, "TotalRevenue"), "operating_income": _g(y, "OperatingIncome"),
                    "net_income": _g(y, "NetIncome"), "free_cash_flow": _g(y, "FreeCashFlow"), "eps": _g(y, "DilutedEPS"),
                    "roic": _r(roic(y)) if not fin else None} for y in years],
    }
    return out


def _pct(v):
    return round(v * 100, 2) if v is not None else None


def _r(v):
    return round(v, 1) if v is not None else None
