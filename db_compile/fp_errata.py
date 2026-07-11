"""fp_errata：Faction Pack 兵牌级真漂移外科补丁层（S4 落账）。

**为什么这层很薄**：29 包 481 张重印数据表 × 17138 个属性/武器单元格全量 A/B 核对
后，库已 98.7%/99.9% 与官方 11 版重印一致——Wahapedia 早把 6 月 Faction Pack 勘误
并进了主数据集，我们 7 月初下载的 CSV 就是打过补丁的 11 版。所以**不做冗余整行覆盖**
（那会拿解析结果去改本已正确的数据，一旦解析有误反把对的改错）。只补两类真·漂移：

  1. stat_patches：库仍是十版值的少数格子。最大一类是 25 台飞机的移动值——Wahapedia
     没套用 11 版飞机固定移动重做，库仍是十版 `20+"`；外加 3 台 FW 单位真漂移
     （War Dog Moirax / Land Speeder / Venerable Dreadnought，均被 BSData 交叉校验佐证）。
  2. new_units：11 版新增、Wahapedia 尚无的单位（3 个兽人：Bigboss/Bannernob/
     Big Mek Dakkarig）。纯插入，不动既有行。

**防误覆盖守卫**：每条 stat_patch 带落账时的库现值 `from`。apply 前校验库现值==from
才改；已等于 to 幂等跳过；既非 from 也非 to（说明库被上游改过）→ 跳过并告警，绝不盲覆盖。
这样将来 Wahapedia 若自己补了这些值，本层自动让路而非制造冲突。

与 mfm_apply 同理：build 重建整库会清掉本层，须在 build 之后重跑（已挂进
update.restore_authority_layers）。只改 models/weapons/units 结构表，不动检索层——
get_datasheet 直读库，无需重建 FAISS。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

# 只允许补这些属性字段（防止 field 名拼进 SQL 造成注入/写错列）
_STAT_FIELDS = {"m", "t", "sv", "w", "ld", "oc"}


def _guard_norm(v) -> str:
    """守卫用归一化：只去引号/寸号/空白，**保留 + 和 -**。

    关键：不能沿用 datasheet._norm_stat（它会剥掉 '+'），否则 '20+"'(from) 与
    '20"'(to) 都归一成 '20' 而无法区分，飞机移动补丁的 from/to 守卫会失效。
    """
    if v is None:
        return ""
    s = str(v).strip().lower()
    for j in ('"', "”", "“", "″", "′", "'", "寸", "吋", " "):
        s = s.replace(j, "")
    return s


def load_patches(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _apply_stat_patches(conn, patches: List[dict], report: Dict) -> None:
    for p in patches:
        field = p.get("field")
        uid = p.get("unit_id")
        if field not in _STAT_FIELDS or not uid:
            report["stat_invalid"].append(p)
            continue
        rows = conn.execute(
            f"SELECT rowid, {field} FROM models WHERE unit_id = ?", (uid,)).fetchall()
        if len(rows) != 1:
            # 单位不存在或多 model（本层只补单 model 单位）——不猜，记下来
            report["stat_skipped"].append(
                {**_slim(p), "reason": f"{len(rows)} model rows"})
            continue
        rowid, cur = rows[0]
        gc, gf, gt = _guard_norm(cur), _guard_norm(p.get("from")), _guard_norm(p.get("to"))
        if gc == gt:
            report["stat_already"] += 1            # 幂等：已是目标值
            continue
        if gc != gf:
            # 库现值既非 from 也非 to：上游动过，让路不盲覆盖
            report["stat_mismatch"].append(
                {**_slim(p), "db_now": cur})
            continue
        conn.execute(
            f"UPDATE models SET {field} = ? WHERE rowid = ?", (p["to"], rowid))
        report["stat_applied"] += 1
        report["stat_changes"].append(
            {**_slim(p), "from": cur, "to": p["to"]})


def _slim(p: dict) -> dict:
    return {"unit": p.get("unit"), "faction": p.get("faction"), "field": p.get("field")}


def _insert_new_units(conn, units: List[dict], report: Dict) -> None:
    for u in units:
        fac, name = u.get("faction"), u.get("name")
        exists = conn.execute(
            "SELECT id FROM units WHERE faction_id = ? AND name_en = ? COLLATE NOCASE",
            (fac, name)).fetchone()
        if exists:
            report["units_exist"].append(f"{fac}:{name}")
            continue
        uid = u["unit_id"]
        kw_json = json.dumps(
            {"keywords": u.get("keywords", []),
             "faction_keywords": u.get("faction_keywords", [])},
            ensure_ascii=False)
        # datasheets（保真骨架行）
        conn.execute(
            """INSERT OR REPLACE INTO datasheets
               (id, name, faction_id, source_id, legend, role, loadout,
                transport, virtual, leader_head, leader_footer,
                damaged_w, damaged_description, link)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, name, fac, u.get("src"), None, None, None,
             None, None, None, None, None, None, None))
        # units（语义视图，标 version=11e-fp 便于溯源/回归）
        conn.execute(
            """INSERT OR REPLACE INTO units
               (id, faction_id, name_en, name_zh, points_json, keywords_json, version)
               VALUES (?, ?, ?, NULL, NULL, ?, ?)""",
            (uid, fac, name, kw_json, u.get("version", "11e-fp")))
        for m in u.get("models", []):
            conn.execute(
                """INSERT INTO models (unit_id, name, m, t, sv, invuln, w, ld, oc, base)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (uid, m.get("name", name), m.get("m"), m.get("t"), m.get("sv"),
                 m.get("invuln") or None, m.get("w"), m.get("ld"), m.get("oc")))
        for i, w in enumerate(u.get("weapons", []), 1):
            conn.execute(
                """INSERT OR REPLACE INTO weapons
                   (id, unit_id, name_en, range, a, bs_ws, s, ap, d, keywords_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"{uid}_w{i}", uid, w.get("name"), w.get("range"), w.get("a"),
                 w.get("bs_ws"), w.get("s"), w.get("ap"), w.get("d"),
                 json.dumps(w.get("keywords", []), ensure_ascii=False)
                 if w.get("keywords") else None))
        report["units_inserted"].append(f"{fac}:{name}")


def apply_fp_errata(db_path, patches: dict) -> Dict:
    """应用 fp_errata 补丁到库，返回结构化报告（含逐条改动与告警）。"""
    report = {
        "stat_applied": 0, "stat_already": 0,
        "stat_changes": [], "stat_mismatch": [], "stat_skipped": [], "stat_invalid": [],
        "units_inserted": [], "units_exist": [],
    }
    conn = sqlite3.connect(str(db_path))
    try:
        _apply_stat_patches(conn, patches.get("stat_patches", []), report)
        _insert_new_units(conn, patches.get("new_units", []), report)
        conn.commit()
    finally:
        conn.close()
    return report


def apply_from_file(db_path, patches_path) -> Dict:
    return apply_fp_errata(db_path, load_patches(patches_path))
