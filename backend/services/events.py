"""Actualités transformées en faits mesurables, puis en a priori chiffrés.

1. Chaque article est classé dans une liste fermée de types d'événements (mots-clés FR / EN sur le titre ; l'IA, quand elle
   est utilisée, précise le type, l'ampleur, le caractère ponctuel ou durable et l'effet sur l'avantage concurrentiel).
2. Étude d'événements sur l'archive locale (24 mois d'articles) : pour chaque type, rendement anormal moyen (face à l'indice
   de la région) le jour de l'annonce puis à 5, 20 et 60 séances, avec un intervalle de confiance.
3. Pour une valeur, chaque événement récent reçoit l'a priori de son type et un test « déjà dans les prix ? » : réaction
   du jour comparée à ce que ce type d'événement a produit en moyenne.
Seul le premier article d'un groupe de doublons compte (même valeur, même type, 5 jours)."""
import bisect
import json
import math
import re
import statistics
import time

import store

TYPES = {
    "earnings_beat": (1, r"beats? (estimates|expectations|forecasts)|tops? (estimates|expectations)|better[- ]than[- ]expected|above (estimates|expectations)|"
                         r"dépasse (les )?(attentes|prévisions|estimations)|supérieurs? aux attentes|meilleurs? que prévu"),
    "earnings_miss": (-1, r"miss(es|ed)? (estimates|expectations|forecasts)|below (estimates|expectations)|worse[- ]than[- ]expected|falls? short|"
                          r"inférieurs? aux attentes|déçoit|déçu|en deçà des attentes|moins bons? que prévu"),
    "guidance_up": (1, r"raises? (its |full[- ]year )?(guidance|outlook|forecast)|lifts? (guidance|outlook)|upgrades? (its )?outlook|"
                       r"relève (ses |son )?(objectifs?|prévisions?|perspectives?)|rehausse"),
    "guidance_down": (-1, r"cuts? (its |full[- ]year )?(guidance|outlook|forecast)|lowers? (guidance|outlook|forecast)|"
                          r"abaisse (ses |son )?(objectifs?|prévisions?|perspectives?)|revoit à la baisse"),
    "profit_warning": (-1, r"profit warning|warns? (on|of) (profit|earnings|sales)|avertissement sur (ses )?(résultats|bénéfices)"),
    "buyback": (1, r"buy ?back|share repurchase|rachat d'actions|rachète ses (propres )?actions"),
    "dividend_up": (1, r"(raises?|hikes?|increases?) (its )?dividend|dividend (increase|hike)|(hausse|relève|augmente) (de )?(son )?dividende|dividende en hausse"),
    "dividend_cut": (-1, r"(cuts?|suspends?|slashes?) (its )?dividend|dividend cut|(réduit|suspend|supprime|baisse) (son |le )?dividende"),
    "acquisition": (0, r"to (acquire|buy)|acquires?|agrees? to buy|takeover bid|rachète|acquiert|acquisition de|offre publique"),
    "divestment": (0, r"to sell (its )?(unit|division|stake|business)|divests?|spin[- ]?off|cède|cession de"),
    "ceo_change": (0, r"(ceo|chief executive) (steps down|resigns|to step down|ousted|replaced)|names? new (ceo|chief executive)|"
                      r"(nouveau|nouvelle) (pdg|directeur général|directrice générale)|démission du (pdg|directeur)"),
    "litigation": (-1, r"lawsuit|sued|antitrust|probe|investigation|fine[ds]? |class action|procès|enquête|amende|condamné"),
    "contract_loss": (-1, r"loses? (a |the )?contract|contract (cancelled|terminated)|perd (un |le )?contrat|contrat (annulé|résilié)"),
    "contract_win": (1, r"wins? (a |the )?(\$?[\d.,]+ ?(bn|billion|m|million) )?contract|awarded (a )?contract|remporte (un |le )?contrat|décroche"),
}
_RX = {k: re.compile(v[1], re.I) for k, v in TYPES.items()}
HORIZONS = {"d0": 0, "d5": 5, "d20": 20, "d60": 60}
DEDUP_DAYS = 5


def classify(headline: str, ai_event: str | None = None) -> str | None:
    """Type d'événement d'un titre (le type donné par l'IA est prioritaire s'il appartient à la liste)."""
    if ai_event:
        try:
            t = json.loads(ai_event).get("type")
            if t in TYPES:
                return t
        except (ValueError, AttributeError):
            pass
    for k, rx in _RX.items():
        if rx.search(headline or ""):
            return k
    return None


_LEGAL = re.compile(r"\b(inc|corp|corporation|company|co|ltd|plc|s\.?a|se|n\.?v|ag|asa|ab|oyj|spa|s\.p\.a|group|groupe|holdings?|international|the)\b\.?", re.I)


def name_tokens(symbol: str) -> list[str]:
    """Mots qui désignent la société dans un titre (ex. « LVMH », « Air Liquide ») : évite d'attribuer à MC.PA un article
    sur Moelis (ticker MC) ou un article général qui ne la nomme pas."""
    import catalog
    name = (catalog.lookup(symbol) or {}).get("name") or ""
    words = [re.sub(r"^(l|d)['’]", "", w, flags=re.I) for w in re.split(r"[\s,.()\-–]+", _LEGAL.sub(" ", name))]
    words = [w for w in words if len(w) >= 3]
    out = []
    if words:
        out.append(words[0] if len(words[0]) >= 4 or len(words) == 1 else f"{words[0]} {words[1]}")
    base = symbol.split(".")[0]
    if len(base) >= 4 and base.isalpha():
        out.append(base)
    return [o.lower() for o in out]


def relevant(symbol: str, headline: str) -> bool:
    toks = name_tokens(symbol)
    h = (headline or "").lower()
    return not toks or any(re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", h) for t in toks)


def _first_of_groups(rows):
    """Premier article de chaque groupe (même valeur, même type, moins de 5 jours d'écart)."""
    out, last = [], {}
    for r in sorted(rows, key=lambda r: r["timestamp"]):
        k = (r["symbol"], r["type"])
        if k in last and r["timestamp"] - last[k] < DEDUP_DAYS * 86400:
            continue
        last[k] = r["timestamp"]
        out.append(r)
    return out


def detected(symbol: str | None = None, since: float = 0) -> list[dict]:
    q = "SELECT symbol, headline, url, source, timestamp, ai_event FROM articles WHERE timestamp >= ? AND symbol NOT LIKE '\\_%' ESCAPE '\\'"
    args: list = [since]
    if symbol:
        q += " AND symbol = ?"
        args.append(symbol.upper())
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute(q, args)]
    names: dict[str, list] = {}
    for r in rows:
        r["type"] = classify(r["headline"], r.get("ai_event"))
    keep = []
    for r in rows:
        if not r["type"]:
            continue
        if r["symbol"] not in names:
            names[r["symbol"]] = name_tokens(r["symbol"])
        toks, h = names[r["symbol"]], r["headline"].lower()
        if not toks or any(re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", h) for t in toks):
            keep.append(r)
    return _first_of_groups(keep)


def _closes(hist):
    return [p["ts"] for p in hist], [p.get("adj") or p["close"] for p in hist]


def abnormal(hist, bench, ts) -> dict | None:
    """Rendement de la valeur moins celui de l'indice : jour de l'annonce (veille -> jour), puis dérive à 5, 20, 60 séances."""
    days, px = _closes(hist)
    bdays, bpx = _closes(bench)
    i = bisect.bisect_left(days, ts - 6 * 3600)  # séance de l'annonce (ou la suivante si publiée après la clôture)
    if i <= 0 or i >= len(days):
        return None
    out = {}
    for k, n in HORIZONS.items():
        j = i + n
        if j >= len(days):
            continue
        start, end = (i - 1, i) if n == 0 else (i, j)
        b0 = bisect.bisect_right(bdays, days[start]) - 1
        b1 = bisect.bisect_right(bdays, days[end]) - 1
        if b0 < 0 or b1 < 0 or not bpx[b0]:
            continue
        out[k] = round(((px[end] / px[start]) - (bpx[b1] / bpx[b0])) * 100, 2)
    return out or None


def study(fetch_hist, bench_for, since_days: int = 760) -> dict:
    """Étude d'événements sur l'archive : a priori chiffré par type (moyenne, intervalle de confiance, nombre)."""
    evs = detected(since=time.time() - since_days * 86400)
    samples: dict[str, dict[str, list]] = {}
    cache: dict[str, list] = {}
    for e in evs:
        sym = e["symbol"]
        if sym not in cache:
            try:
                cache[sym] = fetch_hist(sym)
            except Exception:
                cache[sym] = []
        if not cache[sym]:
            continue
        ab = abnormal(cache[sym], bench_for(sym), e["timestamp"])
        if not ab:
            continue
        for k, v in ab.items():
            samples.setdefault(e["type"], {}).setdefault(k, []).append(v)
    out = {}
    for t, hz in samples.items():
        out[t] = {"direction": TYPES[t][0]}
        for k, vals in hz.items():
            m = statistics.mean(vals)
            half = 1.96 * statistics.pstdev(vals) / math.sqrt(len(vals)) if len(vals) > 1 else None
            out[t][k] = {"mean": round(m, 2), "n": len(vals), "low": round(m - half, 2) if half is not None else None,
                         "high": round(m + half, 2) if half is not None else None}
    return {"computed_at": int(time.time()), "events": len(evs), "types": out}


def latest_study() -> dict | None:
    raw = store.get_setting("event_study")
    return json.loads(raw) if raw else None


def for_symbol(symbol: str, hist, bench, days: int = 90) -> list[dict]:
    """Événements récents d'une valeur, avec l'a priori historique de leur type et le test « déjà dans les prix ? »."""
    st = (latest_study() or {}).get("types", {})
    out = []
    for e in sorted(detected(symbol, time.time() - days * 86400), key=lambda e: -e["timestamp"]):
        ab = abnormal(hist, bench, e["timestamp"]) if hist and bench else None
        prior = st.get(e["type"]) or {}
        react, expected = (ab or {}).get("d0"), (prior.get("d0") or {}).get("mean")
        drift = (prior.get("d60") or {})
        note = None
        if react is not None:
            if TYPES[e["type"]][0] > 0 and react <= 0:
                note = "good_news_ignored"       # bonne nouvelle, cours plat ou en baisse : opportunité possible
            elif TYPES[e["type"]][0] < 0 and react <= -10:
                note = "possible_overreaction"   # mauvaise nouvelle, chute de plus de 10 % : surréaction possible
            elif expected is not None and abs(react - expected) <= 1:
                note = "priced_as_usual"
        ai = None
        try:
            ai = json.loads(e["ai_event"]) if e.get("ai_event") else None
        except ValueError:
            pass
        out.append({"type": e["type"], "direction": TYPES[e["type"]][0], "headline": e["headline"], "url": e["url"],
                    "source": e["source"], "timestamp": e["timestamp"], "reaction": react, "since": ab,
                    "prior_d0": prior.get("d0"), "prior_d60": drift or None, "note": note, "ai": ai})
    return out
