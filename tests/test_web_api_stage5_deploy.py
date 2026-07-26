"""tests/test_web_api_stage5_deploy.py — Stage 5 部署硬化测试。

覆盖三块：
  1. 限流器本体（固定窗口、两档配额、键驱逐、X-Forwarded-For 默认不信）
  2. 限流中间件挂进 FastAPI 后的真实行为（429 + Retry-After + /healthz 豁免）
  3. 启动前置校验（缺资产要报得出来）与部署配置文件的一致性

第 3 块是「假部署」防线：Dockerfile/compose 里写的路径必须和代码里真实读取的
路径对得上——挂载键写错时容器照样能起来，只是所有回答静默降级，正是这项目
最忌讳的失败形态。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_api import preflight
from web_api.ratelimit import (EXEMPT_PATHS, FixedWindowLimiter,
                               RateLimitConfig, bucket_of, client_key, install)

REPO = Path(__file__).resolve().parent.parent


# ── 1. 限流器本体 ────────────────────────────────────────────────

class _Clock:
    """可手拨的单调时钟，避免测试里真的 sleep。"""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_limiter_allows_up_to_limit_then_blocks():
    clock = _Clock()
    lim = FixedWindowLimiter(RateLimitConfig(3, 3, window_s=60.0), clock)
    assert [lim.check("1.2.3.4", "default") for _ in range(3)] == [None] * 3
    retry = lim.check("1.2.3.4", "default")
    assert retry is not None and 0 < retry <= 60.0


def test_limiter_window_rolls_over():
    clock = _Clock()
    lim = FixedWindowLimiter(RateLimitConfig(2, 2, window_s=60.0), clock)
    lim.check("a", "default")
    lim.check("a", "default")
    assert lim.check("a", "default") is not None
    clock.t += 61.0
    assert lim.check("a", "default") is None


def test_limiter_buckets_and_clients_are_independent():
    clock = _Clock()
    lim = FixedWindowLimiter(RateLimitConfig(5, 1, window_s=60.0), clock)
    assert lim.check("a", "heavy") is None
    assert lim.check("a", "heavy") is not None      # heavy 档只有 1
    assert lim.check("a", "default") is None        # default 档不受影响
    assert lim.check("b", "heavy") is None          # 另一个客户端不受影响


def test_limiter_zero_means_unlimited():
    lim = FixedWindowLimiter(RateLimitConfig(0, 0, window_s=60.0), _Clock())
    assert all(lim.check("a", "default") is None for _ in range(1000))


def test_limiter_evicts_expired_keys_instead_of_growing_forever():
    clock = _Clock()
    lim = FixedWindowLimiter(RateLimitConfig(10, 10, window_s=60.0), clock)
    for i in range(5000):
        lim.check("ip-{}".format(i), "default")
    assert len(lim._hits) <= 4096                   # 有上限，不会无限涨
    clock.t += 61.0
    lim.check("fresh", "default")
    assert lim.check("fresh", "default") is None    # 过期键清掉后仍能正常服务


def test_bucket_routing_matches_expensive_endpoints():
    assert bucket_of("/chat") == "heavy"
    assert bucket_of("/chat/sync") == "heavy"
    assert bucket_of("/simulate") == "heavy"
    assert bucket_of("/roster/critique") == "heavy"
    # 实时重算是前端每次编辑都调的轻活，不能进 heavy 档
    assert bucket_of("/roster/validate") == "default"
    assert bucket_of("/codex/factions") == "default"


def test_forwarded_header_ignored_unless_trusted():
    # 默认不信：伪造 XFF 换不来新配额
    assert client_key("10.0.0.1", "9.9.9.9", trust_forwarded=False) == "10.0.0.1"
    # 显式信任时取首段
    assert client_key("10.0.0.1", "9.9.9.9, 10.0.0.1",
                      trust_forwarded=True) == "9.9.9.9"
    # 信任但头为空 → 回落 socket 地址
    assert client_key("10.0.0.1", "", trust_forwarded=True) == "10.0.0.1"
    assert client_key(None, None, trust_forwarded=False) == "unknown"


# ── 2. 中间件端到端 ──────────────────────────────────────────────

def _app_with_limit(default: int, heavy: int) -> TestClient:
    app = FastAPI()
    install(app, RateLimitConfig(default, heavy, window_s=60.0), _Clock())

    @app.get("/healthz")
    def _health():
        return {"ok": True}

    @app.get("/codex/factions")
    def _light():
        return {"ok": True}

    @app.post("/simulate")
    def _heavy():
        return {"ok": True}

    return TestClient(app)


def test_middleware_returns_429_with_retry_after():
    client = _app_with_limit(default=2, heavy=1)
    assert client.get("/codex/factions").status_code == 200
    assert client.get("/codex/factions").status_code == 200
    resp = client.get("/codex/factions")
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1
    assert "频繁" in resp.json()["detail"]


def test_middleware_heavy_bucket_is_stricter():
    client = _app_with_limit(default=10, heavy=1)
    assert client.post("/simulate").status_code == 200
    assert client.post("/simulate").status_code == 429
    # 轻端点还有额度，不该被重活的超限连坐
    assert client.get("/codex/factions").status_code == 200


def test_healthz_is_never_rate_limited():
    client = _app_with_limit(default=1, heavy=1)
    for _ in range(20):
        assert client.get("/healthz").status_code == 200


def test_healthz_path_is_in_exempt_list():
    assert "/healthz" in EXEMPT_PATHS


# ── 3. 前置校验 + 部署配置一致性 ─────────────────────────────────

def test_preflight_reports_missing_assets(tmp_path):
    statuses = preflight.check_assets(tmp_path)      # 空目录：什么都没有
    assert [s.ok for s in statuses] == [False] * len(statuses)
    assert {s.name for s in statuses} == {
        "embed_model", "vector_store", "structured_db", "wiki", "keyword_index"}
    # 每条缺失都要给出人话原因和修复办法，不能只报个 False
    assert all(s.detail and s.hint for s in statuses)
    summary = preflight.summary(tmp_path)
    assert summary["ready"] is False


def test_preflight_detects_present_assets(tmp_path):
    snap = tmp_path / "opt" / "models--BAAI--bge-m3" / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "modules.json").write_text("{}", encoding="utf-8")
    (tmp_path / "local_vector_store").mkdir()
    (tmp_path / "local_vector_store" / "index.faiss").write_bytes(b"")
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "wh40k.sqlite").write_bytes(b"")
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "index.md").write_text("# index", encoding="utf-8")
    (tmp_path / "wiki" / "indexes").mkdir()
    (tmp_path / "wiki" / "indexes" / "keywords.json").write_text(
        '{"items": []}', encoding="utf-8")
    summary = preflight.summary(tmp_path)
    assert summary["ready"] is True
    assert all(a["ok"] for a in summary["assets"])


def test_preflight_rejects_half_downloaded_snapshot(tmp_path):
    """只下了一半的快照（无 modules.json）要算缺失——否则容器起来后第一次
    检索才在 HF 联网重试里超时，错得又晚又难查。"""
    snap = tmp_path / "opt" / "models--BAAI--bge-m3" / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}", encoding="utf-8")
    embed = [s for s in preflight.check_assets(tmp_path) if s.name == "embed_model"][0]
    assert embed.ok is False


def test_retrieval_off_demotes_model_and_index_to_optional(tmp_path, monkeypatch):
    """轻量部署（WEB_API_RETRIEVAL=off）下模型与索引按设计不该在场：
    它们必须降为非必需，否则 ready 天天 false，人就学会无视它。"""
    monkeypatch.setenv("WEB_API_RETRIEVAL", "off")
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "wh40k.sqlite").write_bytes(b"")
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "index.md").write_text("# index", encoding="utf-8")
    info = preflight.summary(tmp_path)
    assert info["retrieval"] is False
    assert info["ready"] is True, "只缺检索资产时轻量部署应判就绪"
    by_name = {a["name"]: a for a in info["assets"]}
    assert by_name["embed_model"]["required"] is False
    assert by_name["vector_store"]["required"] is False
    # 但仍如实报告"不在场"，并说明是没开而不是坏了
    assert by_name["embed_model"]["ok"] is False
    assert "未启用" in by_name["embed_model"]["detail"]
    # 结构库仍是硬要求——三个页签全靠它
    assert by_name["structured_db"]["required"] is True


def test_retrieval_off_still_fails_on_missing_db(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_API_RETRIEVAL", "off")
    assert preflight.summary(tmp_path)["ready"] is False


def test_retrieval_on_is_the_default(tmp_path, monkeypatch):
    monkeypatch.delenv("WEB_API_RETRIEVAL", raising=False)
    assert preflight.retrieval_enabled() is True
    assert preflight.summary(tmp_path)["retrieval"] is True


def test_report_marks_skipped_assets_differently_from_missing(monkeypatch):
    """[略] 与 [缺!] 必须分得开——否则轻量部署的日志读起来像坏了。"""
    monkeypatch.setenv("WEB_API_RETRIEVAL", "off")
    report = preflight.format_report(preflight.check_assets(REPO / "no-such-dir"))
    assert "[略 ]" in report and "检索关" in report


def test_preflight_strict_mode_refuses_to_start(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_API_PREFLIGHT_STRICT", "1")
    with pytest.raises(RuntimeError):
        preflight.run_preflight(tmp_path, echo=False)


def test_preflight_report_marks_missing_required():
    statuses = preflight.check_assets(REPO / "no-such-dir")
    report = preflight.format_report(statuses)
    assert "缺!" in report and "必需资产缺失" in report


# ── 部署文件存在性与路径一致性（防"挂载键写错→静默降级"）──────

DEPLOY_FILES = ["Dockerfile", ".dockerignore", "docker-compose.yml",
                ".env.example", "requirements-docker.txt",
                "requirements-server.txt",
                "web/Dockerfile", "web/.dockerignore",
                "deploy/wh40k-api.service", "deploy/openresty-site.conf",
                "deploy/deploy.sh"]


@pytest.mark.parametrize("rel", DEPLOY_FILES)
def test_deploy_file_exists(rel):
    assert (REPO / rel).exists(), "{} 缺失，部署链不完整".format(rel)


def test_compose_mounts_cover_every_required_asset():
    """compose 的挂载目标必须覆盖 preflight 认定的每个必需资产目录。"""
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    targets = set(re.findall(r"-\s+\./[^:]+:(/app/[^:\s]+):ro", compose))
    for status in preflight.check_assets(REPO):
        if not status.required:
            continue
        top = Path(status.path).relative_to(REPO).parts[0]
        assert "/app/{}".format(top) in targets, \
            "必需资产 {} 所在的 {}/ 没在 compose 里挂载".format(status.name, top)


def test_compose_mounts_are_readonly_and_bound_to_loopback():
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    # 行尾常跟着注释，别用 $ 锚定（正则太紧会把真挂载漏成"没解析到"）
    mounts = re.findall(r"^\s+-\s+(\./\S+)", compose, re.M)
    assert mounts, "compose 里没解析到卷挂载，正则或文件结构变了"
    assert all(m.endswith(":ro") for m in mounts), \
        "容器不该有权写宿主机数据资产：{}".format(mounts)
    ports = re.findall(r'-\s+"([^"]+:\d+:\d+)"', compose)
    assert ports and all(p.startswith("127.0.0.1:") for p in ports), \
        "端口必须只绑本机（含规则书衍生内容，不外露）：{}".format(ports)


def test_dockerignore_excludes_heavy_assets_and_secrets():
    ignored = {
        line.strip() for line in
        (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    for heavy in ("opt/", "data/", "local_vector_store/", "db/", ".venv/"):
        assert heavy in ignored, "{} 没排除，构建上下文会传几个 G".format(heavy)
    assert ".env" in ignored, "密钥文件必须挡在镜像外"
    assert ".git/" in ignored


def test_env_example_documents_every_env_var_the_code_reads():
    """代码里读的每个 WEB_API_* 变量都要在 .env.example 里有交代，
    否则部署时只能靠翻源码猜。"""
    env_example = (REPO / ".env.example").read_text(encoding="utf-8")
    sources = "\n".join(
        (REPO / "web_api" / name).read_text(encoding="utf-8")
        for name in ("main.py", "ratelimit.py", "preflight.py")
    )
    used = set(re.findall(r'"(WEB_API_[A-Z_]+)"', sources))
    assert used, "没扫到 WEB_API_* 变量，正则或代码结构变了"
    missing = sorted(v for v in used if v not in env_example)
    assert not missing, "这些变量没写进 .env.example：{}".format(missing)


def test_next_config_supports_both_output_modes():
    """两种部署形态都要在配置里立得住：
    - standalone（默认）：web/Dockerfile 只拷 .next/standalone，没开就在 COPY 阶段炸
    - export：静态产物 out/ 交给服务器已有的 openresty 托管，省掉 node 进程
    """
    cfg = (REPO / "web" / "next.config.ts").read_text(encoding="utf-8")
    assert 'NEXT_OUTPUT === "export"' in cfg, "缺静态导出分支"
    assert '"standalone"' in cfg, "缺 standalone 默认值"
    assert "output," in cfg or "output:" in cfg
