"""tests/test_dsl_condition_anchor.py — dsl_payloads 门控结构锚全局对账。

gnhf 审查模块 8 F1/F2：早期阵营（PR4-PR25）198 条门控载荷零测试引用 + 43 条相位门
双保险全缺——删门/换相位/裸关键词门回潮都静默通过，正是历史五次同型 HIGH（漏阶段门
过度施加）的回归通道。本测试把全库 524 条门控条目的 condition 结构逐键钉死在
tests/data/dsl_condition_anchor.json；有意改门时跑
`python scripts/gen_dsl_condition_anchor.py` 更新清单，让结构变化显式进 diff。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANCHOR_PATH = ROOT / "tests" / "data" / "dsl_condition_anchor.json"


def _live_anchor() -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from gen_dsl_condition_anchor import build_anchor
    finally:
        sys.path.pop(0)
    return build_anchor()


def test_condition_anchor_matches_snapshot():
    snapshot = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    live = _live_anchor()

    removed = sorted(set(snapshot) - set(live))
    added = sorted(set(live) - set(snapshot))
    changed = sorted(k for k in set(snapshot) & set(live)
                     if snapshot[k] != live[k])
    problems = []
    if removed:
        problems.append(f"门被删除（条目从门控集消失）{len(removed)} 条: {removed[:5]}")
    if added:
        problems.append(f"新增门控条目未入锚清单 {len(added)} 条: {added[:5]}")
    for k in changed[:5]:
        problems.append(f"门结构变化 {k}: 锚 {snapshot[k]} → 现 {live[k]}")
    if len(changed) > 5:
        problems.append(f"……另有 {len(changed) - 5} 条门结构变化")
    assert not problems, (
        "dsl_payloads 门控结构与锚清单不一致——若为有意改动，跑 "
        "`python scripts/gen_dsl_condition_anchor.py` 更新清单并在 review 里核对 diff：\n"
        + "\n".join(problems))


def test_condition_anchor_snapshot_sanity():
    # 锚清单本身的底线：门控条目数不缩水（审查时点 524；只增不减，防清单被整体重写掏空）
    snapshot = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    assert len(snapshot) >= 524, len(snapshot)
    # 每个值都是「condition 列表的列表」且至少一个非空（键集定义 = 带门条目）
    for key, conds in snapshot.items():
        assert isinstance(conds, list) and any(conds), key
