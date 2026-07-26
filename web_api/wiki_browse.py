"""web_api/wiki_browse.py — 分队浏览只读层（图鉴 · 分队页）。

数据源是 **`wiki/` 下的 .md 文件**，不是 `db/wh40k.sqlite`。理由有三：
那是已发布产物（同一份内容 Obsidian 里看到什么、网页上就是什么）；容器里已按
`./wiki:/app/wiki:ro` 挂好；而且它经过了 crosslinks 处理——现从库里渲一遍，
交叉链接和译名都会和 wiki 页各说各话。

失败一律吵：wiki 没挂上 → `WikiUnavailable`（路由 503），未知阵营/分队 →
`NotFound`（404）。**绝不返回空列表**——空列表在前端长得跟"这个阵营没有分队"一模一样，
是个毫不心虚的错误答案。唯一允许空的是 TL/UN 这两个真没有分队的阵营，见
`list_detachments` 里的判据。

子条目对账同理：分队页「## 增强」「## 战略」清单里列了 N 条，就必须读到 N 条；
少一条直接 503 并在日志里点名，不许悄悄少给。这些页是一次生成的整体产物，出现缺口
只可能是卷挂了一半或产物被改坏，而不是"这条战略真没了"。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from web_api.contract import (DetachmentDetail, DetachmentSummary,
                              EnhancementBrief, StratagemBrief, WikiSection)
from web_api.wiki_blocks import (list_link_targets, parse_sections,
                                 pick_sections, split_frontmatter)

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = REPO_ROOT / "wiki"

_MOUNT_HINT = "挂载仓库的 ./wiki 到 /app/wiki（compose 卷 wiki:ro）"

# 分队页三节固定顺序（wiki/CLAUDE.md §4.5）
_RULE_SECTION = "分队规则"
_ENH_SECTION = "增强"
_STRAT_SECTION = "战略"
_STRAT_SECTIONS = ("使用时机", "使用对象", "效果", "限制")
_ENH_SECTIONS = ("效果", "携带限制")


class WikiUnavailable(RuntimeError):
    """wiki 资产缺失或不完整 → HTTP 503。

    单独立一个异常而不是返回 None：调用侧一旦能拿 None 当"没有内容"用，
    "卷没挂"和"这个阵营真没有分队"就会在同一个分支里汇合，再也分不开。
    """


class NotFound(LookupError):
    """未知阵营 / 未知分队 slug → HTTP 404。"""


def _short(path: Path) -> str:
    """给用户看的路径：仓库相对。绝对路径会把服务器目录结构吐进 HTTP 响应体。"""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _faction_dirs() -> Dict[str, str]:
    """faction_id → wiki 中文目录名。

    直接复用 `wiki_engine.from_db.FACTION_DIRS`——**就是它**决定了这些目录叫什么名字。
    web_api 自己那份 `codex._FACTION_ZH` 用不得：它是给图鉴单位页显示用的另一套译名
    （NEC→死灵、AE→艾尔达），和磁盘上的目录名（太空死灵、艾达灵族）对不上，
    照着它拼路径会 8 个阵营全 404。
    """
    from wiki_engine.from_db import FACTION_DIRS
    return FACTION_DIRS


# ── 页缓存：按 (mtime_ns, size) 失效 ──────────────────────────────────
#
# 一个分队详情要读 1 + 增强 + 战略 ≈ 11 个文件，列表要读该阵营的全部分队页（最多 56 个，
# 星际战士）。每次请求重解析纯属浪费，故缓存解析结果。失效判据取 (mtime_ns, size) 而非
# "进程内只读一次"：离线重跑 wiki_engine 后不必重启 API，下一个请求自动吃到新内容。

@dataclass(frozen=True)
class _Doc:
    """一页 wiki 的解析结果。"""

    path: str                                   # 仓库相对 posix 路径
    fm: Dict[str, Any]
    sections: Tuple[WikiSection, ...]
    enh_links: Tuple[Tuple[str, str], ...]      # 仅分队页有：(wiki 相对路径, 显示名)
    strat_links: Tuple[Tuple[str, str], ...]


_PAGE_CACHE: Dict[str, Tuple[int, int, _Doc]] = {}
_DIR_CACHE: Dict[str, Tuple[int, Tuple[str, ...]]] = {}
_LOCK = threading.Lock()


def clear_cache() -> None:
    """丢弃缓存。测试用：同一路径先后放两份不同 wiki 时，别让上一份糊住。"""
    with _LOCK:
        _PAGE_CACHE.clear()
        _DIR_CACHE.clear()


def _parse_doc(path: Path) -> _Doc:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WikiUnavailable("wiki 页读不出来（{}）：{}；{}".format(
            _short(path), exc, _MOUNT_HINT))
    fm, body = split_frontmatter(text)
    if not fm:
        # 生成器写的每一页都有 frontmatter；没有 = 文件被改坏或写了一半，
        # 此时正文里的数值不能信，宁可 503 也不把半截页当成规则端上去
        raise WikiUnavailable("wiki 页缺 frontmatter（{}），产物可能已损坏；{}".format(
            _short(path), _MOUNT_HINT))
    return _Doc(
        path=_short(path),
        fm=fm,
        sections=tuple(parse_sections(body)),
        enh_links=tuple(list_link_targets(body, _ENH_SECTION)),
        strat_links=tuple(list_link_targets(body, _STRAT_SECTION)),
    )


def _read_doc(path: Path) -> _Doc:
    try:
        stat = path.stat()
    except OSError:
        raise WikiUnavailable("wiki 页缺失（{}）；{}".format(_short(path), _MOUNT_HINT))
    key = str(path)
    with _LOCK:
        hit = _PAGE_CACHE.get(key)
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2]
        doc = _parse_doc(path)
        _PAGE_CACHE[key] = (stat.st_mtime_ns, stat.st_size, doc)
        return doc


def _listdir_md(directory: Path) -> Tuple[str, ...]:
    """目录下 .md 文件名（已排序），按目录 mtime 缓存——别每次请求都重扫。"""
    try:
        stat = directory.stat()
    except OSError:
        return ()
    key = str(directory)
    with _LOCK:
        hit = _DIR_CACHE.get(key)
        if hit is not None and hit[0] == stat.st_mtime_ns:
            return hit[1]
        names = tuple(sorted(p.name for p in directory.iterdir()
                             if p.is_file() and p.suffix == ".md"))
        _DIR_CACHE[key] = (stat.st_mtime_ns, names)
        return names


# ── 定位 ─────────────────────────────────────────────────────────────

def _faction_root(faction_id: str) -> Path:
    """faction_id → `wiki/factions/<中文名>/`。未知阵营 404，wiki 不完整 503。"""
    zh = _faction_dirs().get(faction_id)
    if zh is None:
        raise NotFound("阵营不存在（faction_id={}）".format(faction_id))
    factions = WIKI_ROOT / "factions"
    if not factions.is_dir():
        raise WikiUnavailable("wiki 未挂载或不完整（缺 {}）；{}".format(
            _short(factions), _MOUNT_HINT))
    root = factions / zh
    if not root.is_dir():
        raise WikiUnavailable("wiki 中缺少阵营目录 {}，卷可能只挂了一部分；{}".format(
            _short(root), _MOUNT_HINT))
    return root


def _detachment_dir(faction_id: str) -> Optional[Path]:
    """分队目录；返回 None 表示**该阵营确实没有分队**（不是缺件）。

    泰坦军团（TL）与无阵营工事（UN）在 11 版里本就没有分队，生成器压根不建这个目录。
    但"没建"和"卷挂了一半"长得一样，所以要求阵营目录里至少还有别的内容（units 等）：
    整个阵营目录空着 = 产物残缺，走 503 而不是让前端显示"该阵营没有分队"。
    """
    root = _faction_root(faction_id)
    ddir = root / "detachments"
    if ddir.is_dir():
        return ddir
    siblings = [p.name for p in root.iterdir()]
    if not siblings:
        raise WikiUnavailable("wiki 中阵营目录 {} 是空的，产物残缺；{}".format(
            _short(root), _MOUNT_HINT))
    return None


# ── 组装 ─────────────────────────────────────────────────────────────

def _fm_str(doc: _Doc, key: str) -> Optional[str]:
    val = doc.fm.get(key)
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def _fm_int(doc: _Doc, key: str) -> Optional[int]:
    """frontmatter 整数字段。**缺字段才是 None，0 照实返回 0**。"""
    val = doc.fm.get(key)
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _rule_name(doc: _Doc) -> Optional[str]:
    """分队规则名 = 「## 分队规则」下第一个 `###` 标题（形如「指令协议 Command Protocols」）。

    不用 frontmatter 的 `detachment`——那是**容器名**（Awakened Dynasty）。也不从导语
    「分队规则「指令协议」」里抠：导语只有中文名，而 h3 中英并列，信息更全。
    没有 h3 的分队（结构库里没绑规则行）返回 None，不拿分队名冒充。
    """
    for section in doc.sections:
        if section.title != _RULE_SECTION:
            continue
        for block in section.blocks:
            if getattr(block, "t", None) == "h":
                return block.text
    return None


def _summary(doc: _Doc, slug: str) -> DetachmentSummary:
    return DetachmentSummary(
        slug=slug,
        name_en=_fm_str(doc, "name_en") or slug,
        name_zh=_fm_str(doc, "name_zh"),
        rule_name=_rule_name(doc),
        stratagem_count=len(doc.strat_links),
        enhancement_count=len(doc.enh_links),
    )


def _child_doc(rel_path: str) -> Tuple[Optional[_Doc], Optional[str]]:
    """读一个子页（增强/战略）。读不到返回 (None, 原因)，交给调用方统一对账。"""
    target = (WIKI_ROOT / rel_path).resolve()
    if not target.is_relative_to(WIKI_ROOT.resolve()):
        return None, "{}（链接指向 wiki 之外）".format(rel_path)
    if not target.is_file():
        return None, rel_path
    try:
        return _read_doc(target), None
    except WikiUnavailable as exc:
        return None, "{}（{}）".format(rel_path, exc)


def _reconcile(kind: str, owner: _Doc, links: int, missing: List[str]) -> None:
    """链接数 vs 实际读到的页数对账。差额 = 503 + 日志点名，绝不悄悄少给。"""
    if not missing:
        return
    msg = ("分队页 {} 的{}子页对不上账：清单 {} 条、实际读到 {} 条，缺 {}；{}".format(
        owner.path, kind, links, links - len(missing), "、".join(missing), _MOUNT_HINT))
    print("[wiki_browse] ⚠ {}".format(msg), flush=True)
    raise WikiUnavailable(msg)


def _enhancement(doc: _Doc, slug: str) -> EnhancementBrief:
    return EnhancementBrief(
        id=str(doc.fm.get("id") or slug),
        slug=slug,
        name_en=_fm_str(doc, "name_en") or slug,
        name_zh=_fm_str(doc, "name_zh"),
        cost=_fm_int(doc, "cost"),
        sections=pick_sections(list(doc.sections), _ENH_SECTIONS),
    )


def _stratagem(doc: _Doc, slug: str) -> StratagemBrief:
    return StratagemBrief(
        id=str(doc.fm.get("id") or slug),
        slug=slug,
        name_en=_fm_str(doc, "name_en") or slug,
        name_zh=_fm_str(doc, "name_zh"),
        cp=_fm_int(doc, "cp"),
        phase=_fm_str(doc, "phase") or "",
        stratagem_type=_fm_str(doc, "stratagem_type") or "",
        sections=pick_sections(list(doc.sections), _STRAT_SECTIONS),
    )


# ── 对外 ─────────────────────────────────────────────────────────────

def list_detachments(faction_id: str) -> List[DetachmentSummary]:
    """某阵营的分队列表，按英文名排序。未知阵营 NotFound，wiki 缺件 WikiUnavailable。"""
    ddir = _detachment_dir(faction_id)
    if ddir is None:
        return []
    out = [_summary(_read_doc(ddir / name), name[:-3])
           for name in _listdir_md(ddir)]
    out.sort(key=lambda d: (d.name_en.lower(), d.slug))
    return out


def detachment_detail(faction_id: str, slug: str) -> DetachmentDetail:
    """某分队详情，增强与战略内联返回。未知 slug NotFound。

    路由带 faction_id 是必须的：同名分队跨阵营存在（Infestation Swarm 在基因窃取者教派
    与泰伦虫族各一个，规则不同），只按 slug 找会随目录遍历顺序返回错的那个。
    """
    ddir = _detachment_dir(faction_id)
    if ddir is None:
        raise NotFound("该阵营没有分队（faction_id={}）".format(faction_id))
    # 防目录穿越：分量里不许出现分隔符与 `..`，再用 resolve 后的路径归属兜底一次
    if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        raise NotFound("分队不存在（slug={}）".format(slug))
    target = (ddir / (slug + ".md")).resolve()
    if not target.is_relative_to(ddir.resolve()) or not target.is_file():
        raise NotFound("分队不存在（faction_id={}，slug={}）".format(faction_id, slug))

    doc = _read_doc(target)

    enhancements: List[EnhancementBrief] = []
    missing: List[str] = []
    for rel, _label in doc.enh_links:
        child, why = _child_doc(rel)
        if child is None:
            missing.append(why or rel)
            continue
        enhancements.append(_enhancement(child, rel.rsplit("/", 1)[-1][:-3]))
    _reconcile("增强", doc, len(doc.enh_links), missing)

    stratagems: List[StratagemBrief] = []
    missing = []
    for rel, _label in doc.strat_links:
        child, why = _child_doc(rel)
        if child is None:
            missing.append(why or rel)
            continue
        stratagems.append(_stratagem(child, rel.rsplit("/", 1)[-1][:-3]))
    _reconcile("战略", doc, len(doc.strat_links), missing)

    base = _summary(doc, slug)
    return DetachmentDetail(
        slug=base.slug,
        name_en=base.name_en,
        name_zh=base.name_zh,
        rule_name=base.rule_name,
        stratagem_count=base.stratagem_count,
        enhancement_count=base.enhancement_count,
        faction_id=faction_id,
        faction_zh=_fm_str(doc, "faction") or _faction_dirs().get(faction_id),
        rule_sections=pick_sections(list(doc.sections), (_RULE_SECTION,)),
        enhancements=enhancements,
        stratagems=stratagems,
    )
