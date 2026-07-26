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

**中文侧的档位（参数）从对照表本身推，不另写一套「中文串怎么剥参数」的规则。**
原先这里写的是「中文只走对照表精确匹配」——**那只在词条串全部由
`codex.py::_localize_weapon_keywords` 逐词翻出来时成立**。它翻出来的是紧凑写法
（`速射1`），而技能正文与核心规则正文里的人写形态是 `【速射 1】`、`[速射 X]`、`速射D`，
表里一条都没有，于是 `resolve('速射 1')` 静默返回纯文本——武器行的词条能悬停、
同一个词条出现在技能正文里就不能，页面上看着只是「这条没做」。

补法是**从对照表反推**，不新造中文语法：对照表每行的英文侧过一遍
`normalize_keyword` 就知道档位是什么（`RAPID FIRE D6+3` → 参数 `D6+3`），
把这个参数从中文侧尾部削掉即得中文基名（`速射D6+3` → `速射`）。削不掉就跳过，
不猜。查表时先去掉全部空白再比（`速射 1` ≡ `速射1`），未命中才退到「中文基名 +
ASCII 档位尾巴」这条路——尾巴限定 ASCII（`0-9 D X + -`），中文尾巴一律不认，
否则 `劈砍狠`（DEAD CHOPPY，另一个独立词条）会被吃成 `劈砍`+`狠`。

**词条的「长相」与「身份」是两层，别合并。** `web_api/richtext.to_richtext` 只管
长相：把 `【…】`/`[…]` 标成 `kw` span，纯语法、不查任何真源，所以核心规则页正文里的
`[速射 1]` 一直只是**青色文字**、并不是链接（2026-07-27 复核：全仓库没有一处把 `kw`
渲染成 `<a>`）。身份判定只有本模块这一处：`kw` 里装的东西拿到这里查，查得到才交互。

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

from web_api.contract import (AbilityKwSpan, AbilitySpan, AbilityTextSpan,
                              KeywordRef)
from wiki_engine.keyword_index import normalize_keyword

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "wh40k.sqlite"

# 解释文本上限。实测第 24 章 38 节的中文正文最长 204 字，这个阈值平时不生效；
# 留着是防某一节将来变长后把整段规则书塞进一个 tooltip。
BRIEF_MAX = 300

# 节号不在这里抠：`core_rules_browse` 下发的每个小节已自带 `number`（那份实现锚在
# 行尾，绕开了「…领袖  24.22/辅助 24.34」这种被 PDF 版面污染的标题）。这里再写一份
# 正则就是第二个错源，而两份规则打架时页面上看不出差别。

# 各种连字符：官方中文 PDF 直提出来的 `[CLOSE‑QUARTERS]` 用的是 U+2011 不换行连字符，
# 而库里的词条是 ASCII `-`。不归一化就会有两个词条永远配不上，且页面上看不出差别。
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


def _norm_en(text: str) -> str:
    """英文词条名归一：去方括号、统一连字符、压空白、大写。"""
    s = str(text or "").translate(_DASHES)
    s = s.strip().strip("[]").strip()
    return " ".join(s.split()).upper()


def _norm_zh(text: str) -> str:
    """中文查表键：去方括号、统一连字符、**去掉全部空白**、大写。

    去空白是这层的关键：对照表存的是紧凑写法（`速射1`），而人写形态是
    `速射 1` / `连击 3`。大写只对 ASCII 档位有效（`速射d6` → `速射D6`），中文不受影响。
    """
    s = str(text or "").translate(_DASHES)
    s = s.strip().strip("[]【】").strip()
    return "".join(s.split()).upper()


# 中文基名后面允许跟的档位尾巴：只认 ASCII（`1` / `4+` / `D6+3` / `X`）。
# **中文尾巴一律不认**——`劈砍狠`（DEAD CHOPPY）与 `劈砍`（CLEAVE）是两个独立词条，
# 放开中文尾巴会把前者吃成后者加一个「狠」字，而页面上只是解释变成了另一条规则。
_ZH_PARAM_TAIL = re.compile(r"[0-9DX+\-]*")


# ── 缓存 ─────────────────────────────────────────────────────────────
#
# 三份派生数据各自按自己的真源失效：对照表看 db 的 (mtime_ns, size)，节正文看
# core_rules_browse 自己的缓存（它已按 mtime 失效），词条索引看 web_api.keywords 的。
# 离线重跑生成器后不必重启 API。

_LOCK = threading.Lock()
_GLOSSARY: Optional[Tuple[int, int, Dict[str, str], Dict[str, str],
                         Dict[str, str]]] = None
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

def _glossary() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """(en→zh, zh→en, zh基名→en基名)。库缺失/无此表 → 三个空表 + 吼一声（不抛）。

    为什么不抛：对照表没了只意味着兵牌上的词条本来就是英文（`_localize_weapon_keywords`
    也是查它翻的），英文那条解析路径照样走得通——降级是真降级，不是掩盖。

    后两张表的键都过 `_norm_zh`（去空白）：`速射 1` 与 `速射1` 必须是同一个键，
    否则同一个词条在武器行能悬停、在技能正文里不能。
    """
    global _GLOSSARY
    try:
        stat = DB_PATH.stat()
    except OSError:
        _warn_once("db-missing", "结构库缺失（{}），词条中文名与反查失效，"
                                 "兵牌词条按英文解析".format(DB_PATH.name))
        return {}, {}, {}
    with _LOCK:
        hit = _GLOSSARY
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2], hit[3], hit[4]
    en_zh: Dict[str, str] = {}
    zh_en: Dict[str, str] = {}
    zh_base: Dict[str, str] = {}
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
        key = _norm_zh(zh)
        # 实测 81 条零碰撞；真撞了保留先到的一条并吼——静默取后者会让某个词条
        # 的中文名跟着表的物理顺序漂移
        if key in zh_en and zh_en[key] != en:
            _warn_once("gloss-collide-" + key,
                       "对照表中文名撞车：{} 同时对应 {} 与 {}，取前者".format(
                           zh, zh_en[key], en))
        else:
            zh_en[key] = en
        _learn_zh_base(en, key, zh_base)
    with _LOCK:
        _GLOSSARY = (stat.st_mtime_ns, stat.st_size, en_zh, zh_en, zh_base)
    return en_zh, zh_en, zh_base


def _learn_zh_base(en: str, zh_key: str, out: Dict[str, str]) -> None:
    """从对照表的一行学出「中文基名 → 英文基名」。学不出来就不学，**不猜**。

    档位是什么由英文侧的 `normalize_keyword` 说了算（全仓库唯一一份词条参数语法），
    这里只负责把同一个档位串从中文侧的尾巴上削掉：`RAPID FIRE D6+3` / `速射D6+3`
    → 参数 `D6+3` → 中文基名 `速射`。中文侧尾巴对不上（译名把档位挪了位置、或
    干脆没写档位）时跳过——硬按「剥掉尾部数字」去猜，就是又造了一套中文参数语法。
    """
    base_en, param = normalize_keyword(en)
    if param is None:
        base_zh = zh_key
    else:
        tail = _norm_zh(param)
        if not tail or not zh_key.endswith(tail):
            return
        base_zh = zh_key[:-len(tail)]
    if not base_zh:
        return
    prior = out.get(base_zh)
    if prior is not None and prior != base_en:
        _warn_once("zhbase-collide-" + base_zh,
                   "中文基名撞车：{} 同时指向 {} 与 {}，取前者".format(
                       base_zh, prior, base_en))
        return
    out[base_zh] = base_en


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
            number = section.number
            if not number:
                # 每节标题都带官方节号；不带 = 切分又出问题了（折叠被腰斩过一次）。
                # 跳过而不是收下——收下会得到一条节号为空、永远配不上的假节。
                continue
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


def _section_for(item: Dict[str, Any]) -> Optional[_Section]:
    """词条索引条目 → 它在核心规则里的那一节（查不到返回 None）。

    节号优先用速查表印的那个；速查表漏印时（实测 PISTOL / SUSTAINED HITS 两条）退回
    按官方英文名与核心规则章节配对——**不按顺序推断补号**。速查表印了号、但那一节
    我们并没有正文时（`number not in by_no`）同样走英文名兜底，否则会给出一个
    点进去什么都没有的链接。
    """
    by_no, by_en = _sections()
    base = _norm_en(item.get("base", ""))
    number = item.get("section")
    if not number or number not in by_no:
        number = by_en.get(base)
    return by_no.get(number) if number else None


def rule_link(base: str) -> Tuple[Optional[str], Optional[str]]:
    """官方英文基名 → (官方节号, 核心规则章节页 slug)。查不到 → (None, None)。

    给词条索引页用（它只有英文基名，不需要中英对照表那一步）。成对返回：
    只有节号而没有章节页的链接无处可去，宁可两个都不给。
    """
    item = _index().get(_norm_en(base))
    section = _section_for(item) if item else None
    return (section.number, section.chapter_slug) if section else (None, None)


def _base_en(text: str) -> str:
    """任意写法的词条 token → 官方英文基名（查不到时退回英文归一化结果）。

    三条路依次试，**先精确后推导**：
      ① 对照表整条命中（`针对步兵3+`、`速射 1` ≡ `速射1`）——最可信，优先
      ② 中文基名 + ASCII 档位尾巴（`速射 X`、`速射D`、`连击 3`、光秃秃的 `速射`）
      ③ 英文侧（`ANTI-INFANTRY 3+`、`RAPID FIRE D6+`）

    ② 取**最长**匹配的中文基名：短基名是长基名的前缀时（本库暂无，但译名会变）
    取短的会把另一个词条的后半截当成档位。
    """
    _, zh_en, zh_base = _glossary()
    key = _norm_zh(text)
    hit = zh_en.get(key)
    if hit is None and zh_base:
        for cand in sorted(zh_base, key=len, reverse=True):
            if not key.startswith(cand):
                continue
            if _ZH_PARAM_TAIL.fullmatch(key[len(cand):]) is None:
                continue                       # 尾巴不是档位（`劈砍狠` 那种）
            return zh_base[cand]
    base, _param = normalize_keyword(hit or _norm_en(text))
    return base


def resolve(token: str) -> KeywordRef:
    """一个词条 token → KeywordRef。查不到真源时只有 `text`（诚实降级，不编解释）。

    token 可以是中文（`针对步兵3+` / `【致命一击】` / `[速射 1]`，zh 模式的兵牌与
    技能正文）或英文（`ANTI-INFANTRY 3+` / `[LETHAL HITS]`）。
    """
    text = " ".join(str(token or "").split())
    if not text:
        return KeywordRef(text="")

    item = _index().get(_norm_en(_base_en(text)))
    if item is None:
        return KeywordRef(text=text)

    section = _section_for(item)
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


# ── 技能正文里内嵌的词条 ─────────────────────────────────────────────
#
# 官方源里同一件事有三种写法，三种都要认：
#   ① 黑图中文层：`【致命一击】`
#   ② 英文 abilities 表：`[LETHAL HITS]`（实测 346 行 / 48 个不同串）
#   ③ 英文 abilities 表：`<span class="kwb">VEHICLE</span>`（实测 1202 行 / 362 个串）
#
# ③ 的 span 里装的**绝大多数是阵营/单位关键词**（VEHICLE、ASTARTES、CHARACTER），
# 不是武器词条。它们查不到真源、按规矩退成纯文本——所以这里不需要事先分辨"这个 span
# 是不是 USR"，判据始终只有一条：**能不能在词条真源里查到**。
#
# ③ 的标签要在 HTML 被剥掉**之前**换成哨兵，否则剥完只剩裸词、位置就找不回来了。
# 哨兵用 U+0000/U+0001：正文里不可能出现，且能穿过 `html.unescape` 与空白压缩。
KW_OPEN = "\x00"
KW_CLOSE = "\x01"

# 三种写法合成一条正则，一次扫描：合成不是为了省事，而是因为分三遍扫要处理
# "上一遍已经切走了一段"的偏移，两套偏移必然有一处算错。
_MARKED = re.compile(
    "{}(?P<span>[^{}]*){}".format(KW_OPEN, KW_CLOSE, KW_CLOSE)
    + r"|【(?P<zh>[^】]+)】"
    + r"|\[(?P<en>[^\[\]]+)\]"
)

# ② 的候选还要过一道形态闸：英文 abilities 正文里同样有 `[1]` 这类脚注、
# 以及长句被方括号括起来的情形。限成「不含句号/逗号且不太长」——真词条最长的
# `ANTI-EPIC HERO 2+` 也才 17 字符。**这只是省一次查表，不是判据**：
# 判据永远是下面 resolve() 查不查得到。
_TOKEN_SANE = re.compile(r"^[^。，,.;；:：!！?？]{1,40}$")


def strip_markers(text: str) -> str:
    """去掉 kwb 哨兵，还原成给人看的正文。"""
    return str(text or "").replace(KW_OPEN, "").replace(KW_CLOSE, "")


def ability_spans(text: str) -> List[AbilitySpan]:
    """带标记的技能正文 → 段序列（纯文本段 / 可查解释的词条段）。

    词条段的显示串**逐字保留**原样（`【致命一击】` 连方头括号一起，kwb 哨兵去掉），
    把所有段的显示串接起来必须等于 `strip_markers(text)`——这条在测试里是硬断言：
    切段切丢了字，页面上只是少了半句话，没有任何报错。

    查不到真源的候选**合并回纯文本**，不留一个空壳词条段：给了段就等于说"这是个
    规则词条"，而 kwb 里装的多半是 VEHICLE / ASTARTES 这类阵营关键词。
    """
    raw = str(text or "")
    out: List[AbilitySpan] = []
    pos = 0

    def _plain(chunk: str) -> None:
        if not chunk:
            return
        last = out[-1] if out else None
        if isinstance(last, AbilityTextSpan):
            out[-1] = AbilityTextSpan(s=last.s + chunk)
        else:
            out.append(AbilityTextSpan(s=chunk))

    for m in _MARKED.finditer(raw):
        _plain(strip_markers(raw[pos:m.start()]))
        shown = strip_markers(m.group(0))
        inner = m.group("span") or m.group("zh") or m.group("en") or ""
        ref = resolve(shown) if _TOKEN_SANE.match(inner.strip()) else None
        if ref is not None and ref.slug:
            out.append(AbilityKwSpan(kw=ref))
        else:
            _plain(shown)
        pos = m.end()
    _plain(strip_markers(raw[pos:]))
    return out
