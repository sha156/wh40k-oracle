"""SimContext 组装 + 诚实声明清单收集（P4-d）。

P4 只做：把武器词条（modeled / annotated / unparsed）与标准系统性偏差汇成清单，
供报告层 not_modeled / bias_notes 如实声明。faction/detachment join 是 P5 占位。
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from engines.simulator.abilities import AbilityClassification, classify_records
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
    "先攻方已按 fight_order 判定（冲锋/Fights First/Fights Last 抵消）；但同一步的逐单位交替选取"
    "与 Counter-offensive 插队仍以『整单位先手→幸存反打』近似",
    "士气/Battle-shock、接战范围/视线/射程可达性、守方最优分配均未建模（守方按掷骰顺序固定分配）",
    "交换比按『击杀模型→点数』折算，多耐伤单位被打残未死的部分点损失不计入",
)

# P4 遗留：守方无挂载技能行时的兜底声明（P5-a 起优先用逐条精确分类，见 build_not_modeled）
_ABILITIES_NOTE = "阵营技能/军队规则/分队规则/CP 战略未建模（abilities 全表 not_modeled）"


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


def classify_target_abilities(target: TargetProfile) -> AbilityClassification:
    """守方挂载技能 → 分类（P5-a）。无技能行时返回空分类。"""
    return classify_records(tuple(target.abilities))


def build_toggles_available(target: TargetProfile) -> Tuple[Tuple[str, str, bool], ...]:
    """检测到的守方防守技能提示（名字, 一句话, 是否已解析出参数）——只列名不施加。

    如实说明（评审 M）：这里没有"开关即生效"的接线（留待 P7），用户需在 options/面板
    的手动开关里自行填数，引擎才会计入。
    """
    return tuple(classify_target_abilities(target).toggle_summaries())


def build_not_modeled(attacker: AttackerProfile, target: TargetProfile) -> List[str]:
    """本次模拟已知但未计入的机制清单（词条标注 + 低频词条 + 精确技能分类 + 混编警示）。"""
    _modeled, annotated, unparsed = collect_effect_reporting(attacker)
    notes: List[str] = list(annotated)
    if unparsed:
        notes.append("未识别低频专属词条（记日志、未建模）：" + "、".join(sorted(set(unparsed))))

    # P5-a：守方技能逐条精确分类披露，取代 P4 那句笼统声明
    cls = classify_target_abilities(target)
    if cls.total > 0:
        notes.extend(cls.not_modeled_by_category())
        toggles = cls.toggle_summaries()
        if toggles:
            names = "、".join(f"{n}（{d}）" for n, d, _ in toggles)
            notes.append("检测到可建模防守技能（仅提示，未计入；需在手动开关自行填数，"
                         "自动接线留待 P7）：" + names)
    else:
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
    """⚠ 未接入执行链路（P5 遗留占位，P8 FastAPI 预留）；修改此处不影响模拟结果，
    真实 Effect 通道在 sequence._gather_params。

    组装 SimContext（P5-a：效果通道 + 精确技能分类 + 防守技能提示列名）。"""
    return SimContext(
        attacker=attacker,
        target=target,
        stance=stance,
        effects=(),
        toggles_available=build_toggles_available(target),
        not_modeled=tuple(build_not_modeled(attacker, target)),
    )
