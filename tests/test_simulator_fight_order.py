"""P5-b 战斗顺序判定器全分支单测（十版 Fight phase 先攻）。

覆盖：冲锋先打、Fights First 步同层从 active 起、Fights Last 押最后、
**E2 抵消**（fights-first 来源 + Fights Last → 回正常时序，不押队尾）、
Counter-offensive 说明、都不冲锋 active 先。
"""
from __future__ import annotations

from engines.simulator.fight_order import (
    FighterState,
    judge,
    _STEP_FIRST,
    _STEP_LAST,
    _STEP_REMAIN,
)


def _act(name, **kw):
    return FighterState(name=name, is_active_player=True, **kw)


def _def(name, **kw):
    return FighterState(name=name, is_active_player=False, **kw)


# ── step 分层（含 E2 抵消）────────────────────────────────────
def test_step_charged_is_fights_first():
    assert _act("A", charged=True).step == _STEP_FIRST


def test_step_fights_first_ability():
    assert _def("B", fights_first=True).step == _STEP_FIRST


def test_step_plain_is_remaining():
    assert _def("B").step == _STEP_REMAIN


def test_step_pure_fights_last_goes_last():
    assert _def("B", fights_last=True).step == _STEP_LAST


def test_e2_charged_plus_fights_last_cancels_to_remaining():
    # 评审 E2：冲锋（先打来源）+ Fights Last → 抵消 → 正常时序，不押队尾
    assert _act("A", charged=True, fights_last=True).step == _STEP_REMAIN


def test_e2_fights_first_ability_plus_fights_last_cancels():
    assert _def("B", fights_first=True, fights_last=True).step == _STEP_REMAIN


# ── judge 顺序 ───────────────────────────────────────────────
def test_charger_strikes_first():
    v = judge(_act("Warboss", charged=True), _def("Terminators"))
    assert v.first_striker == "Warboss"
    assert v.order == ("Warboss", "Terminators")
    assert v.simultaneous_risk is False          # 不同步


def test_both_in_fights_first_active_goes_first():
    # A 冲锋（active），B 有 Fights First → 同处 Step1 → active(A) 先
    v = judge(_act("A", charged=True), _def("B", fights_first=True))
    assert v.first_striker == "A"
    assert v.simultaneous_risk is True           # 同一步，交替，反打即时


def test_defender_fights_first_when_attacker_didnt_charge():
    # A 未冲锋（普通），B 有 Fights First → B 在 Step1 先打
    v = judge(_act("A", charged=False), _def("B", fights_first=True))
    assert v.first_striker == "B"
    assert v.order == ("B", "A")


def test_pure_fights_last_defender_strikes_after():
    v = judge(_act("A", charged=True), _def("B", fights_last=True))
    assert v.first_striker == "A"
    assert v.order == ("A", "B")


def test_e2_defender_ff_plus_last_returns_to_normal_not_last():
    # B 有 Fights First + Fights Last（抵消回 Step2）；A 冲锋 Step1 → A 仍先，但 B 不被押到"最后"
    # 关键：若错误实现把 B 押到 STEP_LAST，顺序不变但语义错；这里断言 B 落 Remaining
    b = _def("B", fights_first=True, fights_last=True)
    assert b.step == _STEP_REMAIN
    v = judge(_act("A", charged=True), b)
    assert v.first_striker == "A"


def test_neither_charges_active_first():
    v = judge(_act("A"), _def("B"))
    assert v.first_striker == "A"                # 同 Step2，active 先
    assert v.simultaneous_risk is True


def test_rationale_and_refs_nonempty():
    v = judge(_act("A", charged=True), _def("B"))
    assert v.rationale and "先打" in v.rationale
    assert len(v.rule_refs) >= 3
    assert v.counter_offensive_note


# ── 评审 M：Fights Last 出处核查（data_refined 全库检索 0 命中 → 降级标注）──
def test_fights_last_provenance_caveat_in_refs_and_rationale():
    v = judge(_act("A", charged=True), _def("B", fights_last=True))
    # rule_refs 里明确标注：未找到原文出处、按对称假设实现
    assert any("未在当前核心规则数据源" in r for r in v.rule_refs)
    assert any("对称" in r for r in v.rule_refs)
    # 涉及 Fights Last 的判定，rationale 附谨慎使用提示
    assert "谨慎使用" in v.rationale


def test_no_fights_last_no_caveat_in_rationale():
    v = judge(_act("A", charged=True), _def("B"))
    assert "谨慎使用" not in v.rationale       # 不涉及 Fights Last 时不打扰


# ── Counter-offensive 说明 ───────────────────────────────────
def test_counter_offensive_by_second_striker_notes_insert():
    v = judge(_act("A", charged=True), _def("B", fights_first=True),
              counter_offensive_by="B")
    assert "Counter-offensive" in v.counter_offensive_note
    assert "B" in v.counter_offensive_note


def test_counter_offensive_by_first_striker_is_noop_note():
    v = judge(_act("A", charged=True), _def("B"), counter_offensive_by="A")
    assert "本就先打" in v.counter_offensive_note


# ── 评审 CRITICAL#1：镜像对局（同名）必须靠 first_is_a 判方向，不比名字 ──
def test_first_is_a_flag_disambiguates_same_name_matchup():
    # 双方同名，B 有 Fights First 而 A 未冲锋 → B 先打；名字都叫 "Intercessor Squad"
    a = FighterState("Intercessor Squad", is_active_player=True, charged=False)
    b = FighterState("Intercessor Squad", is_active_player=False, fights_first=True)
    v = judge(a, b)
    assert v.first_is_a is False              # B 先打——名字相同，只能靠布尔
    assert v.first_striker == "Intercessor Squad"


def test_first_is_a_true_when_a_charges():
    v = judge(_act("Same", charged=True), _def("Same"))
    assert v.first_is_a is True
