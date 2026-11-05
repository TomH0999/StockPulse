"""Onglet News : les actualités les plus importantes d'une période et les sujets qui reviennent le plus.

Popularité (aucune source gratuite ne donne le nombre de lectures) : un sujet est important quand beaucoup de
médias différents en parlent. Les articles proches sont regroupés (mots en commun) ; chaque groupe est classé
selon le nombre de sources distinctes, avec un bonus pour la « Une » économique de Google News et pour la fraîcheur.
Les sujets récurrents sont les mots et expressions présents dans le plus de titres distincts."""
import calendar
import math
import re
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import store
from services import news

MARKET, TOP = "_MARKET", "_TOP"
REFRESH = 1800
# Google News ne renvoie qu'une vingtaine d'articles anciens par requête : on multiplie les angles
QUERIES = {"fr": ["bourse", '"CAC 40"', "BCE OR inflation", "économie", '"résultats annuels" OR "chiffre d\'affaires"', "pétrole OR énergie",
                  "rachat OR acquisition OR fusion", "Wall Street"],
           "en": ['"stock market"', '"Wall Street"', '"Federal Reserve" OR Fed', "earnings", "economy", '"oil prices"',
                  "merger OR acquisition", 'Nasdaq OR "S&P 500"']}
TOP_FEEDS = ["https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr&gl=FR&ceid=FR:fr",
             "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"]
STOP = set("""a à au aux avec ce ces cette dans de des du elle en et est il ils la le les leur leurs mais ne ou par pas plus pour qu que qui sa
se ses son sont sur un une après avant contre entre face fait faire selon sous vers comme être avoir été tout tous très deux trois
nouveau nouvelle nouvelles déjà encore aussi chez dont lors via plus moins quand comment pourquoi
the and for with from that this its are was will has have been their more than into over under after amid about says said
of to in on by at as an or be is it not new how why what who you your our over up down out off after before amid amid
vs per year years day week month today could would may might can just now""".split())
GENERIC = set("""bourse bourses marché marchés stock stocks market markets action actions share shares investisseurs investors
news update live économie economy finance financier financière france u.s sans big top best here première premier
points point inc since high global cour dollar million groupe hausse baisse prix economic économique record exclusive milliard euro rate plan but ans fall higher lower report growth entreprise sale result year journal street first quarter année service impact outlook paris""".split())
# Les mots des requêtes reviennent forcément : ils ne comptent ni comme sujet ni pour regrouper les articles
GENERIC |= {w for qs in QUERIES.values() for q in qs for w in re.findall(r"[a-zà-ÿ0-9&']+", q.lower())
            if w not in ("or",)} | {"chiffre", "affaires", "d'affaires", "oil", "prices", "s&p", "cac"}
_last: dict[str, float] = {}
_lock = threading.Lock()


def bounds(period: str, year: int | None = None, month: int | None = None, today: date | None = None) -> tuple[date, date]:
    """Dates de début et de fin (incluses) de la période demandée."""
    today = today or date.today()
    if period == "day":
        return today, today
    if period == "week":
        return today - timedelta(days=today.weekday()), today
    if period == "month":
        return today.replace(day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    if period == "custom" and year:
        if month:
            last = date(year, month, calendar.monthrange(year, month)[1])
            return date(year, month, 1), min(last, today)
        return date(year, 1, 1), min(date(year, 12, 31), today)
    raise ValueError("Période inconnue")


def _chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Découpe en tranches d'une semaine au plus (Google News renvoie 100 articles par requête)."""
    out, d = [], start
    step = 7 if (end - start).days <= 62 else 31
    while d <= end:
        e = min(d + timedelta(days=step - 1), end)
        out.append((d, e))
        d = e + timedelta(days=1)
    return out


def _due(key: str, past: bool) -> bool:
    """Une tranche passée n'est téléchargée qu'une fois ; une tranche en cours toutes les 30 min."""
    with _lock:
        if past and store.get_setting(f"news_hist:{key}"):
            return False
        if not past and time.time() - _last.get(key, 0) < REFRESH:
            return False
        _last[key] = time.time()
        return True


def _fetch(period: str, start: date, end: date):
    today = date.today()
    jobs, done = [], []
    if period in ("day", "week"):  # période en cours : « when: » renvoie jusqu'à 100 articles récents par requête
        if _due(period, False):
            when = "1d" if period == "day" else "7d"
            jobs += [(MARKET, news._google(f"{q} when:{when}", lang)) for lang, qs in QUERIES.items() for q in qs]
            jobs += [(TOP, url) for url in TOP_FEEDS]
    else:
        for a, b in _chunks(start, end):
            past = b < today
            if _due(f"{a}:{b}", past):
                jobs += [(MARKET, news._google(f"{q} after:{a} before:{b + timedelta(days=1)}", lang)) for lang, qs in QUERIES.items() for q in qs]
                if past:
                    done.append(f"{a}:{b}")

    def run(job):
        try:
            return job[0], news._rss(job[1], True)
        except Exception as e:
            print(f"News marché : {e}")
            return job[0], []
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(run, jobs))
    by_sym = defaultdict(list)
    for sym, items in results:
        by_sym[sym] += items
    for sym, items in by_sym.items():
        news._save(sym, items)
    for key in done:
        store.set_setting(f"news_hist:{key}", str(int(time.time())))


JUNK = re.compile(r"cours action|cotation bourse|stock price|share price today|earnings call (is live|highlights|transcript)", re.I)


def _stem(w: str) -> str:
    w = re.sub(r"^(l|d|qu|n|s|j|c)['’]", "", w)
    return w[:-1] if len(w) > 4 and w.endswith("s") and w[-2] not in "sèéuiï" else w


def _words(title: str) -> list[str]:
    ws = (_stem(w) for w in re.findall(r"[a-zà-ÿ0-9][a-zà-ÿ0-9'’&.-]*[a-zà-ÿ0-9]|[a-zà-ÿ0-9]", title.lower()))
    return [w for w in ws if len(w) > 2 and w not in STOP and not w.isdigit()]


STOP |= {_stem(w) for w in STOP}
GENERIC |= {_stem(w) for w in GENERIC}


def topics(articles: list[dict], top: int = 15) -> list[dict]:
    df, sources = Counter(), defaultdict(set)
    for a in articles:
        ws = _words(a["headline"])
        terms = {w for w in ws if w not in GENERIC} | {f"{x} {y}" for x, y in zip(ws, ws[1:]) if x not in GENERIC or y not in GENERIC}
        for t in terms:
            df[t] += 1
            sources[t].add(a["source"])
    scored = sorted(((n * math.log(1 + len(sources[t])), t) for t, n in df.items() if n >= 2), reverse=True)
    out, chosen = [], []
    for _, t in scored:
        if any(t in c.split() or (t.count(" ") and set(t.split()) <= set(c.split())) for c in chosen):
            continue
        # un mot seul déjà couvert par une expression aussi fréquente est redondant
        if " " not in t and any(t in c.split() and df[c] >= 0.7 * df[t] for c in chosen):
            continue
        if " " in t:
            for c in list(chosen):
                if " " not in c and c in t.split() and df[t] >= 0.7 * df[c]:
                    chosen.remove(c)
                    out = [o for o in out if o["term"] != c]
        chosen.append(t)
        out.append({"term": t, "count": df[t], "sources": len(sources[t]), "share": round(df[t] / max(1, len(articles)) * 100, 1)})
        if len(out) >= top:
            break
    return out


def stories(articles: list[dict], end_ts: float, top: int = 30) -> list[dict]:
    clusters, index = [], defaultdict(set)
    for a in sorted(articles, key=lambda a: a["timestamp"]):
        ws = set(_words(a["headline"])) - GENERIC
        if not ws:
            continue
        cand = set().union(*(index[w] for w in ws))
        best, sim = None, 0.0
        for ci in cand:
            c = clusters[ci]
            s = len(ws & c["core"]) / len(ws | c["core"])
            if s > sim:
                best, sim = ci, s
        if best is not None and sim >= 0.3:
            c = clusters[best]
        else:
            c = {"core": ws, "items": []}
            clusters.append(c)
            best = len(clusters) - 1
        c["items"].append(a)
        for w in ws:
            index[w].add(best)
    out = []
    for c in clusters:
        items = c["items"]
        srcs = {i["source"] for i in items}
        lead = max(items, key=lambda i: (i["symbol"] == TOP, i["timestamp"]))
        last = max(i["timestamp"] for i in items)
        fresh = math.exp(-max(0, end_ts - last) / (3 * 86400))
        score = len(srcs) + 0.1 * min(len(items) - len(srcs), 10) + (1 if any(i["symbol"] == TOP for i in items) else 0) + fresh
        sents = [i["sentiment_score"] for i in items if i.get("sentiment_score") is not None]
        out.append({"headline": lead["headline"], "url": lead["url"], "source": lead["source"], "timestamp": last,
                    "first_seen": min(i["timestamp"] for i in items), "count": len(items), "sources": sorted(srcs)[:6],
                    "source_count": len(srcs), "headline_page": any(i["symbol"] == TOP for i in items),
                    "symbols": sorted({i["symbol"] for i in items if not i["symbol"].startswith("_")})[:6],
                    "sentiment": round(sum(sents) / len(sents), 2) if sents else 0.0, "score": round(score, 2),
                    "related": [{"headline": i["headline"], "url": i["url"], "source": i["source"], "timestamp": i["timestamp"]}
                                for i in sorted(items, key=lambda i: -i["timestamp"]) if i is not lead][:5]})
    out.sort(key=lambda s: -s["score"])
    return out[:top]


def report(period: str = "day", year: int | None = None, month: int | None = None, fetch: bool = True) -> dict:
    start, end = bounds(period, year, month)
    if fetch:
        _fetch(period, start, end)
    t0 = datetime.combine(start, datetime.min.time()).timestamp()
    t1 = datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp()
    if period == "day":  # le jour même : on inclut les dernières 24 h pour ne pas être vide le matin
        t0 = min(t0, time.time() - 86400)
    with store.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT symbol, headline, url, source, timestamp, sentiment_score FROM articles WHERE timestamp >= ? AND timestamp < ?",
            (t0, t1))]
    seen, arts = set(), []
    for r in sorted(rows, key=lambda r: r["symbol"] != TOP):  # en cas de doublon on garde la version « Une »
        k = news._norm(r["headline"])
        if k and k not in seen and not JUNK.search(r["headline"]):
            seen.add(k)
            arts.append(r)
    return {"period": period, "start": start.isoformat(), "end": end.isoformat(), "articles": len(arts),
            "sources": len({a["source"] for a in arts}), "topics": topics(arts), "stories": stories(arts, min(t1, time.time()))}
