"""Objectifs et paramètres du PEA choisis par l'utilisateur."""
import json

import store

DEFAULTS = {
    "opened": None,          # date d'ouverture du PEA (AAAA-MM-JJ)
    "monthly_deposit": 0.0,  # versement programmé mensuel (€)
    "etf_share": 0.0,        # part cible d'ETF (%)
    "etf_symbol": "CW8.PA",  # ETF socle (MSCI World éligible PEA)
    "max_line": 20.0,        # % maximum par ligne
    "max_sector": 35.0,      # % maximum par secteur
    "cash_reserve": 2.0,     # % de liquidités conservées
    "fx_fee_pct": 0.0,       # frais de change du courtier (%)
    "ttf": True,             # taxe sur les transactions financières (0,4 % depuis 2025 : grandes sociétés françaises)
}
LIMITS = {"monthly_deposit": (0, 20000), "etf_share": (0, 100), "max_line": (5, 100), "max_sector": (10, 100),
          "cash_reserve": (0, 50), "fx_fee_pct": (0, 5)}


def get() -> dict:
    raw = store.get_setting("objectives")
    return {**DEFAULTS, **(json.loads(raw) if raw else {})}


def update(values: dict) -> dict:
    cur = get()
    for k, v in values.items():
        if k not in DEFAULTS:
            continue
        if k in LIMITS:
            lo, hi = LIMITS[k]
            v = float(v)
            if not lo <= v <= hi:
                raise ValueError(f"{k} doit être entre {lo} et {hi}")
        cur[k] = v
    store.set_setting("objectives", json.dumps(cur))
    return cur
