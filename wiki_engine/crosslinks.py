"""wiki_engine/crosslinks.py — 自动 [[wikilink]] 注入（wiki 编译器步骤④）。

扫描 wiki/ 所有实体页，建立名→路径索引，在正文中关键词首次出现处注入 Obsidian [[链接]]。
纯代码实现，零 LLM 调用。

本模块还负责修复合成阶段（步骤③）直接产出的裸关键词断链：LLM 把武器数据表中的
武器技能（如 [[Lethal Hits]]、[[BLAST]]）和正文中的核心技能（如 [[深入打击]]、
[[无敌豁免]]）写成不带路径的 [[关键词]] 形式，这些关键词本身并不是任何实体页的
路径，导致 lint 的 broken-links 检查报错。见 canonicalize_known_terms()。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Set, Tuple

from wiki_engine.models import WikiPage, WikiPageFrontmatter


# ── 已知核心技能/武器技能关键词 → wiki/core-rules/ 术语页 canonical 映射 ──
#
# 数据来源：
#   - data/10版40K通用技能速查表1.08.pdf（核心技能 + 武器技能全部条目）
#   - data/战锤40K总规则10版老湿腐版1.11.pdf（阶段流程/移动/致命伤害/特殊保护等通用核心规则）
#   - data/规则注解中文.pdf（术语补充定义：接战范围/领导力测试/远程攻击等）
# 术语页内容见 wiki/core-rules/<id>.md（由本次迭代人工核对来源后生成）。
#
# key 为断链中实际出现的裸关键词字面量（大小写/译名变体），value 为
# wiki/core-rules/ 下术语页的 id（不含扩展名）。

_CORE_TERM_EXACT_ALIASES: Dict[str, str] = {
    # 核心技能
    "深入打击": "deep-strike",
    "斥候": "scouts",
    "渗透": "infiltrators", "渗透者": "infiltrators",
    "独行特工": "lone-operative",
    "领袖": "leader",
    "隐蔽": "stealth", "隐匿": "stealth",
    "不知疼痛": "feel-no-pain",
    "致命破灭": "deadly-demise", "致命消亡": "deadly-demise",
    "致命覆灭": "deadly-demise", "致命死亡": "deadly-demise",
    "致命毁灭": "deadly-demise", "致命终局": "deadly-demise",
    "致命爆退": "deadly-demise", "死战不退": "deadly-demise",
    # 武器技能
    "突击": "assault", "Assault": "assault",
    "忽视掩体": "ignores-cover", "忽略掩体": "ignores-cover",
    "无视掩体": "ignores-cover", "Ignores Cover": "ignores-cover",
    "IGNORES COVER": "ignores-cover",
    "双联": "twin-linked", "TWIN-LINKED": "twin-linked",
    "Twin-linked": "twin-linked",
    "手枪": "pistol",
    "喷射": "torrent", "洪流": "torrent", "Torrent": "torrent",
    "致命一击": "lethal-hits", "Lethal Hits": "lethal-hits",
    "迅猛冲锋": "lance",
    "曲射": "indirect-fire", "INDIRECT FIRE": "indirect-fire",
    "精准": "precision",
    "爆炸": "blast", "BLAST": "blast", "Blast": "blast",
    "重型": "heavy", "HEAVY": "heavy",
    "危险": "hazardous", "HAZARDOUS": "hazardous",
    "毁灭伤害": "devastating-wounds", "Devastating Wounds": "devastating-wounds",
    "DEVASTATING WOUNDS": "devastating-wounds", "毁灭创伤": "devastating-wounds",
    "毁灭之伤": "devastating-wounds", "毁灭伤损": "devastating-wounds",
    "额外攻击": "extra-attacks", "Extra Attacks": "extra-attacks",
    "一次性": "one-shot", "单次射击": "one-shot", "单次使用": "one-shot",
    "One Shot": "one-shot",
    "灵能攻击": "psychic-attacks", "Psychic Attacks": "psychic-attacks",
    # 通用核心规则概念（总规则10版）
    "致命伤": "mortal-wounds", "致命伤害": "mortal-wounds",
    "特殊保护": "invulnerable-save", "无敌豁免": "invulnerable-save",
    "急流": "torrent",
    # 通用核心规则：阶段/回合结构（总规则10版 + 规则注解中文）
    "交战范围": "engagement-range", "接战范围": "engagement-range",
    "移动阶段": "movement-phase",
    "射击阶段": "shooting-phase",
    "指挥阶段": "command-phase",
    "冲锋阶段": "charge-phase",
    "近战阶段": "fight-phase",
    "战斗震慑测试": "battle-shock-test", "战斗震撼测试": "battle-shock-test",
    "战斗震惊测试": "battle-shock-test", "震慑测试": "battle-shock-test",
    "震慑": "battle-shock-test",
    "绝望撤退测试": "desperate-escape-test", "绝望脱逃测试": "desperate-escape-test",
    "战略预备队": "strategic-reserves", "Strategic Reserves": "strategic-reserves",
    "领导力测试": "leadership-test",
    "加速移动": "advance", "加速": "advance", "全力冲锋": "advance",
    "撤退": "fall-back", "撤退移动": "fall-back",
    "标准移动": "normal-move", "常规移动": "normal-move", "普通移动": "normal-move",
    "命中掷骰": "hit-roll", "命中骰": "hit-roll",
    "造伤骰": "wound-roll",
    "计谋": "stratagem", "战略技能": "stratagem", "战略能力": "stratagem",
    "巨兽": "monster",
    "载具": "vehicle",
    "飞行": "fly",
    "远程攻击": "ranged-attack",
    "援军入场子阶段": "reinforcements-step", "增援步骤": "reinforcements-step",
    "援军": "reinforcements-step", "增援": "reinforcements-step",
    "水平距离": "horizontal-distance",
    "坚守射击": "fire-overwatch",
    "快速部署": "rapid-ingress", "迅速入场": "rapid-ingress",
    "悬浮": "hover",
    "掩体效果": "benefit-of-cover", "掩体优势": "benefit-of-cover",
    "掩体加成": "benefit-of-cover", "掩体奖励": "benefit-of-cover",
    "回合": "battle-round", "游戏大回合": "battle-round",
    "部署": "deployment", "部署阶段": "deployment",
    "冲锋": "charge", "冲锋移动": "charge", "宣言冲锋": "charge",
    # 阵营专属军队规则（钛帝国十版CODEX / 混沌星际战士 / 混沌恶魔 codex）
    "誓言时刻": "oath-of-moment", "忠诚誓言": "oath-of-moment",
    "破敌誓言": "oath-of-moment",
    "黑暗契约": "dark-pact",
    "混沌之影": "shadow-of-chaos",
    "为了上上善道": "for-the-greater-good", "为了上善之道": "for-the-greater-good",
    "为了更伟大的上好": "for-the-greater-good", "观察员": "for-the-greater-good",
    "标记光": "markerlight",
    # 通用类别关键词（单位类型）→ core-rules 术语页（中英双形，兼容中文页与英文兜底页）
    "步兵": "infantry", "Infantry": "infantry", "INFANTRY": "infantry",
    "人物": "character", "Character": "character", "CHARACTER": "character",
    "手雷": "grenades", "Grenades": "grenades", "GRENADES": "grenades",
    "运输工具": "transport", "运输载具": "transport", "Transport": "transport",
    "TRANSPORT": "transport",
    "专属运输": "dedicated-transport", "Dedicated Transport": "dedicated-transport",
    "骑乘": "mounted", "Mounted": "mounted", "MOUNTED": "mounted",
    "史诗英雄": "epic-hero", "Epic Hero": "epic-hero", "EPIC HERO": "epic-hero",
    "步行者": "walker", "Walker": "walker", "WALKER": "walker",
    "泰坦级": "titanic", "Titanic": "titanic", "TITANIC": "titanic",
    "飞行器": "aircraft", "Aircraft": "aircraft", "AIRCRAFT": "aircraft",
    "灵能者": "psyker", "Psyker": "psyker", "PSYKER": "psyker",
    "战线": "battleline", "Battleline": "battleline", "BATTLELINE": "battleline",
    "要塞": "fortification", "Fortification": "fortification",
    "FORTIFICATION": "fortification",
    "野兽": "beast", "Beast": "beast", "BEAST": "beast",
    "蜂群": "swarm", "Swarm": "swarm", "SWARM": "swarm",
    "高耸": "towering", "Towering": "towering", "TOWERING": "towering",
    "烟雾": "smoke", "Smoke": "smoke", "SMOKE": "smoke",
}

# 数值/关键词参数化技能（如"速射1""连击2""反载具3+""斥候7〞"）：
# 保留原始字面量作为链接显示文本，仅替换目标路径。
_CORE_TERM_PREFIX_RULES: List[Tuple[Pattern, str]] = [
    (re.compile(r"^速射\s*\d+$"), "rapid-fire"),
    (re.compile(r"^Rapid Fire\s*\d+$", re.IGNORECASE), "rapid-fire"),
    (re.compile(r"^连击\s*\d+$"), "sustained-hits"),
    (re.compile(r"^持续命中\s*\d+$"), "sustained-hits"),
    (re.compile(r"^Sustained Hits\s*\d+$", re.IGNORECASE), "sustained-hits"),
    (re.compile(r"^热熔\s*\d+$"), "melta"),
    (re.compile(r"^Melta\s*\d+$", re.IGNORECASE), "melta"),
    (re.compile(r"^斥候\s*\d+[\"”″]?$"), "scouts"),
    (re.compile(r"^不知疼痛\s*\d\+$"), "feel-no-pain"),
    (re.compile(r"^不怕疼\s*\d\+$"), "feel-no-pain"),
    (re.compile(r"^(反|针对|防空)[一-鿿]*\s*\d\+$"), "anti"),
    (re.compile(r"^ANTI-[A-Z]+\s*\d\+$", re.IGNORECASE), "anti"),
]

# 链接目标字面量直接映射到已存在的其他 wiki 页面（非术语页），
# 用于修复指向阵营名等已有实体的裸链接。
_DIRECT_PATH_ALIASES: Dict[str, str] = {
    "钛帝国": "factions/钛帝国/index.md",
}

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\\?\|([^\]]+?))?\]\]")


def strip_wikilinks(text: str) -> str:
    """[[path|显示]]→显示、[[target]]→target——用于摘要等纯文本上下文，防 wikilink 的
    竖线进入 Markdown 表格单元格断列（模块 6 F7）。目标尾随反斜杠一并剥除。"""
    def _plain(m: "re.Match[str]") -> str:
        target, display = m.group(1), m.group(2)
        return (display or target).strip().rstrip("\\")
    return _WIKILINK_RE.sub(_plain, text)


def _resolve_known_alias(raw_target: str) -> Optional[str]:
    """把已知的裸关键词解析为其术语页/实体页的 canonical 相对路径。

    返回 None 表示不是已知别名，调用方应保留原样（避免误伤指向真实
    实体页的正常链接）。
    """
    target = raw_target.strip()
    if not target:
        return None
    if target in _DIRECT_PATH_ALIASES:
        return _DIRECT_PATH_ALIASES[target]
    if target in _CORE_TERM_EXACT_ALIASES:
        return "core-rules/{}.md".format(_CORE_TERM_EXACT_ALIASES[target])
    for pattern, term_id in _CORE_TERM_PREFIX_RULES:
        if pattern.match(target):
            return "core-rules/{}.md".format(term_id)
    return None


def canonicalize_known_terms(body: str) -> str:
    """重写正文中已知核心技能/武器技能关键词的裸 [[wikilink]]。

    合成阶段（步骤③）会把武器数据表中的技能列、正文中的核心技能名直接
    写成 [[关键词]] 形式，但关键词本身不是任何实体页的路径，导致断链。
    本函数把这些已知关键词重写为指向 wiki/core-rules/ 术语页（或其他
    已存在页面）的 [[path|显示名]] 形式；无法识别的目标保持原样，不
    编造新的链接目标。
    """
    def _replace(m: "re.Match[str]") -> str:
        raw_target = m.group(1)
        display = m.group(2)
        target = raw_target.strip()
        if not target or "/" in target:
            return m.group(0)  # 已经是路径形式（含 "/"），不处理

        # 组合技能："危险，双联" 这类由多个关键词以顿号/逗号连接的裸链接
        for sep in ("，", "、", ","):
            if sep in target:
                parts = [p.strip() for p in target.split(sep) if p.strip()]
                if len(parts) > 1:
                    resolved = [_resolve_known_alias(p) for p in parts]
                    if all(resolved):
                        return sep.join(
                            "[[{}|{}]]".format(path, part)
                            for path, part in zip(resolved, parts)
                        )
                break

        canonical = _resolve_known_alias(target)
        if canonical is None:
            return m.group(0)
        label = display.strip() if display else raw_target.strip()
        return "[[{}|{}]]".format(canonical, label)

    return _WIKILINK_RE.sub(_replace, body)


def _parse_frontmatter_yaml(text: str) -> Optional[Dict]:
    """从 .md 文件中解析 YAML frontmatter（标准 PyYAML 解析）。"""
    import yaml
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        result = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(result, dict):
        return None
    return result


def load_link_targets(pages_dir: Path) -> Dict[str, str]:
    """扫描 wiki/ 下所有 .md 文件，构建 {名称: 相对路径} 索引。

    索引键包含：中文名、英文名、所有别名。
    值为 wiki/ 根目录下的相对路径（用于 [[path|name]] 语法）。
    """
    targets: Dict[str, str] = {}
    for md_file in sorted(pages_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _parse_frontmatter_yaml(text)
        if fm is None:
            continue
        if fm.get("type") == "core-rule":
            # 核心技能/武器技能术语页不参与通用实体名自动加链：
            # 这些名字（"双联""重型""突击"……）在武器数据表里大量以
            # 单方括号 [双联] 等非 wikilink 记法出现，若当作普通实体名
            # 自动扫描注入，会把 [双联] 错误改写成嵌套的 [[[...]]]。
            # 这类裸关键词断链改由 canonicalize_known_terms() 精确修复。
            continue
        rel_path = str(md_file.relative_to(pages_dir)).replace("\\", "/")

        # 注册各种名称
        names_found: List[str] = []
        for key in ("name_zh", "name_en"):
            val = fm.get(key)
            if val and isinstance(val, str):
                names_found.append(val)
        # 别名
        aliases_val = fm.get("aliases")
        if isinstance(aliases_val, list):
            for a in aliases_val:
                if isinstance(a, str):
                    names_found.append(a)

        for name in names_found:
            name = name.strip()
            if name and name not in targets:
                targets[name] = rel_path

    return targets


def _faction_of(rel_path: Optional[str]) -> Optional[str]:
    """相对路径 → 所属阵营目录名（"factions/<阵营>/…"），非阵营页返回 None。"""
    if not rel_path:
        return None
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[0] == "factions":
        return parts[1]
    return None


def _name_pattern(name: str) -> "re.Pattern":
    """实体名 → 带边界护栏的匹配正则。

    ASCII 词首/词尾加 (?<![A-Za-z0-9]) / (?![A-Za-z0-9]) 负回溯——防 "Vyper" 命中
    "Vypers"、"Ork" 命中 "Orkish"。CJK 无词界可用（\\w 在 Py3 匹配 CJK，空格边界
    对中文恒假），靠调用方的长度门（纯 CJK ≥3）拦短词误注。
    """
    pat = re.escape(name)
    if name[0].isascii() and name[0].isalnum():
        pat = r"(?<![A-Za-z0-9])" + pat
    if name[-1].isascii() and name[-1].isalnum():
        pat = pat + r"(?![A-Za-z0-9])"
    return re.compile(pat)


def inject_wikilinks(
    page: WikiPage,
    link_targets: Dict[str, str],
    term_aliases: Optional[Dict[str, str]] = None,
    self_path: Optional[str] = None,
) -> WikiPage:
    """在 page.body 中扫描已知实体名，首次出现处注入 [[path|name]]。

    规则：
      - 每个实体名在正文中首次出现时加链接
      - 不链接自身（page.fm 中已有的名称；以及 self_path 指向自身的候选——
        H14：terms.json 全局别名可能不在 fm 名称集里，但目标是本页自己，
        按目标路径过滤才堵得住这类自链）
      - 阵营门：目标是异阵营的单位页（factions/X/units/*）时不注入——1715 个单位名
        的全局笛卡尔扫描曾把「堡主战斧」切进星际战士 Castellan、把兽人页的「先知」
        链到灵族 Farseer（gnhf 审查模块 6 F2，产物实测 125 处词中/跨阵营错链）
      - 纯 CJK 名长度 <3 不注入（先知/毒刃/堡主 类同形短词是重灾区）；
        ASCII 词边界见 _name_pattern

    self_path：当前页面相对 wiki 根的路径（"/"分隔，含 .md），可选。

    返回新的 WikiPage（不可变模式——创建新对象）。
    """
    body = page.body
    # 构建"不链接自己"的名称集合
    self_names: Set[str] = set()
    if page.fm.name_zh:
        self_names.add(page.fm.name_zh)
    if page.fm.name_en:
        self_names.add(page.fm.name_en)
    for alias in page.fm.aliases:
        self_names.add(alias)

    # 将别名映射也加入候选（社区译名 → wiki 页名）
    if term_aliases:
        for alias, target_en in term_aliases.items():
            if target_en in link_targets and alias not in link_targets:
                link_targets[alias] = link_targets[target_en]

    # 按名称长度降序排列，优先匹配长的（避免"火战士"在"火战士队"前面误匹配）
    # 双重自引用过滤：名字命中 self_names，或目标路径就是本页自身（H14）
    candidates = sorted(
        [(n, p) for n, p in link_targets.items()
         if n not in self_names and (self_path is None or p != self_path)],
        key=lambda x: -len(x[0]),
    )

    # 记录每个名称是否已经链接过
    linked: Set[str] = set()
    modified = False

    def _link_spans(text: str):
        # 已有 [[...]] 的字符区间——name 落在其中（尤其是路径里）不得再注入，
        # 否则会把链接嵌套进另一条链接的路径（如 基因窃取者 落在
        # factions/基因窃取者教派/units/lictor.md 路径里 → 断链的嵌套 wikilink）
        return [(m.start(), m.end()) for m in re.finditer(r"\[\[[^\]]*\]\]", text)]

    self_faction = _faction_of(self_path)
    for name, path in candidates:
        if name in linked or len(name) < 2:
            continue
        # 纯 CJK 短名（<3 字）误注率极高（同形词遍地），直接不注
        if len(name) < 3 and all("一" <= c <= "鿿" for c in name):
            continue
        # 阵营门：异阵营单位页不作为注入目标（同阵营/非单位页不受限；
        # 仅在调用方提供了 self_path 语境时生效——inject_all 生产路径恒传）
        target_faction = _faction_of(path)
        if (self_path is not None and target_faction is not None
                and "/units/" in path and target_faction != self_faction):
            continue
        # 用正则查找 name 首个「不在任何已有 [[...]] 区间内」的出现处
        pattern = _name_pattern(name)
        spans = _link_spans(body)
        match = next((m for m in pattern.finditer(body)
                      if not any(s <= m.start() < e for s, e in spans)), None)
        if match:
            start, end = match.start(), match.end()
            # 注入链接
            link = "[[{}|{}]]".format(path, name)
            body = body[:start] + link + body[end:]
            linked.add(name)
            modified = True

    if modified:
        return WikiPage(fm=page.fm, body=body)
    return page


def escape_table_pipes(body: str) -> str:
    """表格行内 [[路径|别名]] 的别名竖线转义成 \\|，避免与表格列分隔符 | 冲突。

    canonicalize 把裸 [[速射2]] 落成 [[core-rules/rapid-fire.md|速射2]] 后，若该链接
    在表格单元格里，未转义的 | 会被 Markdown 表格解析器当成列分隔符而断列。幂等。"""
    def esc_link(m):
        inner = m.group(1)
        return m.group(0) if "\\|" in inner else "[[" + inner.replace("|", "\\|") + "]]"
    out = []
    for ln in body.split("\n"):
        if re.match(r"\s*\|", ln):
            ln = re.sub(r"\[\[([^\]]+)\]\]", esc_link, ln)
        out.append(ln)
    return "\n".join(out)


def inject_all(
    pages_dir: Path,
    terms_path: Optional[Path] = None,
) -> List[str]:
    """遍历 wiki/ 所有实体页，注入交叉链接后写回。

    返回修改的文件相对路径列表。
    """
    targets = load_link_targets(pages_dir)
    if not targets:
        print("未找到可链接的 wiki 页面。")
        return []

    # M6：复用 wiki_compile.terms.load_term_aliases（缺失/损坏/结构异常安全降级），
    # 不再在此处重复实现 terms.json 解析。
    from wiki_compile.terms import load_term_aliases
    term_aliases: Optional[Dict[str, str]] = (
        load_term_aliases(terms_path) if terms_path else None)

    # 链接注入是流水线自动改写：同步刷新 .gen_hashes.json 登记值，
    # 否则下一次 synthesize 会把注入后的页面误判为"人工编辑"而拒绝更新（配合 H16）。
    from wiki_engine._io import load_gen_hashes, save_gen_hashes, text_sha256
    gen_hashes = load_gen_hashes(pages_dir)
    hashes_dirty = False

    modified: List[str] = []
    for md_file in sorted(pages_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        parsed = WikiPage.from_markdown(text)
        if parsed is None:
            continue

        canonical_body = canonicalize_known_terms(parsed.body)
        if canonical_body != parsed.body:
            parsed = WikiPage(fm=parsed.fm, body=canonical_body)

        rel = str(md_file.relative_to(pages_dir)).replace("\\", "/")
        result = inject_wikilinks(parsed, dict(targets), term_aliases,
                                  self_path=rel)
        escaped_body = escape_table_pipes(result.body)
        if escaped_body != result.body:
            result = WikiPage(fm=result.fm, body=escaped_body)
        new_text = result.to_markdown()
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")
            modified.append(rel)
            if rel in gen_hashes:
                gen_hashes[rel] = text_sha256(new_text)
                hashes_dirty = True

    if hashes_dirty:
        save_gen_hashes(pages_dir, gen_hashes)
    print("交叉链接: {} 页已更新".format(len(modified)))
    return modified


# ── re-export for test convenience ──
__all__ = [
    "load_link_targets", "inject_wikilinks", "inject_all",
    "canonicalize_known_terms",
]
