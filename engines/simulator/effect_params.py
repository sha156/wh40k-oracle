"""Effect 条件求值 + 武器参数聚合 + 消费点注册表（P7-PR7 自 sequence.py 拆出）。

内容三块（原 sequence.py 81-395 / 494-569 行，逻辑零改动）：
  · KNOWN_CONDITION_TAGS + _cond_true：condition (tag, *args) 单 tag 契约的唯一求值器
  · _WeaponParams + _gather_params：把一把武器的 Effect 汇成标量开关（含守方效果并入、
    掩体 BS 折算、修正统一夹取与 S/T 延迟分量路由）
  · ATTACKER_CONSUMED / TARGET_CONSUMED + 未消费对账 helpers：引擎消费点白名单唯一真源
    （dsl.py 校验引用）与「要么被消费、要么显式披露」的对账层

拆分动因：sequence.py 787 行逼近项目 800 行上限（PR6 审查 MEDIUM）。**公共契约不变**：
sequence.py re-export 全部符号，外部（dsl.py/engine.py/测试）仍从 sequence 导入即可。
依赖方向与母模块一致：只 import contracts，不碰 sqlite/app/streamlit。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from engines.simulator.contracts import Stance, TargetProfile, WeaponProfile

_FACES = 6


# ---------------------------------------------------------------------------
# Effect 读取（P4-c：词条按阶段生效）
# ---------------------------------------------------------------------------
# _cond_true 认识的全部条件 tag——DSL 校验（dsl.py）引用此集合做白名单，唯一真源在此。
# 新增 tag 时两处同步：本集合 + _cond_true 分支；test_simulator_dsl 有护栏断言
# （集合内逐 tag 求值不 raise、集合外 raise）。
KNOWN_CONDITION_TAGS = frozenset({
    "half_range", "stationary", "charging", "long_range", "indirect",
    "phase_shooting", "phase_melee", "target_has_keyword",
    "guided_vs_spotted", "guided_markerlight", "markerlight_observer",
    "detachment_rounds_shooting", "detachment_rounds_guided",
    "ranged_within_12", "ranged_within_8",          # P7-PR4：绝对射程档假设（自含射击阶段）
    "target_below_starting", "target_below_half",   # P7-PR4：目标战损状态假设
    "target_models_in_range",                       # P7-PR4：(tag, lo, hi) 按目标模型数分档
    "shooting_target_models_in_range",              # P7-PR4：复合 tag=射击阶段 × 目标规模
    "melee_charging",                               # P7-PR5：复合 tag=近战阶段 × 本回合冲锋
                                                    # （Relentless Rage 等"冲锋回合近战武器"条款——
                                                    # 单独 charging 会在射击阶段误放行）
    "blessing_martial_excellence",                  # P7-PR5·恐虐赐福（各自自含近战阶段门控）
    "blessing_warp_blades",
    "blessing_decapitating_strikes_vs_infantry",    # 复合 tag=近战 × 赐福开 × 目标步兵
    "melee_target_has_keyword",                     # P7-PR5：(tag, kw) 近战阶段 × 目标关键词
                                                    # （A Trophy for the Throne 等 Fight phase
                                                    # 战略——裸 target_has_keyword 会在射击误放行）
    "melee_disembarked",                            # P7-PR6：近战 × 本回合下车（BT Shock and
                                                    # Awe 命中+1 / Paragon of Fury 伤害档）
    "melee_s_lte_t",                                # P7-PR6：近战 × 最终 S≤T（BT 誓言 Accept Any
                                                    # Challenge 致伤+1）。S/T 比较延迟到
                                                    # _resolve_weapon 的最终 S（含 s_improve）处
                                                    # 判定——录入面仅限 (wound,modify)，dsl 校验拦
    "wound_s_gt_t",                                 # P7-PR6：守方向 × 最终 S>T（BT Purge and
                                                    # Sanctify 被伤-1）。同为延迟判定 tag
    "omen_instrument_vs_character",                 # P7-PR6·圣兆「神皇之器」：近战 × 圣兆开 ×
                                                    # 目标 CHARACTER → [DEVASTATING WOUNDS]
    "omen_momentous_brutality",                     # P7-PR6·圣兆「凶暴神视」：近战 × 圣兆开
})


def _cond_true(condition: Tuple, stance: Stance, target: TargetProfile) -> bool:
    """Effect.condition 是否在本次态势/目标下成立。契约：condition = (tag, *args)——
    单 tag，首元素定分支、其余元素是该 tag 的参数；复合条件用复合 tag（不做合取求值器）。"""
    if not condition:
        return True
    tag = condition[0]
    if tag == "half_range":
        return stance.half_range
    if tag == "stationary":
        return stance.stationary
    if tag == "charging":
        return stance.charging
    if tag == "long_range":
        return stance.long_range
    if tag == "indirect":
        return stance.indirect
    if tag == "phase_shooting":          # P5-a：Stealth（11版=掩体）等仅对射击生效
        return stance.phase == "shooting"
    if tag == "phase_melee":             # cleave（11版24.06）等仅对近战生效
        return stance.phase == "melee"
    if tag == "target_has_keyword":
        return len(condition) > 1 and condition[1] in target.keywords
    if tag == "guided_vs_spotted":       # P7：FTGG 受引导单位打被标记目标（11版军规）
        return stance.phase == "shooting" and stance.guided
    if tag == "guided_markerlight":      # P7：观察员带 Markerlight 关键词 → 追加 [IGNORES COVER]
        return (stance.phase == "shooting" and stance.guided
                and stance.markerlight_observer)
    if tag == "markerlight_observer":    # P7-PR3：本单位自身带 Markerlight（不要求 guided——
        return (stance.phase == "shooting"    # Coordinate to Engage 的攻方就是观察员）
                and stance.markerlight_observer)
    if tag == "detachment_rounds_shooting":  # P7-PR3：分队规则战轮门控（远程武器条款）
        return stance.phase == "shooting" and stance.detachment_rounds
    if tag == "detachment_rounds_guided":    # P7-PR3：战轮门控 + 受引导（分队规则第二条款）
        return (stance.phase == "shooting" and stance.detachment_rounds
                and stance.guided)
    if tag == "ranged_within_12":            # P7-PR4：假设目标在 12" 内（8" 档几何蕴含）
        return (stance.phase == "shooting"
                and (stance.range_within_12 or stance.range_within_8))
    if tag == "ranged_within_8":             # P7-PR4：假设目标在 8" 内
        return stance.phase == "shooting" and stance.range_within_8
    if tag == "target_below_starting":       # P7-PR4：目标低于满编（低于半编蕴含之）
        return stance.target_below_starting or stance.target_below_half
    if tag == "target_below_half":           # P7-PR4：目标低于半编
        return stance.target_below_half
    if tag == "target_models_in_range":      # P7-PR4：(tag, lo, hi) 按目标模型数分档
        if len(condition) != 3:              # 缺参静默 False=效果静默失效，与未知 tag 同罪
            raise ValueError(
                f"target_models_in_range 需要 (tag, lo, hi)，收到 {condition!r}")
        return int(condition[1]) <= int(target.models) <= int(condition[2])
    if tag == "shooting_target_models_in_range":  # P7-PR4 复合 tag（评审 F2：单 tag 契约，
        if len(condition) != 3:                   # 复合语义注册复合 tag）——Arro'kon 等
            raise ValueError(                     # "射击阶段战略 × 目标规模分档"用
                f"shooting_target_models_in_range 需要 (tag, lo, hi)，收到 {condition!r}")
        return (stance.phase == "shooting"
                and int(condition[1]) <= int(target.models) <= int(condition[2]))
    if tag == "melee_charging":              # P7-PR5：冲锋回合的近战条款（Relentless Rage）
        return stance.phase == "melee" and stance.charging
    if tag == "melee_target_has_keyword":    # P7-PR5：(tag, kw) 近战 × 目标关键词复合
        if len(condition) != 2:
            raise ValueError(
                f"melee_target_has_keyword 需要 (tag, keyword)，收到 {condition!r}")
        return stance.phase == "melee" and condition[1] in target.keywords
    if tag == "blessing_martial_excellence":     # P7-PR5·卓越武艺：近战 [SUSTAINED HITS 1]
        return stance.phase == "melee" and stance.blessing_martial_excellence
    if tag == "blessing_warp_blades":            # P7-PR5·次元邪刃：近战 [LETHAL HITS]
        return stance.phase == "melee" and stance.blessing_warp_blades
    if tag == "blessing_decapitating_strikes_vs_infantry":  # P7-PR5·斩首一击：近战对步兵 dev
        return (stance.phase == "melee" and stance.blessing_decapitating_strikes
                and "infantry" in target.keywords)
    if tag == "melee_disembarked":               # P7-PR6：近战 × 本回合下车（LR 档蕴含下车）
        return stance.phase == "melee" and (stance.disembarked_this_turn
                                            or stance.disembarked_from_land_raider)
    if tag == "melee_s_lte_t":                   # P7-PR6：S≤T 分量延迟到 _resolve_weapon
        return stance.phase == "melee"           # （此处只判近战门控；见 wound_mod_s_lte_t）
    if tag == "wound_s_gt_t":                    # P7-PR6：守方向 S>T 延迟判定（无态势门控）
        return True
    if tag == "omen_instrument_vs_character":    # P7-PR6·圣兆「神皇之器」
        return (stance.phase == "melee" and stance.omen_instrument
                and "character" in target.keywords)
    if tag == "omen_momentous_brutality":        # P7-PR6·圣兆「凶暴神视」
        return stance.phase == "melee" and stance.omen_momentous_brutality
    # P7 加固（评审 F2）：未知 tag 静默返回 False = 效果静默失效（攻方侧零披露），
    # 是 CLAUDE.md 明令的静默降级缝——改为 raise，让 DSL 录入笔误在测试期就炸出来。
    raise ValueError(f"未知 Effect condition tag: {tag!r}（来源条件 {condition!r}）")


@dataclass
class _WeaponParams:
    """一把武器在当前态势下解算出的生效参数（把 Effect 汇成标量开关）。"""
    rf_exprs: tuple = ()           # tuple[DiceExpr]（附加攻击骰：rapid fire X / DSL "+X A"；
                                   # P7-PR5 起累加——分队规则与战略同阶段各 +1 A 必须叠加，
                                   # 旧的单值 last-write 会静默吞掉一层）
    blast_x: int = 0               # [BLAST X]/[CLEAVE X]：每满 5 目标模型 +X 攻击骰（0=无）
    melta_expr: object = None      # DiceExpr | None（melta X，X 可为骰子）
    crit_hit_thr: int = _FACES
    sustained: object = None      # DiceExpr | None
    lethal: bool = False
    torrent: bool = False
    indirect_fixed: bool = False   # 11版间接开火：命中改固定未修正阈值（6+；驻停代理 4+）
    hit_mod: int = 0
    bs_delta: int = 0              # P7：BS 特征值净变化（改善为正、恶化为负；掩体 13.08 在此）。
                                   # 特征值修正≠命中骰修正：不进 ±1 夹取（上限条款语料缺页，
                                   # 按无上限实现并披露——spec D2），也不影响暴击阈值（看自然骰）
    ignore_neg_hit: bool = False   # 11版24.29 [PSYCHIC]：无视不利命中修正（保留有利修正）
    crit_wound_thr: int = _FACES
    twin: bool = False
    has_dev: bool = False
    wound_mod: int = 0
    ignores_cover: bool = False
    cover: bool = False
    ap_improve: int = 0            # P7-PR3：AP 特征值改善累计（AP 存负值，改善=更负）
    hit_reroll_fail: bool = False  # P7-PR3：命中骰失败重骰（最优策略=只重骰失败）
    s_improve: int = 0             # P7-PR4：S 特征值改善累计（Bonded Heroes 等；
                                   # 特征值≠致伤骰修正——改 S vs T 查表本身，不吃 ±1 夹取）
    sv_improve: int = 0            # P7-PR4：守方护甲 Sv 特征值改善累计（+1 Sv=阈值-1；
                                   # 下限由 effective_save 的 ≥2 夹取承担）
    target_invuln: object = None   # P7-PR4：守方 DSL 授予的无效保护阈值（Optional[int]，
                                   # 与 profile 自带 invuln 取更优）
    wound_mod_raw: int = 0         # P7-PR6：致伤修正夹取前的原始累计——S/T 延迟分量并入后
                                   # 须与基础分量【合并夹取 ±1】，不能各夹各的
    wound_mod_s_lte_t: int = 0     # P7-PR6：仅当最终 S≤T 生效的致伤修正分量（BT 誓言
                                   # Accept Any Challenge；最终 S=strength+s_improve，
                                   # 在 _resolve_weapon 判定——录入期基础 S 判定会在
                                   # S 改善叠加越过 T 时高估）
    wound_mod_s_gt_t: int = 0      # P7-PR6：仅当最终 S>T 生效的致伤修正分量（守方向
                                   # Purge and Sanctify 被伤-1）


def _gather_params(w: WeaponProfile, stance: Stance, target: TargetProfile) -> _WeaponParams:
    p = _WeaponParams(cover=stance.target_in_cover)
    hit_pos = hit_neg = 0        # 命中修正分正负累计（[PSYCHIC] 只忽略负修正）
    bs_pos = bs_neg = 0          # P7：BS 特征值修正另立通道，分正负累计（同 PSYCHIC 有利方向语义）
    for e in w.effects:
        ok = _cond_true(e.condition, stance, target)
        if e.phase == "attacks":
            if e.op == "modify" and ok:
                p.rf_exprs = p.rf_exprs + (e.params[0],)   # DiceExpr（rapid fire / +X A，累加）
            elif e.op == "blast" and ok:
                # blast（无条件）与 cleave（condition=phase_melee）共用本通道；
                # 无参旧式 Effect（十版 [BLAST]）向后兼容为 X=1
                p.blast_x = max(p.blast_x, int(e.params[0]) if e.params else 1)
        elif e.phase == "hit":
            # P7-PR3：extra_hits/auto_wound/auto_hit 补 ok 门控——既有词条 condition 恒空
            # （ok=True，行为不变），分队规则经 DSL 注入的条件版（战轮门控）靠它放行/拦截
            if e.op == "extra_hits" and ok:
                p.sustained = e.params[0]
            elif e.op == "auto_wound" and ok:
                p.lethal = True
            elif e.op == "auto_hit" and ok:
                p.torrent = True
            elif e.op == "indirect_fixed" and ok:
                p.indirect_fixed = True           # 11版24.19+10.07：命中改固定未修正阈值
            elif e.op == "crit_threshold" and ok:
                p.crit_hit_thr = min(p.crit_hit_thr, int(e.params[0]))
            elif e.op == "ignore_hit_mods" and ok:
                p.ignore_neg_hit = True       # 11版24.29 [PSYCHIC]；P7-PR3 起带条件
                                              # （Patient Hunter 受引导忽略修正走同通道）
            elif e.op == "reroll" and ok:
                p.hit_reroll_fail = True      # P7-PR3：命中失败重骰（Pinpoint 等）
            elif e.op == "modify" and ok:
                v = int(e.params[0])
                if v >= 0:
                    hit_pos += v
                else:
                    hit_neg += v
            elif e.op == "bs_improve" and ok:
                # P7：BS 特征值改善（FTGG "improve the Ballistic Skill characteristic
                # by 1"）。特征值修正≠命中骰修正——禁止折进 hit_pos（会被 ±1 夹取吞掉
                # 与 heavy 等叠加量）。负参数表示特征值恶化。
                v = int(e.params[0])
                if v >= 0:
                    bs_pos += v
                else:
                    bs_neg += v
        elif e.phase == "wound":
            if e.op == "mortal_pool" and ok:
                p.has_dev = True
            elif e.op == "crit_threshold" and ok:
                p.crit_wound_thr = min(p.crit_wound_thr, int(e.params[0]))
            elif e.op == "reroll" and ok:
                p.twin = True      # 致伤失败重骰；P7-PR3 起带条件（Combat Debarkation 等）
            elif e.op == "modify" and ok:
                if e.condition and e.condition[0] == "melee_s_lte_t":
                    # P7-PR6：S≤T 分量延迟判定（_cond_true 只放行了近战门控）
                    p.wound_mod_s_lte_t += int(e.params[0])
                else:
                    p.wound_mod += int(e.params[0])
            elif e.op == "s_improve" and ok:
                # P7-PR4："improve the Strength characteristic by 1"（Bonded Heroes）。
                # 特征值改善≠致伤骰修正：改 S vs T 查表输入本身——S4→S5 打 T7 仍 5+，
                # 而致伤骰 +1 会错升成 4+；两通道禁止互相折算
                p.s_improve += int(e.params[0])
        elif e.phase == "damage":
            if e.op == "modify" and ok:
                p.melta_expr = e.params[0]        # DiceExpr（melta）
        elif e.phase == "save":
            if e.op == "ignores_cover" and ok:
                p.ignores_cover = True
            elif e.op == "cover" and ok:
                p.cover = True
            elif e.op == "ap_improve" and ok:
                # P7-PR3："improve the Armour Penetration characteristic by 1"
                # （Point-Blank Ambush / Focused Fire）。AP 存负值，改善=更负
                p.ap_improve += int(e.params[0])
    # P5-a：守方防守 Effect 并入。
    #   · hit+modify（烟幕等减命中）叠加进攻方命中修正，再统一夹取——修正上限是对
    #     【总和】夹 ±1（未审计项，沿用十版口径），故必须在 clamp 之前叠加
    #     （烟幕 -1 与 heavy +1 可抵消为 0）；
    #   · save+cover（11版 Stealth 24.33：被远程攻击选中获掩体收益）并入掩体开关，
    #     于下方折成命中惩罚时被武器侧 [IGNORES COVER]（24.18）整体抵消。
    for e in target.effects:
        if not _cond_true(e.condition, stance, target):
            continue
        if e.phase == "hit" and e.op == "modify":
            v = int(e.params[0])
            if v >= 0:
                hit_pos += v
            else:
                hit_neg += v
        elif e.phase == "save" and e.op == "cover":
            p.cover = True
        elif e.phase == "hit" and e.op == "bs_improve":
            # P7-PR4 守方 DSL：WS/BS 特征值修正（EMP Grenades "worsen the ... Ballistic
            # Skill characteristics by 1" → 参数 -1）。与掩体折算同通道：特征值层净算，
            # 不吃 ±1 骰修正夹取；[PSYCHIC] 按有利方向可无视其恶化分量
            v = int(e.params[0])
            if v >= 0:
                bs_pos += v
            else:
                bs_neg += v
        elif e.phase == "save" and e.op == "invuln":
            # P7-PR4 守方 DSL：授予无效保护（Skirmish Fighters 远程 5+/近战 6+ 等）。
            # 多来源取更优（阈值更小）；与 profile 自带 invuln 的合并在 _resolve_weapon
            v = int(e.params[0])
            p.target_invuln = v if p.target_invuln is None else min(int(p.target_invuln), v)
        elif e.phase == "save" and e.op == "sv_improve":
            # P7-PR4 守方 DSL："+1 Sv"（Autoreactive Camouflage）——护甲特征值改善，
            # 不作用于 invuln；1+ 以下由 effective_save 的 ≥2 夹取兜住
            p.sv_improve += int(e.params[0])
        elif e.phase == "wound" and e.op == "modify":
            # P7-PR5 守方 DSL：致伤骰修正（DAEMONIC RESISTANCE "subtract 1 from the
            # Wound roll" → 参数 -1）。并入攻方致伤修正同一累计，随后统一夹 ±1
            # ——与守方 hit+modify 的烟幕先例同语义（正负可与攻方修正抵消）
            if e.condition and e.condition[0] == "wound_s_gt_t":
                # P7-PR6：S>T 分量延迟到 _resolve_weapon 的最终 S 处判定
                p.wound_mod_s_gt_t += int(e.params[0])
            else:
                p.wound_mod += int(e.params[0])
    # ── Benefit of Cover（11版 13.08）：掩体收益 = 恶化该次攻击的 BS 1 点（射击专属），
    #   十版"护甲保存骰+1、且 AP0 对 3+ 甲无效"整体作废——掩体从保存侧挪到命中侧。
    #   P7 起折进 **BS 特征值通道 bs_neg**（S7 曾折 hit_neg，与 13.08 "worsen the
    #   Ballistic Skill characteristic" 的措辞对齐后迁移；差异仅在与 bs_improve/命中修正
    #   三方叠加时显现——特征值层先净算、命中骰修正层再独立夹 ±1）。三条 11 版联动不变：
    #     · 武器侧 [IGNORES COVER]（24.18）→ p.ignores_cover 使 cover_active 为假，惩罚不进桶；
    #     · 攻方 [PSYCHIC]（24.29）→ 下方按有利方向把 bs_neg 与 hit_neg 一并清零（B6 交互，
    #       24.29 原文同时覆盖 "BS/WS 与命中骰" 两类修正）；
    #     · 曲射固定阈值 / torrent 自动命中路径在 _resolve_weapon 不读 hit_mod/bs_delta，
    #       故掩体对其天然无效（曲射阈值作用于"未修正"命中骰）。
    #   近战不受掩体影响（13.08 只对远程攻击），故仅射击阶段折算。
    cover_active = p.cover and not p.ignores_cover
    if cover_active and stance.phase == "shooting":
        bs_neg -= 1
    # [PSYCHIC]（11版24.29）：攻方每次攻击可无视 BS/WS 与命中骰的任意修正（含掩体的 BS
    # 惩罚）——按有利方向执行：只忽略负修正（两个通道），保留正修正（heavy +1、
    # FTGG bs_improve 照常享受）。
    if p.ignore_neg_hit:
        hit_neg = 0
        bs_neg = 0
    # 命中/致伤修正各自夹到 ±1（修正总和上限，未审计项沿用十版口径）；
    # BS 特征值净变化不夹取（上限条款语料缺页，spec D2 按无上限实现并披露）。
    # P7-PR6：致伤修正保留夹取前原值 wound_mod_raw——S/T 延迟分量（wound_mod_s_lte_t /
    # wound_mod_s_gt_t）在 _resolve_weapon 判定成立后须与原值合并再统一夹 ±1
    p.hit_mod = max(-1, min(1, hit_pos + hit_neg))
    p.bs_delta = bs_pos + bs_neg
    p.wound_mod_raw = p.wound_mod
    p.wound_mod = max(-1, min(1, p.wound_mod))
    return p


# ── Effect 消费点注册表（P7）────────────────────────────────────────────────
# 引擎实际消费的 (phase, op) 全集，与 _gather_params/_target_effect_value 的分支一一对应。
# DSL 校验（engines/simulator/dsl.py）按侧引用这两个集合做白名单——白名单唯一真源在此，
# 不许在别处手抄第二份（评审 F7：encoded 判据第④条 = 施加侧存在消费点）。
# 新增引擎分支时必须同步登记，测试 test_simulator_dsl 有差分断言护住漂移。
ATTACKER_CONSUMED = frozenset({
    ("attacks", "modify"), ("attacks", "blast"),
    ("hit", "extra_hits"), ("hit", "auto_wound"), ("hit", "auto_hit"),
    ("hit", "indirect_fixed"), ("hit", "crit_threshold"), ("hit", "ignore_hit_mods"),
    ("hit", "modify"), ("hit", "bs_improve"), ("hit", "reroll"),
    ("wound", "mortal_pool"), ("wound", "crit_threshold"), ("wound", "reroll"),
    ("wound", "modify"), ("wound", "s_improve"),
    ("damage", "modify"),
    ("save", "ignores_cover"), ("save", "cover"), ("save", "ap_improve"),
})
TARGET_CONSUMED = frozenset({
    ("fnp", "fnp"), ("damage", "damage_reduction"),
    ("hit", "modify"), ("save", "cover"),
    ("save", "invuln"), ("save", "sv_improve"),     # P7-PR4：inject_target 防守向通道
    ("hit", "bs_improve"),                          # P7-PR4：守方 BS/WS 特征值修正（EMP）
    ("wound", "modify"),                            # P7-PR5：守方致伤骰修正（-1 被伤，
                                                    # DAEMONIC RESISTANCE 等；并入统一 ±1 夹取）
})


def unconsumed_attacker_effect_notes(attacker) -> List[str]:
    """列出攻方 loadout 各武器 effects 中引擎不会消费的条目（评审 F4）。

    _gather_params 对未知 op 直接跳过零记账——DSL 注入若 op 合法但引擎该侧没接，
    效果会静默归零。与守方对账同语义：要么被消费、要么显式披露。
    """
    notes = []
    for w in attacker.loadout:
        for e in w.effects:
            if (e.phase, e.op) not in ATTACKER_CONSUMED:
                notes.append(
                    f"攻方 Effect 未消费：{w.name_en} 的 phase={e.phase}/op={e.op}"
                    f"（来源 {e.source or '未知'}）——引擎攻方侧无此消费点，"
                    f"该效果未计入本次结果")
    return notes


# ── 守方 Effect 消费对账（评审 M：target.effects 要么被消费、要么显式披露，绝不静默丢）──
# 引擎当前的全部消费点：
#   · op == "fnp" / "damage_reduction" → run_sequence 顶层经 _target_effect_value 读取
#     （P7-PR4 起过 condition + 多来源取更优）；
#   · phase == "hit" 且 op == "modify" → _gather_params 并入攻方命中修正（烟幕等减命中）；
#   · phase == "save" 且 op == "cover" → _gather_params 并入掩体开关（11版 Stealth 24.33）；
#   · phase == "save" 且 op == "invuln"/"sv_improve" → _gather_params 折进有效保存
#     （P7-PR4 inject_target 防守向通道：DSL 授予无效保护/护甲改善）；
#   · phase == "wound" 且 op == "modify" → _gather_params 并入致伤修正统一夹取
#     （P7-PR5：DAEMONIC RESISTANCE 等"被伤致伤骰-1"）。
# 其余 phase/op 当前没有消费者——列入报告注解透传。
def _target_effect_consumed(e) -> bool:
    if e.op in ("fnp", "damage_reduction"):
        return True
    if e.phase == "hit" and e.op in ("modify", "bs_improve"):
        return True
    if e.phase == "wound" and e.op == "modify":     # P7-PR5：守方致伤骰修正
        return True
    return e.phase == "save" and e.op in ("cover", "invuln", "sv_improve")


def unconsumed_target_effect_notes(target: TargetProfile) -> List[str]:
    """列出守方 effects 中引擎不会消费的条目（供 engine.simulate 透传进 not_modeled）。

    只披露、不改数值——保证「报告里出现 ≠ 结果被影响」这一诚实语义。
    """
    return [
        f"守方 Effect 未消费：phase={e.phase}/op={e.op}"
        f"（来源 {e.source or '未知'}）——引擎当前只消费 fnp/damage_reduction/"
        f"命中修正（hit+modify）/掩体（save+cover）/无效保护（save+invuln）/"
        f"护甲改善（save+sv_improve），该效果未计入本次结果"
        for e in target.effects if not _target_effect_consumed(e)
    ]


