"""装配层（C1）：把"选项池"武器表 + 模型数文本组装成可开火的 AttackerProfile。

数据现实（评审 C1）：weapons 表是**无数量、无归属的选项池**（Warboss 列 5 把互斥武器），
单位模型数只以自由文本存 points_json.items[].desc（"10 models"）。故本层：
  · parse_model_tiers：从 points desc 解析每档模型数（干净可测）
  · assemble_attacker：给定手动 loadout → 组装 AttackerProfile；未给 loadout → 返回
    ambiguous + 武器池，让调用方选（P4 不猜默认装配，见 spec headline 收敛）。

2026-07-25 修：武器池按**阶段**收窄（`usable_in_phase`）。"不猜默认装配"的理由是选项池
含互斥选项——本阶段可开火武器只剩 1 把时并无选项，逼用户装配等于让他"选唯一项"，且
射击阶段列出近战武器会诱导出全 0 报告。故：
  · 该阶段 0 把可开火 → no_phase_weapon（该切阶段，不是该装配）
  · 该阶段 1 把可开火 → auto_assembled 直接装配（count=模型数），note 披露此假设
  · ≥2 把 → 照旧 ambiguous，且 weapon_pool 只给该阶段能用的
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


def usable_in_phase(weapons, phase: Optional[str]) -> List[WeaponProfile]:
    """该阶段真能开火的武器（melee→近战 / shooting→远程）；phase 未给则原样返回。

    装配层不按阶段滤武器、序列层才滤——纯近战 loadout 打射击阶段会装配成功却 0 攻击
    （P6 军表侧踩过同一个陷阱）。本函数是装配层/军表点评/模拟入口共用的判据。
    """
    if phase not in ("shooting", "melee"):
        return list(weapons)
    want_melee = phase == "melee"
    return [w for w in weapons if w.is_melee == want_melee]


@dataclass
class AssemblyResult:
    """装配结果。ambiguous=True 时 attacker=None，需调用方据 weapon_pool 指定 loadout。"""
    canonical_id: str
    name_en: str
    models: int
    tiers: List[Dict]
    weapon_pool: List[WeaponProfile]     # 按 phase 收窄后的可选池（调用方该从这里选）
    attacker: Optional[AttackerProfile] = None
    ambiguous: bool = False
    note: str = ""
    errors: List[str] = field(default_factory=list)
    full_pool: List[WeaponProfile] = field(default_factory=list)  # 未按阶段过滤的全池
    no_phase_weapon: bool = False        # 该阶段无可开火武器（该切阶段，不是该装配）
    auto_assembled: bool = False         # 该阶段唯一武器 → 自动装配（note 披露件数假设）


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

    pool_phase = usable_in_phase(pool, phase)

    base = AssemblyResult(
        canonical_id=header.canonical_id, name_en=header.name_en,
        models=resolved_models, tiers=tiers, weapon_pool=pool_phase,
        full_pool=pool)

    def _mk_attacker(chosen: List[WeaponProfile]) -> AttackerProfile:
        return AttackerProfile(
            canonical_id=header.canonical_id, name_en=header.name_en,
            name_zh=header.name_zh, models=resolved_models,
            loadout=tuple(chosen), keywords=header.keywords)

    if not loadout:
        here = "近战" if phase == "melee" else "射击"
        other = "射击" if phase == "melee" else "近战"
        if not pool:
            base.ambiguous = True
            base.note = "该单位武器表为空（数据缺口），无法装配"
            return base
        if not pool_phase:
            # 全池非空但本阶段无可开火武器：要求装配是无解的（填任何数量都 0 攻击）
            base.ambiguous = True
            base.no_phase_weapon = True
            base.note = (
                f"该单位在{here}阶段没有可开火武器——武器池里只有{other}武器"
                f"（{'、'.join(w.name_en for w in pool[:6])}）。请切到{other}阶段再模拟。")
            return base
        if len(pool_phase) == 1:
            # 该阶段只有一把武器 ⇒ 无互斥选项可选，逼用户装配纯属卡住；件数按满编假设并披露
            only = pool_phase[0]
            base.attacker = _mk_attacker([replace(only, count=resolved_models)])
            base.auto_assembled = True
            base.note = (
                f"{here}阶段武器池只有 1 把（{only.name_en}），无可选项 → 已按每个模型各带"
                f" 1 件自动装配（{resolved_models} 件）；要改件数请显式指定 loadout")
            return base
        base.ambiguous = True
        base.note = ("武器表是选项池（含互斥选项），P4 不猜默认装配；"
                     "请据 weapon_pool 指定 loadout=[(武器名,数量),...]")
        if len(pool_phase) < len(pool):
            base.note += f"（已按{here}阶段过滤，另有 {len(pool) - len(pool_phase)} 把{other}武器）"
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
        n = int(count)
        if n <= 0:
            # 件数 ≤0 必须显式失败。sequence.py 的引擎层对 count<=0 是**对的**
            # （诚实地不开火，非 max(...,1) 幽灵开火），于是"0 件"会一路装配成功、
            # 端出一份 ok=True + expected_damage=0.0 + warning=None 的**假成功**报告，
            # 模型据此答"该单位期望伤害为 0"——每层都是成功路径的错答。
            # loadout 由 LLM 从自然语言现编（"不带爆弹枪"很可能被写成 0），必须拦在这里。
            # 走既有 errors → ambiguous 通道，不新增返回形态、不动引擎。
            base.errors.append(
                f"武器 {w.name_en!r} 的件数 {n} ≤ 0，无法模拟"
                f"（0 件 = 不开火，只会得到期望伤害恒为 0 的空报告）；"
                f"要排除这把武器就别把它写进 loadout")
            continue
        chosen.append(replace(w, count=n))

    if base.errors:
        base.ambiguous = True
        base.note = "loadout 不可用（武器名无法匹配或件数非法），见 errors"
        return base

    base.attacker = _mk_attacker(chosen)
    base.note = "ok"
    return base
