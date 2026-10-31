import os
import shutil
import sqlite3
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Dossier de données : défini par l'application de bureau (profil utilisateur), sinon racine du dépôt en dev
DATA_DIR = os.environ.get("STOCKPULSE_DATA_DIR") or os.path.join(BASE_DIR, "..")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "market_news.db")

# Premier lancement de l'app installée : reprend l'archive d'articles fournie avec l'installateur
_seed = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "market_news.db")
if not os.path.exists(DB_PATH) and os.path.exists(_seed):
    shutil.copy(_seed, DB_PATH)
    _fresh_install = True
else:
    _fresh_install = False

_lock = threading.Lock()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _lock, connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT, headline TEXT, summary TEXT, url TEXT UNIQUE,
                source TEXT, published_at TEXT, timestamp INTEGER, sentiment TEXT
            );
            CREATE TABLE IF NOT EXISTS favorites (
                symbol TEXT PRIMARY KEY, name TEXT, position INTEGER,
                added_at INTEGER DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS advice_cache (
                symbol TEXT, lang TEXT, created_at INTEGER, payload TEXT,
                PRIMARY KEY (symbol, lang)
            );
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, quantity REAL NOT NULL,
                avg_price REAL NOT NULL, added_at INTEGER DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS advice_history (
                symbol TEXT, day TEXT, verdict TEXT, score INTEGER, price REAL, engine TEXT, PRIMARY KEY (symbol, day)
            );
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, direction TEXT, price REAL, triggered_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS notified (key TEXT PRIMARY KEY, at INTEGER);
            CREATE TABLE IF NOT EXISTS orders_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, quantity REAL, price REAL, fees REAL,
                at INTEGER DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS pea_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, type TEXT NOT NULL, symbol TEXT,
                quantity REAL, price REAL, fees REAL DEFAULT 0, amount REAL, created_at INTEGER DEFAULT (strftime('%s','now'))
            );
            CREATE INDEX IF NOT EXISTS idx_articles_symbol_ts ON articles(symbol, timestamp);
        ''')
        cols = [r[1] for r in conn.execute("PRAGMA table_info(articles)")]
        if "sentiment_score" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN sentiment_score REAL")
        mcols = [r[1] for r in conn.execute("PRAGMA table_info(pea_movements)")]
        if "fx" not in mcols:
            conn.execute("ALTER TABLE pea_movements ADD COLUMN fx REAL")
        if "ai_sentiment" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN ai_sentiment TEXT")
        if _fresh_install:  # seule l'archive d'articles est partagée : PEA, favoris, clés et réglages propres à chaque machine
            for t in PERSONAL_TABLES:
                conn.execute(f"DELETE FROM {t}")


PERSONAL_TABLES = ("favorites", "settings", "advice_cache", "holdings", "advice_history", "price_alerts",
                   "notified", "orders_log", "pea_movements")


def get_setting(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with _lock, connect() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))


# --- Secrets (clés IA) : chiffrés avec le compte Windows (DPAPI), illisibles depuis une autre session ou un autre PC ---
if sys.platform == "win32":
    import base64
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _dpapi(data: bytes, protect: bool) -> bytes:
        buf = ctypes.create_string_buffer(data, len(data))
        blob_in, blob_out = _Blob(len(data), buf), _Blob()
        fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0x01, ctypes.byref(blob_out)):
            raise OSError("Échec DPAPI")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def _encrypt(text: str) -> str:
        return "dpapi:" + base64.b64encode(_dpapi(text.encode(), True)).decode()

    def _decrypt(value: str) -> str:
        return _dpapi(base64.b64decode(value[6:]), False).decode()
else:
    def _encrypt(text: str) -> str:
        return "plain:" + text

    def _decrypt(value: str) -> str:
        raise ValueError("Secret chiffré illisible sur ce système")


def get_secret(key: str, default: str = "") -> str:
    value = get_setting(key)
    if not value:
        return default
    if value.startswith("plain:"):
        return value[6:]
    if value.startswith("dpapi:"):
        return _decrypt(value)
    set_secret(key, value)  # valeur en clair d'une version précédente : chiffrée au passage
    return value


def set_secret(key: str, value: str):
    try:
        set_setting(key, _encrypt(value))
    except OSError:
        set_setting(key, "plain:" + value)
