"""Offline gold selection/validation; no application resources or model clients."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_bench  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "benchmarks/v3_edition11/qa_gold_v3.6.json"
FROZEN_SHA256 = "a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc"
FIELDS = ("id", "faction", "question", "gold", "gold_type")


def _document():
    return {
        "meta": {"version": "v3.7", "edition": 11, "total": 2},
        "details": [
            {"id": 1, "faction": "Tau", "question": "What is Shadowsun's T?",
             "gold": "Commander Shadowsun T=4", "gold_type": "stat"},
            {"id": 2, "faction": "Tau", "question": "What is Shadowsun's W?",
             "gold": "Commander Shadowsun W=6", "gold_type": "stat"},
        ],
    }


def _write(tmp_path, document):
    path = tmp_path / "selected.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_frozen_baseline_is_exact_original_bytes_and_all_115_rows():
    raw = (ROOT / "qa_gold.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FROZEN_SHA256
    assert FROZEN.read_bytes() == raw
    document = json.loads(raw)
    assert document["meta"]["version"] == "v3.6"
    assert len(document["details"]) == document["meta"]["total"] == 115
    assert len({row["id"] for row in document["details"]}) == 115
    # Exactly the original loader's five fields, values and order, including #63.
    expected = [{key: row.get(key) for key in FIELDS} for row in document["details"]]
    assert qa_bench.load_questions() == expected
    assert qa_bench.load_questions(gold_path=FROZEN) == expected
    assert qa_bench.load_questions(3) == expected[:3]


def test_default_source_is_resolved_at_call_time(tmp_path, monkeypatch):
    document = _document()
    monkeypatch.setattr(qa_bench, "QA_SOURCE", _write(tmp_path, document))
    assert qa_bench.load_questions()[0]["question"] == document["details"][0]["question"]


def test_explicit_selection_is_caller_relative_or_absolute(tmp_path, monkeypatch):
    document = _document()
    path = _write(tmp_path, document)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(qa_bench, "QA_SOURCE", tmp_path / "missing-default.json")
    expected = [{key: row[key] for key in FIELDS} for row in document["details"]]
    assert qa_bench.load_questions(gold_path="selected.json") == expected
    assert qa_bench.load_questions(gold_path=path) == expected


def test_missing_explicit_selection_never_falls_back(tmp_path):
    with pytest.raises(FileNotFoundError):
        qa_bench.load_questions(gold_path=tmp_path / "missing.json")


def test_invalid_json_selection_never_falls_back(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        qa_bench.load_questions(gold_path=path)


@pytest.mark.parametrize("field,value", [("gold", ""), ("id", 1)])
def test_invalid_default_tail_does_not_escape_validation_with_limit(tmp_path, monkeypatch,
                                                                  field, value):
    document = _document()
    document["details"][1][field] = value
    monkeypatch.setattr(qa_bench, "QA_SOURCE", _write(tmp_path, document))
    with pytest.raises(ValueError, match=field):
        qa_bench.load_questions(limit=1)


@pytest.mark.parametrize("invalid", [None, [], "gold", 42])
def test_document_requires_object(tmp_path, invalid):
    with pytest.raises(ValueError, match="root"):
        qa_bench.load_questions(gold_path=_write(tmp_path, invalid))


@pytest.mark.parametrize("field,value", [
    ("meta", None), ("meta", []), ("details", None), ("details", {}),
    ("details", []),
])
def test_document_structure_rejected(tmp_path, field, value):
    document = _document()
    document[field] = value
    with pytest.raises(ValueError, match=field):
        qa_bench.load_questions(gold_path=_write(tmp_path, document))


@pytest.mark.parametrize("field,value", [
    ("version", None), ("version", ""), ("version", "v3.7 junk"),
    ("version", "v2"), ("edition", True), ("edition", "11"),
    ("edition", 10), ("total", True), ("total", "2"), ("total", 1),
])
def test_metadata_rejected(tmp_path, field, value):
    document = _document()
    document["meta"][field] = value
    with pytest.raises(ValueError, match=field):
        qa_bench.load_questions(gold_path=_write(tmp_path, document))


@pytest.mark.parametrize("field,value", [
    ("id", True), ("id", 0), ("id", -1), ("id", "2"), ("id", 2.0),
    ("id", 1), ("faction", " \t"), ("faction", None),
    ("question", " \n"), ("question", 5), ("gold_type", "intrinsic"),
    ("gold_type", None), ("gold_type", []), ("gold", ""),
    ("gold", " \n"), ("gold", False), ("gold", []), ("gold", None),
])
def test_full_document_validated_before_limit(tmp_path, field, value):
    document = _document()
    document["details"][1][field] = value
    with pytest.raises(ValueError, match=field):
        qa_bench.load_questions(limit=1, gold_path=_write(tmp_path, document))


def test_non_object_row_rejected_before_limit(tmp_path):
    document = _document()
    document["details"][1] = "not an object"
    with pytest.raises(ValueError, match="details"):
        qa_bench.load_questions(limit=1, gold_path=_write(tmp_path, document))


@pytest.mark.parametrize("field", ["id", "faction", "question", "gold", "gold_type"])
def test_required_row_fields_cannot_be_missing(tmp_path, field):
    document = _document()
    del document["details"][1][field]
    with pytest.raises(ValueError, match=field):
        qa_bench.load_questions(limit=1, gold_path=_write(tmp_path, document))


def test_only_original_explicit_63_null_gold_contract_is_intrinsic(tmp_path):
    document = json.loads((ROOT / "qa_gold.json").read_bytes())
    original = next(row for row in document["details"] if row["id"] == 63)
    assert original["gold"] is None
    fixture = _document()
    fixture["details"][1] = copy.deepcopy(original)
    assert qa_bench.load_questions(gold_path=_write(tmp_path, fixture))[1]["gold"] is None
    for field, value in [("question", "New question"), ("faction", "Other faction"),
                         ("gold_type", "rule"), ("canonical_id", "different")]:
        changed = copy.deepcopy(fixture)
        changed["details"][1][field] = value
        with pytest.raises(ValueError, match="gold"):
            qa_bench.load_questions(gold_path=_write(tmp_path, changed))


@pytest.mark.parametrize("gold_type", ["stat", "weapon", "ability", "rule", "points"])
def test_all_supported_scoring_types_retained(tmp_path, gold_type):
    document = _document()
    document["details"][1]["gold_type"] = gold_type
    assert qa_bench.load_questions(gold_path=_write(tmp_path, document))[1]["gold_type"] == gold_type
