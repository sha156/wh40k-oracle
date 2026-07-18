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


class LoadoutParseError(ValueError):
    """loadout 文本解析失败（评审 H11）：消息里带坏 token + 期望格式示例，供 CLI/面板友好提示。"""


def _parse_loadout(text: Optional[str]) -> Optional[List[Tuple[str, int]]]:
    """'Shoota:9,Slugga:1' → [('Shoota',9),('Slugga',1)]。畸形片段抛 LoadoutParseError。"""
    if not text:
        return None
    out: List[Tuple[str, int]] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        name, sep, cnt = part.rpartition(":")
        if not sep:                       # 无冒号 → 整段是武器名，数量默认 1
            out.append((part, 1))
            continue
        name = name.strip()
        if not name:
            raise LoadoutParseError(
                f"loadout 片段 {part!r} 缺少武器名：期望格式「武器名:数量」，"
                f"如 'Shoota:9,Slugga:1'")
        try:
            count = int(cnt.strip())
        except ValueError:
            raise LoadoutParseError(
                f"loadout 片段 {part!r} 的数量 {cnt.strip()!r} 不是整数："
                f"期望格式「武器名:数量」，如 'Shoota:9,Slugga:1'")
        out.append((name, count))
    return out


def _positive_int(text: str) -> int:
    """argparse type：正整数校验（评审 H9——n=0/-5 会让 numpy 裸崩，入口拦截）。"""
    try:
        v = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"迭代次数必须是正整数，收到 {text!r}")
    if v <= 0:
        raise argparse.ArgumentTypeError(f"迭代次数必须是正整数，收到 {v}")
    return v


def _clean_options(raw: dict) -> dict:
    """滤掉未提供的项：只滤 None 与 False 本身，绝不滤 0（评审 H10——
    `v not in (None, False)` 会因 0 == False 把 seed=0/n=0 等合法显式值静默丢弃）。"""
    return {k: v for k, v in raw.items() if v is not None and v is not False}


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
                                description="战锤40K 蒙特卡洛对战模拟"
                                            "（先攻判定与 Stealth/间接火力/Heavy/Blast/Cleave"
                                            " 词条按11版；其余词条经审计一致或沿用十版口径）")
    p.add_argument("attacker", help="攻方单位名（中/英/俗名）")
    p.add_argument("defender", help="守方单位名")
    p.add_argument("--phase", default="shooting", choices=["shooting", "melee"])
    p.add_argument("--charge", action="store_true")
    p.add_argument("--half-range", action="store_true", dest="half_range")
    p.add_argument("--cover", action="store_true",
                   help="目标享受掩体收益（11版13.08：恶化攻方 BS 1，射击专属，"
                        "非十版护甲+1）；攻方 [IGNORES COVER] 抵消、[PSYCHIC] 可无视")
    p.add_argument("--stationary", action="store_true",
                   help='满足 Heavy 条件（11版24.16：未交战、本回合未上场且全员移动≤3"）；'
                        '亦作间接火力「驻停+有友军可见目标」的代理条件')
    p.add_argument("--long-range", action="store_true", dest="long_range")
    p.add_argument("--indirect", action="store_true",
                   help="以间接火力开火（11版24.19：目标获掩体，未修正6+命中；"
                        "配合 --stationary 为4+）")
    p.add_argument("--attacker-models", type=int, dest="attacker_models")
    p.add_argument("--defender-models", type=int, dest="defender_models")
    p.add_argument("--loadout", help='攻方装配 "武器名:数量,..."（多模型单位必填）')
    p.add_argument("--defender-loadout", dest="defender_loadout",
                   help="守方装配（给了则做串行幸存反打）")
    p.add_argument("--fnp", type=int, help="守方无痛 X+")
    p.add_argument("--damage-reduction", type=int, dest="damage_reduction")
    p.add_argument("--stealth", action="store_true",
                   help="守方 Stealth（11版24.33：被远程攻击选中获掩体收益，"
                        "攻方 [IGNORES COVER] 可抵消）")
    p.add_argument("--smokescreen", action="store_true",
                   help="守方烟幕战略（11版核心战略：对手射击阶段开始时使用，该阶段获掩体"
                        "收益=恶化攻方 BS 1；不额外附加十版 Stealth 式减命中。"
                        "Go to Ground 已从 11 版核心战略移除）")
    p.add_argument("--guided", action="store_true",
                   help="攻方阵营 DSL 开关（P7·钛帝国 FTGG）：假设本单位为受引导（Guided）"
                        "且目标已被标记（Spotted）——BS 特征值改善 1（不吃 ±1 修正夹取）。"
                        "观察员自身不射击的机会成本不建模，报告有披露")
    p.add_argument("--markerlight-observer", action="store_true", dest="markerlight_observer",
                   help="观察员带 Markerlight 关键词（与 --guided 同开=FTGG 引导加成；"
                        "配 --stratagem 'Coordinate to Engage' 时表示攻方观察员自带标记光）："
                        "攻击追加 [IGNORES COVER]")
    p.add_argument("--detachment",
                   help="攻方所属分队名（如 Kauyon / Mont'ka，撇号直弯均可）：放行该分队的"
                        "规则条目；与点名战略做分队一致性校验")
    p.add_argument("--detachment-rounds", action="store_true", dest="detachment_rounds",
                   help="假设当前处于分队规则生效轮次（Kauyon 第3-5轮 / Mont'ka 第1-3轮）——"
                        "引擎无战斗轮概念，此开关是显式假设，报告有披露")
    p.add_argument("--stratagem", action="append", dest="stratagems", metavar="NAME_OR_ID",
                   help="点名施放战略（id/英文名/中文名，可重复传多条）：一次性 opt-in，"
                        "CP 消耗与次数限制不结算只披露；未匹配或分队不符显式报出")
    p.add_argument("--enhancement", action="append", dest="enhancements",
                   metavar="NAME_OR_ID",
                   help="点名攻方增强（P7-PR4，opt-in 同战略；bearer-only 型条目见"
                        " --bearer-leading 假设开关）")
    p.add_argument("--range-within-12", action="store_true", dest="range_within_12",
                   help="假设目标在 12 寸内（Bonded Heroes S+1 档；引擎无距离建模）")
    p.add_argument("--range-within-8", action="store_true", dest="range_within_8",
                   help="假设目标在 8 寸内（Bonded Heroes AP 档；自动蕴含 12 寸档）")
    p.add_argument("--target-below-starting", action="store_true",
                   dest="target_below_starting",
                   help="假设目标低于满编（Hunter's Instincts 命中档）")
    p.add_argument("--target-below-half", action="store_true", dest="target_below_half",
                   help="假设目标低于半编（自动蕴含低于满编档）")
    p.add_argument("--markerlight-visible", action="store_true",
                   dest="markerlight_visible",
                   help="假设目标对未交战的友军标记光单位可见（Starfire 军规）")
    p.add_argument("--blessing-martial-excellence", action="store_true",
                   dest="blessing_martial_excellence",
                   help="恐虐赐福·卓越武艺已激活（近战 [连击1]；军规至多同开两项赐福）")
    p.add_argument("--blessing-warp-blades", action="store_true",
                   dest="blessing_warp_blades",
                   help="恐虐赐福·次元邪刃已激活（近战 [致命一击]）")
    p.add_argument("--blessing-decapitating-strikes", action="store_true",
                   dest="blessing_decapitating_strikes",
                   help="恐虐赐福·斩首一击已激活（近战对步兵 [毁灭伤害]）")
    p.add_argument("--bearer-leading", action="store_true", dest="bearer_leading",
                   help="假设增强携带者正率领本单位（bearer/leading 型增强的生效前提）")
    p.add_argument("--disembarked-this-turn", action="store_true",
                   dest="disembarked_this_turn",
                   help="假设本回合已从运输工具下车（BT 神锤突击队近战命中+1 等条款）")
    p.add_argument("--disembarked-from-land-raider", action="store_true",
                   dest="disembarked_from_land_raider",
                   help="假设下车且运输工具带 LAND RAIDER 关键词（谴责音阵全量致伤重骰；"
                        "自动蕴含下车开关）")
    p.add_argument("--vow-accept-any-challenge", action="store_true",
                   dest="vow_accept_any_challenge",
                   help="圣堂誓言·接受一切挑战已选定（近战 S≤T 时致伤+1；誓言四选一"
                        "由玩家自行保证）")
    p.add_argument("--omen-instrument", action="store_true", dest="omen_instrument",
                   help="指引圣兆·神皇之器已选定（近战接战 CHARACTER 时 [毁灭伤害]；"
                        "圣兆六选三由玩家自行保证）")
    p.add_argument("--omen-momentous-brutality", action="store_true",
                   dest="omen_momentous_brutality",
                   help="指引圣兆·凶暴神视已选定（近战 A+2）")
    p.add_argument("--defender-detachment", dest="defender_detachment",
                   help="守方所属分队名：放行守方分队的防守向 DSL 条目（P7-PR4）")
    p.add_argument("--defender-stratagem", action="append", dest="defender_stratagems",
                   metavar="NAME_OR_ID",
                   help="点名守方防守向战略（Stimm Injectors/Counterfire 等，opt-in）")
    p.add_argument("--defender-enhancement", action="append",
                   dest="defender_enhancements", metavar="NAME_OR_ID",
                   help="点名守方增强（opt-in）")
    p.add_argument("--defender-hidden", action="store_true", dest="defender_hidden",
                   help="假设守方处于 hidden 状态（AAC Autoreactive Camouflage 前提）")
    p.add_argument("--defender-bearer-leading", action="store_true",
                   dest="defender_bearer_leading",
                   help="假设守方增强携带者正率领守方单位")
    p.add_argument("--def-fights-first", action="store_true", dest="defender_fights_first")
    p.add_argument("--def-fights-last", action="store_true", dest="defender_fights_last")
    p.add_argument("--atk-fights-first", action="store_true", dest="attacker_fights_first")
    p.add_argument("--atk-fights-last", action="store_true", dest="attacker_fights_last")
    p.add_argument("--judge-order", action="store_true", dest="judge_order",
                   help="只判定近战先攻顺序（用 --charge/--*-fights-* 描述状态），不跑模拟")
    p.add_argument("-n", type=_positive_int, default=8000, help="迭代次数（默认 8000，须为正整数）")
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = p.parse_args(argv)

    # 评审 H11：loadout 解析失败给友好提示 + exit 2，不再裸 traceback
    try:
        loadout = _parse_loadout(args.loadout)
        defender_loadout = _parse_loadout(args.defender_loadout)
    except LoadoutParseError as exc:
        print(f"[参数错误] {exc}", file=sys.stderr)
        return 2

    from agent.tools import judge_fight_order, simulate_combat

    # --judge-order：只判先攻顺序，不跑模拟
    if args.judge_order:
        v = judge_fight_order({
            "attacker": args.attacker, "defender": args.defender,
            "attacker_charged": args.charge,
            "attacker_fights_first": args.attacker_fights_first,
            "attacker_fights_last": args.attacker_fights_last,
            "defender_fights_first": args.defender_fights_first,
            "defender_fights_last": args.defender_fights_last,
        })
        if args.json:
            print(json.dumps(v, ensure_ascii=False, indent=2))
            return 0
        print(f"=== 先攻判定：{args.attacker} vs {args.defender} ===")
        print(f"先打方：{v['first_striker']}｜顺序：{' → '.join(v['order'])}"
              f"｜同步反打风险：{'是' if v['simultaneous_risk'] else '否'}")
        print(v["rationale"])
        print("依据：" + "；".join(v["rule_refs"][:2]))
        print("Counter-offensive：" + v["counter_offensive_note"])
        return 0

    options = _clean_options({
        "phase": args.phase, "charge": args.charge, "half_range": args.half_range,
        "cover": args.cover, "stationary": args.stationary,
        "long_range": args.long_range, "indirect": args.indirect,
        "stealth": args.stealth,
        "smokescreen": args.smokescreen,
        "guided": args.guided,
        "markerlight_observer": args.markerlight_observer,
        "detachment": args.detachment,
        "detachment_rounds": args.detachment_rounds,
        "stratagems": args.stratagems,
        "enhancements": args.enhancements,
        "range_within_12": args.range_within_12,
        "range_within_8": args.range_within_8,
        "target_below_starting": args.target_below_starting,
        "target_below_half": args.target_below_half,
        "markerlight_visible": args.markerlight_visible,
        "bearer_leading": args.bearer_leading,
        "blessing_martial_excellence": args.blessing_martial_excellence,
        "blessing_warp_blades": args.blessing_warp_blades,
        "blessing_decapitating_strikes": args.blessing_decapitating_strikes,
        "disembarked_this_turn": args.disembarked_this_turn,
        "disembarked_from_land_raider": args.disembarked_from_land_raider,
        "vow_accept_any_challenge": args.vow_accept_any_challenge,
        "omen_instrument": args.omen_instrument,
        "omen_momentous_brutality": args.omen_momentous_brutality,
        "defender_detachment": args.defender_detachment,
        "defender_stratagems": args.defender_stratagems,
        "defender_enhancements": args.defender_enhancements,
        "defender_hidden": args.defender_hidden,
        "defender_bearer_leading": args.defender_bearer_leading,
        "attacker_fights_first": args.attacker_fights_first,
        "attacker_fights_last": args.attacker_fights_last,
        "defender_fights_first": args.defender_fights_first,
        "defender_fights_last": args.defender_fights_last,
        "attacker_models": args.attacker_models,
        "defender_models": args.defender_models,
        "loadout": loadout,
        "defender_loadout": defender_loadout,
        "fnp": args.fnp, "damage_reduction": args.damage_reduction,
        "n": args.n, "seed": args.seed,
    })

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
