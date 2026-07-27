"""agent/tools.py — L5 Agent 工具箱（spec 第七节，12 个工具）。

已具备能力接真实实现（只读调用 wiki_engine / db_compile / app.py 的既有检索链，
不修改这些模块）；未建模能力（模拟/判定/验表/归档写入）诚实打桩，明确注明计划期数，
严禁伪造结果。
"""
from __future__ import annotations

import importlib
import threading
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
# 双检锁（评审 M#7）：qa_bench 6 线程并发首调时避免重复构造。
_default_resolver: Optional[EntityResolver] = None
_default_resolver_lock = threading.Lock()


def _get_default_resolver() -> EntityResolver:
    global _default_resolver
    if _default_resolver is None:
        with _default_resolver_lock:
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


# ⚠️ 与 #63 / #109 同型：解析器返回的是「这条名字映射路径的状态」，不是「世上有没有这个东西」。
# entity_resolver 此前是本通道里**唯一一个空手时连一句 note 都没有**的工具：
#   · confidence="ambiguous"（有候选、无 canonical_id）被 loop._EMPTY_CHECKS 判为**非空**
#     （评审 #25：候选是实质回复），于是既不降级、也没有任何下一步指引——模型拿到的是一个
#     裸 dict，正是 #63「不降级也不作答」的形状（get_entity 已于 1efb6e5c 补上逐候选重查的
#     note，get_datasheet 的 ambiguous 分支一直有 note，只有这里是空白）。
#   · confidence="none" 会被判空并降级 classic，模型看不到；但同一函数被 web/军表侧直调时
#     仍应把界线说穿，故两态都给 note。
_RESOLVER_AMBIGUOUS_NOTE = (
    "这个名字匹配到多个候选，本工具按判据拒绝静默取先入者。"
    "⚠️ 有歧义 ≠ 该单位不存在。请把 candidates 里的候选串**原样**回填本工具重查"
    "（`名字 (阵营缩写)` 形式可精确命中唯一阵营）；按问题上下文无法确定用户指哪一个时，"
    "逐个候选查证后分别说明，不要在未查证任何候选前就把问题退回给用户。"
)
_RESOLVER_MISS_NOTE = (
    "没能把这个名字解析到 canonical id（本工具只做「名字 → id」映射，不检索规则原文）。"
    "⚠️ 解析不到 ≠ 该单位或该阵营不存在，也 ≠ 它没有规则/点数——只说明这次名字映射没命中。"
    "请改用 get_datasheet / get_entity 直接传用户原文里的中文名重查，或用 rag_search 兜底；"
    "全都查不到就如实说「档案缺失，建议查阅原始规则书」。"
    "禁止据此输出「该单位/阵营不存在」「不属于战锤40K」这类否定性断言。"
)


def entity_resolver(name: str, resolver: Optional[EntityResolver] = None) -> Dict[str, Any]:
    """中文名/英文名/社区俗名 → canonical id（db_compile.entity_resolver）。

    解析不到时**必须**把「这条路径没命中」与「这个东西不存在」的界线说穿（见上方注释）。
    """
    r = resolver or _get_default_resolver()
    result = r.resolve(name)
    out: Dict[str, Any] = {
        "canonical_id": result.canonical_id,
        "name_en": result.name_en,
        "confidence": result.confidence,
        "candidates": result.candidates,
    }
    if not result.canonical_id:
        out["note"] = (_RESOLVER_AMBIGUOUS_NOTE if result.candidates
                       else _RESOLVER_MISS_NOTE)
    return out


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
        # ⚠️ 这里**不能**让 LLM 直接反问用户。ambiguous 被 loop._EMPTY_CHECKS 判为
        # 「非空」（评审 #25：候选是实质回复，不该降级 classic），于是经典链兜底也不会触发；
        # 若本 note 再让模型把问题退回用户，这条路径就成了「不降级也不作答」的死胡同
        # （基准 #63 坦克指挥官：0 检索源、judge 判「答非所问」❌）。
        # 正确做法与 get_datasheet 的 ambiguous 分支一致：先逐个候选查证再作答。
        note = ("译名有多个候选：" + "、".join(resolved["candidates"])
                + "。请逐个用候选名重新调用 get_entity 取回各自的实体页，"
                  "并在回答中分别说明各候选单位的情况；只有在查证候选之后仍无法判断"
                  "用户所指时才反问用户，不要在未查证任何候选前就把问题退回给用户。")
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

# ⚠️ 「本工具没查到」和「这个单位不存在」是两件事，工具返回里必须把这句话说穿。
# 基准 #109（一次问四个泰坦的点数）实测：calc_points 只按 units.id 精确查表，四个中文名
# 全部返回「未找到该 unit id」，模型把这个**查询失败**升级成了**否定性事实断言**——
# 「泰坦军团是独立桌游、不是 40K 阵营、四个泰坦在 11 版无官方点数」。而事实相反：
# Adeptus Titanicus 是 11 版正经阵营，官方 MFM 有阵营页，库里四行点数与官网逐条一致。
# 同样四个单位逐个单独问（走 get_datasheet）全部答对，可见错的不是数据而是这条空手返回。
_CALC_POINTS_UNRESOLVED_NOTE = (
    "未能把这个名字解析到库内任何单位（本工具按 units.id 精确查表）。"
    "⚠️ 查不到 ≠ 该单位或该阵营不存在，也 ≠ 它没有官方点数——只说明这次名字解析没命中。"
    "请改用 get_datasheet 传用户原文里的中文名重查，或先用 entity_resolver 取 canonical id "
    "再回来算分；全都查不到就如实说「档案缺失」。"
    "禁止据此输出「该单位/阵营不存在」「不属于战锤40K」「无官方点数」这类否定性断言。"
)


def calc_points(
    unit_list: List[str],
    db_path: Optional[Path] = None,
    resolver: Optional[EntityResolver] = None,
) -> Dict[str, Any]:
    """精确算分（SQLite，db_compile.calc_points）。点数缺失时诚实报告原因，不编造数值。

    底层 `db_compile.calc_points` 是纯 id 查表（保持不变——它被军表/web 侧按 canonical id
    直调）。名字解析放在这层 agent 包装里：LLM 拿到的是用户原文里的中文名，按既有约定
    直接查 id 必然全空，于是它只能凭记忆作答（基准 #109 的硬错来源）。这里先按 id 查，
    只对「未找到该 unit id」的那几个走 entity_resolver 重试，既不改变纯 id 调用的行为，
    也让中文名这条最常见的入参形态真的能查到。
    """
    from db_compile.calc_points import UNKNOWN_UNIT_NOTE

    # 参数防护（评审 M#4）：LLM 可能把 unit_list 传成单个字符串——字符串是可迭代的，
    # 会被逐字符拆成"单位名"胡乱查询。字符串包成单元素列表；其余非列表类型明确报错。
    if isinstance(unit_list, str):
        unit_list = [unit_list]
    elif not isinstance(unit_list, (list, tuple)):
        return {"ok": False, "found": False, "units": [],
                "note": f"参数错误：unit_list 应为单位名列表，收到 {type(unit_list).__name__}"}
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"found": False, "units": [], "note": "wh40k.sqlite 不存在，需先跑 db_compile"}

    results = _calc_points_impl(db_path, list(unit_list))
    units: List[Dict[str, Any]] = []
    unresolved: List[str] = []
    for query, r in zip(unit_list, results):
        if r.note != UNKNOWN_UNIT_NOTE:
            units.append({"unit_id": r.unit_id, "name_en": r.name_en,
                          "points": r.points, "note": r.note})
            continue

        resolved = _resolve_for_points(str(query), resolver)
        canonical_id = (resolved or {}).get("canonical_id")
        if canonical_id:
            retry = _calc_points_impl(db_path, [canonical_id])[0]
            if retry.note != UNKNOWN_UNIT_NOTE:
                units.append({
                    "unit_id": retry.unit_id, "name_en": retry.name_en,
                    "points": retry.points, "note": retry.note,
                    "query": str(query),
                    "resolved_via": {"canonical_id": canonical_id,
                                     "confidence": resolved.get("confidence")},
                })
                continue

        unresolved.append(str(query))
        units.append({"unit_id": r.unit_id, "name_en": None, "points": None,
                      "unresolved": True,
                      "candidates": (resolved or {}).get("candidates") or [],
                      "note": _CALC_POINTS_UNRESOLVED_NOTE})

    out: Dict[str, Any] = {"found": True, "units": units}
    if unresolved:
        out["unresolved"] = unresolved
        out["note"] = ("以下名字没能解析到库内单位：" + "、".join(unresolved)
                       + "。" + _CALC_POINTS_UNRESOLVED_NOTE)
    return out


def _resolve_for_points(
    name: str, resolver: Optional[EntityResolver],
) -> Optional[Dict[str, Any]]:
    """名字 → canonical id；解析器构造/查询失败不许把整次算分带崩（诚实返回 None 即可）。"""
    try:
        return entity_resolver(name, resolver=resolver)
    except Exception:
        return None


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

    from db_compile.datasheet import AmbiguousUnitName, find_datasheet

    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"found": False, "datasheet": None,
                "note": "wh40k.sqlite 不存在，需先跑 db_compile build"}

    try:
        ds = find_datasheet(db_path, name_or_id,
                            resolver=resolver or _get_default_resolver())
    except AmbiguousUnitName as exc:
        # 评审 #25：同名单位存在于多个阵营（如 Helbrute×4），静默取一会答错阵营数据。
        # 附各候选核心属性预览——LLM 可按上下文选定或逐一披露，无需（也不许）凭记忆填数。
        from db_compile.datasheet import lookup_datasheet
        preview = []
        for uid, nm, fac in exc.hits[:6]:
            ds2 = lookup_datasheet(db_path, uid)
            if ds2 and ds2.models:
                m0 = ds2.models[0]
                preview.append({"candidate": "{} ({})".format(nm, fac or "?"),
                                "faction": ds2.faction, "m": m0.m, "t": m0.t,
                                "sv": m0.sv, "w": m0.w})
        return {"found": False, "datasheet": None, "reason": "ambiguous",
                "candidates": exc.candidates,
                "candidates_preview": preview,
                "note": "同名单位存在于多个阵营，各阵营数值可能不同（见 candidates_preview）。"
                        "请按问题上下文用候选名（含阵营缩写）重查其一；无法确定阵营时，"
                        "逐一列出各候选数值作答，绝不要只挑一个当作唯一答案："
                        + "、".join(exc.candidates)}
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

# rag_search 是**唯一**一个空手结果一定会被模型看到的工具：loop.py 的降级分支显式排除了它
# （`tool_name != "rag_search"`——它自己就是兜底目标，降级到自己没意义），所以这里的措辞就是
# 模型作答前看到的最后一句话。三种失败态此前共用同一个形状 `{found: False, passages: []}`，
# 模型无从区分「语料里没有」和「检索管线自己坏了」，很容易把工具故障写成「档案里没有这条规则」
# 的否定性断言（#109 同型）。故按失败性质分开措辞，并给 error 标志。
_RAG_EMPTY_NOTE = (
    "本次混合检索没有命中任何段落（提问措辞/译名与语料用词不一致时最常见）。"
    "⚠️ 没检索到 ≠ 该规则或该单位不存在。请换更短的关键词、或改用中/英文术语再检一次，"
    "也可以改用 get_datasheet / get_entity / get_keyword_definition 直查结构库；"
    "仍无结果就如实说「档案缺失，建议查阅原始规则书」，"
    "禁止据此输出「规则书里没有这条规则」「该单位不存在」这类否定性断言。"
)
_RAG_UNAVAILABLE_HINT = (
    "⚠️ 这是**检索侧环境故障**，不是「语料里没有相关内容」——不可据此判断该规则/单位是否存在。"
    "请改用 get_datasheet / get_entity / get_keyword_definition 直查结构库；"
    "都取不到就如实说明本次检索不可用，禁止输出任何否定性事实断言。"
)


def rag_search(query: str, app_module: Optional[Any] = None) -> Dict[str, Any]:
    """现有混合检索（兜底）。只读调用 app.py 的 load_resources/build_bm25/hybrid_retrieve，
    不修改 app.py 本身。

    失败态分两类并各自标注：`error=True` 表示检索管线/环境本身不可用（知识库未构建、调用异常），
    `error` 缺省表示检索跑通了但零命中——后者才是关于语料内容的信息。
    """
    try:
        app = app_module if app_module is not None else _import_app()
        embeddings, vectorstore, reranker, reranker_warning = app.load_resources()
        if vectorstore is None:
            return {"found": False, "error": True, "passages": [],
                    "note": "知识库未构建（local_vector_store 为空），请先跑 ingest.py。"
                            + _RAG_UNAVAILABLE_HINT}

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
            "note": None if passages else _RAG_EMPTY_NOTE,
        }
    except Exception as exc:
        return {"found": False, "error": True, "passages": [],
                "note": f"rag_search 执行异常（检索管线本身出错）: {exc}。"
                        + _RAG_UNAVAILABLE_HINT}


# ── 未建模能力：诚实打桩，严禁伪造结果 ────────────────────────────

def _not_modeled(tool: str, note: str) -> Dict[str, Any]:
    return {"ok": False, "modeled": False, "tool": tool, "note": note}


def judge_fight_order(ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """P5-b/e：Fight phase 先攻判定（11 版口径）。

    ctx（全可选，含默认）：
      attacker / defender：单位名（仅作展示，不解析）。
      attacker_charged：攻方本回合是否冲锋（默认 True——"我冲上去"语境）。
      attacker_fights_first / attacker_fights_last / defender_fights_first /
      defender_fights_last：布尔（Fights First / Fights Last 能力，datasheet 上有则填）。
      counter_offensive_by："attacker" | "defender"（谁用 Counter-offensive 战略）。

    Fights First 等能力无法从库里可靠自动判定（见 abilities T1），故由调用方显式提供，
    不猜、不静默默认（除"冲锋"默认按语境 True）。
    """
    ctx = ctx or {}
    try:
        from engines.simulator.fight_order import FighterState, judge
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "modeled": True, "tool": "judge_fight_order",
                "note": f"fight_order 导入失败: {exc}"}

    a_name = str(ctx.get("attacker", "攻方"))
    b_name = str(ctx.get("defender", "守方"))
    co_raw = ctx.get("counter_offensive_by")
    co_by = None
    if co_raw in ("attacker", "a", a_name):
        co_by = a_name
    elif co_raw in ("defender", "b", b_name):
        co_by = b_name

    a = FighterState(a_name, is_active_player=True,
                     charged=bool(ctx.get("attacker_charged", True)),
                     fights_first=bool(ctx.get("attacker_fights_first")),
                     fights_last=bool(ctx.get("attacker_fights_last")))
    b = FighterState(b_name, is_active_player=False, charged=False,
                     fights_first=bool(ctx.get("defender_fights_first")),
                     fights_last=bool(ctx.get("defender_fights_last")))
    v = judge(a, b, counter_offensive_by=co_by)
    return {
        "ok": True, "modeled": True, "tool": "judge_fight_order",
        "first_striker": v.first_striker,
        "first_side": "attacker" if v.first_is_a else "defender",  # 名字可能相同，用侧标识
        "order": list(v.order),
        "simultaneous_risk": v.simultaneous_risk,
        "rationale": v.rationale,
        "rule_refs": list(v.rule_refs),
        "counter_offensive_note": v.counter_offensive_note,
    }


def _resolve_unit(name: str, resolver: Optional[EntityResolver] = None) -> Dict[str, Any]:
    """单位名 → canonical id，返回统一形态；三失败路径显式区分，绝不静默取第一个。"""
    r = entity_resolver(name, resolver=resolver)
    cid, name_en, conf, cands = (r["canonical_id"], r["name_en"],
                                 r["confidence"], r["candidates"])
    if conf == "ambiguous":
        return {"ok": False, "reason": "ambiguous", "input": name,
                "candidates": cands,
                "note": f"『{name}』有多个候选，请指明其一：" + "、".join(cands[:8])}
    if cid is None:
        return {"ok": False, "reason": "not_found", "input": name,
                "note": f"未解析到单位『{name}』（译名未收录或拼写不符），请换用更精确的名称"}
    out = {"ok": True, "canonical_id": cid, "name_en": name_en, "confidence": conf}
    if conf == "fuzzy":
        out["warning"] = f"『{name}』为模糊匹配到 {name_en}，若非此单位请用更精确的名称"
    return out


def _report_to_dict(rep) -> Dict[str, Any]:
    """SimReport → JSON 可序列化 dict（含递归的 reverse）。"""
    return {
        "expected_damage": rep.expected_damage,
        "expected_kills": rep.expected_kills,
        "wipe_probability": rep.wipe_probability,
        "distribution": rep.distribution,
        "funnel": rep.funnel,
        "efficiency": rep.efficiency,
        "modeled_effects": rep.modeled_effects,
        "not_modeled": rep.not_modeled,
        "bias_notes": rep.bias_notes,
        "iterations": rep.iterations,
        "seed": rep.seed,
        "reverse": _report_to_dict(rep.reverse) if rep.reverse else None,
    }


def simulate_combat(
    attacker: str, defender: str, options: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None, resolver: Optional[EntityResolver] = None,
) -> Dict[str, Any]:
    """P4 蒙特卡洛：attacker 打 defender 一次攻击序列 × N，返回带诚实声明的报告。

    options（全可选）：phase(shooting|melee)、charge、half_range、cover、stationary、
    long_range、indirect；attacker_models、defender_models；loadout=[[武器名,数量],...]
    （多模型单位必填，否则返回 ambiguous+武器池）；defender_loadout（给了则串行幸存反打）；
    fnp(守方无痛X)、damage_reduction；n(默认8000)、seed。
    P7 阵营 DSL：guided、markerlight_observer、detachment(分队名，如 Kauyon/Mont'ka)、
    detachment_rounds(假设处于分队规则生效轮次)、stratagems=[战略 id/英文名/中文名,...]
    （一次性 opt-in；CP 不结算，未匹配/分队不符显式披露）。
    P7-PR4 新增：enhancements=[增强名,...]（opt-in 同战略）；假设开关
    range_within_12/range_within_8（Bonded Heroes 射程档）、target_below_starting/
    target_below_half（Hunter's Instincts 战损档）、markerlight_visible、bearer_leading；
    守方向：defender_detachment、defender_stratagems、defender_enhancements、
    defender_hidden、defender_bearer_leading（防守 DSL 经 inject_target 注入）。
    """
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"ok": False, "modeled": True, "tool": "simulate_combat",
                "note": "wh40k.sqlite 不存在，需先跑 db_compile build"}

    a = _resolve_unit(attacker, resolver=resolver)
    if not a["ok"]:
        return {"ok": False, "modeled": True, "tool": "simulate_combat", **a}
    d = _resolve_unit(defender, resolver=resolver)
    if not d["ok"]:
        return {"ok": False, "modeled": True, "tool": "simulate_combat", **d}
    return simulate_combat_resolved(a, d, options, db_path)


def simulate_combat_resolved(
    a: Dict[str, Any], d: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None, db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """已解析攻/守（{"canonical_id","name_en",可选"warning"}）→ 模拟核心。

    web_api /simulate 用图鉴 canonical id 直调（免名字解析歧义）；
    simulate_combat 解析名字后同走此核心。options 语义见 simulate_combat。
    """
    options = options or {}
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {"ok": False, "modeled": True, "tool": "simulate_combat",
                "note": "wh40k.sqlite 不存在，需先跑 db_compile build"}

    try:
        from dataclasses import replace as _replace

        from engines.simulator.assembly import assemble_attacker, usable_in_phase
        from engines.simulator.contracts import Effect, Stance
        from engines.simulator.engine import simulate, simulate_matchup
        from engines.simulator.profile import load_target

        phase = options.get("phase", "shooting")
        stance = Stance(
            phase=phase, charging=bool(options.get("charge")),
            stationary=bool(options.get("stationary")),
            half_range=bool(options.get("half_range")),
            target_in_cover=bool(options.get("cover")),
            long_range=bool(options.get("long_range")),
            indirect=bool(options.get("indirect")),
            guided=bool(options.get("guided")),
            markerlight_observer=bool(options.get("markerlight_observer")),
            detachment_rounds=bool(options.get("detachment_rounds")),
            range_within_12=bool(options.get("range_within_12")),
            range_within_8=bool(options.get("range_within_8")),
            target_below_starting=bool(options.get("target_below_starting")),
            target_below_half=bool(options.get("target_below_half")),
            blessing_martial_excellence=bool(options.get("blessing_martial_excellence")),
            blessing_warp_blades=bool(options.get("blessing_warp_blades")),
            blessing_decapitating_strikes=bool(options.get("blessing_decapitating_strikes")),
            disembarked_this_turn=bool(options.get("disembarked_this_turn")),
            disembarked_from_land_raider=bool(options.get("disembarked_from_land_raider")),
            omen_instrument=bool(options.get("omen_instrument")),
            omen_momentous_brutality=bool(options.get("omen_momentous_brutality")),
            plague_rattlejoint=bool(options.get("plague_rattlejoint")),
        )

        loadout = options.get("loadout")
        loadout = [(str(w), int(c)) for w, c in loadout] if loadout else None
        asm = assemble_attacker(db_path, a["canonical_id"],
                                models=options.get("attacker_models"),
                                loadout=loadout, phase=phase)
        if asm is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "not_found", "note": f"单位 {a['name_en']} 无法装载"}
        # 该阶段压根没有可开火武器 → 不是"该装配"而是"该换阶段"：要求 loadout 无解
        # （只有近战武器的单位在射击阶段填任何件数都是 0 攻击）
        if asm.no_phase_weapon:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "no_weapon_for_phase", "note": asm.note,
                    "weapon_pool": [w.name_en for w in asm.full_pool],
                    "model_tiers": asm.tiers, "errors": asm.errors}
        if asm.ambiguous or asm.attacker is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "loadout_required", "note": asm.note,
                    "weapon_pool": [w.name_en for w in asm.weapon_pool],
                    "model_tiers": asm.tiers, "errors": asm.errors}
        # 显式 loadout 与阶段不匹配（如手填纯近战武器打射击阶段）→ 序列层会滤成 0 攻击，
        # 与其发一份"成功的"全 0 报告（假成功），不如显式失败并指路（诚实降级纪律）
        if not usable_in_phase(asm.attacker.loadout, phase):
            _here = "近战" if phase == "melee" else "射击"
            _other = "射击" if phase == "melee" else "近战"
            return {
                "ok": False, "modeled": True, "tool": "simulate_combat",
                "reason": "no_weapon_for_phase",
                "note": (f"loadout 里没有{_here}阶段能开火的武器"
                         f"（{'、'.join(w.name_en for w in asm.attacker.loadout[:6])}"
                         f" 全是{_other}武器），期望伤害必为 0。请改装配或切到{_other}阶段。"),
                "weapon_pool": [w.name_en for w in asm.weapon_pool],
                "model_tiers": asm.tiers, "errors": asm.errors}

        target = load_target(db_path, d["canonical_id"],
                             models=options.get("defender_models"))
        if target is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "not_found", "note": f"守方 {d['name_en']} 无法装载"}

        # P7：攻方阵营 DSL 条目——先过选择层（分队匹配 + 战略/增强点名，PR3/PR4），
        # 再按开关注入（stance 同源 options 点亮，条件 tag 放行），注记随后挂进 report
        # （modeled⇄结果被影响 成对，评审 F5）
        from engines.simulator.dsl import (
            attacker_toggles_from_options,
            inject_attacker,
            inject_target,
            select_entries,
            target_toggles_from_options,
        )
        from engines.simulator.profile import load_unit_dsl
        dsl_entries = load_unit_dsl(db_path, a["canonical_id"])
        selected_entries, select_notes = select_entries(
            list(dsl_entries),
            detachment=options.get("detachment"),
            stratagems=tuple(options.get("stratagems") or ()),
            enhancements=tuple(options.get("enhancements") or ()))
        dsl_toggles = attacker_toggles_from_options(options)
        attacker_prof, dsl_modeled, dsl_notes = inject_attacker(
            asm.attacker, selected_entries, dsl_toggles)
        dsl_notes = select_notes + dsl_notes
        # P7-PR4：守方阵营 DSL——防守向条目（Skirmish Fighters/Stimm Injectors/
        # Counterfire 等）经 inject_target 注入 target.effects；守方自己的分队/
        # 战略/增强用 defender_* 选项点名
        defender_dsl = load_unit_dsl(db_path, d["canonical_id"])
        d_selected, d_select_notes = select_entries(
            list(defender_dsl),
            detachment=options.get("defender_detachment"),
            stratagems=tuple(options.get("defender_stratagems") or ()),
            enhancements=tuple(options.get("defender_enhancements") or ()))
        target, t_modeled, t_notes = inject_target(
            target, d_selected, target_toggles_from_options(options))
        dsl_modeled = dsl_modeled + t_modeled
        dsl_notes = dsl_notes + d_select_notes + t_notes
        # 面板/上层可见的可用开关/战略/增强清单（surface，不自动开；PR4 补 side
        # 供前端分攻/守两栏渲染与点名回传）：攻方栏=攻方阵营的攻方向条目，
        # 守方栏=守方阵营的防守向条目（异阵营对局两栏各取各的）
        dsl_available = [
            {"table": e.table, "id": e.row_id, "side": e.side,
             "name_en": e.name_en, "name_zh": e.name_zh, "status": e.status,
             "detachment": e.detachment,
             "requires_toggles": list(e.requires_toggles)}
            for e in dsl_entries if e.effects and e.side == "attacker"
        ] + [
            {"table": e.table, "id": e.row_id, "side": e.side,
             "name_en": e.name_en, "name_zh": e.name_zh, "status": e.status,
             "detachment": e.detachment,
             "requires_toggles": list(e.requires_toggles)}
            for e in defender_dsl if e.effects and e.side == "target"]

        def _annotate_dsl(rep):
            rep.modeled_effects.extend(dsl_modeled)
            rep.not_modeled.extend(dsl_notes)
            return rep
        # P5-a：守方可 opt-in 的防守开关（名字/说明/是否解析出参数）——供面板预填、不自动施加
        from engines.simulator.context import build_toggles_available
        from engines.simulator.profile import load_faction_options
        defender_toggles = [{"name": nm, "note": note, "parsed": parsed}
                            for nm, note, parsed in build_toggles_available(target)]
        # P5-c：守方阵营分队名 surface（只列名不施加，诚实披露未建模的分队/军队规则）
        faction_options = load_faction_options(db_path, d["canonical_id"])
        # 防守侧手动开关 → Effect
        def_effects = []
        if options.get("fnp"):
            def_effects.append(Effect("fnp", "fnp", (int(options["fnp"]),), (),
                                      f"feel no pain {options['fnp']}+"))
        if options.get("damage_reduction"):
            def_effects.append(Effect("damage", "damage_reduction",
                                      (int(options["damage_reduction"]),), (),
                                      "damage reduction"))
        if options.get("stealth"):    # 11版24.33：守方 Stealth → 被远程攻击选中获掩体收益
            def_effects.append(Effect("save", "cover", (), ("phase_shooting",),
                                      "stealth"))    # 仅射击；攻方 [IGNORES COVER] 可抵消
        # P5-c 手工核验通用开关（2026-07-11 按 11 版核心战略清单审计订正）：
        #   Smokescreen（1CP 核心战略）：对手射击阶段开始时选一友方 SMOKE 单位，该阶段
        #   指向它的攻击目标获掩体收益（13.08=恶化攻方 BS 1）——不额外附加十版 Stealth 式
        #   减命中（那部分成分已删）；「遮蔽后方友军」成分超出 1v1 模拟范围，不建模。
        #   Go to Ground 已不在 11 版核心战略清单中 → 开关废弃；旧调用传入时不静默
        #   忽略，经 warning 显式披露（近似替代：cover=True + 手动设守方无效保护）。
        cover_on = bool(options.get("cover"))
        if options.get("smokescreen"):
            cover_on = True
        gtg_warn = ("go_to_ground 开关已废弃（11 版核心战略无 Go to Ground），本次未生效"
                    if options.get("go_to_ground") else None)
        # loadout 与阶段不匹配已在装配后显式失败（reason=no_weapon_for_phase），此处不再
        # 有"全 0 报告 + warning"的假成功路径。自动装配（该阶段唯一武器）的件数假设须披露。
        auto_warn = f"攻方自动装配：{asm.note}" if asm.auto_assembled else None
        warn_parts: List[Optional[str]] = [a.get("warning"), d.get("warning"),
                                           gtg_warn, auto_warn]
        if cover_on and not stance.target_in_cover:
            stance = _replace(stance, target_in_cover=True)
        if def_effects:
            # P7-PR4：追加而非整体替换——target.effects 里可能已有 inject_target
            # 注入的守方 DSL 效果，替换会静默吞掉（多来源同 op 由引擎取更优）
            target = _replace(target, effects=target.effects + tuple(def_effects))

        n = int(options.get("n", 8000))
        seed = int(options.get("seed", 1234))
        # 点数用 canonical_id 查（calc_points 按 units.id，name_en 查不到——评审 M#6）
        def _pts(cid):
            r = _calc_points_impl(db_path, [cid])
            return r[0].points if r and r[0].points else None
        points_a = _pts(a["canonical_id"])
        points_b = _pts(d["canonical_id"])          # 评审 M#7：B 侧点数也算，供反打性价比

        # 反打：显式 reverse 开关 或 给了 defender_loadout 才做串行幸存反打，否则单向。
        # 守方多武器且未指明 loadout → 走 defender_loadout_required 让上层要求装配。
        d_loadout = options.get("defender_loadout")
        if options.get("reverse") or d_loadout:
            rev_phase = options.get("reverse_phase", "melee")
            d_asm = assemble_attacker(
                db_path, d["canonical_id"], models=options.get("defender_models"),
                loadout=[(str(w), int(c)) for w, c in d_loadout] if d_loadout else None,
                phase=rev_phase)
            a_as_target = load_target(db_path, a["canonical_id"],
                                      models=options.get("attacker_models"))
            if d_asm is None or a_as_target is None:
                return {"ok": False, "modeled": True, "tool": "simulate_combat",
                        "reason": "not_found",
                        "note": f"守方 {d['name_en']} 反打装载失败"}
            # 守方在反打阶段无可开火武器 → 装配也救不了，显式失败并指路（不静默退回单向）
            if d_asm.no_phase_weapon:
                return {"ok": False, "modeled": True, "tool": "simulate_combat",
                        "reason": "defender_no_weapon_for_phase",
                        "note": f"守方反打：{d_asm.note}（或关掉「守方反打」只看单向）",
                        "weapon_pool": [w.name_en for w in d_asm.full_pool],
                        "model_tiers": d_asm.tiers, "errors": d_asm.errors}
            # 守方多武器且未指明 → 显式要求装配（禁止静默退回单向：违反诚实降级纪律）
            if d_asm.ambiguous or d_asm.attacker is None:
                return {"ok": False, "modeled": True, "tool": "simulate_combat",
                        "reason": "defender_loadout_required", "note": d_asm.note,
                        "weapon_pool": [w.name_en for w in d_asm.weapon_pool],
                        "model_tiers": d_asm.tiers, "errors": d_asm.errors}
            # 显式守方 loadout 与反打阶段不匹配 → 同攻方，显式失败不发全 0 反打
            if not usable_in_phase(d_asm.attacker.loadout, rev_phase):
                return {
                    "ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "defender_no_weapon_for_phase",
                    "note": (f"守方反打：defender_loadout 里没有"
                             f"{'近战' if rev_phase == 'melee' else '射击'}阶段能开火的武器"
                             f"（{'、'.join(w.name_en for w in d_asm.attacker.loadout[:6])}），"
                             f"反打期望伤害必为 0"),
                    "weapon_pool": [w.name_en for w in d_asm.weapon_pool],
                    "model_tiers": d_asm.tiers, "errors": d_asm.errors}
            if d_asm.auto_assembled:
                warn_parts.append(f"守方反打自动装配：{d_asm.note}")
            warning = "；".join(x for x in warn_parts if x) or None
            rep = simulate_matchup(
                attacker_prof, target, d_asm.attacker, a_as_target,
                stance_forward=stance, stance_reverse=Stance(phase=rev_phase),
                n=n, seed=seed, points_a=points_a, points_b=points_b,
                a_fights_first=bool(options.get("attacker_fights_first")),
                a_fights_last=bool(options.get("attacker_fights_last")),
                b_fights_first=bool(options.get("defender_fights_first")),
                b_fights_last=bool(options.get("defender_fights_last")))
            return {"ok": True, "modeled": True, "tool": "simulate_combat",
                    "attacker": a["name_en"], "defender": d["name_en"],
                    "phase": phase, "report": _report_to_dict(_annotate_dsl(rep)),
                    "defender_toggles": defender_toggles,
                    "faction_options": faction_options,
                    "dsl_available": dsl_available,
                    "warning": warning}

        warning = "；".join(x for x in warn_parts if x) or None
        rep = simulate(attacker_prof, target, stance, n=n, seed=seed, points=points_a)
        return {"ok": True, "modeled": True, "tool": "simulate_combat",
                "attacker": a["name_en"], "defender": d["name_en"],
                "phase": phase, "report": _report_to_dict(_annotate_dsl(rep)),
                "defender_toggles": defender_toggles,
                "faction_options": faction_options,
                "dsl_available": dsl_available,
                "warning": warning}
    except Exception as exc:   # noqa: BLE001 — 显式暴露，不静默吞
        import traceback
        return {"ok": False, "modeled": True, "tool": "simulate_combat",
                "note": f"模拟执行异常: {exc}", "trace": traceback.format_exc()[-800:]}


def validate_roster(roster_text: str) -> Dict[str, Any]:
    # P6 验表引擎已上线（engines/roster + 军表实验室页签）；聊天侧缺的是
    # 自由文本军表 → 结构化 Roster 的解析层（P6-PR1c，待真实样本）。
    # 文案不许再说「计划于 P6」——对用户陈述过时假事实（gnhf 审查模块 5 M3）。
    return _not_modeled(
        "validate_roster",
        "聊天侧军表文本解析未建模（无法从自由文本可靠还原单位/模型数/强化）。"
        "验表功能已上线：请到「军表实验室」页签用图鉴单位搭表，即可实时验证点数与编制约束")


def critique_roster(roster_text: str) -> Dict[str, Any]:
    return _not_modeled(
        "critique_roster",
        "聊天侧军表文本解析未建模（无法从自由文本可靠还原单位/装配）。"
        "点评功能已上线：请到「军表实验室」页签搭表并装配武器，即可获得强度点评")


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
    {"name": "judge_fight_order", "description": "战斗顺序判定：给定冲锋/Fights First/Fights Last/Counteroffensive，判谁先打 + 依据（11版 Fight phase）"},
    {"name": "simulate_combat", "description": "蒙特卡洛对战模拟：attacker 打 defender 期望伤害/击杀/团灭率+漏斗+性价比（多模型单位需 options.loadout）"},
    {"name": "validate_roster", "description": "验表（聊天侧文本解析未建模——引导用户去军表实验室页签）"},
    {"name": "critique_roster", "description": "验表+模拟点评（聊天侧文本解析未建模——引导用户去军表实验室页签）"},
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
