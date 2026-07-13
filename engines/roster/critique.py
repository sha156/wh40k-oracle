"""engines/roster/critique.py — 军表点评（P6-PR2）。

接模拟器给「这套配置强度评估」：每个装配好的单位 → 打 4 个合成典型目标（GEQ 杂兵 /
MEQ 战锤 / TEQ 终结者 / VEH 载具）→ 每 100 点期望伤害（性价比）+ 军队级短板提示。

诚实红线：
- 点评**必须有 loadout**（几乎所有单位是多武器选项池，不猜默认装配）——无 loadout 的单位
  surface「需装配，未评估」，不瞎估。
- 合成目标是标准 stat 假人（非真单位），只测「对该防御档的输出」，不含阵营规则/技能。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from engines.roster.contracts import Roster
from engines.roster.points import recompute

# ── 合成典型目标（标准防御档假人；models 给足以吸收伤害不溢出）─────
_TARGETS_SPEC = [
    # key,  label,      t,  sv, invuln, w,  oc, models, keywords
    ("geq", "杂兵(GEQ)", 3, 5, None, 1, 2, 20, ("INFANTRY",)),
    ("meq", "战锤(MEQ)", 4, 3, None, 2, 2, 20, ("INFANTRY",)),
    ("teq", "终结者(TEQ)", 5, 2, 4, 3, 1, 10, ("INFANTRY",)),
    ("veh", "载具(VEH)", 10, 3, None, 12, 4, 3, ("VEHICLE",)),
]


def _archetypes():
    from engines.simulator.contracts import TargetProfile
    return [(key, label, TargetProfile(
        canonical_id=f"_arch_{key}", name_en=label, name_zh=None,
        models=models, t=t, sv=sv, invuln=inv, w=w, oc=oc,
        keywords=frozenset(kw)))
        for key, label, t, sv, inv, w, oc, models, kw in _TARGETS_SPEC]


@dataclass(frozen=True)
class TargetScore:
    key: str
    label: str
    expected_damage: float
    damage_per_100: Optional[float]     # 每 100 点期望伤害（无点数时 None）


@dataclass(frozen=True)
class UnitAssessment:
    canonical_id: str
    name_en: str
    points: Optional[int]
    assessed: bool
    phase: Optional[str] = None          # 评估所用阶段
    scores: Tuple[TargetScore, ...] = ()
    note: str = ""                       # 未评估原因（诚实 surface）


@dataclass(frozen=True)
class CritiqueReport:
    total_points: int
    assessments: Tuple[UnitAssessment, ...]
    summary: Tuple[str, ...] = ()        # 军队级观察
    not_modeled: Tuple[str, ...] = ()    # 诚实披露


def _assemble_best_phase(db_path, unit):
    """按 unit.loadout 试装配（先射击后近战），返回 (phase, attacker) 或 (None, None)。"""
    from engines.simulator.assembly import assemble_attacker
    loadout = [(str(w), int(c)) for w, c in unit.loadout]
    for phase in ("shooting", "melee"):
        asm = assemble_attacker(db_path, unit.canonical_id,
                                models=unit.models, loadout=loadout, phase=phase)
        if asm and not asm.ambiguous and asm.attacker is not None:
            return phase, asm.attacker
    return None, None


def _assess_unit(db_path, unit, n: int, seed: int) -> UnitAssessment:
    if not unit.loadout:
        return UnitAssessment(
            unit.canonical_id, unit.name_en, unit.points, assessed=False,
            note="需装配（多武器选项池，未指定 loadout → 不评估，不瞎估）")
    phase, attacker = _assemble_best_phase(db_path, unit)
    if attacker is None:
        return UnitAssessment(
            unit.canonical_id, unit.name_en, unit.points, assessed=False,
            note="装配失败（loadout 与武器池不匹配 / 该阶段无武器）")

    from engines.simulator.contracts import Stance
    from engines.simulator.engine import simulate
    scores: List[TargetScore] = []
    for key, label, target in _archetypes():
        rep = simulate(attacker, target, Stance(phase=phase), n=n, seed=seed,
                       points=unit.points, include_bias=False)
        dmg = round(rep.expected_damage, 2)
        per100 = (round(dmg / unit.points * 100, 2)
                  if unit.points else None)
        scores.append(TargetScore(key, label, dmg, per100))
    return UnitAssessment(
        unit.canonical_id, unit.name_en, unit.points, assessed=True,
        phase=phase, scores=tuple(scores))


def _build_summary(assessments: Tuple[UnitAssessment, ...]) -> Tuple[str, ...]:
    out: List[str] = []
    unassessed = [a for a in assessments if not a.assessed]
    if unassessed:
        out.append(f"{len(unassessed)}/{len(assessments)} 单位未评估（需先装配武器）")
    done = [a for a in assessments if a.assessed]
    if not done:
        return tuple(out)
    # 反装甲短板：所有单位对 VEH 的每 100 点伤害
    def veh100(a):
        s = next((s for s in a.scores if s.key == "veh"), None)
        return s.damage_per_100 if s and s.damage_per_100 is not None else None
    anti_tank = [(a.name_en, veh100(a)) for a in done if veh100(a) is not None]
    if anti_tank:
        best = max(anti_tank, key=lambda x: x[1])
        out.append(f"反装甲最强：{best[0]}（对 VEH 每 100 点 {best[1]} 伤）")
        if best[1] < 3.0:
            out.append("⚠️ 全军对载具每 100 点伤害偏低，反装甲可能不足")
    return tuple(out)


_NOT_MODELED = (
    "合成目标为标准防御档假人，不含阵营规则/军队规则/分队加成",
    "单位技能/光环/CP 战略未计入（沿用模拟器建模边界）",
    "每单位按其 loadout 独立评估，未计协同（如指挥官挂载增益）",
)


def critique(db_path, roster: Roster, n: int = 1000, seed: int = 1234) -> CritiqueReport:
    """军表 → 强度点评报告。先 recompute（点数供性价比），逐单位打典型目标。"""
    priced = recompute(db_path, roster)
    assessments = tuple(_assess_unit(db_path, u, n, seed) for u in priced.units)
    total = sum(u.points or 0 for u in priced.units)
    return CritiqueReport(
        total_points=total, assessments=assessments,
        summary=_build_summary(assessments), not_modeled=_NOT_MODELED)
