"""顶层编排（P4-d/e）：simulate 单向 + simulate_matchup 串行幸存反打。

依赖 sequence（掷骰）+ report（聚合）+ context（清单）；装载/组装在 profile/assembly。
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from engines.simulator.contracts import (
    AttackerProfile,
    SimReport,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.context import STANDARD_BIAS, build_not_modeled, collect_effect_reporting
from engines.simulator.report import build_report
from engines.simulator.sequence import run_sequence


def simulate(
    attacker: AttackerProfile,
    target: TargetProfile,
    stance: Stance,
    n: int = 10000,
    seed: int = 1234,
    points: Optional[int] = None,
    include_bias: bool = True,
) -> SimReport:
    """单向：attacker 打 target 一次攻击序列 × N，返回聚合报告。"""
    raw = run_sequence(attacker, target, stance, n=n, seed=seed)
    modeled, _annotated, _unparsed = collect_effect_reporting(attacker)
    not_modeled = build_not_modeled(attacker, target)
    return build_report(
        raw, points=points, modeled_effects=modeled, not_modeled=not_modeled,
        bias_notes=list(STANDARD_BIAS) if include_bias else [],
    )


def _scale_loadout(attacker: AttackerProfile, survivors: int) -> AttackerProfile:
    """把攻方 loadout 的武器数按幸存比例缩放（串行幸存反打的近似，已进 bias_notes）。"""
    if attacker.models <= 0:
        return replace(attacker, models=0, loadout=())
    ratio = survivors / attacker.models
    scaled = []
    for w in attacker.loadout:
        c = max(0, round(w.count * ratio))
        if c > 0:
            scaled.append(replace(w, count=c))
    return replace(attacker, models=survivors, loadout=tuple(scaled))


def simulate_matchup(
    a_attacker: AttackerProfile,
    b_target: TargetProfile,
    b_attacker: AttackerProfile,
    a_target: TargetProfile,
    stance_forward: Stance,
    stance_reverse: Stance,
    n: int = 10000,
    seed: int = 1234,
    points_a: Optional[int] = None,
    points_b: Optional[int] = None,
) -> SimReport:
    """『A 冲 B 值不值』：A→B 正打，再让 B 的**幸存模型**反打 A（reverse 字段）。

    spec 第八节：串行幸存反打去偏——守方不满编反打，而是扣掉被 A 击杀数后反打。
    """
    forward = simulate(a_attacker, b_target, stance_forward, n=n, seed=seed,
                       points=points_a)

    survivors = max(0, b_target.models - int(round(forward.expected_kills)))
    forward.bias_notes.append(
        f"反打基于 B 期望幸存 {survivors}/{b_target.models} 个模型（A 期望击杀 "
        f"{forward.expected_kills:.2f}）")

    if survivors > 0 and b_attacker.loadout:
        b_surv = _scale_loadout(b_attacker, survivors)
        if b_surv.loadout:
            forward.reverse = simulate(b_surv, a_target, stance_reverse,
                                       n=n, seed=seed + 1, points=points_b)
    return forward
