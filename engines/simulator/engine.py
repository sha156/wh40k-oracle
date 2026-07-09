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


def _survivor_retaliation(
    forward: SimReport, defender_attacker: AttackerProfile, defender_models: int,
    attacker_as_target: TargetProfile, stance_reverse: Stance,
    n: int, seed: int, points: Optional[int], label: str,
) -> None:
    """把「守方幸存者反打」结果挂到 forward.reverse（就地）。"""
    survivors = max(0, defender_models - int(round(forward.expected_kills)))
    forward.bias_notes.append(
        f"反打基于 {label} 期望幸存 {survivors}/{defender_models} 个模型"
        f"（先手方期望击杀 {forward.expected_kills:.2f}）")
    if survivors > 0 and defender_attacker.loadout:
        surv = _scale_loadout(defender_attacker, survivors)
        if surv.loadout:
            forward.reverse = simulate(surv, attacker_as_target, stance_reverse,
                                       n=n, seed=seed + 1, points=points)


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
    a_fights_first: bool = False,
    a_fights_last: bool = False,
    b_fights_first: bool = False,
    b_fights_last: bool = False,
) -> SimReport:
    """『A 冲 B 值不值』：用 fight_order 判定先攻方，先手方满编打、后手方幸存者反打。

    P5-b：接入战斗顺序判定器（替代 P4 写死"A 先打"）。A 是发起/当前玩家（冲锋由
    stance_forward.charging 决定，冲锋必属当前玩家）；B 是守方。判定 B 先打时（A 未冲锋
    且 B 有 Fights First 等），A 以幸存者反打——返回的 forward 恒为「A→B」视角，
    但 A 的攻击强度按先攻顺序对应满编/幸存。
    """
    from engines.simulator.fight_order import FighterState, judge

    a_state = FighterState(a_attacker.name_en or "A", is_active_player=True,
                           charged=stance_forward.charging,
                           fights_first=a_fights_first, fights_last=a_fights_last)
    b_state = FighterState(b_attacker.name_en or "B", is_active_player=False,
                           charged=False, fights_first=b_fights_first,
                           fights_last=b_fights_last)
    verdict = judge(a_state, b_state)
    a_first = verdict.first_is_a          # 用侧标识，不比名字（镜像对局名字相同，见评审 CRITICAL#1）

    if a_first:
        # A 满编先打 B，B 幸存者反打 A（P4 常态）
        forward = simulate(a_attacker, b_target, stance_forward, n=n, seed=seed,
                           points=points_a)
        forward.bias_notes.append(f"先攻判定：{verdict.rationale}")
        _survivor_retaliation(forward, b_attacker, b_target.models, a_target,
                              stance_reverse, n, seed, points_b, "B")
        return forward

    # B 先打：B 满编打 A → A 幸存者数 → A(幸存)→B 才是用户要的 forward
    strike = simulate(b_attacker, a_target, stance_reverse, n=n, seed=seed,
                      points=points_b)
    a_surv = max(0, a_target.models - int(round(strike.expected_kills)))
    a_scaled = _scale_loadout(a_attacker, a_surv) if a_surv > 0 else replace(
        a_attacker, models=0, loadout=())
    forward = simulate(a_scaled, b_target, stance_forward, n=n, seed=seed + 2,
                       points=points_a)
    forward.reverse = strike
    forward.bias_notes.append(f"先攻判定：{verdict.rationale}")
    forward.bias_notes.append(
        f"B 先手满编反打，A 以幸存 {a_surv}/{a_target.models} 个模型出手"
        f"（B 期望击杀 {strike.expected_kills:.2f}）——A 输出已按此缩放")
    return forward
