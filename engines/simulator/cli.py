"""最小命令行入口（开发期自测，非 UI）。

薄封装 agent.tools.simulate_combat（已含实体解析 + 装配 + 三失败路径），把结果
渲染成人读文本或 JSON。示例：
  python -m engines.simulator.cli "兽人 Warboss" "终结者小队" --phase melee --charge
  python -m engines.simulator.cli "Boyz" "Intercessor Squad" --loadout "Shoota:9,Slugga:1" --half-range
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Tuple


def _parse_loadout(text: Optional[str]) -> Optional[List[Tuple[str, int]]]:
    """'Shoota:9,Slugga:1' → [('Shoota',9),('Slugga',1)]。"""
    if not text:
        return None
    out: List[Tuple[str, int]] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, cnt = part.rpartition(":")
        out.append((name.strip(), int(cnt))) if name else out.append((part, 1))
    return out


def _fmt_report(rep: dict, indent: str = "") -> List[str]:
    lines = [
        f"{indent}期望伤害 {rep['expected_damage']}｜期望击杀 {rep['expected_kills']}"
        f"｜团灭率 {rep['wipe_probability'] * 100:.1f}%",
        f"{indent}漏斗 " + " → ".join(
            f"{k}:{rep['funnel'][k]}" for k in
            ("attacks", "hits", "wounds", "unsaved", "damage", "kills")),
    ]
    d = rep["distribution"]
    lines.append(f"{indent}击杀分布 p10/p50/p90 = {d['p10']}/{d['p50']}/{d['p90']}")
    if rep.get("efficiency"):
        e = rep["efficiency"]
        lines.append(f"{indent}性价比 每100点 伤害{e['damage_per_100']}/击杀{e['kills_per_100']}"
                     f"（{e['points']}点）")
    if rep["modeled_effects"]:
        lines.append(f"{indent}计入词条：" + "、".join(rep["modeled_effects"]))
    if rep["not_modeled"]:
        lines.append(f"{indent}未计入：" + "；".join(rep["not_modeled"][:4]))
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="engines.simulator.cli",
                                description="战锤40K 十版蒙特卡洛对战模拟")
    p.add_argument("attacker", help="攻方单位名（中/英/俗名）")
    p.add_argument("defender", help="守方单位名")
    p.add_argument("--phase", default="shooting", choices=["shooting", "melee"])
    p.add_argument("--charge", action="store_true")
    p.add_argument("--half-range", action="store_true", dest="half_range")
    p.add_argument("--cover", action="store_true")
    p.add_argument("--stationary", action="store_true")
    p.add_argument("--long-range", action="store_true", dest="long_range")
    p.add_argument("--indirect", action="store_true")
    p.add_argument("--attacker-models", type=int, dest="attacker_models")
    p.add_argument("--defender-models", type=int, dest="defender_models")
    p.add_argument("--loadout", help='攻方装配 "武器名:数量,..."（多模型单位必填）')
    p.add_argument("--defender-loadout", dest="defender_loadout",
                   help="守方装配（给了则做串行幸存反打）")
    p.add_argument("--fnp", type=int, help="守方无痛 X+")
    p.add_argument("--damage-reduction", type=int, dest="damage_reduction")
    p.add_argument("-n", type=int, default=8000, help="迭代次数（默认 8000）")
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = p.parse_args(argv)

    from agent.tools import simulate_combat

    options = {k: v for k, v in {
        "phase": args.phase, "charge": args.charge, "half_range": args.half_range,
        "cover": args.cover, "stationary": args.stationary,
        "long_range": args.long_range, "indirect": args.indirect,
        "attacker_models": args.attacker_models,
        "defender_models": args.defender_models,
        "loadout": _parse_loadout(args.loadout),
        "defender_loadout": _parse_loadout(args.defender_loadout),
        "fnp": args.fnp, "damage_reduction": args.damage_reduction,
        "n": args.n, "seed": args.seed,
    }.items() if v not in (None, False)}

    result = simulate_combat(args.attacker, args.defender, options)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if not result.get("ok"):
        print(f"[未完成] {result.get('note', '未知错误')}")
        if result.get("candidates"):
            print("  候选：" + "、".join(result["candidates"][:8]))
        if result.get("weapon_pool"):
            print("  该单位武器池（用 --loadout 指定）：" + "、".join(result["weapon_pool"]))
        return 1

    print(f"=== {result['attacker']} 打 {result['defender']}（{result['phase']}）===")
    if result.get("warning"):
        print(f"[提示] {result['warning']}")
    for line in _fmt_report(result["report"]):
        print(line)
    rev = result["report"].get("reverse")
    if rev:
        print("--- 幸存者反打 ---")
        for line in _fmt_report(rev, indent="  "):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
