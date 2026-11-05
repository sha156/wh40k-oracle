"""Promotion verifies raw identities and preserves data during a partial crawl."""
import copy
import json
from pathlib import Path

import pytest
import requests

from db_compile.blacklibrary_snapshot import checked_json, merge_snapshot, sha
from tests.test_blacklibrary_snapshot import (
    CATALOGS, DETAIL_PATH, POWER_PATH, RULE_PATH, Session, envelope, snapshot, unit,
)


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


BOUNDARY_ERROR = "Snapshot manifest or required outputs are incomplete or invalid"


def assert_boundary_rejected(snap, prior):
    original = copy.deepcopy(prior)
    before = {p.relative_to(snap.out): p.read_bytes() for p in snap.out.rglob("*") if p.is_file()}
    with pytest.raises(ValueError) as caught:
        merge_snapshot(snap.out, prior)
    assert str(caught.value) == BOUNDARY_ERROR
    assert prior == original
    assert before == {p.relative_to(snap.out): p.read_bytes() for p in snap.out.rglob("*") if p.is_file()}


def test_actual_partial_run_without_details_is_rejected(tmp_path, monkeypatch):
    snap = snapshot(tmp_path, Session())
    replace = Path.replace

    def deny_details(path, target):
        if target == snap.out / "details.json":
            raise PermissionError(13, "private-account Bearer secret", str(target))
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", deny_details)
    result = snap.run()
    assert result["status"] == "partial" and result["error"] == "PermissionError"
    assert result["unit_list_reconciled"] is True
    assert "details.json" not in result["outputs"]
    assert not (snap.out / "details.json").exists()
    assert_boundary_rejected(snap, [existing()])


@pytest.mark.parametrize("problem", [
    "non_object", "missing_outputs", "outputs_not_object", "missing_units", "missing_details",
    "unexpected_output", "output_meta_not_object", "missing_hash", "hash_not_string", "bad_hash",
    "missing_count", "boolean_count", "negative_count", "string_count", "float_count",
    "extra_metadata", "missing_expected", "boolean_expected", "negative_expected", "string_expected",
    "boolean_schema", "boolean_game", "missing_requests", "requests_not_object", "request_not_object",
    "missing_file", "invalid_json", "output_not_list", "row_not_object", "count_mismatch",
    "detail_keyset", "truncated_json", "missing_manifest",
])
def test_malformed_or_incomplete_output_contract_is_rejected(tmp_path, problem):
    snap = snapshot(tmp_path, Session())
    assert snap.run()["status"] == "complete_known_endpoints"
    manifest = snap.manifest
    meta = manifest["outputs"]["details.json"]
    if problem == "non_object":
        manifest = []
    elif problem == "missing_outputs":
        del manifest["outputs"]
    elif problem == "outputs_not_object":
        manifest["outputs"] = []
    elif problem in ("missing_units", "missing_details"):
        del manifest["outputs"]["units.json" if problem == "missing_units" else "details.json"]
    elif problem == "unexpected_output":
        manifest["outputs"]["../private-account-secret.json"] = dict(meta)
    elif problem == "output_meta_not_object":
        manifest["outputs"]["details.json"] = []
    elif problem in ("missing_hash", "missing_count"):
        del meta["sha256" if problem == "missing_hash" else "records"]
    elif problem in ("hash_not_string", "bad_hash"):
        meta["sha256"] = 7 if problem == "hash_not_string" else "private-account-secret"
    elif problem in ("boolean_count", "negative_count", "string_count", "float_count"):
        meta["records"] = {"boolean_count": True, "negative_count": -1,
                           "string_count": "1", "float_count": 1.0}[problem]
    elif problem == "extra_metadata":
        meta["private-account"] = "secret"
    elif problem == "missing_expected":
        del manifest["unit_list_expected"]
    elif problem in ("boolean_expected", "negative_expected", "string_expected"):
        manifest["unit_list_expected"] = {"boolean_expected": True, "negative_expected": -1,
                                          "string_expected": "1"}[problem]
    elif problem in ("boolean_schema", "boolean_game"):
        manifest["schema_version" if problem == "boolean_schema" else "game_id"] = True
    elif problem == "missing_requests":
        del manifest["requests"]
    elif problem == "requests_not_object":
        manifest["requests"] = []
    elif problem == "request_not_object":
        manifest["requests"]["unit-list/page-001"] = []
    elif problem == "missing_file":
        (snap.out / "details.json").unlink()
    elif problem == "count_mismatch":
        meta["records"] += 1
    elif problem in ("invalid_json", "output_not_list", "row_not_object", "detail_keyset"):
        raw = {"invalid_json": b'{"private-account":secret}', "output_not_list": b'{}',
               "row_not_object": b'[null]', "detail_keyset": b'[]'}[problem]
        (snap.out / "details.json").write_bytes(raw)
        meta.update(sha256=sha(raw), records=0 if problem == "detail_keyset" else 1)
    if problem == "truncated_json":
        (snap.out / "manifest.json").write_bytes(b'{"private-account":secret}')
    elif problem == "missing_manifest":
        (snap.out / "manifest.json").unlink()
    else:
        (snap.out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert_boundary_rejected(snap, [existing()])


def test_complete_partial_inventory_retains_exact_previous_fields(tmp_path):
    def override(path, payload):
        if path == DETAIL_PATH:
            return envelope(unit(99, inline=True))

    snap = snapshot(tmp_path, Session([unit(1), unit(2, inline=True)], override))
    result = snap.run()
    assert result["status"] == "partial"
    assert result["counts"]["details"] == result["unit_list_expected"] == 2
    assert result["counts"]["details_failed"] == 1
    prior = [existing(1), existing(3)]
    original = copy.deepcopy(prior)
    rows, units, report = merge_snapshot(snap.out, prior)
    assert prior == original
    by_id = {row["id"]: row for row in rows}
    for old in prior:
        assert {key: by_id[old["id"]][key] for key in old} == old
    assert report["accepted"] == 1 and report["added"] == ["2"]
    assert report["retained_previous"] == ["1", "3"]
    assert by_id[1]["provenance"]["reason"] == "failed"
    assert by_id[3]["provenance"]["reason"] == "absent_from_inventory"
    assert {row["id"] for row in units} == {1, 2}


@pytest.mark.parametrize("problem", [
    "missing_source_capture", "source_capture_not_string", "unknown_source_capture",
    "missing_detail_field", "missing_detail_id", "missing_unit_name", "invalid_unit_name",
    "missing_raw_hash", "invalid_raw_path", "missing_raw_endpoint", "missing_raw_request",
    "missing_capture_path", "raw_not_object", "raw_missing_envelope", "raw_invalid_envelope",
    "captured_detail_references_unmaterialized_failure", "failed_raw_hash_mismatch",
])
def test_incomplete_rows_and_capture_references_are_rejected(tmp_path, problem):
    snap = snapshot(tmp_path, Session())
    assert snap.run()["status"] == "complete_known_endpoints"
    rows = json.loads((snap.out / "details.json").read_text(encoding="utf-8"))
    origin = rows[0]["source_capture"]
    if problem == "missing_source_capture":
        del rows[0]["source_capture"]
    elif problem == "source_capture_not_string":
        rows[0]["source_capture"] = ["private-account-secret"]
    elif problem == "unknown_source_capture":
        rows[0]["source_capture"] = "private-account-secret"
    elif problem in ("missing_detail_field", "missing_detail_id"):
        del rows[0]["detail" if problem == "missing_detail_field" else "id"]
    elif problem in ("missing_unit_name", "invalid_unit_name"):
        units = json.loads((snap.out / "units.json").read_text(encoding="utf-8"))
        if problem == "missing_unit_name":
            del units[0]["unitEnglishName"]
        else:
            units[0]["unitEnglishName"] = []
        snap.output("units.json", units)
        # Keep compiled/raw inventory equal to reach the consumed lookup-field
        # boundary, rather than the independent inventory-substitution guard.
        meta = snap.manifest["requests"]["unit-list/page-001"]
        raw = json.loads((snap.out / meta["path"]).read_text(encoding="utf-8"))
        raw["envelope"]["data"] = units
        encoded = (json.dumps(raw, ensure_ascii=False) + "\n").encode("utf-8")
        (snap.out / meta["path"]).write_bytes(encoded)
        meta["sha256"] = sha(encoded)
    elif problem.startswith("raw_"):
        meta = snap.manifest["requests"][origin]
        raw = {"raw_not_object": b'[]', "raw_missing_envelope": b'{"request":{}}',
               "raw_invalid_envelope": b'{"request":{},"envelope":[]}'}[problem]
        (snap.out / meta["path"]).write_bytes(raw)
        meta["sha256"] = sha(raw)
    elif problem == "captured_detail_references_unmaterialized_failure":
        meta = snap.manifest["requests"][origin]
        meta["status"] = "failed"
        del meta["sha256"]
    elif problem == "failed_raw_hash_mismatch":
        meta = snap.manifest["requests"][origin]
        meta["status"] = "failed"
        (snap.out / meta["path"]).write_bytes(b'[]')
    else:
        meta = snap.manifest["requests"][origin]
        if problem == "invalid_raw_path":
            meta["path"] = ["private-account-secret"]
        else:
            field = {"missing_raw_hash": "sha256", "missing_raw_endpoint": "endpoint",
                     "missing_raw_request": "request", "missing_capture_path": "path"}[problem]
            del meta[field]
    rewrite_output(snap, "details.json", rows)
    assert_boundary_rejected(snap, [existing()])


@pytest.mark.parametrize("endpoint", [DETAIL_PATH, RULE_PATH, POWER_PATH, CATALOGS["40k-factions"]])
def test_complete_partial_with_unmaterialized_failed_request_retains_cache(tmp_path, endpoint):
    class FailedSession(Session):
        failures = 0

        def get(self, url, timeout):
            if url == endpoint:
                self.failures += 1
                raise requests.ConnectionError("private-account Bearer secret")
            return super().get(url, timeout)

    def override(path, payload):
        if path == endpoint and (path == DETAIL_PATH or payload["topName"] == "星际战士"):
            session.failures += 1
            raise requests.ConnectionError("private-account Bearer secret")

    session = FailedSession([unit(inline=endpoint != DETAIL_PATH)], override)
    snap = snapshot(tmp_path, session)
    result = snap.run()
    assert result["status"] == "partial" and result["counts"]["details"] == 1
    assert session.failures == snap.retries
    missing_raw = [meta for meta in result["requests"].values()
                   if meta.get("status") == "failed" and "sha256" not in meta]
    assert len(missing_raw) == 1 and not (snap.out / missing_raw[0]["path"]).exists()
    prior = [existing(), existing(2)]
    original = copy.deepcopy(prior)
    rows, units, report = merge_snapshot(snap.out, prior)
    assert prior == original and len(units) == 1 and len(rows) == 2
    by_id = {row["id"]: row for row in rows}
    retained = prior if endpoint == DETAIL_PATH else prior[1:]
    for old in retained:
        assert {key: by_id[old["id"]][key] for key in old} == old
    assert report["accepted"] == (0 if endpoint == DETAIL_PATH else 1)
    assert report["raw_hashes_checked"] == sum("sha256" in meta for meta in result["requests"].values())


@pytest.mark.parametrize("lookup", ["absent", None, []])
def test_complete_partial_without_lookup_name_retains_cache(tmp_path, lookup):
    listed = unit()
    if lookup == "absent":
        del listed["unitEnglishName"]
    else:
        listed["unitEnglishName"] = lookup
    snap = snapshot(tmp_path, Session([listed]))
    result = snap.run()
    assert result["status"] == "partial" and result["counts"]["details_failed"] == 1
    assert result["counts"]["details"] == result["unit_list_expected"] == 1
    prior = [existing()]
    original = copy.deepcopy(prior)
    rows, _, report = merge_snapshot(snap.out, prior)
    assert prior == original and report["accepted"] == 0
    assert {key: rows[0][key] for key in prior[0]} == prior[0]
    assert rows[0]["provenance"]["reason"] == "failed"
