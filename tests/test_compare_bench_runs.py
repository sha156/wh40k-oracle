"""Offline comparison contracts; no benchmark execution or production writes."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import compare_bench_runs as compare  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent


def _run(provenance=False):
    data = {"summary": {}, "details": [
        {"id": i, "faction": "Fixture", "question": f"Question {i}",
         "gold": f"Expectation {i}", "gold_type": "rule", "verdict": "✅"}
        for i in (1, 2)
    ]}
    if provenance:
        data["summary"]["gold_source"] = {
            "path": "/fixture/gold.json", "sha256": "a" * 64,
            "version": "v3.6", "edition": 11, "total": 2,
            "source_limitations": ["Fixture source coverage only."],
        }
        for row in data["details"]:
            row["gold_metadata"] = {"canonical_id": f"fixture-{row['id']}",
                                    "note": "Captured fixture."}
    return data


def _compare(tmp_path, base, new, *flags):
    paths = [tmp_path / name for name in ("base.json", "new.json")]
    for path, data in zip(paths, (base, new)):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return compare.main(["compare_bench_runs.py", *flags, *map(str, paths)])


def test_same_historical_expectations_compare_actual_rows(tmp_path, capsys):
    base = _run()
    new = copy.deepcopy(base)
    new["details"][1]["verdict"] = "❌"
    assert _compare(tmp_path, base, new) == 0
    output = capsys.readouterr().out
    assert "#2: ✅ -> ❌" in output
    assert "provenance unavailable" in output
    assert "same detailed expectations" in output


@pytest.mark.parametrize("field,value", [
    ("question", "Different identity question"), ("gold", "New expectation"),
    ("gold_type", "ability"), ("faction", "Other faction"),
])
def test_changed_expectations_refused_before_verdicts(tmp_path, capsys, field, value):
    base, new = _run(), _run()
    new["details"][1][field] = value
    new["details"][1]["verdict"] = "❌"
    assert _compare(tmp_path, base, new) == 2
    output = capsys.readouterr().out
    assert f"#2 {field}:" in output
    assert "verdict differences" not in output


def test_explicit_cross_gold_enumerates_every_difference(tmp_path, capsys):
    base, new = _run(True), _run(True)
    new["summary"]["gold_source"].update(version="v3.7", sha256="b" * 64)
    row = new["details"][1]
    row.update(question="Changed question", gold="Changed expectation",
               gold_type="points", verdict="❌")
    row["gold_metadata"].update(canonical_id="other", note="New citation")
    assert _compare(tmp_path, base, new, "--allow-different-gold") == 0
    output = capsys.readouterr().out
    for field in ("gold_source.version", "gold_source.sha256", "#2 question",
                  "#2 gold:", "#2 gold_type", "#2 gold_metadata.canonical_id",
                  "#2 gold_metadata.note"):
        assert field in output
    assert "not an application regression claim" in output
    assert "#2: ✅ -> ❌" in output


@pytest.mark.parametrize("field,value", [
    ("version", "v3.7"), ("sha256", "b" * 64), ("edition", 10),
    ("source_limitations", ["Different coverage"]), ("total", 3),
])
def test_source_changes_block_same_gold_comparison(tmp_path, capsys, field, value):
    base, new = _run(True), _run(True)
    new["summary"]["gold_source"][field] = value
    assert _compare(tmp_path, base, new) == 2
    assert f"gold_source.{field}:" in capsys.readouterr().out


def test_different_paths_are_locations_not_expectation_changes(tmp_path, capsys):
    base, new = _run(True), _run(True)
    new["summary"]["gold_source"]["path"] = "/other/gold.json"
    assert _compare(tmp_path, base, new) == 0
    assert "/other/gold.json" in capsys.readouterr().out


def test_historical_to_modern_checks_rows_and_discloses_unknowns(tmp_path, capsys):
    assert _compare(tmp_path, _run(), _run(True)) == 0
    output = capsys.readouterr().out
    assert "base: gold provenance unavailable" in output
    assert "#1 gold_metadata availability differs" in output
    assert "source equivalence is unverified" in output


@pytest.mark.parametrize("mode", ["default", "allow"])
def test_missing_ids_are_reported_and_require_explicit_comparison(tmp_path, capsys, mode):
    base, new = _run(), _run()
    new["details"].pop()
    flags = ("--allow-different-gold",) if mode == "allow" else ()
    assert _compare(tmp_path, base, new, *flags) == (0 if flags else 2)
    assert "Only base IDs: [2]" in capsys.readouterr().out


@pytest.mark.parametrize("field,value", [
    ("id", 1), ("id", True), ("id", 0), ("id", -2), ("id", "2"),
    ("id", 2.0), ("question", " "), ("faction", None),
    ("gold_type", "unknown"), ("gold", ""), ("gold", None),
    ("verdict", "unknown"), ("gold_metadata", []),
])
def test_invalid_tail_rejected_even_with_override(tmp_path, capsys, field, value):
    base, new = _run(), _run()
    new["details"][1][field] = value
    assert _compare(tmp_path, base, new, "--allow-different-gold") == 2
    output = capsys.readouterr()
    assert field in output.err
    assert "verdict differences" not in output.out


@pytest.mark.parametrize("invalid", [None, [], {"details": []}, {"details": {}},
                                     {"details": [None]}, {"summary": [], "details": []}])
def test_invalid_documents(tmp_path, capsys, invalid):
    assert _compare(tmp_path, _run(), invalid) == 2
    assert "Invalid benchmark input" in capsys.readouterr().err


@pytest.mark.parametrize("field", ["question", "gold", "gold_type", "verdict"])
def test_missing_contract_field_cannot_be_inferred(tmp_path, capsys, field):
    base, new = _run(), _run()
    del new["details"][1][field]
    assert _compare(tmp_path, base, new) == 2
    assert field in capsys.readouterr().err


@pytest.mark.parametrize("field,value", [
    ("sha256", "bad"), ("version", None), ("edition", True),
    ("total", 1), ("total", True), ("source_limitations", []), ("path", ""),
])
def test_malformed_declared_provenance_is_not_historical(tmp_path, capsys, field, value):
    new = _run(True)
    new["summary"]["gold_source"][field] = value
    assert _compare(tmp_path, _run(), new) == 2
    assert f"gold_source.{field}" in capsys.readouterr().err


def test_matching_hash_never_overrides_different_actual_gold(tmp_path, capsys):
    base, new = _run(True), _run(True)
    new["details"][1]["gold"] = "Different despite same claimed hash"
    assert _compare(tmp_path, base, new) == 2
    assert "#2 gold:" in capsys.readouterr().out


def test_layered_results_compare_both_axes(tmp_path, capsys):
    base = _run(True)
    for row in base["details"]:
        del row["verdict"]
        row.update(retrieval_verdict="✅", generation_verdict="✅")
    new = copy.deepcopy(base)
    new["details"][1].update(retrieval_verdict="❌", generation_verdict="⚠️")
    assert _compare(tmp_path, base, new) == 0
    output = capsys.readouterr().out
    assert "retrieval_verdict differences: 1" in output
    assert "generation_verdict differences: 1" in output


def test_mixed_result_modes_are_not_comparable(tmp_path, capsys):
    base, new = _run(), _run()
    for row in new["details"]:
        del row["verdict"]
        row.update(retrieval_verdict="✅", generation_verdict="✅")
    assert _compare(tmp_path, base, new, "--allow-different-gold") == 2
    assert "verdict axes differ" in capsys.readouterr().err


def test_actual_historical_pair_works_without_inventing_provenance(capsys):
    directory = ROOT / "benchmarks/v3_edition11"
    assert compare.main(["compare_bench_runs.py",
                         str(directory / "qa_agent_results_same_name_disambig.json"),
                         str(directory / "qa_agent_results_same_name_disambig_run2.json")]) == 0
    output = capsys.readouterr().out
    assert "verdict differences: 0" in output
    assert "provenance unavailable" in output


def test_missing_file_and_invalid_json_are_clean_errors(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert compare.main(["compare", str(missing), str(broken)]) == 2
    assert "Invalid benchmark input" in capsys.readouterr().err
    assert compare.main(["compare", str(broken), str(broken)]) == 2
    assert "Invalid benchmark input" in capsys.readouterr().err


@pytest.mark.parametrize("side", ["base", "new"])
def test_duplicate_default_input_never_collapses_rows(tmp_path, capsys, side):
    base, new = _run(), _run()
    (base if side == "base" else new)["details"][1]["id"] = 1
    assert _compare(tmp_path, base, new) == 2
    output = capsys.readouterr()
    assert "duplicates #1" in output.err
    assert output.out == ""


def test_canonical_identity_changes_outside_metadata_are_detected(tmp_path, capsys):
    base, new = _run(True), _run(True)
    for data in (base, new):
        del data["details"][0]["gold_metadata"]["canonical_id"]
        data["details"][0]["canonical_id"] = "base-identity"
    new["details"][0]["canonical_id"] = "new-identity"
    assert _compare(tmp_path, base, new) == 2
    assert "#1 canonical_id:" in capsys.readouterr().out


def test_contradictory_identity_metadata_rejected(tmp_path, capsys):
    new = _run(True)
    new["details"][0]["canonical_id"] = "contradicts-metadata"
    assert _compare(tmp_path, _run(True), new, "--allow-different-gold") == 2
    assert "canonical_id conflicts" in capsys.readouterr().err


def test_null_metadata_removal_is_visible(tmp_path, capsys):
    base, new = _run(True), _run(True)
    base["details"][0]["gold_metadata"]["source_coverage"] = None
    assert _compare(tmp_path, base, new) == 2
    assert "source_coverage: null -> <absent>" in capsys.readouterr().out


@pytest.mark.parametrize("total", [1, True, "2"])
@pytest.mark.parametrize("layered", [False, True])
def test_declared_executed_count_must_match_all_rows(tmp_path, capsys, total, layered):
    new = _run()
    new["summary"].update({"total": total} if layered else {"results": {"total": total}})
    assert _compare(tmp_path, _run(), new) == 2
    assert "executed total" in capsys.readouterr().err


def test_original_null_contract_is_valid_but_cannot_change_identity(tmp_path, capsys):
    base = _run()
    row = base["details"][1]
    row.update(id=63, faction="帝国卫队", question="坦克指挥官的坦克命令有什么效果？",
               gold=None, gold_type="ability")
    assert _compare(tmp_path, base, base) == 0
    capsys.readouterr()
    new = copy.deepcopy(base)
    new["details"][1]["canonical_id"] = "different-tank"
    assert _compare(tmp_path, base, new) == 2
    assert "null contract" in capsys.readouterr().err
    new["details"][1].update(canonical_id=None, gold_metadata={"canonical_id": "different-tank"})
    assert _compare(tmp_path, base, new) == 2
    assert "null contract" in capsys.readouterr().err


@pytest.mark.parametrize("source", [None, [], "hash"])
def test_invalid_provenance_object_rejected(tmp_path, capsys, source):
    new = _run()
    new["summary"]["gold_source"] = source
    assert _compare(tmp_path, _run(), new) == 2
    assert "gold_source must be an object" in capsys.readouterr().err


def test_invalid_version_and_conflicting_axes_rejected(tmp_path, capsys):
    new = _run(True)
    new["summary"]["gold_source"]["version"] = "unknown version"
    assert _compare(tmp_path, _run(), new) == 2
    assert "gold_source.version" in capsys.readouterr().err
    new = _run()
    new["details"][1]["generation_verdict"] = "✅"
    assert _compare(tmp_path, _run(), new) == 2
    assert "conflicting verdict axes" in capsys.readouterr().err
