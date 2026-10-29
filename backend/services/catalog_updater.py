"""Construction et mise à jour du catalogue depuis des sources publiques (aucun jeton IA consommé).
- Cote Euronext complète (avec ISIN), composants d'indices (catalog_sources/), grandes valeurs US (> 10 Md$)
- Validation de chaque symbole sur Yahoo ; secteur via la recherche Yahoo
- Valeurs disparues : « suspendue » (plus de cotation récente) ou « radiée » (absente des sources et sans cours)."""
import csv
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (StockPulse catalog)"}
SOURCES = os.path.join(getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "catalog_sources")
EURONEXT_MARKETS = {"Euronext Paris": "PA", "Euronext Growth Paris": "PA", "Euronext Amsterdam": "AS", "Euronext Brussels": "BR",
                    "Euronext Lisbon": "LS", "Euronext Dublin": "IR", "Euronext Milan": "MI", "Euronext Growth Milan": "MI",
                    "Oslo Børs": "OL", "Euronext Growth Oslo": "OL", "Euronext Brussels, Paris": "PA", "Euronext Amsterdam, Paris": "AS"}
EUROPE_SUFFIXES = ("PA", "DE", "AS", "BR", "MC", "MI", "LS", "IR", "HE", "ST", "CO", "OL", "VI", "WA")
SUSPENDED_DAYS = 30


def euronext() -> list[dict]:
    res = requests.post("https://live.euronext.com/en/pd_es/data/stocks/download?mics=dm_all_stock",
                        data={"args[fe_type]": "csv", "args[fe_decimal]": ".", "args[fe_date_format]": "d/m/Y"}, headers=UA, timeout=60)
    res.raise_for_status()
    out = []
    for r in list(csv.reader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))[4:]:
        if len(r) > 12 and r[3] in EURONEXT_MARKETS and r[2]:
            turnover = float(r[12]) if r[12].replace(".", "", 1).isdigit() else 0
            out.append({"symbol": f"{r[2].replace(' ', '-')}.{EURONEXT_MARKETS[r[3]]}", "name": r[0], "isin": r[1], "turnover": turnover})
    return out


def us_majors(min_cap=10e9) -> list[dict]:
    rows = requests.get("https://api.nasdaq.com/api/screener/stocks", params={"tableonly": "true", "limit": 10000, "download": "true"},
                        headers=UA, timeout=60).json()["data"]["rows"]
    return [{"symbol": r["symbol"].replace(".", "-"), "name": r["name"], "sector": r["sector"] or None, "cap": float(r["marketCap"] or 0)}
            for r in rows if float(r["marketCap"] or 0) >= min_cap and "^" not in r["symbol"] and "/" not in r["symbol"]]


def quotes_meta(symbols: list[str]) -> dict[str, dict]:
    """Symboles connus de Yahoo : nom officiel et date de dernière cotation."""
    def batch(b):
        try:
            r = requests.get("https://query1.finance.yahoo.com/v7/finance/spark", params={"symbols": ",".join(b), "range": "5d", "interval": "1d"},
                             headers=UA, timeout=30)
            items = r.json().get("spark", {}).get("result") or [] if r.ok else []
        except Exception:
            return {}
        out = {}
        for it in items:
            m = ((it.get("response") or [{}])[0] or {}).get("meta", {})
            if m.get("regularMarketPrice"):
                out[it["symbol"]] = {"name": m.get("longName") or m.get("shortName"), "time": m.get("regularMarketTime") or 0}
        return out
    found = {}
    with ThreadPoolExecutor(6) as pool:
        for d in pool.map(batch, [symbols[i:i + 20] for i in range(0, len(symbols), 20)]):
            found.update(d)
    return found


def sectors(symbols: list[str]) -> dict[str, str | None]:
    def one(s):
        try:
            q = requests.get("https://query1.finance.yahoo.com/v1/finance/search", params={"q": s, "quotesCount": 1, "newsCount": 0},
                             headers=UA, timeout=10).json()["quotes"]
            return s, next((x.get("sector") for x in q if x.get("symbol") == s), None)
        except Exception:
            return s, None
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(one, symbols))


def candidates() -> dict[str, dict]:
    """Toutes les valeurs proposées par les sources, avec le fichier de catalogue cible et le statut « principale »."""
    cands: dict[str, dict] = {}
    eu = euronext()
    top = {e["symbol"] for e in sorted(eu, key=lambda e: -e["turnover"])[:250]}
    for e in eu:
        cands[e["symbol"]] = {"symbol": e["symbol"], "name": e["name"], "isin": e["isin"], "file": "europe", "core": e["symbol"] in top}
    for file, syms in json.load(open(os.path.join(SOURCES, "index_constituents.json"), encoding="utf-8")).items():
        for s in syms:
            c = cands.setdefault(s, {"symbol": s, "name": s, "file": file})
            c["core"] = file != "etf" or c.get("core", False)
            if file == "etf":
                c.update(file="etf", pea=True)
    for i, e in enumerate(sorted(us_majors(), key=lambda e: -e["cap"])):
        cands.setdefault(e["symbol"], {"symbol": e["symbol"], "name": e["name"], "sector": e["sector"], "file": "us", "core": i < 200})
    return cands


def file_for(symbol: str) -> str:
    sfx = symbol.rsplit(".", 1)[-1] if "." in symbol else ""
    return "europe" if sfx in EUROPE_SUFFIXES else "world" if sfx else "us"


def update(known: dict[str, dict]) -> dict:
    """Compare les sources au catalogue connu : nouvelles valeurs (validées) et statut des valeurs existantes."""
    cands = candidates()
    new_syms = [s for s in cands if s not in known]
    metas = quotes_meta(sorted(set(new_syms) | set(known)))
    added = []
    secs = sectors([s for s in new_syms if s in metas and not cands[s].get("sector")])
    for s in new_syms:
        if s in metas:
            c = cands[s]
            entry = {k: v for k, v in {"symbol": s, "name": metas[s]["name"] or c["name"], "isin": c.get("isin"),
                                         "sector": c.get("sector") or secs.get(s), "core": c.get("core") or None,
                                         "pea": c.get("pea"), "file": c["file"]}.items() if v is not None}
            added.append(entry)
    now = time.time()
    status = {}
    for s in known:
        m = metas.get(s)
        if m and now - m["time"] < SUSPENDED_DAYS * 86400:
            continue
        in_sources = s in cands
        status[s] = {"status": "suspended" if (m or in_sources) else "delisted",
                     "last_quote": m["time"] if m else None, "checked_at": int(now)}
    return {"added": added, "status": status, "updated_at": int(now), "source_count": len(cands)}
