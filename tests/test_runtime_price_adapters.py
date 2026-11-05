"""Source-only prices through real adapters, dispatch, recovery and formatter."""
import copy
import hashlib
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from agent.context import SessionContext
from agent.loop import AgentLoop, _has_usable_evidence
from db_compile.coverage_notes import CoverageError, describe_coverage
from db_compile.entity_resolver import EntityResolver
from db_compile.source_coverage import apply_coverage
from tests.test_agent_loop import ScriptedLLM
from tests.test_source_only_price_identity import CAPTURED, price_db
from web_api.formatter import _derive_entity_card, _evidence_digest, format_answer
from web_api.trace import TraceRecorder


@pytest.fixture
def qualified_db(price_db):
    records = []
    for name, date in (("Kaius", None), ("Marneus Calgar", "2026-09-30")):
        source = {"url": "https://example.invalid/space-marines", "kind": "web",
                  "sha256": hashlib.sha256(b"space-marines").hexdigest(),
                  "page": None, "source_date": "2026-09-30", "captured_at": CAPTURED}
        records.append({
            "identity": {"unit_id": None, "name_en": name, "faction_id": "SM",
                         "faction_slug": "space-marines", "faction_keywords": []},
            "reviewed_on": "2026-10-04",
            "body": {"status": "source_only_price", "scope": [], "effective_date": None,
                     "sources": [source], "retained_snapshot": None},
            "points": {"status": "current_published", "effective_date": date,
                       "sources": [copy.deepcopy(source)]},
        })
    with closing(sqlite3.connect(price_db)) as conn, conn:
        conn.execute("BEGIN")
        apply_coverage(conn, {"schema_version": 1, "records": records},
                       expected_records=[None, None])
    return price_db, records


def lookup(db, tool, query, tmp_path):
    resolver = EntityResolver(db_path=db)
    if tool == "get_entity":
        return tools.get_entity(query, wiki_root=tmp_path / "empty-wiki", resolver=resolver)
    return tools.get_datasheet(query, db_path=db, resolver=resolver)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
@pytest.mark.parametrize("query,points", [("Kaius", 100), ("Marneus Calgar", 180),
    ("马涅乌斯·卡尔加", 180), ("@mfm:space-marines:Kaius", 100),
    ("Kaius (Prototype)", 110)])
def test_exact_price_adapter_does_not_acquire_a_body(qualified_db, tmp_path, tool, query, points):
    db, records = qualified_db
    before = db.read_bytes()
    result = lookup(db, tool, query, tmp_path)
    assert result["found"] and result["points"] == points
    assert result["points_only"] and result["unit_id"] is None
    assert result.get("datasheet") is None and result.get("page") is None
    assert not any(result.get(key) for key in ("models", "weapons", "composition", "canonical_id"))
    if points != 110:
        record = next(r for r in records if r["identity"]["name_en"] == result["name_en"])
        assert describe_coverage(record) in result["source_note"]
    if points == 180:
        assert result["historical_record"]["historical_points"] == 200
        assert result["historical_record"]["is_current"] is False
    assert _has_usable_evidence(tool, result)
    recorder = TraceRecorder({})
    recorder.last_result[tool] = result
    assert _derive_entity_card(recorder, None) is None
    assert db.read_bytes() == before


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_equal_price_cross_faction_is_ambiguous(qualified_db, tmp_path, tool):
    db, _ = qualified_db
    result = lookup(db, tool, "Shared Hero", tmp_path)
    assert not result["found"] and result["reason"] == "ambiguous"
    assert result["points"] is None and result["unit_id"] is None
    assert len(result["candidates"]) == 2
    assert not _has_usable_evidence(tool, result)
    for candidate in result["candidates"]:
        exact = lookup(db, tool, candidate["query"], tmp_path)
        assert exact["points"] == 120 and exact["faction_slug"] == candidate["faction_slug"]
        assert exact.get("datasheet") is None and exact.get("page") is None


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
@pytest.mark.parametrize("query", ["@mfm:adeptus-custodes:Kaius", "@mfm:space-marines:Kaius%ZZ"])
def test_reserved_selector_cannot_borrow_a_fuzzy_body(qualified_db, tmp_path, tool, query):
    result = lookup(qualified_db[0], tool, query, tmp_path)
    assert not result["found"] and result["reason"] == "price_selector"
    assert result.get("datasheet") is None and result.get("page") is None
    assert not _has_usable_evidence(tool, result)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_invalid_source_declaration_is_visible(qualified_db, tmp_path, tool):
    db, _ = qualified_db
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE source_coverage_registry SET record_json='{' ")
    with pytest.raises(CoverageError):
        lookup(db, tool, "Kaius", tmp_path)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
@pytest.mark.parametrize("ending", ["empty", "malformed", "forbidden", "max_steps"])
def test_real_dispatch_preserves_two_source_subjects_through_recovery_and_formatter(
        qualified_db, tmp_path, tool, ending):
    db, records = qualified_db
    calls = []

    def actual(name_or_id):
        calls.append(name_or_id)
        return lookup(db, tool, name_or_id, tmp_path)

    def fallback(query):
        pytest.fail("Useful exact price evidence must not be discarded for automatic RAG")

    steps = [{"type": "tool_call", "tool": tool, "args": {"name_or_id": name}}
             for name in ("Kaius", "Marneus Calgar")]
    if ending == "empty":
        steps += [{"type": "tool_call", "tool": tool, "args": {"name_or_id": "No Such Unit"}},
                  {"type": "final", "content": 42}]
    elif ending == "forbidden":
        steps += [{"type": "tool_call", "tool": tool,
                   "args": {"name_or_id": "Kaius", "db_path": "forbidden.sqlite"}}]
    elif ending == "malformed":
        steps += [{"type": "final", "content": []}]
    else:
        steps += [{"type": "tool_call", "tool": tool, "args": {"name_or_id": "Kaius"}}]
    recorder = TraceRecorder({tool: actual, "rag_search": fallback})
    llm = ScriptedLLM("算", steps)
    session = SessionContext()
    loop = AgentLoop(llm=llm, tools=recorder.wrapped_tools(),
                     max_steps=2 if ending == "max_steps" else 6)
    result = loop.run("Compare the published prices and their separate limits", session=session)
    assert result.degraded and "rag_search" not in result.tool_calls
    assert "100" in result.answer and "180" in result.answer and "200" in result.answer
    assert "YOUR 2ND UNIT COSTS" in result.answer and "YOUR WARGEAR COSTS" in result.answer
    digest = _evidence_digest(recorder, limit=200)
    history = str(session.history)
    for record in records:
        note = describe_coverage(record)
        assert note in result.answer and note in digest and note in history
    assert {s["url"] for s in result.sources} >= {"https://example.invalid/space-marines"}
    assert calls == (["Kaius", "Marneus Calgar", "No Such Unit"] if ending == "empty"
                     else ["Kaius", "Marneus Calgar"])

    class FailedFormatter:
        def structure(self, question, answer, evidence, cites):
            assert all(describe_coverage(r) in evidence for r in records)
            raise RuntimeError("synthetic formatting failure")

    answer = format_answer("price comparison", result, recorder, structurer=FailedFormatter())
    assert answer.entity_card is None and answer.degraded
    assert all(describe_coverage(r) in str(answer.model_dump()) for r in records)
    assert any(c.url == "https://example.invalid/space-marines" for c in answer.cites)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_identity_only_never_becomes_price_or_rules_evidence(tool):
    assert not _has_usable_evidence(tool, {"found": True, "unit_id": "identity-only",
                                         "points_only": True, "official_prices": []})


@pytest.mark.parametrize("query,points", [("Current Squad", 90), ("102", 90),
    ("Marneus Calgar in Armour of Antilochus", None)])
def test_copied_database_canonical_path_preserves_body_and_historical_price(
        qualified_db, monkeypatch, query, points):
    db, _ = qualified_db

    def forbidden_default():
        pytest.fail("Copied database lookup must not use a production resolver")

    monkeypatch.setattr(tools, "_get_default_resolver", forbidden_default)
    result = tools.get_datasheet(query, db_path=db)
    assert result["found"] and result["datasheet"]["unit_id"] in ("100", "102")
    assert result["datasheet"]["points_min"] == points
    assert not result.get("points_only")
    if points is None:
        assert "155" in result["datasheet"]["source_note"]


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_archive_without_current_price_remains_explicitly_historical(qualified_db, tmp_path, tool):
    db, _ = qualified_db
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DELETE FROM official_mfm_points WHERE unit_name='Marneus Calgar'")
        conn.execute("DELETE FROM source_coverage_registry")
    result = lookup(db, tool, "普通卡尔加", tmp_path)
    assert result["historical_record"]["historical_points"] == 200
    assert result["historical_record"]["is_current"] is False
    assert result.get("points") is None and not result.get("official_prices")
    assert result.get("datasheet") is None and result.get("page") is None


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_successful_real_dispatch_supplies_price_evidence_to_synthesis(qualified_db, tmp_path, tool):
    db, records = qualified_db
    recorder = TraceRecorder({tool: lambda name_or_id: lookup(db, tool, name_or_id, tmp_path)})
    llm = ScriptedLLM("算", [
        {"type": "tool_call", "tool": tool, "args": {"name_or_id": "Kaius"}},
        {"type": "final", "content": "Kaius 100; published price only, rules unverified."},
    ])
    result = AgentLoop(llm=llm, tools=recorder.wrapped_tools()).run("Kaius price")
    evidence = llm.next_step_calls[-1][-1]["content"]
    assert result.answer.startswith("Kaius 100") and not result.degraded
    assert evidence["points"] == 100 and describe_coverage(records[0]) in evidence["source_note"]


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_unregistered_price_qualifiers_keep_each_subject_in_digest(price_db, tmp_path, tool):
    recorder = TraceRecorder({tool: lambda name_or_id: lookup(price_db, tool, name_or_id, tmp_path)})
    fn = recorder.wrapped_tools()[tool]
    results = [fn(name_or_id=name) for name in ("Kaius", "Marneus Calgar")]
    digest = _evidence_digest(recorder, limit=200)
    for result in results:
        assert result["source_note"] in digest
        assert result["name_en"] in digest and result["faction_slug"] in digest
