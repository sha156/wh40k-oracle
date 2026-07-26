"""web_api/core_rules_browse.py — 11 版核心规则全文只读层（图鉴 · 核心规则）。

数据源是 `wiki/core-rules/sections/<NN>-<slug>.md`（24 章 156 节），由
`wiki_engine/core_rules.py` + `core_rules_zh.py` 离线生成：正文是 **GW 官方简体中文**，
每节挂一个 `<details>` 折叠块装官方英文原文。这里只读盘 + 切块，不碰 PDF、不查库
——容器里 `data/` 根本没挂，想现算也算不出来；就算算得出，也会和已发布的 wiki 页各说各话。

失败一律吵（沿用 `wiki_browse` 的两个异常语义）：资产缺件/残缺 → `WikiUnavailable`
（503），未知章节 slug → `NotFound`（404）。**绝不返回空列表/空章节**：一份空的
「核心规则」在前端长得跟"这一版没有核心规则"一样，是毫不心虚的错误答案。

两条容易忽略的规矩：

1. **导语必须一起下发。** 分队页那边导语按设计丢弃（它是 frontmatter 的重复展示），
   但核心规则页的导语里装的是「中文由官方 PDF 文本层直提，表格与版式会有失真——判定
   规则以英文原文为准」这条披露。丢了它，页面就成了一份看着像官方定稿的中文规则书。
2. **小节名连官方节号一起原样给**（"执行行动 16.01"），同时把节号另抠一份放进
   `WikiSection.number`。原先这里写的是"不做成字段，从展示串里再正则抠一次只是给自己
   找一次错的机会"——**这个判断只在没人需要节号的时候成立**。现在有三个消费方
   （词条解释层 `keyword_refs`、词条页跳到规则正文的链接、章节页的锚点），各抠各的
   才是真正的三份规则打架。所以规则收在本模块的 `section_number()` 里，只此一份。
   抠法本身有坑：第 24 章有个节标题被 PDF 版面污染成「…领袖  24.22/辅助 24.34」，
   取**第一个** NN.NN 会把它认成 24.22 的重复，真正的 24.34 就此消失（156 节只剩
   155 个号），而两个页面都照常渲染。所以正则锚在**行尾**。
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from web_api.contract import (CoreRuleChapter, CoreRuleChapterSummary,
                              WikiBlock, WikiSection)
from web_api.wiki_blocks import parse_intro, parse_sections, split_frontmatter
from web_api.wiki_browse import NotFound, WikiUnavailable

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS_DIR = REPO_ROOT / "wiki" / "core-rules" / "sections"

_MOUNT_HINT = "挂载仓库的 ./wiki 到 /app/wiki（compose 卷 wiki:ro）"
_REBUILD_HINT = "离线跑 python -m wiki_engine core-rules 重建"

# 文件名形态：`24-core-abilities`。章号保留两位前导零——它同时是排序键，
# 转 int 再格式化回去只是多一次出错机会
_SLUG = re.compile(r"^(\d{2})-([a-z0-9-]+)$")

# frontmatter 名字里的样板前缀：`核心规则第 16 章《行动》` / `Core Rules 16: ACTIONS`。
# 前缀由章号确定性拼出，列表里 24 行全带一遍纯属噪声，故取书名号/冒号后的短名。
# **匹配不上就原样用全名**——短名靠猜不如长名难看。
_ZH_TITLE = re.compile(r"《(.+)》")
_EN_TITLE = re.compile(r"^Core Rules\s*\d+\s*[:：]\s*(.+)$")

# 官方节号，**锚在行尾**（见头注第 2 条：取第一个匹配会被被污染的标题骗掉一个号）
_SECTION_NO = re.compile(r"(\d{2}\.\d{2})\s*$")


def section_number(title: str) -> Optional[str]:
    """小节名 → 官方节号（"执行行动 16.01" → "16.01"）；没有编号返回 None。

    全仓库唯一的一份「从小节名取节号」实现。没有节号不是异常：变更清单页与分队页的
    小节名（「使用时机」）本来就没编号，此处 None 即真值。
    """
    m = _SECTION_NO.search(str(title or "").strip())
    return m.group(1) if m else None


def _short(path: Path) -> str:
    """给用户看的路径：仓库相对。绝对路径会把服务器目录结构吐进 HTTP 响应体。"""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


@dataclass(frozen=True)
class _Chapter:
    """一章的解析结果（缓存单元）。"""

    slug: str
    number: str
    name_zh: str
    name_en: str
    intro: Tuple[WikiBlock, ...]
    sections: Tuple[WikiSection, ...]


# path → (mtime_ns, size, _Chapter)。失效判据取 (mtime_ns, size) 而非"进程内只读一次"：
# 离线重跑生成器后不必重启 API，下一个请求自动吃到新内容。
_CACHE: Dict[str, Tuple[int, int, _Chapter]] = {}
_DIR_CACHE: Dict[str, Tuple[int, Tuple[str, ...]]] = {}
_LOCK = threading.Lock()


def clear_cache() -> None:
    """丢弃缓存。测试用：同一路径先后放两份不同 wiki 时，别让上一份糊住。"""
    with _LOCK:
        _CACHE.clear()
        _DIR_CACHE.clear()


def _title(raw: str, pattern: "re.Pattern[str]") -> str:
    m = pattern.search(raw.strip())
    return (m.group(1).strip() or raw.strip()) if m else raw.strip()


def _parse(path: Path, slug: str, number: str) -> _Chapter:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WikiUnavailable("核心规则页读不出来（{}）：{}；{}".format(
            _short(path), exc, _MOUNT_HINT))
    fm, body = split_frontmatter(text)
    if not fm:
        # 生成器写的每一页都有 frontmatter；没有 = 文件被改坏或写了一半，
        # 此时正文里的规则不能信，宁可 503 也不把半截规则端上去
        raise WikiUnavailable("核心规则页缺 frontmatter（{}），产物可能已损坏；{}".format(
            _short(path), _MOUNT_HINT))
    # 节号在这里一次性填进 WikiSection.number：下游（词条解释、跳链、页面锚点）
    # 谁都不许再从 title 里抠第二遍
    sections = tuple(s.model_copy(update={"number": section_number(s.title)})
                     for s in parse_sections(body))
    if not sections:
        # 一节都没切出来 = 页被截断或切分规则失效。空章节在前端就是一页空白，
        # 而"这一章本来就没有内容"在核心规则里不存在——24 章最少的一章也有 1 节
        raise WikiUnavailable("核心规则第 {} 章一节都没有（{}），产物残缺；{}".format(
            number, _short(path), _REBUILD_HINT))
    return _Chapter(
        slug=slug,
        number=number,
        name_zh=_title(str(fm.get("name_zh") or slug), _ZH_TITLE),
        name_en=_title(str(fm.get("name_en") or slug), _EN_TITLE),
        intro=tuple(parse_intro(body)),
        sections=sections,
    )


def _read(path: Path, slug: str, number: str) -> _Chapter:
    try:
        stat = path.stat()
    except OSError:
        raise WikiUnavailable("核心规则页缺失（{}）；{}".format(
            _short(path), _MOUNT_HINT))
    key = str(path)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2]
    chapter = _parse(path, slug, number)         # 解析放锁外：读盘 + 切块可能上百毫秒
    with _LOCK:
        _CACHE[key] = (stat.st_mtime_ns, stat.st_size, chapter)
    return chapter


def _slugs() -> List[Tuple[str, str]]:
    """目录里的 [(slug, 章号)]，按章号排序。目录缺失/空 → WikiUnavailable。"""
    if not SECTIONS_DIR.is_dir():
        raise WikiUnavailable("wiki 未挂载或不完整（缺 {}）；{}".format(
            _short(SECTIONS_DIR), _MOUNT_HINT))
    try:
        stat = SECTIONS_DIR.stat()
    except OSError:
        raise WikiUnavailable("核心规则目录读不出来（{}）；{}".format(
            _short(SECTIONS_DIR), _MOUNT_HINT))
    key = str(SECTIONS_DIR)
    with _LOCK:
        hit = _DIR_CACHE.get(key)
        names: Optional[Tuple[str, ...]] = hit[1] if (
            hit is not None and hit[0] == stat.st_mtime_ns) else None
    if names is None:
        names = tuple(sorted(p.stem for p in SECTIONS_DIR.iterdir()
                             if p.is_file() and p.suffix == ".md"))
        with _LOCK:
            _DIR_CACHE[key] = (stat.st_mtime_ns, names)
    out: List[Tuple[str, str]] = []
    for name in names:
        m = _SLUG.match(name)
        if m is None:
            # 目录里冒出别的 .md：跳过而不是当章节收下（收下会在列表里多一行
            # 章号为空的怪东西），但要吼一声——多半是生成器改了命名
            print("[core_rules_browse] ⚠ 忽略不合命名的核心规则页 {}".format(name),
                  flush=True)
            continue
        out.append((name, m.group(1)))
    if not out:
        raise WikiUnavailable("核心规则目录里一章都没有（{}）；{}".format(
            _short(SECTIONS_DIR), _REBUILD_HINT))
    out.sort(key=lambda pair: pair[1])
    return out


# ── 对外 ─────────────────────────────────────────────────────────────

def list_chapters() -> List[CoreRuleChapterSummary]:
    """24 章目录，按官方章号排序。"""
    return [CoreRuleChapterSummary(
        slug=ch.slug, number=ch.number, name_zh=ch.name_zh,
        name_en=ch.name_en, section_count=len(ch.sections),
    ) for ch in (_read(SECTIONS_DIR / (slug + ".md"), slug, number)
                 for slug, number in _slugs())]


def chapter_detail(slug: str) -> CoreRuleChapter:
    """某章全文（导语 + 各节，每节含官方英文原文折叠块）。未知 slug → NotFound。"""
    m = _SLUG.match(slug or "")
    if m is None:
        # slug 形态先卡一道：这同时挡掉了目录穿越（`..`、分隔符都过不了这条正则），
        # 下面的 resolve 归属检查是第二道
        raise NotFound("核心规则章节不存在（slug={}）".format(slug))
    target = (SECTIONS_DIR / (slug + ".md")).resolve()
    if not target.is_relative_to(SECTIONS_DIR.resolve()) or not target.is_file():
        raise NotFound("核心规则章节不存在（slug={}）".format(slug))
    ch = _read(target, slug, m.group(1))
    return CoreRuleChapter(
        slug=ch.slug, number=ch.number, name_zh=ch.name_zh, name_en=ch.name_en,
        section_count=len(ch.sections), intro=list(ch.intro),
        sections=list(ch.sections),
    )
