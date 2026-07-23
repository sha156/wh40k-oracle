"""scripts/gen_dsl_condition_anchor.py — 生成 dsl_payloads 门控结构锚快照。

gnhf 审查模块 8 F1/F2：524 条带 condition 门的载荷中 198 条在全部测试里零引用、
43 条相位门「双保险全缺」——对早期阵营 payload 的误编辑（删门 / phase_melee→
phase_shooting / 裸 target_has_keyword 回潮）会静默通过。这正是历史五次同型 HIGH
（漏阶段门过度施加）的回归通道。

本脚本把全库「带门条目 → 各 effect 的 condition 元组」快照锁进
tests/data/dsl_condition_anchor.json；tests/test_dsl_condition_anchor.py 逐键对账。
改动任何门都必须重跑本脚本更新清单，diff 会把结构变化显式亮给审阅者。

用法：
    .\\.venv\\Scripts\\python.exe scripts/gen_dsl_condition_anchor.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = ROOT / "dsl_payloads"
ANCHOR_PATH = ROOT / "tests" / "data" / "dsl_condition_anchor.json"


def build_anchor() -> dict:
    """全库扫描：{ "<faction文件名>:<table>:<id>": [sorted condition lists] }。

    只收「至少一个 effect 带非空 condition」的条目——快照键集本身就是门控条目全集，
    删门（键消失）与加门（键新增）双向都会被对账测试逮住。
    """
    anchor: dict = {}
    for path in sorted(PAYLOAD_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            conditions = [list(f.get("condition") or [])
                          for f in entry.get("effects") or []]
            if not any(conditions):
                continue
            key = f"{path.stem}:{entry.get('table')}:{entry.get('id')}"
            if key in anchor:
                raise SystemExit(f"锚键冲突（同文件同表同 id 出现两次）：{key}")
            anchor[key] = sorted(conditions)
    return anchor


def main() -> int:
    anchor = build_anchor()
    ANCHOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANCHOR_PATH.write_text(
        json.dumps(anchor, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"锚清单已写入 {ANCHOR_PATH}（{len(anchor)} 条门控条目）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
