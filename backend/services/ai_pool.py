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


OPENROUTER_FAMILIES = ["gpt-oss-120b", "gemma-4-31b", "llama-3.3-70b", "deepseek", "nemotron-3-ultra", "qwen", "gemma", "inkling"]


# Requêtes par jour et par clé (offres gratuites, ordre de grandeur) ; l'arrière-plan n'en utilise que 70 %
DAILY_BUDGET = {"groq": 300, "gemini": 200, "cerebras": 400, "openrouter": 45, "mistral": 300}
BACKGROUND_SHARE = 0.7
BACKGROUND_INTERVAL = 90  # secondes minimum entre deux analyses d'arrière-plan sur une même clé
INTERACTIVE_GRACE = 120  # l'arrière-plan s'efface pendant 2 min après une demande de l'utilisateur
_last_interactive = 0.0


class NoCapacity(Exception):
    pass


_lock = threading.Lock()
_state: dict[str, dict] = {}  # id -> {cooldown_until, reason, ok, errors, last_error, model, last_used, day, used_today}
_PERSISTED = ("cooldown_until", "reason", "day", "used_today")


def _restore():
    raw = store.get_setting("ai_usage")
    for kid, st in (json.loads(raw) if raw else {}).items():
        _state.setdefault(kid, {}).update({k: v for k, v in st.items() if k in _PERSISTED})


def _persist():
    store.set_setting("ai_usage", json.dumps({kid: {k: st[k] for k in _PERSISTED if k in st} for kid, st in _state.items()}))


def _count(entry: dict):
    st = _state.setdefault(entry["id"], {})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if st.get("day") != today:
        st["day"], st["used_today"] = today, 0
    st["used_today"] = st.get("used_today", 0) + 1


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
        today = time.strftime("%Y-%m-%d", time.gmtime())
        out.append({"id": k["id"], "provider": k["provider"], "hint": f"…{k['key'][-4:]}", "model": st.get("model"),
                    "ok": st.get("ok", 0), "errors": st.get("errors", 0), "last_error": st.get("last_error"),
                    "cooldown": max(0, int(st.get("cooldown_until", 0) - now)), "reason": st.get("reason"),
                    "used_today": st.get("used_today", 0) if st.get("day") == today else 0,
                    "budget": DAILY_BUDGET.get(k["provider"], 100)})
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


def _background_ok(k: dict, now: float) -> bool:
    st = _state.get(k["id"], {})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    used = st.get("used_today", 0) if st.get("day") == today else 0
    return (used < DAILY_BUDGET.get(k["provider"], 100) * BACKGROUND_SHARE
            and now - st.get("last_used", 0) >= BACKGROUND_INTERVAL and now - _last_interactive >= INTERACTIVE_GRACE)


def available_count(background: bool = False) -> int:
    now = time.time()
    return sum(1 for k in _load() if _state.get(k["id"], {}).get("cooldown_until", 0) <= now and (not background or _background_ok(k, now)))


def next_available() -> int:
    """Secondes avant qu'une clé redevienne disponible (0 si une clé est libre)."""
    now = time.time()
    waits = [max(0.0, _state.get(k["id"], {}).get("cooldown_until", 0) - now) for k in _load()]
    return int(min(waits)) if waits else 0


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
            # Les modèles gratuits changent souvent : choix par famille, en écartant les modèles spécialisés
            free = [m for m in ids if m.endswith(":free") and not any(x in m for x in ("safety", "code", "guard", "omni", "vl:", "lfm"))]
            ranked = [m for fam in OPENROUTER_FAMILIES for m in free if fam in m] + free
            ranked = list(dict.fromkeys(ranked))
            model = ranked[0] if ranked else None
            st["fallbacks"] = ranked[1:3]  # modèles de repli si le modèle gratuit principal est saturé
        st["model"] = model or p["models"][0]
    except requests.HTTPError:
        raise
    except Exception:
        st["model"] = p["models"][0]
    return st["model"]


def _seconds_to_midnight() -> float:
    return 86400 - time.time() % 86400 + 60


def _wait_seconds(res) -> float:
    reset = res.headers.get("x-ratelimit-reset")
    if reset and reset.isdigit():  # OpenRouter : horodatage en millisecondes
        return max(1.0, int(reset) / 1000 - time.time())
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
    fallbacks = _state.get(entry["id"], {}).get("fallbacks")
    if entry["provider"] == "openrouter" and fallbacks:
        body["models"] = [model] + fallbacks
    if "gpt-oss" in model and entry["provider"] in ("groq", "cerebras"):
        body["reasoning_effort"] = "low"
    res = requests.post(f"{p['base']}/chat/completions", headers={"Authorization": f"Bearer {entry['key']}"}, json=body, timeout=120)
    if res.status_code == 400 and "response_format" in res.text:
        body.pop("response_format")
        res = requests.post(f"{p['base']}/chat/completions", headers={"Authorization": f"Bearer {entry['key']}"}, json=body, timeout=120)
    if res.status_code == 429:
        body = res.text.lower()
        daily = any(w in body for w in ("per day", "per-day", "daily", "free-models-per-day", "quota exceeded", "rpd"))
        raise _RateLimited(_seconds_to_midnight() if daily and "x-ratelimit-reset" not in res.headers else _wait_seconds(res),
                           "daily" if daily else "rate")
    if res.status_code in (400, 404) and "model" in res.text.lower():
        _state.get(entry["id"], {}).pop("model", None)  # modèle retiré : nouveau choix au prochain appel
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict:
    """Objet JSON de la réponse, même entouré d'un raisonnement ou de texte (on garde le plus grand objet valide)."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    dec, best = json.JSONDecoder(), None
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, end = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict) and (best is None or end - i > best[0]):
                best = (end - i, obj)
    if best is None:
        raise ValueError("Réponse IA sans JSON exploitable")
    return best[1]


class _RateLimited(Exception):
    def __init__(self, wait, reason="rate"):
        self.wait, self.reason = wait, reason


def _pick(exclude: set, background: bool = False) -> dict | None:
    now = time.time()
    with _lock:
        ready = [k for k in _load() if k["id"] not in exclude and _state.get(k["id"], {}).get("cooldown_until", 0) <= now
                 and (not background or _background_ok(k, now))]
        if not ready:
            return None
        k = min(ready, key=lambda k: _state.get(k["id"], {}).get("last_used", 0))
        _state.setdefault(k["id"], {})["last_used"] = now
        return k


def complete_json(prompt: str, max_wait: float = 0, background: bool = False) -> tuple[dict, str]:
    """Envoie le prompt à la première clé disponible. Renvoie (réponse JSON, fournisseur).
    background=True : analyse automatique, limitée à une part du quota et suspendue quand l'utilisateur demande une analyse."""
    global _last_interactive
    if not _state:
        _restore()
    if not background:
        _last_interactive = time.time()
    deadline = time.time() + max_wait
    tried: set = set()
    last_error = "Aucune clé IA configurée"
    while True:
        entry = _pick(tried, background)
        if entry is None:
            cooldowns = [s.get("cooldown_until", 0) for s in _state.values() if s.get("cooldown_until", 0) > time.time()]
            nxt = min(cooldowns) if cooldowns else 0
            if background or not has_keys() or not nxt or nxt > deadline:
                raise NoCapacity(last_error if not nxt else f"{last_error} — de nouveau disponible dans {int((nxt - time.time()) / 60) + 1} min")
            time.sleep(nxt - time.time() + 0.5)
            tried.clear()
            continue
        st = _state.setdefault(entry["id"], {})
        try:
            _count(entry)
            text = _request(entry, prompt)
            st["ok"] = st.get("ok", 0) + 1
            st["last_error"] = None
            return extract_json(text), entry["provider"]
        except _RateLimited as e:
            st["cooldown_until"] = time.time() + min(e.wait, 86400) + 1
            st["reason"] = e.reason
            last_error = f"{entry['provider']} : {'quota du jour atteint' if e.reason == 'daily' else 'limite de débit atteinte'}"
        except Exception as e:
            st["errors"] = st.get("errors", 0) + 1
            st["last_error"] = str(e)[:200]
            last_error = f"{entry['provider']} : {st['last_error']}"
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code in (401, 403):
                st["cooldown_until"] = time.time() + 3600
        finally:
            _persist()
        tried.add(entry["id"])
