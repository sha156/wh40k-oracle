"""web_api/simulate.py — 模拟器页签后端（BUILD-PLAN Stage 4）。

图鉴 canonical id 直调 P4/P5 模拟核心（agent.tools.simulate_combat_resolved），
免名字解析歧义；tool dict → SimResponse（camelCase 镜像，契约真源 web/src/lib/sim.ts）。
options 在边界白名单过滤 + 类型收敛（n 有上限，防把后端当算力用）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from web_api.contract import SimFactionOptions, SimReportOut, SimResponse, SimToggle

# 允许透传给模拟核心的 options 键 → 收敛函数（边界验证，未知键静默丢弃）
_N_MIN, _N_MAX = 100, 20000


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


def _as_pos_int(v: Any) -> Optional[int]:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return i if i > 0 else None


def _as_loadout(v: Any) -> Optional[List[Tuple[str, int]]]:
    """[[武器名, 数量], ...] → [(str, int>0)]；任一项非法则整体丢弃（不猜半份装配）。"""
    if not isinstance(v, list) or not v:
        return None
    out: List[Tuple[str, int]] = []
    for item in v:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            return None
        name, cnt = item
        c = _as_pos_int(cnt)
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
    # smokescreen 不在白名单：引擎里它只是 cover_on 的别名（smokescreen→cover_on），
    # 网页用 cover 开关表达即可，不重复暴露；agent 直调路径不过此白名单，仍可用 smokescreen。
    for key in ("charge", "half_range", "cover", "stationary", "long_range",
                "indirect", "stealth"):
        if key in raw:
            out[key] = _as_bool(raw[key])
    for key in ("attacker_models", "defender_models", "damage_reduction", "seed"):
        v = _as_pos_int(raw.get(key))
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
        errors=res.get("errors") or [],
    )
