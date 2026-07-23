"""tests/test_web_api_roster.py — 军表实验室后端（Stage 4 / P6-PR3）。

覆盖：loadout 收敛（纯）、detachments/enhancements/weapons 查询、validate（camelCase 契约、
合法/非法）、critique（装配评估 + 未装配 surface、camelCase）、未知单位 404。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from web_api.contract import RosterIn
from web_api.roster import _to_loadout

DB = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"
needs_db = pytest.mark.skipif(not DB.exists(), reason="wh40k.sqlite 不存在")

INTERCESSOR = "000001157"
APOTHECARY = "000000060"
DET_BASTION = "000001130"
ENH = "Eye of the Primarch"


# ── 纯逻辑：loadout 收敛 ───────────────────────────────────────────

def test_to_loadout_coercion():
    assert _to_loadout([["Bolt rifle", 5]]) == (("Bolt rifle", 5),)
    assert _to_loadout([["Gun", "3"]]) == (("Gun", 3),)     # 字符串数字收敛
    assert _to_loadout([]) == ()
    assert _to_loadout([["Gun", 0]]) == ()                  # 非正 → 整体拒收
    assert _to_loadout([["Gun"]]) == ()                     # 半份 → 拒收
    assert _to_loadout([["", 2]]) == ()                     # 空名 → 拒收
    # 同名武器合并求和（防客户端追加行 → 引擎双计伤害）
    assert _to_loadout([["Bolt rifle", 1], ["Bolt rifle", 2]]) == (("Bolt rifle", 3),)


def test_to_loadout_caps_dos_levers():
    # gnhf 审查模块 7 HIGH：点评的蒙特卡洛数组宽度随武器数扩张，无上限即 DoS 面
    assert _to_loadout([["Gun", 10**9]]) == ()               # 单件数量超限 → 拒收
    assert _to_loadout([[f"g{i}", 1] for i in range(41)]) == ()   # 行数超限 → 拒收
    # 合并后总量超限同样拒收（防拆行绕过单件上限）
    assert _to_loadout([["Gun", 300], ["Gun", 300]]) == ()
    # 负向成对：合法装配不受影响
    assert _to_loadout([["Gun", 60], ["Blade", 2]]) == (("Gun", 60), ("Blade", 2))


def test_roster_contract_caps():
    # 契约层边界：models 超上限 / units 超上限 → 422 拒收（不静默钳）
    import pydantic
    from web_api.contract import RosterUnitIn
    with pytest.raises(pydantic.ValidationError):
        RosterUnitIn(canonicalId="000000001", models=10**9)
    with pytest.raises(pydantic.ValidationError):
        RosterIn(factionId="SM", units=[
            RosterUnitIn(canonicalId=f"{i:09d}") for i in range(61)])
    # 负向成对：合法规模通过
    assert RosterUnitIn(canonicalId="000000001", models=20).models == 20
    assert len(RosterIn(factionId="SM", units=[
        RosterUnitIn(canonicalId=f"{i:09d}") for i in range(40)]).units) == 40


def _client():
    from fastapi.testclient import TestClient
    from web_api.main import app
    return TestClient(app)


# ── 查询端点 ──────────────────────────────────────────────────────

@needs_db
def test_detachments_and_enhancements():
    c = _client()
    r = c.get("/roster/detachments", params={"faction": "SM"})
    assert r.status_code == 200 and len(r.json()["detachments"]) > 10
    assert {"id", "name"} <= set(r.json()["detachments"][0].keys())
    e = c.get("/roster/enhancements", params={"detachment": DET_BASTION})
    names = {x["name"] for x in e.json()["enhancements"]}
    assert ENH in names


@needs_db
def test_weapons_endpoint_and_404():
    c = _client()
    assert len(c.get(f"/roster/units/{INTERCESSOR}/weapons").json()["weaponPool"]) > 0
    assert c.get("/roster/units/999999999/weapons").status_code == 404


# ── validate ──────────────────────────────────────────────────────

@needs_db
def test_validate_legal_and_camelcase():
    c = _client()
    r = c.post("/roster/validate", json={
        "factionId": "SM", "detachmentId": DET_BASTION, "size": "strike_force",
        "units": [
            {"canonicalId": APOTHECARY, "nameEn": "Apothecary Biologis",
             "models": 1, "isWarlord": True, "enhancement": ENH},
            {"canonicalId": INTERCESSOR, "nameEn": "Intercessor Squad", "models": 5},
        ]})
    b = r.json()
    assert r.status_code == 200 and b["legal"] is True
    # 70 + 80 + 强化 10——强化点数计入总分（模块 3 审查 F1）
    assert b["totalPoints"] == 160 and b["issues"] == []


@needs_db
def test_validate_illegal_surfaces_issues():
    c = _client()
    # 0 warlord + 错强化
    r = c.post("/roster/validate", json={
        "factionId": "SM", "detachmentId": DET_BASTION,
        "units": [{"canonicalId": APOTHECARY, "nameEn": "Apo", "models": 1,
                   "enhancement": "NotReal"}]})
    b = r.json()
    assert b["legal"] is False
    codes = {i["code"] for i in b["issues"]}
    assert "warlord_count" in codes and "enh_wrong_detachment" in codes
    # camelCase 契约
    assert "surfacedOnly" in b["issues"][0]


# ── critique ──────────────────────────────────────────────────────

@needs_db
def test_critique_assessed_and_surfaced():
    c = _client()
    r = c.post("/roster/critique", json={
        "factionId": "SM", "detachmentId": DET_BASTION,
        "units": [
            {"canonicalId": INTERCESSOR, "nameEn": "Intercessor Squad",
             "models": 5, "loadout": [["Bolt rifle", 5]]},
            {"canonicalId": APOTHECARY, "nameEn": "Apothecary Biologis",
             "models": 1, "isWarlord": True},          # 无 loadout
        ]})
    b = r.json()
    assert r.status_code == 200 and b["totalPoints"] == 150
    by_name = {a["nameEn"]: a for a in b["assessments"]}
    assert by_name["Intercessor Squad"]["assessed"] is True
    assert len(by_name["Intercessor Squad"]["scores"]) == 4
    assert "damagePer100" in by_name["Intercessor Squad"]["scores"][0]  # camelCase
    assert by_name["Apothecary Biologis"]["assessed"] is False
    assert "notModeled" in b and len(b["notModeled"]) > 0
