"""web_api/main.py — FastAPI 后端（BUILD-PLAN Stage 3/5）。

端点：
  POST /chat        SSE：先流 trace（逐工具）→ 再逐槽位 → done。
  POST /simulate    模拟器页签：canonical id 直调 P4/P5 蒙特卡洛（零 LLM）。
  GET  /wiki/{path} 只读返回 wiki 页（图鉴页 Stage 4 用）。
  GET  /healthz     存活探针。

安全（Stage 5 既定）：key 只读 env（DEEPSEEK_API_KEY）；CORS 白名单；限流（见
`web_api/ratelimit.py`）；会话内存 session。启动做资产前置校验（`web_api/preflight.py`），
缺卷在日志里吼出来并反映到 /healthz，不静默降级。
LLM 未配置（无 key）时以 Fake 直答降级，端点仍可用于前端联调，绝不因缺 key 崩溃。
"""
from __future__ import annotations

import contextlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from web_api.contract import (Answer, ChangelogFactionPage, ChangelogIndex,
                              CoreRuleChapter, CoreRuleChapterListResponse,
                              CritiqueReportOut, DetachmentDetail,
                              DetachmentListResponse, KeywordDetail,
                              KeywordIndexResponse, RosterIn, SimResponse,
                              ValidationReportOut)
from web_api.formatter import format_answer
from web_api.preflight import (retrieval_enabled, run_preflight,
                               summary as preflight_summary)
from web_api.ratelimit import install as install_rate_limit
from web_api.trace import TraceRecorder

# ── 配置（全部从 env 读，不落盘）─────────────────────────────────
_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "WEB_API_CORS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if o.strip()
]
_PROVIDER = os.environ.get("WEB_API_LLM_PROVIDER", "DeepSeek")
_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ── 预热：首个 /chat 要现加载 bge-m3（CPU、GB 级），冷启动能等到超时。
# 容器里 WEB_API_WARMUP=1 让它在后台线程提前加载，状态如实挂到 /healthz。
_WARMUP: Dict[str, Any] = {"requested": False, "done": False, "error": None}


def _warmup_resources() -> None:
    try:
        import importlib
        app_mod = importlib.import_module("app")
        _embeddings, vectorstore, _r, _w = app_mod.load_resources()
        _WARMUP["done"] = True
        _WARMUP["error"] = None
        print("[warmup] 检索资源就绪（vectorstore={}）".format(
            "已加载" if vectorstore is not None else "缺索引"), flush=True)
    except Exception as exc:                      # 预热失败必须吼出来，不吞
        _WARMUP["error"] = "{}: {}".format(type(exc).__name__, exc)
        print("[warmup] ⚠ 预热失败：{}（首个请求会现加载并可能再次失败）".format(
            _WARMUP["error"]), flush=True)


@contextlib.asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    run_preflight()
    if os.environ.get("WEB_API_WARMUP", "") == "1" and retrieval_enabled():
        _WARMUP["requested"] = True
        threading.Thread(target=_warmup_resources, name="warmup",
                         daemon=True).start()
    yield


app = FastAPI(title="40K 规则专家 API", version="0.4.0", lifespan=_lifespan)
# 顺序要紧：先挂限流、后挂 CORS，CORS 才在外层——429 响应带得上跨域头，
# 浏览器 OPTIONS 预检也不会白占配额。
install_rate_limit(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 会话内存 session：sid → 历史轮（蓝图既定，不引数据库）
_SESSIONS: Dict[str, List[Dict[str, str]]] = {}


class ChatRequest(BaseModel):
    question: str
    context: str = "当前语境：通用"
    session_id: Optional[str] = None


def _make_clients():
    """构造主循环 LLM + 结构化 LLM；无 key 时返回 (None, None) 触发降级。"""
    if not _API_KEY:
        return None, None
    from agent.llm_client import OpenAICompatLLMClient
    from web_api.structurer import OpenAIStructuringLLM
    llm = OpenAICompatLLMClient(api_key=_API_KEY, provider=_PROVIDER)
    structurer = OpenAIStructuringLLM(
        api_key=_API_KEY, base_url=llm.base_url, model=llm.model)
    return llm, structurer


_NO_LLM_MSG = "后端未配置 LLM（DEEPSEEK_API_KEY 缺失），暂无法生成回答。"


def _degraded_answer(question: str, message: Optional[str] = None) -> Answer:
    """诚实降级回答（不编造）。

    `message` 是**完整**说明而非后缀：降级原因不止"缺 key"一种，措辞必须指向
    这次真正的原因。轻量部署里主因是没开检索，却先甩一句"key 缺失"，等于把人
    往错方向引。
    """
    from agent.loop import AgentResult
    from web_api.formatter import format_answer as _ff
    from web_api.trace import TraceRecorder as _TR
    rec = _TR({})
    res = AgentResult(
        answer=message or _NO_LLM_MSG,
        intent="查", tool_calls=[], degraded=True, sources=[])
    return _ff(question, res, rec, structurer=None)


def _run_answer(req: ChatRequest) -> Answer:
    # 小内存部署（WEB_API_RETRIEVAL=off）只上三个零 LLM 页签：检索栈实测常驻 3.2 GB。
    # 这里必须**提前**明确降级——不拦的话 agent 会一路跑到 rag_search 才因缺 torch 抛错，
    # 被 except 吞成"未检索到相关段落"，看起来像"库里没有"，而真相是"这台机器没装检索"。
    if not retrieval_enabled():
        return _degraded_answer(
            req.question,
            "本站为轻量部署，规则问答未启用：它依赖 bge-m3 向量检索，"
            "实测常驻内存超过 3 GB，超出本机规格。"
            "图鉴 / 模拟器 / 军表实验室三个页签是纯引擎计算，功能完整可用，"
            "数值与官方 11 版一致。")
    llm, structurer = _make_clients()
    if llm is None:
        return _degraded_answer(req.question)
    from agent.tools import TOOLS
    recorder = TraceRecorder(TOOLS)
    from agent.loop import AgentLoop
    loop = AgentLoop(llm=llm, tools=recorder.wrapped_tools())
    result = loop.run(req.question)
    if req.session_id:
        hist = _SESSIONS.setdefault(req.session_id, [])
        hist.append({"role": "user", "content": req.question})
        hist.append({"role": "assistant", "content": result.answer})
    return format_answer(req.question, result, recorder, structurer)


def _sse(event: str, data: Any) -> str:
    return "event: {}\ndata: {}\n\n".format(
        event, json.dumps(data, ensure_ascii=False))


def _stream_answer(answer: Answer):
    """先流 trace（逐工具）→ 再逐槽位 → done。"""
    d = answer.model_dump(by_alias=True)
    yield _sse("meta", {"summary": d["summary"], "traceWarn": d.get("traceWarn"),
                        "degraded": d["degraded"]})
    for step in d["trace"]:
        yield _sse("trace", step)
    yield _sse("verdict", d["verdict"])
    for c in d["calc"]:
        yield _sse("calc", c)
    if d.get("entityCard"):
        yield _sse("entityCard", d["entityCard"])
    for c in d["cites"]:
        yield _sse("cite", c)
    if d.get("sensitivity"):
        yield _sse("sensitivity", d["sensitivity"])
    if d.get("cta"):
        yield _sse("cta", d["cta"])
    yield _sse("followups", d["followups"])
    yield _sse("done", {"ok": True})


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    """存活 + 就绪。ok 只说进程活着；ready 说必需资产都挂上了，别混用。"""
    info = preflight_summary()
    return {
        "ok": True,
        "llm_configured": bool(_API_KEY),
        "retrieval": info["retrieval"],
        "ready": info["ready"],
        "assets": info["assets"],
        "warmup": dict(_WARMUP),
    }


@app.post("/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    """SSE 结构化回答。v1 先跑完 loop 再按序推（trace 已录全）。"""
    answer = _run_answer(req)
    return StreamingResponse(
        _stream_answer(answer),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/sync", response_model=Answer)
def chat_sync(req: ChatRequest) -> Answer:
    """非流式整体返回（便于前端调试/契约测试）。"""
    return _run_answer(req)


DB_PATH = Path(__file__).resolve().parent.parent / "db" / "wh40k.sqlite"


@app.get("/codex/factions")
def codex_factions(include_legacy: bool = False) -> Dict[str, Any]:
    """图鉴：有单位的阵营列表（Stage 4）。

    默认只数现役单位；include_legacy=1 把 Legends/福基世界等传承条目一并计入。
    """
    from web_api import codex
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    return {"factions": codex.list_factions(DB_PATH, include_legacy=include_legacy)}


@app.get("/codex/factions/{faction_id}/units")
def codex_units(faction_id: str, include_legacy: bool = False) -> Dict[str, Any]:
    """图鉴：某阵营单位列表。默认只列现役，传承条目需 include_legacy=1。"""
    from web_api import codex
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    if not codex.faction_exists(DB_PATH, faction_id):
        raise HTTPException(status_code=404, detail="阵营不存在")
    return {"faction_id": faction_id,
            "units": codex.list_units(DB_PATH, faction_id,
                                      include_legacy=include_legacy)}


@app.get("/codex/units/{unit_id}")
def codex_unit(unit_id: str, lang: str = "zh") -> Dict[str, Any]:
    """图鉴：单位兵牌（EntityCard）。lang=zh 本地化优先 / lang=en 全英文。"""
    from web_api import codex
    if lang not in ("zh", "en"):
        raise HTTPException(status_code=422, detail="lang 仅支持 zh/en")
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    card = codex.unit_card(DB_PATH, unit_id, lang=lang)
    if card is None:
        raise HTTPException(status_code=404, detail="单位不存在")
    return {"card": card.model_dump(by_alias=True)}


@app.get("/codex/keywords", response_model=KeywordIndexResponse,
         response_model_by_alias=True)
def codex_keywords() -> KeywordIndexResponse:
    """图鉴：武器词条（USR）索引。

    数据来自离线载荷 `wiki/indexes/keywords.json`（不查库、不读 PDF，容器没挂 data/）。
    返回的条目不带 weapons 反查表——那占载荷九成体积，索引页一把也用不上。
    """
    from web_api import keywords as kw
    try:
        items = kw.list_keywords()
    except kw.KeywordPayloadError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return KeywordIndexResponse(items=items)


@app.get("/codex/keywords/{slug}", response_model=KeywordDetail,
         response_model_by_alias=True)
def codex_keyword(slug: str) -> KeywordDetail:
    """图鉴：单个武器词条详情（含「哪些武器带它」反查表）。未知 slug 404。"""
    from web_api import keywords as kw
    try:
        item = kw.get_keyword(slug)
    except kw.KeywordPayloadError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if item is None:
        raise HTTPException(status_code=404, detail="词条不存在")
    return KeywordDetail(**item)


class SimulateRequest(BaseModel):
    attacker_id: str = Field(alias="attackerId")
    defender_id: str = Field(alias="defenderId")
    options: Dict[str, Any] = {}

    model_config = ConfigDict(populate_by_name=True)


# 蒙特卡洛重活的并发上限：n 已钳到 ≤20000，再对并发数封顶，防多客户端/多标签
# 齐发把 FastAPI 同步线程池打满（sync 端点跑在 threadpool，用 threading 原语）。
_SIM_MAX_CONCURRENCY = 4
_SIM_SEMAPHORE = threading.Semaphore(_SIM_MAX_CONCURRENCY)


@app.post("/simulate", response_model=SimResponse, response_model_by_alias=True)
def simulate(req: SimulateRequest) -> SimResponse:
    """模拟器页签（Stage 4）：图鉴 canonical id 直调 P4/P5 蒙特卡洛核心。

    需 DEEPSEEK_API_KEY？不需要——纯引擎计算零 LLM。失败以 ok=False + reason
    结构化返回（loadout_required 附武器池），仅未知 id 走 404；并发饱和走 503。
    """
    from web_api.simulate import run_simulation
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    if not _SIM_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="模拟器繁忙，请稍后重试")
    try:
        resp = run_simulation(DB_PATH, req.attacker_id, req.defender_id, req.options)
    finally:
        _SIM_SEMAPHORE.release()
    if resp is None:
        raise HTTPException(status_code=404, detail="攻方或守方单位不存在")
    return resp


@app.get("/roster/detachments")
def roster_detachments(faction: str) -> Dict[str, Any]:
    """某阵营的分队目录（从 enhancements 表派生）。"""
    from web_api.roster import list_detachments
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    return {"detachments": list_detachments(DB_PATH, faction)}


@app.get("/roster/enhancements")
def roster_enhancements(detachment: str) -> Dict[str, Any]:
    """某分队的合法强化清单（强化下拉用）。"""
    from web_api.roster import list_enhancements
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    return {"enhancements": list_enhancements(DB_PATH, detachment)}


@app.get("/roster/units/{unit_id}/weapons")
def roster_unit_weapons(unit_id: str) -> Dict[str, Any]:
    """单位武器选项池（装配面板用）；未知单位 404。"""
    from web_api.roster import unit_weapon_pool
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    pool = unit_weapon_pool(DB_PATH, unit_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="单位不存在")
    return {"weaponPool": pool}


@app.post("/roster/validate", response_model=ValidationReportOut,
          response_model_by_alias=True)
def roster_validate(req: RosterIn) -> ValidationReportOut:
    """军表验表（实时重算：点数+编制合法性，零 LLM 零模拟，可每次编辑即调）。"""
    from web_api.roster import validate_roster
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    return validate_roster(DB_PATH, req)


@app.post("/roster/critique", response_model=CritiqueReportOut,
          response_model_by_alias=True)
def roster_critique(req: RosterIn) -> CritiqueReportOut:
    """军表点评（蒙特卡洛：每单位打典型目标）。并发饱和走 503（复用模拟并发闸）。"""
    from web_api.roster import critique_roster
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    if not _SIM_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="点评繁忙，请稍后重试")
    try:
        return critique_roster(DB_PATH, req)
    finally:
        _SIM_SEMAPHORE.release()


@app.get("/codex/factions/{faction_id}/detachments",
         response_model=DetachmentListResponse, response_model_by_alias=True)
def codex_detachments(faction_id: str) -> DetachmentListResponse:
    """图鉴：某阵营的分队列表（数据源是 wiki/ 下已发布的 .md，不查 sqlite）。

    未知阵营 404；wiki 卷没挂上/产物残缺 503——**不返回空列表**，那在前端长得跟
    「这个阵营没有分队」一模一样。真没有分队的阵营（泰坦军团、无阵营工事）才给空。
    """
    from web_api import wiki_browse
    try:
        return DetachmentListResponse(items=wiki_browse.list_detachments(faction_id))
    except wiki_browse.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except wiki_browse.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/codex/factions/{faction_id}/detachments/{slug}",
         response_model=DetachmentDetail, response_model_by_alias=True)
def codex_detachment(faction_id: str, slug: str) -> DetachmentDetail:
    """图鉴：分队详情，增强与战略内联返回（免前端为一页打八次请求）。

    路由必须带 faction_id：同名分队跨阵营存在（Infestation Swarm 在 GC 与 TYR 各一个）。
    子页对不上账（清单列了 N 条、读到 M 条）走 503 并在日志点名，不悄悄少给。
    """
    from web_api import wiki_browse
    try:
        return wiki_browse.detachment_detail(faction_id, slug)
    except wiki_browse.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except wiki_browse.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/codex/rules", response_model=CoreRuleChapterListResponse,
         response_model_by_alias=True)
def codex_rule_chapters() -> CoreRuleChapterListResponse:
    """图鉴：11 版核心规则章节目录（24 章）。

    数据源是 wiki/core-rules/sections/*.md（离线生成物），不查库不读 PDF。
    wiki 卷没挂上/产物残缺 503——**不返回空列表**，那在前端长得跟「这一版没有核心规则」
    一模一样。
    """
    from web_api import core_rules_browse as crb
    try:
        return CoreRuleChapterListResponse(items=crb.list_chapters())
    except crb.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/codex/rules/{slug}", response_model=CoreRuleChapter,
         response_model_by_alias=True)
def codex_rule_chapter(slug: str) -> CoreRuleChapter:
    """图鉴：某章全文。正文是官方简体中文，每节带一个官方英文原文折叠块。

    导语一并返回（里面是「中文由 PDF 文本层直提，判定以英文原文为准」那条披露），
    前端必须显示——丢了它这页就像一份官方中文定稿。
    """
    from web_api import core_rules_browse as crb
    try:
        return crb.chapter_detail(slug)
    except crb.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except crb.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/codex/changelog", response_model=ChangelogIndex,
         response_model_by_alias=True)
def codex_changelog() -> ChangelogIndex:
    """图鉴：规则变更清单首页（通用规则更新 + 28 阵营包一览）。

    响应前会把 index 的一览表与 28 个阵营页逐条对账（条目数、🆕 数、页是否都在）；
    对不上一律 503 并在日志点名——"592 条改动"是这页的头条断言，
    悄悄少几条页面照样渲染得漂漂亮亮。
    """
    from web_api import changelog_browse as cgb
    try:
        return cgb.changelog_index()
    except cgb.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/codex/changelog/{slug}", response_model=ChangelogFactionPage,
         response_model_by_alias=True)
def codex_changelog_faction(slug: str) -> ChangelogFactionPage:
    """图鉴：某阵营包官方「规则更新」全文。未知 slug 404。"""
    from web_api import changelog_browse as cgb
    try:
        return cgb.faction_changelog(slug)
    except cgb.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except cgb.WikiUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/wiki/{path:path}")
def wiki(path: str) -> Dict[str, Any]:
    """只读返回 wiki 页 markdown（图鉴页 Stage 4 用）。"""
    from pathlib import Path
    wiki_root = (Path(__file__).resolve().parent.parent / "wiki").resolve()
    # 防目录穿越：解析后必须仍在 wiki_root **内**。
    # 旧实现用 str.startswith 比前缀——`../wiki_engine/from_db` 解析成
    # `…/RAG/wiki_engine/from_db.md`，字符串仍以 `…/RAG/wiki` 开头，守卫形同虚设
    # （同前缀兄弟目录 wiki_engine/wiki_build/wiki_compile 的 .md 全可读）。
    # 改按路径分量判定：is_relative_to（Python 3.9+）不吃前缀巧合。
    target = (wiki_root / (path + ".md")).resolve()
    if not target.is_relative_to(wiki_root) or not target.is_file():
        raise HTTPException(status_code=404, detail="wiki 页不存在")
    return {"path": path, "markdown": target.read_text(encoding="utf-8")}
