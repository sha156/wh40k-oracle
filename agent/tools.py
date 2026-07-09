"""agent/tools.py — L5 Agent 工具箱（spec 第七节，12 个工具）。

已具备能力接真实实现（只读调用 wiki_engine / db_compile / app.py 的既有检索链，
不修改这些模块）；未建模能力（模拟/判定/验表/归档写入）诚实打桩，明确注明计划期数，
严禁伪造结果。
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from db_compile.calc_points import calc_points as _calc_points_impl
from db_compile.entity_resolver import EntityResolver, load_unit_aliases
from wiki_engine.models import WikiPage, slugify
from wiki_engine.operations.query_op import find_entity, load_index

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = REPO_ROOT / "wiki"
CORE_RULES_DIR = WIKI_ROOT / "core-rules"
TERMS_PATH = WIKI_ROOT / "terms.json"
APP_PATH = REPO_ROOT / "app.py"
DB_PATH = REPO_ROOT / "db" / "wh40k.sqlite"

# entity_resolver 单例缓存（懒加载，避免每次工具调用都重新解析 terms.json/app.py）。
_default_resolver: Optional[EntityResolver] = None


def _get_default_resolver() -> EntityResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = EntityResolver(
            terms_path=TERMS_PATH, app_path=APP_PATH, db_path=DB_PATH,
        )
    return _default_resolver


def _import_app():
    """懒加载 app.py 作为模块（只读调用其函数，绝不修改/替换其内容）。"""
    return importlib.import_module("app")


# ── ①③⑪ 查询类：wiki_engine 只读封装 ──────────────────────────────

def search_wiki(query: str, wiki_root: Optional[Path] = None) -> Dict[str, Any]:
    """LLM Wiki Query：先查 index.md 定位，再全文检索（wiki_engine.operations.query_op）。"""
    wiki_root = wiki_root or WIKI_ROOT
    index = load_index(wiki_root)
    if not index:
        return {"found": False, "page": None, "results": [],
                "note": "wiki/index.md 不存在或为空"}

    page = find_entity(query, index, wiki_root)
    if page is not None:
        return {"found": True, "page": page, "results": []}

    from wiki_engine.operations.query_op import search_entities
    results = search_entities(query, index)
    return {"found": len(results) > 0, "page": None, "results": results[:10]}


def entity_resolver(name: str, resolver: Optional[EntityResolver] = None) -> Dict[str, Any]:
    """中文名/英文名/社区俗名 → canonical id（db_compile.entity_resolver）。"""
    r = resolver or _get_default_resolver()
    result = r.resolve(name)
    return {
        "canonical_id": result.canonical_id,
        "name_en": result.name_en,
        "confidence": result.confidence,
        "candidates": result.candidates,
    }


def get_entity(
    name_or_id: str,
    wiki_root: Optional[Path] = None,
    resolver: Optional[EntityResolver] = None,
    app_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """读实体页；先直接查 wiki，未命中则走「社区俗名 → 规则书译名」自动实体解析后重试。

    wiki/index.md 目前只索引中文名（title_en 恒为 None，P1 既有限制，不在本迭代改动），
    所以别名解析优先用 app.py 的 UNIT_ALIASES（俗名 → 规则书中文名）直接重试 wiki 查找；
    entity_resolver 的 canonical_id/name_en 结果仍一并返回供上层引用/反问歧义候选。
    """
    wiki_root = wiki_root or WIKI_ROOT
    app_path = app_path or APP_PATH
    index = load_index(wiki_root)
    page = find_entity(name_or_id, index, wiki_root)
    if page is not None:
        return {"found": True, "page": page, "resolved_via": None}

    alias_target = load_unit_aliases(app_path).get(name_or_id)
    if alias_target:
        page = find_entity(alias_target, index, wiki_root)
        if page is not None:
            return {"found": True, "page": page,
                    "resolved_via": {"alias_target": alias_target}}

    resolved = entity_resolver(name_or_id, resolver=resolver)
    if resolved["name_en"]:
        page = find_entity(resolved["name_en"], index, wiki_root)
        if page is not None:
            return {"found": True, "page": page, "resolved_via": resolved}

    note = "未找到实体页（可能未编译或译名未收录）"
    if resolved["confidence"] == "ambiguous":
        note = "译名有多个候选，需向用户反问确认：" + "、".join(resolved["candidates"])
    return {"found": False, "page": None, "resolved_via": resolved, "note": note}


def get_keyword_definition(
    keyword: str, core_rules_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """USR/核心概念定义：读 wiki/core-rules/ 术语页（纯代码匹配，不依赖 LLM）。"""
    core_rules_dir = core_rules_dir or CORE_RULES_DIR
    if not core_rules_dir.exists():
        return {"found": False, "page": None, "note": "core-rules 目录不存在"}

    keyword_norm = keyword.strip().lower()

    slug = slugify(keyword)
    candidate = core_rules_dir / f"{slug}.md"
    if candidate.exists():
        page = WikiPage.from_markdown(candidate.read_text(encoding="utf-8"))
        if page is not None:
            return {"found": True, "page": page}

    for md_path in sorted(core_rules_dir.glob("*.md")):
        page = WikiPage.from_markdown(md_path.read_text(encoding="utf-8"))
        if page is None:
            continue
        names = [page.fm.name_zh, page.fm.name_en, *page.fm.aliases]
        if any(n and n.strip().lower() == keyword_norm for n in names):
            return {"found": True, "page": page}

    return {"found": False, "page": None, "note": "未找到该关键词的术语页"}


# ── ⑧ 数据类：db_compile 只读封装 ─────────────────────────────────

def calc_points(unit_list: List[str], db_path: Optional[Path] = None) -> Dict[str, Any]:
    """精确算分（SQLite，db_compile.calc_points）。P2 阶段点数 CSV 未导入时
    诚实报告缺失原因，不编造数值。"""
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"found": False, "units": [], "note": "wh40k.sqlite 不存在，需先跑 db_compile"}

    results = _calc_points_impl(db_path, unit_list)
    return {
        "found": True,
        "units": [
            {"unit_id": r.unit_id, "name_en": r.name_en, "points": r.points, "note": r.note}
            for r in results
        ],
    }


def get_datasheet(
    name_or_id: str,
    db_path: Optional[Path] = None,
    resolver: Optional[EntityResolver] = None,
) -> Dict[str, Any]:
    """英文属性块查表：单位名/id → M/T/Sv/W + 武器 A/S/AP/D + 点数（db_compile.datasheet）。

    分层评测证明数值/属性题在 PDF 里检索会被译名/拍扁坑；此工具直接查 L3 结构库拿干净真值，
    是数值类问题的首选路径。英文为权威真值，中文名可缺。查不到诚实报缺，绝不编造。
    """
    from dataclasses import asdict

    from db_compile.datasheet import find_datasheet

    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"found": False, "datasheet": None,
                "note": "wh40k.sqlite 不存在，需先跑 db_compile build"}

    ds = find_datasheet(db_path, name_or_id,
                        resolver=resolver or _get_default_resolver())
    if ds is None:
        return {"found": False, "datasheet": None, "note": "库中未找到该单位"}

    out: Dict[str, Any] = {"found": True, "datasheet": asdict(ds)}
    # 叠加黑图书馆中文原生 datasheet（属性/能力/武器）——英文仍是权威真值，
    # 中文层供作答时用母语呈现能力/武器描述。表不存在或无此单位时静默跳过。
    try:
        from db_compile.blacklibrary import load_zh_detail
        from db_compile.datasheet import diff_core_stats
        zh = load_zh_detail(db_path, ds.unit_id)
        if zh:
            out["datasheet_zh"] = zh
            # 两源数值不一致时显式标注，防止一次回答内部自相矛盾——官方英文块为准。
            conflicts = diff_core_stats(ds, zh)
            if conflicts:
                out["stat_conflicts"] = conflicts
                out["note"] = ("黑图书馆中文层与官方源在部分属性上不一致，"
                               "数值以官方英文属性块(datasheet)为准。")
    except Exception:
        pass
    return out


# ── ⑩ 兜底：只读包装 app.py 现有混合检索（绝不修改 app.py）──────────

def rag_search(query: str, app_module: Optional[Any] = None) -> Dict[str, Any]:
    """现有混合检索（兜底）。只读调用 app.py 的 load_resources/build_bm25/hybrid_retrieve，
    不修改 app.py 本身。"""
    try:
        app = app_module if app_module is not None else _import_app()
        embeddings, vectorstore, reranker, reranker_warning = app.load_resources()
        if vectorstore is None:
            return {"found": False, "passages": [],
                    "note": "知识库未构建（local_vector_store 为空），请先跑 ingest.py"}

        bm25_retriever = app.build_bm25(vectorstore)
        passages = app.hybrid_retrieve(
            query=query,
            vectorstore=vectorstore,
            bm25_retriever=bm25_retriever,
            reranker=reranker,
        )
        return {
            "found": bool(passages),
            "passages": passages,
            "note": None if passages else "未检索到相关段落",
        }
    except Exception as exc:
        return {"found": False, "passages": [], "note": f"rag_search 异常: {exc}"}


# ── 未建模能力：诚实打桩，严禁伪造结果 ────────────────────────────

def _not_modeled(tool: str, note: str) -> Dict[str, Any]:
    return {"ok": False, "modeled": False, "tool": tool, "note": note}


def judge_fight_order(ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _not_modeled("judge_fight_order", "战斗顺序判定器未建模，计划于 P5 实现")


def simulate_combat(
    attacker: str, defender: str, options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _not_modeled("simulate_combat", "蒙特卡洛模拟引擎未建模，计划于 P4 实现")


def validate_roster(roster_text: str) -> Dict[str, Any]:
    return _not_modeled("validate_roster", "军表合法性验证未建模，计划于 P6 实现")


def critique_roster(roster_text: str) -> Dict[str, Any]:
    return _not_modeled("critique_roster", "军表点评（验表+模拟）未建模，计划于 P6 实现")


def archive_answer(title: str, content: str) -> Dict[str, Any]:
    return _not_modeled(
        "archive_answer",
        "本迭代未接线：wiki_engine.operations.archive_op.archive_judgment 已具备实现，"
        "但会写入 wiki/faq/，超出本次安全增量约束（不改 wiki/），留待人工审后接线",
    )


# ── 工具注册表（供 agent/loop.py 的 function-calling 循环调用）──────

TOOL_SPECS: List[Dict[str, str]] = [
    {"name": "search_wiki", "description": "LLM Wiki Query：先查 index.md 定位，再全文检索"},
    {"name": "get_entity", "description": "读实体页（自动实体解析）"},
    {"name": "get_keyword_definition", "description": "USR/核心概念定义"},
    {"name": "judge_fight_order", "description": "战斗顺序判定器（未建模，P5）"},
    {"name": "simulate_combat", "description": "蒙特卡洛模拟引擎（未建模，P4）"},
    {"name": "validate_roster", "description": "验表（未建模，P6）"},
    {"name": "critique_roster", "description": "验表+模拟点评（未建模，P6）"},
    {"name": "calc_points", "description": "精确算分"},
    {"name": "get_datasheet", "description": "英文属性块查表：M/T/Sv/W + 武器 A/S/AP/D（数值题首选）"},
    {"name": "archive_answer", "description": "把判定/结论存为 wiki 页（本迭代未接线）"},
    {"name": "rag_search", "description": "现有混合检索（兜底）"},
    {"name": "entity_resolver", "description": "中文名/英文名/社区俗名 → canonical id"},
]

TOOLS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "search_wiki": search_wiki,
    "get_entity": get_entity,
    "get_keyword_definition": get_keyword_definition,
    "judge_fight_order": judge_fight_order,
    "simulate_combat": simulate_combat,
    "validate_roster": validate_roster,
    "critique_roster": critique_roster,
    "calc_points": calc_points,
    "get_datasheet": get_datasheet,
    "archive_answer": archive_answer,
    "rag_search": rag_search,
    "entity_resolver": entity_resolver,
}

assert set(TOOLS) == {spec["name"] for spec in TOOL_SPECS}
