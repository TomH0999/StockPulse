"""Pool de clés IA gratuites (plusieurs fournisseurs compatibles OpenAI) avec rotation et respect des limites de débit."""
import json
import re
import threading
import time
import uuid

import requests

import store

PROVIDERS = {
    "groq": {"base": "https://api.groq.com/openai/v1",
             "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]},
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "models": ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]},
    "cerebras": {"base": "https://api.cerebras.ai/v1",
                 "models": ["gpt-oss-120b", "llama-3.3-70b", "qwen-3-235b-a22b-instruct-2507", "llama3.1-8b"]},
    "openrouter": {"base": "https://openrouter.ai/api/v1",
                   "models": ["openai/gpt-oss-120b:free", "meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat-v3-0324:free"]},
    "mistral": {"base": "https://api.mistral.ai/v1",
                "models": ["mistral-small-latest", "mistral-medium-latest", "open-mistral-nemo"]},
}


class NoCapacity(Exception):
    pass


_lock = threading.Lock()
_state: dict[str, dict] = {}  # id -> {cooldown_until, ok, errors, last_error, model, last_used}


def _load() -> list[dict]:
    raw = store.get_secret("ai_keys")
    if raw:
        return json.loads(raw)
    # Reprise de la configuration de la version 1.0 (une seule clé)
    provider, key = store.get_setting("ai_provider"), store.get_setting("ai_key")
    keys = [{"id": uuid.uuid4().hex[:8], "provider": provider, "key": key}] if key and provider in PROVIDERS else []
    _save(keys)
    store.set_setting("ai_key", "")
    return keys


def _save(keys: list[dict]):
    store.set_secret("ai_keys", json.dumps(keys))


def keys() -> list[dict]:
    return _load()


def public_keys() -> list[dict]:
    now = time.time()
    out = []
    for k in _load():
        st = _state.get(k["id"], {})
        out.append({"id": k["id"], "provider": k["provider"], "hint": f"…{k['key'][-4:]}", "model": st.get("model"),
                    "ok": st.get("ok", 0), "errors": st.get("errors", 0), "last_error": st.get("last_error"),
                    "cooldown": max(0, int(st.get("cooldown_until", 0) - now))})
    return out


def add_key(provider: str, key: str) -> dict:
    if provider not in PROVIDERS:
        raise ValueError("Fournisseur inconnu")
    key = key.strip()
    entry = {"id": uuid.uuid4().hex[:8], "provider": provider, "key": key}
    _request(entry, 'Reply with the JSON {"ok": true}', max_tokens=50)  # vérifie la clé avant de l'enregistrer
    with _lock:
        ks = [k for k in _load() if k["key"] != key] + [entry]
        _save(ks)
    return entry


def remove_key(key_id: str):
    with _lock:
        _save([k for k in _load() if k["id"] != key_id])
        _state.pop(key_id, None)


def has_keys() -> bool:
    return bool(_load())


def available_count() -> int:
    now = time.time()
    return sum(1 for k in _load() if _state.get(k["id"], {}).get("cooldown_until", 0) <= now)


def _model(entry: dict) -> str:
    st = _state.setdefault(entry["id"], {})
    if st.get("model"):
        return st["model"]
    p = PROVIDERS[entry["provider"]]
    try:
        res = requests.get(f"{p['base']}/models", headers={"Authorization": f"Bearer {entry['key']}"}, timeout=20)
        res.raise_for_status()
        ids = [m["id"].removeprefix("models/") for m in res.json().get("data", [])]
        model = next((m for m in p["models"] if m in ids), None)
        if not model and entry["provider"] == "openrouter":
            model = next((m for m in ids if m.endswith(":free")), None)
        st["model"] = model or p["models"][0]
    except requests.HTTPError:
        raise
    except Exception:
        st["model"] = p["models"][0]
    return st["model"]


def _wait_seconds(res) -> float:
    for h in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        v = res.headers.get(h)
        if not v:
            continue
        m = re.match(r"^(?:(\d+)h)?(?:(\d+)m(?!s))?(?:([\d.]+)s)?$", v)
        if v.replace(".", "", 1).isdigit():
            return float(v)
        if m and any(m.groups()):
            return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0)
    return 30.0


def _request(entry: dict, prompt: str, max_tokens: int = 4000) -> str:
    p = PROVIDERS[entry["provider"]]
    model = _model(entry)
    body = {"model": model, "temperature": 0.3, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    if "gpt-oss" in model and entry["provider"] in ("groq", "cerebras"):
        body["reasoning_effort"] = "low"
    res = requests.post(f"{p['base']}/chat/completions", headers={"Authorization": f"Bearer {entry['key']}"}, json=body, timeout=120)
    if res.status_code == 400 and "response_format" in res.text:
        body.pop("response_format")
        res = requests.post(f"{p['base']}/chat/completions", headers={"Authorization": f"Bearer {entry['key']}"}, json=body, timeout=120)
    if res.status_code == 429:
        raise _RateLimited(_wait_seconds(res))
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


class _RateLimited(Exception):
    def __init__(self, wait):
        self.wait = wait


def _pick(exclude: set) -> dict | None:
    now = time.time()
    with _lock:
        ready = [k for k in _load() if k["id"] not in exclude and _state.get(k["id"], {}).get("cooldown_until", 0) <= now]
        if not ready:
            return None
        k = min(ready, key=lambda k: _state.get(k["id"], {}).get("last_used", 0))
        _state.setdefault(k["id"], {})["last_used"] = now
        return k


def complete_json(prompt: str, max_wait: float = 0) -> tuple[dict, str]:
    """Envoie le prompt à la première clé disponible. Renvoie (réponse JSON, fournisseur)."""
    deadline = time.time() + max_wait
    tried: set = set()
    last_error = "Aucune clé IA configurée"
    while True:
        entry = _pick(tried)
        if entry is None:
            cooldowns = [s.get("cooldown_until", 0) for s in _state.values() if s.get("cooldown_until", 0) > time.time()]
            nxt = min(cooldowns) if cooldowns else 0
            if not has_keys() or not nxt or nxt > deadline:
                raise NoCapacity(last_error)
            time.sleep(nxt - time.time() + 0.5)
            tried.clear()
            continue
        st = _state.setdefault(entry["id"], {})
        try:
            text = _request(entry, prompt)
            st["ok"] = st.get("ok", 0) + 1
            st["last_error"] = None
            return json.loads(text[text.find("{"): text.rfind("}") + 1]), entry["provider"]
        except _RateLimited as e:
            st["cooldown_until"] = time.time() + min(e.wait, 3600) + 1
            last_error = f"{entry['provider']} : limite de débit atteinte"
        except Exception as e:
            st["errors"] = st.get("errors", 0) + 1
            st["last_error"] = str(e)[:200]
            last_error = f"{entry['provider']} : {st['last_error']}"
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code in (401, 403):
                st["cooldown_until"] = time.time() + 3600
        tried.add(entry["id"])
