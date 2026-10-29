import html
import re
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import store
from services import sentiment
from services.yahoo import _session

REFRESH_SECONDS = 600
_last_fetch: dict[str, float] = {}
_backfill_running: set[str] = set()
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text or ""))).strip()


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())[:120]


def _company_query(name: str) -> str:
    name = re.sub(r",.*$", "", name or "")
    name = re.sub(r"\b(Inc|Corp|Corporation|Company|Co|Ltd|plc|S\.?A|SE|N\.?V|AG|Holdings?|Group|Class [A-Z])\b\.?", "", name, flags=re.I)
    return name.strip(" .-") or ""


def _yahoo_search(sym: str) -> list[dict]:
    res = _session.get("https://query1.finance.yahoo.com/v1/finance/search",
                       params={"q": sym, "quotesCount": 0, "newsCount": 50}, timeout=8)
    out = []
    for n in res.json().get("news", []) if res.ok else []:
        if n.get("providerPublishTime") and n.get("title"):
            out.append({"headline": n["title"], "summary": "", "url": n.get("link", ""),
                        "source": n.get("publisher", "Yahoo Finance"), "ts": int(n["providerPublishTime"])})
    return out


def _rss(url: str, google: bool) -> list[dict]:
    res = _session.get(url, timeout=10)
    if not res.ok:
        return []
    out = []
    for item in ET.fromstring(res.content).findall(".//item"):
        title = _clean(item.findtext("title"))
        source = _clean(item.findtext("source")) or ("Google News" if google else "Yahoo Finance")
        if google and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        summary = _clean(item.findtext("description"))
        if google or _norm(summary).startswith(_norm(title)[:40]):
            summary = ""  # Google ne fournit que le titre répété
        try:
            ts = int(parsedate_to_datetime(item.findtext("pubDate")).timestamp())
        except Exception:
            continue
        if title:
            out.append({"headline": title, "summary": summary, "url": item.findtext("link") or "", "source": source, "ts": ts})
    return out


def _google(query: str, lang: str = "en") -> str:
    region = {"en": "hl=en-US&gl=US&ceid=US:en", "fr": "hl=fr&gl=FR&ceid=FR:fr"}[lang]
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&{region}"


def _save(sym: str, items: list[dict]) -> int:
    added = 0
    with store.connect() as conn:
        seen = {_norm(r[0]) for r in conn.execute("SELECT headline FROM articles WHERE symbol = ?", (sym,))}
        for it in items:
            key = _norm(it["headline"])
            if not key or key in seen:
                continue
            s = sentiment.score(f"{it['headline']}. {it['summary']}")
            cur = conn.execute(
                "INSERT OR IGNORE INTO articles (symbol, headline, summary, url, source, published_at, timestamp, sentiment, sentiment_score) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sym, it["headline"], it["summary"], it["url"], it["source"],
                 datetime.fromtimestamp(it["ts"], timezone.utc).strftime("%Y-%m-%d %H:%M"), it["ts"], sentiment.label(s), s))
            if cur.rowcount:
                seen.add(key)
                added += 1
    return added


def refresh(sym: str, company: str = "", force: bool = False):
    """Récupère les nouveaux articles (au plus toutes les 10 min par action)."""
    sym = sym.upper()
    if not force and time.time() - _last_fetch.get(sym, 0) < REFRESH_SECONDS:
        return
    _last_fetch[sym] = time.time()
    name = _company_query(company)
    base = sym.split(".")[0]
    jobs = [
        lambda: _yahoo_search(sym),
        lambda: _rss(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US", False),
        lambda: _rss(_google(f"{base} stock"), True),
    ]
    if name:
        jobs += [lambda: _rss(_google(f'"{name}" stock'), True),
                 lambda: _rss(_google(f'"{name}" bourse', "fr"), True)]
    items = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for fut in [pool.submit(j) for j in jobs]:
            try:
                items += fut.result()
            except Exception as e:
                print(f"Source d'articles en erreur pour {sym}: {e}")
    _save(sym, items)
    _start_backfill(sym, name or base)


def _start_backfill(sym: str, name: str):
    """Constitue en arrière-plan une archive sur 24 mois (une requête Google News par mois)."""
    if store.get_setting(f"backfill:{sym}") or sym in _backfill_running:
        return
    _backfill_running.add(sym)

    def run():
        try:
            end = date.today()
            for _ in range(24):
                start = (end.replace(day=1) - timedelta(days=1)).replace(day=1) if end.day == 1 else end.replace(day=1)
                q = f'"{name}" stock after:{start.isoformat()} before:{end.isoformat()}'
                try:
                    _save(sym, _rss(_google(q), True))
                except Exception as e:
                    print(f"Archive {sym} {start}: {e}")
                end = start
                time.sleep(1.5)
            store.set_setting(f"backfill:{sym}", str(int(time.time())))
        finally:
            _backfill_running.discard(sym)

    threading.Thread(target=run, daemon=True).start()


def is_backfilling(sym: str) -> bool:
    return sym.upper() in _backfill_running


def articles(sym: str, since_ts: int = 0) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id, headline, summary, url, source, timestamp, sentiment, sentiment_score, ai_sentiment "
            "FROM articles WHERE symbol = ? AND timestamp >= ? ORDER BY timestamp DESC", (sym.upper(), since_ts)).fetchall()
    return [dict(r) for r in rows]


def migrate():
    """Nettoie les articles enregistrés par les versions précédentes (HTML, sentiment manquant)."""
    with store.connect() as conn:
        rows = conn.execute("SELECT id, headline, summary, source FROM articles WHERE sentiment_score IS NULL").fetchall()
        for r in rows:
            title, summary = _clean(r["headline"]), _clean(r["summary"])
            if r["source"] and title.endswith(" - " + r["source"]):
                title = title[: -len(r["source"]) - 3]
            if _norm(summary).startswith(_norm(title)[:40]):
                summary = ""
            s = sentiment.score(f"{title}. {summary}")
            conn.execute("UPDATE articles SET headline = ?, summary = ?, sentiment = ?, sentiment_score = ? WHERE id = ?",
                         (title, summary, sentiment.label(s), s, r["id"]))
