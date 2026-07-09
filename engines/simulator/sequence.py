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
# Effect 读取（P4-b：dev / 防守开关；P4-c 扩展）
# ---------------------------------------------------------------------------
def _weapon_has(w: WeaponProfile, phase: str, op: str) -> bool:
    return any(e.phase == phase and e.op == op for e in w.effects)


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
    count = max(int(w.count), 1)

    # ① Attacks：每个持武器模型各掷 A，求和为本武器总攻击数
    atk = sample_dice(w.attacks, rng, (n, count))          # (n, count)
    n_attacks = atk.sum(axis=1).astype(np.int64)           # (n,)
    max_a = int(n_attacks.max())
    empty = np.zeros((n, 0), dtype=np.int64)
    if max_a == 0:
        zeros = np.zeros(n, dtype=np.int64)
        return empty, empty, {"attacks": n_attacks, "hits": zeros,
                              "wounds": zeros, "unsaved": zeros, "mortals": zeros}

    slot = np.arange(max_a)[None, :]                        # (1, max_a)
    active = slot < n_attacks[:, None]                      # (n, max_a) 有效攻击槽

    # ② Hit：torrent/自动命中（bs_ws=None）跳掷；否则自然骰（1 必失、6 必中）
    if w.bs_ws is None:
        hit = active.copy()
    else:
        hit_roll = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
        hit = active & (hit_roll != 1) & ((hit_roll == _FACES) | (hit_roll >= w.bs_ws))

    # ③ Wound：S-T 查表，自然骰（1 必失、6 恒为暴击造伤且必成功）
    wt = wound_target(w.strength, target.t)
    wound_roll = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
    crit_wound = hit & (wound_roll == _FACES)
    wound_ok = hit & (wound_roll != 1) & ((wound_roll == _FACES) | (wound_roll >= wt))

    has_dev = _weapon_has(w, "wound", "mortal_pool")
    if has_dev:
        to_mortal = crit_wound                              # 暴击造伤入致命池（跳保存）
        normal_wound = wound_ok & ~crit_wound
    else:
        to_mortal = np.zeros_like(hit)
        normal_wound = wound_ok

    # ④/⑤ Save：仅正常致伤走保存（致命池跳保存/invuln）
    ignores_cover = _weapon_has(w, "save", "ignores_cover")
    sv_need = effective_save(target.sv, w.ap, target.invuln,
                             stance.target_in_cover, ignores_cover)
    save_roll = rng.integers(1, _FACES + 1, size=(n, max_a), dtype=np.int64)
    saved = normal_wound & (save_roll != 1) & (save_roll >= sv_need)
    unsaved = normal_wound & ~saved

    # ⑥ Damage：采样 D；减伤后夹 ≥1（对致命池同样适用）
    dmg = sample_dice(w.damage, rng, (n, max_a)).astype(np.int64)
    if dmg_reduction > 0:
        dmg = np.maximum(dmg - dmg_reduction, 1)
    normal_dmg = np.where(unsaved, dmg, 0)
    mortal_dmg = np.where(to_mortal, dmg, 0)

    funnel = {
        "attacks": n_attacks,
        "hits": hit.sum(axis=1).astype(np.int64),
        "wounds": (normal_wound | to_mortal).sum(axis=1).astype(np.int64),
        "unsaved": (unsaved.sum(axis=1) + to_mortal.sum(axis=1)).astype(np.int64),
        "mortals": to_mortal.sum(axis=1).astype(np.int64),
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
