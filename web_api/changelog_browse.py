"""web_api/changelog_browse.py — 11 版规则变更清单只读层（图鉴 · 规则变更）。

数据源是 `wiki/changelog/`（`index.md` + `factions/<slug>.md` 28 页），由
`wiki_engine/changelog.py` 离线生成：正文照抄官方阵营包自带的「规则更新」章节，
🆕 标记读自 PDF 的**红色高亮**（官方导言写明初版之后的修订以红色标出），不是 diff 猜的。

**这一层的重点是对账。** `index.md` 的「各阵营改动一览」表是一份清单：28 行、每行写明
该包多少条改动、其中多少条是 v1.1 增量、明细页在哪。阵营页里实际有多少条 `###` 条目
是另一侧。两侧对不上就 503 并在日志点名——因为这两个数字是这个页面的**头条断言**
（"592 条官方改动"），一侧悄悄少了几条，页面照样渲染得漂漂亮亮，没人看得出来。
本仓库在核心规则那边刚吃过一次同型的亏：切分正则漏了 6 节，而探测器与被测正则共用
同一条假设，一起瞎，最后是靠中英节号集合相等这条**跨产物**对账逮出来的。

口径提醒（页面上也写了）：本清单只收官方**文字**改动。兵牌数值与规则文本的 10→11 漂移
是另一条线，落在 `db_compile/fp_errata_patches.json` 与 `fp_rules_patches.json`，
两者不要混读——所以 index 里那节口径说明也一并下发（见 `note_sections`）。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from web_api.contract import (ChangelogFactionPage, ChangelogFactionSummary,
                              ChangelogIndex, WikiBlock, WikiSection)
from web_api.wiki_blocks import (find_wikilinks, flatten_wikilinks, parse_intro,
                                 parse_sections, section_table_rows,
                                 split_frontmatter)
from web_api.wiki_browse import NotFound, WikiUnavailable

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_DIR = REPO_ROOT / "wiki" / "changelog"
INDEX_PATH = CHANGELOG_DIR / "index.md"
FACTIONS_DIR = CHANGELOG_DIR / "factions"

_MOUNT_HINT = "挂载仓库的 ./wiki 到 /app/wiki（compose 卷 wiki:ro）"
_REBUILD_HINT = "离线跑 python -m wiki_engine changelog 重建"

# index.md 的三节：一览表（清单）、通用规则更新（跨全阵营）、口径说明。
# 通用节按**前缀**认（标题带版本号 `通用规则更新 v1.0（跨全部阵营）`，版本会变）
_MANIFEST_SECTION = "各阵营改动一览"
_GENERAL_PREFIX = "通用规则更新"
_MANIFEST_COLUMNS = 5           # 阵营包 | 版本 | 改动条数 | 其中新增 | 明细
_NEW_MARK = "🆕"


def _short(path: Path) -> str:
    """给用户看的路径：仓库相对。绝对路径会把服务器目录结构吐进 HTTP 响应体。"""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


@dataclass(frozen=True)
class _Page:
    """一页变更清单的解析结果（缓存单元）。"""

    path: str
    fm: Dict[str, object]
    intro: Tuple[WikiBlock, ...]
    sections: Tuple[WikiSection, ...]
    body: str                                   # 原始正文，一览表要按原始 markdown 取链接


_CACHE: Dict[str, Tuple[int, int, _Page]] = {}
_LOCK = threading.Lock()


def clear_cache() -> None:
    """丢弃缓存。测试用：同一路径先后放两份不同 wiki 时，别让上一份糊住。"""
    with _LOCK:
        _CACHE.clear()


def _parse(path: Path) -> _Page:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WikiUnavailable("变更清单页读不出来（{}）：{}；{}".format(
            _short(path), exc, _MOUNT_HINT))
    fm, body = split_frontmatter(text)
    if not fm:
        raise WikiUnavailable("变更清单页缺 frontmatter（{}），产物可能已损坏；{}".format(
            _short(path), _MOUNT_HINT))
    return _Page(path=_short(path), fm=fm, intro=tuple(parse_intro(body)),
                 sections=tuple(parse_sections(body)), body=body)


def _read(path: Path) -> _Page:
    try:
        stat = path.stat()
    except OSError:
        raise WikiUnavailable("变更清单页缺失（{}）；{}".format(
            _short(path), _MOUNT_HINT))
    key = str(path)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
            return hit[2]
    page = _parse(path)                          # 解析放锁外
    with _LOCK:
        _CACHE[key] = (stat.st_mtime_ns, stat.st_size, page)
    return page


def _count_entries(page: _Page) -> Tuple[int, int]:
    """(条目数, 其中 🆕 数)。条目 = 各节里的 `###` 标题块。

    按**已解析的块**数，而不是回去数原始 markdown 的 `### ` 行：数出来的必须是页面上
    真正会渲染出来的那些条目，否则对账通过了、页面上还是少几条（校验器要和被校验的
    东西看同一份产物）。
    """
    total = new = 0
    for section in page.sections:
        for block in section.blocks:
            if getattr(block, "t", None) != "h" or getattr(block, "level", 0) != 3:
                continue
            total += 1
            if _NEW_MARK in block.text:
                new += 1
    return total, new


def _int_cell(raw: str, what: str, path: str) -> int:
    try:
        return int(raw.strip())
    except ValueError:
        raise WikiUnavailable("变更清单一览表的{}不是数字（{}：{!r}）；{}".format(
            what, path, raw, _REBUILD_HINT))


def _faction_path(slug: str) -> Path:
    """slug → 阵营页路径。形态先卡一道（挡目录穿越），resolve 归属再兜一次。"""
    if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        raise NotFound("变更清单页不存在（slug={}）".format(slug))
    target = (FACTIONS_DIR / (slug + ".md")).resolve()
    if not target.is_relative_to(FACTIONS_DIR.resolve()) or not target.is_file():
        raise NotFound("变更清单页不存在（slug={}）".format(slug))
    return target


@dataclass(frozen=True)
class _Row:
    """一览表一行（清单侧）。"""

    slug: Optional[str]
    name: str
    version: str
    total: int
    new_count: int
    detail: str


def _manifest_rows(index: _Page) -> List[_Row]:
    """一览表 → 行数组。表结构不对（列数变了/没有行）一律 503，不猜。"""
    raw_rows = section_table_rows(index.body, _MANIFEST_SECTION)
    if not raw_rows:
        raise WikiUnavailable(
            "变更清单 index 里找不到「{}」表（{}），产物残缺；{}".format(
                _MANIFEST_SECTION, index.path, _REBUILD_HINT))
    out: List[_Row] = []
    for cells in raw_rows:
        if len(cells) != _MANIFEST_COLUMNS:
            raise WikiUnavailable(
                "变更清单一览表列数不对（{}）：期望 {} 列、实际 {} 列（{!r}）；{}".format(
                    index.path, _MANIFEST_COLUMNS, len(cells), cells,
                    _REBUILD_HINT))
        name, version, total, new, detail = cells
        links = find_wikilinks(detail)
        slug: Optional[str] = None
        if links:
            target = links[0][0]
            slug = target.rsplit("/", 1)[-1]
            if slug.endswith(".md"):
                slug = slug[:-3]
        out.append(_Row(
            slug=slug, name=name.strip(), version=version.strip(),
            total=_int_cell(total, "改动条数", index.path),
            new_count=_int_cell(new, "其中新增", index.path),
            # 无链接行的明细列写的是原因（"首版，无更新章节"）——照实带给前端，
            # 别伪造一个空页面让人点进去看"本包 0 条改动"
            detail=flatten_wikilinks(detail).strip(),
        ))
    return out


def _reconcile(rows: List[_Row]) -> None:
    """一览表（清单侧）vs 阵营页实际条目（产物侧）逐条对账。差额 = 503 + 日志点名。

    查三件事，任一不符都吵：
      · 清单里点了名的明细页读不到 → 卷挂了一半 / 产物被删
      · 页里的条目数或 🆕 数与清单不符 → 两份产物有一份是旧的
      · 磁盘上多出清单没列的阵营页 → index 是旧的（页面头条数字就会偏小）
    """
    problems: List[str] = []
    linked: set = set()
    for row in rows:
        if row.slug is None:
            continue
        linked.add(row.slug)
        try:
            page = _read(_faction_path(row.slug))
        except NotFound:
            problems.append("{}（清单点名的明细页读不到）".format(row.slug))
            continue
        total, new = _count_entries(page)
        if total != row.total or new != row.new_count:
            problems.append("{}（清单 {}/{} 条、页里 {}/{} 条）".format(
                row.slug, row.total, row.new_count, total, new))

    if not FACTIONS_DIR.is_dir():
        problems.append("缺目录 {}".format(_short(FACTIONS_DIR)))
    else:
        on_disk = {p.stem for p in FACTIONS_DIR.glob("*.md")}
        unlisted = sorted(on_disk - linked)
        # 没链接的行（首版无更新章节 / 官方未列改动）在磁盘上照样有一页 0 条的空页，
        # 所以"清单外的页"允许恰好等于无链接行数；多出来就是 index 落后了
        blank_rows = sum(1 for r in rows if r.slug is None)
        if len(unlisted) != blank_rows:
            problems.append(
                "磁盘上有 {} 页不在清单里（{}），而清单只有 {} 行没有明细链接".format(
                    len(unlisted), "、".join(unlisted) or "无", blank_rows))

    if problems:
        msg = "变更清单对不上账：{}；{}".format("；".join(problems), _REBUILD_HINT)
        print("[changelog_browse] ⚠ {}".format(msg), flush=True)
        raise WikiUnavailable(msg)


# ── 对外 ─────────────────────────────────────────────────────────────

def changelog_index() -> ChangelogIndex:
    """变更清单首页：导语 + 通用规则更新 + 各阵营一览（已对账）。"""
    index = _read(INDEX_PATH)
    rows = _manifest_rows(index)
    _reconcile(rows)

    general: List[WikiSection] = []
    notes: List[WikiSection] = []
    for section in index.sections:
        if section.title == _MANIFEST_SECTION:
            continue                             # 表格自己渲染成 factions 列表，不重复下发
        if section.title.startswith(_GENERAL_PREFIX):
            general.append(section)
        else:
            # 兜底桶：index 里除一览表和通用更新之外的节（此刻是「数值层的 10→11 漂移」
            # 这条口径说明）。不硬编码它的标题——生成器哪天多写一节，也要出现在页面上，
            # 而不是被静默丢掉
            notes.append(section)

    return ChangelogIndex(
        intro=list(index.intro),
        general_sections=general,
        note_sections=notes,
        factions=[ChangelogFactionSummary(
            slug=r.slug, name=r.name, version=r.version, total=r.total,
            new_count=r.new_count, detail=r.detail) for r in rows],
        total=sum(r.total for r in rows),
        new_count=sum(r.new_count for r in rows),
    )


def faction_changelog(slug: str) -> ChangelogFactionPage:
    """某阵营包的官方「规则更新」全文。未知 slug → NotFound。

    条目数就地数（不回头查 index）：详情页要说的是"这一页有什么"，
    拿清单里的数字当它的门面，反倒可能在页面残缺时报出一个漂亮的假数。
    """
    page = _read(_faction_path(slug))
    total, new = _count_entries(page)
    version = ""
    ver = page.fm.get("version")
    if isinstance(ver, dict):
        version = str(ver.get("rules") or "").strip()
    return ChangelogFactionPage(
        slug=slug,
        name_zh=str(page.fm.get("name_zh") or slug).strip(),
        name_en=str(page.fm.get("name_en") or slug).strip(),
        version=version,
        total=total,
        new_count=new,
        intro=list(page.intro),
        sections=list(page.sections),
    )
