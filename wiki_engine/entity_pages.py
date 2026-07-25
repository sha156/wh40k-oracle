"""wiki_engine/entity_pages.py — 分队 / 战略 / 增强三类实体页（确定性渲染，零 LLM）。

与 `from_db.py`（兵牌页）同一范式：**所有游戏数值与正文取自官方结构库**，
中文只用于**名称**。这是 2026-07-25 的用户裁决：宁可正文是英文，也要与官网一致——
仓库里确实有十版汉化译本可叠（`data_refined/` 32 个中文目录、814 个结构化战略块、
612 块能按英文名匹配上），但那是十版译本，与 11 版存在漂移（FP added_11e 200 /
removed_11e 47），叠上去会得到"读着通顺但与官网不一致"的页面。

中文名的三个来源，按优先级：
  ① 库内 `name_zh`（战略 426 / 分队规则 106 / 增强 0）
  ② `dsl_payloads/*.json`——P7 阵营 DSL 编码时按 11 版 Faction Pack 人工译的
     （战略 681 / 增强 378 / 分队规则 165），是增强中文名的**唯一**来源
  ③ 没有就留英文，不机翻

「分队容器」这个坑值得单独说：`detachments` 表存的是**分队规则名**（Command Protocols），
不是玩家说的**分队名**（Awakened Dynasty）。容器名的真源是官方 CSV 的 `detachment` 列，
入库时曾被丢掉；实测拿容器名去撞 `detachments.name_en` 命中率是 **0/323**，
而按 id 邻接反推**不可靠**（Pactbound Zealots 的规则是 Dark Pacts，邻接却指向
Combat Doctrines）。所以本模块要求库里有 `detachments.detachment_name` 列，
没有就**明确报错**而不是猜。

CLI：python -m wiki_engine entities
"""
from __future__ import annotations

import glob
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from wiki_engine._io import (atomic_write_text, load_gen_hashes,
                             save_gen_hashes, text_sha256)
from wiki_engine.crosslinks import escape_table_pipes
from wiki_engine.from_db import FACTION_DIRS
from wiki_engine.html_md import SECTION_TITLES, html_to_markdown, split_stratagem
from wiki_engine.models import WikiPage, WikiPageFrontmatter, slugify

PAYLOAD_DIR = Path("dsl_payloads")
SOURCE_NOTE = "官方结构库 db/wh40k.sqlite（Wahapedia 11 版镜像）"
# 伪容器：strat.detachment 里混着的一个非分队值，剔除（实测唯一一个）
_PSEUDO_CONTAINERS = {"Army Rules"}


# ── 中文名 ─────────────────────────────────────────────────────────

def load_payload_names(payload_dir: Path = PAYLOAD_DIR) -> Dict[str, Dict[str, str]]:
    """P7 载荷里的人工译名 → {table: {英文名大写: 中文名}}。

    载荷是 git 真源、按 11 版 FP 人工编码的，比库里零星的 name_zh 覆盖更全，
    也是 enhancements 中文名的**唯一**来源（库里 0/1058）。
    """
    out: Dict[str, Dict[str, str]] = defaultdict(dict)
    for path in sorted(glob.glob(str(Path(payload_dir) / "*.json"))):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in data.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            en, zh = entry.get("name_en"), entry.get("name_zh")
            table = entry.get("table") or ""
            if en and zh and table:
                out[table].setdefault(str(en).strip().upper(), str(zh).strip())
    return dict(out)


def _zh_name(name_en: Optional[str], db_zh: Optional[str],
             table_names: Dict[str, str]) -> Optional[str]:
    """库内 name_zh 优先，其次载荷译名；都没有返回 None（留英文，不机翻）。"""
    if db_zh and str(db_zh).strip() and str(db_zh).strip().lower() != "none":
        return str(db_zh).strip()
    if name_en:
        return table_names.get(str(name_en).strip().upper())
    return None


def _title(name_zh: Optional[str], name_en: Optional[str]) -> str:
    """页面显示名：有中文用中文，否则英文。"""
    return name_zh or (name_en or "")


# ── 渲染：战略 ─────────────────────────────────────────────────────

def render_stratagem(row: sqlite3.Row, faction_zh: str,
                     zh_names: Dict[str, Dict[str, str]]) -> Tuple[WikiPage, List[str]]:
    name_en = (row["name_en"] or "").strip()
    name_zh = _zh_name(name_en, row["name_zh"], zh_names.get("stratagems", {}))
    cp = _as_int(row["cp_cost"])
    phase = (row["phase"] or "").strip()
    container = (row["detachment"] or "").strip()
    stype = _row_get(row, "type")

    sections, order, warns = split_stratagem(row["text_zh"])
    lead_bits = ["{} CP".format(cp) if cp is not None else "CP 未知"]
    if phase:
        lead_bits.append(phase)
    if container:
        lead_bits.append("{} 分队".format(container))
    if stype:
        lead_bits.append(_short_type(stype))

    L: List[str] = ["、".join(lead_bits) + "。", ""]
    if sections:
        for title in order:
            L += ["## {}".format(title), "", sections[title], ""]
        # 四节固定顺序：缺的节保留标题写「—」，让下游能区分"没有"和"漏了"（宪法 §4.2 同理）
        for title in ("使用时机", "使用对象", "效果"):
            if title not in sections:
                L += ["## {}".format(title), "", "（源文本未提供）", ""]
                warns.append("缺段：{}".format(title))
    else:
        # 拆不出标准段：原样保留并显式标注。硬切等于改规则（宪法 §4.4）
        md, w2 = html_to_markdown(row["text_zh"])
        warns += w2
        L += ["## 原文（未识别出标准段落）", "",
              "> 本条战略的官方文本没有采用 WHEN / TARGET / EFFECT 的标准排版，"
              "此处原样保留，未做拆分。", "", md or "（源文本未提供）", ""]

    fm = WikiPageFrontmatter(
        id=str(row["id"]), name_zh=name_zh, name_en=name_en,
        faction=faction_zh, type="stratagem",
        detachment=container, cp=cp, phase=phase,
        stratagem_type=stype or "",
        sources=[{"book": SOURCE_NOTE}], updated="2026-07-25",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n")), warns


def _short_type(raw: str) -> str:
    """'Eradication Cohort – Wargear Stratagem' → 'Wargear Stratagem'（去掉分队前缀）。"""
    parts = re.split(r"\s*[–—-]\s*", str(raw))
    return parts[-1].strip() if parts else str(raw).strip()


# ── 渲染：增强 ─────────────────────────────────────────────────────

_ONLY_RE = re.compile(r"^(.{0,80}?\bonly\b\.)\s*", re.IGNORECASE)


def render_enhancement(row: sqlite3.Row, faction_zh: str,
                       zh_names: Dict[str, Dict[str, str]]) -> Tuple[WikiPage, List[str]]:
    name_en = (row["name"] or "").strip()
    name_zh = _zh_name(name_en, None, zh_names.get("enhancements", {}))
    cost = _as_int(row["cost"])
    container = (row["detachment_name"] or "").strip()

    md, warns = html_to_markdown(row["description"])
    # 「XXX model only.」这类携带限制官方写在正文开头，抽出来单列一节；抽不到就照实说没有
    limit = ""
    m = _ONLY_RE.match(md)
    if m:
        limit = m.group(1).strip()
        md = md[m.end():].strip()

    lead = ["{} 分".format(cost) if cost is not None else "分数未知"]
    if container:
        lead.append("{} 分队".format(container))
    L: List[str] = ["、".join(lead) + "。", "",
                    "## 效果", "", md or "（源文本未提供）", ""]
    if cost is not None:
        L += ["**分数**：{} 分".format(cost), ""]
    L += ["## 携带限制", "", limit or "（源文本未提供）", ""]

    fm = WikiPageFrontmatter(
        id=str(row["id"]), name_zh=name_zh, name_en=name_en,
        faction=faction_zh, type="enhancement",
        detachment=container, cost=cost,
        sources=[{"book": SOURCE_NOTE}], updated="2026-07-25",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n")), warns


# ── 渲染：分队 ─────────────────────────────────────────────────────

def render_detachment(container: str, faction_zh: str,
                      rules: Sequence[sqlite3.Row],
                      enh_links: Sequence[Tuple[str, str]],
                      strat_links: Sequence[Tuple[str, str]],
                      zh_names: Dict[str, Dict[str, str]],
                      det_id: str) -> Tuple[WikiPage, List[str]]:
    """一个**分队容器** = 一页。规则正文来自与之绑定的 detachments 行。

    rules 是列表而非单行：实测同一阵营内确有同名容器挂两条不同规则
    （混沌恶魔 Daemonic Incursion 同时挂 Warp Rifts 与 Unnatural Energies）。
    二选一会**静默丢掉一条真规则**，所以全部并列并在页面上说明。
    """
    warns: List[str] = []
    rules = list(rules)
    if not rules:
        warns.append("无绑定的分队规则行")
    elif len(rules) > 1:
        warns.append("同名容器挂了 {} 条分队规则，已全部并列".format(len(rules)))

    first_label = ""
    if rules:
        r0 = rules[0]
        first_label = _title(
            _zh_name((r0["name_en"] or "").strip(), r0["name_zh"],
                     zh_names.get("abilities", {})),
            (r0["name_en"] or "").strip())

    L: List[str] = [
        "{}的分队{}。".format(
            faction_zh or "通用",
            "，分队规则「{}」".format(first_label) if first_label else ""),
        "",
        "## 分队规则", "",
    ]
    if len(rules) > 1:
        L += ["> 结构库中本分队名下有 {} 条分队规则，以下全部列出。".format(len(rules)), ""]
    for rule in rules:
        rule_en = (rule["name_en"] or "").strip()
        rule_zh = _zh_name(rule_en, rule["name_zh"], zh_names.get("abilities", {}))
        rule_md, w = html_to_markdown(rule["rule_text"])
        warns += w
        if rule_en:
            head = _title(rule_zh, rule_en)
            L += ["### {}".format("{} {}".format(head, rule_en) if rule_zh else head), ""]
        L += [rule_md or "（源文本未提供）", ""]
    if not rules:
        L += ["（源文本未提供）", ""]

    def _links(title: str, links: Sequence[Tuple[str, str]], empty: str) -> List[str]:
        out = ["## {}".format(title), ""]
        if links:
            out += ["- [[{}\\|{}]]".format(path, label) for path, label in links]
        else:
            out.append(empty)
        return out + [""]

    L += _links("增强", enh_links, "（本分队在结构库中无增强条目）")
    L += _links("战略", strat_links, "（本分队在结构库中无战略条目）")

    fm = WikiPageFrontmatter(
        id=det_id, name_zh=None, name_en=container,
        faction=faction_zh, type="detachment", detachment=container,
        sources=[{"book": SOURCE_NOTE}], updated="2026-07-25",
    )
    fm.generate_tags()
    return WikiPage(fm=fm, body=escape_table_pipes("\n".join(L).rstrip() + "\n")), warns


# ── 小工具 ─────────────────────────────────────────────────────────

def _as_int(val: Any) -> Optional[int]:
    """'1' → 1；''/None/非数字 → None（**不塞 0**：0 CP 是真值，未知不是）。"""
    s = str(val if val is not None else "").strip()
    return int(s) if s.isdigit() else None


def _row_get(row: sqlite3.Row, key: str) -> str:
    """兼容旧库：列不存在时返回 ''，不炸。"""
    try:
        val = row[key]
    except (IndexError, KeyError):
        return ""
    return "" if val is None else str(val).strip()


def has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute("PRAGMA table_info({})".format(table)))


# ── 批量生成 ───────────────────────────────────────────────────────

def _faction_zh(fid: Optional[str]) -> Optional[str]:
    """faction id → wiki 中文目录名。空 id ＝ 通用（核心战略），返回 ""。
    认不出的 id 返回 None，调用方跳过并计入报告——瞎猜一个目录等于把条目藏起来。"""
    fid = (fid or "").strip()
    if not fid:
        return ""
    return FACTION_DIRS.get(fid)


def _alloc_slug(used: Dict[str, int], base: str) -> str:
    """同名实体的 slug 去重：第 2 个起加 -N 后缀。

    调用顺序必须确定（按 id 排序），否则重跑时哪个拿基础 slug 会互换，
    打乱全部入链（from_db 踩过，模块 6 F4）。
    """
    base = base or "unnamed"
    used[base] = used.get(base, 0) + 1
    return base if used[base] == 1 else "{}-{}".format(base, used[base])


def generate_all(db_path: Path, wiki_root: Path) -> Dict[str, Any]:
    """生成全部 分队/战略/增强 页，返回对账报告。"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    gen_hashes = load_gen_hashes(wiki_root)
    zh_names = load_payload_names()
    report: Dict[str, Any] = {
        "stratagems": {"rows": 0, "written": 0, "skipped": []},
        "enhancements": {"rows": 0, "written": 0, "skipped": []},
        "detachments": {"containers": 0, "written": 0, "no_rule": []},
        "conflicts": [], "warnings": defaultdict(list), "zh_named": defaultdict(int),
    }
    try:
        if not has_column(conn, "detachments", "detachment_name"):
            raise RuntimeError(
                "detachments 表缺 detachment_name 列——分队「容器名」的真源在官方 CSV 的 "
                "detachment 列，入库时被丢过一次。先跑 db_compile 重新入库再生成，"
                "**不要**按 id 邻接反推（实测会把 Pactbound Zealots 的规则认成 Combat Doctrines）。")

        # ① 先把所有实体的落点算出来，再渲染——分队页要链到战略/增强页，
        #    路径必须与它们实际落盘的位置一字不差
        strat_rows = conn.execute(
            "SELECT * FROM stratagems ORDER BY id").fetchall()
        enh_rows = conn.execute(
            "SELECT * FROM enhancements ORDER BY id").fetchall()
        det_rows = conn.execute(
            "SELECT * FROM detachments ORDER BY id").fetchall()

        plan_s = _plan(strat_rows, "stratagem", zh_names, report, "stratagems",
                       lambda r: r["faction"], lambda r: r["name_en"],
                       _strat_discriminator)
        plan_e = _plan(enh_rows, "enhancement", zh_names, report, "enhancements",
                       lambda r: r["faction_id"], lambda r: r["name"],
                       lambda r: (r["detachment_name"] or "").strip())

        # ② 容器清单 = 增强容器 ∪ 战略容器 − 伪容器
        # 键 = (阵营 id, 容器名)。只按名字建键会把 Infestation Swarm 的
        # 基因窃取者教派版与泰伦虫族版并成一页（实测唯一一例跨阵营同名分队）。
        containers: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row, _rel, _slug in plan_e:
            name = (row["detachment_name"] or "").strip()
            if name and name not in _PSEUDO_CONTAINERS:
                key = ((row["faction_id"] or "").strip(), name)
                containers.setdefault(key, {"faction": row["faction_id"], "enh": [], "strat": []})
                containers[key]["enh"].append((row, _rel))
        for row, _rel, _slug in plan_s:
            name = (row["detachment"] or "").strip()
            if name and name not in _PSEUDO_CONTAINERS:
                key = ((row["faction"] or "").strip(), name)
                c = containers.setdefault(key, {"faction": row["faction"], "enh": [], "strat": []})
                c["strat"].append((row, _rel))
        report["detachments"]["containers"] = len(containers)

        # 值是**列表**：同一阵营内同名容器可挂多条规则（混沌恶魔 Daemonic Incursion
        # 同时挂 Warp Rifts 与 Unnatural Energies），取第一条会静默丢掉一条真规则
        rule_by_container: Dict[Tuple[str, str], List[sqlite3.Row]] = defaultdict(list)
        for r in det_rows:
            name = (r["detachment_name"] or "").strip()
            if name:
                rule_by_container[((r["faction"] or "").strip(), name)].append(r)

        # ③ 渲染并落盘
        for row, rel, _slug in plan_s:
            fzh = _faction_zh(row["faction"])
            page, warns = render_stratagem(row, fzh or "", zh_names)
            _write(wiki_root, rel, page, gen_hashes, report)
            _collect(report, "stratagems", row["id"], warns, page.fm.name_zh)
        for row, rel, _slug in plan_e:
            fzh = _faction_zh(row["faction_id"])
            page, warns = render_enhancement(row, fzh or "", zh_names)
            _write(wiki_root, rel, page, gen_hashes, report)
            _collect(report, "enhancements", row["id"], warns, page.fm.name_zh)

        used_det: Dict[str, int] = {}
        for key in sorted(containers):
            fid, name = key
            info = containers[key]
            fzh = _faction_zh(info["faction"])
            if fzh is None:
                report["detachments"]["no_rule"].append("{}（阵营 id 未知）".format(name))
                continue
            rules = rule_by_container.get(key, [])
            if not rules:
                report["detachments"]["no_rule"].append("{}/{}".format(fid or "通用", name))
            enh_links = sorted((rel, _title(_zh_name(r["name"], None,
                                                     zh_names.get("enhancements", {})),
                                            r["name"]))
                               for r, rel in info["enh"])
            strat_links = sorted((rel, _title(_zh_name(r["name_en"], r["name_zh"],
                                                       zh_names.get("stratagems", {})),
                                              r["name_en"]))
                                 for r, rel in info["strat"])
            det_id = str(rules[0]["id"]) if rules else "container-" + slugify(name)
            page, warns = render_detachment(name, fzh or "", rules, enh_links,
                                            strat_links, zh_names, det_id)
            # slug 去重按阵营各算各的：同名容器分处两个阵营目录，不该互相加 -2 后缀
            slug = _alloc_slug(used_det, "{}/{}".format(fzh or "core", slugify(name)))
            slug = slug.split("/", 1)[1]
            base = "core-rules" if not fzh else "factions/{}".format(fzh)
            rel = "{}/detachments/{}.md".format(base, slug)
            _write(wiki_root, rel, page, gen_hashes, report)
            report["detachments"]["written"] += 1
            if warns:
                report["warnings"][name] = warns
        # 清理陈旧登记：改过 slug 规则或实体下架后，登记表里会留下指向不存在文件的键。
        # 只清本生成器自己管的三个目录——别人的页面不归我裁决。
        stale = [rel for rel in list(gen_hashes)
                 if re.search(r"/(stratagems|enhancements|detachments)/", rel)
                 and not (wiki_root / rel).exists()]
        for rel in stale:
            del gen_hashes[rel]
        report["pruned_hashes"] = len(stale)
        return report
    finally:
        conn.close()
        save_gen_hashes(wiki_root, gen_hashes)


def _plan(rows, etype, zh_names, report, bucket, faction_of, name_of,
          discriminator_of=None):
    """先算落点：返回 [(row, 相对路径, slug)]，同时把跳过的记进报告。

    重名不用 `-2` 后缀敷衍：全库 43 组同名战略，绝大多数是**核心版 vs 登舰战版**
    （COMMAND RE-ROLL 两条：Core – Battle Tactic / Boarding Actions – Epic Deed），
    落成 command-re-roll.md 与 command-re-roll-2.md 的话，读者从文件名和索引里
    根本分不出哪个是哪个。所以重名时用「分队/模式」做区分词，实在还撞才退回 -N。
    """
    # ① 先数一遍同目录下的重名，才知道谁需要区分词
    name_count: Dict[Tuple[str, str], int] = defaultdict(int)
    prepared = []
    for row in rows:
        report[bucket]["rows"] += 1
        fzh = _faction_zh(faction_of(row))
        if fzh is None:
            report[bucket]["skipped"].append(
                "{}（阵营 id {!r} 不认识）".format(row["id"], faction_of(row)))
            continue
        name = (name_of(row) or "").strip()
        if not name:
            report[bucket]["skipped"].append("{}（无名）".format(row["id"]))
            continue
        base = slugify(name)
        name_count[(fzh, base)] += 1
        prepared.append((row, fzh, base))

    used: Dict[str, int] = {}
    out = []
    for row, fzh, base in prepared:
        slug = base
        if name_count[(fzh, base)] > 1 and discriminator_of is not None:
            disc = slugify(discriminator_of(row) or "")
            if disc:
                slug = "{}-{}".format(base, disc)
        slug = _alloc_slug(used, "{}/{}".format(fzh or "core", slug)).split("/", 1)[1]
        prefix = "core-rules" if not fzh else "factions/{}".format(fzh)
        out.append((row, "{}/{}s/{}.md".format(prefix, etype, slug), slug))
    return out


def _strat_discriminator(row) -> str:
    """战略重名时的区分词：优先分队名，其次官方 type 的模式前缀（Core / Boarding Actions）。"""
    det = (row["detachment"] or "").strip()
    if det:
        return det
    raw = _row_get(row, "type")
    return re.split(r"\s*[–—-]\s*", raw)[0].strip() if raw else ""


def _write(wiki_root: Path, rel: str, page: WikiPage,
           gen_hashes: Dict[str, str], report: Dict[str, Any]) -> None:
    """写页，带人工编辑保护（内容 ≠ 上次生成登记值 ⇒ 跳过并计入 conflicts）。"""
    target = wiki_root / rel
    text = page.to_markdown()
    if target.exists():
        registered = gen_hashes.get(rel)
        if registered is not None:
            try:
                if text_sha256(target.read_text(encoding="utf-8")) != registered:
                    report["conflicts"].append(rel)
                    return
            except (OSError, UnicodeDecodeError):
                pass
    atomic_write_text(target, text)
    gen_hashes[rel] = text_sha256(text)


def _collect(report, bucket, rid, warns, name_zh) -> None:
    report[bucket]["written"] += 1
    if name_zh:
        report["zh_named"][bucket] += 1
    if warns:
        report["warnings"][str(rid)] = warns
