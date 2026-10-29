"""Analyse de sentiment financière par lexique pondéré (anglais + français), utilisée sans clé IA."""
import re

_LEXICON = {
    # haussier
    "beat": 2, "beats": 2, "tops": 2, "surge": 2, "surges": 2, "soar": 2, "soars": 2, "jump": 1.5, "jumps": 1.5,
    "rally": 1.5, "rallies": 1.5, "record": 1, "upgrade": 2.5, "upgraded": 2.5, "outperform": 2, "overweight": 1.5,
    "raises": 1.5, "raised": 1, "boost": 1, "boosts": 1, "growth": 1, "profit": 1, "profitable": 1.5, "strong": 1,
    "gain": 1, "gains": 1, "rise": 1, "rises": 1, "climb": 1, "climbs": 1, "buyback": 2, "dividend": 1,
    "breakthrough": 2, "approval": 2, "approved": 2, "partnership": 1, "wins": 1.5, "win": 1, "bullish": 2,
    "buy": 1, "optimistic": 1.5, "rebound": 1.5, "recovers": 1.5, "expands": 1, "launch": 0.5, "exceeds": 2,
    "hausse": 1.5, "bondit": 2, "grimpe": 1.5, "progresse": 1, "relève": 1.5, "rachat": 1.5, "record": 1,
    "acheter": 1, "surperformance": 2, "croissance": 1, "bénéfice": 1, "dépasse": 1.5, "rebond": 1.5,
    # baissier
    "miss": -2, "misses": -2, "plunge": -2.5, "plunges": -2.5, "tumble": -2, "tumbles": -2, "slump": -2, "slumps": -2,
    "drop": -1.5, "drops": -1.5, "fall": -1.5, "falls": -1.5, "sink": -1.5, "sinks": -1.5, "crash": -3,
    "downgrade": -2.5, "downgraded": -2.5, "underperform": -2, "underweight": -1.5, "cut": -1.5, "cuts": -1.5,
    "lowers": -1.5, "weak": -1.5, "loss": -1.5, "losses": -1.5, "lawsuit": -2, "sued": -2, "probe": -1.5,
    "investigation": -1.5, "recall": -2, "fraud": -3, "layoffs": -1, "warning": -1.5, "warns": -2,
    "bearish": -2, "sell": -1, "decline": -1.5, "declines": -1.5, "fine": -1, "fined": -2, "antitrust": -1.5,
    "bankruptcy": -3, "default": -2, "slowdown": -1.5, "concerns": -1, "fears": -1.5, "risk": -0.5, "tariffs": -1,
    "baisse": -1.5, "chute": -2, "plonge": -2.5, "recule": -1.5, "dégringole": -2.5, "avertissement": -2,
    "perte": -1.5, "pertes": -1.5, "enquête": -1.5, "amende": -2, "licenciements": -1, "abaisse": -1.5, "vendre": -1,
}
_PHRASES = {
    "price target raised": 2, "raises guidance": 2.5, "raised guidance": 2.5, "all-time high": 1.5, "beats estimates": 2.5,
    "better than expected": 2, "price target cut": -2, "cuts guidance": -2.5, "lowers guidance": -2.5,
    "worse than expected": -2, "misses estimates": -2.5, "52-week low": -1.5, "objectif relevé": 2, "objectif abaissé": -2,
}
_NEGATIONS = {"not", "no", "never", "fails", "failed", "without", "ne", "pas", "sans"}
_WORD = re.compile(r"[a-zàâçéèêëîïôûùüÿ'-]+")


def score(text: str) -> float:
    """Score entre -1 (très négatif) et 1 (très positif)."""
    t = (text or "").lower()
    total = sum(w for p, w in _PHRASES.items() if p in t)
    words = _WORD.findall(t)
    for i, w in enumerate(words):
        val = _LEXICON.get(w)
        if val:
            if any(n in _NEGATIONS for n in words[max(0, i - 3):i]):
                val = -val * 0.7
            total += val
    return max(-1.0, min(1.0, total / 4))


def label(s: float) -> str:
    return "Bullish" if s >= 0.15 else "Bearish" if s <= -0.15 else "Neutral"
