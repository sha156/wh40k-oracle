"""web_api/keyword_refs.py — 「词条 → 官方解释」的**唯一**解析层。

兵牌上有两处会出现规则词条，两处必须走同一份解析：

  ① 武器行的 USR（`[针对步兵3+，手枪，精准，连击3]`）
  ② 技能正文里内嵌的 `【致命一击】` / `[LETHAL HITS]` / `<span class="kwb">`

三个真源各管一件事，**都已存在，本模块不新造第四份**：

| 真源 | 只负责 |
|---|---|
| `wiki/indexes/keywords.json` | 词条身份：slug / 官方英文基名 / 中文名 / 分档 / 速查表节号 |
| `db/wh40k.sqlite` `zh_keyword_glossary` | 带档位的中英对照（`ANTI-INFANTRY 3+` ↔ `针对步兵3+`） |
| `wiki/core-rules/sections/*.md` | **解释正文**（GW 官方简体中文，逐字摘录、不改写、不概括） |

红线：查不到就是查不到。`resolve()` 永远返回一个 `KeywordRef`，但查不到真源时
**只有 `text`**——前端据此渲染成不可交互的纯文本。绝不为一个不认识的词条编一句解释：
本项目有 refine 造数前科（`docs/superpowers/specs/2026-07-24-refine-fabrication-fix.md`）。

## 两个不显眼的设计决定

**中文 → 英文只走对照表精确匹配，不做「剥掉中文尾巴的参数」那套。**
兵牌上的中文词条串是 `web_api/codex.py::_localize_weapon_keywords` 用同一张
`zh_keyword_glossary` 逐词翻出来的，反查回去是同一张表的逆映射（实测 81 条中文名零碰撞），
是精确可逆的。再写一套「中文串怎么剥参数」的规则等于给自己开第二个错源，
而两套规则打架时页面上看不出来。

**节正文不自己解析，一律走 `core_rules_browse.chapter_detail()`。**
核心规则页那套 `##` 切分踩过一个大坑：英文原文折叠里自带 `## ` 标题，不认
`<details>` 深度就会把折叠腰斩，而**折叠个数一个不少**（计数骗人）。那份规则已经
在 `wiki_blocks` 修好并被四处共用，这里再抄一遍 markdown 解析必然重新踩。
"""
from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from web_api.contract import KeywordRef
from wiki_engine.keyword_index import normalize_keyword

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "wh40k.sqlite"

# 解释文本上限。实测第 24 章 38 节的中文正文最长 204 字，这个阈值平时不生效；
# 留着是防某一节将来变长后把整段规则书塞进一个 tooltip。
BRIEF_MAX = 300

# 官方节号：`24.03`。中英两版共用同一套编号，它同时是配对键与身份。
# **必须锚在行尾**：官方小节名一律「名字 + 节号」结尾，而第 24 章有一个节标题被 PDF
# 版面污染成「…领袖  24.22/辅助 24.34」（侧栏的交叉引用串进了标题）。取第一个匹配会
# 把它认成 24.22 的重复，真正的 24.34 就此在按号查找里消失——156 节只剩 155 个号，
# 而页面上一切正常。取行尾那个两处都对。
_SECTION_NO = re.compile(r"(\d{2}\.\d{2})\s*$")

# 各种连字符：官方中文 PDF 直提出来的 `[CLOSE‑QUARTERS]` 用的是 U+2011 不换行连字符，
# 而库里的词条是 ASCII `-`。不归一化就会有两个词条永远配不上，且页面上看不出差别。
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


def _norm_en(text: str) -> str:
    """英文词条名归一：去方括号、统一连字符、压空白、大写。"""
    s = str(text or "").translate(_DASHES)
    s = s.strip().strip("[]").strip()
    return " ".join(s.split()).upper()


# ── 缓存 ─────────────────────────────────────────────────────────────
#
# 三份派生数据各自按自己的真源失效：对照表看 db 的 (mtime_ns, size)，节正文看
# core_rules_browse 自己的缓存（它已按 mtime 失效），词条索引看 web_api.keywords 的。
# 离线重跑生成器后不必重启 API。

_LOCK = threading.Lock()
_GLOSSARY: Optional[Tuple[int, int, Dict[str, str], Dict[str, str]]] = None
_SECTIONS: Optional[Tuple[Any, Dict[str, "_Section"], Dict[str, str]]] = None
_WARNED: set = set()


def clear_cache() -> None:
    """丢弃全部缓存。测试用：同一进程里先后换库/换 wiki 时别让上一份糊住。"""
    global _GLOSSARY, _SECTIONS
    with _LOCK:
        _GLOSSARY = None
        _SECTIONS = None
        _WARNED.clear()


def _warn_once(key: str, message: str) -> None:
    """同一类降级每进程只吼一次——但**必须吼**。

    静默降级在这里的具体后果：词条全部退成纯文本，页面看着完全正常，
    只是「没有一个词条能悬停」，没人会把它当成部署缺件去查。
    """
    with _LOCK:
        if key in _WARNED:
            return
        _WARNED.add(key)
    print("[keyword_refs] ⚠ {}".format(message), flush=True)


# ── 真源 1：中英对照表（带档位）──────────────────────────────────────

def _glossary() -> Tuple[Dict[str, str], Dict[str, str]]:
    """(en→zh, zh→en)。库缺失/无此表 → 两个空表 + 吼一声（不抛）。

    为什么不抛：对照表没了只意味着兵牌上的词条本来就是英文（`_localize_weapon_keywords`
    也是查它翻的），英文那条解析路径照样走得通——降级是真降级，不是掩盖。
    """
    global _GLOSSARY
    try:
        stat = DB_PATH.stat()
    except OSError:
        _warn_once("db-missing", "结构库缺失（{}），词条中文名与反查失效，"
                                 "兵牌词条按英文解析".format(DB_PATH.name))
        return {}, {}
    with _LOCK:
        hit = _GLOSSARY
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2], hit[3]
    en_zh: Dict[str, str] = {}
    zh_en: Dict[str, str] = {}
    conn = sqlite3.connect("file:{}?mode=ro".format(DB_PATH.as_posix()), uri=True)
    try:
        rows = conn.execute("SELECT term_en, term_zh FROM zh_keyword_glossary").fetchall()
    except sqlite3.OperationalError:
        _warn_once("gloss-missing", "结构库里没有 zh_keyword_glossary 表，"
                                    "兵牌词条按英文解析")
        rows = []
    finally:
        conn.close()
    for term_en, term_zh in rows:
        en = _norm_en(term_en)
        zh = " ".join(str(term_zh or "").split())
        if not en or not zh:
            continue
        en_zh.setdefault(en, zh)
        # 实测 81 条零碰撞；真撞了保留先到的一条并吼——静默取后者会让某个词条
        # 的中文名跟着表的物理顺序漂移
        if zh in zh_en and zh_en[zh] != en:
            _warn_once("gloss-collide-" + zh,
                       "对照表中文名撞车：{} 同时对应 {} 与 {}，取前者".format(
                           zh, zh_en[zh], en))
        else:
            zh_en[zh] = en
    with _LOCK:
        _GLOSSARY = (stat.st_mtime_ns, stat.st_size, en_zh, zh_en)
    return en_zh, zh_en


# ── 真源 2：官方中文规则正文 ─────────────────────────────────────────

@dataclass(frozen=True)
class _Section:
    """核心规则的一节（只留解析词条要用的四样）。"""

    number: str                 # 官方节号 24.03
    chapter_slug: str           # 章节页 slug 24-core-abilities
    name_en: str                # 节标题下那行 *[ANTI]* 的英文名（已归一）
    brief: str                  # 中文正文摘录（逐字，未改写）


def _inline_text(inline: Iterable[Any]) -> str:
    return "".join(str(getattr(piece, "s", "") or "") for piece in inline or [])


def _section_brief(blocks: Iterable[Any]) -> Tuple[str, str]:
    """一节的块数组 → (英文名, 中文正文摘录)。

    英文名来自紧跟标题的整行斜体（`*[ANTI]*`，契约里是单个 `em` 行内）；
    正文取折叠**之前**的段落与列表——折叠里装的是英文原文，混进来就成了中英夹杂。
    """
    name_en = ""
    parts: List[str] = []
    for block in blocks or []:
        kind = getattr(block, "t", None)
        if kind == "details":
            break                       # 折叠 = 英文原文，正文到此为止
        if kind == "p":
            inline = list(getattr(block, "inline", []) or [])
            if not name_en and len(inline) == 1 and getattr(inline[0], "t", "") == "em":
                name_en = _norm_en(_inline_text(inline))
                continue
            text = _inline_text(inline).strip()
            if text:
                parts.append(text)
        elif kind in ("ul", "ol"):
            for item in getattr(block, "items", []) or []:
                text = _inline_text(item).strip()
                if text:
                    parts.append(text)
    brief = "\n".join(parts).strip()
    if len(brief) > BRIEF_MAX:
        brief = brief[:BRIEF_MAX].rstrip() + "…"
    return name_en, brief


def _sections() -> Tuple[Dict[str, _Section], Dict[str, str]]:
    """({节号: _Section}, {英文名: 节号})。核心规则页缺失 → 两个空表 + 吼一声。"""
    global _SECTIONS
    from web_api import core_rules_browse as crb

    try:
        stamp = tuple(sorted(
            (p.name, p.stat().st_mtime_ns, p.stat().st_size)
            for p in crb.SECTIONS_DIR.iterdir()
            if p.is_file() and p.suffix == ".md"))
    except OSError:
        _warn_once("rules-missing", "核心规则页缺失（{}），词条解释与规则页链接失效，"
                                    "词条退成纯文本".format(crb.SECTIONS_DIR.name))
        return {}, {}
    with _LOCK:
        hit = _SECTIONS
        if hit is not None and hit[0] == stamp:
            return hit[1], hit[2]

    by_no: Dict[str, _Section] = {}
    by_en: Dict[str, str] = {}
    try:
        chapters = crb.list_chapters()
    except Exception as exc:                       # WikiUnavailable 及读盘异常
        _warn_once("rules-broken", "核心规则页读不出来（{}），词条退成纯文本".format(exc))
        return {}, {}
    for summary in chapters:
        try:
            chapter = crb.chapter_detail(summary.slug)
        except Exception as exc:
            _warn_once("chapter-" + summary.slug,
                       "核心规则第 {} 章读不出来（{}），该章词条无解释".format(
                           summary.number, exc))
            continue
        for section in chapter.sections:
            m = _SECTION_NO.search(section.title or "")
            if not m:
                # 每节标题都带官方节号；不带 = 切分又出问题了（折叠被腰斩过一次）。
                # 跳过而不是收下——收下会得到一条节号为空、永远配不上的假节。
                continue
            number = m.group(1)
            name_en, brief = _section_brief(section.blocks)
            by_no.setdefault(number, _Section(
                number=number, chapter_slug=chapter.slug,
                name_en=name_en, brief=brief))
            if name_en:
                by_en.setdefault(name_en, number)
    with _LOCK:
        _SECTIONS = (stamp, by_no, by_en)
    return by_no, by_en


# ── 真源 3：词条身份索引 ─────────────────────────────────────────────

def _index() -> Dict[str, Dict[str, Any]]:
    """{官方英文基名: keywords.json 条目}。载荷缺失 → 空表 + 吼一声。"""
    from web_api.keywords import KeywordPayloadError, load_items

    try:
        items = load_items()
    except KeywordPayloadError as exc:
        _warn_once("payload", "词条索引载荷不可用（{}），词条退成纯文本".format(exc))
        return {}
    return {_norm_en(it.get("base", "")): it for it in items if it.get("base")}


# ── 对外 ─────────────────────────────────────────────────────────────

def split_tokens(values: Iterable[Any]) -> List[str]:
    """武器关键词列表 → 逐条 token。库里一格常是 `heavy, devastating wounds` 逗号串。"""
    out: List[str] = []
    for value in values or []:
        for part in re.split(r"[,，]", str(value)):
            token = " ".join(part.split())
            if token:
                out.append(token)
    return out


def resolve(token: str) -> KeywordRef:
    """一个词条 token → KeywordRef。查不到真源时只有 `text`（诚实降级，不编解释）。

    token 可以是中文（`针对步兵3+`，zh 模式的兵牌）或英文（`ANTI-INFANTRY 3+`）。
    """
    text = " ".join(str(token or "").split())
    if not text:
        return KeywordRef(text="")

    _, zh_en = _glossary()
    en = zh_en.get(text) or _norm_en(text)
    base, _param = normalize_keyword(en)
    item = _index().get(_norm_en(base))
    if item is None:
        return KeywordRef(text=text)

    by_no, by_en = _sections()
    # 节号优先用速查表印的那个；速查表漏印时（实测 PISTOL / SUSTAINED HITS 两条）
    # 退回按官方英文名与核心规则章节配对——**不按顺序推断补号**
    number = item.get("section")
    if not number or number not in by_no:
        number = by_en.get(_norm_en(base))
    section = by_no.get(number) if number else None

    return KeywordRef(
        text=text,
        slug=item.get("slug") or None,
        base=item.get("base") or None,
        name_zh=item.get("nameZh") or None,
        brief=(section.brief or None) if section else None,
        section=section.number if section else None,
        rule_slug=section.chapter_slug if section else None,
        group=item.get("group") or None,
    )


def resolve_all(values: Iterable[Any]) -> List[KeywordRef]:
    """武器关键词列表（可能是逗号串）→ 逐条 KeywordRef。"""
    return [resolve(tok) for tok in split_tokens(values)]
