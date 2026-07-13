"""web_api/main.py — FastAPI 后端（BUILD-PLAN Stage 3/5）。

端点：
  POST /chat        SSE：先流 trace（逐工具）→ 再逐槽位 → done。
  POST /simulate    模拟器页签：canonical id 直调 P4/P5 蒙特卡洛（零 LLM）。
  GET  /wiki/{path} 只读返回 wiki 页（图鉴页 Stage 4 用）。
  GET  /healthz     存活探针。

安全（Stage 5 既定）：key 只读 env（DEEPSEEK_API_KEY）；CORS 白名单；会话内存 session。
LLM 未配置（无 key）时以 Fake 直答降级，端点仍可用于前端联调，绝不因缺 key 崩溃。
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from web_api.contract import Answer, SimResponse
from web_api.formatter import format_answer
from web_api.trace import TraceRecorder

# ── 配置（全部从 env 读，不落盘）─────────────────────────────────
_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "WEB_API_CORS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if o.strip()
]
_PROVIDER = os.environ.get("WEB_API_LLM_PROVIDER", "DeepSeek")
_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

app = FastAPI(title="40K 规则专家 API", version="0.3.0")
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


def _degraded_answer(question: str, note: str) -> Answer:
    """无 LLM 可用时的诚实降级回答（不编造）。"""
    from agent.loop import AgentResult
    from web_api.formatter import format_answer as _ff
    from web_api.trace import TraceRecorder as _TR
    rec = _TR({})
    res = AgentResult(
        answer="后端未配置 LLM（DEEPSEEK_API_KEY 缺失），暂无法生成回答。" + note,
        intent="查", tool_calls=[], degraded=True, sources=[])
    return _ff(question, res, rec, structurer=None)


def _run_answer(req: ChatRequest) -> Answer:
    llm, structurer = _make_clients()
    if llm is None:
        return _degraded_answer(req.question, "")
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
    return {"ok": True, "llm_configured": bool(_API_KEY)}


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
def codex_factions() -> Dict[str, Any]:
    """图鉴：有单位的阵营列表（Stage 4）。"""
    from web_api import codex
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    return {"factions": codex.list_factions(DB_PATH)}


@app.get("/codex/factions/{faction_id}/units")
def codex_units(faction_id: str) -> Dict[str, Any]:
    """图鉴：某阵营单位列表。"""
    from web_api import codex
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="结构库未构建")
    if not codex.faction_exists(DB_PATH, faction_id):
        raise HTTPException(status_code=404, detail="阵营不存在")
    return {"faction_id": faction_id, "units": codex.list_units(DB_PATH, faction_id)}


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


@app.get("/wiki/{path:path}")
def wiki(path: str) -> Dict[str, Any]:
    """只读返回 wiki 页 markdown（图鉴页 Stage 4 用）。"""
    from pathlib import Path
    wiki_root = Path(__file__).resolve().parent.parent / "wiki"
    # 防目录穿越：解析后必须仍在 wiki_root 内
    target = (wiki_root / (path + ".md")).resolve()
    if not str(target).startswith(str(wiki_root.resolve())) or not target.exists():
        raise HTTPException(status_code=404, detail="wiki 页不存在")
    return {"path": path, "markdown": target.read_text(encoding="utf-8")}
