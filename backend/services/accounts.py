"""Comptes de l'investisseur : PEA, PEA-PME, PEA « jeune », compte-titres (CTO) et assurance-vie.

Chaque mouvement appartient à un compte. Le compte « courant » d'une requête est choisi par l'interface
(paramètre ?account=) et lu par les services via current() : le PEA reste le compte par défaut."""
import contextvars
import json
import re

import store

TYPES = {
    "PEA": {"label": "PEA", "ceiling": 150_000, "pea_rules": True},
    "PEA_PME": {"label": "PEA-PME", "ceiling": 225_000, "pea_rules": True},     # plafond commun avec le PEA
    "PEA_JEUNE": {"label": "PEA jeune", "ceiling": 20_000, "pea_rules": True},  # 18-25 ans rattachés au foyer fiscal
    "CTO": {"label": "Compte-titres", "ceiling": None, "pea_rules": False},
    "AV": {"label": "Assurance-vie", "ceiling": None, "pea_rules": False},
}
DEFAULT = [{"id": "pea", "type": "PEA", "name": "Mon PEA"}]
_current: contextvars.ContextVar[str] = contextvars.ContextVar("account", default="pea")


def all_accounts() -> list[dict]:
    raw = store.get_setting("accounts")
    return json.loads(raw) if raw else [dict(a) for a in DEFAULT]


def get(account_id: str | None = None) -> dict:
    aid = account_id or current()
    acc = next((a for a in all_accounts() if a["id"] == aid), None)
    if not acc:
        raise ValueError("Compte inconnu")
    return {**acc, **TYPES[acc["type"]]}


def current() -> str:
    return _current.get()


def use(account_id: str | None):
    """Sélectionne le compte de la requête en cours (inconnu : PEA)."""
    ids = {a["id"] for a in all_accounts()}
    return _current.set(account_id if account_id in ids else "pea")


def create(type: str, name: str) -> dict:
    if type not in TYPES:
        raise ValueError("Type de compte inconnu")
    accs = all_accounts()
    if type != "CTO" and type != "AV" and any(a["type"] == type for a in accs):
        raise ValueError(f"Un seul {TYPES[type]['label']} par personne")
    base = re.sub(r"[^a-z0-9]+", "-", (name or type).lower()).strip("-")[:20] or type.lower()
    aid, i = base, 2
    while any(a["id"] == aid for a in accs):
        aid, i = f"{base}-{i}", i + 1
    acc = {"id": aid, "type": type, "name": (name or TYPES[type]["label"]).strip()[:40]}
    store.set_setting("accounts", json.dumps(accs + [acc]))
    return acc


def rename(account_id: str, name: str) -> dict:
    accs = all_accounts()
    for a in accs:
        if a["id"] == account_id:
            a["name"] = name.strip()[:40] or a["name"]
    store.set_setting("accounts", json.dumps(accs))
    return get(account_id)


def delete(account_id: str):
    if account_id == "pea":
        raise ValueError("Le PEA principal ne peut pas être supprimé (utilisez « Réinitialiser »)")
    with store.connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM pea_movements WHERE account = ?", (account_id,)).fetchone()[0]:
            raise ValueError("Compte non vide : réinitialisez-le d'abord")
    store.set_setting("accounts", json.dumps([a for a in all_accounts() if a["id"] != account_id]))


def ceiling_left(account_id: str | None = None) -> float | None:
    """Versements encore possibles. PEA-PME : 225 000 € moins les versements du PEA et du PEA-PME."""
    acc = get(account_id)
    if acc["ceiling"] is None:
        return None
    ids = [acc["id"]]
    if acc["type"] == "PEA_PME":
        ids += [a["id"] for a in all_accounts() if a["type"] in ("PEA", "PEA_JEUNE")]
    with store.connect() as conn:
        q = f"SELECT COALESCE(SUM(CASE type WHEN 'deposit' THEN amount ELSE 0 END), 0) FROM pea_movements WHERE account IN ({','.join('?' * len(ids))})"
        deposits = conn.execute(q, ids).fetchone()[0]
    return round(acc["ceiling"] - deposits, 2)


def eligible(account_type: str, entry: dict | None) -> bool | None:
    """Titre autorisé dans ce type de compte ? None = inconnu (à vérifier)."""
    if not TYPES[account_type]["pea_rules"]:
        return True
    if not entry:
        return None
    return bool(entry.get("pea")) and not entry.get("leveraged") if entry.get("kind") == "etf" else bool(entry.get("pea"))


def envelope(entry: dict | None, symbol: str) -> dict:
    """Dans quelle enveloppe placer ce titre ? (règles fiscales générales, à adapter à sa situation)."""
    reasons, best = [], "CTO"
    have = {a["type"]: a["id"] for a in all_accounts()}
    kind = (entry or {}).get("kind", "stock")
    if entry and entry.get("leveraged"):
        reasons.append("leveraged")
    if entry and entry.get("pea"):
        room = ceiling_left(have["PEA"]) if "PEA" in have else None
        if room is None or room > 0:
            best = "PEA"
            reasons.append("pea_eligible")
        elif "PEA_PME" in have:
            best = "PEA_PME"
            reasons.append("pea_full_pme")
        else:
            reasons.append("pea_full")
        if not entry.get("isin"):
            reasons.append("pea_to_confirm")
    else:
        reasons.append("not_pea")
        if kind == "stock" and "." not in symbol:
            reasons.append("us_w8ben")
        elif kind == "stock":
            reasons.append("foreign_withholding")
    from services import taxes  # import tardif
    wh = taxes.withholding((entry or {}).get("country")) if best == "CTO" and kind == "stock" else None
    return {"recommended": best, "label": TYPES[best]["label"], "have": best in have, "reasons": reasons, "withholding": wh}
