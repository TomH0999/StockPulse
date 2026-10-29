"""Régénère les fichiers de base backend/catalog/*.json depuis les sources publiques.
Usage : python tools/build_catalog.py  (l'application met aussi son catalogue à jour seule chaque jour)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from services import catalog_updater as cu  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "catalog")


def main():
    old = {e["symbol"]: e for f in os.listdir(OUT) if f.endswith(".json") for e in json.load(open(os.path.join(OUT, f), encoding="utf-8"))}
    cands = cu.candidates()
    for s, e in old.items():  # l'ancien catalogue reste suivi
        cands.setdefault(s, {**e, "file": cu.file_for(s)})
        cands[s].update({k: v for k, v in e.items() if k in ("sector", "core", "isin") and v and not cands[s].get(k)})
    metas = cu.quotes_meta(list(cands))
    print(f"{len(metas)}/{len(cands)} symboles valides")
    keep = {s: c for s, c in cands.items() if s in metas}
    for s, sec in cu.sectors([s for s, c in keep.items() if not c.get("sector")]).items():
        keep[s]["sector"] = sec
    files: dict[str, list] = {}
    for s, c in sorted(keep.items()):
        entry = {"symbol": s, "name": metas[s]["name"] or c["name"]}
        for k in ("isin", "sector", "core", "pea"):
            if c.get(k):
                entry[k] = c[k]
        files.setdefault(c["file"], []).append(entry)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for name, entries in files.items():
        with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as fh:
            fh.write("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n]\n")
        print(name, len(entries))


if __name__ == "__main__":
    main()
