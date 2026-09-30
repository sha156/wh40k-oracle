"""Wiki path boundary regressions using present, disposable page fixtures."""
import asyncio
from itertools import count
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from web_api import main


_clients = count()
CONTROLS = [chr(value) for value in (*range(32), 127)]


@pytest.fixture
def wiki_fixture(tmp_path, monkeypatch):
    api = tmp_path / "web_api"
    api.mkdir()
    root = tmp_path / "wiki"
    (root / "nested").mkdir(parents=True)
    pages = {
        "nested/safe": "# Synthetic safe page\n",
        "nested/规则 with space": "# Synthetic Unicode page\n",
        "nested/literal%00": "# Synthetic literal percent page\n",
    }
    for slug, markdown in pages.items():
        (root / (slug + ".md")).write_text(markdown, encoding="utf-8")
    sibling = tmp_path / "wiki_engine"
    sibling.mkdir()
    outside = sibling / "outside.md"
    outside.write_text("Synthetic outside marker", encoding="utf-8")
    monkeypatch.setattr(main, "__file__", str(api / "main.py"))
    with TestClient(main.app, raise_server_exceptions=False,
                    client=(f"wiki-path-{next(_clients)}", 50000)) as client:
        yield client, pages, outside


@pytest.mark.parametrize("control", CONTROLS, ids=lambda value: f"U+{ord(value):04X}")
def test_decoded_controls_return_deliberate_404(wiki_fixture, control):
    client, _, _ = wiki_fixture
    response = client.get("/wiki/" + quote("nested/safe" + control, safe="/"))
    assert response.status_code == 404
    assert response.json() == {"detail": "wiki 页不存在"}
    assert "traceback" not in response.text.lower()


def test_decoded_newline_in_asgi_scope_returns_404(wiki_fixture):
    # Exercise the full decoded scope independently of HTTP client encoding:
    # the router can omit the terminal LF from the captured slug.
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "GET", "scheme": "http", "path": "/wiki/nested/safe\n",
             "raw_path": b"/wiki/nested/safe%0A", "query_string": b"",
             "root_path": "", "headers": [], "client": ("wiki-newline", 50000),
             "server": ("testserver", 80)}
    asyncio.run(main.app(scope, receive, send))
    assert next(item["status"] for item in sent if item["type"] == "http.response.start") == 404


@pytest.mark.parametrize("url", ["/wiki/%00", "/wiki/nested/%00safe"])
def test_nul_at_root_or_inside_slug_returns_404(wiki_fixture, url):
    client, _, _ = wiki_fixture
    response = client.get(url)
    assert response.status_code == 404
    assert response.json() == {"detail": "wiki 页不存在"}


@pytest.mark.parametrize("control", CONTROLS, ids=lambda value: f"U+{ord(value):04X}")
def test_decoded_controls_never_reach_filesystem(monkeypatch, control):
    def unexpected_resolution(*args, **kwargs):
        pytest.fail("Invalid wiki path reached filesystem resolution")

    monkeypatch.setattr(Path, "resolve", unexpected_resolution)
    with pytest.raises(HTTPException) as caught:
        main.wiki("nested/safe" + control)
    assert caught.value.status_code == 404


def test_present_pages_and_percent_encoded_slugs_are_preserved(wiki_fixture):
    client, pages, _ = wiki_fixture
    for slug, markdown in pages.items():
        # The route takes already decoded slugs and must not decode them again.
        assert main.wiki(slug) == {"path": slug, "markdown": markdown}
        if "%" in slug:
            # TestClient's transport unquotes twice; it cannot exercise a literal
            # percent-escape filename over HTTP without changing the input.
            continue
        response = client.get("/wiki/" + quote(slug, safe="/"))
        assert response.status_code == 200
        assert response.json() == {"path": slug, "markdown": markdown}


def test_present_outside_files_remain_confined(wiki_fixture):
    client, _, outside = wiki_fixture
    paths = ["../wiki_engine/outside", r"..\wiki_engine\outside",
             str(outside.with_suffix(""))]
    for path in paths:
        # Encoding keeps HTTP clients from normalizing away the traversal probe.
        response = client.get("/wiki/" + quote(path, safe=""))
        assert response.status_code == 404
        assert "Synthetic outside marker" not in response.text
        with pytest.raises(HTTPException) as caught:
            main.wiki(path)
        assert caught.value.status_code == 404


def test_missing_page_keeps_existing_404(wiki_fixture):
    client, _, _ = wiki_fixture
    response = client.get("/wiki/nested/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "wiki 页不存在"}
