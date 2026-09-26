"""Public-source snapshots reconcile coverage and never silently turn errors into empties."""
import copy
import json

import pytest
import requests

from scripts.fetch_blacklibrary_snapshot import (
    BASE_URL, CATALOGS, DETAIL_PATH, LIST_PATH, POWER_PATH, RULE_PATH,
    Snapshot, SourceError, sanitize,
)


def unit(identity=1, faction="星际战士", inline=False):
    return {"id": identity, "gameId": 2, "topName": faction, "unitName": "单位" + str(identity),
            "unitEnglishName": "Unit " + str(identity), "unitScore": 100,
            "unitDetail": json.dumps({"能力": [{"name": "A", "text": "Real source text"}]}) if inline else "",
            "userId": "private-account", "keywords": ["INFANTRY"], "weapons": [{"name": "bolter"}]}


def envelope(data, **extra):
    return {"code": "200", "data": data, **extra}


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return copy.deepcopy(self.data)


class Session:
    def __init__(self, units=None, override=None):
        self.units = units if units is not None else [unit()]
        self.override = override
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(("GET", url, None))
        if url == CATALOGS["40k-factions"]:
            return Response([{"种族名称": "星际战士"}, {"种族名称": "无单位阵营"}])
        if url == CATALOGS["40k-universal-rules"]:
            return Response([{"cName": "致命命中", "eName": "Lethal Hits", "desc": "Source rule"}])
        return Response([{"阵营": "秩序", "种族列表": []}])

    def post(self, url, json, timeout):
        path = url.removeprefix(BASE_URL)
        self.calls.append(("POST", path, json))
        if self.override:
            value = self.override(path, json)
            if value is not None:
                return Response(value)
        if path == LIST_PATH:
            page = json["pageNum"]
            return Response(envelope(self.units[(page-1)*50:page*50], totalCount=len(self.units),
                                     currentPageNo=page, pageLength=max(1, (len(self.units)+49)//50)))
        if path == DETAIL_PATH:
            listed = next(u for u in self.units if u["unitEnglishName"] == json["unitName"])
            result = copy.deepcopy(listed)
            result["unitDetail"] = '{"属性":[{"m":"6"}],"能力":[{"name":"A"}]}'
            return Response(envelope(result))
        if path == RULE_PATH:
            return Response(envelope({"gameId": 2, "topName": json["topName"], "content": "Source rules",
                                      "subDTOSN": [{"content": "Detachment", "userId": "private-account"}]}))
        if path == POWER_PATH:
            return Response(envelope([]))
        raise AssertionError(path)


def snapshot(tmp_path, session):
    return Snapshot(tmp_path / "snapshot", session=session, interval=0, sleep=lambda _: None)


def test_complete_snapshot_has_details_catalog_only_faction_and_redacted_raw_envelopes(tmp_path):
    session = Session()
    snap = snapshot(tmp_path, session)
    result = snap.run()
    assert result["status"] == "complete_known_endpoints"
    assert result["counts"] == {"units": 1, "factions": 2, "details": 1,
                                "details_with_content": 1, "details_source_empty": 0, "details_failed": 0}
    assert any(call[1] == RULE_PATH and call[2]["topName"] == "无单位阵营" for call in session.calls)
    assert not session.trust_env
    details = json.loads((snap.out / "details.json").read_text(encoding="utf-8"))
    assert details[0]["detail"]["属性"][0]["m"] == "6"
    assert details[0]["score"] == 100
    assert set(("id", "faction_zh", "name_zh", "name_en", "score", "detail")) <= details[0].keys()
    all_json = "".join(path.read_text(encoding="utf-8") for path in snap.out.rglob("*.json"))
    assert "private-account" not in all_json
    assert "Detachment" in all_json and "bolter" in all_json
    assert len([call for call in session.calls if call[1] == DETAIL_PATH]) == 1


def test_sanitize_recurses_into_embedded_detail_but_keeps_game_ids_and_text():
    raw = {"userId": "secret", "id": 6, "gameId": 2, "unitDetail": json.dumps({
        "能力": [{"name": "Rule", "userHead": "private-avatar", "text": "Actual rule"}],
        "managerUserId": "secret", "nested": {"authorization": "secret"}})}
    clean = sanitize(raw)
    assert clean["id"] == 6 and clean["gameId"] == 2
    assert "secret" not in json.dumps(clean) and "private-avatar" not in json.dumps(clean)
    assert json.loads(clean["unitDetail"])["能力"][0]["text"] == "Actual rule"
    assert "userId" in raw  # Do not mutate caller-owned source data.


def test_totalcount_paginates_and_reconciles_every_identity(tmp_path):
    session = Session([unit(i, inline=True) for i in range(51)])
    snap = snapshot(tmp_path, session)
    assert len(snap.fetch_units()) == 51
    assert [c[2]["pageNum"] for c in session.calls] == [1, 2]
    assert snap.manifest["unit_list_reconciled"] is True


@pytest.mark.parametrize("breakage", ["duplicate", "short_page", "missing_total", "changed_total"])
def test_broken_inventory_never_claims_complete(tmp_path, breakage):
    units = [unit(i, inline=True) for i in range(51)]
    def override(path, payload):
        if path != LIST_PATH:
            return None
        page = payload["pageNum"]
        records = units[(page-1)*50:page*50]
        result = envelope(records, totalCount=51, currentPageNo=page, pageLength=2)
        if breakage == "duplicate" and page == 2:
            result["data"] = [units[0]]
        if breakage == "short_page" and page == 1:
            result["data"] = records[:-1]
        if breakage == "missing_total":
            result.pop("totalCount")
            result["total"] = 51  # The observed contract specifically uses totalCount.
        if breakage == "changed_total" and page == 2:
            result["totalCount"] = 52
        return result
    snap = snapshot(tmp_path, Session(units, override))
    result = snap.run()
    assert result["status"] == "partial" and not result["unit_list_reconciled"]
    assert any(entry["status"] == "failed" for entry in result["requests"].values())
    assert not (snap.out / "details.json").exists()


def test_powers_keeps_all_returned_rows_without_blind_pagination(tmp_path):
    powers = [{"id": i, "gameId": 2, "topName": "星际战士", "effect": "Rule"} for i in range(1001)]
    session = Session(override=lambda path, payload: envelope(powers) if path == POWER_PATH else None)
    snap = snapshot(tmp_path, session)
    rows = snap.fetch_factions(["星际战士"])
    assert rows[1]["records"] == 1001
    assert len([c for c in session.calls if c[1] == POWER_PATH]) == 1
    saved = json.loads((snap.out / ("raw/" + rows[1]["source_capture"] + ".json")).read_text(encoding="utf-8"))
    assert len(saved["envelope"]["data"]) == 1001


@pytest.mark.parametrize("data,status", [(None, "source_empty"), (unit(999), "failed")])
def test_detail_source_empty_is_distinct_from_wrong_identity(tmp_path, data, status):
    session = Session(override=lambda path, payload: envelope(data) if path == DETAIL_PATH else None)
    snap = snapshot(tmp_path, session)
    result = snap.run()
    details = json.loads((snap.out / "details.json").read_text(encoding="utf-8"))
    assert details[0]["detail_status"] == status and details[0]["detail"] is None
    assert result["status"] == ("partial" if status == "failed" else "complete_known_endpoints")


def test_bounded_retry_resume_fetches_only_failed_capture(tmp_path):
    def fail_details(path, payload):
        if path == DETAIL_PATH:
            raise requests.ConnectionError("credential-like text must not be saved")
    first_session = Session(override=fail_details)
    first = snapshot(tmp_path, first_session)
    assert first.run()["status"] == "partial"
    assert sum(call[1] == DETAIL_PATH for call in first_session.calls) == 3
    assert "credential-like" not in (first.out / "manifest.json").read_text(encoding="utf-8")
    second_session = Session()
    resumed = snapshot(tmp_path, second_session)
    assert resumed.run()["status"] == "complete_known_endpoints"
    assert len(second_session.calls) == 1 and second_session.calls[0][1] == DETAIL_PATH


def test_resume_refetches_tampered_capture(tmp_path):
    first = snapshot(tmp_path, Session())
    first.fetch_units()
    raw = first.out / "raw/unit-list/page-001.json"
    raw.write_text("{}", encoding="utf-8")
    session = Session()
    resumed = snapshot(tmp_path, session)
    assert len(resumed.fetch_units()) == 1
    assert len(session.calls) == 1


def test_disappeared_deleted_cache_is_retained_separately_and_never_relabelled_current(tmp_path):
    cache = tmp_path / "old-details.json"
    old = [{"id": 6, "name_zh": "卡尔加（已删除）", "name_en": "Marneus Calgar", "score": 200,
            "detail": {"能力": ["Old rule"]}, "userId": "private-account"},
           {"id": 7, "name_zh": "Not marked deleted", "score": 250}]
    cache.write_text(json.dumps(old), encoding="utf-8")
    before = cache.read_bytes()
    snap = snapshot(tmp_path, Session())
    snap.run([cache])
    retained = json.loads((snap.out / "historical_deleted_details.json").read_text(encoding="utf-8"))
    assert len(retained) == 1 and retained[0]["record"]["score"] == 200
    assert retained[0]["status"] == "historical_source_only" and retained[0]["is_current"] is False
    assert cache.read_bytes() == before
    details = json.loads((snap.out / "details.json").read_text(encoding="utf-8"))
    assert [row["id"] for row in details] == [1]


@pytest.mark.parametrize("code,text,expected", [
    ("1010", "数据不存在", "source_empty"),
    ("1010", "Unknown business error", "failed"),
    ("500", "数据不存在", "failed"),
])
def test_only_observed_missing_army_rule_response_is_source_empty(tmp_path, code, text, expected):
    session = Session(override=lambda path, payload: {
        "code": code, "text": text, "data": None} if path == RULE_PATH else None)
    snap = snapshot(tmp_path, session)
    rows = snap.fetch_factions(["星际战士"])
    assert rows[0]["status"] == expected
    assert sum(call[1] == RULE_PATH for call in session.calls) == (1 if expected == "source_empty" else 3)


def test_output_cannot_overwrite_canonical_cache_root(tmp_path, monkeypatch):
    from scripts import fetch_blacklibrary_snapshot as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    cache = tmp_path / "db_sources/blacklibrary"
    cache.mkdir(parents=True)
    details = cache / "details.json"
    details.write_text('[{"id":6,"score":200}]', encoding="utf-8")
    before = details.read_bytes()
    with pytest.raises(SourceError, match="canonical"):
        Snapshot(cache, session=Session())
    assert details.read_bytes() == before and not (cache / "manifest.json").exists()
