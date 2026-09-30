"""The legacy detail fetcher must not relabel a same-name response as its request."""
import copy
import json

import pytest

from scripts import fetch_blacklibrary_details as fetcher


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return copy.deepcopy(self.payload)


class Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response(self.payload)


def source():
    return {"id": 992, "gameId": 2, "topName": "帝国特勤",
            "unitEnglishName": "Ministorum Priest",
            "unitDetail": json.dumps({"能力": [{"name": "Real captured ability"}]})}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetcher.time, "sleep", lambda _: None)


def test_verified_identity_returns_original_detail():
    captured = source()
    captured["id"] = "992"
    captured["unitEnglishName"] = "MINISTORUM-PRIEST"
    session = Session({"code": "200", "data": captured})
    detail, failed = fetcher.fetch_detail(session, "帝国特勤", "Ministorum Priest", expected_id=992)
    assert not failed
    assert detail == json.loads(captured["unitDetail"])
    assert len(session.calls) == 1
    assert session.calls[0][1]["json"] == {
        "gameId": 2, "topName": "帝国特勤", "unitName": "Ministorum Priest"}


@pytest.mark.parametrize("field,wrong", [
    ("id", 577), ("gameId", 1), ("topName", "修女会"),
    ("unitEnglishName", "Different Unit"), ("id", None), ("gameId", None),
    ("topName", None), ("unitEnglishName", None),
])
def test_wrong_identity_is_visible_failure_not_a_datasheet(field, wrong, capsys):
    captured = source()
    captured[field] = wrong
    session = Session({"code": "200", "data": captured})
    detail, failed = fetcher.fetch_detail(session, "帝国特勤", "Ministorum Priest", expected_id=992)
    assert detail is None
    assert failed
    assert len(session.calls) == 3
    assert "identity" in capsys.readouterr().out


def test_identity_is_checked_even_for_empty_body():
    captured = source()
    captured.update(id=577, topName="修女会", unitDetail="")
    assert fetcher.fetch_detail(Session({"code": 200, "data": captured}),
                                "帝国特勤", "Ministorum Priest", expected_id=992) == (None, True)


@pytest.mark.parametrize("payload", [
    {"code": "500", "data": source()}, {"code": "200"},
    {"code": "200", "data": []},
    {"code": "200", "data": dict(source(), unitDetail="[]")},
])
def test_business_or_malformed_response_is_not_success(payload):
    assert fetcher.fetch_detail(Session(payload), "帝国特勤", "Ministorum Priest",
                                expected_id=992) == (None, True)


@pytest.mark.parametrize("body", [None, ""])
def test_verified_empty_response_is_distinct_from_failure(body):
    captured = dict(source(), unitDetail=body)
    assert fetcher.fetch_detail(Session({"code": "200", "data": captured}),
                                "帝国特勤", "Ministorum Priest", expected_id=992) == (None, False)


def test_main_preserves_previous_body_on_failed_identity_and_marks_it_unverified(tmp_path, monkeypatch):
    out = tmp_path / "details.json"
    previous = {"id": 992, "name_en": "Ministorum Priest", "name_zh": "教廷牧师",
                "faction_zh": "帝国特勤", "detail": {"能力": [{"name": "Prior body"}]},
                "provenance": {"status": "verified_capture"}}
    absent = {"id": 55, "name_en": "Absent old unit", "detail": {"属性": [{"m": 6}]}}
    out.write_text(json.dumps([previous, absent]), encoding="utf-8")
    unit = dict(source(), unitName="教廷牧师", unitScore=50)
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "--out", str(out)])
    monkeypatch.setattr(fetcher, "fetch_list", lambda _: [unit])
    monkeypatch.setattr(fetcher, "new_session", lambda: object())
    calls = []

    def failure(sess, faction, name, *, expected_id):
        calls.append((faction, name, expected_id))
        return None, True

    monkeypatch.setattr(fetcher, "fetch_detail", failure)
    fetcher.main()
    rows = {row["id"]: row for row in json.loads(out.read_text(encoding="utf-8"))}
    assert rows[992]["detail"] == previous["detail"]
    assert rows[992]["provenance"]["status"] == "retained_previous_cache"
    assert rows[992]["provenance"]["reason"] == "failed"
    assert rows[55]["detail"] == absent["detail"]
    assert calls == [("帝国特勤", "Ministorum Priest", 992)]


def test_main_marks_new_verified_capture_and_retains_failed_new_record(tmp_path, monkeypatch):
    out = tmp_path / "details.json"
    units = [dict(source(), unitName="教廷牧师", unitScore=50),
             dict(source(), id=1001, unitEnglishName="Watch Captain Artemis", unitName="阿耳忒弥斯")]
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "--out", str(out)])
    monkeypatch.setattr(fetcher, "fetch_list", lambda _: units)
    monkeypatch.setattr(fetcher, "new_session", lambda: object())
    monkeypatch.setattr(fetcher, "fetch_detail", lambda *args, expected_id: (
        (json.loads(source()["unitDetail"]), False) if expected_id == 992 else (None, True)))
    fetcher.main()
    rows = {row["id"]: row for row in json.loads(out.read_text(encoding="utf-8"))}
    assert rows[992]["provenance"]["status"] == "verified_capture"
    assert rows[1001]["detail"] is None
    assert rows[1001]["detail_status"] == "failed"


def test_main_never_labels_sisters_response_as_imperial_agents(tmp_path, monkeypatch, capsys):
    """Before the guard, this real response shape overwrote the requested ID's body."""
    out = tmp_path / "details.json"
    previous = {"id": 992, "name_en": "Ministorum Priest", "faction_zh": "帝国特勤",
                "detail": {"能力": [{"name": "Previous captured body"}]}}
    out.write_text(json.dumps([previous]), encoding="utf-8")
    wrong = dict(source(), id=577, topName="修女会",
                 unitDetail=json.dumps({"能力": [{"name": "Wrong Sisters body"}]}))
    session = Session({"code": "200", "data": wrong})
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "--out", str(out)])
    monkeypatch.setattr(fetcher, "fetch_list", lambda _: [dict(source(), unitName="教廷牧师")])
    monkeypatch.setattr(fetcher, "new_session", lambda: session)
    fetcher.main()
    result = json.loads(out.read_text(encoding="utf-8"))[0]
    assert result["detail"] == previous["detail"]
    assert result["faction_zh"] == "帝国特勤"
    assert result["provenance"]["status"] == "retained_previous_cache"
    assert len(session.calls) == 3
    assert "identity" in capsys.readouterr().out
