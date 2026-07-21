# -*- coding: utf-8 -*-
"""Module-2 mechanical scans (read-only):
1) load every dsl_payloads/*.json through dsl.load_payload_file (full parse validation);
2) direction-sanity scans (wrong-sign params / side-mismatched S-T tags);
3) weapon_filter existence check against the faction's DB weapon names.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))
from engines.simulator.dsl import load_payload_file

ROOT = Path(".").resolve()
DB = ROOT / "db" / "wh40k.sqlite"

con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
cur = con.cursor()
tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("DB tables:", tables)

weapon_tbl = None
for cand in ("weapons", "wargear", "datasheet_weapons"):
    if cand in tables:
        weapon_tbl = cand
        break

total = 0
flags = []
for path in sorted((ROOT / "dsl_payloads").glob("*.json")):
    entries = load_payload_file(path)   # raises on any invalid payload
    total += len(entries)
    for e in entries:
        for eff in e.effects:
            key = (eff.phase, eff.op)
            tag = eff.condition[0] if eff.condition else None
            p0 = eff.params[0] if eff.params else None
            # side-mismatched S/T delayed tags (module-1 MEDIUM-1 exposure recheck)
            if e.side == "attacker" and tag in ("wound_s_gt_t",):
                flags.append((path.stem, e.row_id, "attacker-side wound_s_gt_t", key))
            if e.side == "target" and tag in ("melee_s_lte_t",):
                flags.append((path.stem, e.row_id, "target-side melee_s_lte_t", key))
            # direction sanity
            if e.side == "target" and key == ("save", "ap_improve") and isinstance(p0, int) and p0 > 0:
                flags.append((path.stem, e.row_id, "target ap_improve POSITIVE (improves attacker AP?)", p0))
            if e.side == "target" and key == ("hit", "modify") and isinstance(p0, int) and p0 > 0:
                flags.append((path.stem, e.row_id, "target hit modify POSITIVE (helps attacker?)", p0))
            if e.side == "target" and key == ("wound", "modify") and isinstance(p0, int) and p0 > 0:
                flags.append((path.stem, e.row_id, "target wound modify POSITIVE (helps attacker?)", p0))
            if e.side == "attacker" and key == ("save", "ap_improve") and isinstance(p0, int) and p0 < 0:
                flags.append((path.stem, e.row_id, "attacker ap_improve NEGATIVE (worsens own AP?)", p0))
            if e.side == "target" and key == ("wound", "t_improve") and isinstance(p0, int) and p0 < 0:
                flags.append((path.stem, e.row_id, "target t_improve NEGATIVE", p0))
            if e.side == "target" and key == ("hit", "bs_improve") and isinstance(p0, int) and p0 > 0:
                flags.append((path.stem, e.row_id, "target bs_improve POSITIVE (helps attacker?)", p0))

print(f"parsed OK: {total} entries across 19 files")
print("--- direction/side flags ---")
for f in flags:
    print(" | ".join(str(x) for x in f))
print(f"total: {len(flags)}")

# weapon_filter existence (5 priority factions), if a weapon table exists
FIVE = {"darkangels", "spacemarines", "imperialknights", "imperialagents", "votann"}
if weapon_tbl:
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({weapon_tbl})")]
    print(f"--- weapon_filter check via {weapon_tbl} cols={cols} ---")
    namecol = "name_en" if "name_en" in cols else ("name" if "name" in cols else None)
    names = [r[0] for r in cur.execute(
        f"SELECT DISTINCT {namecol} FROM {weapon_tbl}")] if namecol else []
    lows = [(n or "").casefold() for n in names]
    for path in sorted((ROOT / "dsl_payloads").glob("*.json")):
        if path.stem not in FIVE:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data["entries"]:
            wf = (e.get("weapon_filter") or "").casefold()
            if not wf:
                continue
            hits = sum(1 for n in lows if wf in n)
            print(f"{path.stem} | {e['id']} | {e['name_en']} | wf={wf!r} | db_name_hits={hits}")
else:
    print("no weapon table found; weapon_filter check skipped")
con.close()
