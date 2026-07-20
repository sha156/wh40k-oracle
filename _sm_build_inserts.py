# -*- coding: utf-8 -*-
"""P7-PR20 Space-Marines：向 fp_rules_patches.json 追加 fp_new 补录插行。
2 新迷你分队（Fulguris Task Force / Subversion Assets，各 1 规则 + 2 增强 + 3 战略）
+ Bastion Task Force 漏录的 Angels Defiant 战略（DB id 序 002-005,007 缺 006）。"""
import json
from pathlib import Path

KWB = lambda s: f'<span class="kwb">{s}</span>'
LEG = "点数未知：FP 不含点数，MFM 缓存无增强数据（诚实置空，勿猜）"
FS_NEW = "Faction Pack Space-Marines（11 版新分队，Wahapedia 无源）"
FS_GAP = "Faction Pack Space-Marines（Bastion Task Force 漏录战略补回，DB id 序缺 006）"

inserts = []

def det(id_, zh, en, rule):
    inserts.append({"table": "detachments", "fp_source": FS_NEW,
                    "values": {"id": id_, "faction": "SM", "name_zh": zh,
                               "name_en": en, "rule_text": rule}})

def enh(id_, det_id, det_name, name, desc):
    inserts.append({"table": "enhancements", "fp_source": FS_NEW,
                    "values": {"id": id_, "faction_id": "SM", "detachment_id": det_id,
                               "detachment_name": det_name, "name": name, "cost": None,
                               "legend": LEG, "description": desc}})

def strat(id_, det_name, zh, en, phase, text, fp=FS_NEW):
    inserts.append({"table": "stratagems", "fp_source": fp,
                    "values": {"id": id_, "faction": "SM", "detachment": det_name,
                               "name_zh": zh, "name_en": en, "cp_cost": "1",
                               "phase": phase, "text_zh": text}})

# ── Fulguris Task Force ────────────────────────────────────────────────
det("fp11e-spacemarines-fulguris", "天雷突袭", "Skystrike",
    f"Friendly {KWB('LAND')} {KWB('SPEEDER')}/{KWB('STORM')} {KWB('SPEEDER')} "
    f"HAILSTRIKE/HAMMERSTRIKE/THUNDERSTRIKE units have the {KWB('SPEEDER')} keyword."
    "<br><br>In your first Movement phase, friendly SPEEDER units can make an ingress move.")
enh("fp11e-spacemarines-fulguris-e1", "fulguris-task-force", "Fulguris Task Force",
    "Bellicose Weapon Spirits",
    "SPEEDER unit only. This unit can re-roll Damage rolls and rolls to determine "
    "the Attacks characteristic of a weapon.")
enh("fp11e-spacemarines-fulguris-e2", "fulguris-task-force", "Fulguris Task Force",
    "Raptorial Cogitator Core",
    "SPEEDER unit only. This unit's ranged attacks have [IGNORES COVER].")
strat("fp11e-spacemarines-fulguris-s1", "Fulguris Task Force", "数据链导测", "Data-Link Augury",
      "Shooting phase",
      "<b>WHEN:</b> Your Shooting phase, when a friendly SPEEDER unit is selected to shoot."
      "<br><br><b>TARGET:</b> That SPEEDER unit.<br><br><b>EFFECT:</b> Select one enemy unit "
      "within 24\" of your unit. That enemy unit has +6\" detection range until your unit has shot.")
strat("fp11e-spacemarines-fulguris-s2", "Fulguris Task Force", "反应机动", "Reactive Evasion",
      "Movement phase",
      "<b>WHEN:</b> Your opponent's Movement phase, when an enemy unit ends a move within 8\" of a "
      "friendly unengaged SPEEDER unit.<br><br><b>TARGET:</b> That SPEEDER unit.<br><br>"
      "<b>EFFECT:</b> Your unit can make a Normal move of up to D3+3\".")
strat("fp11e-spacemarines-fulguris-s3", "Fulguris Task Force", "反重力涌动", "Anti-Grav Surge",
      "Fight phase",
      "<b>WHEN:</b> End of your opponent's Fight phase.<br><br><b>TARGET:</b> One friendly "
      "unengaged SPEEDER unit.<br><br><b>EFFECT:</b> Place your unit in Strategic Reserves.")

# ── Subversion Assets ──────────────────────────────────────────────────
det("fp11e-spacemarines-subversion", "无所遁形", "Nowhere to Hide",
    f"Friendly {KWB('PHOBOS')}/{KWB('SCOUT')} {KWB('SQUAD')} units have the following ability:"
    "<br><br><b>Transhuman Perception:</b> In your Shooting phase, this unit can select one "
    "visible enemy unit within 12\". That enemy unit is detected. While a unit is detected, "
    "that unit has +3\" detection range.")
enh("fp11e-spacemarines-subversion-e1", "subversion-assets", "Subversion Assets",
    "Shroud Field", "PHOBOS model only. This model has Lone Operative and Stealth.")
enh("fp11e-spacemarines-subversion-e2", "subversion-assets", "Subversion Assets",
    "Death in the Dark",
    "INFANTRY PHOBOS unit only. This unit's attacks that target a hidden unit have "
    "+1 to Hit rolls.")
strat("fp11e-spacemarines-subversion-s1", "Subversion Assets", "适应作战", "Adaptive Operations",
      "Shooting phase",
      "<b>WHEN:</b> Your Shooting phase, when a friendly PHOBOS/SCOUT SQUAD unit starts an action."
      "<br><br><b>TARGET:</b> That PHOBOS/SCOUT SQUAD unit.<br><br><b>EFFECT:</b> That action does "
      "not prevent your unit from being eligible to shoot.")
strat("fp11e-spacemarines-subversion-s2", "Subversion Assets", "暗影狙杀", "Strike from the Shadows",
      "Shooting phase",
      "<b>WHEN:</b> Your Shooting phase, when a friendly PHOBOS/SCOUT SQUAD unit has shot."
      "<br><br><b>TARGET:</b> That PHOBOS/SCOUT SQUAD unit.<br><br><b>EFFECT:</b> Those ranged "
      "attacks do not prevent your unit from being hidden.")
strat("fp11e-spacemarines-subversion-s3", "Subversion Assets", "潜行阵位", "Cloaked Position",
      "Movement phase",
      "<b>WHEN:</b> Start of your opponent's Movement phase.<br><br><b>TARGET:</b> One friendly "
      "unengaged PHOBOS/SCOUT SQUAD unit.<br><br><b>EFFECT:</b> Your unit has -3\" detection range "
      "until the end of the turn.")

# ── Bastion Task Force：漏录的 Angels Defiant（DB id 序缺 006）──────────
strat("000010677006", "Bastion Task Force", "天使不屈", "Angels Defiant", "Fight phase",
      "<b>WHEN:</b> Your opponent's Shooting phase or the Fight phase, just after an enemy unit has "
      "selected its targets.<br><br><b>TARGET:</b> One ADEPTUS ASTARTES Battleline unit from your "
      "army that was selected as the target of one or more of the attacking unit's attacks.<br><br>"
      "<b>EFFECT:</b> Until the end of the phase, each time an attack targets your unit, if the "
      "Strength characteristic of that attack is greater than the Toughness characteristic of your "
      "unit, subtract 1 from the Wound roll.", fp=FS_GAP)

# 追加到 fp_rules_patches.json
path = Path("db_compile/fp_rules_patches.json")
data = json.loads(path.read_text(encoding="utf-8"))
existing_ids = {ins["values"]["id"] for ins in data["inserts"]}
added = 0
for ins in inserts:
    if ins["values"]["id"] in existing_ids:
        print("SKIP existing:", ins["values"]["id"])
        continue
    data["inserts"].append(ins)
    added += 1
data["_comment"] += ("｜P7-PR20 Space-Marines 追加（2026-07-20）：inserts +13 —— 2 新迷你分队"
    "（Fulguris Task Force 天雷突袭 / Subversion Assets 无所遁形，各 1 规则 + 2 增强 + 3 战略，"
    "id 前缀 fp11e-spacemarines-）+ Bastion Task Force 漏录的 Angels Defiant 战略"
    "（DB id 序 002-005,007 缺 006，补回 000010677006）。11 现有分队"
    "（Armoured Speartip→Reclamation Force + Librarius Conclave）文本与 11 版 FP 逐字一致"
    "（Wahapedia 已滚入），零 text_patches/零 deactivations/零 fp_errata。")
path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"appended {added} inserts; total now {len(data['inserts'])}")
