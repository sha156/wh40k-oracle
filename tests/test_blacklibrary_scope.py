"""Empty product/source listings are separate from missing valid datasheets."""
import json

import pytest

from db_compile import blacklibrary_scope as scope
from db_compile.blacklibrary_snapshot import merge_snapshot
from scripts.fetch_blacklibrary_snapshot import DETAIL_PATH, digest, encode
from tests.test_blacklibrary_snapshot import Session, snapshot, unit


def reviewed(tmp_path, monkeypatch):
    box = unit(2743)
    box.pop("userId")  # Policies fingerprint the sanitized public inventory.
    box.update(unitName="先驱者小队", unitEnglishName="", unitScore=None)
    path = tmp_path / "policy.json"
    path.write_bytes(encode({"schema_version": 1, "records": [{
        "id": "2743", "reason": "duplicate_listing",
        "inventory_sha256": digest(encode(box)), "full_detail_source_ids": [69]}]}))
    monkeypatch.setattr(scope, "POLICY", path)
    return box


def test_ignore_box_but_capture_full_card_with_same_chinese_name(tmp_path, monkeypatch):
    box = reviewed(tmp_path, monkeypatch)
    full = unit(69)
    full.update(unitName=box["unitName"], unitEnglishName="INCEPTOR SQUAD")
    session = Session([box, full])
    snap = snapshot(tmp_path, session)
    result = snap.run()
    assert result["counts"]["details_ignored"] == 1
    assert result["counts"]["details_with_content"] == 1
    assert result["counts"]["details_failed"] == 0
    assert len([c for c in session.calls if c[1] == DETAIL_PATH]) == 1
    merged, _, report = merge_snapshot(snap.out, [])
    assert [r["id"] for r in merged] == [69]
    assert report["not_imported"] == ["2743"]


@pytest.mark.parametrize("field,value", [
    ("id", 99), ("topName", "Other faction"), ("unitName", "New name"),
    ("unitScore", 120), ("unitEnglishName", "INCEPTOR SQUAD"),
    ("unitDetail", '{"能力":[{"name":"New rule"}]}'),
    ("detailPic", "https://example.test/new-rule.png"),
])
def test_any_inventory_change_reopens_review(tmp_path, monkeypatch, field, value):
    box = reviewed(tmp_path, monkeypatch)
    assert scope.reviewed_empty_listing(box)
    changed = dict(box, **{field: value})
    assert scope.reviewed_empty_listing(changed) is None


def test_new_source_detail_is_captured_after_previous_exclusion(tmp_path, monkeypatch):
    box = reviewed(tmp_path, monkeypatch)
    snap = snapshot(tmp_path, Session([box]))
    assert snap.fetch_details([box])[0]["detail_status"] == "ignored_empty_listing"
    changed = dict(box, unitDetail='{"能力":[{"name":"Real rule"}]}')
    assert snap.fetch_details([changed])[0]["detail_status"] == "captured"


def test_unknown_empty_listing_remains_failure(tmp_path, monkeypatch):
    box = reviewed(tmp_path, monkeypatch)
    changed = dict(box, id=99)
    snap = snapshot(tmp_path, Session([changed]))
    assert snap.fetch_details([changed])[0]["detail_status"] == "failed"


def test_exclusion_cannot_be_forged_in_compiled_snapshot(tmp_path, monkeypatch):
    reviewed(tmp_path, monkeypatch)
    snap = snapshot(tmp_path, Session())
    snap.run()
    rows = json.loads((snap.out / "details.json").read_text(encoding="utf-8"))
    rows[0]["detail_status"] = "ignored_empty_listing"
    snap.output("details.json", rows)
    snap.checkpoint()
    with pytest.raises(ValueError, match="reviewed policy"):
        merge_snapshot(snap.out, [])


def test_policy_accounts_for_all_reviewed_records():
    policy = json.loads(scope.POLICY.read_text(encoding="utf-8"))
    rows = policy["records"]
    assert len(rows) == len({r["id"] for r in rows}) == 94
    assert {reason: sum(r["reason"] == reason for r in rows) for reason in
            ("duplicate_listing", "empty_legends", "empty_listing")} == {
        "duplicate_listing": 49, "empty_legends": 36, "empty_listing": 9}
    inceptor = next(r for r in rows if r["id"] == "2743")
    assert inceptor["full_detail_source_ids"] == [69]
