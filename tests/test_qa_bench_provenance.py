"""Exercise CLI selection and real output paths with offline resource/client stubs."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_bench  # noqa: E402
import compare_bench_runs  # noqa: E402


def _document():
    return {
        "meta": {
            "version": "v3.7", "edition": 11, "total": 2,
            "source_limitations": ["Fixture coverage is limited to its captured rule."],
        },
        "details": [
            {
                "id": identity, "faction": "Fixture faction",
                "question": f"Explain captured rule {identity}.",
                "gold": f"Captured expectation {identity}.", "gold_type": "rule",
                "canonical_id": f"fixture-{identity}", "note": "Dated fixture only.",
                "source_provenance": [{"url": "https://example.org/fixture",
                                       "captured_date": "2026-09-30"}],
                "source_coverage": "Captured rule only; no current body certification.",
            }
            for identity in (1, 2)
        ],
    }


def _write(path, document):
    # Deliberate whitespace/CRLF proves output hashes bytes, not reserialized JSON.
    raw = (json.dumps(document, ensure_ascii=False, indent=3) + "\n\n").replace(
        "\n", "\r\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def _offline(monkeypatch, messages, on_init=None, verdict="✅"):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "offline-test-sentinel")

    def create(**kwargs):
        messages.append(kwargs["messages"])
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=f"{verdict} Offline fixture verdict."))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(qa_bench, "make_client", lambda provider: client)

    def resources():
        if on_init:
            on_init()
        return (None,) * 5

    monkeypatch.setattr(qa_bench, "init_resources", resources)
    monkeypatch.setattr(qa_bench, "answer_classic", lambda *args: ("Fixture answer.", []))
    monkeypatch.setattr(qa_bench, "answer_agent", lambda *args: (
        "Fixture answer.", [], {"degraded": True, "fell_back_to_classic": True}))
    monkeypatch.setattr(qa_bench, "retrieve_and_answer_classic", lambda *args: (
        "Fixture answer.", []))


@pytest.mark.parametrize("mode", ["classic", "agent", "layered"])
@pytest.mark.parametrize("selection", ["absolute", "relative", "default"])
def test_cli_records_exact_selected_snapshot_in_both_modes(tmp_path, monkeypatch,
                                                          mode, selection):
    document = _document()
    selected = tmp_path / "selected.json"
    raw = _write(selected, document)
    output = tmp_path / "output.json"
    messages = []
    # Change the file after loading: provenance and expectations must stay paired
    # to the bytes originally read, not a second read after resources initialize.
    _offline(monkeypatch, messages, lambda: selected.write_text("{}", encoding="utf-8"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(qa_bench, "QA_SOURCE", selected if selection == "default"
                        else tmp_path / "missing-default.json")
    argv = ["qa_bench", "--out", str(output), "--limit", "1", "--workers", "1"]
    if selection != "default":
        argv += ["--gold", str(selected) if selection == "absolute" else selected.name]
    argv += ["--layered"] if mode == "layered" else ["--path", mode]
    monkeypatch.setattr(sys, "argv", argv)
    qa_bench.main()

    result = json.loads(output.read_text(encoding="utf-8"))
    summary = result["summary"]
    assert summary["gold_source"] == {
        "path": str(selected.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
        "version": "v3.7", "edition": 11, "total": 2,
        "source_limitations": document["meta"]["source_limitations"],
    }
    assert len(result["details"]) == 1
    row = result["details"][0]
    original = document["details"][0]
    for field in ("id", "faction", "question", "gold", "gold_type"):
        assert row[field] == original[field]
    assert row["gold_metadata"] == {key: value for key, value in original.items()
                                    if key not in ("id", "faction", "question", "gold", "gold_type")}
    assert any("Captured expectation 1." in message["content"]
               for call in messages for message in call)
    assert all("Captured expectation 2." not in message["content"]
               for call in messages for message in call)
    if mode == "layered":
        assert {"path", "mode", "provider", "total", "retrieval", "generation",
                "stages", "retrieval_accuracy", "generation_accuracy",
                "conditional_gen_accuracy", "wall_time"} <= summary.keys()
        assert summary["total"] == 1
        assert summary["generation"]["correct"] == 1
        assert row["generation_verdict"] == "✅"
    else:
        assert {"path", "provider", "results", "accuracy", "degraded_count",
                "wall_time"} <= summary.keys()
        assert summary["results"] == {"correct": 1, "partial": 0, "wrong": 0, "total": 1}
        assert summary["degraded_count"] == (1 if mode == "agent" else 0)
        assert row["judge_method"] == "llm_gold"
        assert row["verdict"] == "✅"


def test_default_historical_gold_does_not_claim_current_source_coverage(tmp_path, monkeypatch):
    document = _document()
    del document["meta"]["source_limitations"]
    document["meta"]["version"] = "v3.6"
    selected = tmp_path / "historical.json"
    _write(selected, document)
    output = tmp_path / "output.json"
    _offline(monkeypatch, [])
    monkeypatch.setattr(qa_bench, "QA_SOURCE", selected)
    monkeypatch.setattr(sys, "argv", ["qa_bench", "--out", str(output), "--workers", "1"])
    qa_bench.main()
    source = json.loads(output.read_text(encoding="utf-8"))["summary"]["gold_source"]
    assert source["version"] == "v3.6"
    assert source["source_limitations"] == [
        "Selected gold does not declare source-coverage limitations; numerical agreement "
        "alone does not certify current source coverage."
    ]


@pytest.mark.parametrize("mode", ["classic", "layered"])
@pytest.mark.parametrize("invalid", ["missing", "broken_json", "empty_tail", "duplicate_tail"])
def test_cli_invalid_selection_fails_before_credentials_resources_or_output(
        tmp_path, monkeypatch, mode, invalid):
    selected = tmp_path / "invalid.json"
    document = _document()
    if invalid == "broken_json":
        selected.write_text("{", encoding="utf-8")
    elif invalid != "missing":
        document["details"][1]["gold" if invalid == "empty_tail" else "id"] = (
            "" if invalid == "empty_tail" else 1)
        _write(selected, document)
    output = tmp_path / "must-not-exist.json"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def forbidden(*args):
        pytest.fail("invalid selected gold reached resources or client initialization")

    monkeypatch.setattr(qa_bench, "init_resources", forbidden)
    monkeypatch.setattr(qa_bench, "make_client", forbidden)
    argv = ["qa_bench", "--gold", str(selected), "--out", str(output), "--limit", "1"]
    if mode == "layered":
        argv += ["--layered"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises((FileNotFoundError, ValueError)):
        qa_bench.main()
    assert not output.exists()


@pytest.mark.parametrize("mode", ["classic", "layered"])
@pytest.mark.parametrize("verdict,count_key", [("⚠️", "partial"), ("❌", "wrong")])
def test_provenance_does_not_turn_completed_run_into_passing_answers(
        tmp_path, monkeypatch, mode, verdict, count_key):
    selected = tmp_path / "selected.json"
    raw = _write(selected, _document())
    output = tmp_path / "output.json"
    _offline(monkeypatch, [], verdict=verdict)
    argv = ["qa_bench", "--gold", str(selected), "--out", str(output), "--workers", "1"]
    if mode == "layered":
        argv += ["--layered"]
    monkeypatch.setattr(sys, "argv", argv)
    qa_bench.main()
    result = json.loads(output.read_text(encoding="utf-8"))
    summary = result["summary"]
    counts = summary["generation" if mode == "layered" else "results"]
    assert counts[count_key] == 2
    assert counts["correct"] == 0
    assert summary["generation_accuracy" if mode == "layered" else "accuracy"] == 0.0
    assert summary["gold_source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert all(row["generation_verdict" if mode == "layered" else "verdict"] == verdict
               for row in result["details"])


@pytest.mark.parametrize("invalid", [None, [], "unqualified", [None], [" "]])
def test_malformed_declared_source_limitations_are_rejected(tmp_path, invalid):
    document = _document()
    document["meta"]["source_limitations"] = invalid
    selected = tmp_path / "invalid.json"
    _write(selected, document)
    with pytest.raises(ValueError, match="source_limitations"):
        qa_bench.load_questions(limit=1, gold_path=selected)


@pytest.mark.parametrize("mode", ["classic", "agent", "layered"])
@pytest.mark.parametrize("identity", [42, True, [], "", " \t"])
def test_cli_invalid_identity_rejected_before_credentials_resources_or_worker(
        tmp_path, monkeypatch, capsys, mode, identity):
    document = _document()
    # Invalid metadata outside --limit still invalidates the whole selection.
    document["details"][1]["canonical_id"] = identity
    selected = tmp_path / "invalid.json"
    _write(selected, document)
    output = tmp_path / "must-not-exist.json"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def forbidden(*args):
        pytest.fail("invalid canonical identity reached benchmark work")

    for name in ("init_resources", "make_client", "run_one", "run_one_layered"):
        monkeypatch.setattr(qa_bench, name, forbidden)
    argv = ["qa_bench", "--gold", str(selected), "--out", str(output), "--limit", "1"]
    argv += ["--layered"] if mode == "layered" else ["--path", mode]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match=r"details\[1\]\.canonical_id.*nonempty text"):
        qa_bench.main()
    assert not output.exists()
    assert "[qa_bench] mode=" not in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["classic", "agent", "layered"])
@pytest.mark.parametrize("identity_kind", ["text", "null", "absent"])
def test_valid_optional_identity_round_trips_through_actual_output_and_comparator(
        tmp_path, monkeypatch, mode, identity_kind):
    document = _document()
    for row in document["details"]:
        if identity_kind == "null":
            row["canonical_id"] = None
        elif identity_kind == "absent":
            del row["canonical_id"]
        else:
            # IDs are exact strings, including leading zeros and surrounding space.
            row["canonical_id"] = " 000000001 "
    selected = tmp_path / "valid.json"
    raw = _write(selected, document)
    output = tmp_path / "result.json"
    _offline(monkeypatch, [])
    argv = ["qa_bench", "--gold", str(selected), "--out", str(output), "--workers", "1"]
    argv += ["--layered"] if mode == "layered" else ["--path", mode]
    monkeypatch.setattr(sys, "argv", argv)
    qa_bench.main()
    result = json.loads(output.read_bytes())
    assert result["summary"]["gold_source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    for original, emitted in zip(document["details"], result["details"]):
        assert emitted["gold_metadata"] == {
            key: value for key, value in original.items()
            if key not in ("id", "faction", "question", "gold", "gold_type")}
    assert compare_bench_runs.main(["compare", str(output), str(output)]) == 0
