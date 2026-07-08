"""全系统共用实体解析器（spec 第七节）：中文名/英文名/社区俗名 → canonical id。

三级解析，前两级本期实现，③ 向量检索兜底留给 P3 Agent 层：
① aliases 精确命中（wiki/terms.json 中文名 + app.py 的 UNIT_ALIASES 社区俗名）
② 模糊匹配（编辑距离）
"""
from __future__ import annotations

import ast
import difflib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

FUZZY_CUTOFF = 0.6


@dataclass(frozen=True)
class ResolveResult:
    canonical_id: Optional[str]
    name_en: Optional[str]
    confidence: str  # exact / fuzzy / ambiguous / none
    candidates: List[str] = field(default_factory=list)


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


def _load_datasheet_names(db_path: Path) -> Dict[str, str]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT id, name FROM datasheets")
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()


class EntityResolver:
    def __init__(self, terms_path: Optional[Path] = None,
                 app_path: Optional[Path] = None,
                 db_path: Optional[Path] = None):
        self._zh_to_id: Dict[str, str] = {}
        self._id_to_en: Dict[str, str] = {}
        self._en_to_id: Dict[str, str] = {}
        for p in _load_term_pairs(terms_path) if terms_path else []:
            cid = p.get("canonical_id")
            if not cid:
                continue
            if p.get("en"):
                self._id_to_en.setdefault(cid, p["en"])
                self._en_to_id.setdefault(p["en"].upper(), cid)
            if p.get("zh"):
                self._zh_to_id[p["zh"]] = cid

        if db_path is not None and Path(db_path).exists():
            for cid, name in _load_datasheet_names(db_path).items():
                self._id_to_en.setdefault(cid, name)
                self._en_to_id.setdefault(name.upper(), cid)
            # 中文别名层：aliases 表的「中文名 → canonical_id」（data_refined 等来源）。
            # terms.json 的 zh 优先（先入 _zh_to_id 的不被覆盖）。
            from db_compile.aliases import load_zh_aliases

            for alias, cid in load_zh_aliases(db_path).items():
                self._zh_to_id.setdefault(alias, cid)

        self._unit_aliases = load_unit_aliases(app_path) if app_path else {}

    def resolve(self, name: str) -> ResolveResult:
        name = name.strip()

        cid = self._zh_to_id.get(name)
        if cid:
            return ResolveResult(cid, self._id_to_en.get(cid), "exact")

        cid = self._en_to_id.get(name.upper())
        if cid:
            return ResolveResult(cid, self._id_to_en.get(cid), "exact")

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
        hits = zh_hits + en_hits
        if len(hits) == 1:
            hit = hits[0]
            cid = self._zh_to_id.get(hit) or self._en_to_id.get(hit)
            return ResolveResult(cid, self._id_to_en.get(cid), "fuzzy")
        if hits:
            return ResolveResult(None, None, "ambiguous", hits)

        return ResolveResult(None, None, "none")
