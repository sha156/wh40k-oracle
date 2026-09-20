"""The web formatting boundary must preserve merged-card provenance."""
from agent.loop import AgentResult
from agent.tools import _entity_page_result
from web_api.formatter import format_answer
from web_api.trace import TraceRecorder
from wiki_engine.models import WikiPage


def test_merged_card_has_its_own_citation_and_keeps_scope_in_digest():
    page = WikiPage.from_markdown(
        "---\nid: '202'\nname_en: Commander\nfaction: Alpha\ntype: unit\n"
        "version:\n  source: official-db\nsources:\n"
        "- book: Keyword patch\n  pages: [23]\n---\n\n"
        + "Weapon profile rows\n" * 800
        + "Two orders, command range 12 inches."
    )
    card = _entity_page_result(page, {"canonical_id": "202"})
    recorder = TraceRecorder({})
    recorder.last_result["rag_search"] = {"passages": ["General orders " * 600]}
    recorder.last_result["get_entity"] = card
    captured = {}

    class Capture:
        def structure(self, question, prose, evidence, cites):
            captured.update(evidence=evidence, cites=cites)
            return {"verdict": {"lede": prose}}

    answer = format_answer(
        "What are this commander's orders?",
        AgentResult(answer="Two orders from the merged card; effects from Core Rules.",
                    intent="查", sources=[{"book": "Core Rules", "page": 1}]),
        recorder, Capture(),
    )
    structured = next(c for c in answer.cites if c.book == "L3 结构库 · Alpha")
    assert structured.term == "Commander"
    assert structured.page is None
    assert structured.section == "合并兵牌"
    assert any(c.book == "Core Rules" and c.page == 1 for c in answer.cites)
    assert not any(c.book == "Keyword patch" for c in answer.cites)
    assert card["source_scope"] in captured["evidence"]
    assert "Commander" in captured["evidence"]
    assert len(captured["evidence"]) <= 2000


def test_failed_entity_lookup_does_not_create_a_card_citation():
    recorder = TraceRecorder({})
    recorder.last_result["get_entity"] = {"found": False, "page": None}
    answer = format_answer("Unknown", AgentResult(answer="Not found", intent="查"), recorder)
    assert answer.cites == []


def test_valid_json_cannot_silently_drop_the_answer_table():
    prose = "Order effects:\n| Order | Effect |\n|---|---|\n| Advance | M+3 |\n| Aim | BS+1 |"

    class Lossy:
        def structure(self, *args):
            return {"verdict": {"lede": "Orders last one round."},
                    "calc": ["Issued in the command phase."]}

    answer = format_answer("Order effects?", AgentResult(answer=prose, intent="查"),
                           TraceRecorder({}), Lossy())
    assert answer.degraded
    assert answer.trace_warn
    visible = "".join(getattr(span, "s", "") for span in answer.verdict.lede)
    for value in ("Advance", "M+3", "Aim", "BS+1"):
        assert value in visible


def test_named_table_rows_can_be_reformatted_as_steps():
    from web_api.formatter import _missing_table_labels
    prose = "| Order | Effect |\n| :--- | ---: |\n| **快快快！** | M+3 |\n| 瞄准！ | BS+1 |"
    assert _missing_table_labels(prose, {
        "verdict": {"lede": "命令如下"},
        "calc": ["【快快快】M+3", "【瞄准】BS+1"],
    }) == []
