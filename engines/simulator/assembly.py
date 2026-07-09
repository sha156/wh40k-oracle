"""装配层（C1）：把"选项池"武器表 + 模型数文本组装成可开火的 AttackerProfile。

数据现实（评审 C1）：weapons 表是**无数量、无归属的选项池**（Warboss 列 5 把互斥武器），
单位模型数只以自由文本存 points_json.items[].desc（"10 models"）。故本层：
  · parse_model_tiers：从 points desc 解析每档模型数（干净可测）
  · assemble_attacker：给定手动 loadout → 组装 AttackerProfile；未给 loadout → 返回
    ambiguous + 武器池，让调用方选（P4 不猜默认装配，见 spec headline 收敛）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

from engines.simulator.contracts import AttackerProfile, WeaponProfile
from engines.simulator.profile import load_unit_header, load_weapon_pool

_MODELS_RE = re.compile(r"(\d+)\s*models?", re.IGNORECASE)


def parse_model_tiers(points_json: Optional[str]) -> List[Dict]:
    """points_json.items[].desc（"10 models" / "1 model"）→ [{"models":int,"cost":int}]。

    按模型数升序；无法解析模型数的档跳过（不编造）。
    """
    if not points_json:
        return []
    try:
        data = json.loads(points_json)
    except (json.JSONDecodeError, TypeError):
        return []
    tiers: List[Dict] = []
    for it in data.get("items") or []:
        m = _MODELS_RE.search(str(it.get("desc") or ""))
        if not m:
            continue
        cost = it.get("cost")
        tiers.append({"models": int(m.group(1)),
                      "cost": cost if isinstance(cost, int) else None})
    tiers.sort(key=lambda x: x["models"])
    return tiers


def default_model_count(points_json: Optional[str]) -> Optional[int]:
    """默认满编模型数 = 最小档模型数（与 calc_points 取 min 档一致）。"""
    tiers = parse_model_tiers(points_json)
    return tiers[0]["models"] if tiers else None


@dataclass
class AssemblyResult:
    """装配结果。ambiguous=True 时 attacker=None，需调用方据 weapon_pool 指定 loadout。"""
    canonical_id: str
    name_en: str
    models: int
    tiers: List[Dict]
    weapon_pool: List[WeaponProfile]
    attacker: Optional[AttackerProfile] = None
    ambiguous: bool = False
    note: str = ""
    errors: List[str] = field(default_factory=list)


def _match_weapon(pool: List[WeaponProfile], name: str,
                  phase: Optional[str]) -> Tuple[Optional[WeaponProfile], List[WeaponProfile]]:
    """按名（大小写不敏感）匹配武器池；同名多 profile 时按 phase(melee/ranged) 收窄。"""
    hits = [w for w in pool if w.name_en.strip().lower() == name.strip().lower()]
    if len(hits) > 1 and phase in ("shooting", "melee"):
        want_melee = phase == "melee"
        narrowed = [w for w in hits if w.is_melee == want_melee]
        if narrowed:
            hits = narrowed
    if len(hits) == 1:
        return hits[0], []
    return None, hits


def assemble_attacker(
    db_path,
    unit_id: str,
    models: Optional[int] = None,
    loadout: Optional[List[Tuple[str, int]]] = None,
    phase: Optional[str] = None,
) -> Optional[AssemblyResult]:
    """组装攻方单位。查不到单位返回 None（诚实报缺）。

    loadout：[(武器名, 持此武器的模型/武器数), ...]。未给 → ambiguous=True + 武器池。
    """
    header = load_unit_header(db_path, unit_id)
    if header is None:
        return None
    pool = load_weapon_pool(db_path, unit_id)
    tiers = parse_model_tiers(header.points_json)
    resolved_models = (models if models is not None
                       else (tiers[0]["models"] if tiers else 1))

    base = AssemblyResult(
        canonical_id=header.canonical_id, name_en=header.name_en,
        models=resolved_models, tiers=tiers, weapon_pool=pool)

    if not loadout:
        base.ambiguous = True
        base.note = ("武器表是选项池（含互斥选项），P4 不猜默认装配；"
                     "请据 weapon_pool 指定 loadout=[(武器名,数量),...]")
        return base

    chosen: List[WeaponProfile] = []
    for name, count in loadout:
        w, candidates = _match_weapon(pool, name, phase)
        if w is None:
            if candidates:
                base.errors.append(
                    f"武器名 {name!r} 命中 {len(candidates)} 个同名 profile，"
                    f"请用 phase 或精确 range 区分")
            else:
                base.errors.append(f"武器名 {name!r} 不在该单位武器池")
            continue
        chosen.append(replace(w, count=int(count)))

    if base.errors:
        base.ambiguous = True
        base.note = "loadout 存在无法匹配的武器，见 errors"
        return base

    base.attacker = AttackerProfile(
        canonical_id=header.canonical_id, name_en=header.name_en,
        name_zh=header.name_zh, models=resolved_models,
        loadout=tuple(chosen), keywords=header.keywords)
    base.note = "ok"
    return base
