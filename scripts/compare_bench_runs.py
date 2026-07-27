"""逐题对比两次 qa_bench 产物的 verdict（判回归用，不看绝对分）。

用法：python scripts/compare_bench_runs.py <base.json> <new.json>

为什么必须逐题比而不是比总分：基准里有几道固定波动题（#41/#42 互换等），
总分持平也可能掩盖「一题转绿一题转红」。见 benchmarks/v3_edition11/README.md。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict


def _verdicts(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["id"]): item["verdict"] for item in data["details"]}


def main(argv) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    base, new = _verdicts(Path(argv[1])), _verdicts(Path(argv[2]))

    print("base 题数 {} / new 题数 {}".format(len(base), len(new)))
    only_base = sorted(set(base) - set(new), key=lambda x: int(x))
    only_new = sorted(set(new) - set(base), key=lambda x: int(x))
    if only_base:
        print("仅 base 有:", only_base)
    if only_new:
        print("仅 new 有:", only_new)

    changed = [(qid, base[qid], new[qid])
               for qid in sorted(set(base) & set(new), key=lambda x: int(x))
               if base[qid] != new[qid]]
    print("共有题 verdict 差异数: {}".format(len(changed)))
    for qid, b, n in changed:
        print("  #{}: {} -> {}".format(qid, b, n))

    for anchor in ("63", "109", "118"):
        if anchor in new:
            print("锚点 #{}: {} -> {}".format(
                anchor, base.get(anchor, "-"), new[anchor]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
