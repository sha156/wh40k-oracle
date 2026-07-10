"""P5-b：十版战斗顺序判定器（纯规则有限状态机，零外部依赖）。

十版 Fight phase 先攻顺序是可枚举的确定规则，故代码化 + 单测即可高置信覆盖。规则（十版核心规则）：

  Step 1「Fights First」：具备 fights-first 来源（本回合冲锋成功 或 拥有 Fights First 能力）的单位先打。
  Step 2「Remaining Combats」：其余单位。
  两步各自：若两边都有资格，从【非当前回合玩家（守方）】的单位起交替选取结算。
  ⚠ 版本裁决（2026-07-10）：库内英文《Core Rules - New 40K Core Rules》page_040 写
  "Starting with the player whose turn it is"（当前玩家先）——该书经查证是【下一版】核心规则
  （目录含 SURGING/ACTIONS 等非十版章节、12.04 式编号条款），非十版真源。十版原文为
  "starting with the player whose turn is not currently taking place"，与中文
  《战锤40K总规则10版》page_033「当前是谁的回合，就从对方玩家开始」一致。本模拟器定位十版
  （数据库/MFM/中文 codex 全为十版），故按十版方向实现；勿按那本英文书"改回去"。
  「Fights Last」抵消规则（评审 E2）：
     · 单位 fights_last 且【无任何 fights-first 来源】→ 押到全场最后（Step 3）；
     · 单位【同时】有 fights-first 来源 且 fights_last → 两者相互抵消 → 回 Step 2 正常时序。
     ⚠ 出处存疑（2026-07-10 审查核实）：data_refined 全库检索 "fights last / fight last /
     strikes last" 0 命中——Fights Last 未在当前核心规则数据源中找到原文出处，上述判定逻辑
     按与 Fights First 对称的假设实现，涉及 Fights Last 的结论请谨慎使用。
  「Counter-offensive」战略（2CP）：某敌方单位刚结算完毕后，可选己方一个尚未结算的合格单位插队立刻结算。

注意：冲锋只发生在当前玩家的冲锋阶段，故 charged 必然属于 active player 一侧；冲锋方"通常先打"
是因为它独占 Fights First 步（守方无 fights-first 来源时不同步），而非同步内的选取顺序。
本模块回答「谁先打」，供 `engine.simulate_matchup` 判定正/反打方向、供 `agent.tools.judge_fight_order` 作答。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# 分层键：越小越先打
_STEP_FIRST = 1     # Fights First
_STEP_REMAIN = 2    # Remaining Combats（含 fights-first + fights-last 抵消回正常）
_STEP_LAST = 3      # 纯 Fights Last

_RULE_REFS = (
    "核心规则·Fight phase·Fights First（冲锋或 Fights First 能力的单位在第一步先打）",
    "Fights First/Fights Last 抵消：Fights Last 未在当前核心规则数据源（data_refined 全库"
    "检索 0 命中）找到原文出处，判定逻辑按与 Fights First 对称的假设实现，"
    "涉及 Fights Last 的结论请谨慎使用",
    "十版核心规则·同一步内从非当前回合玩家起交替选取单位结算"
    "（《战锤40K总规则10版》p33「当前是谁的回合，就从对方玩家开始」；"
    "库内英文《New 40K Core Rules》为下一版规则，方向相反，不适用于十版）",
    "核心战略·Counter-offensive（2CP，敌方单位刚结算后插队一个己方单位）",
)


@dataclass(frozen=True)
class FighterState:
    """一个参战单位在 Fight phase 开始时的先攻相关状态。"""
    name: str
    is_active_player: bool          # 是否当前回合玩家（谁的回合）——冲锋方必然是它
    charged: bool = False           # 本回合冲锋成功
    fights_first: bool = False      # 拥有 Fights First 能力
    fights_last: bool = False       # 拥有 Fights Last 能力

    @property
    def has_fights_first_source(self) -> bool:
        return self.charged or self.fights_first

    @property
    def step(self) -> int:
        """该单位落入的结算步（含 E2 抵消）。"""
        ff = self.has_fights_first_source
        if ff and not self.fights_last:
            return _STEP_FIRST
        if self.fights_last and not ff:
            return _STEP_LAST
        return _STEP_REMAIN         # 都没有，或 ff+last 抵消


@dataclass(frozen=True)
class FightVerdict:
    order: Tuple[str, ...]              # 先攻→后攻的单位名序列
    first_striker: str                 # 谁先打（单位名，仅展示）
    first_is_a: bool                   # 先打方是否为入参 a——**名字可能相同（镜像对局），
                                       #   调用方必须用本布尔判定方向，绝不可比对 first_striker 名字字符串**
    simultaneous_risk: bool            # 双方同一步 → 交替结算，反打即时（近战反伤风险高）
    rationale: str                     # 中文判定说明
    rule_refs: Tuple[str, ...]         # 规则锚点
    counter_offensive_note: str        # Counter-offensive 可否改变结论


def _step_label(step: int) -> str:
    return {_STEP_FIRST: "Fights First 步",
            _STEP_REMAIN: "Remaining Combats 步",
            _STEP_LAST: "Fights Last（全场最后）"}[step]


def _why(f: FighterState) -> str:
    if f.has_fights_first_source and f.fights_last:
        src = "冲锋" if f.charged else "Fights First 能力"
        return f"{f.name} 同时有 {src} 与 Fights Last → 抵消，回正常时序（Remaining Combats）"
    if f.charged:
        return f"{f.name} 本回合冲锋成功 → Fights First 步"
    if f.fights_first:
        return f"{f.name} 拥有 Fights First 能力 → Fights First 步"
    if f.fights_last:
        return f"{f.name} 拥有 Fights Last（且无先打来源）→ 押到全场最后"
    return f"{f.name} 无先攻修饰 → Remaining Combats 步"


def judge(a: FighterState, b: FighterState,
          counter_offensive_by: Optional[str] = None) -> FightVerdict:
    """判定 a、b 两单位的近战先攻顺序。

    a 通常是发起方（正打方）、b 是守方。counter_offensive_by 给单位名时，说明该单位
    插队后的差异（在其后一位敌方单位结算之后立即结算）。
    """
    sa, sb = a.step, b.step
    same_step = sa == sb

    if sa != sb:
        first, second = (a, b) if sa < sb else (b, a)
        tie_reason = ""
    else:
        # 同一步 → 十版：从非当前回合玩家（守方）起交替选取（版本裁决见模块 docstring）。
        if b.is_active_player and not a.is_active_player:
            first, second = a, b
        elif a.is_active_player and not b.is_active_player:
            first, second = b, a
        else:
            # 两边同为/同非 active（1v1 罕见）：保序取 a，标注歧义
            first, second = a, b
        tie_reason = "（同处一步，十版从非当前回合玩家起交替选取）"

    rationale = (
        f"{_why(a)}；{_why(b)}。"
        f"{first.name} 在 {_step_label(first.step)} 先打{tie_reason}，"
        f"{second.name} 后打（其时已承受先手伤亡、以幸存者反打）。"
    )
    if a.fights_last or b.fights_last:
        # 出处存疑（评审 M）：Fights Last 在 data_refined 核心规则源 0 命中，按对称假设实现
        rationale += ("（注意：Fights Last 未在当前核心规则数据源中找到原文出处，"
                      "其判定按对称假设实现，结果谨慎使用）")

    # Counter-offensive：仅当先打方是 counter_offensive_by 的敌人时才有意义（让己方插到敌方之后）
    if counter_offensive_by:
        if counter_offensive_by == second.name and same_step:
            co_note = (f"若 {second.name} 用 Counter-offensive（2CP），可在 {first.name} 结算后"
                       f"立即插队结算，1v1 下不改变「{first.name} 先打」但缩短其独占先手窗口；"
                       f"多单位场景可抢在对手下一个单位前动作。")
        elif counter_offensive_by == first.name:
            co_note = (f"{first.name} 本就先打，无需 Counter-offensive。")
        else:
            co_note = (f"Counter-offensive 需在敌方单位刚结算后使用；本 1v1 对 {counter_offensive_by} "
                       f"改变有限（主要影响多单位交替）。")
    else:
        co_note = "未启用 Counter-offensive；若守方有 2CP 可在攻方单位结算后插队反打（多单位更显著）。"

    return FightVerdict(
        order=(first.name, second.name),
        first_striker=first.name,
        first_is_a=(first is a),
        simultaneous_risk=same_step,
        rationale=rationale,
        rule_refs=_RULE_REFS,
        counter_offensive_note=co_note,
    )
