"""Conversion centrale des devises vers l'euro : tous les montants comparés, additionnés ou affichés en euros
passent par ce module (cours Yahoo XXXEUR=X, cache 10 min ; GBp = pence)."""
import threading
import time

from services import yahoo

TTL = 600
_cache: dict[str, tuple[float, float | None]] = {"EUR": (float("inf"), 1.0)}
_lock = threading.Lock()


def rate(currency: str | None) -> float | None:
    """Euros pour 1 unité de la devise (None si le taux est introuvable)."""
    ccy = currency or "EUR"
    hit = _cache.get(ccy)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    base, div = ("GBP", 100) if ccy == "GBp" else ("ILS", 100) if ccy == "ILA" else (ccy.upper(), 1)
    try:
        value = yahoo.quote(f"{base}EUR=X")["price"] / div
    except Exception:
        value = hit[1] if hit else None  # dernier taux connu plutôt qu'aucun
    with _lock:
        _cache[ccy] = (time.time(), value)
    return value


def rates(currencies) -> dict[str, float | None]:
    return {c: rate(c) for c in set(currencies)}


def to_eur(amount: float | None, currency: str | None) -> float | None:
    r = rate(currency)
    return None if amount is None or r is None else amount * r
