"""Génère backend/catalog/*.json : toutes les actions Euronext (PEA), indices européens, grandes valeurs mondiales.
Usage : python tools/build_catalog.py   (les sources publiques sont téléchargées, chaque symbole est vérifié sur Yahoo)."""
import csv
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (StockPulse catalog builder)"}
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "catalog")

EURONEXT_MARKETS = {"Euronext Paris": "PA", "Euronext Growth Paris": "PA", "Euronext Amsterdam": "AS", "Euronext Brussels": "BR",
                    "Euronext Lisbon": "LS", "Euronext Dublin": "IR", "Euronext Milan": "MI", "Euronext Growth Milan": "MI",
                    "Oslo Børs": "OL", "Euronext Growth Oslo": "OL", "Euronext Brussels, Paris": "PA", "Euronext Amsterdam, Paris": "AS"}
# Composants des grands indices (DAX, MDAX, IBEX 35, OMX, ATX, WIG20, SMI, FTSE 100, grandes valeurs Asie) : index_constituents.json
# ETF éligibles PEA les plus courants (Amundi, BNP Paribas, iShares PEA)
ETF_PEA = ["CW8.PA", "EWLD.PA", "PE500.PA", "PSP5.PA", "PUST.PA", "PANX.PA", "C40.PA", "CAC.PA", "ESE.PA", "ETZ.PA",
           "PAEEM.PA", "PCEU.PA", "MEUD.PA", "OBLI.PA", "RS2K.PA", "PTPXE.PA", "DCAM.PA", "WPEA.PA", "LQQ.PA", "CL2.PA"]


def euronext():
    res = requests.post("https://live.euronext.com/en/pd_es/data/stocks/download?mics=dm_all_stock",
                        data={"args[fe_type]": "csv", "args[fe_decimal]": ".", "args[fe_date_format]": "d/m/Y"}, headers=UA, timeout=60)
    rows = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))[4:]
    out = []
    for r in rows:
        if len(r) > 12 and r[3] in EURONEXT_MARKETS and r[2]:
            turnover = float(r[12]) if r[12].replace(".", "", 1).isdigit() else 0
            out.append({"symbol": f"{r[2].replace(' ', '-')}.{EURONEXT_MARKETS[r[3]]}", "name": r[0], "turnover": turnover})
    return out


def us_majors(min_cap=10e9):
    rows = requests.get("https://api.nasdaq.com/api/screener/stocks", params={"tableonly": "true", "limit": 10000, "download": "true"},
                        headers=UA, timeout=60).json()["data"]["rows"]
    out = []
    for r in rows:
        cap = float(r["marketCap"] or 0)
        if cap >= min_cap and "^" not in r["symbol"] and "/" not in r["symbol"]:
            out.append({"symbol": r["symbol"].replace(".", "-"), "name": r["name"], "sector": r["sector"] or None, "cap": cap})
    return out


def validate(symbols):
    """Garde les symboles connus de Yahoo, avec leur nom officiel."""
    def batch(b):
        r = requests.get("https://query1.finance.yahoo.com/v7/finance/spark", params={"symbols": ",".join(b), "range": "5d", "interval": "1d"},
                         headers=UA, timeout=30)
        ok = {}
        for it in (r.json().get("spark", {}).get("result") or []) if r.ok else []:
            m = ((it.get("response") or [{}])[0] or {}).get("meta", {})
            if m.get("regularMarketPrice"):
                ok[it["symbol"]] = m.get("longName") or m.get("shortName")
        return ok
    found = {}
    with ThreadPoolExecutor(6) as pool:
        for d in pool.map(batch, [symbols[i:i + 20] for i in range(0, len(symbols), 20)]):
            found.update(d)
    return found


def sectors(symbols):
    def one(s):
        try:
            q = requests.get("https://query1.finance.yahoo.com/v1/finance/search", params={"q": s, "quotesCount": 1, "newsCount": 0},
                             headers=UA, timeout=10).json()["quotes"]
            return s, next((x.get("sector") for x in q if x.get("symbol") == s), None)
        except Exception:
            return s, None
    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(one, symbols))


def main():
    old = {e["symbol"]: e for f in os.listdir(OUT) if f.endswith(".json") for e in json.load(open(os.path.join(OUT, f), encoding="utf-8"))}
    cands: dict[str, dict] = {}
    eu = euronext()
    top = {e["symbol"] for e in sorted(eu, key=lambda e: -e["turnover"])[:250]}
    for e in eu:
        cands[e["symbol"]] = {"symbol": e["symbol"], "name": e["name"], "file": "europe", "core": e["symbol"] in top}
    indices = json.load(open(os.path.join(os.path.dirname(__file__), "index_constituents.json")))
    for file, syms in indices.items():
        for sym in syms:
            cands.setdefault(sym, {"symbol": sym, "name": sym, "file": file})["core"] = True
    for s in ETF_PEA:
        cands[s] = {"symbol": s, "name": s, "file": "etf", "core": False}
    us = sorted(us_majors(), key=lambda e: -e["cap"])
    for i, e in enumerate(us):
        cands.setdefault(e["symbol"], {"symbol": e["symbol"], "name": e["name"], "sector": e["sector"], "file": "us", "core": i < 200})
    for s, e in old.items():  # l'ancien catalogue reste suivi en priorité
        sfx = s.rsplit(".", 1)[-1] if "." in s else ""
        cands.setdefault(s, {**e, "file": "europe" if sfx in ("PA", "DE", "AS", "BR", "MC", "MI", "LS", "IR", "HE", "ST", "CO", "OL", "VI", "WA") else "world" if sfx else "us"})["core"] = True
    names = validate(list(cands))
    print(f"{len(names)}/{len(cands)} symboles valides")
    keep = {s: c for s, c in cands.items() if s in names}
    missing = [s for s, c in keep.items() if not c.get("sector")]
    for s, sec in sectors(missing).items():
        keep[s]["sector"] = sec
    files: dict[str, list] = {}
    for s, c in sorted(keep.items()):
        entry = {"symbol": s, "name": names[s] or c["name"]}
        if c.get("sector"):
            entry["sector"] = c["sector"]
        if c.get("core"):
            entry["core"] = True
        files.setdefault(c["file"], []).append(entry)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for name, entries in files.items():
        with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as fh:
            fh.write("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n]\n")
        print(name, len(entries))


if __name__ == "__main__":
    main()
