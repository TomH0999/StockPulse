"""Journal de thèse : pourquoi j'ai acheté, ce que vaut l'entreprise selon moi, quand je vendrais. Revue annuelle."""
import time
from datetime import date, timedelta

import store
from services import accounts

REVIEW_DAYS = 365


def _init():
    with store.connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS theses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, symbol TEXT, thesis TEXT, fair_value REAL,
            sell_if TEXT, created_at INTEGER, reviewed_at INTEGER, next_review TEXT, UNIQUE (account, symbol))""")


def get(symbol: str, account: str | None = None) -> dict | None:
    _init()
    with store.connect() as conn:
        r = conn.execute("SELECT * FROM theses WHERE account = ? AND symbol = ?", (account or accounts.current(), symbol.upper())).fetchone()
    return dict(r) if r else None


def all_for(account: str | None = None) -> list[dict]:
    _init()
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM theses WHERE account = ? ORDER BY symbol", (account or accounts.current(),))]


def save(symbol: str, thesis: str, fair_value: float | None = None, sell_if: str = "", reviewed: bool = True) -> dict:
    if not (thesis or "").strip():
        raise ValueError("Écrivez au moins une phrase de thèse")
    if fair_value is not None and fair_value <= 0:
        raise ValueError("Valeur estimée positive requise")
    _init()
    acc, sym, now = accounts.current(), symbol.upper(), int(time.time())
    nxt = (date.today() + timedelta(days=REVIEW_DAYS)).isoformat()
    with store.connect() as conn:
        old = conn.execute("SELECT created_at FROM theses WHERE account = ? AND symbol = ?", (acc, sym)).fetchone()
        conn.execute("INSERT OR REPLACE INTO theses (account, symbol, thesis, fair_value, sell_if, created_at, reviewed_at, next_review)"
                     " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (acc, sym, thesis.strip()[:4000], fair_value, (sell_if or "").strip()[:2000], old[0] if old else now,
                      now if reviewed else None, nxt))
    return get(sym)


def delete(symbol: str):
    _init()
    with store.connect() as conn:
        conn.execute("DELETE FROM theses WHERE account = ? AND symbol = ?", (accounts.current(), symbol.upper()))


def due() -> list[dict]:
    """Thèses à relire (une fois par an), tous comptes confondus."""
    _init()
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM theses WHERE next_review <= ?", (date.today().isoformat(),))]
