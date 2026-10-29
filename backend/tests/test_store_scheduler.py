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
    q = scheduler._queue(ai=False)
    assert q[0] == "ZZFAV.PA" and len(q) > 500
    advisor.advise("MC.PA", "fr")
    assert "MC.PA" not in scheduler._queue(ai=False)  # analyse locale fraîche
    assert "MC.PA" in scheduler._queue(ai=True)  # pas encore analysée par IA


def test_frontend_fallback_route():
    import main
    from fastapi.testclient import TestClient
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main.app.routes):
        pytest.skip("interface non compilée")
    r = TestClient(main.app, base_url="http://127.0.0.1").get("/une/page/inconnue")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text
