"""Tests rapides lancés par la CI (Windows) avant de construire l'installateur."""
import os
import sys
import tempfile

os.environ["STOCKPULSE_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import catalog  # noqa: E402
import store  # noqa: E402
from services import advisor, sentiment  # noqa: E402

store.init()
store.set_secret("t", "secret-value")
raw = store.get_setting("t")
assert store.get_secret("t") == "secret-value"
if sys.platform == "win32":
    assert raw.startswith("dpapi:") and "secret-value" not in raw, raw
assert len(catalog.entries()) > 2000 and len(catalog.core_symbols()) > 500
assert sentiment.label(sentiment.score("Shares plunge after earnings miss")) == "Bearish"
assert sentiment.label(sentiment.score("Stock soars to record high after upgrade")) == "Bullish"
hist = [{"close": 100 + i * 0.1, "ts": 1_600_000_000 + i * 86400, "timestamp": "2020-09-13"} for i in range(400)]
assert advisor.technicals(hist)["sma200"] is not None
print("OK")
