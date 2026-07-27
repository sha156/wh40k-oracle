"""全系统共用实体解析器（spec 第七节）：中文名/英文名/社区俗名 → canonical id。

三级解析，前两级本期实现，③ 向量检索兜底留给 P3 Agent 层：
① aliases 精确命中（wiki/terms.json 中文名 + app.py 的 UNIT_ALIASES 社区俗名）
② 模糊匹配（编辑距离）
"""
from __future__ import annotations

import ast
import difflib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FUZZY_CUTOFF = 0.6

# ⚠️ 模糊匹配的第二道判据：**绝对字符编辑距离**，与 FUZZY_CUTOFF 的相似度比例正交。
#
# 病灶（2026-07-27 实测）：`Flamestorm Drake`（一个不存在的名字）以 ratio 0.606 命中
# `Firestorm Redoubt`，resolve 报 fuzzy + canonical_id，get_entity 于是 found=True 地
# 端回另一张真实兵牌——每一层都是成功路径，界面上毫无破绽。
#
# 为什么不是「把 FUZZY_CUTOFF 调高」（1842 个样本实测，方法与数据见
# docs/superpowers/specs/2026-07-27-fuzzy-silent-mismatch-fix.md）：
#   · 两类命中的 ratio 区间**重叠**——真纠错（人类拼错）最低 0.750，造名命中最高 0.846，
#     没有能同时保住前者、挡住后者的比例阈值；
#   · 更糟的是调高 cutoff 会让情况**变坏**：滤掉竞争命中会把「多命中→ambiguous（不给 id）」
#     变成「单命中→fuzzy（给 id）」，造名被接受数 56 → 79（th 0.60 → 0.75）。
# 换成绝对编辑距离后两类分开得很干净：真纠错到原单位的距离 max=2（n=1427，中英文皆然），
# 造名到最近命中的距离 median=6 / p25=5。取 2 时真纠错 1427/1427 全保（0 落空 0 误配），
# 造名 412/415 判 none；残留 3 条（如 `KNIGHT SPINNER`→`NIGHT SPINNER` 差 1 个字母）
# 本就是该纠错的边界情形，不是「离谱命中」。
FUZZY_MAX_EDITS = 2

# ⚠️ 光有编辑距离会误伤**用户打简称**这一类——「坦克指挥官」是「黎曼鲁斯坦克指挥官」的
# 子串，距离却有 4，一刀切会把两个正主全滤掉、只留下距离 2 的「远见指挥官」，
# 于是基准 #63 从 ambiguous（三候选，正主在内）翻成 fuzzy 报 Commander Farsight——
# 比原缺陷更糟。故加一条**单向**豁免：查询串是命中名的连续子串 ⇒ 按简称放行。
# 单向是数据选的：反过来（命中名是查询串的子串）等于放行「真名 + 自造修饰词」，
# 造名被接受数 3 → 45（`DECIMUS WRAITHKNIGHT`→`Wraithknight` 之流），必须挡住。
# 三种判据在 typo(1427) / 简称(748) / 造名(415) 三类样本上的实测：
#   仅 cutoff（改动前）：真纠错单命中 490、简称误配 102、**造名给出 id 57 / 判 none 23**
#   dist≤2            ：真纠错单命中 1375、简称落空 404（#63 即此类）、造名给出 id 3
#   dist≤2 或 简称子串 ：真纠错单命中 1368（误配 0）、简称落空 61、误配 102→58、
#                       **造名给出 id 3 / 判 none 412**


def _is_abbreviation(query: str, hit: str) -> bool:
    """查询串是命中名的连续子串（大小写已由调用方统一）⇒ 视为简称，不算错配。"""
    return bool(query) and query in hit


# ⚠️ 音译名分隔号在**库内自己就不统一**：`_zh_to_id` 里 30 个键用中文间隔号「·」、
# 6 个键用半角句点「.」（含 `罗伯特.基里曼`）。用户与题面写的是通行的「·」，于是
# 「罗伯特·基里曼」在精确表里查空、只能落到 fuzzy——而 `datasheet.find_datasheet`
# 出于防错配**只信 exact**，于是数值权威路径整条查不到，Agent 判空降级经典链，
# 最终从民间译本 PDF 答出过期的 320 分（基准 #113 硬错，实测 tool_calls 只有
# `get_datasheet(name_or_id="罗伯特·基里曼")` 一步就降级了）。
#
# 这是**同一个名字的两种写法**，不是模糊匹配，所以修在归一化层而不是放宽 fuzzy 判据：
# FUZZY_MAX_EDITS 那道防线（造名给出 id 57→3）一个字节都不动。
_ZH_SEPARATORS = "·.．•‧・‥/-— \t"


def _sep_normalized(name: str) -> str:
    """抹掉音译名里的分隔号/空白，用于「同名不同写法」的精确二次命中。"""
    return "".join(ch for ch in name if ch not in _ZH_SEPARATORS).lower()

# 消歧语法：`Helbrute (WE)` / `Helbrute（WE）`——candidates 原样回填即可精确重查
_FACTION_QUALIFIED = re.compile(r"^(?P<base>.+?)\s*[（(]\s*(?P<faction>[A-Za-z0-9 _-]+)\s*[)）]$")


@dataclass(frozen=True)
class ResolveResult:
    canonical_id: Optional[str]
    name_en: Optional[str]
    confidence: str  # exact / fuzzy / ambiguous / none
    candidates: List[str] = field(default_factory=list)
    # 长得像但**差得太远**、已被 FUZZY_MAX_EDITS 挡下的名字。它们不是 candidates：
    # candidates 是「确实指向库内实体、可以原样回填重查」的候选，suggestions 只是
    # 「你要找的会不会是这个」的猜测，调用方必须原样标注为猜测，不得当作解析结果。
    suggestions: List[str] = field(default_factory=list)


def _edit_distance(a: str, b: str) -> int:
    """两个名字之间的字符改动量（替换按较长一侧计），用 difflib 的 opcodes 折算。

    与 `SequenceMatcher.ratio()` 的区别正是本判据的全部意义：ratio 是**比例**，名字越长
    越容易达标（`Flamestorm Drake`→`Firestorm Redoubt` 差 10 个字符仍有 0.606）；
    这里要的是**绝对量**——人类拼错一个名字只会差一两个字符，换成另一个名字则整词皆非。
    autojunk 必须关掉：它会把长串里出现频繁的字符当噪声跳过，使距离偏小。
    """
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(max(i2 - i1, j2 - j1)
               for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")


def load_unit_aliases(app_path: Path) -> Dict[str, str]:
    """从 app.py 的源码里取 UNIT_ALIASES 字面量，不执行整个模块（避免 streamlit 等副作用）。"""
    if not app_path.exists():
        return {}
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "UNIT_ALIASES"
                for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


def _load_term_pairs(terms_path: Path) -> List[dict]:
    if not terms_path.exists():
        return []
    try:
        data = json.loads(terms_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data.get("pairs", []) if isinstance(data, dict) else []


def _load_datasheet_rows(db_path: Path) -> List[Tuple[str, str, Optional[str]]]:
    """datasheets 的 (id, name, faction_id)——faction 用于同名跨阵营消歧。"""
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT id, name, faction_id FROM datasheets")
        return [(row[0], row[1], row[2]) for row in cur.fetchall()]
    finally:
        conn.close()


class EntityResolver:
    def __init__(self, terms_path: Optional[Path] = None,
                 app_path: Optional[Path] = None,
                 db_path: Optional[Path] = None):
        self._zh_to_id: Dict[str, str] = {}
        self._id_to_en: Dict[str, str] = {}
        self._en_to_id: Dict[str, str] = {}
        # 同名跨阵营碰撞消歧（评审 #25：4 个阵营各有 Helbrute，setdefault 静默取先入者，
        # 英文名查询会拿到错误阵营的数据表）：每个英文名记全部 cid + 各 cid 的 faction
        self._en_buckets: Dict[str, List[str]] = {}
        self._id_to_faction: Dict[str, str] = {}
        # 分隔号归一化的中文索引（见 _sep_normalized）。值为 None ⇒ 该归一键被多个不同
        # 实体共用，属于真歧义，宁可不解析也不猜。
        self._zh_norm_to_id: Dict[str, Optional[str]] = {}

        def _index_en(en_name: str, cid: str, faction: Optional[str]) -> None:
            self._id_to_en.setdefault(cid, en_name)
            key = en_name.upper()
            self._en_to_id.setdefault(key, cid)
            bucket = self._en_buckets.setdefault(key, [])
            if cid not in bucket:
                bucket.append(cid)
            if faction:
                self._id_to_faction.setdefault(cid, faction)

        for p in _load_term_pairs(terms_path) if terms_path else []:
            cid = p.get("canonical_id")
            if not cid:
                continue
            if p.get("en"):
                _index_en(p["en"], cid, p.get("faction_id"))
            if p.get("zh"):
                self._zh_to_id[p["zh"]] = cid

        if db_path is not None and Path(db_path).exists():
            for cid, name, faction in _load_datasheet_rows(db_path):
                _index_en(name, cid, faction)
            # 中文别名层：aliases 表的「中文名 → canonical_id」（data_refined 等来源）。
            # terms.json 的 zh 优先（先入 _zh_to_id 的不被覆盖）。
            from db_compile.aliases import load_zh_aliases

            for alias, cid in load_zh_aliases(db_path).items():
                self._zh_to_id.setdefault(alias, cid)

        # 归一索引在两条中文来源（terms.json 的 zh + aliases 表）都灌完之后统一建，
        # 保证它与 `_zh_to_id` 的最终内容一致；键冲突（不同实体归一后同名）记 None。
        for zh_name, zh_cid in self._zh_to_id.items():
            norm = _sep_normalized(zh_name)
            if not norm or norm == zh_name:
                continue      # 名字里本就没有分隔号 ⇒ 精确表已覆盖，不必重复建键
            if self._zh_norm_to_id.setdefault(norm, zh_cid) != zh_cid:
                self._zh_norm_to_id[norm] = None

        self._unit_aliases = load_unit_aliases(app_path) if app_path else {}

    def _qualified_candidates(self, key: str) -> List[str]:
        """碰撞桶 → `Name (FACTION)` 候选串（可原样回填 resolve 精确重查）。"""
        return [
            "{} ({})".format(self._id_to_en.get(c, key),
                             self._id_to_faction.get(c, "?"))
            for c in self._en_buckets.get(key, [])
        ]

    def _resolve_en_key(self, key: str, confidence: str) -> ResolveResult:
        """按大写英文名 key 出结果；同名跨阵营碰撞时如实报 ambiguous，绝不静默取先入者。"""
        bucket = self._en_buckets.get(key, [])
        if len(bucket) > 1:
            return ResolveResult(None, None, "ambiguous",
                                 self._qualified_candidates(key))
        cid = self._en_to_id.get(key)
        return ResolveResult(cid, self._id_to_en.get(cid), confidence)

    def resolve(self, name: str) -> ResolveResult:
        name = name.strip()

        cid = self._zh_to_id.get(name)
        if cid:
            return ResolveResult(cid, self._id_to_en.get(cid), "exact")

        # 分隔号写法差异（罗伯特·基里曼 ↔ 罗伯特.基里曼）算**同名**，判 exact：
        # 只有这样 `datasheet.find_datasheet`（只信 exact）才够得着数值权威路径。
        norm_cid = self._zh_norm_to_id.get(_sep_normalized(name))
        if norm_cid:
            return ResolveResult(norm_cid, self._id_to_en.get(norm_cid), "exact")

        # 消歧语法 `Name (FACTION)`：ambiguous 候选串原样回填即可命中唯一阵营
        m = _FACTION_QUALIFIED.match(name)
        if m:
            key = m.group("base").strip().upper()
            fac = m.group("faction").strip().upper()
            for c in self._en_buckets.get(key, []):
                if (self._id_to_faction.get(c) or "").upper() == fac:
                    return ResolveResult(c, self._id_to_en.get(c), "exact")

        if name.upper() in self._en_to_id:
            return self._resolve_en_key(name.upper(), "exact")

        alias_target = self._unit_aliases.get(name)
        if alias_target:
            resolved = self.resolve(alias_target)
            if resolved.canonical_id:
                return ResolveResult(resolved.canonical_id, resolved.name_en, "exact")

        # 中英文分开模糊匹配：en_to_id 的 key 恒为大写，name 需同样大写化才能比对
        zh_hits = difflib.get_close_matches(
            name, self._zh_to_id.keys(), n=3, cutoff=FUZZY_CUTOFF)
        en_hits = difflib.get_close_matches(
            name.upper(), self._en_to_id.keys(), n=3, cutoff=FUZZY_CUTOFF)
        near = ([(h, _edit_distance(h, name), _is_abbreviation(name, h))
                 for h in zh_hits]
                + [(h, _edit_distance(h, name.upper()),
                    _is_abbreviation(name.upper(), h)) for h in en_hits])
        # 相似但差了太多个字符、又不是简称 ⇒ 不是拼错，是**另一个名字**：宁可诚实报
        # 「没解析到」，也不端回一张不相干的兵牌（见 FUZZY_MAX_EDITS 上方的实测数据）。
        hits = [h for h, dist, is_abbr in near
                if dist <= FUZZY_MAX_EDITS or is_abbr]
        if len(hits) == 1:
            hit = hits[0]
            if hit in self._zh_to_id:
                cid = self._zh_to_id[hit]
                return ResolveResult(cid, self._id_to_en.get(cid), "fuzzy")
            return self._resolve_en_key(hit, "fuzzy")   # 模糊命中同名碰撞键同样要消歧
        if hits:
            return ResolveResult(None, None, "ambiguous", hits)

        # 被编辑距离挡下的近似名只作为**猜测**回报，canonical_id 仍是 None、confidence 仍是
        # none——调用方据此如实说「库里没有这个名字」，同时可以标注着猜测把它们告诉用户。
        return ResolveResult(None, None, "none",
                             suggestions=[h for h, _, _ in near[:3]])
