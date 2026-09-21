"""The web formatting boundary must preserve merged-card provenance."""
import pytest

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


@pytest.mark.parametrize("last_missing", [False, True])
def test_comparison_keeps_each_successful_card_source(last_missing):
    def get_entity(name):
        if name == "Missing":
            return {"found": False, "page": None}
        page = WikiPage.from_markdown(
            "---\nid: '{}-id'\nname_en: {}\nfaction: Alpha\ntype: unit\n"
            "version:\n  source: official-db\n---\nTwo orders.".format(name, name)
        )
        return _entity_page_result(page, {"canonical_id": page.fm.id})

    recorder = TraceRecorder({"get_entity": get_entity})
    lookup = recorder.wrapped_tools()["get_entity"]
    lookup("Commander A")
    lookup("Commander B")
    if last_missing:
        lookup("Missing")
    captured = {}

    class Capture:
        def structure(self, question, prose, evidence, cites):
            captured.update(evidence=evidence)
            return {"verdict": {"lede": prose}}

    answer = format_answer("Compare commanders", AgentResult(answer="Comparison", intent="查"),
                           recorder, Capture())
    assert {c.term for c in answer.cites} == {"Commander A", "Commander B"}
    assert "Commander A" in captured["evidence"]
    assert "Commander B" in captured["evidence"]
    assert not any(c.page for c in answer.cites)


@pytest.mark.parametrize("malformed", [
    {"verdict": {"lede": "Short answer", "calc": ["Hidden rule effect"]}},
    {"verdict": {"lede": "Short answer"}, "calc": "Lost rule effect"},
    {"verdict": {"lede": "Short answer"}, "calc": [{"text": "Wrong shape"}]},
])
def test_malformed_layout_keeps_prose_and_discloses_degradation(malformed):
    class Malformed:
        def structure(self, *args):
            return malformed

    answer = format_answer("Rule?", AgentResult(answer="Complete verified rule effect", intent="查"),
                           TraceRecorder({}), Malformed())
    assert answer.degraded
    assert answer.trace_warn
    assert "Complete verified rule effect" in "".join(
        getattr(span, "s", "") for span in answer.verdict.lede)


def test_repeated_datasheet_and_points_calls_keep_all_sources_and_latest_result():
    def datasheet(name):
        return {"found": True, "datasheet": {"name_en": name, "faction": "Alpha"}}

    def points(url):
        return {"official_sources": [{"url": url}]}

    recorder = TraceRecorder({"get_datasheet": datasheet, "calc_points": points})
    tools = recorder.wrapped_tools()
    tools["get_datasheet"]("A")
    tools["get_datasheet"]("B")
    tools["calc_points"]("https://example.org/alpha")
    tools["calc_points"]("https://example.org/beta")
    tools["calc_points"]("https://example.org/alpha")
    answer = format_answer("Compare", AgentResult(answer="Comparison", intent="查"), recorder)
    assert {c.term for c in answer.cites if c.book.startswith("L3")} == {"A", "B"}
    assert {c.url for c in answer.cites if c.url} == {
        "https://example.org/alpha", "https://example.org/beta"}
    assert len(answer.cites) == 4
    assert recorder.get_result("get_datasheet")["datasheet"]["name_en"] == "B"
    assert TraceRecorder({}).get_results("get_datasheet") == []
