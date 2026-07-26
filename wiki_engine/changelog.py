"""wiki_engine/changelog.py — 官方「规则更新」章节 → 规则变更清单 wiki 页。

**要的是真改动，不是版本号 diff**：某计谋 CP 从 1 改 2、某分遣队规则整段重写、
某单位技能被移除。这些改动官方自己列在每个阵营包的「规则更新」章节里，
本模块把它们抽出来，不做任何推断。

**v1.1 增量怎么来的**：阵营包导言写着「凡是在本阵营包初版发布之后所作的修订，
均将以红色高亮显示」。红色是 PDF span 的 `color` 属性（`0xa31418`），
所以 v1.0 → v1.1 的增量是**从文件里读出来的**，不是靠比对两个版本的 PDF 猜的——
手上只有 v1.1 一版，没有 v1.0 可 diff，红色标记是唯一的一手证据。

**版式判据全部来自 PDF 自身的字号/字体/字色**，不靠正则猜标题：
  · size 20 粗体 → 章节大标题（`规则更新` / `常见问题解答`）
  · size 12 粗体 → 分组（`军队规则` / `烈焰使者分遣队` / `数据表`）
  · size 8.5 粗体 → 条目标题（`帝皇圣光计谋，CP 花费`）
  · size 8.5 细体 → 条目正文（`修改为“2CP”。`）
  · color 0xa31418 → 初版之后新增的修订（= v1.1 增量）

**对账**：抽取必须配反向对账（仓库教训：核心规则切章三轮漏切，每次都报"成功"）。
`extract_faction_updates` 会把章节里**没被归入任何条目**的行数一并返回，
生成器在 orphan 行过多时报警而不是安静地少写几条。

CLI：python -m wiki_engine changelog
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from wiki_engine._io import (atomic_write_text, load_gen_hashes,
                             save_gen_hashes, text_sha256)
from wiki_engine.core_rules_zh import format_zh_text
from wiki_engine.crosslinks import escape_table_pipes
from wiki_engine.models import WikiPage, WikiPageFrontmatter, slugify
from wiki_engine.pdf_sections import CONTROL_CHARS, _column_bounds

ZH_DIR = Path("data/官方中文")
UNIVERSAL_PDF = ZH_DIR / ("chi_22-07_warhammer_40,000_universal_rules_updates-"
                          "aqctndydaz-cnwbdjvk0p.pdf")
FACTION_GLOB = "chi_*faction_pack_*.pdf"
OUT_SUBDIR = "changelog"

# 官方标红色（初版之后新增的修订）。实测 `0xa31418`，同一个值在 27 个包里通用。
RED = 0xA31418
# 字号档位。用区间不用等值：不同包的排版有零点几的浮动。
_CHAPTER_SIZE, _GROUP_SIZE, _ENTRY_SIZE = 18.0, 11.0, 7.5
# 章节页顶部的巨号阵营名（实测 size 36）
_FACTION_NAME_SIZE = 30.0
# 「规则更新」章节自己的标题与子标题——碰到它们不算章节结束
_SELF_HEADINGS = {"规则更新", "更新", "规则更新与澄清"}
_CHAPTER_TITLE = "规则更新"
# 章节最多读这么多页。没有这个上限，末章（后面没有下一章标题）会一路读到
# 131 页文档的结尾，dict 提取的代价直接翻十几倍。
_MAX_CHAPTER_PAGES = 15
# 页脚的生效日期行排在正文栏里、字号也和正文一样，只能按文案认。
# 不滤掉会粘在本页最后一条改动的末尾，读起来像那条改动自带的生效条件。
_FOOTER_LINE = re.compile(r"^自\s*20\d\d\s*年.{0,24}起适用")
# 章节导言。它 size 9、整行粗体，和 size 8.5 的条目标题只差半档，
# 靠字号分不开，只能按这句固定文案认。不滤掉的话，导言会变成本章的头两条
# 「改动」，正文还是空的。
_INTRO_START = re.compile(r"^本章节旨在")
# 正文的起始词。官方每条改动的正文都以它们开头，而条目标题从不这样开头。
# 用来挡住「标题续行合并」——否则 `卡斯特兰机器人，脉冲电网技能` 会把
# 紧跟其后、同样整行粗体的 `修改为：` 吞进标题里。
_BODY_START = re.compile(r"^(?:修改为|改为|将|移除|添加|增加|替换|删除|更改)")
# 条目标题里不会出现句号。官方偶尔把整段正文排成粗体，
# 只看粗体的话那些正文行会变成一堆没有正文的"条目"。
# **只能排句号**：感叹号在标题里合法——欧克蛮人的军队规则就叫「Waaagh！」，
# 把它排掉会连带整条规则的正文一起变成没人认领的孤儿行。
_SENTENCE_END = "。"


@dataclass(frozen=True)
class ChangeEntry:
    """一条官方规则改动。`new_in_latest` = 红色高亮 = 初版之后新增的修订。"""
    faction: str
    group: str
    title: str
    body: str
    new_in_latest: bool
    page: int


@dataclass
class FactionChanges:
    faction: str
    faction_zh: str
    pdf: str
    version: str
    entries: List[ChangeEntry] = field(default_factory=list)
    orphan_lines: List[str] = field(default_factory=list)   # 没归进任何条目的行
    pages: List[int] = field(default_factory=list)
    # 三态要分清，否则「0 条」看起来都像抽取失败：
    #   有章节 + 有条目  → 正常
    #   有章节 + 0 条目  → 该阵营本次真的没有改动（混沌恶魔：导言后直接是 FAQ）
    #   无章节           → 首版包本来就没有「规则更新」章（死亡守望 v1.0）
    chapter_found: bool = False


@dataclass(frozen=True)
class _Line:
    text: str
    size: float
    bold: bool
    color: int
    page: int


def _page_lines(page, page_no: int) -> List[_Line]:
    """一页 → 按 (栏, y) 排好序的行，带字号/字体/字色。

    规则更新页是双栏。不按栏排序的话，左右两栏的条目会交错，
    某条计谋的「修改为…」会接到另一条计谋的标题下面——读起来通顺，内容是错的。
    """
    blocks = [b for b in page.get_text("dict")["blocks"] if b.get("lines")]
    if not blocks:
        return []
    bounds = _column_bounds([b["bbox"][0] for b in blocks])

    def column_of(x0: float) -> int:
        idx = 0
        for i, left in enumerate(bounds):
            if x0 >= left - 0.01:
                idx = i
        return idx

    blocks.sort(key=lambda b: (column_of(b["bbox"][0]), round(b["bbox"][1], 1)))
    out: List[_Line] = []
    for block in blocks:
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = CONTROL_CHARS.sub("", "".join(s["text"] for s in spans)).strip()
            if not text:
                continue
            head = spans[0]
            if _FOOTER_LINE.match(text):
                continue
            out.append(_Line(text=text, size=round(head["size"], 1),
                             # **整行**粗体才算标题。官方在正文里把「效果：」
                             # 「目标：」这类字段名单独加粗，只看首个 span 的话
                             # 这些正文行会被当成新条目的标题，把一条改动
                             # 从中间劈成两条、前一条正文还空着。
                             bold=all("Bold" in s["font"] for s in spans),
                             # 一行里只要有红字就算红：官方常只标改动的那几个字
                             color=RED if any(s["color"] == RED for s in spans)
                             else head["color"],
                             page=page_no))
    return out


def _pdf_version(text: str) -> str:
    m = re.search(r"版本\s*([\d.]+)", text)
    return m.group(1) if m else ""


def extract_faction_updates(pdf_path: Path) -> FactionChanges:
    """一个阵营包 → 它的「规则更新」章节全部条目。

    章节从 size-20 的「规则更新」标题起，到下一个 size-20 标题止
    （通常是「常见问题解答」——那是澄清不是改动，不收）。
    """
    import fitz

    name = pdf_path.name
    m = re.search(r"faction_pack_(.+?)-", name)
    faction = (m.group(1) if m else pdf_path.stem).replace("_", " ").strip()
    result = FactionChanges(faction=faction, faction_zh="", pdf=name, version="")

    with fitz.open(str(pdf_path)) as doc:
        first = doc[0].get_text() if doc.page_count else ""
        result.version = _pdf_version(first)
        # 先用便宜的纯文本扫出候选页，再只对候选页做带字体属性的 dict 提取——
        # 后者贵得多，而阵营包最厚的有 131 页，全量提取要几分钟。
        # 候选必须再按**字号**确认：第 1 页的目录里也写着「▪规则更新的修正」，
        # 只按文本命中会把起点定在目录页，然后一条都抽不出来。
        candidates = [i for i in range(doc.page_count)
                      if _CHAPTER_TITLE in doc[i].get_text()]
        start, lines = None, []      # type: Optional[int], List[_Line]
        for i in candidates:
            page_lines = _page_lines(doc[i], i + 1)
            if any(ln.size >= _CHAPTER_SIZE and ln.bold
                   and ln.text.strip() == _CHAPTER_TITLE for ln in page_lines):
                start, lines = i, list(page_lines)
                break
        if start is None:
            return result                # chapter_found 保持 False
        result.chapter_found = True
        # 阵营中文名是章节页的巨号标题（size 36）。用它而不是文件名派生的英文——
        # 官方文件名里有 `orkss`、`imperia_agents`、`emperor_s_children` 这种
        # 笔误和下划线，直接摊到页面上很难看，也搜不到。
        result.faction_zh = next(
            (ln.text for ln in lines if ln.size >= _FACTION_NAME_SIZE), "")
        for i in range(start + 1, min(doc.page_count, start + _MAX_CHAPTER_PAGES)):
            page_lines = _page_lines(doc[i], i + 1)
            lines.extend(page_lines)
            # 出现下一章的大标题就不必再往后读（主循环会在该标题处收尾）
            if any(ln.size >= _CHAPTER_SIZE and ln.bold
                   and ln.text.strip() not in _SELF_HEADINGS for ln in page_lines):
                break

    group = ""
    in_intro = False
    current: Optional[List[object]] = None      # [title, [body…], red, page]
    entries: List[ChangeEntry] = []
    orphans: List[str] = []
    pages: List[int] = []

    def close() -> None:
        if current is not None:
            body = format_zh_text("\n".join(str(x) for x in current[1]))
            entries.append(ChangeEntry(
                faction=faction, group=group or "（未分组）",
                title=str(current[0]), body=body,
                new_in_latest=bool(current[2]), page=int(current[3])))

    # 起点页在上面已按字号确认过，这里不再靠「行序里先出现章节标题」来开闸——
    # 版面把「修女会」「规则更新」两个大标题放在**右栏**（x0≈250），正文在左栏
    # （x0≈42），按栏排序后标题落到第 45 行，等它出现就已经跳过了整页正文，
    # 页面上只剩后半章的条目。
    for ln in lines:
        # 下一章（常见问题解答）开始。上限排除 size 36 的阵营名——
        # 它也排在正文之后，按「大字即新章」判会在第一页就收工。
        if (_CHAPTER_SIZE <= ln.size < _FACTION_NAME_SIZE and ln.bold
                and ln.text.strip() not in _SELF_HEADINGS):
            break
        if ln.size >= _CHAPTER_SIZE:
            in_intro = False
            continue                             # 本章自己的标题/子标题与阵营名
        if _INTRO_START.match(ln.text):
            in_intro = True
        if in_intro:
            if ln.size >= _GROUP_SIZE:           # 导言到第一个分组标题为止
                in_intro = False
            else:
                continue
        if ln.page not in pages:
            pages.append(ln.page)
        if ln.bold and ln.size >= _GROUP_SIZE:
            close()
            current = None
            group = ln.text
            continue
        looks_like_title = (ln.bold and ln.size >= _ENTRY_SIZE
                            and not any(c in ln.text for c in _SENTENCE_END)
                            and not _BODY_START.match(ln.text))
        if looks_like_title:
            # 上一条还一个字正文都没有 → 这不是新条目，是上一条的标题被版式
            # 折成了两行（`…修女会犀牛装甲车 -` + `关键词部分`）。
            # 官方每条改动后面必跟「修改为…」，真条目不会没有正文。
            if current is not None and not current[1]:
                sep = " " if str(current[0]).endswith(("-", "－", "—")) else ""
                current[0] = "{}{}{}".format(current[0], sep, ln.text)
                current[2] = bool(current[2]) or ln.color == RED
                continue
            close()
            current = [ln.text, [], ln.color == RED, ln.page]
            continue
        if current is None:
            # 章节导言之外还落单的行要报出来——可能是没认出的排版变体
            orphans.append(ln.text)
            continue
        current[1].append(ln.text)              # type: ignore[union-attr]
    close()

    result.entries = entries
    result.orphan_lines = orphans
    result.pages = pages
    return result


def extract_universal_updates(pdf_path: Path = UNIVERSAL_PDF) -> FactionChanges:
    """「通用规则更新」→ 跨阵营条目。这份文档没有分组，标题是 size-12 粗体。"""
    import fitz

    result = FactionChanges(faction="Universal", faction_zh="通用规则更新",
                            pdf=pdf_path.name, version="")
    with fitz.open(str(pdf_path)) as doc:
        result.version = _pdf_version(doc[0].get_text())
        lines: List[_Line] = []
        for i in range(doc.page_count):
            lines.extend(_page_lines(doc[i], i + 1))

    entries: List[ChangeEntry] = []
    current: Optional[List[object]] = None

    def close() -> None:
        if current is not None:
            entries.append(ChangeEntry(
                faction="Universal", group="通用规则更新",
                title=str(current[0]),
                body=format_zh_text("\n".join(str(x) for x in current[1])),
                new_in_latest=bool(current[2]), page=int(current[3])))

    for ln in lines:
        if ln.size >= _CHAPTER_SIZE:
            continue                             # 文档大标题与版本号
        if ln.bold and ln.size >= _GROUP_SIZE:
            close()
            current = [ln.text, [], ln.color == RED, ln.page]
            continue
        if current is None:
            continue                             # 文档导言
        current[1].append(ln.text)               # type: ignore[union-attr]
    close()

    # 标题跨行的那条（`可以在每个阶段/回合中` + `使用超过一次的计谋`）会被
    # 拆成两条，后一条正文为空。合并回去，并保留合并痕迹供对账。
    merged: List[ChangeEntry] = []
    for e in entries:
        if merged and not merged[-1].body:
            prev = merged.pop()
            merged.append(ChangeEntry(
                faction=e.faction, group=e.group,
                title="{}{}".format(prev.title, e.title), body=e.body,
                new_in_latest=prev.new_in_latest or e.new_in_latest, page=prev.page))
        else:
            merged.append(e)
    result.entries = merged
    result.pages = sorted({e.page for e in merged})
    return result


def collect_all(zh_dir: Path = ZH_DIR) -> List[FactionChanges]:
    packs = sorted(zh_dir.glob(FACTION_GLOB))
    out = [extract_faction_updates(p) for p in packs]
    if (zh_dir / UNIVERSAL_PDF.name).exists():
        out.insert(0, extract_universal_updates(zh_dir / UNIVERSAL_PDF.name))
    return out


# ── 渲染 ───────────────────────────────────────────────────────────

_NEW_MARK = "🆕"


def _entry_lines(entry: ChangeEntry) -> List[str]:
    mark = " {}".format(_NEW_MARK) if entry.new_in_latest else ""
    return ["### {}{}".format(entry.title, mark), "",
            entry.body or "（官方未给出正文）", ""]


def render_faction_page(fc: FactionChanges) -> Tuple[WikiPage, str]:
    slug = slugify(fc.faction)
    label = fc.faction_zh or fc.faction
    new_count = sum(1 for e in fc.entries if e.new_in_latest)
    L: List[str] = [
        "《{}》阵营包 v{} 的官方「规则更新」章节，共 {} 条改动，"
        "其中 {} 条是初版发布之后新增的（标 {}）。".format(
            label, fc.version or "?", len(fc.entries), new_count, _NEW_MARK),
        "",
        "> 正文照抄官方简体中文阵营包，未作改写。{} 标记来自官方**红色高亮**"
        "——阵营包导言写明「凡是在本阵营包初版发布之后所作的修订，均将以红色高亮显示」，"
        "所以它就是 v1.0 → v{} 的增量。".format(_NEW_MARK, fc.version or "1.1"),
        "",
    ]
    if not fc.chapter_found:
        L += ["本阵营包没有「规则更新」章节——它是首版发布，尚无改动可列。", ""]
    elif not fc.entries:
        L += ["本阵营包有「规则更新」章节，但**官方本次没有列出任何改动**"
              "（导言之后直接进入常见问题解答）。", ""]

    group = ""
    for entry in fc.entries:
        if entry.group != group:
            group = entry.group
            L += ["## {}".format(group), ""]
        L += _entry_lines(entry)

    fm = WikiPageFrontmatter(
        id="changelog-{}".format(slug),
        name_zh="{} 规则更新".format(label),
        name_en="{} Rules Updates".format(fc.faction.title()),
        type="changelog",
        # 阵营包没有中文名时 label 就等于英文名，两条别名会撞成同一个字符串，
        # lint 会报「同一别名被同一页用了两次」——去重而不是让它进报告
        aliases=[a for a in ["{} 规则变更".format(label),
                             "{} 规则更新".format(fc.faction)]
                 if a != "{} 规则更新".format(label)],
        sources=[{"book": fc.pdf, "pages": ["page_{:03d}".format(p)
                                            for p in fc.pages]}],
        version={"rules": "阵营包 v{}（2026-07-22 生效）".format(fc.version or "1.1")},
        updated="2026-07-26",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n")), slug


def render_index(all_changes: Sequence[FactionChanges]) -> WikiPage:
    universal = next((c for c in all_changes if c.faction == "Universal"), None)
    factions = [c for c in all_changes if c.faction != "Universal"]
    total = sum(len(c.entries) for c in factions)
    total_new = sum(1 for c in factions for e in c.entries if e.new_in_latest)

    L: List[str] = [
        "11 版官方规则变更清单：**{} 条阵营改动**（{} 个阵营包）"
        "＋ **{} 条通用规则更新**。其中 {} 条阵营改动标了 {}，"
        "是各包初版发布之后新增的修订。".format(
            total, len(factions), len(universal.entries) if universal else 0,
            total_new, _NEW_MARK),
        "",
        "> 这份清单只收**官方自己列出的改动**，全部来自阵营包的「规则更新」章节"
        "与《通用规则更新》，逐条照抄、不作推断。"
        "{} 标记读自 PDF 的红色高亮，不是靠比对两个版本猜的——"
        "手上只有 v1.1 一版，没有 v1.0 可以 diff。".format(_NEW_MARK),
        "",
    ]

    if universal and universal.entries:
        L += ["## 通用规则更新 v{}（跨全部阵营）".format(universal.version or "1.0"), ""]
        for entry in universal.entries:
            L += _entry_lines(entry)

    L += ["## 各阵营改动一览", "",
          "| 阵营包 | 版本 | 改动条数 | 其中新增 | 明细 |",
          "|---|---:|---:|---:|---|"]
    for c in sorted(factions, key=lambda c: -len(c.entries)):
        slug = slugify(c.faction)
        new_count = sum(1 for e in c.entries if e.new_in_latest)
        if not c.chapter_found:
            note = "首版，无更新章节"
        elif not c.entries:
            note = "官方本次未列改动"
        else:
            note = "[[changelog/factions/{}.md\\|查看]]".format(slug)
        L += ["| {} | v{} | {} | {} | {} |".format(
            c.faction_zh or c.faction, c.version or "?", len(c.entries), new_count, note)]
    L += [""]

    L += ["## 数值层的 10 版 → 11 版漂移", "",
          "本页收的是官方**文字**改动。兵牌数值与规则文本的 10→11 漂移是另一条线，"
          "早已逐条落库并带 `from` 值守卫，见 `db_compile/fp_errata_patches.json`"
          "（属性/武器/关键词补丁）与 `db_compile/fp_rules_patches.json`"
          "（规则文本、11 版移除条目、11 版新增条目）。"
          "两条线口径不同，不要混着读。", ""]

    fm = WikiPageFrontmatter(
        id="changelog-index",
        name_zh="规则变更清单",
        name_en="Rules Change Log",
        type="changelog",
        aliases=["规则更新", "规则变更", "改动清单"],
        sources=[{"book": "官方阵营包 v1.1 + 通用规则更新 v1.0",
                  "pages": ["规则更新章节"]}],
        version={"rules": "11版 阵营包 v1.1（2026-07-22 生效）"},
        updated="2026-07-26",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n"))


def generate_all(zh_dir: Path = ZH_DIR,
                 wiki_root: Path = Path("wiki")) -> Dict[str, object]:
    all_changes = collect_all(zh_dir)
    gen_hashes = load_gen_hashes(wiki_root)
    written = 0
    conflicts: List[str] = []

    def write(rel: str, text: str) -> None:
        nonlocal written
        target = wiki_root / rel
        if target.exists() and gen_hashes.get(rel) is not None:
            try:
                if text_sha256(target.read_text(encoding="utf-8")) != gen_hashes[rel]:
                    conflicts.append(rel)
                    return
            except (OSError, UnicodeDecodeError):
                pass
        atomic_write_text(target, text)
        gen_hashes[rel] = text_sha256(text)
        written += 1

    try:
        for fc in all_changes:
            if fc.faction == "Universal":
                continue
            page, slug = render_faction_page(fc)
            write("{}/factions/{}.md".format(OUT_SUBDIR, slug), page.to_markdown())
        write("{}/index.md".format(OUT_SUBDIR), render_index(all_changes).to_markdown())
    finally:
        save_gen_hashes(wiki_root, gen_hashes)

    factions = [c for c in all_changes if c.faction != "Universal"]
    return {
        "packs": len(factions),
        "entries": sum(len(c.entries) for c in factions),
        "new_in_latest": sum(1 for c in factions for e in c.entries
                             if e.new_in_latest),
        "universal": sum(len(c.entries) for c in all_changes
                         if c.faction == "Universal"),
        "written": written,
        "conflicts": conflicts,
        # 抽取必配反向对账：章节里没归进任何条目的行要报出来，
        # 不能等读者发现某个分遣队的改动整块不见了
        "orphan_lines": {c.faction: c.orphan_lines
                         for c in all_changes if c.orphan_lines},
        "no_chapter": [c.faction for c in factions if not c.chapter_found],
        "empty_chapter": [c.faction for c in factions
                          if c.chapter_found and not c.entries],
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="wiki_engine.changelog")
    ap.add_argument("--zh-dir", default=str(ZH_DIR))
    ap.add_argument("--wiki", default="wiki")
    args = ap.parse_args()
    rep = generate_all(Path(args.zh_dir), Path(args.wiki))
    print("规则变更清单：{} 个阵营包 / {} 条改动（{} 条为初版后新增）"
          " + {} 条通用更新 → 写 {} 页".format(
              rep["packs"], rep["entries"], rep["new_in_latest"],
              rep["universal"], rep["written"]))
    if rep["no_chapter"]:
        print("· {} 个包没有「规则更新」章节（首版）：{}".format(
            len(rep["no_chapter"]), "、".join(rep["no_chapter"])))
    if rep["empty_chapter"]:
        print("· {} 个包有章节但官方未列改动：{}".format(
            len(rep["empty_chapter"]), "、".join(rep["empty_chapter"])))
    if rep["orphan_lines"]:
        print("⚠️ 有行没归进任何条目（排版变体？先核对再发布）：{}".format(
            {k: len(v) for k, v in rep["orphan_lines"].items()}))
    if rep["conflicts"]:
        print("⚠️ {} 页检测到人工编辑，已跳过覆盖".format(len(rep["conflicts"])))


if __name__ == "__main__":
    main()
