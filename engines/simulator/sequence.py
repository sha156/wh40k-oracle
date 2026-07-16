"""逐骰攻击序列 pipeline（向量化核，P4-b 裸序列 + 通用 Effect 接缝）。

版本口径（2026-07-10 起，按 11 版 USR 审计 S3 逐项修正，见
docs/superpowers/specs/2026-07-10-edition-11-usr-audit.md）：
  · 已 11 版化：Benefit of Cover（13.08 掩体=恶化攻方 BS 1、非十版护甲+1，且十版"AP0 对
    3+ 甲无效"例外整体废弃，见 _gather_params）/ Stealth（24.33 掩体化）/ Indirect Fire
    （24.19+10.07 固定未修正阈值）/ Heavy（24.16 条件放宽，字段沿用 stationary）/
    Blast X（24.05）/ Cleave X（24.06）/ Psychic（24.29 无视不利命中修正，含无视掩体
    BS 惩罚）/ 特殊保护（05.04 单次保存骰双重对照）/ dev 致命池不吃减伤（24.10+06.02）；
  · 其余词条经审计与 11 版一致（A 类：rapid fire/melta/sustained/dev/anti/…）沿用原实现；
  · 未审计部分（如 ±1 修正夹紧上限）仍为十版口径，如实标注。

依赖方向：**只 import contracts / parse / _spike_allocation**，绝不碰 sqlite/app/streamlit
（见 spec 第五节），保证脱库单测、P8 可复用。

设计（spec 第七节）：对每个"攻击槽"在 N 维上向量化，在攻击槽维度上小循环。
每把武器单独结算，产出该武器的"未过保正常伤害"与"暴击造伤（dev 致命池）"两组
(N, A) 伤害数组（未命中/未过伤/被保存的槽 = 0）；跨武器沿槽维拼接后，正常伤害在前、
致命池在后，喂进已 spike 验证的 `allocate_numpy` 做不溢出+已损伤优先+逐点FNP+致命池分配。

P4-b 覆盖：attacks(裸采样) / hit(BS-WS,自然骰,含掩体 BS 惩罚) / wound(S-T查表,自然骰)
/ save(AP+invuln 单次双重对照) / damage(采样+减伤夹≥1) / fnp / dev 致命池 / 防守开关(FNP·减伤·掩体)。
攻击性词条（rapid fire/sustained/lethal/anti/twin-linked/blast/melta/…）经 Effect 通道在
P4-c 接入本 pipeline 的对应阶段，届时本文件按 op 扩展分支。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from engines.simulator._spike_allocation import allocate_numpy
from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.parse import sample_dice

_FACES = 6


# ---------------------------------------------------------------------------
# 规则查表（写死 + 单测；spec 第七节）
# ---------------------------------------------------------------------------
def wound_target(strength: int, toughness: int) -> int:
    """S vs T 命中伤害查表：返回致伤所需骰面（自上而下）。"""
    if strength >= 2 * toughness:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if 2 * strength > toughness:      # S < T 但 2S > T
        return 5
    return 6                          # 2S ≤ T


def effective_save(sv: int, ap: int, invuln: Optional[int]) -> int:
    """有效保存所需骰面（越小越易保）：AP 修正后的护甲与 invuln 单次保存骰双重对照取更优。

    - AP 存负值，`sv - ap` = 护甲变差（3+ AP-1 → 4+）。
    - 护甲夹到 ≥2（自然 1 恒失败，救不到 1+）。invuln 不受 AP 修正。
    - 11版起掩体不再作用于保存骰（改为攻方 BS 惩罚，见 _gather_params 的掩体折算），
      故本函数不涉掩体，十版"AP0 对 3+ 甲无效"的掩体例外条款随之整体废弃。
    - 11版 05.04 特殊保护"同一颗保存骰同时对照 InSv 与 AP 后 Sv、任一达标即免伤"——一颗骰
      对照两阈值在数学上等价于取更小阈值 min(invuln, armor)，故此处返回二者更优即精确
      （自然 1 必失败由调用方 `save_roll != 1` 保证）。
    """
    armor = sv - ap
    if armor < 2:
        armor = 2
    if invuln is not None and invuln < armor:
        return invuln
    return armor


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
    # P7 加固（评审 F2）：未知 tag 静默返回 False = 效果静默失效（攻方侧零披露），
    # 是 CLAUDE.md 明令的静默降级缝——改为 raise，让 DSL 录入笔误在测试期就炸出来。
    raise ValueError(f"未知 Effect condition tag: {tag!r}（来源条件 {condition!r}）")


@dataclass
class _WeaponParams:
    """一把武器在当前态势下解算出的生效参数（把 Effect 汇成标量开关）。"""
    rf_expr: object = None         # DiceExpr | None（rapid fire X，X 可为骰子）
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


def _gather_params(w: WeaponProfile, stance: Stance, target: TargetProfile) -> _WeaponParams:
    p = _WeaponParams(cover=stance.target_in_cover)
    hit_pos = hit_neg = 0        # 命中修正分正负累计（[PSYCHIC] 只忽略负修正）
    bs_pos = bs_neg = 0          # P7：BS 特征值修正另立通道，分正负累计（同 PSYCHIC 有利方向语义）
    for e in w.effects:
        ok = _cond_true(e.condition, stance, target)
        if e.phase == "attacks":
            if e.op == "modify" and ok:
                p.rf_expr = e.params[0]           # DiceExpr（rapid fire）
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
    # BS 特征值净变化不夹取（上限条款语料缺页，spec D2 按无上限实现并披露）
    p.hit_mod = max(-1, min(1, hit_pos + hit_neg))
    p.bs_delta = bs_pos + bs_neg
    p.wound_mod = max(-1, min(1, p.wound_mod))
    return p


def _sample_damage(dmg_expr, melta_expr, rng, n, k, dmg_reduction) -> np.ndarray:
    """采样伤害 D（+melta，melta 可为骰子）后减伤夹 ≥1。"""
    dmg = sample_dice(dmg_expr, rng, (n, k)).astype(np.int64)
    if melta_expr is not None:
        dmg = dmg + sample_dice(melta_expr, rng, (n, k)).astype(np.int64)
    return (np.maximum(dmg - dmg_reduction, 1) if dmg_reduction > 0
            else np.maximum(dmg, 1))


def _wound_save_damage(
    mask: np.ndarray, rng: np.random.Generator, n: int,
    wt: int, crit_wound_thr: int, wound_mod: int, twin: bool, has_dev: bool,
    sv_need: int, dmg_expr, melta_expr, dmg_reduction: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """给定"进入致伤掷骰"的攻击掩码，产出正常伤害/致命池伤害数组 + 漏斗计数。"""
    k = mask.shape[1]
    zc = np.zeros(n, dtype=np.int64)
    if k == 0:
        z = np.zeros((n, 0), dtype=np.int64)
        return z, z, zc, zc, zc

    def _wound_ok(roll):
        return mask & (roll != 1) & ((roll >= crit_wound_thr) | (roll + wound_mod >= wt))

    roll = rng.integers(1, _FACES + 1, size=(n, k), dtype=np.int64)
    if twin:                                     # twin-linked：重骰失败的致伤骰（整颗替换）
        roll2 = rng.integers(1, _FACES + 1, size=(n, k), dtype=np.int64)
        roll = np.where(mask & ~_wound_ok(roll), roll2, roll)

    crit = mask & (roll >= crit_wound_thr) & (roll != 1)
    wound_ok = _wound_ok(roll)
    if has_dev:
        to_mortal = crit                          # 暴击造伤入致命池（跳保存）
        normal = wound_ok & ~crit
    else:
        to_mortal = np.zeros_like(mask)
        normal = wound_ok

    save_roll = rng.integers(1, _FACES + 1, size=(n, k), dtype=np.int64)
    saved = normal & (save_roll != 1) & (save_roll >= sv_need)
    unsaved = normal & ~saved

    # dev 致命池不吃减伤（11版24.10+06.02）：暴击致伤即结束攻击序列、直接对单位施加
    # 致命伤，从未进入伤害分配步骤——挂在分配上的「受伤-1」类减伤只作用于正常伤害；
    # melta 属 D 特性修正，两路都计。
    dmg_raw = _sample_damage(dmg_expr, melta_expr, rng, n, k, 0)
    dmg_normal = (np.maximum(dmg_raw - dmg_reduction, 1)
                  if dmg_reduction > 0 else dmg_raw)
    normal_dmg = np.where(unsaved, dmg_normal, 0)
    mortal_dmg = np.where(to_mortal, dmg_raw, 0)
    return (normal_dmg, mortal_dmg,
            wound_ok.sum(axis=1).astype(np.int64),
            unsaved.sum(axis=1).astype(np.int64),
            to_mortal.sum(axis=1).astype(np.int64))


def _autowound_save_damage(
    mask: np.ndarray, rng: np.random.Generator, n: int,
    sv_need: int, dmg_expr, melta_expr, dmg_reduction: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """lethal hits 暴击命中 → 自动致伤（跳致伤掷骰、不触发 dev）：直接走保存+伤害。"""
    k = mask.shape[1]
    zc = np.zeros(n, dtype=np.int64)
    if k == 0:
        return np.zeros((n, 0), dtype=np.int64), zc, zc
    save_roll = rng.integers(1, _FACES + 1, size=(n, k), dtype=np.int64)
    saved = mask & (save_roll != 1) & (save_roll >= sv_need)
    unsaved = mask & ~saved
    dmg = _sample_damage(dmg_expr, melta_expr, rng, n, k, dmg_reduction)
    return (np.where(unsaved, dmg, 0),
            mask.sum(axis=1).astype(np.int64),
            unsaved.sum(axis=1).astype(np.int64))


def _target_effect_value(target: TargetProfile, op: str, stance: Stance) -> Optional[int]:
    """守方顶层效果取值（fnp / damage_reduction）。

    P7-PR4 修复：①condition 不再被无视——DSL 注入的条件式守方效果（如仅射击阶段的
    FNP）必须过 _cond_true 才计入（此前首个匹配 op 的效果无条件生效=错编温床）；
    ②多来源取更优（fnp 阈值取小、减伤取大）而非首匹配——手动开关与 DSL 同时给
    fnp 时不再依赖 effects 顺序。
    """
    best = None
    for e in target.effects:
        if e.op != op or not e.params:
            continue
        if not _cond_true(e.condition, stance, target):
            continue
        v = int(e.params[0])
        if best is None:
            best = v
        else:
            best = min(best, v) if op == "fnp" else max(best, v)
    return best


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
#     （P7-PR4 inject_target 防守向通道：DSL 授予无效保护/护甲改善）。
# 其余 phase/op（如 wound 阶段的防守修正）当前没有消费者——列入报告注解透传。
def _target_effect_consumed(e) -> bool:
    if e.op in ("fnp", "damage_reduction"):
        return True
    if e.phase == "hit" and e.op in ("modify", "bs_improve"):
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


# ---------------------------------------------------------------------------
# 逐迭代结果容器
# ---------------------------------------------------------------------------
@dataclass
class SimRaw:
    """N 次迭代的逐次原始产出（report.py 负责聚合成 SimReport）。"""
    kills: np.ndarray            # (N,) 击杀模型数
    damage: np.ndarray           # (N,) 有效移除伤害（不含溢出浪费）
    wiped: np.ndarray            # (N,) bool 是否团灭
    attacks: np.ndarray          # (N,) 总攻击数
    hits: np.ndarray             # (N,) 命中数
    wounds: np.ndarray           # (N,) 致伤数（正常+暴击造伤）
    unsaved: np.ndarray          # (N,) 进伤害分配的实例数（未过保正常 + 致命池）
    mortals: np.ndarray          # (N,) 致命池实例数（dev 暴击造伤）
    seed: int
    iterations: int


# ---------------------------------------------------------------------------
# 单武器结算 → (正常伤害 (N,A), 致命池伤害 (N,A), funnel 计数)
# ---------------------------------------------------------------------------
def _resolve_weapon(
    w: WeaponProfile,
    target: TargetProfile,
    stance: Stance,
    rng: np.random.Generator,
    n: int,
    fnp_thresh: Optional[int],
    dmg_reduction: int,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    p = _gather_params(w, stance, target)
    count = int(w.count)
    empty = np.zeros((n, 0), dtype=np.int64)
    zeros = np.zeros(n, dtype=np.int64)
    if count <= 0:                       # 0 个模型持此武器 → 不开火（非 max(...,1) 幽灵开火）
        return empty, empty, {"attacks": zeros, "hits": zeros,
                              "wounds": zeros, "unsaved": zeros, "mortals": zeros}

    # ① Attacks：每模型掷 A，+rapid fire（半射程，X 可为骰子）
    #   +blast X / cleave X（每满 5 目标模型 +X，11版24.05/24.06）
    atk = sample_dice(w.attacks, rng, (n, count)).astype(np.int64)
    if p.rf_expr is not None:
        atk = atk + sample_dice(p.rf_expr, rng, (n, count)).astype(np.int64)
    if p.blast_x:
        atk = atk + p.blast_x * (int(target.models) // 5)
    n_attacks = np.maximum(atk.sum(axis=1), 0).astype(np.int64)   # 防御性夹 ≥0（真实武器不会负）
    max_a = int(n_attacks.max())
    if max_a == 0:
        return empty, empty, {"attacks": n_attacks, "hits": zeros,
                              "wounds": zeros, "unsaved": zeros, "mortals": zeros}

    active = np.arange(max_a)[None, :] < n_attacks[:, None]      # (n, max_a)

    # ② Hit：torrent/无 BS → 自动命中（不产生暴击命中，故无 sustained/lethal）；
    #         间接开火（11版24.19+10.07）→ 命中与 BS 无关的固定未修正阈值；
    #         否则自然骰（1 必失）+ 修正（±1）+ 暴击命中阈值（conversion 可降到 4+）
    auto_hit = p.torrent or w.bs_ws is None
    if auto_hit:
        hit = active.copy()
        crit_hit = np.zeros_like(hit)
    elif p.indirect_fixed:
        # 11版间接开火：未修正 1-5 失败（仅 6 命中）；stance.stationary（作为
        # 「本回合驻停+有友军可见目标」的代理条件）时改善为 1-3 失败（4+ 命中）。
        # 命中修正与 ±1 夹紧对 indirect 不适用（阈值即最终判定）；
        # 未修正 6 仍按暴击阈值算暴击命中（sustained/lethal 照常触发）。
        need = 4 if stance.stationary else 6
        hr = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
        if p.hit_reroll_fail:
            rr = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
            hr = np.where(active & (hr < need), rr, hr)
        hit = active & (hr >= need)
        crit_hit = hit & (hr >= p.crit_hit_thr) & (hr != 1)
    else:
        hr = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
        # P7：先特征值后修正（11版 1.05 次序）——BS 特征值净变化 bs_delta 改阈值本身
        # （改善为正 → 阈值变小），命中骰修正 hit_mod 已独立夹 ±1。BS 改善到 1+ 时
        # 由 `hr != 1` 涌现出等效 2+ 下限，无需另行钳制（自然 1 恒失手）。
        bs_need = w.bs_ws - p.bs_delta
        if p.hit_reroll_fail:
            # P7-PR3：命中失败重骰（最优策略只重骰失败骰；不建模"重骰非暴击钓
            # sustained"的进阶策略）。重骰用替换法：失败位置换新骰后统一判定，
            # 暴击判定自然基于重骰后的骰面（重骰出的 6 照常触发 sustained/lethal）
            first = (hr != 1) & ((hr >= p.crit_hit_thr) | (hr + p.hit_mod >= bs_need))
            rr = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
            hr = np.where(active & ~first, rr, hr)
        hit = active & (hr != 1) & ((hr >= p.crit_hit_thr) | (hr + p.hit_mod >= bs_need))
        crit_hit = hit & (hr >= p.crit_hit_thr) & (hr != 1)

    # sustained hits：每个暴击命中 +X 命中（X 可为骰子）；这些额外命中走正常致伤
    total_extra = zeros
    extra_mask = np.zeros((n, 0), dtype=bool)
    if p.sustained is not None and not auto_hit:
        xexpr = p.sustained if isinstance(p.sustained, DiceExpr) else DiceExpr(k=int(p.sustained))
        xper = (np.full((n, max_a), xexpr.k, dtype=np.int64)
                if xexpr.is_constant else sample_dice(xexpr, rng, (n, max_a)).astype(np.int64))
        total_extra = np.where(crit_hit, xper, 0).sum(axis=1).astype(np.int64)
        max_extra = int(total_extra.max())
        if max_extra:
            extra_mask = np.arange(max_extra)[None, :] < total_extra[:, None]

    # lethal hits：暴击命中 → 自动致伤（跳致伤掷骰、不触发 dev）
    if p.lethal:
        lethal_mask = crit_hit
        base_to_wound = hit & ~crit_hit
    else:
        lethal_mask = np.zeros_like(hit)
        base_to_wound = hit

    # ③-⑥ Wound / Save / Damage（P7-PR3：AP 特征值改善——AP 存负值，改善=更负；
    #   P7-PR4：S/Sv 特征值改善 + 守方 DSL 授予 invuln 与 profile 自带取更优）
    wt = wound_target(w.strength + p.s_improve, target.t)
    inv = target.invuln
    if p.target_invuln is not None:
        inv = int(p.target_invuln) if inv is None else min(inv, int(p.target_invuln))
    sv_need = effective_save(target.sv - p.sv_improve, w.ap - p.ap_improve, inv)
    to_wound = np.concatenate([base_to_wound, extra_mask], axis=1)

    nd1, md1, w1, u1, m1 = _wound_save_damage(
        to_wound, rng, n, wt, p.crit_wound_thr, p.wound_mod, p.twin, p.has_dev,
        sv_need, w.damage, p.melta_expr, dmg_reduction)
    nd2, w2, u2 = _autowound_save_damage(
        lethal_mask, rng, n, sv_need, w.damage, p.melta_expr, dmg_reduction)

    normal_dmg = np.concatenate([nd1, nd2], axis=1)
    mortal_dmg = md1

    funnel = {
        "attacks": n_attacks,
        "hits": (hit.sum(axis=1).astype(np.int64) + total_extra),
        "wounds": (w1 + w2),
        "unsaved": (u1 + u2 + m1),
        "mortals": m1,
    }
    return normal_dmg, mortal_dmg, funnel


def _fnp_dice(rng: np.random.Generator, dmg_arr: np.ndarray) -> np.ndarray:
    """为伤害数组每点预掷 FNP 骰面：(N, K, Dmax)，Dmax≥每实例伤害值以覆盖全部点。"""
    n, k = dmg_arr.shape
    dmax = int(dmg_arr.max()) if k else 0
    if dmax < 1:
        return np.zeros((n, max(k, 0), 1), dtype=np.int64)
    return rng.integers(1, _FACES + 1, size=(n, k, dmax), dtype=np.int64)


def _select_weapons(loadout: Tuple, phase: str) -> List[WeaponProfile]:
    want_melee = phase == "melee"
    return [w for w in loadout if w.is_melee == want_melee]


# ---------------------------------------------------------------------------
# 顶层：整支单位一次攻击序列 × N 迭代
# ---------------------------------------------------------------------------
def run_sequence(
    attacker: AttackerProfile,
    target: TargetProfile,
    stance: Stance,
    n: int = 10000,
    seed: int = 1234,
) -> SimRaw:
    """跑 N 次攻击序列（版本口径见模块 docstring），返回逐次原始产出。
    只依赖 contracts + parse + 分配核。"""
    # 退化目标（无模型/无生命）→ 全零，不打幽灵模型（非法输入不静默夹成 1）
    if int(target.models) <= 0 or int(target.w) <= 0:
        z = np.zeros(n, dtype=np.int64)
        return SimRaw(kills=z, damage=z, wiped=np.zeros(n, dtype=bool),
                      attacks=z, hits=z, wounds=z, unsaved=z, mortals=z,
                      seed=seed, iterations=n)

    rng = np.random.default_rng(seed)
    weapons = _select_weapons(attacker.loadout, stance.phase)

    fnp_thresh = _target_effect_value(target, "fnp", stance)
    dmg_reduction = _target_effect_value(target, "damage_reduction", stance) or 0

    normal_blocks: List[np.ndarray] = []
    mortal_blocks: List[np.ndarray] = []
    funnel_sum = {k: np.zeros(n, dtype=np.int64)
                  for k in ("attacks", "hits", "wounds", "unsaved", "mortals")}

    for w in weapons:
        nd, md, fn = _resolve_weapon(w, target, stance, rng, n, fnp_thresh, dmg_reduction)
        normal_blocks.append(nd)
        mortal_blocks.append(md)
        for k in funnel_sum:
            funnel_sum[k] = funnel_sum[k] + fn[k]

    zeros2 = np.zeros((n, 0), dtype=np.int64)
    normal_dmg = np.concatenate(normal_blocks, axis=1) if normal_blocks else zeros2
    mortal_dmg = np.concatenate(mortal_blocks, axis=1) if mortal_blocks else zeros2

    normal_fnp = _fnp_dice(rng, normal_dmg)
    mortal_fnp = _fnp_dice(rng, mortal_dmg)

    alloc = allocate_numpy(
        m_models=max(int(target.models), 1),
        w_wounds=max(int(target.w), 1),
        normal_dmg=normal_dmg, normal_fnp=normal_fnp,
        mortal_dmg=mortal_dmg, mortal_fnp=mortal_fnp,
        fnp_thresh=fnp_thresh,
    )

    return SimRaw(
        kills=alloc["kills"], damage=alloc["effective"], wiped=alloc["wiped"],
        attacks=funnel_sum["attacks"], hits=funnel_sum["hits"],
        wounds=funnel_sum["wounds"], unsaved=funnel_sum["unsaved"],
        mortals=funnel_sum["mortals"], seed=seed, iterations=n,
    )
