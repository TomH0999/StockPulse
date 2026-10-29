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
            CREATE INDEX IF NOT EXISTS idx_articles_symbol_ts ON articles(symbol, timestamp);
        ''')
        cols = [r[1] for r in conn.execute("PRAGMA table_info(articles)")]
        if "sentiment_score" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN sentiment_score REAL")
        if "ai_sentiment" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN ai_sentiment TEXT")


def get_setting(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with _lock, connect() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
