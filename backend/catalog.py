"""Catalogue des entreprises suivies : un fichier JSON par marché dans backend/catalog/.
Pour agrandir le catalogue, ajouter des entrées {"symbol", "name"} (symboles Yahoo Finance) ou un nouveau fichier."""
import glob
import json
import os
import sys

_DIR = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "catalog")

# Suffixe Yahoo -> (pays, éligible PEA)
SUFFIXES = {
    "PA": ("FR", True), "DE": ("DE", True), "F": ("DE", True), "AS": ("NL", True), "BR": ("BE", True), "MC": ("ES", True),
    "MI": ("IT", True), "LS": ("PT", True), "IR": ("IE", True), "HE": ("FI", True), "ST": ("SE", True), "CO": ("DK", True),
    "OL": ("NO", True), "VI": ("AT", True), "WA": ("PL", True), "TW": ("TW", False), "L": ("GB", False), "SW": ("CH", False), "HK": ("HK", False), "T": ("JP", False),
    "KS": ("KR", False), "TO": ("CA", False), "AX": ("AU", False),
}

_entries: list[dict] | None = None


def entries() -> list[dict]:
    global _entries
    if _entries is None:
        seen, out = set(), []
        for path in sorted(glob.glob(os.path.join(_DIR, "*.json"))):
            market = os.path.splitext(os.path.basename(path))[0]
            for e in json.load(open(path, encoding="utf-8")):
                sym = e["symbol"].upper()
                if sym in seen:
                    continue
                seen.add(sym)
                country, pea = SUFFIXES.get(sym.rsplit(".", 1)[-1], ("US", False)) if "." in sym else ("US", False)
                out.append({"symbol": sym, "name": e["name"], "market": market,
                            "country": e.get("country", country), "pea": e.get("pea", pea), "sector": e.get("sector"),
                            "core": bool(e.get("core"))})
        _entries = out
    return _entries


def symbols() -> list[str]:
    return [e["symbol"] for e in entries()]


def core_symbols() -> list[str]:
    """Valeurs principales (indices, plus fortes capitalisations / échanges) : analysées automatiquement."""
    return [e["symbol"] for e in entries() if e["core"]]
