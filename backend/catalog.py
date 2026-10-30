"""Catalogue des entreprises suivies.
Base : backend/catalog/*.json (générés par tools/build_catalog.py). L'application y ajoute chaque jour les nouvelles
valeurs et le statut des valeurs disparues (fichier catalog_updates.json du dossier de données)."""
import glob
import json
import os
import sys
import threading
import time

import store

_DIR = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "catalog")
UPDATES_PATH = os.path.join(store.DATA_DIR, "catalog_updates.json")
UPDATE_EVERY = 86400

# Suffixe Yahoo -> (pays, éligible PEA si l'ISIN est inconnu)
SUFFIXES = {
    "PA": ("FR", True), "DE": ("DE", True), "F": ("DE", True), "AS": ("NL", True), "BR": ("BE", True), "MC": ("ES", True),
    "MI": ("IT", True), "LS": ("PT", True), "IR": ("IE", True), "HE": ("FI", True), "ST": ("SE", True), "CO": ("DK", True),
    "OL": ("NO", True), "VI": ("AT", True), "WA": ("PL", True), "L": ("GB", False), "SW": ("CH", False), "HK": ("HK", False),
    "T": ("JP", False), "KS": ("KR", False), "TW": ("TW", False), "TO": ("CA", False), "AX": ("AU", False),
}
# PEA : sociétés dont le siège est dans l'Union européenne ou l'Espace économique européen (préfixe ISIN)
EEA = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO".split())

_lock = threading.Lock()
_entries: list[dict] | None = None


def _make(e: dict, market: str) -> dict:
    sym = e["symbol"].upper()
    country, pea = SUFFIXES.get(sym.rsplit(".", 1)[-1], ("US", False)) if "." in sym else ("US", False)
    isin = e.get("isin")
    if isin:
        country, pea = isin[:2], isin[:2] in EEA
    return {"symbol": sym, "name": e["name"], "market": market, "country": e.get("country", country),
            "pea": e.get("pea", pea), "sector": e.get("sector"), "isin": isin, "core": bool(e.get("core")), "status": None}


def _updates() -> dict:
    try:
        return json.load(open(UPDATES_PATH, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def entries() -> list[dict]:
    global _entries
    with _lock:
        if _entries is None:
            seen, out = set(), []
            for path in sorted(glob.glob(os.path.join(_DIR, "*.json"))):
                market = os.path.splitext(os.path.basename(path))[0]
                for e in json.load(open(path, encoding="utf-8")):
                    if e["symbol"].upper() not in seen:
                        seen.add(e["symbol"].upper())
                        out.append(_make(e, market))
            upd = _updates()
            for e in upd.get("added", []):
                if e["symbol"].upper() not in seen:
                    seen.add(e["symbol"].upper())
                    out.append({**_make(e, e.get("file", "europe")), "new": True})
            status = upd.get("status", {})
            for e in out:
                e["status"] = (status.get(e["symbol"]) or {}).get("status")
            _entries = _dedupe_listings(out)
        return _entries


# Une même société (même ISIN) cotée sur plusieurs places : on garde la cotation en euros la plus liquide
LISTING_PREFERENCE = ["PA", "AS", "BR", "DE", "MI", "MC", "LS", "IR", "HE", "VI", "F", "OL", "ST", "CO", "WA"]


def _rank(sym: str) -> int:
    sfx = sym.rsplit(".", 1)[-1] if "." in sym else ""
    return LISTING_PREFERENCE.index(sfx) if sfx in LISTING_PREFERENCE else len(LISTING_PREFERENCE)


def _dedupe_listings(entries: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for e in entries:
        if e["isin"] and e["market"] != "etf":
            cur = best.get(e["isin"])
            if cur is None or _rank(e["symbol"]) < _rank(cur["symbol"]):
                best[e["isin"]] = e
    out = []
    for e in entries:
        keep = best.get(e["isin"]) if e["isin"] and e["market"] != "etf" else e
        if keep is e:
            e["core"] = e["core"] or any(x["core"] for x in entries if x["isin"] == e["isin"] and e["isin"])
            e["alternatives"] = [x["symbol"] for x in entries if e["isin"] and x["isin"] == e["isin"] and x is not e]
            out.append(e)
    return out


def lookup(symbol: str) -> dict:
    """Fiche du catalogue d'une valeur, y compris pour une cotation secondaire (même société, autre place)."""
    sym = symbol.upper()
    for e in entries():
        if e["symbol"] == sym or sym in e.get("alternatives", []):
            return e
    return {}


def symbols() -> list[str]:
    return [e["symbol"] for e in entries()]


def core_symbols() -> list[str]:
    """Valeurs principales actives (indices, plus fortes capitalisations / échanges) : analysées automatiquement."""
    return [e["symbol"] for e in entries() if e["core"] and not e["status"]]


def last_update() -> int:
    return _updates().get("updated_at", 0)


def refresh_from_sources():
    """Mise à jour quotidienne : nouvelles valeurs et valeurs suspendues / radiées."""
    global _entries
    from services import catalog_updater
    known = {e["symbol"]: e for e in entries() if not e.get("new")}
    result = catalog_updater.update(known)
    previous = _updates().get("added", [])
    added = {e["symbol"]: e for e in previous + result["added"]}
    data = {**result, "added": list(added.values())}
    tmp = UPDATES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, UPDATES_PATH)
    with _lock:
        _entries = None
    return {"added": len(result["added"]), "flagged": len(result["status"])}


def needs_update() -> bool:
    return time.time() - last_update() > UPDATE_EVERY
