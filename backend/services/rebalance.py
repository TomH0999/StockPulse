"""Rééquilibrage du PEA : allocation cible (conseil × confiance / volatilité, plafonds ligne et secteur),
puis ordres concrets pour s'en rapprocher (ventes d'abord, petites opérations écartées à cause des frais)."""
import math

import catalog
from services import advisor, orders, screener

MAX_LINE, MAX_SECTOR, MIN_LINES, CASH_TARGET = 0.20, 0.35, 5, 0.03
CONF = {"low": 0.5, "medium": 0.8, "high": 1.0}


def _conviction(adv: dict | None) -> float:
    """0 = sortir, 1 = neutre, jusqu'à 2 = forte conviction d'achat."""
    if not adv:
        return 0.8
    if adv["verdict"] == "SELL":
        return 0.0
    return max(0.0, 1 + adv["score"] / 100 * CONF.get(adv.get("confidence"), 0.8) * 1.5)


def _cap(weights: dict[str, float], sectors: dict[str, str], budget: float) -> dict[str, float]:
    """Normalise au budget en respectant les plafonds par ligne et par secteur (redistribution itérative)."""
    w = {s: v for s, v in weights.items() if v > 0}
    if not w:
        return w
    # Avec trop peu de lignes ou de secteurs, un plafond strict forcerait à vendre pour garder des liquidités :
    # il est alors levé (l'alerte de concentration et les idées de diversification restent affichées)
    line_cap = MAX_LINE if len(w) * MAX_LINE >= budget else 1.0
    sector_cap = MAX_SECTOR if len({sectors.get(s, "?") for s in w}) * MAX_SECTOR >= budget else 1.0
    fixed: dict[str, float] = {}  # poids figés par un plafond (répartition « par remplissage »)
    alloc: dict[str, float] = {}
    for _ in range(200):
        free = {k: v for k, v in w.items() if k not in fixed}
        remaining = budget - sum(fixed.values())
        total = sum(free.values())
        alloc = {k: v / total * remaining for k, v in free.items()} if free and total > 0 and remaining > 0 else {}
        over = [k for k, v in alloc.items() if v > line_cap + 1e-9]
        if over:
            fixed.update({k: line_cap for k in over})
            continue
        current = {**fixed, **alloc}
        by_sector: dict[str, float] = {}
        for k, v in current.items():
            by_sector[sectors.get(k, "?")] = by_sector.get(sectors.get(k, "?"), 0) + v
        violated = [sec for sec, tot in by_sector.items() if sec != "?" and tot > sector_cap + 1e-9]
        if not violated:
            return current
        for sec in violated:
            f = sector_cap / by_sector[sec]
            fixed.update({k: current[k] * f for k in current if sectors.get(k, "?") == sec})
    return {**fixed, **alloc}


def plan(summary: dict) -> dict:
    total = summary["total"]
    lines = [l for l in summary["lines"] if l.get("in_total", True) and l["price"]]
    if total <= 0:
        return {"actions": [], "target": {}, "before": {}, "after": {}}
    info = {e["symbol"]: e for e in catalog.entries()}
    snap, _ = screener.snapshot(max_age=86400)
    verdicts = advisor.cached_verdicts()
    vol = lambda s: max(10.0, (snap.get(s) or {}).get("volatility") or 30.0)  # noqa: E731
    sector = {s: (info.get(s) or {}).get("sector") or "?" for s in set(verdicts) | {l["symbol"] for l in lines}}

    held = {l["symbol"]: l for l in lines}
    raw = {s: _conviction(verdicts.get(s) or l["advice"]) / vol(s) for s, l in held.items()}
    if any((info.get(s) or {}).get("pea") is False for s in held):
        raw.update({s: 0.0 for s in held if (info.get(s) or {}).get("pea") is False})

    # Candidats : valeurs PEA actives au meilleur conseil, priorité aux secteurs absents ou sous-pondérés
    held_sectors = {sector[s] for s in held}
    cands = sorted((s for s, v in verdicts.items() if s not in held and v["score"] >= 25 and v["verdict"] in ("BUY", "STRONG_BUY")
                    and (info.get(s) or {}).get("pea") and not (info.get(s) or {}).get("status")),
                   key=lambda s: -(verdicts[s]["score"] * CONF.get(verdicts[s]["confidence"], 0.8) + (15 if sector[s] not in held_sectors else 0)))
    picked, used_sectors = [], set(held_sectors)
    kept_lines = sum(1 for v in raw.values() if v > 0)
    for s in cands:
        if kept_lines + len(picked) >= max(MIN_LINES, kept_lines + 2):
            break
        if sector[s] not in used_sectors or kept_lines + len(picked) < MIN_LINES:
            picked.append(s)
            used_sectors.add(sector[s])
    for s in picked:
        raw[s] = _conviction(verdicts[s]) / vol(s)

    target = _cap(raw, sector, 1 - CASH_TARGET)
    min_trade = max(150.0, 0.02 * total)
    prices = {s: l["price"] for s, l in held.items()}
    prices.update({s: (snap.get(s) or {}).get("price") for s in picked})

    actions = []
    for s in sorted(set(held) | set(target)):
        price = prices.get(s)
        if not price:
            continue
        current = held[s]["value"] if s in held else 0.0
        goal = target.get(s, 0.0) * total
        delta = goal - current
        if abs(delta) < min_trade and not (goal == 0 and current > 0):
            continue
        qty = math.floor(abs(delta) / price) if goal > 0 else held[s]["quantity"]
        if qty < 1:
            continue
        adv = verdicts.get(s) or (held[s]["advice"] if s in held else None)
        side = "buy" if delta > 0 else ("sell" if goal == 0 else "reduce")
        reasons = []
        if side == "sell":
            reasons.append("not_pea" if (info.get(s) or {}).get("pea") is False else "verdict_sell")
        elif side == "reduce":
            if s in held and held[s]["weight"] and held[s]["weight"] / 100 * summary["value"] / total > MAX_LINE:
                reasons.append("over_line_cap")
            if adv and adv["verdict"] in ("REDUCE", "HOLD"):
                reasons.append(f"verdict_{adv['verdict'].lower()}")
            reasons.append("rebalance_down")
        else:
            reasons.append("new_sector" if s not in held and sector[s] not in held_sectors else "new_line" if s not in held else "strong_advice")
        actions.append({"symbol": s, "name": (info.get(s) or {}).get("name", s), "side": side, "quantity": qty,
                        "amount": round(qty * price, 2), "current_weight": round(current / total * 100, 1),
                        "target_weight": round(target.get(s, 0) * 100, 1), "sector": sector.get(s), "reasons": reasons,
                        "score": adv["score"] if adv else None})

    # Ventes d'abord (elles financent les achats), puis achats dans la limite des liquidités disponibles
    actions.sort(key=lambda a: (a["side"] == "buy", -a["amount"]))
    cash = summary["cash"] + sum(a["amount"] - orders.fee(a["amount"]) for a in actions if a["side"] != "buy")
    kept = []
    for a in actions:
        if a["side"] == "buy":
            budget = cash - orders.fee(min(a["amount"], cash))
            if budget < min_trade:
                a["blocked"] = "cash"
            else:
                a["quantity"] = min(a["quantity"], math.floor(budget / prices[a["symbol"]]))
                a["amount"] = round(a["quantity"] * prices[a["symbol"]], 2)
                cash -= a["amount"] + orders.fee(a["amount"])
        kept.append(a)

    def alloc(weights):
        out = {}
        for s, w in weights.items():
            out[sector.get(s) or "?"] = round(out.get(sector.get(s) or "?", 0) + w * 100, 1)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
    before = {s: l["value"] / total for s, l in held.items()}
    return {"actions": kept, "target": {s: round(w * 100, 1) for s, w in target.items()},
            "before": alloc(before), "after": alloc(target), "cash_after": round(cash, 2)}
