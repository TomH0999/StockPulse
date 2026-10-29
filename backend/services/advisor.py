"""Conseil d'investissement : analyse technique, rebondissements historiques, actualités, puis IA (si clé configurée)."""
import json
import math
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone

import store
from services import ai_pool, news, yahoo

CACHE_SECONDS = 3600
VERDICTS = ["SELL", "REDUCE", "HOLD", "BUY", "STRONG_BUY"]

T = {
    "fr": {
        "above200": "Cours au-dessus de la moyenne 200 jours : tendance de fond haussière.",
        "below200": "Cours sous la moyenne 200 jours : tendance de fond baissière.",
        "golden": "Croisement haussier récent (MM50 passe au-dessus de la MM200).",
        "death": "Croisement baissier récent (MM50 passe sous la MM200).",
        "rsi_hi": "RSI à {rsi:.0f} : titre en surachat, risque de repli à court terme.",
        "rsi_lo": "RSI à {rsi:.0f} : titre survendu, rebond technique possible.",
        "near_low": "Cours proche du plus bas sur 52 semaines ({pos:.0f} % de la fourchette annuelle).",
        "near_high": "Cours proche du plus haut sur 52 semaines ({pos:.0f} % de la fourchette annuelle).",
        "drawdown": "Recul de {dd:.0f} % depuis le plus haut annuel.",
        "mom_up": "Forte dynamique : {r:+.1f} % sur 3 mois.",
        "mom_dn": "Dynamique négative : {r:+.1f} % sur 3 mois.",
        "news_pos": "Flux d'actualités positif ({pos} articles favorables contre {neg} défavorables sur 30 jours).",
        "news_neg": "Flux d'actualités négatif ({neg} articles défavorables contre {pos} favorables sur 30 jours).",
        "buzz": "Couverture médiatique en forte hausse (x{x:.1f} sur 30 jours).",
        "drop_rebound": "Après ses {n} chutes brutales passées, l'action a rebondi dans {p:.0f} % des cas ({m:+.1f} % en moyenne sur 20 séances).",
        "drop_cont": "Après ses {n} chutes brutales passées, la baisse s'est prolongée dans {p:.0f} % des cas ({m:+.1f} % en moyenne sur 20 séances).",
        "jump_cont": "Après ses {n} envolées passées, la hausse s'est prolongée dans {p:.0f} % des cas ({m:+.1f} % en moyenne sur 20 séances).",
        "jump_fade": "Après ses {n} envolées passées, l'action a rendu ses gains dans {p:.0f} % des cas ({m:+.1f} % en moyenne sur 20 séances).",
        "recent_drop": "Chute brutale récente ({r:+.1f} % le {d}).",
        "recent_jump": "Envolée récente ({r:+.1f} % le {d}).",
        "season": "Historiquement, {month} est positif {p:.0f} % des années ({m:+.1f} % en moyenne).",
        "cagr": "Performance annualisée de {c:+.1f} % sur {y} ans, perte maximale historique de {dd:.0f} %.",
        "topic": "Thème d'actualité : {t}.",
        "dividend": "Rendement du dividende de {y:.1f} % sur 12 mois.",
        "summary": "{name} : verdict « {v} » (score {s:+d}/100). {lead}",
        "pros": "Points forts : {x}", "cons": "Points de vigilance : {x}",
        "topics": {"earnings": "résultats", "guidance": "prévisions", "analysts": "avis d'analystes", "legal": "juridique / régulation",
                   "m&a": "fusions-acquisitions", "buyback/dividend": "rachats d'actions / dividendes", "products/AI": "produits / IA",
                   "layoffs/restructuring": "restructuration", "macro/tariffs": "macro / droits de douane"},
        "months": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
        "v": {"STRONG_BUY": "Achat fort", "BUY": "Achat", "HOLD": "Conserver", "REDUCE": "Alléger", "SELL": "Vendre"},
    },
    "en": {
        "above200": "Price above its 200-day average: long-term uptrend.",
        "below200": "Price below its 200-day average: long-term downtrend.",
        "golden": "Recent golden cross (50-day MA crossed above 200-day MA).",
        "death": "Recent death cross (50-day MA crossed below 200-day MA).",
        "rsi_hi": "RSI at {rsi:.0f}: overbought, short-term pullback risk.",
        "rsi_lo": "RSI at {rsi:.0f}: oversold, technical rebound possible.",
        "near_low": "Trading near its 52-week low ({pos:.0f}% of the yearly range).",
        "near_high": "Trading near its 52-week high ({pos:.0f}% of the yearly range).",
        "drawdown": "Down {dd:.0f}% from its 52-week high.",
        "mom_up": "Strong momentum: {r:+.1f}% over 3 months.",
        "mom_dn": "Negative momentum: {r:+.1f}% over 3 months.",
        "news_pos": "Positive news flow ({pos} favourable vs {neg} unfavourable articles over 30 days).",
        "news_neg": "Negative news flow ({neg} unfavourable vs {pos} favourable articles over 30 days).",
        "buzz": "Media coverage rising sharply (x{x:.1f} over 30 days).",
        "drop_rebound": "After its {n} past sharp drops, the stock rebounded {p:.0f}% of the time ({m:+.1f}% avg over 20 sessions).",
        "drop_cont": "After its {n} past sharp drops, the decline continued {p:.0f}% of the time ({m:+.1f}% avg over 20 sessions).",
        "jump_cont": "After its {n} past spikes, gains extended {p:.0f}% of the time ({m:+.1f}% avg over 20 sessions).",
        "jump_fade": "After its {n} past spikes, the stock gave back gains {p:.0f}% of the time ({m:+.1f}% avg over 20 sessions).",
        "recent_drop": "Recent sharp drop ({r:+.1f}% on {d}).",
        "recent_jump": "Recent spike ({r:+.1f}% on {d}).",
        "season": "Historically, {month} is positive {p:.0f}% of years ({m:+.1f}% on average).",
        "cagr": "Annualised return of {c:+.1f}% over {y} years, worst historical drawdown {dd:.0f}%.",
        "topic": "News theme: {t}.",
        "dividend": "Dividend yield of {y:.1f}% over 12 months.",
        "summary": "{name}: “{v}” (score {s:+d}/100). {lead}",
        "pros": "Strengths: {x}", "cons": "Watch-outs: {x}", "topics": {},
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "v": {"STRONG_BUY": "Strong buy", "BUY": "Buy", "HOLD": "Hold", "REDUCE": "Reduce", "SELL": "Sell"},
    },
}
T["es"] = {**T["en"], "v": {"STRONG_BUY": "Compra fuerte", "BUY": "Comprar", "HOLD": "Mantener", "REDUCE": "Reducir", "SELL": "Vender"}}
T["zh"] = {**T["en"], "v": {"STRONG_BUY": "强烈买入", "BUY": "买入", "HOLD": "持有", "REDUCE": "减持", "SELL": "卖出"}}
LANG_NAMES = {"fr": "French", "en": "English", "es": "Spanish", "zh": "Simplified Chinese"}

TOPICS = {
    "earnings": (r"earnings|results|quarter|résultats|trimestre|revenue|chiffre d'affaires", 0),
    "guidance": (r"guidance|outlook|forecast|prévisions|perspectives", 0),
    "analysts": (r"upgrade|downgrade|price target|analyst|objectif de cours|analyste|rating", 0),
    "legal": (r"lawsuit|sued|probe|investigation|antitrust|regulator|sec |fine|enquête|amende|procès", -1),
    "m&a": (r"acquisition|acquire|merger|takeover|deal|rachat|fusion|acquiert", 1),
    "buyback/dividend": (r"buyback|repurchase|dividend|dividende|rachat d'actions", 1),
    "products/AI": (r"launch|unveil|new product| ai |artificial intelligence|chip|lancement|intelligence artificielle", 1),
    "layoffs/restructuring": (r"layoff|job cuts|restructur|licenciement|plan social", 0),
    "macro/tariffs": (r"tariff|fed |interest rate|inflation|recession|droits de douane|taux", -1),
}


def _ret(c, n):
    return (c[-1] / c[-1 - n] - 1) * 100 if len(c) > n and c[-1 - n] else None


def _sma(c, n):
    return sum(c[-n:]) / n if len(c) >= n else None


def _rsi(c, n=14):
    if len(c) <= n:
        return None
    gains = losses = 0.0
    for a, b in zip(c[-n - 1:-1], c[-n:]):
        d = b - a
        gains, losses = gains + max(d, 0), losses + max(-d, 0)
    return 100.0 if losses == 0 else 100 - 100 / (1 + gains / losses)


def technicals(hist):
    c = [p["close"] for p in hist]
    if len(c) < 30:
        return {}
    year = c[-252:]
    hi, lo = max(year), min(year)
    sma50, sma200 = _sma(c, 50), _sma(c, 200)
    prev50 = sum(c[-70:-20]) / 50 if len(c) >= 220 else None
    prev200 = sum(c[-220:-20]) / 200 if len(c) >= 220 else None
    rets = [b / a - 1 for a, b in zip(c[:-1], c[1:]) if a]
    peak, mdd = c[0], 0.0
    for x in c:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    years = len(c) / 252
    return {
        "price": c[-1], "sma50": sma50, "sma200": sma200, "rsi14": _rsi(c),
        "ret_1m": _ret(c, 21), "ret_3m": _ret(c, 63), "ret_6m": _ret(c, 126), "ret_1y": _ret(c, 252), "ret_5y": _ret(c, 1260),
        "golden_cross": bool(prev50 and sma50 and prev50 < prev200 and sma50 > sma200),
        "death_cross": bool(prev50 and sma50 and prev50 > prev200 and sma50 < sma200),
        "range_pos": (c[-1] - lo) / (hi - lo) * 100 if hi > lo else 50.0,
        "drawdown_52w": (c[-1] / hi - 1) * 100,
        "volatility": statistics.pstdev(rets[-60:]) * math.sqrt(252) * 100 if len(rets) >= 60 else None,
        "cagr": ((c[-1] / c[0]) ** (1 / years) - 1) * 100 if years >= 1 and c[0] > 0 else None,
        "max_drawdown": mdd * 100, "years": round(years, 1),
    }


def events(hist, arts):
    """Rebondissements : séances anormales, actualités associées et comportement de l'action ensuite."""
    c = [p["close"] for p in hist]
    rets = [(i, c[i] / c[i - 1] - 1) for i in range(1, len(c)) if c[i - 1]]
    if len(rets) < 60:
        return [], {}
    sd = statistics.pstdev(r for _, r in rets)
    thr = max(2.5 * sd, 0.03)
    found, stats = [], {"drop": [], "jump": []}
    for i, r in rets:
        if abs(r) < thr:
            continue
        fwd = (c[i + 20] / c[i] - 1) * 100 if i + 20 < len(c) else None
        kind = "drop" if r < 0 else "jump"
        if fwd is not None:
            stats[kind].append(fwd)
        ts = hist[i]["ts"]
        linked = sorted((a for a in arts if ts - 2 * 86400 <= a["timestamp"] <= ts + 86400),
                        key=lambda a: -abs(a["sentiment_score"] or 0))[:3]
        found.append({"date": hist[i]["timestamp"][:10], "ts": ts, "change": round(r * 100, 2), "kind": kind,
                      "after_20d": round(fwd, 2) if fwd is not None else None,
                      "headlines": [a["headline"] for a in linked]})
    return found, stats


def seasonality(hist):
    monthly = defaultdict(list)
    last = {}
    for p in hist:
        d = datetime.fromtimestamp(p["ts"], timezone.utc)
        last.setdefault((d.year, d.month), [p["close"], p["close"]])[1] = p["close"]
    keys = sorted(last)
    for prev, cur in zip(keys, keys[1:]):
        monthly[cur[1]].append((last[cur][1] / last[prev][1] - 1) * 100)
    return monthly


def news_view(arts, now=None):
    now = now or time.time()
    recent = [a for a in arts if a["timestamp"] >= now - 30 * 86400]
    before = [a for a in arts if now - 60 * 86400 <= a["timestamp"] < now - 30 * 86400]
    wsum = wtot = 0.0
    pos = neg = 0
    topics = defaultdict(lambda: [0, 0.0])
    for a in recent:
        s = _article_score(a)
        w = math.exp(-(now - a["timestamp"]) / (10 * 86400))
        wsum, wtot = wsum + s * w, wtot + w
        pos, neg = pos + (s >= 0.15), neg + (s <= -0.15)
        text = f" {a['headline']} {a['summary']} ".lower()
        for name, (pat, _) in TOPICS.items():
            if re.search(pat, text):
                topics[name][0] += 1
                topics[name][1] += s
    return {"score": wsum / wtot if wtot else 0.0, "count": len(recent), "previous": len(before), "pos": pos, "neg": neg,
            "topics": {k: {"count": v[0], "tone": v[1] / v[0]} for k, v in topics.items()}}


def _article_score(a):
    ai = a.get("ai_sentiment")
    if ai:
        try:
            return float(ai)
        except ValueError:
            pass
    return a["sentiment_score"] or 0.0


def local_advice(sym, lang, quote, hist, arts, now=None):
    now = now or time.time()
    L = T.get(lang, T["en"])
    tech = technicals(hist)
    evs, ev_stats = events(hist, arts)
    nv = news_view(arts, now)
    opp, thr, pat = [], [], []
    parts = {}

    if tech:
        if tech["sma200"]:
            up = tech["price"] > tech["sma200"]
            parts["trend"] = 15 if up else -15
            (opp if up else thr).append(L["above200" if up else "below200"])
            if tech["sma50"]:
                parts["trend"] += 8 if tech["sma50"] > tech["sma200"] else -8
        if tech["golden_cross"]:
            parts["cross"] = 10
            opp.append(L["golden"])
        if tech["death_cross"]:
            parts["cross"] = -10
            thr.append(L["death"])
        r3 = tech["ret_3m"]
        if r3 is not None:
            parts["momentum"] = max(-12, min(12, r3 * 0.6))
            if r3 > 10:
                opp.append(L["mom_up"].format(r=r3))
            elif r3 < -10:
                thr.append(L["mom_dn"].format(r=r3))
        rsi = tech["rsi14"]
        if rsi and rsi > 70:
            parts["rsi"] = -8
            thr.append(L["rsi_hi"].format(rsi=rsi))
        elif rsi and rsi < 30:
            parts["rsi"] = 8
            opp.append(L["rsi_lo"].format(rsi=rsi))
        if tech["range_pos"] < 15:
            thr.append(L["near_low"].format(pos=tech["range_pos"]))
            if tech["drawdown_52w"] < -20:
                opp.append(L["drawdown"].format(dd=-tech["drawdown_52w"]))
        elif tech["range_pos"] > 90:
            opp.append(L["near_high"].format(pos=tech["range_pos"]))
        if tech["cagr"] is not None:
            pat.append(L["cagr"].format(c=tech["cagr"], y=int(tech["years"]), dd=-tech["max_drawdown"]))
            parts["long_term"] = max(-8, min(8, tech["cagr"] * 0.5))

    for kind in ("drop", "jump"):
        vals = ev_stats.get(kind) or []
        if len(vals) >= 4:
            p_up = sum(v > 0 for v in vals) / len(vals) * 100
            m = statistics.mean(vals)
            if kind == "drop":
                key, p = ("drop_rebound", p_up) if p_up >= 50 else ("drop_cont", 100 - p_up)
            else:
                key, p = ("jump_cont", p_up) if p_up >= 50 else ("jump_fade", 100 - p_up)
            pat.append(L[key].format(n=len(vals), p=p, m=m))
            recent = [e for e in evs if e["kind"] == kind and e["ts"] >= now - 15 * 86400]
            if recent:
                e = recent[-1]
                pat.append(L["recent_" + kind].format(r=e["change"], d=e["date"]))
                parts["pattern"] = max(-12, min(12, m * 1.5)) if abs(p_up - 50) >= 10 else 0
                (opp if m > 0 else thr).append(pat[-2])

    months = seasonality(hist)
    cur = datetime.fromtimestamp(now).month
    if len(months.get(cur, [])) >= 5:
        vals = months[cur]
        p = sum(v > 0 for v in vals) / len(vals) * 100
        pat.append(L["season"].format(month=L["months"][cur - 1], p=p, m=statistics.mean(vals)))
        if p >= 65 or p <= 35:
            parts["season"] = 4 if p >= 65 else -4

    dy = quote.get("dividend_yield")
    if dy:
        tech["dividend_yield"] = dy
        if dy >= 3:
            opp.append(L["dividend"].format(y=dy))
            parts["dividend"] = min(6, dy)
    if nv["count"]:
        parts["news"] = nv["score"] * 35
        if nv["score"] >= 0.08:
            opp.append(L["news_pos"].format(pos=nv["pos"], neg=nv["neg"]))
        elif nv["score"] <= -0.08:
            thr.append(L["news_neg"].format(pos=nv["pos"], neg=nv["neg"]))
        if nv["previous"] >= 5 and nv["count"] / nv["previous"] >= 1.8:
            pat.append(L["buzz"].format(x=nv["count"] / nv["previous"]))
        for name, t in sorted(nv["topics"].items(), key=lambda kv: -kv[1]["count"])[:4]:
            if t["count"] >= 2 and abs(t["tone"]) >= 0.1:
                (opp if t["tone"] > 0 else thr).append(L["topic"].format(t=L["topics"].get(name, name)) + f" ({t['count']} articles)")

    score = int(max(-100, min(100, round(sum(parts.values())))))
    verdict = ("STRONG_BUY" if score >= 40 else "BUY" if score >= 15 else "HOLD" if score > -15 else "REDUCE" if score > -40 else "SELL")
    signs = [v for v in parts.values() if v]
    agree = sum((v > 0) == (score > 0) for v in signs) / len(signs) if signs else 0
    confidence = "high" if agree >= 0.75 and len(signs) >= 5 else "medium" if agree >= 0.55 else "low"
    lead = ([L["pros"].format(x=opp[0].rstrip("."))] if opp else []) + ([L["cons"].format(x=thr[0].rstrip("."))] if thr else []) + pat[1:2]
    return {
        "symbol": sym, "name": quote.get("name", sym), "verdict": verdict, "verdict_label": L["v"][verdict],
        "score": score, "confidence": confidence, "horizon": None,
        "summary": L["summary"].format(name=quote.get("short_name", sym), v=L["v"][verdict], s=score, lead=". ".join(x.rstrip(".") for x in lead) + "."),
        "opportunities": opp, "threats": thr, "patterns": pat, "catalysts": [],
        "components": {k: round(v, 1) for k, v in parts.items()},
        "technicals": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in tech.items()},
        "news": {k: v for k, v in nv.items() if k != "topics"},
        "events": evs[-12:][::-1], "engine": "local", "ai_error": None, "verification": None,
        "generated_at": int(time.time()), "articles_analyzed": nv["count"],
    }


def _prompt(base, arts, lang):
    t = base["technicals"]
    lines = [f"[{i}] {datetime.fromtimestamp(a['timestamp'], timezone.utc):%Y-%m-%d} | {a['source']} | {a['headline']}"
             + (f" — {a['summary'][:120]}" if a["summary"] else "") for i, a in enumerate(arts)]
    evs = [f"{e['date']}: {e['change']:+.1f}% (20 sessions later: {e['after_20d']}%) news: {' / '.join(e['headlines']) or 'none'}"
           for e in base["events"]]
    return f"""You are a seasoned equity analyst and long-term investor. Analyse {base['name']} ({base['symbol']}).

PRICE DATA (daily, up to 10 years): {json.dumps(t)}
QUANTITATIVE SIGNALS: {json.dumps(base['components'])}
HISTORICAL PATTERNS: {json.dumps(base['patterns'], ensure_ascii=False)}
MAJOR PRICE SHOCKS (most recent first) with surrounding news: {json.dumps(evs, ensure_ascii=False)}
RECENT ARTICLES (numbered):
{chr(10).join(lines)}

Think like an investor: read every article, weigh its real impact on the business (not only its tone), relate the news to the price
history and past shocks, spot recurring patterns (how the stock reacts to earnings, legal issues, macro, etc.) and judge whether the
current situation is an opportunity or a threat. Be concrete and cite facts from the articles.

Answer ONLY with JSON, all text in {LANG_NAMES.get(lang, 'English')}:
{{"verdict": "STRONG_BUY|BUY|HOLD|REDUCE|SELL", "score": <int -100..100>, "confidence": "low|medium|high",
"horizon": "<short phrase, e.g. 3-6 months>", "summary": "<4-6 sentences of investor reasoning>",
"opportunities": ["..."], "threats": ["..."], "patterns": ["<recurring behaviours spotted>"], "catalysts": ["<upcoming events to watch>"],
"article_sentiments": [{{"i": <article number>, "s": <float -1..1 impact on the stock>}}]}}
"article_sentiments" MUST contain exactly one entry for EVERY numbered article (0 to {len(arts) - 1})."""


def advise(sym, lang="fr", force=False, use_ai=True, max_wait=60.0, backfill=True):
    """max_wait : attente maximale d'une clé IA disponible ; backfill : constitution de l'archive 24 mois."""
    sym = sym.upper()
    want_ai = use_ai and ai_pool.has_keys()
    if not force:
        with store.connect() as conn:
            row = conn.execute("SELECT created_at, payload FROM advice_cache WHERE symbol = ? AND lang = ?", (sym, lang)).fetchone()
        if row and time.time() - row[0] < CACHE_SECONDS:
            cached = json.loads(row[1])
            if cached["engine"] != "local" or not want_ai:
                return cached

    quote = yahoo.quote(sym)
    news.refresh(sym, quote.get("name", ""), backfill=backfill)
    hist = yahoo.daily_history(sym)
    arts = news.articles(sym)
    quote["dividend_yield"] = yahoo.dividend_yield(sym, quote.get("price"))
    result = local_advice(sym, lang, quote, hist, arts)
    try:
        result["track_record"] = backtest(sym, quote, hist, arts)
    except Exception as e:
        result["track_record"] = None
        print(f"Backtest {sym}: {e}")

    if want_ai:
        recent = arts[:50]
        try:
            ai, provider = ai_pool.complete_json(_prompt(result, recent, lang), max_wait)
            v = ai.get("verdict") if ai.get("verdict") in VERDICTS else result["verdict"]
            local_score = result["score"]
            known = _known_values(result, quote)
            result.update({
                "verdict": v, "verdict_label": T.get(lang, T["en"])["v"][v],
                "score": int(max(-100, min(100, ai.get("score", result["score"])))),
                "confidence": ai.get("confidence", result["confidence"]), "horizon": ai.get("horizon"),
                "summary": ai.get("summary") or result["summary"],
                "opportunities": ai.get("opportunities") or result["opportunities"],
                "threats": ai.get("threats") or result["threats"],
                "patterns": (ai.get("patterns") or []) + result["patterns"],
                "catalysts": ai.get("catalysts") or [], "engine": provider, "articles_analyzed": len(recent),
            })
            result["verification"] = verify(result, ai, local_score, known)
            with store.connect() as conn:
                for item in ai.get("article_sentiments") or []:
                    i = item.get("i")
                    if isinstance(i, int) and 0 <= i < len(recent):
                        conn.execute("UPDATE articles SET ai_sentiment = ? WHERE id = ?",
                                     (str(max(-1.0, min(1.0, float(item.get("s", 0))))), recent[i]["id"]))
        except Exception as e:
            result["ai_error"] = str(e)[:300]

    _log_history(result, quote.get("price"))
    with store.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO advice_cache (symbol, lang, created_at, payload) VALUES (?, ?, ?, ?)",
                     (sym, lang, int(time.time()), json.dumps(result, ensure_ascii=False)))
    return result


HORIZONS = {"1m": 21, "3m": 63, "6m": 126}


def _hit(verdict, ret):
    if verdict in ("BUY", "STRONG_BUY"):
        return ret > 0
    if verdict in ("SELL", "REDUCE"):
        return ret < 0
    return abs(ret) < 10


def backtest(sym, quote, hist, arts, years=5) -> dict:
    """Rejoue l'analyse locale chaque mois sur le passé et mesure si le verdict s'est révélé juste ensuite."""
    out = {h: {"n": 0, "hits": 0, "buy_returns": [], "sell_returns": []} for h in HORIZONS}
    start = max(260, len(hist) - years * 252)
    arts_sorted = sorted(arts, key=lambda a: a["timestamp"])
    for t in range(start, len(hist) - 21, 21):
        ts = hist[t]["ts"]
        past = [a for a in arts_sorted if a["timestamp"] <= ts]
        r = local_advice(sym, "en", {**quote, "dividend_yield": None}, hist[: t + 1], past, now=ts)
        for h, d in HORIZONS.items():
            if t + d < len(hist):
                ret = (hist[t + d]["close"] / hist[t]["close"] - 1) * 100
                o = out[h]
                o["n"] += 1
                o["hits"] += _hit(r["verdict"], ret)
                if r["verdict"] in ("BUY", "STRONG_BUY"):
                    o["buy_returns"].append(ret)
                elif r["verdict"] in ("SELL", "REDUCE"):
                    o["sell_returns"].append(ret)
    return {h: {"n": o["n"], "hit_rate": round(o["hits"] / o["n"] * 100) if o["n"] else None,
                "avg_after_buy": round(statistics.mean(o["buy_returns"]), 2) if o["buy_returns"] else None,
                "avg_after_sell": round(statistics.mean(o["sell_returns"]), 2) if o["sell_returns"] else None}
            for h, o in out.items()}


def _log_history(result, price):
    with store.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO advice_history (symbol, day, verdict, score, price, engine) VALUES (?, date('now'), ?, ?, ?, ?)",
                     (result["symbol"], result["verdict"], result["score"], price, result["engine"]))


def history_log(sym) -> list[dict]:
    with store.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT day, verdict, score, price, engine FROM advice_history WHERE symbol = ? ORDER BY day DESC LIMIT 60", (sym,))]


_NUM = re.compile(r"([-+−]?\d+(?:[.,]\d+)?)\s*(%|€|\$|USD|EUR)")


def _known_values(result, quote) -> list[float]:
    """Toutes les valeurs réellement calculées, auxquelles les chiffres cités par l'IA doivent correspondre."""
    vals = [v for v in result["technicals"].values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    vals += [quote.get(k) or 0 for k in ("price", "change_percent", "year_high", "year_low", "day_high", "day_low")]
    for e in result["events"]:
        vals += [e["change"], e["after_20d"] or 0]
    for line in result["patterns"] + result["opportunities"] + result["threats"]:
        vals += [float(m.group(1).replace(",", ".").replace("−", "-")) for m in _NUM.finditer(line)]
    vals += [float(x) for x in re.findall(r"\d+(?:\.\d+)?", " ".join(result["patterns"]))]
    return [abs(v) for v in vals]


def verify(result, ai, local_score, known) -> dict:
    """Contrôle anti-hallucination : chiffres cités, cohérence du verdict, écart avec l'analyse calculée."""
    notes, unverified, checked = [], [], 0
    texts = [ai.get("summary") or ""] + (ai.get("opportunities") or []) + (ai.get("threats") or []) + (ai.get("patterns") or [])
    for text in texts:
        for m in _NUM.finditer(text):
            n = abs(float(m.group(1).replace(",", ".").replace("−", "-")))
            checked += 1
            if not any(abs(n - k) <= max(1.0, 0.05 * k) for k in known):
                start = max(0, m.start() - 40)
                unverified.append("…" + text[start:m.end()].strip())
    expected = ("STRONG_BUY" if result["score"] >= 40 else "BUY" if result["score"] >= 15 else "HOLD"
                if result["score"] > -15 else "REDUCE" if result["score"] > -40 else "SELL")
    if abs(VERDICTS.index(expected) - VERDICTS.index(result["verdict"])) > 1:
        notes.append("verdict_score_mismatch")
    if abs(result["score"] - local_score) > 50:
        notes.append("diverges_from_local")
    status = "warning" if notes or len(unverified) > max(1, checked // 3) else "verified"
    return {"status": status, "checked": checked, "unverified": unverified[:6], "notes": notes, "local_score": local_score}


def cached_verdicts() -> dict:
    with store.connect() as conn:
        rows = conn.execute("SELECT symbol, payload FROM advice_cache ORDER BY created_at").fetchall()
    out = {}
    for r in rows:
        p = json.loads(r[1])
        out[r[0]] = {"verdict": p["verdict"], "score": p["score"], "confidence": p["confidence"],
                     "engine": p["engine"], "generated_at": p["generated_at"]}
    return out
