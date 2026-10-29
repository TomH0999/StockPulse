import time

import pytest
import requests

from services import ai_pool


class Resp:
    def __init__(self, status, headers=None):
        self.status_code, self.headers, self.text = status, headers or {}, ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


@pytest.fixture(autouse=True)
def reset_state():
    ai_pool._state.clear()
    yield
    ai_pool._state.clear()


def add_keys(monkeypatch, *providers):
    monkeypatch.setattr(ai_pool, "_request", lambda e, p, max_tokens=4000: '{"ok": true}')
    for i, p in enumerate(providers):
        ai_pool.add_key(p, f"key-{p}-{i}")
    return ai_pool.keys()


@pytest.mark.parametrize("header,value,expected", [("retry-after", "12", 12), ("x-ratelimit-reset-tokens", "7.66s", 7.66),
                                                  ("x-ratelimit-reset-tokens", "2m59.5s", 179.5), ("x-ratelimit-reset-requests", "1h2m3s", 3723)])
def test_wait_seconds(header, value, expected):
    assert ai_pool._wait_seconds(Resp(429, {header: value})) == pytest.approx(expected)


def test_add_remove_and_public_view(monkeypatch):
    keys = add_keys(monkeypatch, "groq", "gemini")
    assert [k["provider"] for k in keys] == ["groq", "gemini"]
    pub = ai_pool.public_keys()
    assert all("key" not in k and k["hint"].startswith("…") for k in pub)
    ai_pool.remove_key(keys[0]["id"])
    assert [k["provider"] for k in ai_pool.keys()] == ["gemini"]
    with pytest.raises(ValueError):
        ai_pool.add_key("unknown", "x")


def test_rotation_on_rate_limit(monkeypatch):
    add_keys(monkeypatch, "groq", "cerebras")
    calls = []

    def req(entry, prompt, max_tokens=4000):
        calls.append(entry["provider"])
        if entry["provider"] == "groq":
            raise ai_pool._RateLimited(30)
        return '{"verdict": "BUY"}'
    monkeypatch.setattr(ai_pool, "_request", req)
    out, provider = ai_pool.complete_json("p")
    assert out == {"verdict": "BUY"} and provider == "cerebras"
    assert ai_pool.available_count() == 1  # groq en pause
    out, provider = ai_pool.complete_json("p")
    assert provider == "cerebras" and calls.count("groq") == 1


def test_no_capacity_and_auth_error(monkeypatch):
    with pytest.raises(ai_pool.NoCapacity):
        ai_pool.complete_json("p")
    add_keys(monkeypatch, "groq")

    def req(entry, prompt, max_tokens=4000):
        raise requests.HTTPError("401", response=Resp(401))
    monkeypatch.setattr(ai_pool, "_request", req)
    with pytest.raises(ai_pool.NoCapacity):
        ai_pool.complete_json("p")
    st = ai_pool.public_keys()[0]
    assert st["errors"] == 1 and st["cooldown"] > 3000


def test_waits_for_cooldown_within_max_wait(monkeypatch):
    add_keys(monkeypatch, "groq")
    k = ai_pool.keys()[0]
    ai_pool._state[k["id"]] = {"cooldown_until": time.time() + 0.5}
    monkeypatch.setattr(ai_pool, "_request", lambda e, p, max_tokens=4000: 'text {"ok": 1} trailing')
    assert ai_pool.complete_json("p", max_wait=5)[0] == {"ok": 1}


def test_keys_are_stored_encrypted_or_marked(monkeypatch):
    import store
    add_keys(monkeypatch, "groq")
    raw = store.get_setting("ai_keys")
    assert raw.startswith(("plain:", "dpapi:"))
