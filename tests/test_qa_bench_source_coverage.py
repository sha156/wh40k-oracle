"""Offline controls for the separate source-cited profile and acceptance ceiling."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_bench

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "benchmarks/v3_edition11/qa_gold_v3.7_source_cited.json"


def profile():
    return json.loads(PROFILE.read_bytes())


def client_with(payloads):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        value = payloads.pop(0)
        if isinstance(value, Exception):
            raise value
        text = value if isinstance(value, str) else json.dumps(value)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


def coverage_reply(contract, answer, passed=True, prohibited=False):
    return {
        "requirements": {key: {"satisfied": passed, "quote": answer if passed else ""}
                         for key in contract["requirements"]},
        "prohibitions": {key: {"present": prohibited, "quote": answer if prohibited else ""}
                         for key in contract["prohibitions"]},
    }


def test_source_profile_retains_all_ordered_targets_and_original_mechanics():
    old = json.loads((ROOT / "qa_gold.json").read_bytes())
    new = profile()
    qa_bench._validate_gold_document(new)
    assert new["meta"]["version"] == "v3.7"
    assert len(new["details"]) == new["meta"]["total"] == 115
    changed = []
    for before, after in zip(old["details"], new["details"]):
        for key in ("id", "question", "faction", "gold_type", "canonical_id", "unit"):
            assert before.get(key) == after.get(key)
        if before["gold"] != after["gold"]:
            changed.append(after["id"])
            assert after["clause_revision"]["before"] == before["gold"]
            assert after["clause_revision"]["after"] == after["gold"]
    assert changed == [14, 34, 93, 113, 114, 115, 118]
    assert [r["id"] for r in new["details"] if "coverage_contract" in r] == (
        list(range(11, 21)) + [34] + list(range(75, 81)) + [113, 114, 115, 118])
    assert (ROOT / "qa_gold.json").read_bytes() == (
        ROOT / "benchmarks/v3_edition11/qa_gold_v3.6.json").read_bytes()
    assert hashlib.sha256((ROOT / "qa_gold.json").read_bytes()).hexdigest() == (
        "a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc")


@pytest.mark.parametrize("mutation", [
    "version", "duplicate", "question", "type", "identity", "gold", "missing_revision",
    "bad_url", "bad_hash", "bad_date", "blank_version", "bad_locator", "missing_source",
    "missing_contract", "blank_claim", "unknown_kind", "certified", "wrong_as_of",
    "lost_claim", "lost_prohibition", "lost_page", "wrong_kind",
])
def test_profile_contracts_are_validated_before_limit(tmp_path, mutation):
    doc = profile()
    row = next(r for r in doc["details"] if r["id"] == 114)
    source = doc["meta"]["sources"]["mfm_space-marines"]
    if mutation == "version": doc["meta"]["version"] = "v3.6"
    elif mutation == "duplicate": doc["details"][-1]["id"] = 114
    elif mutation == "question": row["question"] = "Different target"
    elif mutation == "type": row["gold_type"] = "rule"
    elif mutation == "identity": row["canonical_id"] = "000000138"
    elif mutation == "gold": doc["details"][-1]["gold"] = "Weakened contract"
    elif mutation == "missing_revision": del row["clause_revision"]
    elif mutation == "bad_url": source["url"] = "https://example.org/invented"
    elif mutation == "bad_hash": source["sha256"] = "bad"
    elif mutation == "bad_date": source["snapshot_date"] = "2026-02-30"
    elif mutation == "blank_version": source["version"] = " "
    elif mutation == "bad_locator": row["clause_revision"]["evidence"][0]["locator"] = {}
    elif mutation == "missing_source": row["clause_revision"]["evidence"][0]["source_id"] = "missing"
    elif mutation == "missing_contract": del row["coverage_contract"]
    elif mutation == "blank_claim": row["coverage_contract"]["requirements"]["dated_price"] = " "
    elif mutation == "unknown_kind": row["coverage_contract"]["kind"] = "auto_award"
    elif mutation == "certified": row["coverage_contract"]["full_current_body_verified"] = True
    elif mutation == "wrong_as_of": row["coverage_contract"]["as_of"] = "2026-09-14"
    elif mutation == "lost_claim": del row["coverage_contract"]["requirements"]["latest_absence"]
    elif mutation == "lost_prohibition": del row["coverage_contract"]["prohibitions"]["identity_mix"]
    elif mutation == "lost_page": row["coverage_contract"]["source_ids"].pop()
    elif mutation == "wrong_kind": row["coverage_contract"]["kind"] = "published_points"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        qa_bench.load_questions(limit=1, gold_path=path)


@pytest.mark.parametrize("raw,passed,prohibited,expected", [
    ("❌", True, False, "❌"),   # wrong mechanics + perfect qualifier stays wrong
    ("⚠️", True, False, "⚠️"), # omission + perfect qualifier stays partial
    ("✅", False, False, "⚠️"), # right mechanics, missing qualifier lowers acceptance
    ("✅", True, False, "✅"),  # both can pass
    ("✅", True, True, "❌"),   # identity mix or invented current price fails
    ("❌", False, False, "❌"),
])
def test_coverage_can_only_lower_original_verdict(raw, passed, prohibited, expected):
    row = next(r for r in profile()["details"] if r["id"] == 114)
    answer = "Armour of Antilochus: 155 in the September 14 snapshot; exact current listing absent."
    client, calls = client_with([coverage_reply(row["coverage_contract"], answer, passed, prohibited)])
    check = qa_bench.check_source_coverage("offline-judge", client, row, answer)
    assert qa_bench.coverage_ceiling(raw, check) == expected
    assert check["contract"] == row["coverage_contract"]
    assert len(calls) == 1


@pytest.mark.parametrize("bad", ["garbage", {}, {"requirements": {}, "prohibitions": {}},
                                 RuntimeError("offline error"), "true_without_quotes"])
def test_unknown_or_unsubstantiated_coverage_never_passes(bad):
    row = next(r for r in profile()["details"] if r["id"] == 11)
    if bad == "true_without_quotes":
        bad = coverage_reply(row["coverage_contract"], "quote not in actual answer")
    client, _ = client_with([bad])
    check = qa_bench.check_source_coverage("offline", client, row, "SV=3+ W=2")
    assert check["status"] == "unverified"
    assert qa_bench.coverage_ceiling("✅", check) == "⚠️"
    assert qa_bench.coverage_ceiling("❌", check) == "❌"


@pytest.mark.parametrize("mode", ["classic", "agent", "layered"])
@pytest.mark.parametrize("wrong_stat,qualified", [(True, True), (False, False), (False, True)])
def test_actual_offline_api_harness_coverage_and_outputs(
        tmp_path, monkeypatch, mode, wrong_stat, qualified):
    doc = profile()
    row = next(r for r in doc["details"] if r["id"] == 11)
    answer = ("SV=2+ W=9" if wrong_stat else "SV=3+ W=2") + (
        ". Historical v3.6 September 16 expectations; as of September 30 complete current "
        "Space Marine body unavailable, current profiles unverified." if qualified else "")
    replies = (["✅", "❌" if wrong_stat else "✅"] if mode == "layered" else
               [{"SV": ["2+" if wrong_stat else "3+"], "W": ["9" if wrong_stat else "2"]}])
    replies += [coverage_reply(row["coverage_contract"], answer, qualified)]
    client, calls = client_with(replies)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "offline-sentinel")
    monkeypatch.setattr(qa_bench, "make_client", lambda *a: client)
    monkeypatch.setattr(qa_bench, "init_resources", lambda: (None,) * 5)
    monkeypatch.setattr(qa_bench, "answer_classic", lambda *a: (answer, []))
    monkeypatch.setattr(qa_bench, "answer_agent", lambda *a: (answer, [], {}))
    monkeypatch.setattr(qa_bench, "retrieve_and_answer_classic", lambda *a: (answer, []))
    out = tmp_path / "out.json"
    argv = ["qa_bench", "--gold", str(PROFILE), "--limit", "11", "--out", str(out), "--workers", "1"]
    # Execute only #11 while the real reader validates all 115 rows.
    original = qa_bench._project_questions
    monkeypatch.setattr(qa_bench, "_project_questions", lambda data, limit: [
        r for r in original(data, limit) if r["id"] == 11])
    argv += ["--layered"] if mode == "layered" else ["--path", mode]
    monkeypatch.setattr(sys, "argv", argv)
    qa_bench.main()
    result = json.loads(out.read_bytes())
    actual = result["details"][0]
    key = "generation_verdict" if mode == "layered" else "verdict"
    assert actual[key] == ("❌" if wrong_stat else "✅" if qualified else "⚠️")
    assert actual["factual_verdict"] == ("❌" if wrong_stat else "✅")
    assert actual["source_coverage_check"]["status"] == ("qualified" if qualified else "missing")
    assert result["summary"]["source_coverage"]["checked"] == 1
    assert result["summary"]["source_coverage"]["full_current_body_verified"] is False
    assert result["summary"]["gold_source"]["total"] == 115
    assert any("current" in c["messages"][0]["content"] for c in calls)


def test_unchanged_legacy_workers_do_not_add_coverage_calls(monkeypatch):
    row = qa_bench.load_questions(limit=1)[0]
    client, calls = client_with([{"T": ["3"]}])
    monkeypatch.setattr(qa_bench, "make_client", lambda *a: client)
    monkeypatch.setattr(qa_bench, "answer_classic", lambda *a: ("T=3", []))
    result = qa_bench.run_one((None,) * 5 + ("classic", "DeepSeek", "offline"), row)
    assert "source_coverage_check" not in result
    assert len(calls) == 1


@pytest.mark.parametrize("qid,case", [(114, "historical_both"), (115, "historical_both"),
    (114, "ordinary_180"), (114, "archived_200"), (114, "unqualified_current"),
    (115, "unqualified_current"), (115, "invented_legends"), (114, "unknown_only"),
    (115, "unknown_only"), (76, "related_variant"), (113, "old_355"), (118, "old_prices")])
def test_actual_worker_dated_prices_identity_and_generic_unknown_controls(monkeypatch, qid, case):
    row = next(r for r in profile()["details"] if r["id"] == qid)
    answer = {
        "historical_both": row["gold"],
        "ordinary_180": "Armour of Antilochus is now ordinary Marneus Calgar, 180 points.",
        "archived_200": "Armour of Antilochus uses historical ordinary Calgar's 200-point rules.",
        "unqualified_current": f"Latest price is {155 if qid == 114 else 80} points.",
        "invented_legends": "Pedro is now Legends because no current MFM listing exists; old price 80.",
        "unknown_only": "I don't know the current price; the current body is unavailable.",
        "related_variant": "Death Company Dreadnought WITH MAGNA-GRAPPLE: M=8 T=9.",
        "old_355": "Official MFM September 30 2026: Roboute Guilliman 355 points; full Codex unverified.",
        "old_prices": "Official MFM September 30 2026: CSM130 DG110 TS110 WE120; Codex unverified.",
    }[case]
    wrong = case in {"ordinary_180", "archived_200", "related_variant", "old_355", "old_prices", "unknown_only"}
    prohibited = case in {"ordinary_180", "archived_200", "related_variant", "unqualified_current", "invented_legends"}
    qualified = case in {"historical_both", "old_355", "old_prices"}
    factual = {"M": ["8"], "T": ["9"]} if qid == 76 else "❌" if wrong else "✅"
    reply = coverage_reply(row["coverage_contract"], answer, qualified)
    if prohibited:
        key = {"ordinary_180": "identity_mix", "archived_200": "identity_mix",
               "related_variant": "related_variant", "unqualified_current": "unqualified_current_price",
               "invented_legends": "invented_status"}[case]
        reply["prohibitions"][key] = {"present": True, "quote": answer}
    client, calls = client_with([factual, reply])
    monkeypatch.setattr(qa_bench, "make_client", lambda *a: client)
    monkeypatch.setattr(qa_bench, "answer_agent", lambda *a: (answer, [], {}))
    result = qa_bench.run_one((None,) * 5 + ("agent", "DeepSeek", "offline-judge"), row)
    assert result["verdict"] == ("✅" if case == "historical_both" else "❌")
    if case in {"old_355", "old_prices"}:
        assert result["source_coverage_check"]["status"] == "qualified"
        assert result["factual_verdict"] == result["verdict"] == "❌"
    assert len(calls) == 2


def test_fixture_responses_are_strict_and_do_not_use_metadata_quotes():
    row = next(r for r in profile()["details"] if r["id"] == 114)
    answer = "155 points."
    for field, value in [("satisfied", "true"), ("quote", row["coverage_contract"]["requirements"]["dated_price"])]:
        reply = coverage_reply(row["coverage_contract"], answer)
        reply["requirements"]["dated_price"][field] = value
        client, _ = client_with([reply])
        check = qa_bench.check_source_coverage("offline", client, row, answer)
        assert check["status"] == "unverified"


def test_same_profile_results_compare_and_cross_gold_refuses(tmp_path, capsys):
    import compare_bench_runs
    old = json.loads((ROOT / "qa_gold.json").read_bytes())
    new = profile()

    def write(name, doc):
        path = tmp_path / name
        rows = [{**r, "gold_metadata": {k: v for k, v in r.items()
                 if k not in ("id", "question", "faction", "gold", "gold_type")},
                 "verdict": "✅"} for r in doc["details"]]
        path.write_text(json.dumps({"details": rows}), encoding="utf-8")
        return str(path)

    base, candidate = write("base.json", old), write("candidate.json", new)
    assert compare_bench_runs.main(["compare", candidate, candidate]) == 0
    capsys.readouterr()
    assert compare_bench_runs.main(["compare", base, candidate]) == 2
    output = capsys.readouterr().out
    assert "#114 gold" in output and "#34 gold" in output
    assert compare_bench_runs.main(["compare", "--allow-different-gold", base, candidate]) == 0
    assert "not an application regression claim" in capsys.readouterr().out


def test_complete_115_row_cli_runs_without_exclusion_or_coverage_auto_award(tmp_path, monkeypatch):
    doc = profile()
    rows = {r["question"]: r for r in doc["details"]}
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if kwargs.get("response_format", {}).get("type") == "json_object":
            request = json.loads(kwargs["messages"][-1]["content"])
            contract = request["contract"]
            text = json.dumps(coverage_reply(contract, request["answer"]))
        else:
            text = "✅ offline fixture"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "offline-sentinel")
    monkeypatch.setattr(qa_bench, "make_client", lambda *a: client)
    monkeypatch.setattr(qa_bench, "init_resources", lambda: (None,) * 5)
    monkeypatch.setattr(qa_bench, "answer_agent", lambda *a: (rows[a[-1]]["gold"] or "Intrinsic fixture", [], {}))
    # Exercise the real mechanical decision function with a fake extraction API.
    # #11 is deliberately wrong while its coverage API reports all qualifiers met.
    def extract(model, client, question, answer, required):
        fields = qa_bench.parse_gold_fields(rows[question]["gold"])
        values = {f: fields[f] for f in required}
        if rows[question]["id"] == 11:
            values["W"] = ["9"]
        return values

    monkeypatch.setattr(qa_bench, "extract_answer_fields", extract)
    out = tmp_path / "full-offline.json"
    monkeypatch.setattr(sys, "argv", ["qa_bench", "--gold", str(PROFILE), "--path", "agent",
        "--workers", "6", "--out", str(out)])
    qa_bench.main()
    result = json.loads(out.read_bytes())
    assert [r["id"] for r in result["details"]] == [r["id"] for r in doc["details"]]
    assert len(result["details"]) == result["summary"]["results"]["total"] == 115
    assert result["summary"]["source_coverage"]["checked"] == 21
    assert result["summary"]["source_coverage"]["statuses"]["qualified"] == 21
    wrong = next(r for r in result["details"] if r["id"] == 11)
    assert wrong["source_coverage_check"]["status"] == "qualified"
    assert wrong["factual_verdict"] == wrong["verdict"] == "❌"
    assert result["summary"]["results"]["wrong"] >= 1
    assert result["summary"]["accuracy"] < 100
    # These fixtures test execution and ceilings, not the semantic judge's accuracy.
    assert len([c for c in calls if "contract" in c["messages"][-1]["content"]]) == 21
