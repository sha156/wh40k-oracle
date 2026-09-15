"""P5-b：战斗顺序判定器（纯规则有限状态机，零外部依赖）——11 版口径。

Fight phase 先攻顺序是可枚举的确定规则，故代码化 + 单测即可高置信覆盖。规则真源：
《Core Rules - New 40K Core Rules》（11 版，2026-06-20 生效，data_refined 有全文）：

  12.04 两步结算：
  Step 1「Resolve Fights First Combats」：Fights First 单位先打——冲锋成功的单位本回合获得
    Fights First（24.13，p37 冲锋规则 + p39 双冲锋示例核实），拥有该技能的单位同理。
  Step 2「Resolve Remaining Combats」：其余单位。
  同一步内：从【当前回合玩家（active player）】起交替选取结算（"Starting with the player
  whose turn it is"）；Step 2 由把流程推进到该步的玩家先选（1v1 下等价于 active 先）。
  ⚠ 版本沿革（2026-07-10）：十版方向相反（从非当前玩家起，中文《总规则10版》p33）。项目当日
  裁决切换 11 版（docs/superpowers/plans/2026-07-10-edition-11-migration.md），本模块按 11 版
  实现；十版总规则已归档，勿按它改回去。
  「Fights Last」抵消规则（评审 E2）：
     · 单位 fights_last 且【无任何 fights-first 来源】→ 押到全场最后（Step 3）；
     · 单位【同时】有 fights-first 来源 且 fights_last → 两者相互抵消 → 回 Step 2 正常时序。
     ⚠ 出处存疑：语料（含 11 版核心规则）检索 "fights last / strikes last" 0 命中——判定
     逻辑按与 Fights First 对称的假设实现，涉及 Fights Last 的结论请谨慎使用。
  「COUNTEROFFENSIVE」核心战略（2CP，11版 p57）：对手近战阶段的 Fight step、某敌方单位刚
  结算完攻击后使用；效果=至阶段结束该单位获得 Fights First 且必须是你下一个选中结算的单位。
  1v1 不改变先手方，多单位场景抢队列。

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
    "Core Rules(11版) 12.04·Fight phase 两步结算：冲锋（授予 Fights First，24.13）或"
    "拥有 Fights First 能力的单位在 Resolve Fights First Combats 步先打",
    "Fights First/Fights Last 抵消：Fights Last 未在当前核心规则数据源（含 11 版核心规则，"
    "全库检索 0 命中）找到原文出处，判定逻辑按与 Fights First 对称的假设实现，"
    "涉及 Fights Last 的结论请谨慎使用",
    "Core Rules(11版) 12.04·同一步内从当前回合玩家起交替选取单位结算"
    "（十版方向相反且十版总规则已归档，勿混用）",
    "Core Rules(11版) p57·COUNTEROFFENSIVE（2CP，对手近战阶段敌方单位刚结算后：该单位获得"
    " Fights First 且必须是你下一个选中结算的单位）",
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
          counter_offensive_by: Optional[str] = None,
          counter_offensive_is_a: Optional[bool] = None) -> FightVerdict:
    """判定 a、b 两单位的近战先攻顺序（11 版口径）。

    a 通常是发起方（正打方）、b 是守方。counter_offensive_by 给单位名时，说明该单位用
    COUNTEROFFENSIVE（2CP，11版 p57：获得 Fights First 且必须是其玩家下一个选中结算的
    单位）后的差异。

    `counter_offensive_is_a` 是**方向的权威入参**（True=a 方用，False=b 方用）：
    名字在镜像对局（攻守同名）里分不出谁是谁，而 `FightVerdict.first_is_a` 的注释早已
    写明「绝不可比对 first_striker 名字字符串」——本函数的 CO 分支曾是那条铁律唯一的
    违例处，攻守同名时会把守方的插队问答成「你本就先打，无需 CO」（审查 R1-M2）。
    只给名字而两边同名时不再猜，改为显式披露分不出方向。
    """
    sa, sb = a.step, b.step
    same_step = sa == sb

    if sa != sb:
        first, second = (a, b) if sa < sb else (b, a)
        tie_reason = ""
    else:
        # 同一步 → 11版 12.04：从当前回合玩家（active player）起交替选取（版本沿革见模块 docstring）。
        if a.is_active_player and not b.is_active_player:
            first, second = a, b
        elif b.is_active_player and not a.is_active_player:
            first, second = b, a
        else:
            # 两边同为/同非 active（1v1 罕见）：保序取 a，标注歧义
            first, second = a, b
        tie_reason = "（同处一步，11版 12.04 从当前回合玩家起交替选取）"

    rationale = (
        f"{_why(a)}；{_why(b)}。"
        f"{first.name} 在 {_step_label(first.step)} 先打{tie_reason}，"
        f"{second.name} 后打（其时已承受先手伤亡、以幸存者反打）。"
    )
    if a.fights_last or b.fights_last:
        # 出处存疑（评审 M）：Fights Last 在 data_refined 核心规则源 0 命中，按对称假设实现
        rationale += ("（注意：Fights Last 未在当前核心规则数据源中找到原文出处，"
                      "其判定按对称假设实现，结果谨慎使用）")

    # COUNTEROFFENSIVE（11版 p57）：只在对手近战阶段、敌方单位刚结算后可用——1v1 不改变先手方
    if counter_offensive_by or counter_offensive_is_a is not None:
        # 方向一律走布尔，**不比对名字**（审查 R1-M2）。名字只用于文案措辞。
        co_side_is_a: Optional[bool] = counter_offensive_is_a
        mirror_ambiguous = False
        if co_side_is_a is None:
            if a.name == b.name:
                mirror_ambiguous = True          # 镜像对局：名字给不出方向，不猜
            elif counter_offensive_by == a.name:
                co_side_is_a = True
            elif counter_offensive_by == b.name:
                co_side_is_a = False
            # 名字既不属于 a 也不属于 b：保持 None，落到通用文案

        co_label = counter_offensive_by or (a.name if co_side_is_a else b.name)
        co_is_first = None if co_side_is_a is None else (co_side_is_a is (first is a))

        if mirror_ambiguous:
            co_note = (f"攻守同名（{a.name}），无法从名字判断 COUNTEROFFENSIVE 由哪一方使用——"
                       f"请按侧指明（attacker / defender）。若由后打方使用，可在先打方结算后"
                       f"立即获得 Fights First 并作为下一个结算单位插队；若由先打方使用则无需，"
                       f"它本就先打。")
        elif co_is_first is True:
            co_note = (f"{co_label} 本就先打，无需 COUNTEROFFENSIVE。")
        elif co_is_first is False and same_step:
            co_note = (f"若 {co_label} 用 COUNTEROFFENSIVE（2CP，11版 p57），可在 {first.name} "
                       f"结算后立即获得 Fights First 并作为下一个结算单位插队，1v1 下不改变"
                       f"「{first.name} 先打」但缩短其独占先手窗口；多单位场景可抢在对手下一个单位前动作。")
        else:
            co_note = (f"COUNTEROFFENSIVE 需在对手近战阶段、敌方单位刚结算后使用；本 1v1 对 "
                       f"{co_label} 改变有限（主要影响多单位交替）。")
    else:
        co_note = ("未启用 COUNTEROFFENSIVE；守方若有 2CP 可在攻方单位结算后插队反打"
                   "（11版 p57：获得 Fights First 且必须下一个结算；多单位更显著）。")

    return FightVerdict(
        order=(first.name, second.name),
        first_striker=first.name,
        first_is_a=(first is a),
        simultaneous_risk=same_step,
        rationale=rationale,
        rule_refs=_RULE_REFS,
        counter_offensive_note=co_note,
    )
