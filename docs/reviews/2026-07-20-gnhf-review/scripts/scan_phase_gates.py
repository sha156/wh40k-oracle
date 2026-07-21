# -*- coding: utf-8 -*-
"""Module-2 mechanical scan: stratagem WHEN-clause phase vs DSL effect phase gates.

For every effects-bearing stratagem entry in dsl_payloads/*.json, parse the WHEN
clause from db.stratagems.text_zh (the DB `phase` column is unreliable: e.g.
votann BREKKEKNOTS says 'Shooting phase' there while WHEN says both phases) and
check that each effect carries a phase gate consistent with the trigger window:

  - WHEN mentions both Shooting and Fight  -> no gate required
  - WHEN only Shooting                     -> gate in SHOOTING_GATES required
  - WHEN only Fight                        -> gate in MELEE_GATES required
  - WHEN only Charge (effect lasts turn)   -> gate in MELEE_GATES required
  - WHEN Command/other                     -> no gate required (spans both)

Also reverse check: gate present but WHEN covers both phases -> under-modeling flag.

Ops that are engine-inert outside shooting (cover only folds when
stance.phase=='shooting') are allow-listed ungated.
Read-only. Run with .venv python from repo root.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "db" / "wh40k.sqlite"

SHOOTING_GATES = {
    "phase_shooting", "ranged_within_12", "ranged_within_8",
    "shooting_target_models_in_range", "guided_vs_spotted", "guided_markerlight",
    "markerlight_observer", "detachment_rounds_shooting", "detachment_rounds_guided",
    "indirect", "half_range", "long_range",
}
MELEE_GATES = {
    "phase_melee", "melee_charging", "melee_target_has_keyword", "melee_disembarked",
    "melee_s_lte_t", "melee_wound_s_gt_t", "charging",
    "blessing_martial_excellence", "blessing_warp_blades",
    "blessing_decapitating_strikes_vs_infantry",
    "omen_instrument_vs_character", "omen_momentous_brutality",
}
# (phase, op) pairs that only ever change results while stance.phase == 'shooting'
SHOOTING_INERT_ELSEWHERE = {("save", "ignores_cover"), ("save", "cover")}


def when_clause(text):
    if not text:
        return None
    m = re.search(r"WHEN:</b>(.*?)<br>", text, re.S | re.I)
    return m.group(1) if m else None


def main():
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    flags = []
    n_checked = 0
    for path in sorted((ROOT / "dsl_payloads").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data["entries"]:
            if e["table"] != "stratagems" or not e.get("effects"):
                continue
            row = cur.execute("SELECT text_zh FROM stratagems WHERE id=?",
                              (e["id"],)).fetchone()
            when = when_clause(row[0] if row else None)
            if when is None:
                flags.append((path.stem, e["id"], e["name_en"], "NO-WHEN-TEXT", ""))
                continue
            w = when.lower()
            has_shoot = "shooting phase" in w
            has_fight = "fight phase" in w
            has_charge = "charge phase" in w or "charge move" in w
            n_checked += 1
            for eff in e["effects"]:
                cond = tuple(eff.get("condition") or ())
                tag = cond[0] if cond else None
                key = (eff["phase"], eff["op"])
                gates = ({tag} if tag else set())
                if has_shoot and has_fight:
                    if gates & (SHOOTING_GATES | MELEE_GATES) - {
                            "half_range", "long_range", "indirect"}:
                        flags.append((path.stem, e["id"], e["name_en"],
                                      "GATED-BUT-BOTH-PHASES(under-model?)",
                                      f"{key} cond={cond}"))
                elif has_shoot and not has_fight and not has_charge:
                    if key not in SHOOTING_INERT_ELSEWHERE and not (gates & SHOOTING_GATES):
                        flags.append((path.stem, e["id"], e["name_en"],
                                      "SHOOTING-ONLY-WHEN,NO-SHOOTING-GATE(over-apply)",
                                      f"{key} cond={cond}"))
                elif (has_fight or has_charge) and not has_shoot:
                    if not (gates & MELEE_GATES):
                        flags.append((path.stem, e["id"], e["name_en"],
                                      "FIGHT/CHARGE-WHEN,NO-MELEE-GATE(over-apply)",
                                      f"{key} cond={cond}"))
    print(f"checked {n_checked} stratagem entries with effects")
    for f in flags:
        print(" | ".join(str(x) for x in f))
    print(f"total flags: {len(flags)}")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
