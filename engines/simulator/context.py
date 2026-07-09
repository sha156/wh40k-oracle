"""SimContext 组装 + 诚实声明清单收集（P4-d）。

P4 只做：把武器词条（modeled / annotated / unparsed）与标准系统性偏差汇成清单，
供报告层 not_modeled / bias_notes 如实声明。faction/detachment join 是 P5 占位。
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from engines.simulator.contracts import (
    AttackerProfile,
    SimContext,
    Stance,
    TargetProfile,
)
from engines.simulator.keywords import build_weapon_effects

# spec 第八节：P4 必须写进 bias_notes 的系统性偏差方向（诚实优先）
STANDARD_BIAS: Tuple[str, ...] = (
    "守方反打用『期望幸存数』近似（非逐迭代联动），略高估守方反伤",
    "冲锋成功率未建模：默认冲锋必接触，未算 2D6 冲锋距离检定失败 → 高估『冲』的价值",
    "Fights First / 交替 / interrupt 未建模（P5 战斗顺序判定器）",
    "士气/Battle-shock、接战范围/视线/射程可达性、守方最优分配均未建模（守方按掷骰顺序固定分配）",
    "交换比按『击杀模型→点数』折算，多耐伤单位被打残未死的部分点损失不计入",
)

# abilities 表 3677 条全 not_modeled（spec 第三节）
_ABILITIES_NOTE = "阵营技能/军队规则/分队规则/CP 战略未建模（abilities 全表 not_modeled，P5 主体）"


def collect_effect_reporting(
    attacker: AttackerProfile,
) -> Tuple[List[str], List[str], List[str]]:
    """遍历攻方 loadout，汇总 (modeled 词条, 标注类未建模, unparsed 低频)。去重保序。"""
    modeled: List[str] = []
    annotated: List[str] = []
    unparsed: List[str] = []
    for w in attacker.loadout:
        _eff, mod, ann, unp = build_weapon_effects(w.raw_keywords)
        modeled.extend(mod)
        annotated.extend(ann)
        unparsed.extend(unp)

    def _dedup(seq: Sequence[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return _dedup(modeled), _dedup(annotated), _dedup(unparsed)


def build_not_modeled(attacker: AttackerProfile, target: TargetProfile) -> List[str]:
    """本次模拟已知但未计入的机制清单（词条标注 + 低频词条 + abilities + 混编警示）。"""
    _modeled, annotated, unparsed = collect_effect_reporting(attacker)
    notes: List[str] = list(annotated)
    if unparsed:
        notes.append("未识别低频专属词条（记日志、未建模）：" + "、".join(sorted(set(unparsed))))
    notes.append(_ABILITIES_NOTE)
    if len(target.model_rows) > 1:
        notes.append(f"守方为混编单位（{len(target.model_rows)} 种模型行），"
                     f"本次按主模型行 T{target.t}/Sv{target.sv}/W{target.w} 近似")
    return notes


def build_context(
    attacker: AttackerProfile,
    target: TargetProfile,
    stance: Stance,
) -> SimContext:
    """组装 SimContext（P4：效果通道 + 诚实清单；faction/detachment 留 P5 空位）。"""
    return SimContext(
        attacker=attacker,
        target=target,
        stance=stance,
        effects=(),
        toggles_available=(),
        not_modeled=tuple(build_not_modeled(attacker, target)),
    )
