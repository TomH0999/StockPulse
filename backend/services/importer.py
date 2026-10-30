"""Import des opérations exportées par le courtier (CSV : Boursorama, Fortuneo, Trade Republic, Bourse Direct, BforBank…).
Les colonnes sont reconnues par leur nom ; chaque ligne est convertie en mouvement du journal puis validée."""
import csv
import io
import re
import unicodedata
from datetime import datetime

import catalog
from services import portfolio, yahoo

COLUMNS = {
    "day": ["date d'execution", "date operation", "date de l'operation", "date de valeur", "date", "datetime", "execution date"],
    "type": ["type d'operation", "type", "sens", "operation", "nature", "libelle operation", "transaction type", "side"],
    "isin": ["isin", "code isin"],
    "name": ["libelle", "valeur", "nom", "produit", "titre", "instrument", "name", "security", "symbole", "ticker"],
    "quantity": ["quantite", "qte", "nombre", "nombre de titres", "shares", "quantity"],
    "price": ["cours d'execution", "cours", "prix unitaire", "prix", "price", "price per share"],
    "fees": ["frais", "commission", "courtage", "fees", "fee"],
    "amount": ["montant net", "montant", "total", "amount", "net amount"],
}
TYPES = [("dividend", ["dividende", "coupon", "dividend", "distribution"]), ("withdrawal", ["retrait", "withdrawal", "remboursement"]),
         ("deposit", ["versement", "virement", "depot", "apport", "deposit", "alimentation"]),
         ("sell", ["vente", "sell", "cession"]), ("buy", ["achat", "buy", "souscription", "purchase"])]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()).strip(" \"'")


def _number(text: str) -> float | None:
    t = re.sub(r"[^\d,.\-]", "", (text or "").replace(" ", "").replace("\xa0", "").replace(" ", ""))
    if not t or t in "-.,":
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _date(text: str) -> str | None:
    t = (text or "").strip()[:19]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(t if "%H" in fmt else t[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _columns(header: list[str]) -> dict[str, int]:
    found, normalized = {}, [_norm(h) for h in header]
    for key, names in COLUMNS.items():
        for name in names:  # le nom le plus précis d'abord
            idx = next((i for i, h in enumerate(normalized) if h == name and i not in found.values()), None)
            if idx is None:
                idx = next((i for i, h in enumerate(normalized) if name in h and i not in found.values()), None)
            if idx is not None:
                found[key] = idx
                break
    return found


def _symbol(isin: str | None, name: str | None) -> str | None:
    if isin:
        e = next((x for x in catalog.entries() if x.get("isin") == isin.strip().upper()), None)
        if e:
            return e["symbol"]
    if name:
        n = _norm(name)
        e = next((x for x in catalog.entries() if _norm(x["symbol"]) == n or _norm(x["name"]) == n), None)
        if e:
            return e["symbol"]
        try:
            res = yahoo.search(isin or name)
            if res:
                return res[0]["symbol"]
        except Exception:
            pass
    return None


def parse(content: str) -> dict:
    text = content.lstrip("﻿")
    sample = text[:4000]
    delimiter = max([";", ",", "\t", "|"], key=sample.count)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    header_idx = next((i for i, r in enumerate(rows[:15]) if len(_columns(r)) >= 3), None)
    if header_idx is None:
        raise ValueError("En-tête introuvable : le fichier doit contenir au moins une date, un type d'opération et un montant ou une quantité")
    cols = _columns(rows[header_idx])
    out = []
    for n, r in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if not any(c.strip() for c in r):
            continue
        get = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else ""  # noqa: E731
        raw_type = _norm(get("type"))
        kind = next((t for t, words in TYPES if any(w in raw_type for w in words)), None)
        item = {"line": n, "type": kind, "day": _date(get("day")), "isin": get("isin").strip() or None, "label": get("name").strip() or None,
                "quantity": _number(get("quantity")), "price": _number(get("price")), "fees": abs(_number(get("fees")) or 0.0),
                "amount": _number(get("amount")), "raw_type": get("type")}
        if item["quantity"] is not None:
            item["quantity"] = abs(item["quantity"])
        if item["amount"] is not None:
            item["amount"] = abs(item["amount"])
        if kind in ("buy", "sell") and not item["price"] and item["quantity"] and item["amount"]:
            item["price"] = round((item["amount"] - (item["fees"] if kind == "buy" else -item["fees"])) / item["quantity"], 6)
        if kind in ("buy", "sell", "dividend"):
            item["symbol"] = _symbol(item["isin"], item["label"])
        error = None
        if not kind:
            error = f"type d'opération non reconnu « {item['raw_type']} »"
        elif not item["day"]:
            error = "date illisible"
        elif kind in ("buy", "sell") and not (item.get("symbol") and item["quantity"] and item["price"]):
            error = "valeur, quantité ou prix manquant"
        elif kind not in ("buy", "sell") and not item["amount"]:
            error = "montant manquant"
        item["error"] = error
        out.append(item)
    return {"columns": {k: rows[header_idx][v] for k, v in cols.items()}, "rows": out,
            "valid": sum(1 for i in out if not i["error"]), "errors": sum(1 for i in out if i["error"])}


def run(content: str, commit: bool = False) -> dict:
    """Analyse le fichier ; avec commit, ajoute les lignes valides au journal (ordre chronologique, chaque ligne revalidée)."""
    result = parse(content)
    if commit:
        added = 0
        for item in sorted((i for i in result["rows"] if not i["error"]), key=lambda i: i["day"]):
            try:
                if item["type"] in ("buy", "sell"):
                    portfolio.add_movement(item["type"], item["day"], item["symbol"], item["quantity"], item["price"], item["fees"])
                else:
                    portfolio.add_movement(item["type"], item["day"], item.get("symbol"), amount=item["amount"], fees=0)
                added += 1
            except ValueError as e:
                item["error"] = str(e)
        result["added"] = added
        result["errors"] = sum(1 for i in result["rows"] if i["error"])
    return result
