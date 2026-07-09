"""SimRaw → SimReport 聚合层（P4-d）。

只吃 sequence.py 的逐次原始数组 + 点数/声明清单，产出可读报告：
期望伤害/击杀/团灭率、分布（p10/p50/p90 + 直方图）、阶段漏斗、性价比（每 100 点）。
纯聚合、无随机、只依赖 contracts + numpy。
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

from engines.simulator.contracts import SimReport
from engines.simulator.sequence import SimRaw


def _percentiles(arr: np.ndarray) -> dict:
    return {
        "p10": float(np.percentile(arr, 10)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
    }


def _histogram(arr: np.ndarray) -> dict:
    """离散计数直方图 {值: 概率}（击杀数是小整数，直接 bincount）。"""
    counts = np.bincount(arr.astype(np.int64))
    total = arr.shape[0]
    return {int(v): round(float(c) / total, 4) for v, c in enumerate(counts) if c}


def build_report(
    raw: SimRaw,
    points: Optional[int] = None,
    modeled_effects: Optional[Sequence[str]] = None,
    not_modeled: Optional[Sequence[str]] = None,
    bias_notes: Optional[Sequence[str]] = None,
    sensitivity_hint: Optional[Sequence[str]] = None,
) -> SimReport:
    n = raw.iterations
    exp_damage = float(raw.damage.mean())
    exp_kills = float(raw.kills.mean())
    wipe = float(raw.wiped.mean())

    dist = _percentiles(raw.kills)
    dist["histogram"] = _histogram(raw.kills)
    dist["damage"] = _percentiles(raw.damage)

    funnel = {
        "attacks": float(raw.attacks.mean()),
        "hits": float(raw.hits.mean()),
        "wounds": float(raw.wounds.mean()),
        "unsaved": float(raw.unsaved.mean()),
        "damage": exp_damage,
        "kills": exp_kills,
    }

    efficiency: dict = {}
    if points and points > 0:
        efficiency = {
            "points": int(points),
            "damage_per_100": round(exp_damage / points * 100, 3),
            "kills_per_100": round(exp_kills / points * 100, 4),
        }

    return SimReport(
        expected_damage=round(exp_damage, 3),
        expected_kills=round(exp_kills, 3),
        wipe_probability=round(wipe, 4),
        distribution=dist,
        funnel={k: round(v, 3) for k, v in funnel.items()},
        efficiency=efficiency,
        modeled_effects=list(modeled_effects or []),
        not_modeled=list(not_modeled or []),
        bias_notes=list(bias_notes or []),
        sensitivity_hint=list(sensitivity_hint or []),
        seed=raw.seed,
        iterations=n,
    )
