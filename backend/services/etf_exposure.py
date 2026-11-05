"""Ce qu'il y a dans un ETF : composition approchée des grands indices, pour mesurer la diversification réelle.
Pondérations arrondies des indices (ordre de grandeur des dernières années) : approximation, pas un relevé exact."""
import re

# secteurs au format du catalogue (classification Yahoo)
SECTORS = {"Technology": "Technology", "Information Technology": "Technology", "Financial Services": "Financial Services",
           "Financials": "Financial Services", "Finance": "Financial Services", "Health Care": "Healthcare", "Healthcare": "Healthcare",
           "Consumer Cyclical": "Consumer Cyclical", "Consumer Discretionary": "Consumer Cyclical",
           "Consumer Defensive": "Consumer Defensive", "Consumer Staples": "Consumer Defensive", "Industrials": "Industrials",
           "Communication Services": "Communication Services", "Telecommunications": "Communication Services",
           "Energy": "Energy", "Basic Materials": "Basic Materials", "Materials": "Basic Materials", "Utilities": "Utilities",
           "Real Estate": "Real Estate"}

FAMILIES = [
    (r"msci world|ftse all-world|msci acwi|world", "world",
     {"Technology": 26, "Financial Services": 16, "Healthcare": 10, "Industrials": 11, "Consumer Cyclical": 10, "Communication Services": 8,
      "Consumer Defensive": 6, "Energy": 4, "Basic Materials": 3, "Utilities": 3, "Real Estate": 3},
     {"US": 71, "JP": 5, "GB": 4, "CA": 3, "FR": 3, "CH": 2, "DE": 2, "Autres": 10}),
    (r"s&p 500|msci usa|usa|dow jones|russell", "us",
     {"Technology": 32, "Financial Services": 13, "Healthcare": 10, "Consumer Cyclical": 10, "Communication Services": 9, "Industrials": 8,
      "Consumer Defensive": 6, "Energy": 3, "Utilities": 3, "Real Estate": 2, "Basic Materials": 2, "Autres": 2},
     {"US": 100}),
    (r"nasdaq", "nasdaq",
     {"Technology": 58, "Communication Services": 15, "Consumer Cyclical": 13, "Healthcare": 6, "Consumer Defensive": 4, "Industrials": 4},
     {"US": 97, "Autres": 3}),
    (r"emerging|emergents|em ", "em",
     {"Technology": 24, "Financial Services": 23, "Consumer Cyclical": 13, "Communication Services": 9, "Basic Materials": 7,
      "Industrials": 7, "Energy": 5, "Consumer Defensive": 5, "Healthcare": 4, "Autres": 3},
     {"CN": 27, "TW": 19, "IN": 18, "KR": 10, "BR": 4, "Autres": 22}),
    (r"cac 40|cac40", "cac",
     {"Consumer Cyclical": 24, "Industrials": 22, "Healthcare": 9, "Financial Services": 10, "Energy": 7, "Consumer Defensive": 9,
      "Basic Materials": 5, "Technology": 6, "Utilities": 4, "Communication Services": 2, "Real Estate": 2},
     {"FR": 100}),
    (r"dax", "dax",
     {"Industrials": 25, "Technology": 18, "Financial Services": 18, "Consumer Cyclical": 12, "Healthcare": 7, "Basic Materials": 6,
      "Communication Services": 7, "Utilities": 4, "Autres": 3}, {"DE": 100}),
    (r"euro stoxx 50|emu|euro stoxx|eurozone|zone euro", "emu",
     {"Financial Services": 20, "Industrials": 19, "Technology": 13, "Consumer Cyclical": 15, "Healthcare": 7, "Consumer Defensive": 7,
      "Energy": 5, "Utilities": 6, "Basic Materials": 4, "Communication Services": 4},
     {"FR": 34, "DE": 29, "NL": 14, "ES": 9, "IT": 8, "Autres": 6}),
    (r"stoxx europe 600|stoxx 600|msci europe|europe", "europe",
     {"Financial Services": 19, "Industrials": 18, "Healthcare": 14, "Consumer Defensive": 9, "Technology": 8, "Consumer Cyclical": 9,
      "Basic Materials": 6, "Energy": 5, "Utilities": 5, "Communication Services": 4, "Real Estate": 1, "Autres": 2},
     {"GB": 22, "FR": 16, "CH": 14, "DE": 13, "NL": 7, "Autres": 28}),
    (r"japan|japon|topix|nikkei", "japan", {"Industrials": 23, "Consumer Cyclical": 17, "Technology": 15, "Financial Services": 14,
     "Healthcare": 7, "Communication Services": 7, "Autres": 17}, {"JP": 100}),
]
NARROW = re.compile(r"health|healthcare|banks|technology|tech|energy|real estate|epra|reit|dividend|inflation|court terme|"
                    r"gov|treasury|bond|obligations|gold|or |brazil|brésil|india|china|chine|small|mid", re.I)
LEVERAGED = re.compile(r"leveraged|\(2x\)|\(-2x\)|daily \(-?\d|inverse|short|bear|ultra|3x|2x", re.I)


def normalize_sector(sector: str | None) -> str | None:
    return SECTORS.get(sector, sector) if sector else None


def exposure(entry: dict | None) -> dict | None:
    """Exposition sectorielle et géographique approchée d'un ETF (None si inconnue : traité comme une ligne)."""
    name = ((entry or {}).get("name") or "").lower()
    if not name or (entry or {}).get("leveraged"):
        return None
    for pattern, family, sectors, countries in FAMILIES:
        if re.search(pattern, name):
            if NARROW.search(name) and family in ("world", "us", "europe", "emu"):
                return None  # ETF sectoriel / thématique : pas la composition de l'indice large
            return {"family": family, "sectors": sectors, "countries": countries}
    return None


def is_broad(entry: dict | None) -> bool:
    """ETF diversifié sur un grand indice (plusieurs centaines de sociétés) : exempt de la règle des 20 % par ligne."""
    exp = exposure(entry) if entry and entry.get("kind") == "etf" else None
    return bool(exp and exp["family"] in ("world", "us", "europe", "emu", "em", "nasdaq"))


def is_leveraged(name: str) -> bool:
    return bool(LEVERAGED.search(name or ""))
