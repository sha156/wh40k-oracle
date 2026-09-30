"""Promotion verifies raw identities and preserves data during a partial crawl."""
import copy
import json

import pytest

from db_compile.blacklibrary_snapshot import checked_json, merge_snapshot, sha
from tests.test_blacklibrary_snapshot import Session, snapshot, unit, envelope, DETAIL_PATH


def existing(identity=1):
    return {"id": identity, "name_en": "Unit " + str(identity), "name_zh": "Old name",
            "faction_zh": "星际战士", "score": 99, "detail": {"能力": [{"name": "Old"}]}}


def rewrite_output(snap, name, rows):
    snap.output(name, rows)
    snap.checkpoint()


def test_valid_merge_retains_absent_records_and_does_not_mutate_input(tmp_path):
    snap = snapshot(tmp_path, Session())
    snap.run()
    prior = [existing(), existing(2)]
    original = copy.deepcopy(prior)
    rows, units, report = merge_snapshot(snap.out, prior)
    assert prior == original
    assert len(rows) == 2 and len(units) == 1
    assert report["changed"] == ["1"]
    assert report["retained_previous"] == ["2"]
    assert rows[1]["detail"] == prior[1]["detail"]
    assert rows[1]["provenance"]["reason"] == "absent_from_inventory"
    assert rows[0]["provenance"]["status"] == "verified_capture"


@pytest.mark.parametrize("mode", ["empty", "wrong_id", "missing_name"])
def test_failed_or_empty_capture_never_erases_existing_detail(tmp_path, mode):
    u = unit()
    if mode == "missing_name":
        u["unitEnglishName"] = ""
    def override(path, payload):
        if path == DETAIL_PATH:
            return envelope(None if mode == "empty" else unit(99, inline=True))
    snap = snapshot(tmp_path, Session([u], override))
    snap.run()
    rows, _, report = merge_snapshot(snap.out, [existing()])
    assert report["accepted"] == 0 and report["not_imported"] == ["1"]
    assert rows[0]["detail"] == existing()["detail"]


@pytest.mark.parametrize("tamper", ["output", "raw", "compiled_identity", "compiled_inventory"])
def test_corruption_or_identity_substitution_is_rejected(tmp_path, tamper):
    snap = snapshot(tmp_path, Session())
    snap.run()
    if tamper in ("output", "raw"):
        path = snap.out / "details.json" if tamper == "output" else next((snap.out / "raw/unit-details").glob("*.json"))
        path.write_bytes(path.read_bytes() + b" ")
    elif tamper == "compiled_identity":
        rows = json.loads((snap.out / "details.json").read_text("utf-8"))
        rows[0]["name_en"] = "Wrong unit"
        rewrite_output(snap, "details.json", rows)
    else:
        rows = json.loads((snap.out / "units.json").read_text("utf-8"))
        rows[0]["unitName"] = "Wrong unit"
        rewrite_output(snap, "units.json", rows)
    with pytest.raises(ValueError):
        merge_snapshot(snap.out, [existing()])


def test_inline_capture_and_new_record(tmp_path):
    snap = snapshot(tmp_path, Session([unit(inline=True)]))
    snap.run()
    rows, _, report = merge_snapshot(snap.out, [])
    assert len(rows) == 1 and report["added"] == ["1"]


def test_snapshot_cannot_read_outside_directory(tmp_path):
    raw = b"[]"
    (tmp_path / "outside.json").write_bytes(raw)
    root = tmp_path / "snapshot"
    root.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        checked_json(root, "../outside.json", sha(raw))


def test_duplicate_previous_source_id_rejected(tmp_path):
    snap = snapshot(tmp_path, Session())
    snap.run()
    with pytest.raises(ValueError, match="Duplicate"):
        merge_snapshot(snap.out, [existing(), existing()])
