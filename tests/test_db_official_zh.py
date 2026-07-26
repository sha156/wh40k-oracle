"""db_compile/official_zh：GW 官方中文包 → 战略/强化/分遣队中文名映射。

这里守的是两条命：
① 版面解析——官方 PDF 的 CP 是**浮动文本框**，位置忽左忽右、忽上忽下，
   一旦按"最近标题"贴就会整栏错位一格（数值对、名字错，用户看不出来）。
② 配对纪律——只认跨语言数值指纹，且中英两侧都唯一才落地；配不上宁可留空。
   同类事故在 db_compile/zh_weapons.py 已经出过一次（战斗修女「爆弹手枪」贴错行）。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from db_compile.official_zh import (EnEnhancement, EnStratagem, OUT_PATH,
                                    SLUG_TO_FACTION, ZhEnhancement, ZhStratagem,
                                    _Line, _unique_or_drop, canon_type_en,
                                    canon_type_zh, clean_text,
                                    confirm_detachment_pairs,
                                    derive_detachment_map, gate_by_detachment,
                                    match_enhancements, match_stratagems,
                                    match_within_detachments, number_fingerprint,
                                    parse_page_lines, phases_of_en, phases_of_zh,
                                    score_detachment_pairs, split_en_sections,
                                    strip_html)

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
needs_map = pytest.mark.skipif(not OUT_PATH.exists(),
                               reason="需要 db_compile/official_zh_names.json")


# ── 版面工具 ──────────────────────────────────────────────────────

def L(text: str, x0: float, y0: float, size: float, w: float = 120.0) -> _Line:
    """造一行。宽高按官方包实测比例给，_assign_cp 只用中心点，不敏感。"""
    return _Line(text, x0, y0, x0 + w, y0 + size + 1.0, size, ("MHeiPRC-Bold",))


def _strat_block(name: str, det_line: str, when: str, target: str, effect: str,
                 x: float, y: float, head_size: float = 10.0,
                 body_size: float = 7.5) -> List[_Line]:
    """一条计谋的版面：标题 / 分遣队–类型行 / 背景 / 时机 / 目标 / 效果。整块高约 72pt。"""
    return [
        L(name, x, y, head_size),
        L(det_line, x + 1, y + 17, 6.0),
        L("背景文案随便写几句凑够长度用于判定正文字号。", x, y + 30, body_size),
        L(when, x + 1, y + 45, body_size),
        L(target, x + 1, y + 58, body_size),
        L(effect, x + 1, y + 72, body_size),
    ]


# ── 文本清洗 ──────────────────────────────────────────────────────

def test_clean_text_drops_pdf_control_chars():
    # 官方中文包的文本层里挂着 \x08（「强化\x08」）和 \x07（项目符号后），
    # 肉眼不可见，却让整行匹配静默失效——解析前必须清掉
    assert clean_text("强化\x08") == "强化"
    assert clean_text("\t\n▪\x07己方单位") == "▪己方单位"


def test_clean_text_keeps_fullwidth_parens_in_names():
    # 官方写法是全角「（光环）」。NFKC 会拉成半角，那就不是 GW 官方译名了
    assert clean_text(" 死亡之幕（光环） ") == "死亡之幕（光环）"


def test_clean_text_drops_zero_width_chars():
    """零宽字符必须清（2026-07-26 复核逮到）：机械教包的分遣队名抽出来，
    「启明」和「自动合唱团」之间夹着一个 U+200B 零宽空格。这个名字要当字典键用
    （英文容器名 → 中文分遣队名），夹一个零宽字符就永远 join 不上，偏偏打印出来、
    贴进报告、肉眼比对全都与正常名字一模一样，报错信息里根本看不出差别。

    码位一律写 chr(0x…)，不贴字面量——贴了的话这几行在编辑器里看着是空的，
    复核的人没法确认到底测了哪些码位。
    """
    zwsp = chr(0x200B)
    assert clean_text("启明" + zwsp + "自动合唱团") == "启明自动合唱团"
    for code in (0x00AD,    # 软连字符
                 0x200B,    # 零宽空格
                 0x200D,    # 零宽连接符
                 0x200F,    # 从右至左标记
                 0x202E,    # 从右至左覆盖
                 0x2060,    # 词连接符
                 0xFEFF):   # BOM / 零宽非断空格
        assert clean_text("碎星" + chr(code) + "宝库") == "碎星宝库", hex(code)


def test_number_fingerprint_survives_translation():
    # 指纹的全部立身之本：同一条规则中英两侧的数字多重集相等
    assert number_fingerprint("效果：致伤掷骰结果增加 1 点。") == ("1",)
    assert number_fingerprint("Until the end of the phase, add 1 to the Wound "
                              "roll.") == ("1",)
    assert number_fingerprint("您的单位可以进行一次最多 D6\" 的常规移动。") == ("D6",)
    assert number_fingerprint("Your unit can make a Normal move of up to "
                              "D6\".") == ("D6",)


def test_number_fingerprint_is_multiset_and_nfkc():
    assert number_fingerprint("移动属性降低 2\"，冲锋掷骰结果减 2。") == ("2", "2")
    assert number_fingerprint("提升 ６\"") == ("6",)   # 全角数字要归一才对得上


def test_phase_extraction_matches_across_languages():
    assert phases_of_zh("己方射击阶段或近战阶段。") == ("fight", "shooting")
    assert phases_of_en("Your Shooting phase or the Fight phase.") == \
        ("fight", "shooting")
    assert phases_of_zh("在您的移动阶段结束时。") == ("movement",)


def test_canon_type_both_languages():
    assert canon_type_zh("战斗战术计谋") == "battle_tactic"
    assert canon_type_en("Starshatter Arsenal – Battle Tactic Stratagem") == \
        "battle_tactic"
    assert canon_type_zh("战略计划计谋") == canon_type_en("X – Strategic Ploy Stratagem")
    assert canon_type_en(None) is None


def test_split_en_sections_strips_html():
    text = ("<b>WHEN:</b> Your Shooting phase.<br><br><b>TARGET:</b> One "
            "<span class=\"kwb\">NECRONS</span> unit.<br><br><b>EFFECT:</b> "
            "Add 1 to the Wound roll.")
    sec = split_en_sections(text)
    assert sec["when"] == "Your Shooting phase."
    assert "NECRONS" in sec["target"] and "<span" not in sec["target"]
    assert number_fingerprint(sec["effect"]) == ("1",)
    assert strip_html("<b>a</b>&nbsp;b") == "a b"


# ── 版面解析 ──────────────────────────────────────────────────────

def test_parse_stratagem_block():
    lines = _strat_block("无情收回", "碎星宝库 – 战斗战术计谋",
                         "时机：己方射击阶段或近战阶段。",
                         "目标：一个己方太空死灵单位。",
                         "效果：致伤掷骰结果增加 1 点。", 188, 74)
    lines.append(L("2CP", 161, 138, 12.0, w=16))
    strats, enhs, warns = parse_page_lines(lines, "NEC", "necrons.pdf", 5)
    assert enhs == [] and warns == []
    (s,) = strats
    assert (s.name_zh, s.detachment_zh, s.type_zh, s.cp) == \
        ("无情收回", "碎星宝库", "战斗战术计谋", 2)
    assert s.when_zh == "己方射击阶段或近战阶段。"
    assert number_fingerprint(s.effect_zh) == ("1",)


def test_parse_stratagem_detachment_line_without_type():
    # 有些页只印分遣队名不印类型（实测太空死灵 p1 的新分遣队）
    lines = _strat_block("主宰规程", "王朝之手", "时机：指挥阶段",
                         "目标：一个己方不朽者单位。",
                         "效果：您的单位的 OC +1。", 309, 224)
    strats, _, _ = parse_page_lines(lines, "NEC", "necrons.pdf", 1)
    assert (strats[0].detachment_zh, strats[0].type_zh) == ("王朝之手", None)


def test_parse_detachment_line_accepts_both_dashes():
    # 同一本 PDF 里 – 和 - 混用，只认一种会整页丢掉类型信息
    for dash in ("–", "-", "—"):
        lines = _strat_block("死亡景象", f"诅咒军团 {dash} 战斗战术计谋",
                             "时机：在您对手的射击阶段中。", "目标：一个己方单位。",
                             "效果：命中掷骰结果减 1。", 188, 74)
        strats, _, _ = parse_page_lines(lines, "NEC", "x.pdf", 9)
        assert (strats[0].detachment_zh, strats[0].type_zh) == \
            ("诅咒军团", "战斗战术计谋")


def _two_column_page(cp_boxes: List[Tuple[int, float, float]]) -> List[_Line]:
    """两条计谋上下排在同一栏（实测太空死灵 p9 的版式），外加 (CP, x, y) 指定的框。"""
    lines = _strat_block("系统性杀戮", "诅咒军团 - 战斗战术计谋",
                         "时机：在您的射击阶段中。", "目标：一个己方单位。",
                         "效果：武器拥有[连击 1]技能。", 188, 72)
    lines += _strat_block("死亡景象", "诅咒军团 - 战斗战术计谋",
                          "时机：在您对手的射击阶段中。", "目标：一个己方单位。",
                          "效果：命中掷骰结果减 1。", 188, 207)
    return lines + [L(f"{cp}CP", x, y, 9.0, w=16) for cp, x, y in cp_boxes]


def test_cp_box_below_head_is_not_stolen_by_the_next_stratagem():
    """回归：CP 框 cy≈150 离**第二条**标题（y=207）比离第一条（y=72）更近。

    照"最近标题"配，整栏 CP 会集体后移一位——正是「数值对、名字错」那一类。
    正解是纵向落区间，不是最近邻。
    """
    strats, _, _ = parse_page_lines(_two_column_page([(1, 159, 144), (2, 159, 279)]),
                                    "NEC", "necrons.pdf", 9)
    assert [(s.name_zh, s.cp) for s in strats] == \
        [("系统性杀戮", 1), ("死亡景象", 2)]


def test_cp_box_right_of_column_and_slightly_above_head():
    """另一种版式：CP 框在栏**右侧**（x=516 / 正文 x=309）且比标题**高** 6pt。"""
    lines = _strat_block("主宰规程", "王朝之手", "时机：指挥阶段",
                         "目标：一个己方单位。", "效果：OC +1。", 309, 224)
    lines += _strat_block("征服者的意志", "王朝之手", "时机：在您的移动阶段结束时。",
                          "目标：一个己方单位。", "效果：那个目标被占领。", 309, 324)
    lines += [L("1CP", 516, 218, 12.0, w=16), L("3CP", 516, 318, 12.0, w=16)]
    strats, _, _ = parse_page_lines(lines, "NEC", "necrons.pdf", 1)
    assert [(s.name_zh, s.cp) for s in strats] == \
        [("主宰规程", 1), ("征服者的意志", 3)]


def test_cp_assignment_gives_up_when_not_bijective():
    """两个 CP 框落进同一条计谋的区间＝版面没读懂。整页 CP 判未知，绝不硬贴。"""
    strats, _, _ = parse_page_lines(_two_column_page([(1, 159, 100), (2, 159, 110)]),
                                    "NEC", "necrons.pdf", 9)
    assert [s.cp for s in strats] == [None, None]


def test_missing_cp_box_only_costs_its_own_stratagem():
    """少一个框（实测艾达灵族 p8：框被压在图里没抽出来）只让那一条判未知。

    不能因此把整页作废——同页其它计谋的框是好的，作废它们纯属自伤。
    """
    strats, _, _ = parse_page_lines(_two_column_page([(1, 159, 144)]),
                                    "NEC", "necrons.pdf", 9)
    assert [s.cp for s in strats] == [1, None]


def test_duplicate_cp_box_with_the_same_number_is_tolerated():
    """同一条计谋落到两个框、数字一致＝版面重复渲染（混沌星际战士 p5：7 框 / 6 条）。"""
    strats, _, _ = parse_page_lines(_two_column_page([(1, 159, 120), (1, 159, 150)]),
                                    "NEC", "necrons.pdf", 9)
    assert [s.cp for s in strats] == [1, None]


def test_second_target_label_is_read_as_the_effect_section():
    """混沌星际战士包把第三段的「效果：」错印成「目标：」——p9 六条全中，p7/p15 各一条。

    原样解析的话 target 会一路吞掉 effect 正文、effect 留空，随后被「时机与效果
    必须都在」的守卫整条丢弃：**整页 6 条静默消失**，而报告只会显示"官方就这么多条"，
    覆盖率看着理所当然。定式顺序是 时机→目标→效果，小节不回头，所以
    「目标出现两次而效果还空着」只可能是第二个目标其实是效果。
    """
    lines = [L("恐怖面目", 188, 74, 10.0),
             L("拜尔造物 – 战略计划计谋", 189, 91, 6.0),
             L("时机：对手的射击阶段或近战阶段中，在一个敌方单位选择了攻击目标后。",
               189, 153, 7.5),
             L("目标：一个己方阿斯塔特叛军单位。", 189, 182, 7.5),
             L("目标：直到阶段结束前，命中掷骰结果减少 1 点。", 189, 210, 7.5)]
    strats, _, _ = parse_page_lines(lines, "CSM", "csm.pdf", 9)
    assert [s.name_zh for s in strats] == ["恐怖面目"]
    assert strats[0].target_zh == "一个己方阿斯塔特叛军单位。"
    assert strats[0].effect_zh == "直到阶段结束前，命中掷骰结果减少 1 点。"
    # 指纹必须落在正确的段上，否则救回来的条目会拿错误指纹去配对
    assert number_fingerprint(strats[0].effect_zh) == ("1",)
    assert number_fingerprint(strats[0].target_zh) == ()


def test_repeated_label_is_left_alone_when_the_next_section_is_taken():
    """下一段已经有内容就不动——那不是错印，是效果里有以「目标：」起头的列点之类。"""
    lines = [L("某某", 188, 74, 10.0),
             L("诅咒军团 - 战斗战术计谋", 189, 91, 6.0),
             L("时机：己方射击阶段。", 189, 153, 7.5),
             L("目标：一个己方单位。", 189, 182, 7.5),
             L("效果：攻击力量提升 2 点。", 189, 196, 7.5),
             L("目标：随后再选择一个单位。", 189, 210, 7.5)]
    strats, _, _ = parse_page_lines(lines, "NEC", "x.pdf", 9)
    assert strats[0].effect_zh == "攻击力量提升 2 点。"
    assert strats[0].target_zh.endswith("随后再选择一个单位。")


def test_half_a_stratagem_is_dropped():
    """只有效果没有时机＝被引用的残片或跨页截断。半截指纹配出来的名字最难查。"""
    lines = [L("某某", 188, 74, 10.0),
             L("诅咒军团 - 战斗战术计谋", 189, 91, 6.0),
             L("效果：该己方单位中模型装备的武器拥有[连击 1]技能。", 189, 104, 7.5),
             L("再补一行正文让本栏正文字号可判定。", 189, 118, 7.5)]
    strats, _, _ = parse_page_lines(lines, "NEC", "x.pdf", 9)
    assert strats == []


def test_rules_update_page_is_skipped_entirely():
    """「规则更新」节会整段引用计谋原文，但大标题是**分遣队名**不是计谋名。

    照常解析会把「湮灭军团分遣队」当成一条计谋的中文名（实测太空死灵 p28）。
    """
    lines = [L("规则更新", 258, 127, 20.0),
             L("湮灭军团分遣队", 43, 311, 12.0),
             L("歼灭协议分遣队规则", 43, 327, 8.5),
             L("“时机：在您对手的射击阶段。", 43, 404, 8.5),
             L("目标：那个毁灭者教派单位。", 43, 426, 8.5),
             L("效果：可以进行一次最多 D6\" 的迸发移动。”", 43, 437, 8.5)]
    assert parse_page_lines(lines, "NEC", "necrons.pdf", 28) == ([], [], [])


def test_parse_enhancements_with_legend_split_and_badge():
    lines = [
        L("碎星宝库", 173, 75, 36.0, w=90),
        L("分遣队规则\t", 167, 240, 12.0),
        L("无息攻势", 162, 260, 12.0),
        L("太空死灵拥有各种各样的可怕战争机器，横扫战场夺回领土。", 161, 277, 8.5),
        L("强化\x08", 352, 244, 8.0),
        L("威压气场（光环）", 350, 260, 12.0),
        L("在这位贵族释放出宝库全部力量时，追随者们理解战斗的重要性。", 349, 276, 8.5),
        L("仅限霸主模型。每当位于持有者 6\" 内的单位中的模型进行攻击时，"
          "重掷结果为 1 的命中掷骰。", 350, 331, 8.5),
        L("微缩维度镜\x08", 350, 393, 12.0),
        L("这个装置能够寄生在王朝战争的数据流当中，让使用者追踪敌人。", 349, 410, 8.5),
        L("仅限太空死灵模型。远程武器拥有 [无视掩体] 技能。", 350, 451, 8.5),
    ]
    strats, enhs, warns = parse_page_lines(lines, "NEC", "necrons.pdf", 4)
    assert strats == [] and warns == []
    assert [e.name_zh for e in enhs] == ["威压气场（光环）", "微缩维度镜"]
    assert all(e.detachment_zh == "碎星宝库" for e in enhs)
    assert enhs[0].text_zh.startswith("仅限霸主模型")
    assert "追随者" in enhs[0].legend_zh
    assert number_fingerprint(enhs[0].text_zh) == ("1", "6")


def test_enhancement_badge_upgrade_suffix_stripped():
    lines = [
        L("王朝之手", 57, 145, 38.0, w=90),
        L("分遣队规则", 61, 224, 10.0),
        L("高动力方案", 57, 242, 12.0),
        L("指令协议涌入这些机器人战士的机械躯体，赋予他们更快的速度。", 56, 258, 8.5),
        L("强化", 61, 378, 10.0),
        L("活跃哨卫  升级 ", 57, 396, 12.0),
        L("这些死灵武士在超驰指令的指使下前行，执行着主人的意志。", 56, 412, 8.5),
        L("仅限太空死灵武士单位。该单位拥有斥候 5\"技能。", 57, 445, 8.5),
    ]
    _, enhs, _ = parse_page_lines(lines, "NEC", "necrons.pdf", 1)
    assert [e.name_zh for e in enhs] == ["活跃哨卫"]      # 「升级」是版面徽标


def test_detachment_rule_is_not_mistaken_for_enhancement():
    """分遣队规则没有「仅限…」定式，不能被当成强化收进去。"""
    lines = [
        L("诅咒军团", 173, 75, 36.0, w=90),
        L("分遣队规则", 167, 240, 12.0),
        L("冰冷狂热", 162, 260, 12.0),
        L("毁灭者的狂怒并非野蛮或鲁莽，而是一种冷酷有序的歼灭。", 161, 277, 8.5),
        L("您军队中毁灭者教派模型的武器力量属性提升 2。", 162, 380, 8.5),
    ]
    _, enhs, _ = parse_page_lines(lines, "NEC", "necrons.pdf", 8)
    assert enhs == []


# ── 指纹配对 ──────────────────────────────────────────────────────

def _en(name: str, det: str, cp: Optional[int], when: str, target: str,
        effect: str, typ: Optional[str] = None) -> EnStratagem:
    return EnStratagem(f"id-{name}", "NEC", det, name, cp, typ, when, target, effect)


def _zh(name: str, det: str, cp: Optional[int], when: str, target: str,
        effect: str, typ: Optional[str] = None) -> ZhStratagem:
    return ZhStratagem("NEC", name, det, typ, cp, when, target, effect, "p.pdf", 5)


def test_match_stratagems_pairs_on_numeric_fingerprint():
    en = [_en("CHRONOSHIFT", "Starshatter Arsenal", 1, "Your Movement phase.",
              "One Necrons Vehicle unit.",
              "Add 6\" to the Move characteristic of models in your unit."),
          _en("DIMENSIONAL TUNNEL", "Starshatter Arsenal", 1, "Your Movement phase.",
              "One Necrons Vehicle unit.",
              "Models in your unit can move through terrain features.")]
    zh = [_zh("次元通道", "碎星宝库", 1, "己方移动阶段。", "一个己方太空死灵载具单位。",
              "目标单位中的模型可以水平移动穿过模型和地形模型。"),
          _zh("时间跃迁", "碎星宝库", 1, "己方移动阶段。", "一个己方太空死灵载具单位。",
              "目标单位中模型的移动属性增加 6\"。")]
    pairs, _ = match_stratagems(en, zh)
    assert {(e.name_en, z.name_zh) for e, z in pairs} == \
        {("CHRONOSHIFT", "时间跃迁"), ("DIMENSIONAL TUNNEL", "次元通道")}


def test_opponent_timing_separates_otherwise_identical_fingerprints():
    """无情收回 / 不破造物：同 2CP、同阶段、效果都只有一个 1，只有触发方不同。"""
    en = [_en("MERCILESS RECLAMATION", "Starshatter Arsenal", 2,
              "Your Shooting phase or the Fight phase.", "One NECRONS unit.",
              "Add 1 to the Wound roll."),
          _en("UNYIELDING FORMS", "Starshatter Arsenal", 2,
              "Your opponent's Shooting phase or the Fight phase.",
              "One Necrons Vehicle unit.", "Subtract 1 from the Wound roll.")]
    zh = [_zh("无情收回", "碎星宝库", 2, "己方射击阶段或近战阶段。", "一个己方单位。",
              "致伤掷骰结果增加 1 点。"),
          _zh("不破造物", "碎星宝库", 2, "对手射击阶段或近战阶段中。", "一个己方载具单位。",
              "致伤掷骰结果减少 1 点。")]
    pairs, _ = match_stratagems(en, zh)
    assert {(e.name_en, z.name_zh) for e, z in pairs} == \
        {("MERCILESS RECLAMATION", "无情收回"), ("UNYIELDING FORMS", "不破造物")}


def test_ambiguous_fingerprint_matches_nothing():
    """两条指纹完全一样又都没有 type：宁缺毋错，一条都不配。"""
    en = [_en("ALPHA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1."),
          _en("BETA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1.")]
    zh = [_zh("甲", "分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。"),
          _zh("乙", "分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。")]
    pairs, diag = match_stratagems(en, zh)
    assert pairs == []
    assert diag["ambiguous"]


def test_type_breaks_a_tie_only_when_both_sides_know_it():
    en = [_en("ALPHA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1.",
              "D – Battle Tactic Stratagem"),
          _en("BETA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1.",
              "D – Strategic Ploy Stratagem")]
    zh = [_zh("甲", "分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。",
              "战斗战术计谋"),
          _zh("乙", "分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。",
              "战略计划计谋")]
    pairs, _ = match_stratagems(en, zh)
    assert {(e.name_en, z.name_zh) for e, z in pairs} == \
        {("ALPHA", "甲"), ("BETA", "乙")}
    # 只要有一侧缺 type，就退回"整桶放弃"——缺的那条可能属于任何子桶
    en[1] = _en("BETA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1.")
    assert match_stratagems(en, zh)[0] == []


def test_type_conflict_vetoes_a_one_to_one_match():
    en = [_en("ALPHA", "D", 1, "Your Shooting phase.", "One unit.", "Add 1.",
              "D – Battle Tactic Stratagem")]
    zh = [_zh("甲", "分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。",
              "战略计划计谋")]
    assert match_stratagems(en, zh)[0] == []


def test_detachment_map_needs_a_real_majority():
    def pair(en_det: str, zh_det: str) -> Tuple[EnStratagem, ZhStratagem]:
        return (_en("X", en_det, 1, "", "", ""), _zh("甲", zh_det, 1, "", "", ""))

    mapping, rejected = derive_detachment_map(
        [pair("Starshatter Arsenal", "碎星宝库")] * 5 +
        [pair("Starshatter Arsenal", "墓穴技师密会")])
    assert mapping == {"Starshatter Arsenal": "碎星宝库"}
    assert rejected == []

    # 单票不落地：一条错配就能立起一个错的分遣队名，而分遣队名会被到处引用
    mapping, rejected = derive_detachment_map([pair("Cursed Legion", "诅咒军团")])
    assert mapping == {} and rejected

    # 平票不落地
    mapping, rejected = derive_detachment_map(
        [pair("A", "甲"), pair("A", "甲"), pair("A", "乙"), pair("A", "乙")])
    assert mapping == {} and rejected


def test_match_enhancements_needs_the_detachment_map():
    en = [EnEnhancement("e1", "NEC", "Cryptek Conclave", "Gauntlet of Compression",
                        "Add 6\" to the Range characteristic."),
          EnEnhancement("e2", "NEC", "Cryptek Conclave", "Gravitic Bolas",
                        "Subtract 2\" from Move and 2 from the Charge roll.")]
    zh = [ZhEnhancement("NEC", "压缩拳套", "墓穴技师密会", "", "远程武器的攻击范围属性提升 6\"。",
                        "p.pdf", 6),
          ZhEnhancement("NEC", "重力流星锤", "墓穴技师密会", "",
                        "移动属性降低 2\"，并且冲锋掷骰结果减 2。", "p.pdf", 6)]
    pairs, diag = match_enhancements(en, zh, {"Cryptek Conclave": "墓穴技师密会"})
    assert {(e.name_en, z.name_zh) for e, z in pairs} == \
        {("Gauntlet of Compression", "压缩拳套"), ("Gravitic Bolas", "重力流星锤")}
    # 分遣队没配上 → 搜索域收不窄 → 一条都不敢配
    assert match_enhancements(en, zh, {})[0] == []
    assert diag["no_detachment"] == []


def test_gate_drops_a_pair_whose_detachments_are_not_confirmed_partners():
    """回归两个真错（2026-07-26 自查逮到的，都是 Pass A"全阵营指纹唯一"）：

      · 「傲慢优越感」(凤凰王庭, 2CP) 被配给 DEATH ECSTASY (Peerless Bladesmen, 2CP)
      · 「失常怒火」(恐虐屠夫, 1CP)   被配给 SAVAGE RESILIENCE (Boarding Butchers, 1CP)

    两条真对家都因为库里 CP 还没跟上官方 v1.1 而落选，指纹便撞给了隔壁分遣队。
    「1CP + 某阶段 + 效果里一个 1」这种形状全阵营几十条，指纹一样根本不代表是同一条。
    """
    e = _en("DEATH ECSTASY", "Peerless Bladesmen", 2, "Fight phase.", "", "")
    z = _zh("傲慢优越感", "凤凰王庭", 2, "在近战阶段中。", "", "")
    kept, dropped = gate_by_detachment([(e, z)],
                                       {"Court of the Phoenician": "凤凰王庭"})
    assert kept == [] and dropped == [(e, z)]
    # 分遣队对确认了才放行
    kept, dropped = gate_by_detachment([(e, z)], {"Peerless Bladesmen": "凤凰王庭"})
    assert kept == [(e, z)] and dropped == []
    # 一侧根本没有分遣队信息＝没有证据，也不放行
    assert gate_by_detachment([(e, _zh("甲", None, 2, "", "", ""))], {})[0] == []


def _det_pair_fixture():
    """一个中文分遣队（3 条）对上两个候选英文容器：真对家 3 条同指纹，另一个只有 1 条。"""
    zh = [_zh("甲", "新分队", 1, "己方射击阶段。", "一个己方单位。", "增加 1 点。"),
          _zh("乙", "新分队", 2, "己方移动阶段。", "一个己方单位。", "移动属性增加 6\"。"),
          _zh("丙", "新分队", 1, "己方近战阶段。", "一个己方单位。", "重掷冲锋掷骰。")]
    right = [_en("A", "Right", 1, "Your Shooting phase.", "One unit.", "Add 1."),
             _en("B", "Right", 2, "Your Movement phase.", "One unit.",
                 "Add 6\" to Move."),
             _en("C", "Right", 1, "Your Fight phase.", "One unit.",
                 "Re-roll the Charge roll.")]
    wrong = [_en("X", "Wrong", 1, "Your Shooting phase.", "One unit.", "Add 1."),
             _en("Y", "Wrong", 3, "Your Command phase.", "One unit.", "Nothing."),
             _en("Z", "Wrong", 3, "Your Command phase.", "One unit.", "Nothing at all.")]
    return right + wrong, zh


def test_confirm_detachment_pairs_takes_the_mutual_best():
    en, zh = _det_pair_fixture()
    assert confirm_detachment_pairs(score_detachment_pairs(en, zh)) == \
        {"Right": "新分队"}


def test_confirm_detachment_pairs_refuses_a_tie():
    """并列第一一律谁都不认。用占比之类的次键去打破平局试过——被选中的恰恰是错的
    （钛帝国「辅助核心队」占比把票投给了毫不相干的 Kroot Hunting Pack）。"""
    en, zh = _det_pair_fixture()
    twin = [EnStratagem(f"twin-{s.name_en}", s.faction, "Twin", f"{s.name_en}2",
                        s.cp, s.type_en, s.when_en, s.target_en, s.effect_en)
            for s in en if s.detachment == "Right"]
    assert confirm_detachment_pairs(score_detachment_pairs(en + twin, zh)) == {}


def test_confirm_detachment_pairs_needs_two_hits_and_enough_coverage():
    """单条重合不算数——吞世者「恐虐屠夫」全阵营只跟一个（错的）容器有 1 条交集。"""
    en, zh = _det_pair_fixture()
    assert confirm_detachment_pairs({("新分队", "Right"): (1, 3)}) == {}
    assert confirm_detachment_pairs({("新分队", "Right"): (2, 3)}) == {"Right": "新分队"}
    # 覆盖率地板：10 条里只解释得通 2 条，多半是撞上的
    assert confirm_detachment_pairs({("新分队", "Right"): (2, 10)}) == {}


def test_within_detachment_pass_recovers_a_cp_drifted_stratagem():
    """库里 CP 还停在旧版时，完整指纹配不上；分遣队对确认后放宽 key 才捞得回来。

    这正是「傲慢优越感 ↔ PRIDEFUL SUPERIORITY」的救回路径（官方 2CP / 库里 1CP）。
    """
    en = [_en("PRIDEFUL SUPERIORITY", "Court of the Phoenician", 1,
              "Fight phase.", "One unit.", "You can re-roll the Hit roll.")]
    zh = [_zh("傲慢优越感", "凤凰王庭", 2, "在近战阶段中。", "一个己方单位。",
              "您可以重掷命中掷骰。")]
    assert match_stratagems(en, zh)[0] == []          # cp 不同：完整指纹配不上
    pairs = match_within_detachments(en, zh, {"Court of the Phoenician": "凤凰王庭"},
                                     set(), set())
    assert [(e.name_en, z.name_zh) for e, z in pairs] == \
        [("PRIDEFUL SUPERIORITY", "傲慢优越感")]


def test_within_detachment_pass_still_refuses_leftover_matching():
    """两边各剩一条也不认——官方 v1.1 新增的一条和库里多出来的一条会被硬凑成一对。"""
    en = [_en("SOMETHING NEW", "Court of the Phoenician", 1, "Your Command phase.",
              "One unit.", "Add 3 to something.")]
    zh = [_zh("完全不同的东西", "凤凰王庭", 1, "在您的射击阶段中。", "一个己方单位。",
              "移动属性增加 6\"。")]
    assert match_within_detachments(en, zh, {"Court of the Phoenician": "凤凰王庭"},
                                    set(), set()) == []


def test_unique_or_drop_kills_many_to_one_names():
    out, conflicts = _unique_or_drop([("A", "甲"), ("B", "甲"), ("C", "丙")])
    assert out == {"C": "丙"}
    assert len(conflicts) == 2       # 甲 被两个英文条目认领，两边都丢


# ── 真库 / 真产物不变量 ───────────────────────────────────────────

@needs_map
def test_artifact_shape_and_lf_encoding():
    raw = OUT_PATH.read_bytes()
    assert b"\r\n" not in raw, "产物必须是 LF（Windows 下 json.dump 默认会写 CRLF）"
    data = json.loads(raw.decode("utf-8"))
    assert set(data) == {"stratagems", "stratagems_by_id", "enhancements",
                         "enhancements_by_id", "detachments", "_report"}
    for key in ("stratagems", "stratagems_by_id", "enhancements",
                "enhancements_by_id", "detachments"):
        assert all(isinstance(k, str) and isinstance(v, str)
                   for k, v in data[key].items())
        assert all(k.strip() and v.strip() for k, v in data[key].items())


@needs_map
def test_row_level_map_covers_at_least_the_name_level_one():
    """行级映射恒 ≥ 名级：名级要为「同名不同译」整条让路，行级不用。

    反过来（行级比名级少）说明行级那步把配对丢了，而落库以行级为准——
    表现是「官方明明有中文名，页面却是英文」，没人能从报告里看出来。
    """
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    assert len(data["stratagems_by_id"]) >= len(data["stratagems"])
    assert len(data["enhancements_by_id"]) >= len(data["enhancements"])
    # 名级映射丢掉的那批同名冲突，行级必须真的接住了（否则这一层白加）
    assert len(data["stratagems_by_id"]) > len(data["stratagems"])


@needs_map
def test_no_chinese_name_serves_two_english_entries():
    """同一个中文名配给两个英文条目＝指纹撞车，正是「数值对、名字错」的形状。"""
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    for key in ("stratagems", "enhancements", "detachments"):
        zh_names = list(data[key].values())
        dupes = {n for n in zh_names if zh_names.count(n) > 1}
        assert not dupes, f"{key} 中文名重复：{sorted(dupes)[:5]}"


@needs_map
def test_names_look_chinese_and_english_keys_look_english():
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    for key in ("stratagems", "enhancements", "detachments"):
        for en_name, zh_name in data[key].items():
            assert any("一" <= c <= "鿿" for c in zh_name), \
                f"{key}: {en_name} 的中文名里没有汉字：{zh_name}"
            assert not any("一" <= c <= "鿿" for c in en_name), \
                f"{key}: 英文键里混进了汉字：{en_name}"


@needs_map
@needs_db
def test_every_key_exists_in_the_database():
    """键必须是库里真有的英文条目——不然这份映射落库时会全落空还没人发现。"""
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    conn = sqlite3.connect(str(DB))
    try:
        strat = {(r[0] or "").upper() for r in
                 conn.execute("SELECT name_en FROM stratagems")}
        enh = {r[0] or "" for r in conn.execute("SELECT name FROM enhancements")}
        det = {r[0] or "" for r in
               conn.execute("SELECT detachment FROM stratagems")}
        det |= {r[0] or "" for r in
                conn.execute("SELECT detachment_name FROM detachments")}
    finally:
        conn.close()
    assert not (set(data["stratagems"]) - strat)
    assert not (set(data["enhancements"]) - enh)
    assert not (set(data["detachments"]) - det)


@needs_map
@needs_db
def test_coverage_floor_and_report_consistency():
    """配对率地板：官方中文包只覆盖 FP 收录的分遣队，不可能满库，
    但显著低于这里的地板就说明版面解析又被改版打断了（MFM 解析器踩过一次）。"""
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    rep = data["_report"]
    assert rep["matched"]["stratagems"] == len(data["stratagems"])
    assert rep["matched"]["enhancements"] == len(data["enhancements"])
    assert rep["matched"]["detachments"] == len(data["detachments"])
    assert len(data["detachments"]) >= 100
    assert len(data["stratagems"]) >= 400
    assert len(data["enhancements"]) >= 200


def test_every_faction_pack_slug_is_mapped():
    """新下一批官方包时，漏配 slug 会静默少一个阵营——这条把它变成红灯。"""
    manifest = Path("data/官方中文/manifest.json")
    if not manifest.exists():
        pytest.skip("需要 data/官方中文/manifest.json")
    items = json.loads(manifest.read_text(encoding="utf-8"))["items"]
    slugs = [it["faction_slug"] for it in items if it["kind"] == "faction-pack"]
    assert slugs and not (set(slugs) - set(SLUG_TO_FACTION))
