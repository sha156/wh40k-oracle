"""Real SDK request-count regressions; all HTTP stays in MockTransport."""
from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from agent.llm_client import OpenAICompatLLMClient
from web_api.structurer import OpenAIStructuringLLM


OUTPUT = {"type": "final", "content": "Verified 355", "sources": [],
          "verdict": {"lede": "Verified 355"}, "calc": [], "followups": []}


def invoke(llm, kind):
    if kind == "agent":
        return llm.next_step([{"role": "user", "content": "Points?"}], [])
    return llm.structure("Points?", "Verified 355", "", [])


def construct(kind, **kwargs):
    cls = OpenAICompatLLMClient if kind == "agent" else OpenAIStructuringLLM
    return cls(**kwargs)


def install_transport(monkeypatch, handler):
    """Preserve application constructor options while replacing only HTTP I/O."""
    real_openai = openai.OpenAI
    clients = []

    def factory(**kwargs):
        client = real_openai(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler),
                                             trust_env=False))
        clients.append(client)
        return client

    monkeypatch.setattr(openai, "OpenAI", factory)
    # Zero sleep lets unchanged SDK defaults be reproduced without delay;
    # this does not change retries, application calls or transport counts.
    monkeypatch.setattr(openai._base_client.BaseClient, "_calculate_retry_timeout",
                        lambda *args, **kwargs: 0)
    return clients


def success_response():
    return httpx.Response(200, json={
        "id": "local-test", "object": "chat.completion", "created": 0,
        "model": "deepseek-flash", "choices": [{"index": 0,
            "message": {"role": "assistant", "content": json.dumps(OUTPUT)},
            "finish_reason": "stop"}],
    })


FAILURES = [
    ("unauthorized", 401, {"message": "Invalid authentication", "code": "invalid_api_key"},
     openai.AuthenticationError),
    ("rate_limit", 429, {"message": "Rate limited", "code": "rate_limit_exceeded"},
     openai.RateLimitError),
    ("server_error", 500, {"message": "Unavailable"}, openai.InternalServerError),
    ("unrelated_400", 400, {"message": "Invalid messages", "param": "messages"},
     openai.BadRequestError),
    ("model_not_found", 400, {"message": "Model does not exist", "param": "model",
                            "code": "model_not_found"}, openai.BadRequestError),
    ("invalid_format", 400, {"message": "response_format must be a valid object",
                            "param": "response_format", "code": "invalid_value"},
     openai.BadRequestError),
    ("misleading_model_error", 400, {"message": "response_format is not supported",
                                    "code": "model_not_found"}, openai.BadRequestError),
    ("misleading_param_error", 400, {"message": "response_format is not supported",
                                    "param": "messages"}, openai.BadRequestError),
    ("different_parameter", 400, {"message": "nested_response_format is not supported"},
     openai.BadRequestError),
    ("model_404", 404, {"message": "Model does not exist", "param": "model",
                       "code": "model_not_found"}, openai.NotFoundError),
    ("read_timeout", None, {}, openai.APITimeoutError),
    ("connect_timeout", None, {}, openai.APITimeoutError),
    ("write_timeout", None, {}, openai.APITimeoutError),
    ("pool_timeout", None, {}, openai.APITimeoutError),
]


@pytest.mark.parametrize("kind", ["agent", "structurer"])
@pytest.mark.parametrize("name,status,body,error_type", FAILURES,
                         ids=[case[0] for case in FAILURES])
def test_ordinary_failures_make_one_transport_request(monkeypatch, kind, name,
                                                      status, body, error_type):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        if status is None:
            errors = {"read_timeout": httpx.ReadTimeout, "connect_timeout": httpx.ConnectTimeout,
                      "write_timeout": httpx.WriteTimeout, "pool_timeout": httpx.PoolTimeout}
            raise errors[name]("Injected local timeout", request=request)
        return httpx.Response(status, json={"error": body})

    clients = install_transport(monkeypatch, handler)
    llm = construct(kind, api_key="local-test-placeholder", base_url="https://mock.invalid/v1")
    try:
        with pytest.raises(error_type):
            invoke(llm, kind)
        assert len(requests) == 1, "{} {} requests: {}".format(kind, name, len(requests))
        assert requests[0]["response_format"] == {"type": "json_object"}
    finally:
        for client in clients:
            client.close()


CAPABILITY_ERRORS = [
    {"message": "Unsupported parameter: 'response_format'", "param": "response_format",
     "code": "unsupported_parameter"},
    {"message": "This model does not support response_format of type json_object"},
    {"message": "response_format is not supported", "param": "response_format.type"},
    {"message": "Unknown parameter: response_format", "param": "response_format",
     "code": "unknown_parameter"},
]


@pytest.mark.parametrize("kind", ["agent", "structurer"])
@pytest.mark.parametrize("body", CAPABILITY_ERRORS)
def test_capability_rejection_alone_makes_second_request(monkeypatch, kind, body):
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if "response_format" in payload:
            return httpx.Response(400, json={"error": body})
        return success_response()

    clients = install_transport(monkeypatch, handler)
    llm = construct(kind, api_key="local-test-placeholder", base_url="https://mock.invalid/v1")
    try:
        assert invoke(llm, kind) == OUTPUT
        assert len(requests) == 2
        first, second = requests
        assert first.pop("response_format") == {"type": "json_object"}
        assert first == second  # Keep model, messages, token budget and thinking setting.
        assert second["thinking"] == {"type": "disabled"}
        assert second["max_tokens"] == 3200
    finally:
        for client in clients:
            client.close()


@pytest.mark.parametrize("kind", ["agent", "structurer"])
def test_failure_on_compatibility_request_is_not_retried(monkeypatch, kind):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(400, json={"error": CAPABILITY_ERRORS[0]})
        return httpx.Response(429, json={"error": {"message": "Rate limited"}})

    clients = install_transport(monkeypatch, handler)
    llm = construct(kind, api_key="local-test-placeholder", base_url="https://mock.invalid/v1")
    try:
        with pytest.raises(openai.RateLimitError):
            invoke(llm, kind)
        assert len(requests) == 2
        assert "response_format" not in requests[1]
    finally:
        for client in clients:
            client.close()


@pytest.mark.parametrize("kind", ["agent", "structurer"])
def test_owned_sdk_client_has_finite_phase_timeouts_and_no_sdk_retry(monkeypatch, kind):
    clients = install_transport(monkeypatch, lambda request: success_response())
    llm = construct(kind, api_key="local-test-placeholder", base_url="https://mock.invalid/v1")
    try:
        assert llm.client.max_retries == 0
        assert llm.client.timeout.as_dict() == {
            "connect": 15.0, "read": 180.0, "write": 30.0, "pool": 10.0,
        }
        assert invoke(llm, kind) == OUTPUT
    finally:
        for client in clients:
            client.close()


@pytest.mark.parametrize("kind", ["agent", "structurer"])
@pytest.mark.parametrize("message,compatible", [
    ("create() got an unexpected keyword argument 'response_format'", True),
    ('create() got an unexpected keyword argument "response_format"', True),
    ("create() got an unexpected keyword argument 'model'", False),
    ("internal conversion failed while handling response_format", False),
])
def test_injected_signature_rejection_is_specific(kind, message, compatible):
    calls = []
    error = TypeError(message)

    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise error
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(OUTPUT)))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm = construct(kind, client=client)
    assert llm.client is client
    if compatible:
        assert invoke(llm, kind) == OUTPUT
        assert len(calls) == 2
        assert "response_format" not in calls[1]
    else:
        with pytest.raises(TypeError) as caught:
            invoke(llm, kind)
        assert caught.value is error
        assert len(calls) == 1


@pytest.mark.parametrize("kind", ["agent", "structurer"])
@pytest.mark.parametrize("error", [RuntimeError("Internal failure"),
                                   ValueError("Invalid local input")])
def test_arbitrary_injected_exception_propagates_unchanged(kind, error):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        raise error

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm = construct(kind, client=client)
    with pytest.raises(type(error)) as caught:
        invoke(llm, kind)
    assert caught.value is error
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["agent", "structurer"])
def test_success_without_capability_failure_needs_one_request(monkeypatch, kind):
    requests = []

    def handler(request):
        requests.append(request)
        return success_response()

    clients = install_transport(monkeypatch, handler)
    llm = construct(kind, api_key="local-test-placeholder", base_url="https://mock.invalid/v1")
    try:
        assert invoke(llm, kind) == OUTPUT
        assert len(requests) == 1
        assert requests[0].extensions["timeout"] == llm.client.timeout.as_dict()
    finally:
        for client in clients:
            client.close()
