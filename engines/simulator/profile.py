"""从 wh40k.sqlite 装载 WeaponProfile / TargetProfile / 单位头信息（P4-a）。

本模块是唯一 import sqlite3 的地方（连同 assembly.py）；引擎 sequence.py/report.py
只吃本模块产出的干净 contracts。只读，不改库。复用 db_compile.datasheet 的行形态。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engines.simulator.contracts import AbilityRecord, TargetProfile, WeaponProfile
from engines.simulator.parse import (
    expected_dice,
    norm_stat_int,
    parse_ap,
    parse_dice,
    tokenize_keywords,
)


@dataclass(frozen=True)
class UnitHeader:
    canonical_id: str
    name_en: str
    name_zh: Optional[str]
    points_json: Optional[str]
    keywords: frozenset
    model_rows: Tuple[Dict, ...]     # 每个 dict：name/m/t/sv/invuln/w/ld/oc（数值已归一）


def _keywords_frozenset(keywords_json: Optional[str]) -> frozenset:
    if not keywords_json:
        return frozenset()
    try:
        data = json.loads(keywords_json)
    except (json.JSONDecodeError, TypeError):
        return frozenset()
    if not isinstance(data, dict):
        return frozenset()
    kws = list(data.get("keywords") or []) + list(data.get("faction_keywords") or [])
    return frozenset(str(k).strip().lower() for k in kws if k)


def _row_to_model(row: sqlite3.Row) -> Dict:
    name, m, t, sv, invuln, w, ld, oc = row
    return {
        "name": name,
        "m": norm_stat_int(m),
        "t": norm_stat_int(t),
        "sv": norm_stat_int(sv),
        "invuln": norm_stat_int(invuln),   # '-' → None（无无效保护）
        "w": norm_stat_int(w),
        "ld": norm_stat_int(ld),
        "oc": norm_stat_int(oc),
    }


def _row_to_weapon(row: sqlite3.Row) -> WeaponProfile:
    from engines.simulator.keywords import build_weapon_effects  # 延迟避免循环

    name_zh, name_en, rng, a, bs_ws, s, ap, d, kj = row
    s_expr = parse_dice(s)
    # 契约 strength:int；3/9307 把武器 S 是骰子（2D6/D6+6），用期望值近似（确定性、有记录）
    strength = s_expr.k if s_expr.is_constant else int(round(expected_dice(s_expr)))
    parsed_kw, _unknown = tokenize_keywords(kj)
    effects, _modeled, _annotations, _unparsed = build_weapon_effects(tuple(parsed_kw))
    return WeaponProfile(
        name_zh=name_zh,
        name_en=name_en,
        range=rng or "",
        attacks=parse_dice(a),
        bs_ws=norm_stat_int(bs_ws),        # N/A → None（自动命中）
        strength=strength,
        ap=parse_ap(ap),
        damage=parse_dice(d),
        effects=effects,
        raw_keywords=tuple(parsed_kw),
    )


def load_weapon_pool(db_path, unit_id: str) -> List[WeaponProfile]:
    """单位的全部武器（选项池，非已装配 loadout）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name_zh, name_en, range, a, bs_ws, s, ap, d, keywords_json "
            "FROM weapons WHERE unit_id = ? ORDER BY id", (unit_id,)
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_weapon(r) for r in rows]


def load_abilities(db_path, unit_id: str) -> Tuple[AbilityRecord, ...]:
    """单位挂载的技能行（P5-a）：abilities 表 owner_id 命中，正文清洗成纯文本。

    只读，供分类披露；不自动施加任何效果（见 abilities.py 裁决）。
    """
    from engines.simulator.abilities import clean_text  # 延迟避免循环
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name_en, text_zh FROM abilities WHERE owner_id = ? ORDER BY id",
            (unit_id,)).fetchall()
    finally:
        conn.close()
    return tuple(AbilityRecord(name_en=(r[0] or ""), text=clean_text(r[1]))
                 for r in rows)


def load_faction_options(db_path, unit_id: str) -> Dict:
    """守方所属阵营的分队名清单（P5-c surface-don't-fake）：只列名，不施加任何规则。

    告诉用户"你这支单位的阵营有这些分队/军队规则我没建模"，是诚实披露而非假装计入。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        u = conn.execute("SELECT faction_id FROM units WHERE id = ?", (unit_id,)).fetchone()
        if not u or not u[0]:
            return {"faction_id": None, "faction_name": None, "detachments": []}
        fid = u[0]
        fac = conn.execute("SELECT name FROM factions WHERE id = ?", (fid,)).fetchone()
        dets = conn.execute(
            "SELECT DISTINCT name_en FROM detachments WHERE faction = ? ORDER BY name_en",
            (fid,)).fetchall()
    finally:
        conn.close()
    # 'KEYWORDS' 等抓取噪声名剔除
    names = [d[0] for d in dets if d[0] and d[0].upper() != "KEYWORDS"]
    return {"faction_id": fid, "faction_name": (fac[0] if fac else fid),
            "detachments": names}


def load_unit_header(db_path, unit_id: str) -> Optional[UnitHeader]:
    conn = sqlite3.connect(str(db_path))
    try:
        u = conn.execute(
            "SELECT name_en, name_zh, points_json, keywords_json FROM units WHERE id = ?",
            (unit_id,)).fetchone()
        if u is None:
            return None
        name_en, name_zh, points_json, keywords_json = u
        model_rows = tuple(
            _row_to_model(r) for r in conn.execute(
                "SELECT name, m, t, sv, invuln, w, ld, oc FROM models WHERE unit_id = ?",
                (unit_id,)))
    finally:
        conn.close()
    return UnitHeader(
        canonical_id=unit_id, name_en=name_en, name_zh=name_zh,
        points_json=points_json, keywords=_keywords_frozenset(keywords_json),
        model_rows=model_rows)


def load_target(db_path, unit_id: str, models: Optional[int] = None,
                options: Optional[Dict] = None) -> Optional[TargetProfile]:
    """守方 TargetProfile。混编单位（多 model 行）取首行为主行，全部行存 model_rows 供上层警示。"""
    from engines.simulator.assembly import default_model_count  # 延迟避免循环

    header = load_unit_header(db_path, unit_id)
    if header is None or not header.model_rows:
        return None
    primary = header.model_rows[0]
    resolved_models = models if models is not None else default_model_count(header.points_json)
    return TargetProfile(
        canonical_id=header.canonical_id,
        name_en=header.name_en,
        name_zh=header.name_zh,
        models=resolved_models or 1,
        t=primary["t"] or 1,
        sv=primary["sv"] or 7,
        invuln=primary["invuln"],
        w=primary["w"] or 1,
        oc=primary["oc"] or 0,
        keywords=header.keywords,
        model_rows=header.model_rows,
        abilities=load_abilities(db_path, unit_id),
    )
