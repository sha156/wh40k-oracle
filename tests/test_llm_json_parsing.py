"""Paired model-free regressions for noisy JSON containing quoted delimiters."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agent.llm_client import OpenAICompatLLMClient, _extract_json_object
from agent.loop import AgentResult
from web_api.formatter import format_answer
from web_api.structurer import OpenAIStructuringLLM, _extract_json
from web_api.trace import TraceRecorder


@pytest.fixture(params=["agent", "structurer"])
def parser_and_object(request):
    if request.param == "agent":
        return _extract_json_object, {
            "type": "final", "content": "", "sources": [{"book": "Core Rules", "page": 3}],
        }
    return _extract_json, {
        "verdict": {"label": "Ruling", "labelEn": "Ruling", "lede": "Verified rule"},
        "calc": [], "sensitivity": None, "followups": [],
    }


@pytest.mark.parametrize("content", [
    "A literal } stays inside the answer",
    "A literal { stays inside the answer",
    'An escaped quote " before } and a backslash \\ after {',
])
@pytest.mark.parametrize("wrapper", [
    "prefix: {} trailing text",
    "```json\n{}\n``` trailing text",
    "prefix\n```json\n{}\n```\ntrailing text",
])
def test_quoted_delimiters_in_noisy_json_roundtrip(parser_and_object, content, wrapper):
    parser, obj = parser_and_object
    obj["content"] = content
    # Equality checks every field, including nested objects and citation arrays.
    assert parser(wrapper.format(json.dumps(obj))) == obj


@pytest.mark.parametrize("raw", [
    "prefix: {\"type\":\"final\",\"content\":\"unterminated }",
    'prefix: {"type":"final","content":"closed string but missing object"',
    'prefix: {"type":"final","content":"invalid escape \\q"}',
    'prefix: {"type":"final","content":"x",}',
    'prefix: {broken} {"type":"final","content":"do not salvage a later object"}',
    "no JSON here", " ",
])
def test_invalid_or_incomplete_json_remains_rejected(parser_and_object, raw):
    parser, _ = parser_and_object
    with pytest.raises(ValueError):
        parser(raw)


@pytest.mark.parametrize("raw", ['[]', '[{"type":"final"}]', '"scalar"', 'null', '42'])
def test_nonobject_json_remains_rejected(parser_and_object, raw):
    parser, _ = parser_and_object
    with pytest.raises(ValueError):
        parser(raw)


def test_agent_missing_type_in_noisy_object_remains_rejected():
    with pytest.raises(ValueError, match="type"):
        _extract_json_object('prefix: {"content":"literal }"} trailing')


class CountingClient:
    """Count application calls; this does not claim real SDK transport counts."""

    def __init__(self, content):
        self.content = content
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=self.content),
        )])


def test_agent_noisy_valid_answer_does_not_trigger_parse_retry():
    expected = {"type": "final", "content": 'Literal } and "quote"',
                "sources": [{"book": "Core Rules", "page": 3}]}
    fake = CountingClient("prefix: " + json.dumps(expected) + " trailing")
    llm = OpenAICompatLLMClient(client=fake)
    assert llm.next_step([{"role": "user", "content": "Explain this symbol"}], []) == expected
    assert len(fake.calls) == 1


def test_structurer_preserves_noisy_valid_slots():
    expected = {"verdict": {"lede": 'Literal } and "quote"'},
                "calc": ["Opening { brace"], "sensitivity": None, "followups": []}
    fake = CountingClient("prefix: " + json.dumps(expected) + " trailing")
    layout = OpenAIStructuringLLM(client=fake)
    assert layout.structure("Explain this symbol", "Verified prose", "", []) == expected
    assert len(fake.calls) == 1


def test_structurer_wrong_verdict_schema_retains_prose_fallback():
    # The parser checks object type; slot/schema checks remain in the formatter.
    fake = CountingClient('prefix: {"verdict":[]} trailing')
    result = AgentResult(answer="Verified original prose", intent="查", tool_calls=[],
                         degraded=False, sources=[])
    answer = format_answer("Explain this symbol", result, TraceRecorder({}),
                           OpenAIStructuringLLM(client=fake))
    assert "".join(span.s for span in answer.verdict.lede) == result.answer
    assert answer.verdict.label_en == "Advisory"
    assert answer.calc == []
    assert answer.followups == []
