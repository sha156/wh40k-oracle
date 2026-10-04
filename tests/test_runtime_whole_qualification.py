"""Actual canonical adapters and successful synthesis cannot lose late qualifiers."""
import copy
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from agent.context import SessionContext
from agent.loop import AgentLoop
from db_compile.coverage_notes import CoverageError, describe_coverage
from db_compile.entity_resolver import EntityResolver
from db_compile.source_coverage import apply_coverage
from tests.test_agent_loop import ScriptedLLM
from tests.test_db_compile_datasheet import _make_db
from tests.test_source_coverage_consumers import UID, declaration, install
from tests.test_runtime_price_adapters import qualified_db, lookup, price_db
from web_api.formatter import _evidence_digest, format_answer
from web_api.trace import TraceRecorder


@pytest.fixture
def canonical_subjects(tmp_path):
    db = _make_db(tmp_path)
    first = declaration("newer_full_unavailable")
    install(db, first)
    second = copy.deepcopy(first)
    second["identity"].update(unit_id="000000930", name_en="Chaos Champion")
    second["body"]["retained_snapshot"]["effective_date"] = "2026-08-01"
    second["points"]["effective_date"] = "2026-09-30"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("BEGIN")
        conn.execute("INSERT INTO units SELECT '000000930',faction_id,'Chaos Champion',"
                     "name_zh,points_json,keywords_json,version FROM units WHERE id=?", (UID,))
        conn.execute("INSERT INTO datasheets VALUES ('000000930','Chaos Champion','CSM')")
        conn.execute("INSERT INTO models SELECT '000000930','Chaos Champion',m,t,sv,invuln,"
                     "w,ld,oc,base,count_options_json FROM models WHERE unit_id=?", (UID,))
        conn.execute("INSERT INTO weapons SELECT id || '_second','000000930',name_zh,name_en,"
                     "range,a,bs_ws,s,ap,d,keywords_json FROM weapons WHERE unit_id=?", (UID,))
        conn.execute("INSERT INTO official_mfm_points (faction_slug,kind,section,unit_name,"
                     "tier,models,cost,source_url,source_sha256,fetched_at,ordinal) SELECT faction_slug,kind,section,"
                     "'Chaos Champion',tier,models,cost,source_url,source_sha256,fetched_at,ordinal+1 "
                     "FROM official_mfm_points WHERE unit_name='Chaos Lord'")
        apply_coverage(conn, {"schema_version": 1, "records": [second]}, expected_records=[None])
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text(
        "### Chaos Space Marines\n| unit | [Chaos Lord](lord.md) | | - |\n"
        "| unit | [Chaos Champion](champion.md) | | - |\n", encoding="utf-8")
    for filename, record in (("lord.md", first), ("champion.md", second)):
        identity = record["identity"]
        (wiki / filename).write_text(
            f"---\nid: '{identity['unit_id']}'\nname_en: {identity['name_en']}\n"
            "faction: Chaos Space Marines\ntype: unit\nversion:\n  source: official-db\n---\n"
            + "Retained body text. " * 500 + "\nLate unverified limitation.\n", encoding="utf-8")
    app = tmp_path / "aliases.py"
    app.write_text('UNIT_ALIASES = {"混沌领主": "Chaos Lord"}', encoding="utf-8")
    return db, wiki, app, [first, second]


def canonical_lookup(fixture, tool, name):
    db, wiki, app, _ = fixture
    resolver = EntityResolver(db_path=db, app_path=app)
    if tool == "get_entity":
        return tools.get_entity(name, wiki_root=wiki, resolver=resolver, app_path=app)
    return tools.get_datasheet(name, db_path=db, resolver=resolver)


@pytest.mark.parametrize("query", ["Chaos Lord", UID, "混沌领主"])
def test_canonical_wiki_adapter_exposes_whole_central_note(canonical_subjects, query):
    before = canonical_subjects[0].read_bytes()
    result = canonical_lookup(canonical_subjects, "get_entity", query)
    assert result["found"] and result["page"].fm.id == UID
    assert describe_coverage(canonical_subjects[3][0]) in result.get("source_note", "")
    assert "关联参考" in result["source_scope"]
    assert canonical_subjects[0].read_bytes() == before


def test_canonical_wiki_invalid_registry_is_not_a_stale_body(canonical_subjects):
    with closing(sqlite3.connect(canonical_subjects[0])) as conn, conn:
        conn.execute("UPDATE source_coverage_registry SET record_json='{'")
    with pytest.raises(CoverageError):
        canonical_lookup(canonical_subjects, "get_entity", UID)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
@pytest.mark.parametrize("ending", ["success", "empty_success", "max_success", "malformed", "forbidden"])
def test_two_canonical_dates_survive_actual_dispatch_history_and_formatter(
        canonical_subjects, tool, ending):
    records = canonical_subjects[3]
    recorder = TraceRecorder({tool: lambda name_or_id: canonical_lookup(canonical_subjects, tool, name_or_id)})
    steps = [{"type": "tool_call", "tool": tool, "args": {"name_or_id": r["identity"]["unit_id"]}}
             for r in records]
    if ending == "empty_success":
        steps.append({"type": "tool_call", "tool": tool, "args": {"name_or_id": "No Such Unit"}})
    if ending == "malformed":
        steps.append({"type": "final", "content": []})
    elif ending == "forbidden":
        steps.append({"type": "tool_call", "tool": tool, "args": {"name_or_id": UID, "db_path": "forbidden"}})
    else:
        steps.append({"type": "final", "content": "Chaos Lord and Chaos Champion: retained evidence."})
    session = SessionContext()
    result = AgentLoop(llm=ScriptedLLM("查", steps), tools=recorder.wrapped_tools(),
                       max_steps=2 if ending == "max_success" else 6).run("Compare both subjects", session=session)
    notes = [describe_coverage(r) for r in records]
    assert all(note in result.answer and note in str(session.history) for note in notes)
    assert all(note in _evidence_digest(recorder, limit=100) for note in notes)
    assert result.degraded == (ending in ("malformed", "forbidden"))
    assert "rag_search" not in result.tool_calls

    class OmittingFormatter:
        def structure(self, question, prose, evidence, cites):
            assert all(note in evidence for note in notes)
            return {"verdict": {"label": "RETAINED", "labelEn": "RETAINED", "lede": "Both bodies verified current."}}

    formatted = format_answer("Compare both subjects", result, recorder, structurer=OmittingFormatter())
    assert formatted.degraded
    rendered = "".join(getattr(inline, "s", "") for inline in formatted.verdict.lede)
    assert all(note in rendered for note in notes)


@pytest.mark.parametrize("subject", ["archive_entity", "archive_datasheet", "retained_armour"])
@pytest.mark.parametrize("max_success", [False, True])
def test_actual_historical_warnings_survive_success_and_formatting(price_db, tmp_path, subject, max_success):
    if subject.startswith("archive"):
        with closing(sqlite3.connect(price_db)) as conn, conn:
            conn.execute("DELETE FROM official_mfm_points WHERE unit_name='Marneus Calgar'")
        query = "普通卡尔加"
        tool = "get_entity" if subject == "archive_entity" else "get_datasheet"
    else:
        query = "Marneus Calgar in Armour of Antilochus"
        tool = "get_datasheet"
    payload = lookup(price_db, tool, query, tmp_path)
    notes = ([payload["note"], payload["source_scope"]] if subject.startswith("archive")
             else [payload["datasheet"]["source_note"]])
    recorder = TraceRecorder({tool: lambda name_or_id: lookup(price_db, tool, name_or_id, tmp_path)})
    steps = [{"type": "tool_call", "tool": tool, "args": {"name_or_id": query}},
             {"type": "final", "content": "Calgar costs 200." if subject.startswith("archive") else "Armour costs 155."}]
    session = SessionContext()
    result = AgentLoop(llm=ScriptedLLM("算", steps), tools=recorder.wrapped_tools(),
                       max_steps=1 if max_success else 4).run("Calgar price", session=session)
    assert not result.degraded
    assert all(note in result.answer and note in str(session.history) for note in notes)
    assert all(note in _evidence_digest(recorder, limit=100) for note in notes)

    class OmittingFormatter:
        def structure(self, question, prose, evidence, cites):
            return {"verdict": {"label": "PRICE", "labelEn": "PRICE", "lede": "Calgar costs 200."}}

    formatted = format_answer("Calgar price", result, recorder, structurer=OmittingFormatter())
    assert formatted.degraded
    rendered = "".join(getattr(inline, "s", "") for inline in formatted.verdict.lede)
    assert all(note in rendered for note in notes)


@pytest.mark.parametrize("tool", ["get_entity", "get_datasheet"])
def test_successful_source_only_answer_keeps_both_notes_and_citations(qualified_db, tmp_path, tool):
    db, records = qualified_db
    recorder = TraceRecorder({tool: lambda name_or_id: lookup(db, tool, name_or_id, tmp_path)})
    steps = [{"type": "tool_call", "tool": tool, "args": {"name_or_id": name}}
             for name in ("Kaius", "Marneus Calgar")]
    steps.append({"type": "final", "content": "Kaius 100; Marneus Calgar 180."})
    result = AgentLoop(llm=ScriptedLLM("算", steps), tools=recorder.wrapped_tools()).run("Compare prices")
    notes = [describe_coverage(r) for r in records]
    assert not result.degraded and all(note in result.answer for note in notes)
    assert any(source.get("url") == "https://example.invalid/space-marines" for source in result.sources)

    class CompleteFormatter:
        def structure(self, question, prose, evidence, cites):
            return {"verdict": {"label": "PRICE", "labelEn": "PRICE", "lede": prose}}

    formatted = format_answer("Compare prices", result, recorder, structurer=CompleteFormatter())
    assert not formatted.degraded and formatted.entity_card is None
    rendered = "".join(getattr(inline, "s", "") for inline in formatted.verdict.lede)
    assert all(note in rendered for note in notes)
