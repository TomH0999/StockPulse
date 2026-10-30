"""Suggestions pour le PEA, pensées pour le long terme et sans aller-retour :
- on part du PEA tel qu'il est : aucune vente pour financer un autre achat ;
- ventes seulement pour une vraie raison (conseil « Vendre » / « Alléger » durable, plafond nettement dépassé, non éligible),
  jamais sur une ligne achetée depuis moins de 30 jours (sauf « Vendre » ou plafond) ;
- liquidités investies dans les lignes les plus convaincantes et sous leur cible, puis dans de nouvelles idées ;
- plan d'ensemble vérifié : une fois toutes les suggestions appliquées, aucune autre suggestion n'est déclenchée."""
import math
from datetime import date

import catalog
from services import advisor, fx, objectives, orders, screener

CONF = {"low": 0.5, "medium": 0.8, "high": 1.0}
MIN_LINES = 5
HOLD_DAYS = 30
TOLERANCE = 2.0  # points de pourcentage au-dessus d'un plafond avant d'alléger (évite les petits allers-retours)
SECTOR_TOLERANCE = 5.0


def conviction(adv: dict | None) -> float:
    """Conviction de long terme : conseil × confiance, corrigée par la fiabilité passée et la tendance de fond."""
    if not adv:
        return 0.8
    if adv["verdict"] == "SELL":
        return 0.0
    # pente modérée : la calibration sur 5 ans (tools/calibrate.py) ne montre pas de pouvoir prédictif stable du score
    c = 1 + adv["score"] / 100 * CONF.get(adv.get("confidence"), 0.8) * 0.8
    if adv.get("hit_6m") is not None:
        c *= 0.75 + 0.5 * min(1.0, max(0.0, adv["hit_6m"] / 100))  # conseils historiquement peu fiables : pris avec prudence
    if adv.get("cagr") is not None:
        c *= 1 + max(-0.2, min(0.2, adv["cagr"] / 100))
    return max(0.0, c)


def _cap(weights: dict[str, float], sectors: dict[str, str], budget: float, max_line: float, max_sector: float) -> dict[str, float]:
    """Répartit le budget selon les poids en respectant les plafonds (remplissage itératif)."""
    w = {s: v for s, v in weights.items() if v > 0}
    if not w:
        return {}
    line_cap = max_line if len(w) * max_line >= budget else 1.0
    sector_cap = max_sector if len({sectors.get(s, "?") for s in w}) * max_sector >= budget else 1.0
    fixed: dict[str, float] = {}
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


def _days_since(day: str | None) -> int:
    try:
        return (date.today() - date.fromisoformat(day)).days
    except (TypeError, ValueError):
        return 10_000


def plan(summary: dict) -> dict:
    obj = objectives.get()
    max_line, max_sector = obj["max_line"] / 100, obj["max_sector"] / 100
    total = summary["total"]
    if total <= 0:
        return {"actions": [], "lines": [], "target": {}, "before": {}, "after": {}, "cash_after": 0}
    held = {l["symbol"]: l for l in summary["lines"] if l["price"]}
    verdicts = advisor.cached_verdicts()
    snap, _ = screener.snapshot(max_age=86400)
    info = {s: catalog.lookup(s) for s in set(verdicts) | set(held)}
    sector = {s: (info.get(s) or {}).get("sector") or "?" for s in info}
    price_eur = {s: l["price"] * (l.get("fx") or 1.0) for s, l in held.items()}
    value = {s: l["value"] for s, l in held.items()}
    adv = {s: verdicts.get(s) or held[s]["advice"] for s in held}
    actions, line_notes = [], {}

    def act(sym, side, qty, reasons):
        amount = round(qty * price_eur[sym], 2)
        actions.append({"symbol": sym, "name": (info.get(sym) or {}).get("name") or (held.get(sym) or {}).get("name", sym), "side": side,
                        "quantity": qty, "amount": amount, "current_weight": round((held[sym]["value"] if sym in held else 0) / total * 100, 1),
                        "sector": sector.get(sym), "reasons": reasons, "score": (verdicts.get(sym) or {}).get("score")})
        value[sym] = value.get(sym, 0) + (amount if side == "buy" else -amount)

    # 1. Ventes justifiées uniquement
    for s, l in held.items():
        a = adv.get(s) or {}
        recent = _days_since(l.get("last_buy")) < HOLD_DAYS
        weight = l["value"] / total
        if (info.get(s) or {}).get("pea") is False:
            act(s, "sell", l["quantity"], ["not_pea"])
        elif a.get("verdict") == "SELL" and a.get("confidence") != "low":
            act(s, "sell", l["quantity"], ["verdict_sell"])
        elif weight > max_line + TOLERANCE / 100:
            act(s, "reduce", math.ceil((weight - max_line) * total / price_eur[s]), ["over_line_cap"])
        elif a.get("verdict") == "REDUCE" and a.get("score", 0) <= -25 and not recent:
            act(s, "reduce", max(1, math.floor(l["quantity"] / 3)), ["verdict_reduce"])
        elif recent:
            line_notes[s] = "recent"
    by_sector: dict[str, float] = {}
    for s, v in value.items():
        by_sector[sector.get(s, "?")] = by_sector.get(sector.get(s, "?"), 0) + v
    for sec, v in by_sector.items():
        if sec != "?" and v / total > max_sector + SECTOR_TOLERANCE / 100 and len(by_sector) * max_sector >= 1:
            excess = v - max_sector * total
            # on allège d'abord les lignes anciennes et les moins convaincantes ; jamais un achat récent
            for s in sorted((x for x in held if sector.get(x) == sec and value.get(x, 0) > 0
                             and _days_since(held[x].get("last_buy")) >= HOLD_DAYS), key=lambda x: conviction(adv.get(x))):
                qty = min(math.ceil(excess / price_eur[s]), math.floor(value[s] / price_eur[s]))
                if qty > 0 and not any(a["symbol"] == s for a in actions):
                    act(s, "reduce", qty, ["over_sector_cap"])
                    excess -= qty * price_eur[s]
                if excess <= 0:
                    break

    # 2. Cible de long terme (sert seulement à décider où investir les liquidités)
    etf = obj["etf_symbol"] if obj["etf_share"] > 0 else None
    budget = 1 - obj["cash_reserve"] / 100 - (obj["etf_share"] / 100 if etf else 0)
    vol = lambda s: max(10.0, (verdicts.get(s) or {}).get("volatility") or (snap.get(s) or {}).get("volatility") or 30.0)  # noqa: E731
    raw = {s: conviction(adv.get(s)) / math.sqrt(vol(s)) for s in held if value.get(s, 0) > 0 and s != etf}
    held_sectors = {sector[s] for s in raw}
    cands = sorted((s for s, v in verdicts.items() if s not in held and s != etf and v["score"] >= 25 and v["verdict"] in ("BUY", "STRONG_BUY")
                    and (info.get(s) or {}).get("pea") and not (info.get(s) or {}).get("status") and (info.get(s) or {}).get("market") != "etf"),
                   key=lambda s: -(conviction(verdicts[s]) + (0.5 if sector[s] not in held_sectors else 0)))
    picked, used = [], set(held_sectors)
    for s in cands:
        if len(raw) + len(picked) >= MIN_LINES and all(sector[c] in used for c in [s]):
            continue
        if len(raw) + len(picked) >= max(MIN_LINES, len(raw) + 2):
            break
        picked.append(s)
        used.add(sector[s])
    for s in picked:
        raw[s] = conviction(verdicts[s]) / math.sqrt(vol(s))
        price_eur[s] = fx.to_eur((snap.get(s) or {}).get("price"), (snap.get(s) or {}).get("currency")) or 0
    target = _cap(raw, sector, budget, max_line, max_sector)
    if etf:
        target[etf] = obj["etf_share"] / 100
        price_eur.setdefault(etf, fx.to_eur((snap.get(etf) or {}).get("price"), (snap.get(etf) or {}).get("currency")) or 0)
        sector.setdefault(etf, "ETF")

    # 3. Investir les liquidités disponibles (ventes comprises), sans dépasser les plafonds
    min_trade = max(150.0, 0.02 * total)
    cash = summary["cash"] + sum(a["amount"] - orders.fee(a["amount"]) for a in actions) - obj["cash_reserve"] / 100 * total
    gaps = sorted(((s, target[s] * total - value.get(s, 0)) for s in target if price_eur.get(s)), key=lambda kv: -kv[1])
    for s, gap in gaps:
        if gap < min_trade or cash < min_trade:
            continue
        sec_room = max_sector * total - sum(v for x, v in value.items() if sector.get(x) == sector.get(s))
        budget_eur = min(gap, cash - orders.fee(min(gap, cash)), max_line * total - value.get(s, 0), sec_room if s != etf else gap)
        qty = math.floor(budget_eur / price_eur[s])
        if qty < 1 or qty * price_eur[s] < min_trade:
            continue
        reason = "core_etf" if s == etf else "strong_advice" if s in held else ("new_sector" if sector[s] not in held_sectors else "new_line")
        act(s, "buy", qty, [reason])
        cash -= qty * price_eur[s] + orders.fee(qty * price_eur[s])

    # 4. Conseil ligne par ligne (cohérent avec le plan d'ensemble)
    by_symbol = {a["symbol"]: a for a in actions}
    lines = []
    for s, l in held.items():
        a, tw = by_symbol.get(s), target.get(s, 0) * 100
        if a:
            advice, reasons = a["side"], a["reasons"]
        else:
            advice = "hold"
            reasons = [line_notes.get(s) or ("near_target" if abs(l["value"] / total * 100 - tw) <= 5 else
                                             "under_target_no_cash" if l["value"] / total * 100 < tw else "above_target_ok")]
        lines.append({"symbol": s, "name": l["name"], "advice": advice, "reasons": reasons, "weight": round(l["value"] / total * 100, 1),
                      "target_weight": round(tw, 1), "quantity": a["quantity"] if a else 0, "amount": a["amount"] if a else 0,
                      "pnl_percent": l["pnl_percent"], "days_held": _days_since(l.get("since")), "verdict": (adv.get(s) or {}).get("verdict")})

    for a in actions:
        a["target_weight"] = round(value.get(a["symbol"], 0) / total * 100, 1)
    actions.sort(key=lambda a: (a["side"] == "buy", -a["amount"]))

    def alloc(values):
        out: dict[str, float] = {}
        for s, v in values.items():
            if v > 0:
                out[sector.get(s) or "?"] = round(out.get(sector.get(s) or "?", 0) + v / total * 100, 1)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
    return {"actions": actions, "lines": lines, "target": {s: round(w * 100, 1) for s, w in target.items()},
            "before": alloc({s: l["value"] for s, l in held.items()}), "after": alloc(value),
            "cash_after": round(cash + obj["cash_reserve"] / 100 * total, 2),
            "turnover": round(sum(a["amount"] for a in actions) / total * 100, 1)}
