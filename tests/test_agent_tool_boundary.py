"""Public model arguments must not expose direct Python injection helpers."""
from collections import UserDict
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from agent.context import SessionContext
from agent.loop import AgentLoop
from agent import tools
from agent.llm_client import _TOOL_ARG_HINTS
from web_api import main


# Reviewed against the actual model catalog, independently of raw signatures.
PUBLIC_ARGS = {
    "list_faction_units": {"faction": "Space Marines", "offset": 1, "limit": 2},
    "search_wiki": {"query": "fixture"},
    "get_entity": {"name_or_id": "fixture"},
    "get_keyword_definition": {"keyword": "fixture"},
    "judge_fight_order": {"ctx": {"attacker_charged": True}},
    "simulate_combat": {"attacker": "fixture", "defender": "target",
                        "options": {"n": 100, "seed": 9, "phase": "melee"}},
    "validate_roster": {"roster_text": "Faction: Space Marines"},
    "critique_roster": {"roster_text": "Faction: Space Marines"},
    "calc_points": {"unit_list": ["fixture"]},
    "get_datasheet": {"name_or_id": "fixture"},
    "archive_answer": {"title": "Fixture", "content": "Fixture content"},
    "rag_search": {"query": "fixture"},
    "entity_resolver": {"name": "fixture"},
}
INTERNAL_ARGS = ("db_path", "resolver", "wiki_root", "app_path", "core_rules_dir",
                 "app_module", "callback", "context", "client", "source_dir")
SOURCE = {"book": "Synthetic official reference", "page": 3}
NOTE = "Official preview. " + "Context. " * 80 + "Released codex not verified."
EVIDENCE = {"found": True, "canonical_id": "fixture",
            "units": [{"name_en": "Canonical fixture", "points": 355}],
            "official_sources": [SOURCE], "source_note": NOTE,
            "page": {"body": "Verified synthetic fact"}, "datasheet": {}}


class ScriptedLLM:
    def __init__(self, steps):
        self.steps = list(steps)
        self.messages = []

    def classify_intent(self, question):
        return "查"

    def next_step(self, messages, specs):
        self.messages.append(deepcopy(messages))
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def action(tool, args):
    return {"type": "tool_call", "tool": tool, "args": args}


@pytest.mark.parametrize("tool", PUBLIC_ARGS)
@pytest.mark.parametrize("internal", INTERNAL_ARGS)
def test_every_registered_tool_rejects_internal_or_unknown_arguments(tool, internal):
    calls = []

    def permissive_spy(**kwargs):
        calls.append(kwargs)
        return deepcopy(EVIDENCE)

    args = {**deepcopy(PUBLIC_ARGS[tool]), internal: "synthetic-capability"}
    original = deepcopy(args)
    llm = ScriptedLLM([action(tool, args), {"type": "final", "content": "must not finish"}])
    result = AgentLoop(llm, tools={tool: permissive_spy}).run("Verify")
    assert not calls, "Reject before invocation, including callables accepting **kwargs"
    assert result.degraded
    assert "公开参数契约" in result.answer
    assert "synthetic-capability" not in result.answer
    assert args == original and len(llm.messages) == 1


@pytest.mark.parametrize("tool", PUBLIC_ARGS)
@pytest.mark.parametrize("mapping", (dict, UserDict))
def test_advertised_required_and_optional_arguments_are_preserved(tool, mapping):
    calls = []

    def spy(**kwargs):
        calls.append(kwargs)
        return deepcopy(EVIDENCE)

    args = mapping(deepcopy(PUBLIC_ARGS[tool]))
    original = deepcopy(args)
    llm = ScriptedLLM([action(tool, args), {"type": "final", "content": "Verified",
                                          "sources": [SOURCE]}])
    result = AgentLoop(llm, tools={tool: spy}).run("Verify")
    assert calls == [original] and args == original
    # Useful evidence retains its whole source warning even when final prose
    # omits it; mapping/non-evidence tools keep their original short response.
    qualified = tool in {"search_wiki", "get_entity", "get_keyword_definition", "calc_points", "get_datasheet"}
    expected = "Verified\n\n" + NOTE if qualified else "Verified"
    assert not result.degraded and result.answer == expected
    assert result.tool_calls == [tool] and result.sources == [SOURCE]


@pytest.fixture
def databases(tmp_path, monkeypatch):
    paths = []
    for name, label, points in [("canonical", "Canonical fixture", 355),
                                ("foreign", "SYNTHETIC_OUTSIDE_CANONICAL_MARKER", 123)]:
        path = tmp_path / (name + ".sqlite")
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE units(id TEXT, name_en TEXT, points_json TEXT)")
            conn.execute("INSERT INTO units VALUES (?, ?, ?)",
                         ("fixture", label, json.dumps({"points": points})))
        conn.close()
        paths.append(path)
    monkeypatch.setattr(tools, "DB_PATH", paths[0])
    before = [p.read_bytes() for p in paths]
    yield paths
    assert [p.read_bytes() for p in paths] == before


@pytest.mark.parametrize("route", ("/chat/sync", "/chat"))
@pytest.mark.parametrize("forbidden", (True, False))
def test_real_registered_calc_points_api_boundary(databases, monkeypatch, route, forbidden):
    canonical, foreign = databases
    reads = []
    real_calc = tools._calc_points_impl

    def track_calc(db_path, unit_list):
        reads.append(Path(db_path))
        return real_calc(db_path, unit_list)

    monkeypatch.setattr(tools, "_calc_points_impl", track_calc)

    class EchoToolLLM:
        def classify_intent(self, question):
            return "算"

        def next_step(self, messages, specs):
            responses = [m for m in messages if m["role"] == "tool"]
            if responses:
                return {"type": "final", "content": json.dumps(responses[-1]["content"]),
                        "sources": []}
            args = {"unit_list": ["fixture"]}
            if forbidden:
                args["db_path"] = str(foreign)
            return action("calc_points", args)

    # No provider or retrieval traffic; default registered tools remain real.
    monkeypatch.setattr(main, "retrieval_enabled", lambda: True)
    monkeypatch.setattr(main, "_make_clients", lambda: (EchoToolLLM(), None))
    monkeypatch.setitem(tools.TOOLS, "rag_search", lambda query: {"passages": []})
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.post(route, json={"question": "Synthetic tool boundary"})
    assert response.status_code == 200
    assert "SYNTHETIC_OUTSIDE_CANONICAL_MARKER" not in response.text
    assert foreign not in reads
    if forbidden:
        assert reads == [] and "公开参数契约" in response.text
    else:
        assert reads == [canonical]
        assert "Canonical fixture" in response.text and "355" in response.text


def test_direct_python_database_override_remains_supported(databases):
    canonical, foreign = databases
    assert tools.DB_PATH == canonical
    assert tools.calc_points(["fixture"])["units"][0]["points"] == 355
    result = tools.calc_points(["fixture"], db_path=foreign)
    assert result["units"][0]["points"] == 123
    assert result["units"][0]["name_en"] == "SYNTHETIC_OUTSIDE_CANONICAL_MARKER"


@pytest.mark.parametrize("synthesis_only", (True, False))
def test_later_forbidden_action_keeps_whole_fact_citation_and_source_note(synthesis_only):
    forbidden_calls, rag_calls = [], []
    llm = ScriptedLLM([action("calc_points", {"unit_list": ["fixture"]}),
                      action("get_entity", {"name_or_id": "fixture", "wiki_root": "foreign"})])
    session = SessionContext()
    result = AgentLoop(llm, tools={
        "calc_points": lambda unit_list: deepcopy(EVIDENCE),
        "get_entity": lambda **kwargs: forbidden_calls.append(kwargs),
        "rag_search": lambda query: rag_calls.append(query),
    }, max_steps=1 if synthesis_only else 6).run("Verify both", session)
    assert not forbidden_calls and not rag_calls
    assert result.degraded and result.tool_calls == ["calc_points"]
    assert "355" in result.answer and NOTE in result.answer
    assert "未确认" in result.answer and "公开参数契约" in result.answer
    assert result.sources == [SOURCE]
    assert session.history[-1]["content"] == result.answer
    assert len(llm.messages) == 2


def test_forbidden_action_after_mapping_only_still_uses_one_fallback():
    calls = []
    llm = ScriptedLLM([action("entity_resolver", {"name": "fixture"}),
                      action("calc_points", {"unit_list": ["fixture"], "db_path": "foreign"})])

    def rag(query):
        calls.append(query)
        return {"passages": [{"text": "Fixture fallback", **SOURCE}]}

    result = AgentLoop(llm, tools={"entity_resolver": lambda name: {"canonical_id": "fixture"},
                                  "calc_points": lambda **kwargs: pytest.fail("must not invoke"),
                                  "rag_search": rag}).run("Verify")
    assert calls == ["Verify"] and result.degraded
    assert result.tool_calls == ["entity_resolver", "rag_search"]
    assert "Fixture fallback" in result.answer and "355" not in result.answer


def test_undeclared_custom_tool_is_not_inferred_from_signature():
    calls = []

    def custom(public="default"):
        calls.append(public)
        return {"ok": True}

    llm = ScriptedLLM([action("custom", {"public": "fixture"}),
                      {"type": "final", "content": "must not finish"}])
    result = AgentLoop(llm, tools={"custom": custom}).run("Verify")
    assert not calls and result.degraded and "公开参数契约" in result.answer


def test_explicit_custom_contract_allows_public_arguments_only():
    calls = []

    def custom(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    contracts = {"custom": {"public"}}
    llm = ScriptedLLM([action("custom", {"public": "fixture"}),
                      {"type": "final", "content": "Verified"}])
    loop = AgentLoop(llm, tools={"custom": custom}, public_tool_arguments=contracts)
    contracts["custom"].add("db_path")  # Caller mutation cannot expand a running loop.
    result = loop.run("Verify")
    assert not result.degraded and calls == [{"public": "fixture"}]
    loop.llm = ScriptedLLM([action("custom", {"public": "fixture", "db_path": "foreign"})])
    rejected = loop.run("Verify")
    assert rejected.degraded and calls == [{"public": "fixture"}]


def test_custom_contract_cannot_expand_a_registered_tool():
    with pytest.raises(ValueError, match="registered"):
        AgentLoop(ScriptedLLM([]), tools={"calc_points": lambda **kwargs: None},
                  public_tool_arguments={"calc_points": {"unit_list", "db_path"}})


def test_public_contract_matches_all_registered_model_catalog_entries():
    from agent.tools import PUBLIC_TOOL_ARGUMENTS
    assert set(PUBLIC_TOOL_ARGUMENTS) == set(tools.TOOLS) == set(_TOOL_ARG_HINTS)
    assert {name: set(args) for name, args in PUBLIC_TOOL_ARGUMENTS.items()} == {
        name: set(args) for name, args in PUBLIC_ARGS.items()}
    with pytest.raises(TypeError):
        PUBLIC_TOOL_ARGUMENTS["calc_points"] = frozenset({"db_path"})
