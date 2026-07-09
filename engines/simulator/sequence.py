"""十版逐骰攻击序列 pipeline（向量化核，P4-b 裸序列 + 通用 Effect 接缝）。

依赖方向：**只 import contracts / parse / _spike_allocation**，绝不碰 sqlite/app/streamlit
（见 spec 第五节），保证脱库单测、P8 可复用。

设计（spec 第七节）：对每个"攻击槽"在 N 维上向量化，在攻击槽维度上小循环。
每把武器单独结算，产出该武器的"未过保正常伤害"与"暴击造伤（dev 致命池）"两组
(N, A) 伤害数组（未命中/未过伤/被保存的槽 = 0）；跨武器沿槽维拼接后，正常伤害在前、
致命池在后，喂进已 spike 验证的 `allocate_numpy` 做不溢出+已损伤优先+逐点FNP+致命池分配。

P4-b 覆盖：attacks(裸采样) / hit(BS-WS,自然骰) / wound(S-T查表,自然骰) / save(AP+掩体+invuln)
/ damage(采样+减伤夹≥1) / fnp / dev 致命池 / 防守开关(FNP·减伤·掩体)。
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


def effective_save(sv: int, ap: int, invuln: Optional[int],
                   cover: bool, ignores_cover: bool) -> int:
    """有效保存所需骰面（越小越易保）：护甲经 AP/掩体修正后与 invuln 取更优。

    - AP 存负值，`sv - ap` = 护甲变差（3+ AP-1 → 4+）。
    - 掩体 +1（护甲 -1 所需），但【Sv≤3+ 对 AP0 不享受】、ignores_cover 禁掩体。
    - 护甲夹到 ≥2（自然 1 恒失败，救不到 1+）。invuln 不受 AP/掩体。
    """
    armor = sv - ap
    benefit = cover and not ignores_cover and not (sv <= 3 and ap == 0)
    if benefit:
        armor -= 1
    if armor < 2:
        armor = 2
    if invuln is not None and invuln < armor:
        return invuln
    return armor


# ---------------------------------------------------------------------------
# Effect 读取（P4-c：词条按阶段生效）
# ---------------------------------------------------------------------------
def _cond_true(condition: Tuple, stance: Stance, target: TargetProfile) -> bool:
    """Effect.condition 是否在本次态势/目标下成立。"""
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
    if tag == "phase_shooting":          # P5-a：Stealth 等仅对射击生效
        return stance.phase == "shooting"
    if tag == "target_has_keyword":
        return len(condition) > 1 and condition[1] in target.keywords
    return False


@dataclass
class _WeaponParams:
    """一把武器在当前态势下解算出的生效参数（把 Effect 汇成标量开关）。"""
    rf_expr: object = None         # DiceExpr | None（rapid fire X，X 可为骰子）
    blast: bool = False
    melta_expr: object = None      # DiceExpr | None（melta X，X 可为骰子）
    crit_hit_thr: int = _FACES
    sustained: object = None      # DiceExpr | None
    lethal: bool = False
    torrent: bool = False
    hit_mod: int = 0
    crit_wound_thr: int = _FACES
    twin: bool = False
    has_dev: bool = False
    wound_mod: int = 0
    ignores_cover: bool = False
    cover: bool = False


def _gather_params(w: WeaponProfile, stance: Stance, target: TargetProfile) -> _WeaponParams:
    p = _WeaponParams(cover=stance.target_in_cover)
    for e in w.effects:
        ok = _cond_true(e.condition, stance, target)
        if e.phase == "attacks":
            if e.op == "modify" and ok:
                p.rf_expr = e.params[0]           # DiceExpr（rapid fire）
            elif e.op == "blast":
                p.blast = True
        elif e.phase == "hit":
            if e.op == "extra_hits":
                p.sustained = e.params[0]
            elif e.op == "auto_wound":
                p.lethal = True
            elif e.op == "auto_hit":
                p.torrent = True
            elif e.op == "crit_threshold" and ok:
                p.crit_hit_thr = min(p.crit_hit_thr, int(e.params[0]))
            elif e.op == "modify" and ok:
                p.hit_mod += int(e.params[0])
        elif e.phase == "wound":
            if e.op == "mortal_pool":
                p.has_dev = True
            elif e.op == "crit_threshold" and ok:
                p.crit_wound_thr = min(p.crit_wound_thr, int(e.params[0]))
            elif e.op == "reroll":
                p.twin = True
            elif e.op == "modify" and ok:
                p.wound_mod += int(e.params[0])
        elif e.phase == "damage":
            if e.op == "modify" and ok:
                p.melta_expr = e.params[0]        # DiceExpr（melta）
        elif e.phase == "save":
            if e.op == "ignores_cover":
                p.ignores_cover = True
            elif e.op == "cover" and ok:
                p.cover = True
    # P5-a：守方防守 Effect 里改攻方命中的修正（如 Stealth：射击命中 -1）并入，再统一夹取。
    # 十版修正上限是对【总和】夹 ±1，故必须在 clamp 之前叠加（Stealth -1 与 heavy +1 可抵消为 0）。
    for e in target.effects:
        if e.phase == "hit" and e.op == "modify" and _cond_true(e.condition, stance, target):
            p.hit_mod += int(e.params[0])
    # 命中/致伤修正各自夹到 ±1（十版修正上限）
    p.hit_mod = max(-1, min(1, p.hit_mod))
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

    dmg = _sample_damage(dmg_expr, melta_expr, rng, n, k, dmg_reduction)
    normal_dmg = np.where(unsaved, dmg, 0)
    mortal_dmg = np.where(to_mortal, dmg, 0)
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


def _target_effect_value(target: TargetProfile, op: str) -> Optional[int]:
    for e in target.effects:
        if e.op == op and e.params:
            p = e.params[0]
            return int(p)
    return None


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

    # ① Attacks：每模型掷 A，+rapid fire（半射程，X 可为骰子）+blast（每满 5 目标模型）
    atk = sample_dice(w.attacks, rng, (n, count)).astype(np.int64)
    if p.rf_expr is not None:
        atk = atk + sample_dice(p.rf_expr, rng, (n, count)).astype(np.int64)
    if p.blast:
        atk = atk + (int(target.models) // 5)
    n_attacks = np.maximum(atk.sum(axis=1), 0).astype(np.int64)   # 防御性夹 ≥0（真实武器不会负）
    max_a = int(n_attacks.max())
    if max_a == 0:
        return empty, empty, {"attacks": n_attacks, "hits": zeros,
                              "wounds": zeros, "unsaved": zeros, "mortals": zeros}

    active = np.arange(max_a)[None, :] < n_attacks[:, None]      # (n, max_a)

    # ② Hit：torrent/无 BS → 自动命中（不产生暴击命中，故无 sustained/lethal）；
    #         否则自然骰（1 必失）+ 修正（±1）+ 暴击命中阈值（conversion 可降到 4+）
    auto_hit = p.torrent or w.bs_ws is None
    if auto_hit:
        hit = active.copy()
        crit_hit = np.zeros_like(hit)
    else:
        hr = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
        hit = active & (hr != 1) & ((hr >= p.crit_hit_thr) | (hr + p.hit_mod >= w.bs_ws))
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

    # ③-⑥ Wound / Save / Damage
    wt = wound_target(w.strength, target.t)
    sv_need = effective_save(target.sv, w.ap, target.invuln, p.cover, p.ignores_cover)
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
    """跑 N 次十版攻击序列，返回逐次原始产出。只依赖 contracts + parse + 分配核。"""
    # 退化目标（无模型/无生命）→ 全零，不打幽灵模型（非法输入不静默夹成 1）
    if int(target.models) <= 0 or int(target.w) <= 0:
        z = np.zeros(n, dtype=np.int64)
        return SimRaw(kills=z, damage=z, wiped=np.zeros(n, dtype=bool),
                      attacks=z, hits=z, wounds=z, unsaved=z, mortals=z,
                      seed=seed, iterations=n)

    rng = np.random.default_rng(seed)
    weapons = _select_weapons(attacker.loadout, stance.phase)

    fnp_thresh = _target_effect_value(target, "fnp")
    dmg_reduction = _target_effect_value(target, "damage_reduction") or 0

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
