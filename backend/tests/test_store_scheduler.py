import sys
import time

import pytest

import store
from services import advisor, scheduler


def test_secret_roundtrip_and_plaintext_migration():
    store.set_secret("s", "value-123")
    raw = store.get_setting("s")
    assert store.get_secret("s") == "value-123" and "value-123" not in raw[6:] or raw.startswith("plain:")
    if sys.platform == "win32":
        assert raw.startswith("dpapi:")
    store.set_setting("legacy", '{"k": 1}')  # valeur en clair d'une ancienne version
    assert store.get_secret("legacy") == '{"k": 1}' and store.get_setting("legacy").startswith(("plain:", "dpapi:"))


def test_database_schema_is_idempotent():
    store.init()
    store.init()
    with store.connect() as conn:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_scheduler_queue_priorities(market, monkeypatch):
    with store.connect() as conn:
        conn.execute("INSERT INTO favorites (symbol, name, position) VALUES ('ZZFAV.PA', '', 1)")
    monkeypatch.setattr(scheduler.screener, "snapshot", lambda max_age=0: ({}, time.time()))
    q = scheduler._queue()
    assert q[0] == "ZZFAV.PA" and len(q) > 500
    advisor.advise("MC.PA", "fr")
    assert "MC.PA" not in scheduler._queue()  # analyse fraîche


def test_no_automatic_ai_loop():
    assert not hasattr(scheduler, "_ai_loop")


def test_frontend_fallback_route():
    import main
    from fastapi.testclient import TestClient
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main.app.routes):
        pytest.skip("interface non compilée")
    r = TestClient(main.app, base_url="http://127.0.0.1").get("/une/page/inconnue")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text




def test_seed_db_has_no_personal_data():
    import os, sqlite3
    import store
    seed = os.path.join(os.path.dirname(store.BASE_DIR), "market_news.db")
    with sqlite3.connect(seed) as c:
        for t in store.PERSONAL_TABLES:
            if t != "settings":
                assert c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t
        assert not c.execute("SELECT key FROM settings WHERE key LIKE '%key%' OR key LIKE 'secret%'").fetchall()
