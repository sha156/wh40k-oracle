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

# P7-PR7 拆分：条件求值/参数聚合/消费点注册表移居 effect_params（公共契约经此 re-export，
# dsl.py/engine.py/测试仍从本模块导入这些符号——勿改成直连以免破坏白名单唯一真源口径）
from engines.simulator.effect_params import (  # noqa: F401
    ATTACKER_CONSUMED,
    KNOWN_CONDITION_TAGS,
    TARGET_CONSUMED,
    _cond_true,
    _gather_params,
    _target_effect_consumed,
    _WeaponParams,
    unconsumed_attacker_effect_notes,
    unconsumed_target_effect_notes,
)

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


def _sample_damage(dmg_expr, dmg_mod_exprs, rng, n, k, dmg_reduction) -> np.ndarray:
    """采样伤害 D（+伤害加值：melta / DSL "+1 D"，逐来源累加，可为骰子）后减伤夹 ≥1。"""
    dmg = sample_dice(dmg_expr, rng, (n, k)).astype(np.int64)
    for me in dmg_mod_exprs or ():      # 兼容旧调用方传 None（=无伤害加值）
        dmg = dmg + sample_dice(me, rng, (n, k)).astype(np.int64)
    return (np.maximum(dmg - dmg_reduction, 1) if dmg_reduction > 0
            else np.maximum(dmg, 1))


def _wound_save_damage(
    mask: np.ndarray, rng: np.random.Generator, n: int,
    wt: int, crit_wound_thr: int, wound_mod: int, twin: bool, has_dev: bool,
    sv_need: int, dmg_expr, dmg_mod_exprs, dmg_reduction: int,
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
    dmg_raw = _sample_damage(dmg_expr, dmg_mod_exprs, rng, n, k, 0)
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
    sv_need: int, dmg_expr, dmg_mod_exprs, dmg_reduction: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """lethal hits 暴击命中 → 自动致伤（跳致伤掷骰、不触发 dev）：直接走保存+伤害。"""
    k = mask.shape[1]
    zc = np.zeros(n, dtype=np.int64)
    if k == 0:
        return np.zeros((n, 0), dtype=np.int64), zc, zc
    save_roll = rng.integers(1, _FACES + 1, size=(n, k), dtype=np.int64)
    saved = mask & (save_roll != 1) & (save_roll >= sv_need)
    unsaved = mask & ~saved
    dmg = _sample_damage(dmg_expr, dmg_mod_exprs, rng, n, k, dmg_reduction)
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
    for rf in p.rf_exprs:
        atk = atk + sample_dice(rf, rng, (n, count)).astype(np.int64)
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
    s_final = w.strength + p.s_improve
    # P7-PR8：T 特征值净算（攻方 t_worsen 恶化 − 守方 t_improve 改善），下限钳 ≥1
    # （核心规则特征值不低于 1）。T-1 与 S+1 在 2T/T/2 边界不等价，必须真 T 通道
    t_final = max(1, int(target.t) - p.t_worsen + p.t_improve)
    wt = wound_target(s_final, t_final)
    # P7-PR6：S/T 延迟分量在最终 S（含 s_improve）处判定——誓言 Accept Any Challenge
    # 只在 S≤T 时给 +1（RAW 特征值先改后比：S4+2 改到 S6 打 T5 不再享受）；
    # Purge and Sanctify 只在 S>T 时给 -1。成立分量与基础分量合并后统一夹 ±1。
    # P7-PR8 起比较基准同为最终 T（RAW 修正后特征值互比）
    wound_mod = p.wound_mod
    deferred = ((p.wound_mod_s_lte_t if s_final <= t_final else 0)
                + (p.wound_mod_s_gt_t if s_final > t_final else 0))
    if deferred:
        wound_mod = max(-1, min(1, p.wound_mod_raw + deferred))
    inv = target.invuln
    if p.target_invuln is not None:
        inv = int(p.target_invuln) if inv is None else min(inv, int(p.target_invuln))
    # P7-PR7 审查 HIGH：AP 净算后夹 ≤0——守方「恶化 AP」不能把 AP0 武器推成正 AP
    # 给护甲反向加成（核心规则修改特征值口径：AP 恶化以 0 为界；攻方改善方向更负
    # 不受此夹取影响）
    sv_need = effective_save(target.sv - p.sv_improve,
                             min(0, w.ap - p.ap_improve), inv)
    to_wound = np.concatenate([base_to_wound, extra_mask], axis=1)

    nd1, md1, w1, u1, m1 = _wound_save_damage(
        to_wound, rng, n, wt, p.crit_wound_thr, wound_mod, p.twin, p.has_dev,
        sv_need, w.damage, p.dmg_mod_exprs, dmg_reduction)
    nd2, w2, u2 = _autowound_save_damage(
        lethal_mask, rng, n, sv_need, w.damage, p.dmg_mod_exprs, dmg_reduction)

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
