"""tests/test_web_api_stage4_sim.py — Stage 4 模拟器页签后端。

覆盖：options 边界白名单（未知键丢弃/n 钳制/loadout 半份拒收）、id→name 查找、
loadout_required 流（附武器池）、带 loadout 的完整模拟（报告契约 camelCase）、
未知 id 404、simulate_combat 薄壳与 resolved 核心等价。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from web_api.simulate import (lookup_unit_name, run_simulation,
                              sanitize_options)

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"
BROADSIDE = "000000433"   # Broadside Battlesuits：多武器 → 未给 loadout 必 ambiguous

needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="wh40k.sqlite 不存在")


# ── options 边界白名单 ────────────────────────────────────────────

def test_sanitize_whitelist_and_types():
    out = sanitize_options({
        "phase": "melee", "charge": 1, "cover": True, "fnp": "5",
        "attacker_models": "3", "n": 999999, "seed": 42,
        "evil_key": "rm -rf", "loadout": [["Heavy rail rifle", 3]],
    })
    assert out["phase"] == "melee" and out["charge"] is True
    assert out["fnp"] == 5 and out["attacker_models"] == 3
    assert out["n"] == 20000          # 钳上限
    assert out["seed"] == 42
    assert out["loadout"] == [("Heavy rail rifle", 3)]
    assert "evil_key" not in out


def test_sanitize_rejects_bad_values():
    out = sanitize_options({
        "phase": "psychic",            # 非法枚举 → 丢
        "fnp": 9,                       # 超 2-6 → 丢
        "attacker_models": -2,          # 非正 → 丢
        "n": 1,                         # 钳下限
        "loadout": [["gun", 0]],        # 数量非正 → 整体拒收
    })
    assert "phase" not in out and "fnp" not in out
    assert "attacker_models" not in out
    assert out["n"] == 100
    assert "loadout" not in out


def test_sanitize_empty():
    assert sanitize_options(None) == {}
    assert sanitize_options({}) == {}


def test_sanitize_bool_coercion_no_string_footgun():
    # 字符串 "false"/"0" 不当真值（避免 bool("false")==True）
    assert sanitize_options({"charge": "false"})["charge"] is False
    assert sanitize_options({"cover": "0"})["cover"] is False
    assert sanitize_options({"stationary": "true"})["stationary"] is True
    assert sanitize_options({"charge": 1})["charge"] is True
    assert sanitize_options({"cover": 0})["cover"] is False


def test_sanitize_drops_smokescreen():
    # smokescreen 不在网页白名单（引擎里等同 cover 别名，用 cover 表达）
    assert "smokescreen" not in sanitize_options({"smokescreen": True})
    assert sanitize_options({"cover": True})["cover"] is True


def test_sanitize_dsl_keys():
    # P7-PR3：detachment(str) / detachment_rounds(bool) / stratagems(list[str]) 白名单
    out = sanitize_options({
        "guided": True, "markerlight_observer": "true", "detachment_rounds": 1,
        "detachment": "  Mont'ka  ", "stratagems": ["集中火力", " 抵近伏击 ", 42, ""],
    })
    assert out["guided"] is True and out["markerlight_observer"] is True
    assert out["detachment_rounds"] is True
    assert out["detachment"] == "Mont'ka"
    assert out["stratagems"] == ["集中火力", "抵近伏击"]   # 非 str/空串滤掉
    # 非法形状丢弃；条数上限 16
    assert "detachment" not in sanitize_options({"detachment": 42})
    assert "stratagems" not in sanitize_options({"stratagems": "集中火力"})
    assert len(sanitize_options({"stratagems": [f"s{i}" for i in range(30)]})
               ["stratagems"]) == 16


@needs_db
def test_run_simulation_dsl_available_echo():
    # PR3 认领项：dsl_available 不再在 web 边界被丢——钛帝国单位应回显条目清单
    strike = None
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT id FROM units WHERE name_en='Strike Team'").fetchone()
    conn.close()
    strike = row[0]
    res = run_simulation(DB_PATH, strike, BROADSIDE,
                         {"loadout": [["Pulse rifle", 10]], "n": 100})
    assert res is not None and res.ok
    ids = {e.id for e in res.dsl_available}
    assert "000008439" in ids            # FTGG 军规
    assert "det000008441" in ids         # Patient Hunter（物化分队规则行）
    assert "000008812004" in ids         # Focused Fire 战略
    cte = next(e for e in res.dsl_available if e.id == "det000008441")
    assert cte.detachment == "Kauyon" and cte.requires_toggles == ["detachment_rounds"]
    # camelCase 契约（sim.ts 镜像）
    dumped = res.model_dump(by_alias=True)
    assert "dslAvailable" in dumped
    assert {"table", "id", "nameEn", "nameZh", "status", "detachment",
            "requiresToggles"} <= set(dumped["dslAvailable"][0])


def test_sanitize_reverse_keys():
    out = sanitize_options({
        "reverse": True, "reverse_phase": "melee",
        "defender_loadout": [["Crushing bulk", 1]],
    })
    assert out["reverse"] is True
    assert out["reverse_phase"] == "melee"
    assert out["defender_loadout"] == [("Crushing bulk", 1)]
    # 非法 reverse_phase 丢弃、守方 loadout 半份整体拒收
    assert "reverse_phase" not in sanitize_options({"reverse_phase": "psychic"})
    assert "defender_loadout" not in sanitize_options(
        {"defender_loadout": [["gun", 0]]})


# ── id → name 查找 ────────────────────────────────────────────────

@needs_db
def test_lookup_unit_name():
    assert lookup_unit_name(DB_PATH, BROADSIDE) == "Broadside Battlesuits"
    assert lookup_unit_name(DB_PATH, "999999999") is None


@needs_db
def test_run_simulation_unknown_id_returns_none():
    assert run_simulation(DB_PATH, "999999999", BROADSIDE) is None
    assert run_simulation(DB_PATH, BROADSIDE, "999999999") is None


# ── loadout_required 流 ───────────────────────────────────────────

@needs_db
def test_run_simulation_loadout_required_surfaces_pool():
    resp = run_simulation(DB_PATH, BROADSIDE, BROADSIDE, {})
    assert resp is not None and resp.ok is False
    assert resp.reason == "loadout_required"
    assert resp.weapon_pool and "Heavy rail rifle" in resp.weapon_pool
    assert resp.model_tiers    # points 档位（选模型数用）
    d = resp.model_dump(by_alias=True)
    assert "weaponPool" in d and "modelTiers" in d   # camelCase 契约


# ── 完整模拟（带 loadout）─────────────────────────────────────────

@needs_db
def test_run_simulation_full_report_contract():
    resp = run_simulation(
        DB_PATH, BROADSIDE, BROADSIDE,
        {"loadout": [["Heavy rail rifle", 1]], "stationary": True,
         "n": 2000, "seed": 7},
    )
    assert resp is not None and resp.ok is True, resp.note
    assert resp.attacker == "Broadside Battlesuits"
    rep = resp.report
    assert rep is not None and rep.iterations == 2000 and rep.seed == 7
    assert rep.expected_damage > 0
    # 漏斗单调收窄（attacks ≥ hits ≥ wounds ≥ unsaved）
    f = rep.funnel
    assert f["attacks"] >= f["hits"] >= f["wounds"] >= f["unsaved"]
    # 分布：分位 + 直方图概率和 ≈ 1
    dist = rep.distribution
    assert "p50" in dist and "histogram" in dist
    assert abs(sum(dist["histogram"].values()) - 1.0) < 0.02
    # 诚实披露字段存在（守方开关只 surface 不施加）
    assert isinstance(resp.defender_toggles, list)
    assert resp.faction_options and resp.faction_options.faction_id == "TAU"
    # camelCase 契约
    d = resp.model_dump(by_alias=True)
    assert "expectedDamage" in d["report"] and "wipeProbability" in d["report"]
    assert "notModeled" in d["report"] and "factionOptions" in d


# ── 守方反打（reverse）流 ─────────────────────────────────────────

@needs_db
def test_run_simulation_reverse_needs_defender_loadout():
    """reverse=True + 守方多武器未指明 loadout → defender_loadout_required（不静默退回单向）。"""
    resp = run_simulation(DB_PATH, BROADSIDE, BROADSIDE, {
        "loadout": [["Heavy rail rifle", 1]], "reverse": True, "n": 300})
    assert resp is not None and resp.ok is False
    assert resp.reason == "defender_loadout_required"
    assert resp.weapon_pool and "Crushing bulk" in resp.weapon_pool


@needs_db
def test_run_simulation_reverse_full_report():
    """给齐攻/守 loadout → 串行幸存反打，report.reverse 非空。"""
    resp = run_simulation(DB_PATH, BROADSIDE, BROADSIDE, {
        "loadout": [["Heavy rail rifle", 1]], "reverse": True,
        "defender_loadout": [["Crushing bulk", 1]], "reverse_phase": "melee",
        "n": 500, "seed": 7})
    assert resp is not None and resp.ok is True, resp.note
    assert resp.report is not None and resp.report.reverse is not None
    # camelCase 契约：reverse 也镜像
    d = resp.model_dump(by_alias=True)
    assert d["report"]["reverse"]["expectedDamage"] >= 0


@needs_db
def test_run_simulation_same_options_same_seed_deterministic():
    opts = {"loadout": [["Heavy rail rifle", 1]], "n": 1000, "seed": 99}
    r1 = run_simulation(DB_PATH, BROADSIDE, BROADSIDE, dict(opts))
    r2 = run_simulation(DB_PATH, BROADSIDE, BROADSIDE, dict(opts))
    assert r1.report.expected_damage == r2.report.expected_damage
    assert r1.report.distribution == r2.report.distribution


# ── 薄壳等价：simulate_combat（名字解析）与 resolved 核心同报告 ────

@needs_db
def test_simulate_combat_wrapper_equivalent_to_resolved_core():
    from agent.tools import simulate_combat, simulate_combat_resolved

    opts = {"loadout": [["Heavy rail rifle", 1]], "n": 1000, "seed": 5}
    by_name = simulate_combat("Broadside Battlesuits", "Broadside Battlesuits",
                              dict(opts), db_path=DB_PATH)
    by_id = simulate_combat_resolved(
        {"canonical_id": BROADSIDE, "name_en": "Broadside Battlesuits"},
        {"canonical_id": BROADSIDE, "name_en": "Broadside Battlesuits"},
        dict(opts), db_path=DB_PATH)
    assert by_name["ok"] and by_id["ok"]
    assert by_name["report"] == by_id["report"]


# ── FastAPI 端点 ──────────────────────────────────────────────────

@needs_db
def test_endpoint_simulate_ok_and_404():
    from fastapi.testclient import TestClient
    from web_api.main import app

    client = TestClient(app)
    r = client.post("/simulate", json={
        "attackerId": BROADSIDE, "defenderId": BROADSIDE,
        "options": {"loadout": [["Heavy rail rifle", 1]], "n": 500},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["report"]["expectedDamage"] > 0
    # 未知 id → 404
    r2 = client.post("/simulate", json={
        "attackerId": "999999999", "defenderId": BROADSIDE})
    assert r2.status_code == 404


@needs_db
def test_endpoint_simulate_busy_returns_503():
    """并发信号量占满 → 繁忙 503（而非 db-missing 503）。"""
    from fastapi.testclient import TestClient
    from web_api import main

    client = TestClient(main.app)
    acquired = [main._SIM_SEMAPHORE.acquire(blocking=False)
                for _ in range(main._SIM_MAX_CONCURRENCY)]
    try:
        r = client.post("/simulate", json={
            "attackerId": BROADSIDE, "defenderId": BROADSIDE,
            "options": {"loadout": [["Heavy rail rifle", 1]], "n": 100}})
        assert r.status_code == 503
        assert "繁忙" in r.json()["detail"]
    finally:
        for ok in acquired:
            if ok:
                main._SIM_SEMAPHORE.release()
