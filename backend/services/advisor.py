"""Conseil d'investissement : analyse technique, rebondissements historiques, actualités, puis IA (si clé configurée)."""
import bisect
import json
import math
import os
import sys
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone

import catalog
import store
from services import events as newsevents  # événements d'actualité (≠ events() : chocs de cours)
from services import ai_pool, ai_store, financials, fundamentals, insights, news, portfolio, yahoo

CACHE_SECONDS = 3600
VERDICTS = ["SELL", "REDUCE", "HOLD", "BUY", "STRONG_BUY"]

T = {
    "fr": {
        "above200": "Cours au-dessus de sa moyenne 200 jours : tendance de fond haussière.",
        "below200": "Cours sous sa moyenne 200 jours : tendance de fond baissière.",
        "fcf_high": "Rendement du free cash-flow élevé : {v:.1f} % de la capitalisation par an.",
        "fcf_low": "Rendement du free cash-flow faible : {v:.1f} %.",
        "fcf_neg": "Free cash-flow négatif : l'entreprise consomme de la trésorerie.",
        "pe_cheap": "PER de {pe:.0f}, sous sa médiane des derniers exercices ({m:.0f}) : valorisation inférieure à son historique.",
        "pe_rich": "PER de {pe:.0f}, au-dessus de sa médiane des derniers exercices ({m:.0f}) : valorisation supérieure à son historique.",
        "pe_loss": "Entreprise déficitaire sur le dernier exercice.",
        "ev_low": "VE / EBIT de {v:.0f} : valorisation modérée au regard des résultats.",
        "ev_high": "VE / EBIT de {v:.0f} : valorisation exigeante.",
        "fin_cheap": "PER de {pe:.0f} pour une rentabilité des fonds propres de {roe:.0f} % : valorisation modérée.",
        "debt_low": "Bilan solide : dette nette / EBITDA de {v:.1f}.",
        "net_cash": "Trésorerie supérieure à la dette (trésorerie nette) : bilan très solide.",
        "pe_norm_cheap": "Secteur cyclique : PER de {v:.0f} sur le bénéfice moyen des derniers exercices (et non le dernier) : valorisation modérée.",
        "pe_norm_rich": "Secteur cyclique : PER de {v:.0f} sur le bénéfice moyen des derniers exercices : valorisation exigeante.",
        "value_trap": "Valorisation basse ignorée : cours sous sa moyenne 200 jours et bénéfices en baisse (risque de piège à valeur).",
        "eps_declining": "Bénéfice par action en baisse {n} années de suite.",
        "roic_declining": "Rentabilité du capital (ROIC) en baisse {n} années de suite.",
        "thesis_broken": "Thèse fragilisée ({n} signal(s) : ROIC ou bénéfices en baisse continue, dette excessive, dilution qui s'accélère) : pas d'achat, envisager d'alléger.",
        "mom_rel_up": "Fait mieux que le MSCI World de {v:+.0f} points sur 12 mois (hors dernier mois).",
        "mom_rel_dn": "Fait moins bien que le MSCI World de {a:.0f} points sur 12 mois (hors dernier mois).",
        "debt_high": "Endettement élevé : dette nette / EBITDA de {v:.1f}.",
        "cover_low": "Couverture des intérêts faible ({v:.1f} fois).",
        "growth_up": "Chiffre d'affaires en croissance de {v:+.1f} % par an sur {n} exercices.",
        "growth_dn": "Chiffre d'affaires en recul de {v:+.1f} % par an sur {n} exercices.",
        "eps_up": "Bénéfice par action en hausse de {v:+.1f} % par an.",
        "eps_dn": "Bénéfice par action en baisse de {v:+.1f} % par an.",
        "roic_high": "Rentabilité du capital investi (ROIC) de {v:.0f} % en moyenne : avantage concurrentiel probable.",
        "roic_low": "Rentabilité du capital investi (ROIC) faible : {v:.0f} % en moyenne.",
        "roe_high": "Rentabilité des fonds propres de {v:.0f} % en moyenne.",
        "roe_low": "Rentabilité des fonds propres faible : {v:.0f} % en moyenne.",
        "margin_stable": "Marges très régulières (écart-type de {v:.1f} point).",
        "margin_volatile": "Marges irrégulières (écart-type de {v:.1f} points) : activité cyclique.",
        "dilution": "Dilution des actionnaires : {v:+.1f} % d'actions par an.",
        "buyback": "Rachats d'actions : le nombre d'actions baisse de {v:.1f} % par an.",
        "fcf_irregular": "Free cash-flow négatif {n} année(s) sur {t}.",
        "div_streak": "Dividende sans baisse depuis {n} ans.",
        "div_growth": "Dividende en hausse de {v:+.1f} % par an sur 5 ans.",
        "payout_high": "Taux de distribution élevé ({v:.0f} % du bénéfice) : marge de sécurité réduite pour le dividende.",
        "cagr": "Rendement total (dividendes réinvestis) de {c:+.1f} % par an sur {y} ans, pire baisse {dd:.0f} %.",
        "news_info": "Actualités récentes (information, hors score) : {pos} favorables, {neg} défavorables sur 30 jours.",
        "no_fin": "Comptes de l'entreprise indisponibles : conseil limité à la tendance de fond.",
        "etf": "ETF : pas de verdict d'achat ou de vente ; jugez-le sur ses frais, sa diversification et sa place dans votre allocation.",
        "leveraged": "ETF à effet de levier : conçu pour le court terme, il perd de la valeur avec la volatilité (dérive). Déconseillé sur le long terme.",
        "summary": "{name} : verdict « {v} » (score {s:+d}/100). {lead}",
        "pros": "Points forts : {x}", "cons": "Points de vigilance : {x}",
        "v": {"STRONG_BUY": "Achat fort", "BUY": "Achat", "HOLD": "Conserver", "REDUCE": "Alléger", "SELL": "Vendre"},
    },
    "en": {
        "above200": "Price above its 200-day average: long-term uptrend.",
        "below200": "Price below its 200-day average: long-term downtrend.",
        "fcf_high": "High free cash-flow yield: {v:.1f}% of market cap per year.",
        "fcf_low": "Low free cash-flow yield: {v:.1f}%.",
        "fcf_neg": "Negative free cash-flow: the company burns cash.",
        "pe_cheap": "P/E of {pe:.0f}, below its median of past years ({m:.0f}): cheaper than its own history.",
        "pe_rich": "P/E of {pe:.0f}, above its median of past years ({m:.0f}): pricier than its own history.",
        "pe_loss": "Loss-making in the last fiscal year.",
        "ev_low": "EV / EBIT of {v:.0f}: moderate valuation.",
        "ev_high": "EV / EBIT of {v:.0f}: demanding valuation.",
        "fin_cheap": "P/E of {pe:.0f} for a {roe:.0f}% return on equity: moderate valuation.",
        "debt_low": "Strong balance sheet: net debt / EBITDA of {v:.1f}.",
        "net_cash": "More cash than debt (net cash): very strong balance sheet.",
        "pe_norm_cheap": "Cyclical sector: P/E of {v:.0f} on average earnings of recent years (not the last one): moderate valuation.",
        "pe_norm_rich": "Cyclical sector: P/E of {v:.0f} on average earnings of recent years: demanding valuation.",
        "value_trap": "Low valuation ignored: price below its 200-day average and falling earnings (value-trap risk).",
        "eps_declining": "EPS down {n} years in a row.",
        "roic_declining": "Return on invested capital (ROIC) down {n} years in a row.",
        "thesis_broken": "Weakened thesis ({n} signal(s): steadily falling ROIC or earnings, excessive debt, accelerating dilution): no buy, consider trimming.",
        "mom_rel_up": "Beat the MSCI World by {v:+.0f} points over 12 months (excluding the last month).",
        "mom_rel_dn": "Lagged the MSCI World by {a:.0f} points over 12 months (excluding the last month).",
        "debt_high": "High leverage: net debt / EBITDA of {v:.1f}.",
        "cover_low": "Weak interest coverage ({v:.1f}x).",
        "growth_up": "Revenue growing {v:+.1f}% a year over {n} years.",
        "growth_dn": "Revenue shrinking {v:+.1f}% a year over {n} years.",
        "eps_up": "EPS growing {v:+.1f}% a year.",
        "eps_dn": "EPS falling {v:+.1f}% a year.",
        "roic_high": "Return on invested capital (ROIC) of {v:.0f}% on average: likely competitive advantage.",
        "roic_low": "Low return on invested capital (ROIC): {v:.0f}% on average.",
        "roe_high": "Return on equity of {v:.0f}% on average.",
        "roe_low": "Low return on equity: {v:.0f}% on average.",
        "margin_stable": "Very stable margins (std dev {v:.1f} pt).",
        "margin_volatile": "Volatile margins (std dev {v:.1f} pts): cyclical business.",
        "dilution": "Shareholder dilution: {v:+.1f}% more shares a year.",
        "buyback": "Buybacks: share count falling {v:.1f}% a year.",
        "fcf_irregular": "Negative free cash-flow in {n} of {t} years.",
        "div_streak": "Dividend not cut for {n} years.",
        "div_growth": "Dividend growing {v:+.1f}% a year over 5 years.",
        "payout_high": "High payout ratio ({v:.0f}% of earnings): thin safety margin for the dividend.",
        "cagr": "Total return (dividends reinvested) of {c:+.1f}% a year over {y} years, worst drawdown {dd:.0f}%.",
        "news_info": "Recent news (information only, not scored): {pos} favourable, {neg} unfavourable over 30 days.",
        "no_fin": "Company accounts unavailable: advice limited to the long-term trend.",
        "etf": "ETF: no buy or sell verdict; judge it on fees, diversification and its role in your allocation.",
        "leveraged": "Leveraged ETF: built for short-term trading, it loses value with volatility (decay). Not suited to long-term investing.",
        "summary": "{name}: “{v}” (score {s:+d}/100). {lead}",
        "pros": "Strengths: {x}", "cons": "Watch-outs: {x}",
        "v": {"STRONG_BUY": "Strong buy", "BUY": "Buy", "HOLD": "Hold", "REDUCE": "Reduce", "SELL": "Sell"},
    },
}
LANG_NAMES = {"fr": "French", "en": "English"}
# Pondération long terme (points maximum) : 48 fondamentaux et valorisation (valorisation 18, bilan 15, croissance 15),
# 25 qualité et régularité, 27 tendance (moyenne 200 jours 15, force relative 12 mois hors dernier mois 12).
# Mesures en coupe transversale (tools/validate.py) : la tendance et le momentum 12-1 sont les signaux qui ont le plus
# aidé ; une valorisation basse seule a acheté des entreprises en déclin (garde-fou « valeur + tendance »).
GROUPS = {"valuation": 18, "momentum": 12, "strength": 15, "growth": 15, "quality": 25, "trend": 15}

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
    a = [p.get("adj") or p["close"] for p in hist]  # dividendes réinvestis
    year = c[-252:]
    hi, lo = max(year), min(year)
    sma50, sma200 = _sma(c, 50), _sma(c, 200)
    prev50 = sum(c[-70:-20]) / 50 if len(c) >= 220 else None
    prev200 = sum(c[-220:-20]) / 200 if len(c) >= 220 else None
    rets = [b / a - 1 for a, b in zip(c[:-1], c[1:]) if a]
    peak, mdd = a[0], 0.0
    for x in a:
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
        "cagr": ((a[-1] / a[0]) ** (1 / years) - 1) * 100 if years >= 1 and a[0] > 0 else None,
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


def _verdict(score: int) -> str:
    """Seuils sélectifs : un « Achat » demande des fondamentaux nettement favorables, pas seulement une bonne tendance."""
    return "STRONG_BUY" if score >= 50 else "BUY" if score >= 25 else "HOLD" if score > -20 else "REDUCE" if score > -45 else "SELL"


def _clamp(v, m):
    return max(-m, min(m, v))


def score_financials(m: dict | None, L: dict, opp: list, thr: list, pat: list, trend_up: bool | None = None) -> tuple[dict, list]:
    """Points par groupe (valorisation, solidité, croissance, qualité) et signaux de thèse cassée (verdict « Alléger »).
    Garde-fou « valeur + tendance » : une valorisation basse ne rapporte des points que si le cours est au-dessus de sa
    moyenne 200 jours ou si le bénéfice par action ne baisse pas (sinon c'est le piège classique : PER bas au sommet du cycle
    ou d'une entreprise qui décline). Secteurs cycliques : PER et free cash-flow moyens des exercices disponibles."""
    parts, broken = {}, []
    if not m or not m.get("years"):
        return parts, broken
    fin = m.get("financial_sector")
    run = 3 if m.get("cyclical") else 2  # dans un secteur cyclique, deux années de baisse sont le cycle, pas une thèse cassée
    eps_falling = (m.get("eps_change") is not None and m["eps_change"] < -10) or m.get("eps_declines", 0) >= 2
    value_ok = trend_up is True or not eps_falling
    cyc = m.get("cyclical")
    fcf_y = m.get("fcf_yield_normalized") if cyc and m.get("fcf_yield_normalized") is not None else m.get("fcf_yield")
    v, neg = 0.0, 0.0  # points positifs (soumis au garde-fou) et négatifs (toujours comptés)
    seen = False
    if not fin and fcf_y is not None and m.get("free_cash_flow") is not None:
        seen = True
        if fcf_y < 0:
            neg -= 8; thr.append(L["fcf_neg"])
        elif fcf_y >= 6:
            v += 8; opp.append(L["fcf_high"].format(v=fcf_y))
        elif fcf_y >= 4:
            v += 4; opp.append(L["fcf_high"].format(v=fcf_y))
        elif fcf_y < 2:
            neg -= 4; thr.append(L["fcf_low"].format(v=fcf_y))
    if m.get("pe_loss"):
        seen = True
        neg -= 8; thr.append(L["pe_loss"])
    elif cyc and m.get("pe_normalized"):
        seen = True
        pn = m["pe_normalized"]
        if pn < 10:
            v += 6; opp.append(L["pe_norm_cheap"].format(v=pn))
        elif pn > 25:
            neg -= 6; thr.append(L["pe_norm_rich"].format(v=pn))
    elif m.get("pe") and m.get("pe_history_median"):
        seen = True
        r = m["pe"] / m["pe_history_median"]
        if r < 0.8:
            v += 6; opp.append(L["pe_cheap"].format(pe=m["pe"], m=m["pe_history_median"]))
        elif r < 0.95:
            v += 3; opp.append(L["pe_cheap"].format(pe=m["pe"], m=m["pe_history_median"]))
        elif r > 1.25:
            neg -= 6; thr.append(L["pe_rich"].format(pe=m["pe"], m=m["pe_history_median"]))
        elif r > 1.05:
            neg -= 3; thr.append(L["pe_rich"].format(pe=m["pe"], m=m["pe_history_median"]))
    if m.get("ev_ebit") and not cyc:
        seen = True
        e = m["ev_ebit"]
        if e < 10:
            v += 4; opp.append(L["ev_low"].format(v=e))
        elif e > 25:
            neg -= 4; thr.append(L["ev_high"].format(v=e))
    if fin and m.get("pe") and m.get("roe_avg") is not None and m["pe"] < 10 and m["roe_avg"] >= 10:
        seen = True  # banque / assurance : PER bas avec une rentabilité des fonds propres correcte
        v += 6; opp.append(L["fin_cheap"].format(pe=m["pe"], roe=m["roe_avg"]))
    if seen:
        if v > 0 and not value_ok:
            thr.append(L["value_trap"])
            v = 0.0
        parts["valuation"] = _clamp(v + neg, GROUPS["valuation"])

    if not fin and (m.get("net_debt_ebitda") is not None or m.get("interest_coverage") is not None):
        st = 0.0
        d = m.get("net_debt_ebitda")
        if d is not None:
            if d < 0:
                st += 8; opp.append(L["net_cash"])
            elif d < 1:
                st += 8; opp.append(L["debt_low"].format(v=d))
            elif d < 2.5:
                st += 3
            elif d < 4:
                st -= 5; thr.append(L["debt_high"].format(v=d))
            else:
                st -= 10; thr.append(L["debt_high"].format(v=d))
                broken.append("debt")
        c = m.get("interest_coverage")
        if c is not None:
            if c > 10:
                st += 4
            elif c < 3:
                st -= 6; thr.append(L["cover_low"].format(v=c))
        parts["strength"] = _clamp(st, GROUPS["strength"])

    if m.get("revenue_cagr") is not None or m.get("eps_cagr") is not None:
        g = 0.0
        n = m["years"] - 1
        rc = m.get("revenue_cagr")
        if rc is not None:
            if rc > 8:
                g += 6; opp.append(L["growth_up"].format(v=rc, n=n))
            elif rc > 3:
                g += 3; opp.append(L["growth_up"].format(v=rc, n=n))
            elif rc < 0:
                g -= 5; thr.append(L["growth_dn"].format(v=rc, n=n))
        ec = m.get("eps_cagr")
        if ec is not None:
            if ec > 8:
                g += 5; opp.append(L["eps_up"].format(v=ec))
            elif ec < 0:
                g -= 5; thr.append(L["eps_dn"].format(v=ec))
        if m.get("eps_declines", 0) >= run:
            broken.append("eps")
            thr.append(L["eps_declining"].format(n=m["eps_declines"]))
        dg = (m.get("dividends") or {}).get("growth_5y")
        if dg is not None and dg > 5:
            g += 4; opp.append(L["div_growth"].format(v=dg))
        parts["growth"] = _clamp(g, GROUPS["growth"])

    q, seen = 0.0, False
    if not fin and m.get("roic_avg") is not None:
        seen = True
        r = m["roic_avg"]
        if r >= 15:
            q += 10; opp.append(L["roic_high"].format(v=r))
        elif r >= 10:
            q += 5
        elif r < 6:
            q -= 8; thr.append(L["roic_low"].format(v=r))
        if (m.get("roic_min") or 0) >= 10:
            q += 4
        if m.get("roic_declines", 0) >= run:
            q -= 5; broken.append("roic"); thr.append(L["roic_declining"].format(n=m["roic_declines"]))
    elif fin and m.get("roe_avg") is not None:
        seen = True
        r = m["roe_avg"]
        if r >= 12:
            q += 10; opp.append(L["roe_high"].format(v=r))
        elif r >= 8:
            q += 4
        elif r < 6:
            q -= 8; thr.append(L["roe_low"].format(v=r))
    if m.get("op_margin_std") is not None:
        seen = True
        if m["op_margin_std"] <= 2:
            q += 5; opp.append(L["margin_stable"].format(v=m["op_margin_std"]))
        elif m["op_margin_std"] > 6:
            q -= 5; thr.append(L["margin_volatile"].format(v=m["op_margin_std"]))
    if m.get("dilution_pa") is not None:
        seen = True
        if m["dilution_pa"] > 2:
            q -= 5; thr.append(L["dilution"].format(v=m["dilution_pa"]))
        elif m["dilution_pa"] < -1:
            q += 3; opp.append(L["buyback"].format(v=-m["dilution_pa"]))
        if (m.get("dilution_last") or 0) > 3 and (m.get("dilution_last") or 0) > (m.get("dilution_pa") or 0) + 1:
            broken.append("dilution")  # dilution qui s'accélère
    if not fin and m["years"] >= 3:
        seen = True
        neg_years = m["years"] - m.get("fcf_positive_years", 0)
        if neg_years == 0:
            q += 3
        elif neg_years * 2 >= m["years"]:
            q -= 5; thr.append(L["fcf_irregular"].format(n=neg_years, t=m["years"]))
    dv = m.get("dividends") or {}
    if dv.get("years_without_cut", 0) >= 10:
        seen = True
        q += 3; opp.append(L["div_streak"].format(n=dv["years_without_cut"]))
    if (m.get("payout_ratio") or 0) > 90:
        thr.append(L["payout_high"].format(v=m["payout_ratio"]))
    if seen:
        parts["quality"] = _clamp(q, GROUPS["quality"])
    return parts, broken


def momentum_12_1(hist, bench=None, now=None) -> float | None:
    """Rendement sur 12 mois hors dernier mois, moins celui du MSCI World (CW8) sur la même fenêtre (points de %)."""
    c = [p.get("adj") or p["close"] for p in hist]
    if len(c) < 253 or not c[-253]:
        return None
    mine = c[-22] / c[-253] - 1
    if bench:
        b_at = _series_at(bench)
        b0, b1 = b_at(hist[-253]["ts"]), b_at(hist[-22]["ts"])
        if b0 and b1:
            return (mine - (b1 / b0 - 1)) * 100
    return (mine - MARKET_RETURN / 100) * 100


def local_advice(sym, lang, quote, hist, arts, now=None, fin=None, kind="stock", leveraged=False, bench=None):
    """Conseil long terme : fondamentaux et valorisation (48 pts), qualité et régularité (25), tendance (27 : moyenne
    200 jours et force relative 12-1 face au MSCI World). fin : indicateurs financiers à la date du conseil ;
    bench : historique de CW8 ; les actualités sont informatives (hors score)."""
    now = now or time.time()
    L = T.get(lang, T["en"])
    tech = technicals(hist)
    evs, _ = events(hist, arts)
    nv = news_view(arts, now)
    opp, thr, pat = [], [], []
    parts = {}
    up = None
    if tech.get("sma200"):
        up = tech["price"] > tech["sma200"]
        parts["trend"] = 15 if up else -15
        (opp if up else thr).append(L["above200" if up else "below200"])
    mom = momentum_12_1(hist, bench, now)
    if mom is not None:
        parts["momentum"] = _clamp(mom * 0.3, GROUPS["momentum"])
        if mom >= 10:
            opp.append(L["mom_rel_up"].format(v=mom))
        elif mom <= -10:
            thr.append(L["mom_rel_dn"].format(a=abs(mom)))
    if tech.get("cagr") is not None:
        pat.append(L["cagr"].format(c=tech["cagr"], y=int(tech["years"]), dd=-tech["max_drawdown"]))
    broken = []
    if kind == "stock":
        fparts, broken = score_financials(fin, L, opp, thr, pat, up)
        parts.update(fparts)
        if not fin or not fin.get("years"):
            pat.append(L["no_fin"])
    dy = quote.get("dividend_yield")
    if dy:
        tech["dividend_yield"] = dy
    if nv["count"]:
        pat.append(L["news_info"].format(pos=nv["pos"], neg=nv["neg"]))
    if leveraged:
        thr.insert(0, L["leveraged"])
    score = int(max(-100, min(100, round(sum(parts.values())))))
    verdict = _verdict(score)
    # Verdict symétrique : une thèse cassée (ROIC ou bénéfices en baisse deux ans de suite, dette excessive, dilution
    # qui s'accélère) plafonne le verdict, quels que soient la valorisation et le cours
    if len(broken) >= 2 and VERDICTS.index(verdict) > VERDICTS.index("REDUCE"):
        verdict = "REDUCE"
    elif len(broken) == 1 and VERDICTS.index(verdict) > VERDICTS.index("HOLD"):
        verdict = "HOLD"
    if broken:
        thr.insert(0, L["thesis_broken"].format(n=len(broken)))
    if kind != "stock":  # ETF, indices… : pas de verdict d'achat / vente
        verdict, score = "HOLD", min(score, 15) if score > 0 else max(score, -15)
        pat.insert(0, L["etf"])
    coverage = sum(1 for g in ("valuation", "strength", "growth", "quality") if g in parts) / 4 if kind == "stock" else 0
    signs = [v for v in parts.values() if v]
    agree = sum((v > 0) == (score > 0) for v in signs) / len(signs) if signs else 0
    confidence = ("high" if coverage >= 0.75 and agree >= 0.75 else "medium" if coverage >= 0.5 and agree >= 0.55 else "low")
    lead = ([L["pros"].format(x=opp[0].rstrip("."))] if opp else []) + ([L["cons"].format(x=thr[0].rstrip("."))] if thr else [])
    return {
        "symbol": sym, "name": quote.get("name", sym), "verdict": verdict, "verdict_label": L["v"][verdict],
        "score": score, "confidence": confidence, "horizon": None, "kind": kind, "leveraged": leveraged,
        "summary": L["summary"].format(name=quote.get("short_name", sym), v=L["v"][verdict], s=score, lead=". ".join(x.rstrip(".") for x in lead) + "."),
        "opportunities": opp, "threats": thr, "patterns": pat, "catalysts": [],
        "components": {k: round(v, 1) for k, v in parts.items()}, "coverage": round(coverage, 2),
        "broken": broken, "momentum_12_1": round(mom, 1) if mom is not None else None,
        "technicals": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in tech.items()},
        "news": {k: v for k, v in nv.items() if k != "topics"},
        "events": evs[-12:][::-1], "engine": "local", "ai_error": None, "verification": None,
        "generated_at": int(time.time()), "articles_analyzed": nv["count"], "fundamentals": quote.get("fundamentals") or None,
        "financials": fin,
    }


EVENT_LIST = ", ".join(newsevents.TYPES)


def _prompt(base, arts, lang, pea=None, compact=False):
    t = base["technicals"]
    lines = [f"[{i}] {datetime.fromtimestamp(a['timestamp'], timezone.utc):%Y-%m-%d} | {a['source']} | {a['headline']}"
             + (f" — {a['summary'][:120]}" if a["summary"] else "") for i, a in enumerate(arts)]
    out = f"""You are a long-term investor in the tradition of Buffett, Munger, Lynch and Fisher: you judge the business (moat, ROIC, free cash-flow,
balance sheet, management, valuation against its own history), not short-term price moves or media noise. Analyse {base['name']} ({base['symbol']}).

PRICE DATA (daily, up to 10 years): {json.dumps(t)}
QUANTITATIVE SIGNALS: {json.dumps(base['components'])}
HISTORICAL PATTERNS: {json.dumps(base['patterns'], ensure_ascii=False)}
COMPANY ACCOUNTS (published annual accounts, last {(base.get('financials') or {}).get('years', 0)} fiscal years; null = unknown, never guess): {json.dumps({k: v for k, v in (base.get('financials') or {}).items() if k != 'annual'}, ensure_ascii=False)}
ANNUAL FIGURES: {json.dumps((base.get('financials') or {}).get('annual') or [], ensure_ascii=False)}
RISK (computed): {json.dumps(base.get('risk') or {})}
RELATIVE STRENGTH (computed, vs benchmark and sector peers): {json.dumps(base.get('relative') or {})}
LOCAL QUANTITATIVE PRIOR: score {base['score']} (-100..100), verdict {base['verdict']}, thesis warnings {base.get('broken') or []}.
MODEL RELIABILITY (cross-sectional, all stocks ranked monthly, 12-month rank correlation between score and later return): {json.dumps({k: (base.get('reliability') or {}).get(k) for k in ('level', 'model_ic', 'model_ic_low', 'model_ic_high', 'model_months')})}. If the interval contains 0 the model has NOT been shown to predict anything: say so and do not lean on its score.
INVESTOR'S PEA (French tax wrapper, personal data, EUR): {json.dumps(pea, ensure_ascii=False) if pea else "unknown"}
RECENT ARTICLES (numbered):
{chr(10).join(lines)}

Think like an investor: read every article, weigh its real impact on the business (not only its tone), relate the news to the price
history and past shocks, spot recurring patterns (how the stock reacts to earnings, legal issues, macro, etc.) and judge whether the
current situation is an opportunity or a threat. Be concrete and cite facts from the articles.
Tailor the advice to the investor's PEA: if they hold the stock, take into account their average cost, unrealised gain or loss,
holding period and the line's weight (a line above 20% of the PEA or a sector above 35% is too concentrated); if they do not,
consider their available cash and diversification. Say concretely what they should do with their position.
Start from the LOCAL QUANTITATIVE PRIOR and move away from it only for specific, verifiable reasons, citing the article numbers [i]
or the figures above. Base rates matter: most stocks do not beat their index over 12 months, so a probability far from 50 % needs
strong evidence. Never invent figures that are not given above.

Answer ONLY with JSON, all text in {LANG_NAMES.get(lang, 'English')}:
{{"verdict": "STRONG_BUY|BUY|HOLD|REDUCE|SELL", "score": <int -100..100>, "confidence": "low|medium|high",
"horizon": "<1, 3 or 5 years>", "summary": "<4-6 sentences of investor reasoning>",
"opportunities": ["..."], "threats": ["..."], "patterns": ["<recurring behaviours spotted>"], "catalysts": ["<upcoming events to watch>"],
"prob_outperform_12m": <0..100, probability the stock beats its benchmark over 12 months>,
"scenarios": {{"bear": {{"return_12m": <%>, "probability": <%>}}, "base": {{...}}, "bull": {{...}}}},
"article_sentiments": [{{"i": <article number>, "s": <float -1..1 impact on the stock>, "type": "<one of: {EVENT_LIST} or none>",
  "magnitude": "<quantified size from the article, e.g. '3 % of revenue' or '200 M€', or null>", "durable": <true|false>,
  "moat": <true if it changes the competitive advantage, else false>, "eps_impact_pct": <estimated % effect on normalised EPS, or null>}}]}}
"article_sentiments" MUST contain exactly one entry for EVERY numbered article (0 to {len(arts) - 1}). Extract facts, not opinions:
the type must come from the list, the magnitude must be stated in the article (null otherwise).
Count only the first article of duplicate stories."""
    if compact:  # analyses groupées : réponse courte, sans notation des articles
        out = out.split('"article_sentiments"')[0].rstrip(", \n") + "}\nGive 2 to 4 short items per list."
    return out


def advise(sym, lang="fr", force=False, use_ai=True, max_wait=20.0, backfill=True, fetch_fundamentals=True, background=False):
    """Conseil long terme calculé (le verdict). L'IA, si elle est demandée, ajoute une lecture explicative à part :
    elle ne remplace jamais le verdict ni le score. max_wait : attente maximale d'une clé IA disponible."""
    sym = sym.upper()
    want_ai = use_ai and ai_pool.has_keys()
    if not force:
        with store.connect() as conn:
            row = conn.execute("SELECT created_at, payload FROM advice_cache WHERE symbol = ? AND lang = ?", (sym, lang)).fetchone()
        if row and time.time() - row[0] < CACHE_SECONDS:
            cached = json.loads(row[1])
            if cached.get("v") == ENGINE_VERSION and (cached.get("ai_view") or not want_ai):
                return cached

    quote = yahoo.quote(sym)
    news.refresh(sym, quote.get("name", ""), backfill=backfill)
    hist = yahoo.daily_history(sym)
    arts = news.articles(sym)
    info = catalog.lookup(sym) or {}
    kind, sector = info.get("kind", "stock"), info.get("sector")
    quote["dividend_yield"] = yahoo.dividend_yield(sym, quote.get("price"))
    quote["fundamentals"] = fundamentals.get(sym, fetch=fetch_fundamentals)
    fin_raw = financials.raw(sym) if kind == "stock" else None  # comptes publics sans clé : toujours récupérés (cache 7 jours)
    fin = financials.metrics(fin_raw, quote.get("price"), sector, hist, currency=quote.get("currency"))
    try:
        bench = yahoo.daily_history(BENCHMARK)
    except Exception:
        bench = None
    result = local_advice(sym, lang, quote, hist, arts, fin=fin, kind=kind, leveraged=bool(info.get("leveraged")), bench=bench)
    result["sector"] = sector
    try:
        result["track_record"] = backtest(sym, quote, hist, fin_raw, sector, kind, bench)
    except Exception as e:
        result["track_record"] = None
        print(f"Backtest {sym}: {e}")

    _enrich(result, sym, hist, bench)
    try:
        region = yahoo.daily_history(insights.benchmark(sym)[0])
        result["news_events"] = newsevents.for_symbol(sym, hist, region)
    except Exception as e:
        result["news_events"] = []
        print(f"Événements {sym} : {e}")

    if use_ai and not want_ai:
        result["ai_error"] = "Aucune clé IA : ajoutez-en une dans Paramètres → Clés IA"
    if want_ai:
        recent = arts[:50]
        try:
            try:
                pea = portfolio.context(sym)
            except Exception:
                pea = None
            ai, provider = ai_pool.complete_json(_prompt(result, recent, lang, pea), max_wait, background, effort="medium")
            v = ai.get("verdict") if ai.get("verdict") in VERDICTS else result["verdict"]
            view = {
                "verdict": v, "verdict_label": T.get(lang, T["en"])["v"][v],
                "score": int(max(-100, min(100, float(ai.get("score") or 0)))),
                "confidence": ai.get("confidence") if ai.get("confidence") in ("low", "medium", "high") else "low",
                "horizon": ai.get("horizon"), "summary": ai.get("summary") or "",
                "opportunities": ai.get("opportunities") or [], "threats": ai.get("threats") or [],
                "patterns": ai.get("patterns") or [], "catalysts": ai.get("catalysts") or [],
                "provider": provider, "articles_analyzed": len(recent), "outlook": outlook(ai), "generated_at": int(time.time()),
            }
            view["verification"] = verify(view, ai, result["score"], _known_values(result, quote))
            result["ai_view"] = view
            result["catalysts"] = view["catalysts"]
            ai_store.save(sym, "single", {**view, "local_verdict": result["verdict"], "local_score": result["score"]},
                          quote.get("price"), quote.get("currency"), lang)
            with store.connect() as conn:
                for item in ai.get("article_sentiments") or []:
                    i = item.get("i")
                    if isinstance(i, int) and 0 <= i < len(recent):
                        try:
                            sent = str(max(-1.0, min(1.0, float(item.get("s", 0)))))
                        except (TypeError, ValueError):
                            sent = "0"
                        ev = {"type": item.get("type") if item.get("type") in newsevents.TYPES else None,
                              "magnitude": item.get("magnitude"), "durable": bool(item.get("durable")), "moat": bool(item.get("moat")),
                              "eps_impact_pct": item.get("eps_impact_pct") if isinstance(item.get("eps_impact_pct"), (int, float)) else None}
                        conn.execute("UPDATE articles SET ai_sentiment = ?, ai_event = ? WHERE id = ?", (sent, json.dumps(ev), recent[i]["id"]))
        except Exception as e:
            result["ai_error"] = str(e)[:300]

    result["v"] = ENGINE_VERSION
    _log_history(result, quote.get("price"))
    with store.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO advice_cache (symbol, lang, created_at, payload) VALUES (?, ?, ?, ?)",
                     (sym, lang, int(time.time()), json.dumps(result, ensure_ascii=False)))
    return result


AI_SHRINK = 0.5        # part de l'avis de l'IA conservée : le reste revient vers la moyenne du marché, tant que sa fiabilité n'est pas mesurée
MARKET_RETURN = 7.0    # rendement annuel moyen des actions sur longue période (%)


def outlook(ai: dict) -> dict | None:
    """Scénarios à 12 mois proposés par l'IA, et version corrigée (ramenée vers la moyenne du marché et vers 50 %)."""
    sc = ai.get("scenarios") or {}
    rows = {}
    for k in ("bear", "base", "bull"):
        v = sc.get(k) or {}
        try:
            rows[k] = {"return_12m": float(v.get("return_12m")), "probability": float(v.get("probability"))}
        except (TypeError, ValueError):
            return None
    total = sum(r["probability"] for r in rows.values()) or 1
    for r in rows.values():
        r["probability"] = round(r["probability"] / total * 100)
    expected = sum(r["return_12m"] * r["probability"] for r in rows.values()) / 100
    try:
        p = max(0.0, min(100.0, float(ai.get("prob_outperform_12m"))))
    except (TypeError, ValueError):
        p = None
    try:
        shrink = ai_store.measured_shrink(AI_SHRINK)
    except Exception:
        shrink = AI_SHRINK
    return {"scenarios": rows, "expected_12m": round(expected, 1),
            "expected_12m_adjusted": round(MARKET_RETURN + shrink * (expected - MARKET_RETURN), 1),
            "prob_outperform": p, "prob_outperform_adjusted": round(50 + shrink * (p - 50)) if p is not None else None,
            "shrink": shrink}


def _enrich(result, sym, hist, world=None):
    """Risque, force relative, fiabilité réelle et santé financière : ce qui rend le conseil exploitable."""
    try:
        from services import screener  # import tardif (le module de classement dépend du catalogue)
        bench_sym, _ = insights.benchmark(sym)
        try:
            bench = yahoo.daily_history(bench_sym)
        except Exception:
            bench = None
        info = catalog.lookup(sym) or {}
        result["risk"] = insights.risk(hist, bench)
        try:
            from services import objectives
            cap = float(objectives.get().get("max_line") or insights.MAX_LINE)
            if result["risk"]:
                result["risk"]["max_weight"] = min(result["risk"]["max_weight"], cap)
        except Exception:
            pass
        result["relative"] = insights.relative(sym, hist, bench, info.get("sector"), screener._snapshot)
        result["live_record"] = insights.live_record(sym, hist, world)
        from services import validation
        result["reliability"] = insights.reliability(result.get("track_record"), result["live_record"], result["risk"], validation.latest())
        result["health"] = insights.health(result.get("financials"))
    except Exception as e:
        print(f"Analyse complémentaire {sym} : {e}")


HORIZONS = {"1y": 252, "3y": 756, "5y": 1260}
BENCHMARK = "CW8.PA"  # MSCI World dividendes réinvestis, en euros : l'alternative simple de l'investisseur PEA
ENGINE_VERSION = 4


def _series_at(hist):
    days = [p["ts"] for p in hist]
    vals = [p.get("adj") or p["close"] for p in hist]

    def at(ts):
        i = bisect.bisect_right(days, ts) - 1
        return vals[i] if i >= 0 and ts - days[i] < 10 * 86400 else None
    return at


def backtest(sym, quote, hist, fin_raw=None, sector=None, kind="stock", bench=None) -> dict:
    """Rejoue chaque mois le moteur affiché (avec les seuls comptes publiés à cette date) et compare la suite au
    MSCI World dividendes réinvestis (CW8). « Battre le marché » est la seule question utile : un achat est juste s'il
    a fait mieux que CW8, une vente / un allègement s'il a fait moins bien. Le taux de base est la part des périodes où
    la valeur a battu CW8 (ce qu'aurait obtenu « toujours acheter ») : l'avantage du moteur se mesure par rapport à lui."""
    if not bench:
        return {}
    b_at = _series_at(bench)
    adj = [p.get("adj") or p["close"] for p in hist]
    out = {h: {"all": [], "full": []} for h in HORIZONS}
    for t in range(260, len(hist) - min(HORIZONS.values()), 21):
        ts, price = hist[t]["ts"], hist[t]["close"]
        m = financials.metrics(fin_raw, price, sector, hist[: t + 1], as_of=ts, currency=quote.get("currency")) if fin_raw else None
        r = local_advice(sym, "en", {**quote, "dividend_yield": None, "fundamentals": None}, hist[: t + 1], [], now=ts, fin=m, kind=kind,
                         bench=bench)  # seules les dates passées de CW8 sont lues
        full = bool(m and m.get("years"))
        b0 = b_at(ts)
        for h, d in HORIZONS.items():
            if t + d >= len(hist) or not b0:
                continue
            b1 = b_at(hist[t + d]["ts"])
            if not b1:
                continue
            excess = ((adj[t + d] / adj[t]) - (b1 / b0)) * 100
            sample = (r["verdict"], excess)
            out[h]["all"].append(sample)
            if full:
                out[h]["full"].append(sample)

    def stats(samples, engine):
        n = len(samples)
        buys = [e for v, e in samples if v in ("BUY", "STRONG_BUY")]
        sells = [e for v, e in samples if v in ("SELL", "REDUCE")]
        base = sum(e > 0 for _, e in samples) / n * 100 if n else None
        buy_hit = sum(e > 0 for e in buys) / len(buys) * 100 if buys else None
        sell_hit = sum(e < 0 for e in sells) / len(sells) * 100 if sells else None
        edges = [(buy_hit - base, len(buys))] if buy_hit is not None else []
        if sell_hit is not None:
            edges.append((sell_hit - (100 - base), len(sells)))
        w = sum(k for _, k in edges)
        return {"n": n, "engine": engine, "base": _rnd(base), "buy_n": len(buys), "buy_hit": _rnd(buy_hit),
                "sell_n": len(sells), "sell_hit": _rnd(sell_hit),
                "edge": _rnd(sum(e * k for e, k in edges) / w) if w else None,
                "avg_excess_buy": _rnd(statistics.mean(buys)) if buys else None,
                "avg_excess_all": _rnd(statistics.mean(e for _, e in samples)) if samples else None}

    # Le moteur complet (avec comptes) n'est mesurable que depuis la publication des comptes disponibles
    return {h: stats(o["full"], "full") if len(o["full"]) >= 12 else stats(o["all"], "trend_only") for h, o in out.items()}


def _rnd(v):
    return round(v, 1) if v is not None else None


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
    vals += [quote.get(k) or 0 for k in ("price", "change_percent", "year_high", "year_low", "day_high", "day_low", "dividend_yield")]
    vals += [v for v in (result.get("fundamentals") or {}).values() if isinstance(v, (int, float))]
    fin = result.get("financials") or {}
    vals += [v for v in fin.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    vals += [v for v in (fin.get("dividends") or {}).values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for k in ("risk", "relative"):
        vals += [v for v in (result.get(k) or {}).values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
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
    expected = _verdict(result["score"])
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
        tr = (p.get("track_record") or {}).get("1y") or {}
        tech = p.get("technicals") or {}
        fin = p.get("financials") or {}
        out[r[0]] = {"verdict": p["verdict"], "score": p["score"], "confidence": p["confidence"],
                     "engine": p["engine"], "generated_at": p["generated_at"], "edge_1y": tr.get("edge"),
                     "reliable": (p.get("reliability") or {}).get("signal"), "coverage": p.get("coverage"),
                     "cagr": tech.get("cagr"), "volatility": tech.get("volatility"),
                     "quality": (p.get("components") or {}).get("quality"), "valuation": (p.get("components") or {}).get("valuation"),
                     "fcf_yield": fin.get("fcf_yield"), "roic_avg": fin.get("roic_avg"), "roe_avg": fin.get("roe_avg"),
                     "pe": fin.get("pe"), "pe_history_median": fin.get("pe_history_median"),
                     "net_debt_ebitda": fin.get("net_debt_ebitda"), "div_streak": (fin.get("dividends") or {}).get("years_without_cut"),
                     "dividend_yield": fin.get("dividend_yield")}
    return out
