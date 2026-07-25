"""tests/test_web_api_wiki_route.py — GET /wiki/{path} 只读端点。

这条路由是图鉴 wiki 化（codex-wiki 扩容）的接入点，此前**测试零覆盖**，
而它的目录穿越守卫是字符串前缀比较：

    str(target).startswith(str(wiki_root))

`wiki_root` = `…/RAG/wiki`，而 `path="../wiki_engine/from_db"` 解析后是
`…/RAG/wiki_engine/from_db.md` —— 字符串同样以 `…/RAG/wiki` 开头，守卫放行。
仓库里恰好有三个同前缀兄弟目录（wiki_engine / wiki_build / wiki_compile），
其中的 .md 全部可被读出。本文件把「同前缀兄弟目录」钉成回归用例。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_ROOT = REPO_ROOT / "wiki"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.skipif(not (WIKI_ROOT / "core-rules" / "blast.md").exists(),
                    reason="wiki/core-rules/blast.md 不存在")
def test_wiki_reads_existing_page(client: TestClient) -> None:
    """正常页读得到，且返回的是原始 markdown。"""
    r = client.get("/wiki/core-rules/blast")
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "core-rules/blast"
    assert body["markdown"].lstrip().startswith("---")   # frontmatter


def test_wiki_rejects_parent_escape(client: TestClient) -> None:
    """经典 ../ 逃逸：必须 404。"""
    assert client.get("/wiki/../CLAUDE").status_code == 404


@pytest.mark.parametrize("path", [
    "../wiki_engine/from_db",     # 同前缀兄弟目录（旧守卫在此放行）
    "../wiki_compile/__init__",
    "../wiki_build/x",
])
def test_wiki_rejects_same_prefix_sibling(client: TestClient, path: str) -> None:
    """`wiki*` 同前缀兄弟目录不是 wiki_root 的子目录，一律 404。

    注意本用例的价值不在「该文件此刻是否存在」——旧实现下守卫放行，
    存在即泄漏。所以断言的是**守卫拒绝**，与文件存在与否无关。
    """
    assert client.get("/wiki/{}".format(path)).status_code == 404


def test_wiki_guard_is_path_based_not_prefix_based() -> None:
    """直接钉死判定方式：前缀比较会误判，分量比较不会。

    不经 HTTP，纯粹证明「旧写法为什么不行」——防止有人把守卫改回 startswith。
    """
    wiki_root = WIKI_ROOT.resolve()
    escaped = (wiki_root / "../wiki_engine/from_db.md").resolve()
    assert str(escaped).startswith(str(wiki_root))       # 旧守卫：放行（错）
    assert not escaped.is_relative_to(wiki_root)         # 新守卫：拦截（对）


def test_wiki_missing_page_404(client: TestClient) -> None:
    assert client.get("/wiki/core-rules/no-such-page-xyz").status_code == 404
