"""wiki_engine/keyword_index.py — 武器词条（USR）索引与反查。

回答三个问题，全部确定性、零 LLM：
  ① 这一版有哪些武器词条（正查）
  ② 每个词条是什么、官方第几节、中文叫什么、引擎建模到什么程度
  ③ **哪些武器带这个词条**（反查）——这是「像个真 wiki」的关键，
     兵牌页只能从武器看词条，反过来查不了。

三个数据源，各司其职：
  · `db/wh40k.sqlite` weapons.keywords_json —— 词条在武器上的真实分布（唯一的量化来源）
  · `data/11版40K通用技能速查表.pdf` —— 11 版官方节号 + 中文名（判定「通用 USR」的真源）
  · `engines/simulator/{parse,keywords}.py` —— 引擎建模状态（诚实披露，不吹）

**词条分三档**，混在一起列会骗读者：
  通用     —— 11 版速查表在册（ANTI/爆炸/速射…），任何单位都可能带
  十版遗留 —— 库里还大量存在、但 11 版已被取代（PISTOL → CLOSE-QUARTERS，速查表 24.07 明示）
  单位特有 —— 速查表查无此条，是某个单位数据卡上的专属词条（泡泡炮、星神之力…）

CLI：python -m wiki_engine.keyword_index [--db …] [--wiki wiki] [--pdf …]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from wiki_engine._io import atomic_write_text
from wiki_engine.models import slugify

DEFAULT_PDF = Path("data/11版40K通用技能速查表.pdf")
INDEX_REL = "indexes/keywords.md"
PAYLOAD_REL = "indexes/keywords.json"   # 机器可读镜像，web 层读它（容器不挂 data/）

# 词条后缀参数：整数（MELTA 2）、命中门槛（ANTI-INFANTRY 4+）、骰子式（RAPID FIRE D6+3）。
# 归一化 = 剥掉参数取「基础词条」，参数单独留档做档位表。
_PARAM_SUFFIX = re.compile(r"\s+(\d+\+?|D\d*(?:\+\d+)?)$", re.IGNORECASE)

# 速查表标题行：中文名 + 英文名 + 可选官方节号。正文行都超过 42 字，用长度先粗筛。
_QUICKREF_HEAD = re.compile(
    r"^[ \t]*([一-鿿][一-鿿\d]{0,9})\s*"
    r"([A-Za-z][A-Za-z0-9\-'’]*(?:[ \-][A-Za-z0-9\-'’]+)*)"
    r"(?:\s+(\d{2}\.\d{2}))?[ \t]*$")
_QUICKREF_MIN_ENTRIES = 30      # 实测 33 条；掉到 30 以下说明 PDF 换版或提取坏了，必须吼


@dataclass(frozen=True)
class QuickRefEntry:
    """11 版通用技能速查表的一条。section 可能为空——PDF 里确有条目漏印节号
    （实测「连击 SUSTAINED HITS」那行没有编号）。**不按顺序推断补全**：
    推出来的号码看着像真的，实际是我们编的。"""
    name_en: str
    name_zh: str
    section: Optional[str]


@dataclass
class KeywordStat:
    """一个基础词条的全部统计。current_* 是现役口径（与图鉴列表一致）。"""
    base: str
    variants: Set[str] = field(default_factory=set)          # 档位变体原文
    rows: int = 0                                            # (武器行, 词条) 对
    weapons: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    current_weapons: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    units: Set[str] = field(default_factory=set)
    current_units: Set[str] = field(default_factory=set)

    @property
    def weapon_names(self) -> List[str]:
        return sorted(self.weapons)

    @property
    def current_weapon_names(self) -> List[str]:
        return sorted(self.current_weapons)


# ── 速查表（11 版官方节号与中文名的真源）──────────────────────────

def parse_quickref(pdf_path: Path) -> Dict[str, QuickRefEntry]:
    """5 页速查表 → {英文名大写: QuickRefEntry}。PDF 缺失/条目过少时抛错，不静默返回空。

    静默返回空的后果很具体：判定「通用 USR」的依据没了，49 个词条会**全部**被归进
    「单位特有」——一个看起来正常、实际全错的索引页。
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            "速查表 PDF 不存在：{}（它是判定通用 USR 的真源，缺了不能生成索引）"
            .format(pdf_path))
    import fitz                                   # PyMuPDF，与 ingest.py 同源
    doc = fitz.open(str(pdf_path))
    try:
        text = "\n".join(doc[i].get_text() for i in range(doc.page_count))
    finally:
        doc.close()

    out: Dict[str, QuickRefEntry] = {}
    for line in text.splitlines():
        if len(line.strip()) > 42:               # 正文行（会换行、很长）
            continue
        m = _QUICKREF_HEAD.match(line)
        if not m:
            continue
        zh, en, section = m.group(1), m.group(2).strip().upper(), m.group(3)
        if len(en) < 3:
            continue
        out.setdefault(en, QuickRefEntry(name_en=en, name_zh=zh, section=section))
    if len(out) < _QUICKREF_MIN_ENTRIES:
        raise ValueError(
            "速查表只解析出 {} 条（预期 ≥{}）——PDF 可能换版或文本层坏了，"
            "先核对再生成索引".format(len(out), _QUICKREF_MIN_ENTRIES))
    return out


# ── 词条归一化 ─────────────────────────────────────────────────────

def normalize_keyword(token: str) -> Tuple[str, Optional[str]]:
    """'RAPID FIRE 2' → ('RAPID FIRE', '2')；'BLAST' → ('BLAST', None)。

    不归一化的后果实测过：keywords_json 里一格常是「heavy, devastating wounds」逗号串，
    加上档位变体，裸取会得到 518 个假 distinct（真值 49）。
    """
    t = " ".join(str(token).split()).upper()
    m = _PARAM_SUFFIX.search(t)
    if m:
        return t[:m.start()].strip(), m.group(1)
    return t, None


def _engine_name(base: str) -> str:
    """基础词条 → 引擎内部名（engines/simulator/parse.py 的口径）。"""
    if base.startswith("ANTI-"):
        return "anti"                              # 引擎按 anti 一族统一建模
    return base.lower().replace("-", "_").replace(" ", "_").replace("'", "")


def engine_status(base: str) -> str:
    """引擎建模状态：数值建模 / 仅标注 / 未纳入。诚实披露，不把标注型说成建模。"""
    from engines.simulator.keywords import _ANNOTATE
    from engines.simulator.parse import KNOWN_FLAG, KNOWN_PARAM

    name = _engine_name(base)
    if name in _ANNOTATE:
        return "仅标注"
    if name in KNOWN_FLAG or name in KNOWN_PARAM:
        return "数值建模"
    return "未纳入"


# ── 统计（真实分布的唯一来源）──────────────────────────────────────

def _current_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """现役口径与 web_api/codex.py 一致：官方 MFM 在册 ∪ 黑图书馆收录。"""
    cur: Set[str] = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            if pj and (json.loads(pj) or {}).get("mfm"):
                cur.add(uid)
        except (json.JSONDecodeError, TypeError):
            continue
    for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail"):
        cur.add(uid)
    return cur


def collect(db_path: Path) -> Tuple[Dict[str, KeywordStat], Dict[str, int]]:
    """扫全库武器 → {基础词条: KeywordStat}，外加一份对账数字。"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        current = _current_unit_ids(conn)
        stats: Dict[str, KeywordStat] = {}
        tally = {"weapon_rows": 0, "pairs": 0, "orphan_rows": 0}
        rows = conn.execute(
            "SELECT w.name_en, w.name_zh, w.keywords_json, w.unit_id, "
            "       u.id AS uid, u.name_zh AS unit_zh, u.name_en AS unit_en "
            "FROM weapons w LEFT JOIN units u ON u.id = w.unit_id").fetchall()
        for r in rows:
            tally["weapon_rows"] += 1
            if r["uid"] is None:
                # units 表查无此单位的武器行：不静默计入统计（会让反查列出无主武器）
                tally["orphan_rows"] += 1
                continue
            try:
                items = json.loads(r["keywords_json"] or "[]") or []
            except (json.JSONDecodeError, TypeError):
                continue
            wname = r["name_zh"] or r["name_en"] or ""
            uname = r["unit_zh"] or r["unit_en"] or r["uid"]
            for item in items:
                for part in str(item).split(","):
                    if not part.strip():
                        continue
                    base, param = normalize_keyword(part)
                    st = stats.setdefault(base, KeywordStat(base=base))
                    st.rows += 1
                    tally["pairs"] += 1
                    st.variants.add(base if param is None else "{} {}".format(base, param))
                    st.weapons[wname].add(uname)
                    st.units.add(r["uid"])
                    if r["uid"] in current:
                        st.current_weapons[wname].add(uname)
                        st.current_units.add(r["uid"])
        return stats, tally
    finally:
        conn.close()


def load_glossary(db_path: Path) -> Dict[str, str]:
    conn = sqlite3.connect(str(db_path))
    try:
        return {en: zh for en, zh in conn.execute(
            "SELECT term_en, term_zh FROM zh_keyword_glossary")}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _zh_base(base: str, variants: Set[str], gloss: Dict[str, str]) -> str:
    """基础词条的中文名：先查对照表本体，再从档位变体上剥掉尾部参数。

    对照表存的是「速射1/速射2」这种带档位的形态，基础词条「RAPID FIRE」本身常查不到。
    """
    if base in gloss:
        return gloss[base]
    for v in sorted(variants):
        zh = gloss.get(v)
        if zh:
            stripped = re.sub(r"[\dD\+]+$", "", zh).strip()
            if stripped:
                return stripped
    return ""


def _rule_page(base: str, wiki_root: Path, zh: str = "") -> Optional[str]:
    """基础词条 → 已存在的 core-rules 页相对路径；不存在返回 None（**绝不预埋红链**）。

    同名 slug 只是快捷路径。真正的判据是 crosslinks 的别名表——页名与词条名常常不一致：
    [PSYCHIC] 的页叫 `psychic-attacks`、[CLOSE-QUARTERS] 的页仍叫 `pistol`（11 版 24.07
    等效替换，但改页名等于改全部入链，见宪法 §6）。只按 slug 找会把这些判成「没有规则页」。
    最后**必须验证文件真实存在**：别名表是手维护的，指向已删页时不能吐出红链。
    """
    from wiki_engine.crosslinks import _resolve_known_alias

    candidates: List[str] = ["core-rules/{}.md".format(slugify(base))]
    for label in (base, zh):
        if label:
            got = _resolve_known_alias(label)
            if got:
                candidates.append(got)
    for rel in candidates:
        if (wiki_root / rel).exists():
            return rel
    return None


# ── 渲染 ───────────────────────────────────────────────────────────

def classify(base: str, quickref: Dict[str, QuickRefEntry]) -> str:
    """通用 / 十版遗留 / 单位特有。"""
    if base == "PISTOL":
        # 速查表 24.07 原文：「旧规则中的【手枪】技能等效替换为本技能（CLOSE-QUARTERS）」。
        # 库里 1004 行 PISTOL 是十版骨架残留，不标出来会让读者以为 11 版还有这个词条。
        return "legacy"
    key = "ANTI" if base.startswith("ANTI-") else base
    return "universal" if key in quickref else "unit-specific"


_GROUP_TITLES = [
    ("universal", "通用武器词条", "11 版《通用技能速查表》在册，任何单位都可能带。"),
    ("legacy", "十版遗留词条",
     "库里仍大量存在，但 11 版已被取代：**[PISTOL] → [CLOSE-QUARTERS]**"
     "（速查表 24.07 原文：「旧规则中的【手枪】技能等效替换为本技能」）。"
     "结构库还是十版骨架，所以这些行仍写作 PISTOL——读到时按 CLOSE-QUARTERS 理解。"),
    ("unit-specific", "单位特有词条",
     "速查表查无此条，是某个单位数据卡上的专属词条，只在该单位身上出现。"),
]


def render_index(stats: Dict[str, KeywordStat], quickref: Dict[str, QuickRefEntry],
                 gloss: Dict[str, str], wiki_root: Path) -> str:
    L: List[str] = [
        "# 武器词条（USR）索引",
        "",
        "全库武器身上出现过的每一个词条：中文名、11 版官方节号、带它的武器有多少、"
        "规则页在哪、引擎建模到什么程度，以及**反查**——哪些武器带它。",
        "",
        "> 本页是生成物（`python -m wiki_engine.keyword_index`），禁止手改。",
        "> 数量口径：**现役**＝官方 MFM 在册 ∪ 黑图书馆收录（与图鉴列表一致）；"
        "括号内为含传承/福基世界条目的全库数。",
        "> 「引擎」列说的是 `engines/simulator` 有没有把它算进伤害期望："
        "**数值建模**＝真的改数值；**仅标注**＝识别到但不改数值（会在模拟报告里披露）；"
        "**未纳入**＝引擎不认识它。",
        "",
    ]

    by_group: Dict[str, List[KeywordStat]] = defaultdict(list)
    for st in stats.values():
        by_group[classify(st.base, quickref)].append(st)

    # ── 总览表 ──
    for gid, title, blurb in _GROUP_TITLES:
        group = sorted(by_group.get(gid, []), key=lambda s: (-len(s.current_weapons), s.base))
        if not group:
            continue
        L += ["## {}（{} 条）".format(title, len(group)), "", blurb, "",
              "| 词条 | 英文 | 节号 | 档位 | 现役武器 | 现役单位 | 引擎 |",
              "|---|---|---|---|---|---|---|"]
        for st in group:
            qr = quickref.get("ANTI" if st.base.startswith("ANTI-") else st.base)
            zh = _zh_base(st.base, st.variants, gloss) or st.base
            section = (qr.section if qr and qr.section else "—")
            params = sorted({v[len(st.base):].strip() for v in st.variants
                             if v != st.base and v.startswith(st.base)})
            page = _rule_page(st.base, wiki_root, zh)
            # 词条名本身就是通往规则页的链接（有页才链，无页留纯文本，绝不预埋红链）
            label = "[[{}\\|{}]]".format(page, zh) if page else zh
            L.append("| {} | {} | {} | {} | {}（{}） | {}（{}） | {} |".format(
                label, st.base, section, "/".join(params) if params else "—",
                len(st.current_weapons), len(st.weapons),
                len(st.current_units), len(st.units),
                engine_status(st.base)))
        L.append("")

    # ── 译名差异披露 ──
    diffs = []
    for st in stats.values():
        qr = quickref.get("ANTI" if st.base.startswith("ANTI-") else st.base)
        zh = _zh_base(st.base, st.variants, gloss)
        if qr and zh and qr.name_zh != zh and not st.base.startswith("ANTI-"):
            diffs.append((st.base, zh, qr.name_zh))
    if diffs:
        L += ["## 译名差异（本 wiki 用词 ↔ 11 版速查表用词）", "",
              "两边都是汉化组译名、都不是 GW 官方中文。本 wiki 统一用左列"
              "（与兵牌页一致，取自黑图语料多数写法），右列同样收进检索别名，搜哪个都找得到。", "",
              "| 英文 | 本 wiki | 11 版速查表 |", "|---|---|---|"]
        for en, ours, theirs in sorted(diffs):
            L.append("| {} | {} | {} |".format(en, ours, theirs))
        L.append("")

    # ── 反查 ──
    L += ["## 反查：哪些武器带这个词条", "",
          "只列**现役**单位的武器，按「武器名 —— 携带单位」聚合去重；"
          "同名武器出现在多个单位时只列一行并给出单位数。", ""]
    for gid, title, _blurb in _GROUP_TITLES:
        for st in sorted(by_group.get(gid, []), key=lambda s: (-len(s.current_weapons), s.base)):
            zh = _zh_base(st.base, st.variants, gloss)
            head = "{}（{}）".format(zh, st.base) if zh else st.base
            names = st.current_weapon_names
            L += ["### {}".format(head), ""]
            if not names:
                L += ["现役单位中无武器带此词条（全库 {} 件武器带它，均为传承/福基世界条目）。"
                      .format(len(st.weapons)), ""]
                continue
            L.append("共 {} 件现役武器（全库 {} 件）。".format(len(names), len(st.weapons)))
            L.append("")
            for wname in names:
                units = sorted(st.current_weapons[wname])
                if len(units) == 1:
                    L.append("- {} —— {}".format(wname, units[0]))
                else:
                    L.append("- {} —— {} 等 {} 个单位".format(
                        wname, units[0], len(units)))
            L.append("")
    return "\n".join(L) + "\n"


def build_payload(stats: Dict[str, KeywordStat], quickref: Dict[str, QuickRefEntry],
                  gloss: Dict[str, str], wiki_root: Path) -> Dict[str, object]:
    """机器可读载荷（indexes/keywords.json）——web 层的唯一数据源。

    为什么不让 API 直接跑 collect()+parse_quickref()：容器只挂了 `wiki/`、`db/`、`opt/`、
    `local_vector_store/`，**没有挂 `data/`**（docker-compose.yml），线上根本读不到速查表 PDF。
    离线算好落进 wiki/ 是唯一能同时满足「分类依据来自真源」和「线上读得到」的做法。
    """
    items: List[Dict[str, object]] = []
    for base in sorted(stats):
        st = stats[base]
        qr = quickref.get("ANTI" if base.startswith("ANTI-") else base)
        zh = _zh_base(base, st.variants, gloss)
        items.append({
            "slug": slugify(base),
            "base": base,
            "nameZh": zh,
            "group": classify(base, quickref),
            "section": qr.section if qr else None,
            "quickrefZh": qr.name_zh if qr else None,
            "params": sorted({v[len(base):].strip() for v in st.variants
                              if v != base and v.startswith(base)}),
            "engine": engine_status(base),
            "rulePage": _rule_page(base, wiki_root, zh),
            "currentWeapons": len(st.current_weapons),
            "totalWeapons": len(st.weapons),
            "currentUnits": len(st.current_units),
            "totalUnits": len(st.units),
            "weapons": [{"name": w, "units": sorted(st.current_weapons[w])}
                        for w in st.current_weapon_names],
        })
    return {"generatedBy": "wiki_engine.keyword_index", "items": items}


def generate(db_path: Path, wiki_root: Path,
             pdf_path: Path = DEFAULT_PDF) -> Dict[str, object]:
    quickref = parse_quickref(pdf_path)
    stats, tally = collect(db_path)
    gloss = load_glossary(db_path)
    text = render_index(stats, quickref, gloss, wiki_root)
    target = wiki_root / INDEX_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, text)
    payload = build_payload(stats, quickref, gloss, wiki_root)
    # newline="\n"：机器读的产物强制 LF。Windows 本机与 Linux CI/容器都会重跑生成器，
    # 行尾随平台漂移会让同样的数据每次产生 19687 行的整文件 diff。
    # 人读的 .md 不加这个参数——wiki 下 1800+ 页既有产物都是 CRLF，统一才不制造假 diff。
    atomic_write_text(wiki_root / PAYLOAD_REL,
                      json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                      newline="\n")

    groups: Dict[str, int] = defaultdict(int)
    for st in stats.values():
        groups[classify(st.base, quickref)] += 1
    no_zh = sorted(st.base for st in stats.values()
                   if not _zh_base(st.base, st.variants, gloss))
    return {
        "path": str(target), "payload": str(wiki_root / PAYLOAD_REL),
        "keywords": len(stats), "quickref_entries": len(quickref),
        "groups": dict(groups), "pairs": tally["pairs"],
        "weapon_rows": tally["weapon_rows"], "orphan_rows": tally["orphan_rows"],
        "distinct_weapon_names": sum(len(s.weapons) for s in stats.values()),
        "current_weapon_names": sum(len(s.current_weapons) for s in stats.values()),
        "missing_zh": no_zh,
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="wiki_engine.keyword_index")
    ap.add_argument("--db", default="db/wh40k.sqlite")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--pdf", default=str(DEFAULT_PDF))
    args = ap.parse_args()
    rep = generate(Path(args.db), Path(args.wiki), Path(args.pdf))
    print("速查表条目 {}；基础词条 {}（通用 {} / 十版遗留 {} / 单位特有 {}）".format(
        rep["quickref_entries"], rep["keywords"],
        rep["groups"].get("universal", 0), rep["groups"].get("legacy", 0),
        rep["groups"].get("unit-specific", 0)))
    print("(武器行, 词条) 对 {}；去重 (词条, 武器名) 对 {}（现役 {}）".format(
        rep["pairs"], rep["distinct_weapon_names"], rep["current_weapon_names"]))
    if rep["orphan_rows"]:
        print("⚠️ {} 条武器行的 unit_id 在 units 表里查无此单位，已排除出统计".format(
            rep["orphan_rows"]))
    if rep["missing_zh"]:
        print("⚠️ {} 个词条无中文名（索引里显示英文）：{}".format(
            len(rep["missing_zh"]), "、".join(rep["missing_zh"])))
    print("写入 {}".format(rep["path"]))


if __name__ == "__main__":
    main()
