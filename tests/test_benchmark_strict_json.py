"""Raw duplicate-key regressions at benchmark input boundaries, entirely offline."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_bench  # noqa: E402
import compare_bench_runs as compare  # noqa: E402


def _gold():
    return {
        "meta": {"version": "v3.7", "edition": 11, "total": 2},
        "details": [
            {"id": i, "faction": "Fixture", "question": f"Question {i}",
             "gold": f"Expectation {i}", "gold_type": "rule",
             "canonical_id": None if i == 1 else "000000002",
             "annotations": [{"label": "中文", "child": {"value": None}},
                             {"label": "独立", "child": {"value": "exact"}}]}
            for i in (1, 2)
        ],
    }


def _result():
    gold = _gold()
    rows = []
    for row in gold["details"]:
        rows.append({**{k: row[k] for k in ("id", "faction", "question", "gold", "gold_type")},
                     "verdict": "✅", "gold_metadata": {
                         "canonical_id": row["canonical_id"],
                         "annotations": row["annotations"]}})
    return {"summary": {"results": {"total": 2}}, "details": rows}


def _raw(data):
    return json.dumps(data, ensure_ascii=False, indent=2).replace("\n", "\r\n")


def _duplicate(raw, needle, replacement):
    assert needle in raw
    raw = raw.replace(needle, replacement, 1)
    # These are valid JSON with previously accepted last-value projections.
    json.loads(raw)
    return raw


GOLD_DUPLICATES = [
    ('"meta": {', '"meta": {}, "meta": {', "meta"),
    ('"version": "v3.7"', '"version": "v3.6", "version": "v3.7"', "version"),
    ('"id": 2', '"id": 1, "id": 2', "id"),
    ('"gold": "Expectation 2"', '"gold": "Conflicting", "gold": "Expectation 2"', "gold"),
    ('"canonical_id": "000000002"',
     '"canonical_id": 42, "canonical_id": "000000002"', "canonical_id"),
    ('"value": null', '"value": 42, "value": null', "value"),
    ('"id": 2', '"id": 2, "id": 2', "id"),
    ('"id": 2', '"i\\u0064": 1, "id": 2', "id"),
]

RESULT_DUPLICATES = [
    ('"details": [', '"details": [], "details": [', "details"),
    ('"total": 2', '"total": 1, "total": 2', "total"),
    ('"id": 2', '"id": 1, "id": 2', "id"),
    ('"gold": "Expectation 2"', '"gold": "Conflicting", "gold": "Expectation 2"', "gold"),
    ('"gold_metadata": {', '"gold_metadata": {"canonical_id": "wrong"}, "gold_metadata": {',
     "gold_metadata"),
    ('"canonical_id": "000000002"',
     '"canonical_id": "wrong", "canonical_id": "000000002"', "canonical_id"),
    ('"value": null', '"value": 42, "value": null', "value"),
    ('"id": 2', '"i\\u0064": 2, "id": 2', "id"),
]


@pytest.mark.parametrize("needle,replacement,key", GOLD_DUPLICATES)
def test_gold_duplicate_names_rejected_before_limit(tmp_path, needle, replacement, key):
    selected = tmp_path / "selected.json"
    selected.write_bytes(_duplicate(_raw(_gold()), needle, replacement).encode("utf-8"))
    with pytest.raises(ValueError, match=f"Duplicate JSON object key: '{key}'"):
        qa_bench.load_questions(limit=1, gold_path=selected)


@pytest.mark.parametrize("mode", ["classic", "agent", "layered"])
@pytest.mark.parametrize("needle,replacement,key", GOLD_DUPLICATES)
def test_gold_duplicate_names_reject_before_any_cli_work(
        tmp_path, monkeypatch, capsys, mode, needle, replacement, key):
    selected = tmp_path / "selected.json"
    selected.write_bytes(_duplicate(_raw(_gold()), needle, replacement).encode("utf-8"))
    output = tmp_path / "must-not-exist.json"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        pytest.fail("duplicate JSON reached benchmark initialization or worker")

    for name in ("init_resources", "make_client", "run_one", "run_one_layered"):
        monkeypatch.setattr(qa_bench, name, forbidden)
    argv = ["qa_bench", "--gold", str(selected), "--out", str(output), "--limit", "1"]
    argv += ["--layered"] if mode == "layered" else ["--path", mode]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match=f"Duplicate JSON object key: '{key}'"):
        qa_bench.main()
    assert not output.exists()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("side", ["base", "new"])
@pytest.mark.parametrize("override", [False, True])
@pytest.mark.parametrize("needle,replacement,key", RESULT_DUPLICATES)
def test_result_duplicate_names_reject_before_comparison_acceptance(
        tmp_path, capsys, side, override, needle, replacement, key):
    paths = {name: tmp_path / f"{name}.json" for name in ("base", "new")}
    for name, path in paths.items():
        raw = _raw(_result())
        if name == side:
            raw = _duplicate(raw, needle, replacement)
        path.write_bytes(raw.encode("utf-8"))
    flags = ["--allow-different-gold"] if override else []
    assert compare.main(["compare", *flags, str(paths["base"]), str(paths["new"])]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert f"Invalid benchmark input: Duplicate JSON object key: '{key}'" in output.err


def test_unique_nested_objects_preserve_bytes_metadata_and_repeated_names(tmp_path, capsys):
    document = _gold()
    path = tmp_path / "gold.json"
    raw = _raw(document).encode("utf-8")
    path.write_bytes(raw)
    loaded, source, parsed_bytes = qa_bench._read_gold_document(path)
    assert loaded == document
    assert parsed_bytes == raw
    assert qa_bench._gold_provenance(loaded, source, parsed_bytes)["sha256"] == hashlib.sha256(raw).hexdigest()
    result = tmp_path / "result.json"
    result.write_bytes(_raw(_result()).encode("utf-8"))
    rows, _, _ = compare._read_run(result)
    assert rows[1]["gold_metadata"]["canonical_id"] is None
    assert rows[2]["gold_metadata"]["canonical_id"] == "000000002"
    assert rows[1]["gold_metadata"]["annotations"] == document["details"][0]["annotations"]
    assert compare.main(["compare", str(result), str(result)]) == 0
    assert "same detailed expectations" in capsys.readouterr().out


@pytest.mark.parametrize("boundary", ["gold", "result"])
def test_real_cli_duplicate_input_exits_nonzero_without_acceptance(tmp_path, boundary):
    scripts = Path(qa_bench.__file__).resolve().parent
    selected = tmp_path / "duplicate.json"
    output = tmp_path / "must-not-exist.json"
    data = _gold() if boundary == "gold" else _result()
    selected.write_bytes(_duplicate(_raw(data), '"id": 2', '"id": 1, "id": 2').encode("utf-8"))
    command = [sys.executable, str(scripts / (
        "qa_bench.py" if boundary == "gold" else "compare_bench_runs.py"))]
    command += (["--gold", str(selected), "--out", str(output), "--limit", "1"]
                if boundary == "gold" else ["--allow-different-gold", str(selected), str(selected)])
    env = os.environ.copy()
    env.pop("DEEPSEEK_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env)
    assert process.returncode != 0
    assert "Duplicate JSON object key: 'id'" in process.stderr
    assert process.stdout == ""
    assert not output.exists()
