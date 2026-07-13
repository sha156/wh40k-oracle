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
    assert b["totalPoints"] == 150 and b["issues"] == []


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
