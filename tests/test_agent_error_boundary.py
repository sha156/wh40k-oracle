"""Synthetic SDK/transport failures must never become public exception prose."""
from copy import deepcopy
from dataclasses import asdict
import json

import httpx
from openai import OpenAI
import pytest
from fastapi.testclient import TestClient

from agent.context import SessionContext
from agent.llm_client import OpenAICompatLLMClient
from agent.loop import AgentLoop
from agent import tools
from web_api import main
from web_api.sessions import SessionStore
from web_api.structurer import OpenAIStructuringLLM


TOKEN = "sk-SYNTHETIC-SECURITY-CANARY-NOT-A-REAL-KEY"
BODY = "SYNTHETIC_PRIVATE_UPSTREAM_BODY"
SOURCE = {"book": "Synthetic official reference", "page": 3}
NOTE = "Official preview. " + "Context. " * 80 + "Released codex not verified."
EVIDENCE = {"found": True, "units": [{"name_en": "Canonical fixture", "points": 355}],
            "official_sources": [SOURCE], "source_note": NOTE}
FAILURES = [(401, "provider_authentication", False), (403, "provider_permission", False),
            (400, "provider_request", False), (404, "provider_request", False),
            (422, "provider_request", False), (409, "provider_unavailable", True),
            (429, "provider_rate_limit", True), (500, "provider_unavailable", True),
            ("timeout", "provider_timeout", True), ("connection", "provider_connection", True),
            ("malformed", "invalid_response", False)]


def assert_safe(value):
    text = json.dumps(value, ensure_ascii=False, default=str)
    for secret in (TOKEN, TOKEN.removeprefix("sk-"), BODY, "invalid_api_key"):
        assert secret not in text, "Exception payload reached a public/model/history surface"


def sdk_fixture(kind, phase, calls):
    """Use the real SDK and application parser, with zero network/paid requests."""
    responses = [] if phase == "classification" else ["查"]
    if phase in ("evidence", "synthesis"):
        responses.append(json.dumps({"type": "tool_call", "tool": "calc_points",
                                     "args": {"unit_list": ["fixture"]}}))

    def transport(request):
        calls.append(json.loads(request.content))
        if responses:
            text = responses.pop(0)
        elif kind == "timeout":
            raise httpx.ReadTimeout(TOKEN + BODY, request=request)
        elif kind == "connection":
            raise httpx.ConnectError(TOKEN + BODY, request=request)
        elif kind == "malformed":
            text = '{"content": "' + TOKEN + BODY  # JSONDecodeError carries .doc
        else:
            return httpx.Response(kind, json={"error": {
                "message": "Incorrect API key provided: " + TOKEN + BODY,
                "type": "authentication_error", "code": "invalid_api_key"}}, request=request)
        return httpx.Response(200, json={"id": "fixture", "object": "chat.completion",
            "created": 0, "model": "fixture", "choices": [{"index": 0,
            "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]},
            request=request)

    sdk = OpenAI(api_key=TOKEN, base_url="https://upstream.invalid/v1/", max_retries=0,
                 http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    return sdk, OpenAICompatLLMClient(api_key=TOKEN, provider="DeepSeek", client=sdk)


@pytest.mark.parametrize("kind,category,retryable", FAILURES)
@pytest.mark.parametrize("phase", ("empty", "classification", "evidence", "synthesis"))
def test_real_sdk_exception_categories_and_evidence_survive(kind, category, retryable, phase):
    calls, rag = [], []
    sdk, llm = sdk_fixture(kind, phase, calls)
    session = SessionContext()
    original = deepcopy(EVIDENCE)
    try:
        result = AgentLoop(llm, tools={"calc_points": lambda unit_list: deepcopy(EVIDENCE),
            "rag_search": lambda query: rag.append(query) or {"passages": []}},
            max_steps=1 if phase == "synthesis" else 6).run("Verify fixture", session)
    finally:
        sdk.close()
    assert_safe(asdict(result))
    assert_safe(session.history)
    assert_safe(calls)
    assert result.degraded and category in result.answer
    assert f"retryable={str(retryable).lower()}" in result.answer
    if isinstance(kind, int):
        assert f"status={kind}" in result.answer
    with_evidence = phase in ("evidence", "synthesis")
    assert len(rag) == (0 if with_evidence else 1)
    assert len(calls) == (3 if with_evidence else 2) + (1 if kind == "malformed" else 0)
    if with_evidence:
        assert "355" in result.answer and NOTE in result.answer
        assert result.sources == [SOURCE] and "未确认" in result.answer
    else:
        assert "355" not in result.answer and result.sources == []
    assert EVIDENCE == original
    assert session.history[-1]["content"] == result.answer


@pytest.mark.parametrize("route", ("/chat/sync", "/chat"))
@pytest.mark.parametrize("phase", ("empty", "classification", "evidence"))
def test_real_sdk_echo_never_reaches_sync_sse_or_session(monkeypatch, route, phase):
    calls, rag = [], []
    sdk, llm = sdk_fixture(401, phase, calls)
    sessions = SessionStore()
    monkeypatch.setattr(main, "retrieval_enabled", lambda: True)
    monkeypatch.setattr(main, "_make_clients", lambda: (llm, None))
    monkeypatch.setattr(main, "_SESSIONS", sessions)
    monkeypatch.setattr(tools, "TOOLS", {
        "calc_points": lambda unit_list: deepcopy(EVIDENCE),
        "rag_search": lambda query: rag.append(query) or {"passages": []}})
    try:
        with TestClient(main.app) as client:
            response = client.post(route, json={"question": "Verify fixture", "session_id": "fixture"})
    finally:
        sdk.close()
    assert response.status_code == 200
    assert_safe(response.text)
    with sessions.session("fixture") as session:
        assert_safe(session.history)
        assert "provider_authentication" in session.history[-1]["content"]
        if phase == "evidence":
            assert NOTE in session.history[-1]["content"]
    assert "provider_authentication" in response.text and "status=401" in response.text
    if route == "/chat":
        assert 'event: done\ndata: {"ok": true}' in response.text
        assert response.headers["cache-control"] == "no-cache"
    else:
        assert response.json()["degraded"] is True
    assert len(calls) == (3 if phase == "evidence" else 2)
    if phase == "evidence":
        assert "355" in response.text and SOURCE["book"] in response.text and not rag
    else:
        assert len(rag) == 1


class ScriptedLLM:
    def __init__(self, steps):
        self.steps = iter(steps)
        self.messages = []

    def classify_intent(self, question):
        return "查"

    def next_step(self, messages, specs):
        self.messages.append(deepcopy(messages))
        step = next(self.steps)
        if isinstance(step, Exception):
            raise step
        return step


@pytest.mark.parametrize("error", (RuntimeError, ValueError, TypeError, TimeoutError))
def test_tool_exception_feedback_cannot_be_reflected_by_next_model_turn(error):
    llm = ScriptedLLM([{"type": "tool_call", "tool": "calc_points", "args": {}},
                       {"type": "tool_call", "tool": "get_entity", "args": {}},
                       {"type": "tool_call", "tool": "get_entity", "args": {}}])

    def broken():
        raise error(TOKEN + BODY)

    result = AgentLoop(llm, tools={"calc_points": lambda: deepcopy(EVIDENCE),
                                  "get_entity": broken}).run("Verify")
    assert_safe(llm.messages)
    assert_safe(asdict(result))
    assert result.degraded and "355" in result.answer and NOTE in result.answer
    assert result.sources == [SOURCE] and len(llm.messages) == 3
    assert "retryable=" in llm.messages[2][-1]["content"]["error"]


def test_fallback_exception_does_not_replace_provider_failure_with_secret():
    def broken(query):
        raise RuntimeError(TOKEN + BODY)

    result = AgentLoop(ScriptedLLM([RuntimeError(TOKEN + BODY)]),
                       tools={"rag_search": broken}).run("Verify")
    assert_safe(asdict(result))
    assert result.degraded and "不可用" in result.answer and "未找到相关内容" not in result.answer
    assert "internal_failure" in result.answer and result.tool_calls == ["rag_search"]


@pytest.mark.parametrize("route", ("/chat/sync", "/chat"))
def test_structurer_real_sdk_echo_preserves_safe_prose_and_citation(monkeypatch, route):
    calls = []
    sdk, _ = sdk_fixture(401, "classification", calls)
    structurer = OpenAIStructuringLLM(api_key=TOKEN, client=sdk)
    llm = ScriptedLLM([{"type": "tool_call", "tool": "calc_points", "args": {}},
                       {"type": "final", "content": "Verified 355. " + NOTE, "sources": [SOURCE]}])
    monkeypatch.setattr(main, "retrieval_enabled", lambda: True)
    monkeypatch.setattr(main, "_make_clients", lambda: (llm, structurer))
    monkeypatch.setattr(tools, "TOOLS", {"calc_points": lambda: deepcopy(EVIDENCE)})
    try:
        with TestClient(main.app) as client:
            response = client.post(route, json={"question": "Verify fixture"})
    finally:
        sdk.close()
    assert response.status_code == 200 and len(calls) == 1
    assert_safe(response.text)
    assert "Verified" in response.text and "355" in response.text and SOURCE["book"] in response.text
    assert "回答排版失败" in response.text


def test_invalid_action_payload_is_not_interpolated_into_failure():
    result = AgentLoop(ScriptedLLM([{"type": TOKEN + BODY, "content": TOKEN}]), tools={}).run("Verify")
    assert_safe(asdict(result))
    assert result.degraded


def test_good_provider_output_and_tool_data_are_unchanged():
    session = SessionContext()
    llm = ScriptedLLM([{"type": "tool_call", "tool": "calc_points", "args": {}},
                       {"type": "final", "content": "Verified 355. " + NOTE, "sources": [SOURCE]}])
    result = AgentLoop(llm, tools={"calc_points": lambda: deepcopy(EVIDENCE)}).run("Verify", session)
    assert not result.degraded and result.answer == "Verified 355. " + NOTE
    assert result.sources == [SOURCE] and llm.messages[1][-1]["content"] == EVIDENCE
    assert session.history[-1]["content"] == result.answer


@pytest.mark.parametrize("route", ("/chat/sync", "/chat"))
@pytest.mark.parametrize("partial", (True, False))
def test_returned_retrieval_diagnostics_are_safe_before_trace_and_model_feedback(monkeypatch, route, partial):
    diagnostic = TOKEN + BODY
    passage = {"book": SOURCE["book"], "page": SOURCE["page"],
               "text": "Verified synthetic rule.", "source_note": NOTE}
    if partial:
        returned = {"found": True, "passages": [passage], "retrieval_errors": [diagnostic],
                    "note": "Partial channel failure: " + diagnostic}
    else:
        returned = {"found": False, "passages": [], "error": True, "note": diagnostic,
                    "trace": diagnostic, "source_metadata": {"provider": diagnostic}}
    original = deepcopy(returned)
    llm = ScriptedLLM([{"type": "tool_call", "tool": "rag_search", "args": {"query": "fixture"}},
                       RuntimeError(diagnostic)])
    monkeypatch.setattr(main, "retrieval_enabled", lambda: True)
    monkeypatch.setattr(main, "_make_clients", lambda: (llm, None))
    monkeypatch.setattr(main, "_SESSIONS", SessionStore())
    monkeypatch.setattr(tools, "TOOLS", {"rag_search": lambda query: returned})
    with TestClient(main.app) as client:
        response = client.post(route, json={"question": "Verify fixture", "session_id": "fixture"})
    assert response.status_code == 200
    assert_safe(response.text)
    assert_safe(llm.messages)
    with main._SESSIONS.session("fixture") as session:
        assert_safe(session.history)
    assert returned == original, "Never mutate a shared raw result"
    if partial:
        assert "Verified synthetic rule" in response.text and SOURCE["book"] in response.text
        assert "部分召回通道故障" in response.text
        assert llm.messages[1][-1]["content"]["passages"][0] == passage
    else:
        assert "retrieval_unavailable" in response.text and "不可用" in response.text


def test_outer_safety_net_never_serializes_an_exception():
    class BrokenLoop(AgentLoop):
        def _run_tool_loop(self, user_input, intent, history=None):
            raise RuntimeError(TOKEN + BODY)

    result = BrokenLoop(ScriptedLLM([]), tools={}).run("Verify")
    assert_safe(asdict(result))
    assert result.degraded and "internal_failure" in result.answer


def test_exception_payload_is_never_stringified_even_for_trusted_validation_types():
    from agent.public_errors import PublicActionError, PublicToolContractError, public_failure

    class PayloadError(RuntimeError):
        def __str__(self):
            raise AssertionError("Do not read exception payloads")

    for error in (PayloadError(), PublicActionError(TOKEN), PublicToolContractError(TOKEN)):
        failure = public_failure(error)
        assert_safe(failure.describe())
    assert public_failure(PayloadError()).category == "internal_failure"


def test_typed_sdk_status_ignores_untrusted_noninteger_metadata():
    from openai import APIStatusError
    from agent.public_errors import public_failure

    request = httpx.Request("POST", "https://upstream.invalid/")
    error = APIStatusError(TOKEN, response=httpx.Response(401, request=request), body={"secret": TOKEN})
    error.status_code = TOKEN
    failure = public_failure(error)
    assert failure.status is None and failure.category == "provider_request"
    assert_safe(failure.describe())
