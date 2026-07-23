"""web_api/simulate.py — 模拟器页签后端（BUILD-PLAN Stage 4）。

图鉴 canonical id 直调 P4/P5 模拟核心（agent.tools.simulate_combat_resolved），
免名字解析歧义；tool dict → SimResponse（camelCase 镜像，契约真源 web/src/lib/sim.ts）。
options 在边界白名单过滤 + 类型收敛（n 有上限，防把后端当算力用）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from web_api.contract import (
    SimDslEntry,
    SimFactionOptions,
    SimReportOut,
    SimResponse,
    SimToggle,
)

# 允许透传给模拟核心的 options 键 → 收敛函数（边界验证，未知键静默丢弃）
_N_MIN, _N_MAX = 100, 20000
# 数值入参上限：模拟核心的 numpy 数组宽度 = 武器数×每模型攻击数（含 Blast 按守方
# 模型数放大），这些入参不封顶会绕过 n 钳制构成算力/内存 DoS。真实兵牌模型数 ≤ ~25、
# 单位武器总数 ≤ ~60，上限取数倍余量；超限视同非法值丢弃（与 ≤0 同待遇），不静默钳
# （钳了会悄悄改变模拟语义）。roster 侧（web_api/roster.py、contract.py）共用。
MODELS_MAX = 100
WEAPON_COUNT_MAX = 400
LOADOUT_ITEMS_MAX = 40
_DMG_REDUCTION_MAX = 6


def _as_bool(v: Any) -> bool:
    """JSON 布尔 / 数字 / "true"|"false"（大小写不敏感）→ bool。

    字符串 "false"/"0" 不当真值——直连客户端发字符串布尔时避免 bool("false")==True 陷阱。
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return False


def _as_pos_int(v: Any, hi: Optional[int] = None) -> Optional[int]:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    if i <= 0 or (hi is not None and i > hi):
        return None
    return i


def _as_loadout(v: Any) -> Optional[List[Tuple[str, int]]]:
    """[[武器名, 数量], ...] → [(str, 0<int≤上限)]；任一项非法则整体丢弃（不猜半份装配）。"""
    if not isinstance(v, list) or not v or len(v) > LOADOUT_ITEMS_MAX:
        return None
    out: List[Tuple[str, int]] = []
    for item in v:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            return None
        name, cnt = item
        c = _as_pos_int(cnt, WEAPON_COUNT_MAX)
        if not isinstance(name, str) or not name.strip() or c is None:
            return None
        out.append((name.strip(), c))
    return out


def sanitize_options(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """边界白名单：只放行模拟核心认识的键，并收敛类型；n 钳制到 [100, 20000]。"""
    raw = raw or {}
    out: Dict[str, Any] = {}
    if raw.get("phase") in ("shooting", "melee"):
        out["phase"] = raw["phase"]
    if raw.get("reverse_phase") in ("shooting", "melee"):
        out["reverse_phase"] = raw["reverse_phase"]
    # smokescreen 不在白名单：引擎里它只是 cover_on 的别名（smokescreen→cover_on），
    # 网页用 cover 开关表达即可，不重复暴露；agent 直调路径不过此白名单，仍可用 smokescreen。
    # P7：阵营 DSL 布尔开关（攻/守两侧，PR4 起清单以 dsl.py 注册表为唯一真源——
    # 新增开关登记注册表即自动过边界，不再手抄第二份）
    from engines.simulator.dsl import ATTACKER_TOGGLES, TARGET_TOGGLES
    for key in (("charge", "half_range", "cover", "stationary", "long_range",
                 "indirect", "stealth", "reverse")
                + tuple(ATTACKER_TOGGLES) + tuple(TARGET_TOGGLES)):
        if key in raw:
            out[key] = _as_bool(raw[key])
    # P7-PR3/PR4：分队名（str）+ 战略/增强点名（list[str]，条数/长度设上限防滥用）——
    # 匹配失败在核心层显式披露（select_entries），边界只收敛类型不猜语义
    for det_key in ("detachment", "defender_detachment"):
        det = raw.get(det_key)
        if isinstance(det, str) and det.strip():
            out[det_key] = det.strip()[:80]
    for list_key in ("stratagems", "enhancements",
                     "defender_stratagems", "defender_enhancements"):
        vals = raw.get(list_key)
        if isinstance(vals, list):
            toks = [s.strip()[:80] for s in vals if isinstance(s, str) and s.strip()]
            if toks:
                out[list_key] = toks[:16]
    for key, hi in (("attacker_models", MODELS_MAX), ("defender_models", MODELS_MAX),
                    ("damage_reduction", _DMG_REDUCTION_MAX), ("seed", None)):
        v = _as_pos_int(raw.get(key), hi)
        if v is not None:
            out[key] = v
    fnp = _as_pos_int(raw.get("fnp"))
    if fnp is not None and 2 <= fnp <= 6:
        out["fnp"] = fnp
    n = _as_pos_int(raw.get("n"))
    if n is not None:
        out["n"] = max(_N_MIN, min(_N_MAX, n))
    loadout = _as_loadout(raw.get("loadout"))
    if loadout is not None:
        out["loadout"] = loadout
    d_loadout = _as_loadout(raw.get("defender_loadout"))
    if d_loadout is not None:
        out["defender_loadout"] = d_loadout
    return out


def lookup_unit_name(db_path, unit_id: str) -> Optional[str]:
    """canonical id → name_en；不存在返回 None（端点据此 404）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        r = conn.execute(
            "SELECT name_en FROM units WHERE id = ?", (unit_id,)).fetchone()
    finally:
        conn.close()
    return r[0] if r else None


def _report_out(rep: Optional[Dict[str, Any]]) -> Optional[SimReportOut]:
    if not rep:
        return None
    return SimReportOut(
        expected_damage=rep.get("expected_damage", 0.0),
        expected_kills=rep.get("expected_kills", 0.0),
        wipe_probability=rep.get("wipe_probability", 0.0),
        distribution=rep.get("distribution") or {},
        funnel=rep.get("funnel") or {},
        efficiency=rep.get("efficiency") or {},
        modeled_effects=rep.get("modeled_effects") or [],
        not_modeled=rep.get("not_modeled") or [],
        bias_notes=rep.get("bias_notes") or [],
        iterations=rep.get("iterations") or 0,
        seed=rep.get("seed") or 0,
        reverse=_report_out(rep.get("reverse")),
    )


def run_simulation(
    db_path: Path, attacker_id: str, defender_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[SimResponse]:
    """两个 canonical id + 已白名单化 options → SimResponse。

    任一 id 不存在返回 None（端点 404）；其余失败（loadout_required / 装载失败 /
    执行异常）都以 ok=False 的结构化响应返回，前端据 reason 分流。
    """
    from agent.tools import simulate_combat_resolved

    name_a = lookup_unit_name(db_path, attacker_id)
    name_d = lookup_unit_name(db_path, defender_id)
    if name_a is None or name_d is None:
        return None

    res = simulate_combat_resolved(
        {"canonical_id": attacker_id, "name_en": name_a},
        {"canonical_id": defender_id, "name_en": name_d},
        sanitize_options(options), db_path)

    fo = res.get("faction_options")
    return SimResponse(
        ok=bool(res.get("ok")),
        reason=res.get("reason"),
        note=res.get("note"),
        warning=res.get("warning"),
        attacker=res.get("attacker", name_a),
        defender=res.get("defender", name_d),
        phase=res.get("phase"),
        report=_report_out(res.get("report")),
        defender_toggles=[
            SimToggle(name=t.get("name", ""), note=t.get("note", ""),
                      parsed=t.get("parsed"))
            for t in (res.get("defender_toggles") or [])
        ],
        faction_options=SimFactionOptions(
            faction_id=fo.get("faction_id"), faction_name=fo.get("faction_name"),
            detachments=fo.get("detachments") or []) if fo else None,
        weapon_pool=res.get("weapon_pool"),
        model_tiers=res.get("model_tiers"),
        dsl_available=[
            SimDslEntry(
                table=e.get("table", ""), id=e.get("id", ""),
                side=e.get("side", "attacker"),
                name_en=e.get("name_en", ""), name_zh=e.get("name_zh"),
                status=e.get("status", ""), detachment=e.get("detachment"),
                requires_toggles=e.get("requires_toggles") or [])
            for e in (res.get("dsl_available") or [])
        ],
        errors=res.get("errors") or [],
    )
