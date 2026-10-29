"""Backtest sur données réelles : l'application est replacée à des dates passées (cours et articles connus à cette date
uniquement), puis ses conseils (moteur local et IA) sont comparés à l'évolution réelle de l'action ensuite.
Usage : STOCKPULSE_DATA_DIR=<dossier avec clé IA> python tools/backtest_ai.py [nb_valeurs] [nb_dates] [avec_ia]"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import store  # noqa: E402
from services import advisor, ai_pool, news, yahoo  # noqa: E402

SYMBOLS = ["MC.PA", "AI.PA", "TTE.PA", "SAN.PA", "OR.PA", "SU.PA", "BNP.PA", "AIR.PA", "SAP.DE", "ASML.AS"]
OFFSETS = [252, 189, 126, 63]  # séances avant aujourd'hui (≈ 12, 9, 6, 3 mois)
HORIZONS = {"1m": 21, "3m": 63}


def main(n_sym=8, n_dates=4, with_ai=True):
    store.init()
    rows = []
    for sym in SYMBOLS[:n_sym]:
        q, hist, arts = yahoo.quote(sym), yahoo.daily_history(sym), news.articles(sym)
        for off in OFFSETS[:n_dates]:
            t = len(hist) - 1 - off
            ts = hist[t]["ts"]
            day = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
            past = [a for a in arts if a["timestamp"] <= ts]
            local = advisor.local_advice(sym, "en", {**q, "price": hist[t]["close"]}, hist[: t + 1], past, now=ts)
            row = {"symbol": sym, "date": day, "local": local["verdict"], "local_score": local["score"], "articles": len(past)}
            for h, d in HORIZONS.items():
                row[f"ret_{h}"] = round((hist[t + d]["close"] / hist[t]["close"] - 1) * 100, 2) if t + d < len(hist) else None
            if with_ai:
                prompt = (f"TODAY IS {day}. Use ONLY the data below and nothing you may know after this date.\n"
                          + advisor._prompt(local, sorted(past, key=lambda a: -a["timestamp"])[:30], "en"))
                try:
                    ai, provider = ai_pool.complete_json(prompt, max_wait=90)
                    row.update(ai=ai.get("verdict"), ai_score=ai.get("score"), model=provider)
                except Exception as e:
                    row.update(ai=None, ai_error=str(e)[:120])
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    summary = {}
    for engine in ("local", "ai"):
        for h in HORIZONS:
            pairs = [(r[engine], r[f"ret_{h}"]) for r in rows if r.get(engine) in advisor.VERDICTS and r[f"ret_{h}"] is not None]
            if pairs:
                hits = sum(advisor._hit(v, ret) for v, ret in pairs)
                buys = [ret for v, ret in pairs if v in ("BUY", "STRONG_BUY")]
                summary[f"{engine}_{h}"] = {"n": len(pairs), "hit_rate": round(hits / len(pairs) * 100),
                                            "avg_return_after_buy": round(sum(buys) / len(buys), 2) if buys else None}
    pairs = [r[f"ret_3m"] for r in rows if r["ret_3m"] is not None]
    summary["market_avg_3m"] = round(sum(pairs) / len(pairs), 2) if pairs else None
    print("SUMMARY " + json.dumps(summary))
    return rows, summary


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 8, int(a[1]) if len(a) > 1 else 4, (a[2] != "0") if len(a) > 2 else True)
