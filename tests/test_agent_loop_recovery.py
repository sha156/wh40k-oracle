"""Paired evidence/no-evidence recovery tests; no assets or provider calls."""
from __future__ import annotations

from collections import UserDict
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from agent.context import SessionContext
from agent.loop import AgentLoop
from agent.llm_client import OpenAICompatLLMClient, _extract_json_object
from wiki_engine.models import WikiPage, WikiPageFrontmatter


FAILURES = ("provider", "tool_twice", "empty_twice")
MFM = {"url": "https://example.test/mfm", "fetched_at": "2026-09-14"}
ARCHIVE = {"url": "https://example.test/archive", "source_id": "calgar-old"}
RULE = {"book": "Official Core Rules", "page": 15}


def evidence_case(kind):
    if kind == "points":
        return "calc_points", {
            "found": True, "units": [{"name_en": "Roboute Guilliman", "points": 355}],
            "official_sources": [MFM],
        }, ["Roboute Guilliman", "355"], [MFM]
    if kind == "historical":
        record = {"name_en": "Marneus Calgar", "historical_points": 200,
                  "is_current": False, "source_url": ARCHIVE["url"],
                  "source_id": ARCHIVE["source_id"], "faction_zh": "Space Marines",
                  "source_scope": "Deleted community cache; not current rules.",
                  "identity_scope": {
                      "composition_evidence": "Ordinary Calgar with two Victrix guards",
                      "model_counts": {"calgar": 1, "guard_models": 2},
                      "variant_boundary": "Not Armour of Antilochus.",
                  }}
        return "calc_points", {"found": True, "units": [
            {"name_en": "Marneus Calgar", "points": None, "historical_points": 200,
             "historical_record": record},
            {"name_en": "Roboute Guilliman", "points": 355},
        ], "official_sources": [MFM]}, [
            "200", "355", "非现行", record["identity_scope"]["composition_evidence"],
            record["identity_scope"]["variant_boundary"], record["source_scope"],
            "Space Marines",
        ], [MFM, ARCHIVE]
    if kind == "cross_faction":
        return "calc_points", {"found": True, "units": [{
            "name_en": "Helbrute", "points": 140, "same_name_other_factions": [
                {"candidate": "Helbrute (CSM)", "points": 140},
                {"candidate": "Helbrute (DG)", "points": 185},
            ],
        }], "official_sources": [MFM]}, [
            "Helbrute (CSM)：点数 140", "Helbrute (DG)：点数 185", "必须消歧",
        ], [MFM]
    if kind == "fuzzy":
        return "calc_points", {"found": True, "units": [{
            "query": "Hellbrute", "name_en": "Helbrute", "points": 140,
            "resolved_via": {"confidence": "fuzzy", "canonical_id": "csm-helbrute"},
        }]}, ["Hellbrute", "Helbrute", "140", "模糊匹配，需核对身份"], []
    if kind == "preview":
        note = "Official preview: current MFM points; released codex rules not verified."
        scope = "MFM proves points only; attributes have not been rechecked."
        return "get_datasheet", {"found": True, "datasheet": {
            "unit_id": "ork-nazdreg", "name_en": "Nazdreg", "faction": "Orks",
            "points_min": 140, "models": [{"name": "Nazdreg", "t": "6", "w": "7"}],
            "source_note": note,
        }, "source_scope": scope, "official_sources": [MFM]}, [
            "Nazdreg", "Orks", "140", "T 6", "W 7", note, scope,
        ], [MFM]
    if kind == "rules":
        page = WikiPage(source_rel="core-rules/reroll.md", fm=WikiPageFrontmatter(
            id="reroll", name_en="Command Re-roll", faction="Core Rules", sources=[RULE]),
            body="Re-roll one eligible dice roll.")
        return "get_entity", {"found": True, "page": page,
                              "source_scope": "Associated references, not per-field provenance."}, [
            "Command Re-roll", "Re-roll one eligible dice roll.", "Core Rules",
            "Associated references, not per-field provenance.",
        ], [RULE]
    raise AssertionError(kind)


class RecoveryLLM:
    def __init__(self, first_tool, failure):
        self.steps = [{"type": "tool_call", "tool": first_tool, "args": {}}]
        if failure == "provider":
            self.steps.append(TimeoutError("injected synthesis timeout"))
        elif failure == "tool_twice":
            self.steps.extend([{"type": "tool_call", "tool": "broken_lookup", "args": {}}] * 2)
        else:
            self.steps.extend([{"type": "final", "content": "   "}] * 2)
        self.calls = []

    def classify_intent(self, user_input):
        return "查"

    def next_step(self, messages, tool_specs):
        self.calls.append(deepcopy(messages))
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def recovery_run(tool, evidence, failure, session=None):
    llm = RecoveryLLM(tool, failure)
    rag_calls = []

    def empty_rag(query):
        rag_calls.append(query)
        return {"found": False, "passages": []}

    def broken_lookup():
        raise RuntimeError("injected tool failure")

    session = session if session is not None else SessionContext()
    result = AgentLoop(llm, tools={tool: lambda: evidence, "rag_search": empty_rag,
                                  "broken_lookup": broken_lookup},
                       public_tool_arguments={"broken_lookup": set()}).run(
                                      "Compare these verified rules and points", session)
    return result, llm, rag_calls, session


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize("kind", ("points", "historical", "cross_faction", "fuzzy", "preview", "rules"))
def test_recovery_preserves_verified_evidence_and_qualifiers(kind, failure):
    tool, evidence, expected, sources = evidence_case(kind)
    original = deepcopy(evidence)
    result, llm, rag_calls, session = recovery_run(tool, evidence, failure)

    assert not rag_calls, "Automatic RAG must not replace already verified evidence"
    assert result.degraded is True  # Partial emergency answer, never successful synthesis.
    assert result.tool_calls == [tool] + (["broken_lookup"] if failure == "tool_twice" else [])
    for fragment in expected:
        assert fragment in result.answer
    for source in sources:
        assert source in result.sources
    assert "未确认" in result.answer and "不能据此否定" in result.answer
    if kind == "cross_faction":
        assert "Helbrute：点数 140" not in result.answer
    assert len(llm.calls) == (2 if failure == "provider" else 3)
    assert llm.calls[1][-1]["content"] == original
    assert evidence == original
    assert session.history[-1] == {"role": "assistant", "content": result.answer}


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize("tool,evidence", [
    ("entity_resolver", {"canonical_id": "guilliman", "confidence": "exact"}),
    ("get_keyword_definition", {"found": False, "page": None}),
    ("search_wiki", {"found": True, "page": None,
                     "results": [{"title": "Guilliman", "path": "units/guilliman.md"}]}),
])
def test_mapping_miss_and_title_only_still_use_rag(tool, evidence, failure):
    result, _, rag_calls, _ = recovery_run(tool, evidence, failure)
    assert len(rag_calls) == 1
    assert result.degraded is True and result.tool_calls[-1] == "rag_search"
    assert "355" not in result.answer
    assert result.sources == []
    assert result.tool_calls == [tool] + (["broken_lookup"] if failure == "tool_twice" else []) + ["rag_search"]


def test_old_session_evidence_does_not_suppress_fresh_lookup_fallback():
    session = SessionContext()
    session.append_turn("assistant", "Roboute Guilliman is 355 points, previously verified.")
    result, _, rag_calls, _ = recovery_run(
        "entity_resolver", {"canonical_id": "guilliman"}, "provider", session)
    assert len(rag_calls) == 1
    assert "355" not in result.answer


@pytest.mark.parametrize("kind", ("points", "historical", "cross_faction", "fuzzy", "preview", "rules"))
def test_forced_final_failure_preserves_same_evidence_and_references(kind):
    tool, evidence, expected, sources = evidence_case(kind)
    llm = RecoveryLLM(tool, "provider")
    result = AgentLoop(llm, tools={tool: lambda: evidence}, max_steps=1).run("Verify")
    assert result.degraded is True and result.tool_calls == [tool]
    for fragment in expected:
        assert fragment in result.answer
    for source in sources:
        assert source in result.sources
    assert len(llm.calls) == 2


@pytest.mark.parametrize("failure", FAILURES)
def test_multiple_successes_keep_entire_successful_trace_and_unique_sources(failure):
    tool, points, _, _ = evidence_case("points")
    _, rules, _, _ = evidence_case("rules")
    points["official_sources"].extend([MFM, None, "invalid"])
    rules["sources"] = [MFM, RULE]
    llm = RecoveryLLM(tool, failure)
    llm.steps.insert(1, {"type": "tool_call", "tool": "get_entity", "args": {}})

    def broken_lookup():
        raise RuntimeError("injected tool failure")

    result = AgentLoop(llm, tools={tool: lambda: points, "get_entity": lambda: rules,
                                  "broken_lookup": broken_lookup},
                       public_tool_arguments={"broken_lookup": set()}).run("Verify both")
    assert result.tool_calls == [tool, "get_entity"] + (["broken_lookup"] if failure == "tool_twice" else [])
    assert "355" in result.answer and "Re-roll one eligible dice roll." in result.answer
    assert result.sources == [MFM, RULE]


@pytest.mark.parametrize("tool", ("get_datasheet", "get_entity"))
def test_archived_card_only_recovery_keeps_verified_identity_boundary(tool):
    _, evidence, expected, _ = evidence_case("historical")
    record = evidence["units"][0]["historical_record"]
    result, _, rag, _ = recovery_run(tool, {"found": True, "historical_record": record}, "provider")
    assert not rag
    assert "200" in result.answer and "非现行" in result.answer
    assert record["identity_scope"]["composition_evidence"] in result.answer
    assert record["identity_scope"]["variant_boundary"] in result.answer
    assert ARCHIVE in result.sources
    assert "355" not in result.answer


def test_long_excerpt_does_not_truncate_preview_scope_note():
    note = "Official preview. " + "Context. " * 80 + "Released codex rules not verified."
    page = {"fm": {"name_en": "Preview", "faction": "Orks", "sources": [RULE]},
            "body": "Excerpt " * 150}
    result, _, _, _ = recovery_run("get_entity", {"found": True, "page": page, "source_scope": note}, "provider")
    assert note in result.answer and RULE in result.sources
    assert "其余内容暂列为未确认" in result.answer


def test_cross_faction_candidates_keep_fuzzy_query_qualifier_together():
    tool, evidence, _, _ = evidence_case("cross_faction")
    evidence["units"][0].update(query="Hellbrute", resolved_via={"confidence": "fuzzy"})
    result, _, _, _ = recovery_run(tool, evidence, "provider")
    for line in result.answer.splitlines()[1:]:
        assert "必须消歧" in line and "Hellbrute" in line and "模糊匹配，需核对身份" in line
    assert "Helbrute：点数 140" not in result.answer


@pytest.mark.parametrize("with_evidence", (True, False))
def test_invalid_action_recovers_inside_loop_context(with_evidence):
    tool, evidence, _, _ = evidence_case("points") if with_evidence else (
        "entity_resolver", {"canonical_id": "guilliman"}, [], [])
    llm = RecoveryLLM(tool, "provider")
    llm.steps[-1] = None
    result = AgentLoop(llm, tools={tool: lambda: evidence,
                                  "rag_search": lambda query: {"passages": []}}).run("Verify")
    assert result.tool_calls == [tool] + ([] if with_evidence else ["rag_search"])
    assert ("355" in result.answer) is with_evidence


MALFORMED_ACTIONS = [
    pytest.param({"type": "tool_call", "tool": value, "args": {}}, id="tool-" + name)
    for name, value in [("list", ["invalid"]), ("dict", {"name": "invalid"}),
                        ("number", 12), ("bool", True), ("null", None),
                        ("empty", ""), ("whitespace", " \t"), ("tuple", ("invalid",))]
] + [
    pytest.param({"type": "tool_call", "args": {}}, id="tool-missing"),
] + [
    pytest.param({"type": "tool_call", "tool": "must_not_execute", "args": value},
                 id="args-" + name)
    for name, value in [("list", [1]), ("empty-list", []), ("string", "{}"),
                        ("empty-string", ""), ("null", None), ("bool", False),
                        ("zero", 0), ("number", 12), ("non-string-key", {1: "value"})]
] + [
    pytest.param({"type": value, "tool": "must_not_execute", "args": {}},
                 id="type-" + name)
    for name, value in [("unknown", "unknown"), ("list", ["tool_call"]),
                        ("dict", {"name": "tool_call"}), ("null", None),
                        ("number", 12), ("case", "TOOL_CALL")]
] + [
    pytest.param({"tool": "must_not_execute", "args": {}}, id="type-missing"),
] + [
    pytest.param({"type": "final", "content": value}, id="content-" + name)
    for name, value in [("list", ["Unsupported conclusion"]),
                        ("dict", {"text": "Unsupported conclusion"}),
                        ("number", 12), ("bool", False), ("null", None)]
] + [
    pytest.param({"type": "final", "content": "Unsupported conclusion", "sources": value},
                 id="sources-" + name)
    for name, value in [("dict", MFM), ("string", "MFM"), ("null", None),
                        ("mixed", [MFM, "invalid"])]
]


def malformed_run(tool, evidence, action, *, session=None, max_steps=6):
    llm = RecoveryLLM(tool, "provider")
    llm.steps[-1] = deepcopy(action)
    rag_calls, forbidden_calls = [], []

    def rag(query):
        rag_calls.append(query)
        return {"passages": []}

    def forbidden(**args):
        forbidden_calls.append(args)
        return {"unverified": "must never execute"}

    session = session if session is not None else SessionContext()
    result = AgentLoop(llm, tools={tool: lambda: evidence, "rag_search": rag,
                                  "must_not_execute": forbidden}, max_steps=max_steps,
                       public_tool_arguments={"must_not_execute": set()}).run(
                                      "Verify points and rules", session)
    return result, llm, rag_calls, forbidden_calls, session


@pytest.mark.parametrize("action", MALFORMED_ACTIONS)
@pytest.mark.parametrize("kind", ("points", "historical", "cross_faction", "fuzzy", "preview", "rules"))
def test_malformed_later_action_preserves_facts_sources_and_scope(kind, action):
    tool, evidence, expected, sources = evidence_case(kind)
    note = "September 14 baseline fixture. " + "Context. " * 80 + "Later promotion not verified."
    evidence["note"] = note
    original = deepcopy(evidence)
    result, llm, rag, forbidden, session = malformed_run(tool, evidence, action)
    assert not rag and not forbidden
    assert result.degraded is True and result.tool_calls == [tool]
    for fragment in expected + [note, "未确认", "不能据此否定"]:
        assert fragment in result.answer
    for source in sources:
        assert source in result.sources
    assert "Unsupported conclusion" not in result.answer
    if kind == "cross_faction":
        assert "Helbrute：点数 140" not in result.answer
    assert len(llm.calls) == 2  # Reject once; no repair/synthesis request amplification.
    assert llm.calls[1][-1]["content"] == original and evidence == original
    assert session.history[-1] == {"role": "assistant", "content": result.answer}


@pytest.mark.parametrize("action", MALFORMED_ACTIONS)
@pytest.mark.parametrize("control", ("mapping", "missing", "titles", "history"))
def test_malformed_action_without_fresh_facts_still_uses_one_rag(control, action):
    tool, evidence = {
        "mapping": ("entity_resolver", {"canonical_id": "guilliman", "confidence": "exact"}),
        "missing": ("get_keyword_definition", {"found": False, "page": None}),
        "titles": ("search_wiki", {"found": True, "results": [{"title": "Guilliman"}]}),
        "history": ("entity_resolver", {"canonical_id": "guilliman"}),
    }[control]
    session = SessionContext()
    if control == "history":
        session.append_turn("assistant", "Earlier verified Guilliman 355; not fresh evidence.")
    result, llm, rag, forbidden, session = malformed_run(tool, evidence, action, session=session)
    assert len(rag) == 1 and not forbidden
    assert result.degraded is True and result.tool_calls == [tool, "rag_search"]
    assert result.sources == [] and "355" not in result.answer
    assert "Unsupported conclusion" not in result.answer
    assert len(llm.calls) == 2
    assert session.history[-1]["content"] == result.answer


@pytest.mark.parametrize("action", MALFORMED_ACTIONS)
def test_synthesis_only_malformed_action_uses_same_boundary(action):
    tool, evidence, expected, sources = evidence_case("historical")
    result, llm, rag, forbidden, _ = malformed_run(tool, evidence, action, max_steps=1)
    assert not rag and not forbidden
    assert result.degraded is True and result.tool_calls == [tool]
    assert len(llm.calls) == 2
    for fragment in expected:
        assert fragment in result.answer
    for source in sources:
        assert source in result.sources


def test_real_json_parser_accepts_list_tool_then_loop_recovers_locally():
    action = _extract_json_object(json.dumps({"type": "tool_call", "tool": ["invalid"], "args": {}}))
    tool, evidence, expected, sources = evidence_case("points")
    result, llm, rag, forbidden, _ = malformed_run(tool, evidence, action)
    assert not rag and not forbidden and len(llm.calls) == 2
    assert result.degraded and result.tool_calls == [tool]
    assert all(fragment in result.answer for fragment in expected)
    assert result.sources == sources


@pytest.mark.parametrize("with_evidence", (True, False))
def test_provider_parsed_malformed_action_does_not_trigger_json_retry(with_evidence):
    tool, evidence, expected, sources = evidence_case("points") if with_evidence else (
        "entity_resolver", {"canonical_id": "guilliman"}, [], [])
    responses = iter(["查", json.dumps({"type": "tool_call", "tool": tool, "args": {}}),
                      '{"type":"tool_call","tool":["invalid"],"args":{}}'])
    requests, rag_calls = [], []

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(responses)))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm = OpenAICompatLLMClient(client=client)

    def rag(query):
        rag_calls.append(query)
        return {"passages": []}

    result = AgentLoop(llm, tools={tool: lambda: evidence, "rag_search": rag}).run("Verify")
    assert result.degraded and result.tool_calls == [tool] + ([] if with_evidence else ["rag_search"])
    assert len(requests) == 3  # One classification plus two JSON-mode steps; no parse retry.
    assert all(request["response_format"] == {"type": "json_object"} for request in requests[1:])
    assert len(rag_calls) == (0 if with_evidence else 1)
    assert ("355" in result.answer) is with_evidence
    assert all(fragment in result.answer for fragment in expected)
    assert result.sources == sources


@pytest.mark.parametrize("args", ({"unit_list": ["guilliman"]}, UserDict({"unit_list": ["guilliman"]})))
def test_valid_mapping_arguments_and_final_fields_are_unchanged(args):
    tool, evidence, _, sources = evidence_case("points")
    original = deepcopy(args)
    llm = RecoveryLLM(tool, "provider")
    llm.steps = [{"type": "tool_call", "tool": tool, "args": args},
                 {"type": "final", "content": "Reviewed baseline 355.", "sources": sources}]
    calls = []

    def lookup(**values):
        calls.append(values)
        return evidence

    result = AgentLoop(llm, tools={tool: lookup}).run("Verify")
    assert result.answer == "Reviewed baseline 355." and not result.degraded
    assert result.tool_calls == [tool] and result.sources == sources
    assert calls == [original] and args == original and len(llm.calls) == 2


def test_omitted_args_and_unknown_string_tool_keep_existing_recovery():
    tool, evidence, _, sources = evidence_case("points")
    llm = RecoveryLLM(tool, "provider")
    llm.steps = [{"type": "tool_call", "tool": "unknown_tool", "args": {}},
                 {"type": "tool_call", "tool": tool},
                 {"type": "final", "content": "Reviewed baseline 355."}]
    result = AgentLoop(llm, tools={tool: lambda: evidence}).run("Verify")
    assert not result.degraded and result.tool_calls == [tool]
    assert result.answer == "Reviewed baseline 355." and result.sources == sources
    assert len(llm.calls) == 3
    assert "unknown_tool" in llm.calls[1][-1]["content"]["error"]
