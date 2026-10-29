import pytest

import store
from services import news, sentiment


@pytest.mark.parametrize("text,label", [
    ("Shares surge after earnings beat and price target raised", "Bullish"),
    ("Analyst upgrade sends stock to record high", "Bullish"),
    ("L'action bondit après des résultats records", "Bullish"),
    ("Stock plunges as company cuts guidance", "Bearish"),
    ("Lawsuit and SEC probe weigh on shares", "Bearish"),
    ("Le titre chute après un avertissement sur les résultats", "Bearish"),
    ("Company to hold annual meeting on Tuesday", "Neutral"),
    ("", "Neutral"),
])
def test_labels(text, label):
    assert sentiment.label(sentiment.score(text)) == label


def test_negation_and_bounds():
    assert sentiment.score("Shares did not surge") < sentiment.score("Shares surge")
    assert -1 <= sentiment.score("crash crash crash fraud bankruptcy plunge") <= 1
    assert -1 <= sentiment.score("surge soar beat record upgrade rally") <= 1


def test_cleaning_helpers():
    assert news._clean("<b>A&amp;B</b>   C") == "A&B C"
    assert news._norm("Apple, Inc.!") == "appleinc"
    assert news._company_query("LVMH Moët Hennessy, Société Européenne") == "LVMH Moët Hennessy"
    assert news._company_query("Apple Inc.") == "Apple"


GOOGLE_RSS = b"""<rss><channel>
<item><title>Apple beats estimates - Reuters</title><link>https://x/1</link><pubDate>Wed, 28 Oct 2026 19:07:00 GMT</pubDate>
<description>&lt;a href="x"&gt;Apple beats estimates&lt;/a&gt;</description><source>Reuters</source></item>
<item><title>No date item - Foo</title><link>https://x/2</link></item>
</channel></rss>"""


def test_rss_parsing_and_save(monkeypatch):
    class R:
        ok, content = True, GOOGLE_RSS
    monkeypatch.setattr(news._session, "get", lambda *a, **k: R())
    items = news._rss("https://news.google.com/rss", google=True)
    assert len(items) == 1 and items[0]["headline"] == "Apple beats estimates" and items[0]["source"] == "Reuters"
    assert items[0]["summary"] == ""
    assert news._save("AAPL", items) == 1
    assert news._save("AAPL", items + [{**items[0], "url": "https://other"}]) == 0  # doublon (même titre)
    arts = news.articles("AAPL")
    assert arts[0]["sentiment"] == "Bullish" and arts[0]["sentiment_score"] > 0


def test_migrate_cleans_old_rows():
    with store.connect() as conn:
        conn.execute("INSERT INTO articles (symbol, headline, summary, url, source, timestamp, sentiment) VALUES "
                     "('X', 'Stock plunges - Reuters', '<p>Stock plunges</p>', 'u', 'Reuters', 1, 'Neutral')")
    news.migrate()
    a = news.articles("X")[0]
    assert a["headline"] == "Stock plunges" and a["summary"] == "" and a["sentiment"] == "Bearish"
