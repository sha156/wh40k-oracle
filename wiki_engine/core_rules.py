"""wiki_engine/core_rules.py — 11 版核心规则全文 → 按官方章节切成**中英对照** wiki 页。

源是 `data_refined/Core Rules - New 40K Core Rules/`（官方英文核心规则的逐页 refine 产物）。
两样东西都来自源文件本身，**没有一处是按记忆补的**：

  · **章名与分卷**：page_002 就是官方目录页（`01. CORE CONCEPTS - pg 8` …），
    24 章分属 BASIC RULES / THE BATTLE ROUND / BATTLEFIELDS AND TACTICS /
    ADVANCED RULES / REFERENCE 五卷。
  · **小节与官方节号**：正文里每个小节都带 `NN.NN` 编号（`### [BLAST] 24.05`）。

**为什么先拼再切**：小节会跨页续行（refine 产物用 `<!--CONT-->` 标记接续页）。
按页切会把一条规则拦腰截断，读者看到的是半句话。所以先按页序拼成整份文档再切小节。

正文语言：**中文为主、英文原文可展开对照**（2026-07-26）。中文来自
`data/官方中文/chi_01-06_..._core_rules-*.pdf`，是 **GW 官方 11 版简体中文全译本**，
按 wiki 宪法 §6 与英文原版同档权威。

这与 2026-07-25「正文一律官方英文」的裁决不冲突：那条裁决拒的是
`data_refined/战锤40K总规则10版老湿腐版1.11` 这类**十版民间汉化**（版本已漂移），
不是 GW 自己发的 11 版官方中文。三类实体页（分队/战略/增强）仍是英文正文，
因为官方没有对应的中文语料。

**三个正文源，各司其职**：
  · 中文正文与中文小节名 ← 官方中文 PDF（`core_rules_zh.py`）
  · 英文正文 ← refine 产物（LLM 清洗过，排版最好），共 143 节
  · 英文正文兜底 ← 英文 PDF 直提，补 refine **丢了节号**的 13 节
    （`1. SELECT WEAPONS 04.01` 被 refine 改写成 `**1. SELECT WEAPONS**:`，
     节号没了就配不上中文，那 13 节会只剩中文没有英文对照）

CLI：python -m wiki_engine core-rules
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wiki_engine._io import (atomic_write_text, load_gen_hashes,
                             save_gen_hashes, text_sha256)
from wiki_engine.core_rules_zh import ZH_BOOK
from wiki_engine.crosslinks import escape_table_pipes
from wiki_engine.models import WikiPage, WikiPageFrontmatter, slugify

REFINED_DIR = Path("data_refined/Core Rules - New 40K Core Rules")
BOOK_NAME = "Core Rules - New 40K Core Rules"
OUT_SUBDIR = "core-rules/sections"

# 目录页里的章行：`01. CORE CONCEPTS - pg 8`
_TOC_CHAPTER = re.compile(r"^(\d{2})\.\s+([A-Z][A-Z0-9 \-'&/]+?)\s*-\s*pg\s*(\d+)\s*$", re.M)
# 目录页里的卷标题：`## BASIC RULES`
_TOC_PART = re.compile(r"^##\s+([A-Z][A-Z \-'&/]+)\s*$", re.M)

# 小节标题。五种实测形态都要认——漏一种就是**静默丢规则正文**：
#   `### [BLAST] 24.05`               带方括号的词条
#   `## MEASURING DISTANCES 01.04`
#   `### TERRAIN OBJECTIVES (14.01)`  括号包节号
#   `1. START OF COMMAND PHASE 08.01` 没有 # 前缀、前面带序号
#   `1.  **START OF CHARGE PHASE 11.01**` 粗体包裹（第 11 章整章都是这个形态，
#      不认它的话「冲锋阶段」只剩 1 节而不是 4 节，页面看着完整、内容缺三节）
#   `**1. START OF SHOOTING PHASE 10.01**` 粗体在序号**外面**（第 10 章前三节）
#   `## 21 SURGE MOVES 21.01`             标题自身以数字开头
#   `## COMMAND RE-ROLL 15.02 (1CP)`      节号**后面还有 CP 花费**（第 15 章 11 条
#      核心计谋全是这个形态）。这是第四次同型漏切，也是最阴的一次：前三次靠
#      `unextracted_hints()` 逮到，这次连探测器一起瞎了——它同样要求行尾是节号。
#      教训是探测器与被测正则不能共用同一条"行尾"假设，否则它只能发现
#      "我已经想到的形态"。真正逮到这 11 节的是**中文版节号清单**这个外部对账源。
_SECTION_SUFFIX = r"(?:[ \t]*\(\d+\s*CP\))?"
_SECTION = re.compile(
    r"^[ \t]*(?:#{1,4}[ \t]*)?\*{0,2}[ \t]*(?:\d+[.\s][ \t]*)?\*{0,2}[ \t]*"
    r"(\[?[A-Z][A-Za-z0-9 \-'’&/\[\]‑]*?\]?)[ \t]*"
    r"\(?(\d{2})\.(\d{2})\)?" + _SECTION_SUFFIX + r"[ \t]*\*{0,2}[ \t]*$", re.M)

# 对账用：任何"行尾带 NN.NN（可带 CP 花费）"的行都疑似小节标题。抽不到的要报出来，
# 不能等读者发现某章少了三节
_SECTION_HINT = re.compile(
    r"^.{0,80}?\b(\d{2})\.(\d{2})\b" + _SECTION_SUFFIX + r"[*)\s]*$", re.M)

_CONT_MARK = re.compile(r"^<!--CONT-->\s*$", re.M)
# 除换行与制表符外的控制字符：PDF 提取残留（实测 0x08 退格符挂在
# `## [CLOSE-QUARTERS] 24.07` 行尾），肉眼不可见，却会让「行尾匹配」整条失效——
# 章节切不出来，页面看着完整却少几节。解析前统一清掉。
_CTRL_CHARS = re.compile("[" + "".join(chr(c) for c in
                         list(range(0, 9)) + [11, 12] + list(range(14, 32)) + [127])
                         + "]")


@dataclass(frozen=True)
class Chapter:
    num: str
    title: str
    part: str
    page: int


@dataclass
class Section:
    num: str            # "24.05"
    title: str          # "[BLAST]"
    body: str = ""
    source_pages: List[str] = field(default_factory=list)


# ── 目录（章名与分卷的唯一真源）───────────────────────────────────

def parse_toc(refined_dir: Path = REFINED_DIR) -> List[Chapter]:
    """官方目录页 → 24 章清单。解析不出足够章数时抛错，不返回半张表。"""
    toc_path = refined_dir / "page_002.md"
    if not toc_path.exists():
        raise FileNotFoundError(
            "找不到目录页 {}——章名与分卷的唯一真源。缺了只能靠记忆补章名，"
            "那是编数据".format(toc_path))
    text = toc_path.read_text(encoding="utf-8", errors="ignore")
    # 卷标题与章行按出现顺序交错，逐行扫一遍才知道每章归属哪一卷
    part = ""
    chapters: List[Chapter] = []
    for line in text.splitlines():
        mp = _TOC_PART.match(line)
        if mp:
            part = mp.group(1).strip()
            continue
        mc = _TOC_CHAPTER.match(line)
        if mc:
            chapters.append(Chapter(num=mc.group(1), title=mc.group(2).strip(),
                                    part=part, page=int(mc.group(3))))
    if len(chapters) < 20:
        raise ValueError(
            "目录页只解析出 {} 章（预期 24）——refine 产物可能换版，先核对再生成"
            .format(len(chapters)))
    return chapters


# ── 正文（先拼后切）─────────────────────────────────────────────

def _load_document(refined_dir: Path) -> Tuple[str, List[Tuple[int, str]]]:
    """按页序拼成整份文档，并记录每个字符偏移属于哪一页（供 sources 回溯）。"""
    pages = sorted(refined_dir.glob("page_*.md"),
                   key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    chunks: List[str] = []
    offsets: List[Tuple[int, str]] = []
    pos = 0
    for p in pages:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        raw = _CONT_MARK.sub("", raw)      # 续页标记只是排版记号，不是正文
        # PDF 提取残留的控制字符（实测有 \x08 退格符挂在 `## [CLOSE‑QUARTERS] 24.07`
        # 行尾）会让「行尾匹配」整条失效——章节切不出来，页面看着完整却少几节。
        # 这类字符肉眼不可见，只能在解析前统一清掉。
        raw = _CTRL_CHARS.sub("", raw)
        offsets.append((pos, p.name))
        chunks.append(raw)
        pos += len(raw) + 1
    return "\n".join(chunks), offsets


def _page_at(offsets: List[Tuple[int, str]], pos: int) -> str:
    name = offsets[0][1] if offsets else ""
    for start, pname in offsets:
        if start > pos:
            break
        name = pname
    return name


def collect_sections(refined_dir: Path = REFINED_DIR) -> Dict[str, List[Section]]:
    """整份文档 → {章号: [Section]}，正文按官方节号切分。"""
    doc, offsets = _load_document(refined_dir)
    hits = list(_SECTION.finditer(doc))
    by_chapter: Dict[str, List[Section]] = {}
    for i, m in enumerate(hits):
        chapter, sec = m.group(2), m.group(3)
        end = hits[i + 1].start() if i + 1 < len(hits) else len(doc)
        body = doc[m.end():end].strip()
        title = m.group(1).strip()
        page = _page_at(offsets, m.start())
        lst = by_chapter.setdefault(chapter, [])
        # 同一节号重复出现（目录页里也会列一次）：正文更长的那份胜出，短的丢弃
        existing = next((s for s in lst if s.num == "{}.{}".format(chapter, sec)), None)
        if existing is not None:
            if len(body) > len(existing.body):
                existing.body = body
                existing.title = title
            if page not in existing.source_pages:
                existing.source_pages.append(page)
            continue
        lst.append(Section(num="{}.{}".format(chapter, sec), title=title,
                           body=body, source_pages=[page]))
    for lst in by_chapter.values():
        lst.sort(key=lambda s: s.num)
    return by_chapter


def unextracted_hints(refined_dir: Path = REFINED_DIR) -> List[str]:
    """行尾带节号、却没被切成小节的节号清单（排版变体探测器）。

    第 11 章就是这么发现的：整章标题都写成 `1. **START OF CHARGE PHASE 11.01**`，
    旧正则不认粗体，于是「冲锋阶段」只切出 1 节——**页面看着完整，内容少了三节**。
    这类缺失不会报错，只能靠对账逮。
    """
    doc, _ = _load_document(refined_dir)
    got = {s.num for lst in collect_sections(refined_dir).values() for s in lst}
    hinted = {"{}.{}".format(m.group(1), m.group(2))
              for m in _SECTION_HINT.finditer(doc)}
    # 只关心 01–24 章：正文里还有 pg/尺寸之类的两位小数
    # 排除 NN.00：那是**章级**引用（目录式清单里的「- Actions 16.00」），
    # 官方节号从 .01 起，没有 .00 这一节
    return sorted(n for n in hinted - got
                  if "01" <= n.split(".")[0] <= "24" and not n.endswith(".00"))


# ── 三源合并 ───────────────────────────────────────────────────────

@dataclass
class BilingualSection:
    """一节的中英两份正文。中文为主，英文供对照。"""
    num: str
    title_zh: str
    title_en: str
    body_zh: str
    body_en: str
    asides_zh: List[str] = field(default_factory=list)
    en_from_pdf: bool = False        # 英文正文是否来自 PDF 兜底（refine 丢了这节）
    source_pages: List[str] = field(default_factory=list)
    zh_page: int = 0


def merge_bilingual(refined_dir: Path = REFINED_DIR) -> Dict[str, List[BilingualSection]]:
    """{章号: [BilingualSection]}。以**官方节号**为唯一配对键。

    不按顺序配、也不按标题文本配：中英两版的小节顺序在版面上一致，
    但任何一侧多切或少切一节，顺序配对就会整体错位且毫无征兆。
    """
    from wiki_engine.core_rules_zh import (format_zh_body, load_en_pdf_sections,
                                           load_zh_sections, useful_asides)

    refined = {s.num: s for lst in collect_sections(refined_dir).values() for s in lst}
    zh = load_zh_sections()
    en_pdf = load_en_pdf_sections()

    out: Dict[str, List[BilingualSection]] = {}
    for num in sorted(zh):
        chapter = num.split(".")[0]
        zh_sec = zh[num]
        ref = refined.get(num)
        pdf_en = en_pdf.get(num)
        # refine 命中但正文为空也要回退到 PDF——08.03「战斗震慑」就是这样：
        # 节号在，正文被 refine 归到了相邻小节，只看 `is not None` 会留下一节空白英文。
        if ref is not None and ref.body.strip():
            body_en, title_en, from_pdf = ref.body, ref.title, False
            pages = list(ref.source_pages)
        elif pdf_en is not None:
            body_en, title_en, from_pdf = pdf_en.body, pdf_en.title, True
            pages = ["page_{:03d}".format(pdf_en.page)]
        else:
            body_en, title_en, from_pdf, pages = "", "", False, []
        out.setdefault(chapter, []).append(BilingualSection(
            num=num,
            title_zh=zh_sec.title,
            title_en=title_en,
            body_zh=format_zh_body(zh_sec),
            body_en=body_en,
            asides_zh=useful_asides(zh_sec),
            en_from_pdf=from_pdf,
            source_pages=pages,
            zh_page=zh_sec.page,
        ))
    for lst in out.values():
        lst.sort(key=lambda s: s.num)
    return out


# ── 渲染 ───────────────────────────────────────────────────────────

_KEYWORD_CHAPTER = "24"

# 表格失真探测：PDF 文本层没有表格结构，致伤表这类内容会被拆成
# 「力量大于韧性」「+」「失败」一地碎片。碎片多且短 = 原文是张表，
# 中文这一侧必然失真，要在页面上说清楚而不是让读者以为规则就长这样。
_TABLE_MIN_BLOCKS, _TABLE_MAX_AVG = 6, 9.0


def looks_like_table(body_zh: str) -> bool:
    blocks = [b for b in body_zh.split("\n\n") if b.strip()]
    if len(blocks) < _TABLE_MIN_BLOCKS:
        return False
    return sum(len(b) for b in blocks) / len(blocks) < _TABLE_MAX_AVG


def render_chapter(chapter: Chapter, sections: List[BilingualSection],
                   title_zh: str = "") -> Tuple[WikiPage, str]:
    slug = "{}-{}".format(chapter.num, slugify(chapter.title))
    L: List[str] = [
        "11 版核心规则第 {} 章《{}》（{}）全文，共 {} 节，官方节号 {}。".format(
            chapter.num, title_zh or chapter.title, chapter.title, len(sections),
            "–".join([sections[0].num, sections[-1].num]) if sections else "—"),
        "",
    ]
    if chapter.num == _KEYWORD_CHAPTER:
        # 本章逐条词条另有中文页与反查索引，指过去而不是在这里再抄一份中文
        L += ["> 本章每个词条的中文解释见 `core-rules/` 下的同名页，"
              "中文名、官方节号与「哪些武器带它」的反查见 "
              "[[indexes/keywords.md\\|武器词条索引]]。", ""]
    L += ["> 正文为 **GW 官方简体中文版**；每节可展开对照官方英文原文。"
          "中文由官方 PDF 文本层直提，表格与版式会有失真——"
          "**判定规则以英文原文为准**。", ""]
    for s in sections:
        title = "## {} {}".format(s.title_zh or s.title_en or "（未命名）", s.num)
        L += [title, ""]
        if s.title_en and s.title_zh:
            L += ["*{}*".format(s.title_en), ""]
        L += [s.body_zh or "（官方中文 PDF 未提供本节正文）", ""]
        if looks_like_table(s.body_zh):
            L += ["> ⚠ 本节原文是表格，中文由 PDF 文本层直提、结构已散，"
                  "请以下方英文原文为准。", ""]
        for aside in s.asides_zh:
            L += ["> **边栏**：{}".format(aside.replace("\n", " ")), ""]
        if s.body_en:
            note = "（英文由 PDF 直提）" if s.en_from_pdf else ""
            L += ["<details>",
                  "<summary>官方英文原文{}</summary>".format(note), "",
                  s.body_en, "", "</details>", ""]

    pages = sorted({p for s in sections for p in s.source_pages})
    # 命名要与既有的同名概念页区分开：`core-rules/charge-phase.md` 讲的是「冲锋阶段
    # 是什么」，本页是「官方第 11 章全文」——两类不同的东西。直接用章名当页名会
    # 撞成 alias-conflict，也会让读者以为是重复页。
    sources = [{"book": BOOK_NAME, "pages": pages}]
    zh_pages = sorted({s.zh_page for s in sections if s.zh_page})
    if zh_pages:
        sources.append({"book": ZH_BOOK,
                        "pages": ["page_{:03d}".format(p) for p in zh_pages]})
    fm = WikiPageFrontmatter(
        id="core-rules-{}".format(chapter.num),
        name_zh="核心规则第 {} 章{}".format(
            int(chapter.num), "《{}》".format(title_zh) if title_zh else ""),
        name_en="Core Rules {}: {}".format(chapter.num, chapter.title),
        type="core-rule",
        aliases=["核心规则 {}".format(chapter.num)],
        sources=sources,
        version={"rules": "11版 Core Rules（{}）".format(chapter.part)},
        updated="2026-07-26",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n")), slug


def generate_all(refined_dir: Path = REFINED_DIR,
                 wiki_root: Path = Path("wiki")) -> Dict[str, object]:
    from wiki_engine.core_rules_zh import parse_toc_zh

    chapters = parse_toc(refined_dir)
    by_chapter = merge_bilingual(refined_dir)
    zh_titles = {c.num: c.title for c in parse_toc_zh()}
    gen_hashes = load_gen_hashes(wiki_root)
    written = 0
    conflicts: List[str] = []
    empty: List[str] = []
    missing_en = [s.num for lst in by_chapter.values() for s in lst if not s.body_en]
    try:
        for ch in chapters:
            sections = by_chapter.get(ch.num, [])
            if not sections:
                # 一章都切不出来必须报出来：可能是排版变体没被认出，不是"这章没内容"
                empty.append("{} {}".format(ch.num, ch.title))
                continue
            page, slug = render_chapter(ch, sections, zh_titles.get(ch.num, ""))
            rel = "{}/{}.md".format(OUT_SUBDIR, slug)
            target = wiki_root / rel
            text = page.to_markdown()
            if target.exists() and gen_hashes.get(rel) is not None:
                try:
                    if text_sha256(target.read_text(encoding="utf-8")) != gen_hashes[rel]:
                        conflicts.append(rel)
                        continue
                except (OSError, UnicodeDecodeError):
                    pass
            atomic_write_text(target, text)
            gen_hashes[rel] = text_sha256(text)
            written += 1
    finally:
        save_gen_hashes(wiki_root, gen_hashes)
    extra = sorted(set(by_chapter) - {c.num for c in chapters})
    return {
        "chapters": len(chapters), "written": written,
        "sections": sum(len(v) for v in by_chapter.values()),
        "empty_chapters": empty, "conflicts": conflicts,
        "orphan_chapters": extra,        # 正文里有、目录里没有的章号
        "sections_without_en": missing_en,   # 只有中文、配不到英文原文的节
        "en_from_pdf": sum(1 for lst in by_chapter.values()
                           for s in lst if s.en_from_pdf),
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="wiki_engine.core_rules")
    ap.add_argument("--refined", default=str(REFINED_DIR))
    ap.add_argument("--wiki", default="wiki")
    args = ap.parse_args()
    rep = generate_all(Path(args.refined), Path(args.wiki))
    print("目录 {} 章 / 中英配对 {} 节 → 写 {} 页（其中 {} 节英文走 PDF 兜底）".format(
        rep["chapters"], rep["sections"], rep["written"], rep["en_from_pdf"]))
    if rep["sections_without_en"]:
        print("⚠️ {} 节只有中文、配不到英文原文：{}".format(
            len(rep["sections_without_en"]), rep["sections_without_en"]))
    if rep["empty_chapters"]:
        print("⚠️ {} 章一节都没切出来（排版变体？先核对再发布）：{}".format(
            len(rep["empty_chapters"]), "、".join(rep["empty_chapters"])))
    if rep["orphan_chapters"]:
        print("⚠️ 正文里有、目录里没有的章号：{}".format(rep["orphan_chapters"]))
    if rep["conflicts"]:
        print("⚠️ {} 页检测到人工编辑，已跳过覆盖".format(len(rep["conflicts"])))


if __name__ == "__main__":
    main()
