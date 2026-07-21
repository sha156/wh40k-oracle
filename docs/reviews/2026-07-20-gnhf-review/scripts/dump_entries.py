# -*- coding: utf-8 -*-
"""Module-2 review helper: dump effects-bearing DSL entries joined with original DB rule text.

Usage: .venv\\Scripts\\python.exe docs/reviews/2026-07-20-gnhf-review/scripts/dump_entries.py <faction.json> [...]
Read-only on db/wh40k.sqlite.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "db" / "wh40k.sqlite"

TEXT_COLS = {
    "abilities": ["description"],
    "stratagems": ["legend", "description"],
    "enhancements": ["legend", "description"],
    "detachments": ["rule_text"],
}


def db_text(cur, table, row_id):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
    want = [c for c in ("name", "legend", "description", "rule_text", "text_zh", "type",
                        "cp_cost", "phase", "turn", "detachment", "detachment_name") if c in cols]
    row = cur.execute(
        f"SELECT {', '.join(want)} FROM {table} WHERE id = ?", (str(row_id),)
    ).fetchone()
    if row is None:
        return None
    return dict(zip(want, row))


def main(paths):
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        fname = Path(p).stem
        for e in data["entries"]:
            if not e.get("effects"):
                continue
            mat = e.get("materialize") or {}
            table = mat.get("from_table") or e["table"]
            row_id = mat.get("from_id") or e["id"]
            info = db_text(cur, table, row_id) or {}
            print("=" * 100)
            print(f"[{fname}] {e['table']}:{e['id']}  side={e['side']}  status={e['status']}"
                  f"  det={e.get('detachment')}")
            print(f"  name: {e.get('name_en')}  / zh: {e.get('name_zh')}")
            if e.get("weapon_filter"):
                print(f"  weapon_filter: {e['weapon_filter']!r}")
            if e.get("requires_toggles"):
                print(f"  requires_toggles: {e['requires_toggles']}")
            if e.get("conflicts_with_toggles"):
                print(f"  conflicts: {e['conflicts_with_toggles']}")
            if e.get("toggle_groups"):
                print(f"  toggle_groups: {json.dumps(e['toggle_groups'], ensure_ascii=False)}")
            for eff in e["effects"]:
                print(f"  EFFECT phase={eff['phase']} op={eff['op']} params={eff.get('params')}"
                      f" cond={eff.get('condition')} src={eff.get('source')}")
            for n in e.get("not_modeled_notes_zh") or []:
                print(f"  NOTE: {n}")
            for k, v in info.items():
                if v is None or v == "":
                    continue
                v = str(v).replace("\r", "")
                print(f"  DB.{k}: {v}")
    con.close()


if __name__ == "__main__":
    main(sys.argv[1:])
