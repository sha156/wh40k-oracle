"""Paired Origin execution-boundary checks: no providers or production assets."""
import asyncio
import json
from itertools import count

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from web_api import main
from web_api.origin_boundary import OriginBoundaryMiddleware
from web_api.ratelimit import RateLimitConfig, install


ALLOWED = ("http://localhost:3000", "http://127.0.0.1:3000")
_clients = count()


@pytest.fixture
def chat_client(monkeypatch):
    calls = []

    def answer(req):
        calls.append(req.model_dump())
        return main._degraded_answer(req.question, "Harmless Origin fixture")

    monkeypatch.setattr(main, "_run_answer", answer)
    client = TestClient(main.app, client=(f"origin-fixture-{next(_clients)}", 50000))
    yield client, calls
    client.close()


@pytest.mark.parametrize("path", ["/chat/sync", "/chat"])
def test_foreign_origin_without_content_type_never_executes_chat(chat_client, path):
    client, calls = chat_client
    response = client.post(path, content=json.dumps({"question": "Harmless fixture"}).encode(),
                           headers={"Origin": "https://untrusted.invalid"})
    assert response.request.headers.get("content-type") is None
    # Check invocation independently: denied CORS response access is insufficient.
    assert calls == []
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", [None, *ALLOWED])
@pytest.mark.parametrize("path", ["/chat/sync", "/chat"])
def test_authorized_chat_preserves_payload_stream_and_headers(chat_client, origin, path):
    client, calls = chat_client
    headers = {"Content-Type": "application/json"}
    if origin is not None:
        headers["Origin"] = origin
    payload = {"question": "Harmless fixture", "context": "fixture", "session_id": "sid"}
    response = client.post(path, content=json.dumps(payload).encode(), headers=headers)
    assert response.request.headers["content-type"] == "application/json"
    assert response.status_code == 200
    assert calls == [payload]
    assert response.headers.get("access-control-allow-origin") == origin
    if path == "/chat":
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"
        assert "event: done" in response.text
    else:
        assert response.json()["degraded"] is True


@pytest.mark.parametrize("content_type", [None, "text/plain", "application/json"],
                         ids=["untyped", "wrong-type", "json"])
@pytest.mark.parametrize("origin", [None, *ALLOWED])
@pytest.mark.parametrize("path", ["/chat/sync", "/chat"])
def test_chat_content_type_contract_is_separate_from_origin(
        chat_client, content_type, origin, path):
    client, calls = chat_client
    headers = {} if origin is None else {"Origin": origin}
    if content_type is not None:
        headers["Content-Type"] = content_type
    payload = {"question": "Harmless fixture", "context": "fixture", "session_id": "sid"}
    response = client.post(path, content=json.dumps(payload).encode(), headers=headers)
    assert response.request.headers.get("content-type") == content_type
    assert response.headers.get("access-control-allow-origin") == origin
    if content_type == "application/json":
        assert response.status_code == 200
        assert calls == [payload]
        if path == "/chat":
            assert "event: done" in response.text
        else:
            assert response.json()["degraded"] is True
    else:
        assert response.status_code == 422
        assert calls == []
        assert any(error["loc"] == ["body"] for error in response.json()["detail"])


@pytest.mark.parametrize("headers", [
    [("Origin", "null")], [("Origin", "")],
    [("Origin", "http://localhost:3000/")],
    [("Origin", "http://localhost:3000 https://untrusted.invalid")],
    [("Origin", "http://localhost:3000,https://untrusted.invalid")],
    [("Origin", "http://localhost:3000\x00")],
    [("Origin", "http://localhost:3000"), ("Origin", "https://untrusted.invalid")],
    [("Origin", "https://untrusted.invalid"), ("Origin", "http://localhost:3000")],
    [("Origin", "http://localhost:3000"), ("Origin", "http://localhost:3000")],
])
def test_invalid_or_duplicate_origin_never_executes(chat_client, headers):
    client, calls = chat_client
    response = client.post("/chat/sync", json={"question": "Harmless fixture"}, headers=headers)
    assert calls == []
    assert response.status_code == 403


@pytest.mark.parametrize("origin", ALLOWED)
def test_allowed_preflight_does_not_execute_chat(chat_client, origin):
    client, calls = chat_client
    response = client.options("/chat/sync", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-fixture",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-headers"] == "content-type,x-fixture"
    assert calls == []


def test_foreign_preflight_is_rejected(chat_client):
    client, calls = chat_client
    response = client.options("/chat/sync", headers={
        "Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "POST",
    })
    assert response.status_code == 403
    assert calls == []
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("path,payload,module_name,function_name", [
    ("/simulate", {"attackerId": "a", "defenderId": "d"}, "web_api.simulate", "run_simulation"),
    ("/roster/critique", {"factionId": "SM", "units": []}, "web_api.roster", "critique_roster"),
    ("/roster/validate", {"factionId": "SM", "units": []}, "web_api.roster", "validate_roster"),
])
@pytest.mark.parametrize("origin", ["https://untrusted.invalid", None, *ALLOWED])
def test_real_compute_routes_reject_before_handlers_but_keep_authorized_errors(
        monkeypatch, tmp_path, path, payload, module_name, function_name, origin):
    import importlib

    calls = []
    fixture_db = tmp_path / "unused.sqlite"
    fixture_db.touch()
    monkeypatch.setattr(main, "DB_PATH", fixture_db)

    def handler(*args):
        calls.append(True)
        raise HTTPException(status_code=409, detail="Harmless handler fixture")

    monkeypatch.setattr(importlib.import_module(module_name), function_name, handler)
    headers = {} if origin is None else {"Origin": origin}
    if origin != "https://untrusted.invalid":
        headers["Content-Type"] = "application/json"
    with TestClient(main.app, client=(f"origin-fixture-{next(_clients)}", 50000)) as client:
        response = client.post(path, content=json.dumps(payload).encode(), headers=headers)
    if origin == "https://untrusted.invalid":
        assert response.request.headers.get("content-type") is None
        assert calls == []
        assert response.status_code == 403
    else:
        assert response.request.headers["content-type"] == "application/json"
        assert calls == [True]
        assert response.status_code == 409
        assert response.json() == {"detail": "Harmless handler fixture"}
        assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize("path,payload,module_name,function_name,result", [
    ("/simulate", {"attackerId": "a", "defenderId": "d"},
     "web_api.simulate", "run_simulation", {"ok": True}),
    ("/roster/critique", {"factionId": "SM", "units": []},
     "web_api.roster", "critique_roster", {"totalPoints": 0, "summary": ["Harmless fixture"]}),
    ("/roster/validate", {"factionId": "SM", "units": []},
     "web_api.roster", "validate_roster", {"totalPoints": 0, "limit": 2000, "legal": True}),
])
@pytest.mark.parametrize("origin", [None, *ALLOWED])
@pytest.mark.parametrize("content_type", [None, "text/plain", "application/json"],
                         ids=["untyped", "wrong-type", "json"])
def test_compute_content_type_contract_is_separate_from_origin(
        monkeypatch, tmp_path, path, payload, module_name, function_name, result,
        origin, content_type):
    import importlib

    calls = []
    fixture_db = tmp_path / "unused.sqlite"
    fixture_db.touch()
    monkeypatch.setattr(main, "DB_PATH", fixture_db)

    def handler(*args):
        calls.append(True)
        return result

    monkeypatch.setattr(importlib.import_module(module_name), function_name, handler)
    headers = {} if origin is None else {"Origin": origin}
    if content_type is not None:
        headers["Content-Type"] = content_type
    with TestClient(main.app, client=(f"origin-fixture-{next(_clients)}", 50000)) as client:
        response = client.post(path, content=json.dumps(payload).encode(), headers=headers)
    assert response.request.headers.get("content-type") == content_type
    assert response.headers.get("access-control-allow-origin") == origin
    if content_type == "application/json":
        assert response.status_code == 200
        assert calls == [True]
        assert {key: response.json()[key] for key in result} == result
    else:
        assert response.status_code == 422
        assert calls == []
        assert any(error["loc"] == ["body"] for error in response.json()["detail"])


@pytest.mark.parametrize("host", ["localhost", "localhost/healthz?", "localhost/ordinary?", "[invalid"])
def test_raw_host_cannot_change_rate_limit_bucket_or_health_exemption(host):
    app = FastAPI()
    limiter = install(app, RateLimitConfig(10, 1))

    @app.post("/simulate")
    def compute():
        return {"ok": True}

    @app.get("/healthz")
    def health():
        return {"ok": True}

    with TestClient(app) as client:
        assert client.post("/simulate", headers={"Host": host}).status_code == 200
        assert client.post("/simulate", headers={"Host": host}).status_code == 429
        assert client.get("/healthz", headers={"Host": host}).status_code == 200
    assert set(bucket for _, bucket in limiter._hits) == {"heavy"}


def test_rejected_origin_does_not_read_body_or_invoke_inner_app():
    sent = []

    async def forbidden(*args):
        pytest.fail("Origin rejection must not read the body or invoke the inner app")

    async def send(message):
        sent.append(message)

    boundary = OriginBoundaryMiddleware(forbidden, ALLOWED)
    asyncio.run(boundary({"type": "http", "headers": [
        (b"origin", b"https://untrusted.invalid")], "path": "/chat"}, forbidden, send))
    assert sent[0]["status"] == 403
    assert b"untrusted.invalid" not in sent[1]["body"]


def test_configured_origin_cors_errors_and_preflight_quota_are_preserved():
    app = FastAPI()
    configured = ["http://localhost:4321"]
    limiter = install(app, RateLimitConfig(1, 1))
    app.add_middleware(CORSMiddleware, allow_origins=configured,
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    app.add_middleware(OriginBoundaryMiddleware, allowed_origins=configured)
    calls = []

    @app.post("/chat")
    def handler():
        calls.append(True)
        return {"ok": True}

    with TestClient(app) as client:
        assert client.post("/chat", headers={"Origin": ALLOWED[0]}).status_code == 403
        assert limiter._hits == {}  # Rejected Origins consume no handler/quota work.
        for _ in range(3):
            preflight = client.options("/chat", headers={"Origin": configured[0],
                                                       "Access-Control-Request-Method": "POST"})
            assert preflight.status_code == 200
        assert limiter._hits == {}
        assert client.post("/chat", headers={"Origin": configured[0]}).status_code == 200
        limited = client.post("/chat", headers={"Origin": configured[0]})
        assert limited.status_code == 429
        assert limited.headers["access-control-allow-origin"] == configured[0]
        assert int(limited.headers["retry-after"]) >= 1
    assert calls == [True]


@pytest.mark.parametrize("origin", ["null", "*", ""])
def test_special_config_entries_do_not_grant_origin_access(origin):
    app = FastAPI()
    app.add_middleware(OriginBoundaryMiddleware, allowed_origins=[origin])
    with TestClient(app) as client:
        assert client.get("/", headers={"Origin": origin}).status_code == 403
