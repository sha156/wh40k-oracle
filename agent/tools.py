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
    """P5-b/e：十版 Fight phase 先攻判定。

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
    """
    options = options or {}
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

    try:
        from dataclasses import replace as _replace

        from engines.simulator.assembly import assemble_attacker
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
        )

        loadout = options.get("loadout")
        loadout = [(str(w), int(c)) for w, c in loadout] if loadout else None
        asm = assemble_attacker(db_path, a["canonical_id"],
                                models=options.get("attacker_models"),
                                loadout=loadout, phase=phase)
        if asm is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "not_found", "note": f"单位 {attacker} 无法装载"}
        if asm.ambiguous or asm.attacker is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "loadout_required", "note": asm.note,
                    "weapon_pool": [w.name_en for w in asm.weapon_pool],
                    "model_tiers": asm.tiers, "errors": asm.errors}

        target = load_target(db_path, d["canonical_id"],
                             models=options.get("defender_models"))
        if target is None:
            return {"ok": False, "modeled": True, "tool": "simulate_combat",
                    "reason": "not_found", "note": f"守方 {defender} 无法装载"}
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
        if options.get("stealth"):    # P5-a：守方 Stealth → 攻方射击命中 -1（仅射击）
            def_effects.append(Effect("hit", "modify", (-1,), ("phase_shooting",),
                                      "stealth"))
        # P5-c 手工核验通用开关（评审 E1 订正）：
        #   Go to Ground（1CP）= Benefit of Cover + 6+ 无效保护（不给 Stealth）
        #   Smokescreen        = Benefit of Cover + Stealth(-1 射击命中)
        cover_on = bool(options.get("cover"))
        if options.get("go_to_ground"):
            cover_on = True
            target = _replace(target, invuln=min(target.invuln or 7, 6))
        if options.get("smokescreen"):
            cover_on = True
            def_effects.append(Effect("hit", "modify", (-1,), ("phase_shooting",),
                                      "smokescreen"))
        if cover_on and not stance.target_in_cover:
            stance = _replace(stance, target_in_cover=True)
        if def_effects:
            target = _replace(target, effects=tuple(def_effects))

        n = int(options.get("n", 8000))
        seed = int(options.get("seed", 1234))
        # 点数用 canonical_id 查（calc_points 按 units.id，name_en 查不到——评审 M#6）
        def _pts(cid):
            r = _calc_points_impl(db_path, [cid])
            return r[0].points if r and r[0].points else None
        points_a = _pts(a["canonical_id"])
        points_b = _pts(d["canonical_id"])          # 评审 M#7：B 侧点数也算，供反打性价比

        # 反打：给了 defender_loadout 才做串行幸存反打，否则单向
        d_loadout = options.get("defender_loadout")
        if d_loadout:
            d_asm = assemble_attacker(
                db_path, d["canonical_id"], models=options.get("defender_models"),
                loadout=[(str(w), int(c)) for w, c in d_loadout],
                phase=options.get("reverse_phase", "melee"))
            a_as_target = load_target(db_path, a["canonical_id"],
                                      models=options.get("attacker_models"))
            if d_asm and not d_asm.ambiguous and a_as_target is not None:
                rep = simulate_matchup(
                    asm.attacker, target, d_asm.attacker, a_as_target,
                    stance_forward=stance,
                    stance_reverse=Stance(phase=options.get("reverse_phase", "melee")),
                    n=n, seed=seed, points_a=points_a, points_b=points_b,
                    a_fights_first=bool(options.get("attacker_fights_first")),
                    a_fights_last=bool(options.get("attacker_fights_last")),
                    b_fights_first=bool(options.get("defender_fights_first")),
                    b_fights_last=bool(options.get("defender_fights_last")))
                return {"ok": True, "modeled": True, "tool": "simulate_combat",
                        "attacker": a["name_en"], "defender": d["name_en"],
                        "phase": phase, "report": _report_to_dict(rep),
                        "defender_toggles": defender_toggles,
                        "faction_options": faction_options,
                        "warning": a.get("warning") or d.get("warning")}

        rep = simulate(asm.attacker, target, stance, n=n, seed=seed, points=points_a)
        return {"ok": True, "modeled": True, "tool": "simulate_combat",
                "attacker": a["name_en"], "defender": d["name_en"],
                "phase": phase, "report": _report_to_dict(rep),
                "defender_toggles": defender_toggles,
                "faction_options": faction_options,
                "warning": a.get("warning") or d.get("warning")}
    except Exception as exc:   # noqa: BLE001 — 显式暴露，不静默吞
        import traceback
        return {"ok": False, "modeled": True, "tool": "simulate_combat",
                "note": f"模拟执行异常: {exc}", "trace": traceback.format_exc()[-800:]}


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
    {"name": "judge_fight_order", "description": "战斗顺序判定：给定冲锋/Fights First/Fights Last/Counter-offensive，判谁先打 + 依据（十版 Fight phase）"},
    {"name": "simulate_combat", "description": "蒙特卡洛对战模拟：attacker 打 defender 期望伤害/击杀/团灭率+漏斗+性价比（多模型单位需 options.loadout）"},
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
