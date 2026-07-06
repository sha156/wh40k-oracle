"""scripts/qa_bench.py — QA 100 题回归 harness（重建版，原判分脚本已丢失）。

对 100 题（题面来自 qa_100_results.json）跑指定路径，用 LLM judge 判 ✅/⚠️/❌，
输出聚合分与逐题结果，与 77% 经典基线对比。

路径：
  classic = 现有混合检索链（app.hybrid_retrieve → LLM 合成），基线复现，用于校准 judge
  agent   = L5 Agent 编排层（agent.loop），完全镜像 app.py 的 Agent 模式：
            先跑 AgentLoop；若降级则转经典链合成（保证不劣于经典）

判分说明：QA 集无 gold answer，judge 按「是否直接/正确/完整回答问题 + 有数据 + 标注来源」
打分（intrinsic）。同一 judge 同时判两条路径 → 对比公平；classic 应复现 ~77% 以校准。

用法（需 Clash 代理 + DEEPSEEK_API_KEY）：
  export HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897
  DEEPSEEK_API_KEY=sk-xxx .venv/Scripts/python.exe scripts/qa_bench.py \
      --path agent --out qa_agent_results.json [--limit N] [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import warnings

warnings.filterwarnings("ignore")

QA_SOURCE = REPO_ROOT / "qa_100_results.json"

_PROVIDERS = {
    "DeepSeek": ("https://api.deepseek.com", "deepseek-chat"),
    "ZhipuAI (GLM-4)": ("https://open.bigmodel.cn/api/paas/v4/", "glm-4-flash"),
}

_JUDGE_SYSTEM = """你是战锤40K规则问答系统的答案质检员。给定【问题】与系统【回答】
（回答基于规则书检索）。只按回答本身的质量判等级，不要自己去猜标准答案：
✅ = 直接、正确、完整地回答了问题，给出具体数据/规则，并标注了《书名》页码来源；
⚠️ = 部分回答 / 信息不全 / 未直接命中问题 / 来源模糊 / 有明显冗余但主旨对；
❌ = 答错、答非所问、声明「档案缺失/未找到」、或明显编造。
输出格式：第一行只写 ✅ 或 ⚠️ 或 ❌，第二行一句话理由。"""


def load_questions(limit=None):
    data = json.loads(QA_SOURCE.read_text(encoding="utf-8"))
    items = [
        {"id": d["id"], "faction": d["faction"], "question": d["question"]}
        for d in data["details"]
    ]
    return items[:limit] if limit else items


def make_client(provider):
    from openai import OpenAI

    base_url, _ = _PROVIDERS[provider]
    return OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=base_url)


def init_resources():
    """加载检索资源并构造绑定了已加载资源的 agent 工具集（镜像 app.build_agent_tools）。"""
    import app

    embeddings, vs, reranker, _ = app.load_resources()
    if vs is None:
        raise SystemExit("向量库未构建（local_vector_store 为空），请先跑 ingest.py")
    bm25 = app.build_bm25(vs)

    def bound_rag_search(query):
        passages = app.hybrid_retrieve(query, vs, bm25, reranker)
        return {
            "found": bool(passages),
            "passages": passages,
            "note": None if passages else "未检索到相关段落",
        }

    from agent.tools import TOOLS as BASE_TOOLS

    tools = {**BASE_TOOLS, "rag_search": bound_rag_search}
    return app, vs, bm25, reranker, tools


def _dedup_sources(passages):
    seen, out = set(), []
    for p in passages:
        key = (p.get("book", "未知"), p.get("page", "?"))
        if key not in seen:
            seen.add(key)
            out.append({"book": key[0], "page": key[1]})
    return out


def answer_classic(app, vs, bm25, reranker, provider, model, client, question):
    passages = app.hybrid_retrieve(question, vs, bm25, reranker)
    if not passages:
        return "档案缺失，建议查阅原始规则书。", []
    context = app.SYSTEM_PROMPT.replace("{context}", app.format_context(passages))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
        max_tokens=1600,
        stream=False,
    )
    return resp.choices[0].message.content, _dedup_sources(passages)


def answer_agent(app, vs, bm25, reranker, tools, provider, model, client, question):
    """镜像 app.py Agent 模式：跑 AgentLoop；降级则转经典链合成。"""
    from agent.llm_client import OpenAICompatLLMClient
    from agent.loop import AgentLoop

    llm = OpenAICompatLLMClient(
        api_key=os.environ["DEEPSEEK_API_KEY"], provider=provider, temperature=0.1,
    )
    result = AgentLoop(llm=llm, tools=tools).run(question)
    meta = {
        "intent": result.intent,
        "tool_calls": result.tool_calls,
        "degraded": result.degraded,
    }
    if result.degraded:
        answer, sources = answer_classic(
            app, vs, bm25, reranker, provider, model, client, question
        )
        meta["fell_back_to_classic"] = True
        return answer, sources, meta
    srcs = _dedup_sources(
        [s for s in (result.sources or []) if isinstance(s, dict)]
    )
    return result.answer, srcs, meta


def parse_verdict(text):
    text = (text or "").strip()
    for mark in ("✅", "❌", "⚠️"):
        if mark in text:
            return mark
    low = text.lower()
    if any(w in low for w in ("正确", "correct", "pass")):
        return "✅"
    if any(w in low for w in ("错误", "wrong", "编造", "未找到", "缺失")):
        return "❌"
    return "⚠️"


def judge(model, client, question, answer):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": f"【问题】{question}\n\n【回答】{answer}"},
        ],
        temperature=0.0,
        max_tokens=120,
        stream=False,
    )
    text = resp.choices[0].message.content
    return parse_verdict(text), (text or "").strip().replace("\n", " ")[:200]


def run_one(ctx, item):
    app, vs, bm25, reranker, tools, path, provider, model = ctx
    client = make_client(provider)  # 每线程独立 client
    qid, question = item["id"], item["question"]
    t0 = time.time()
    meta = {}
    try:
        if path == "classic":
            answer, sources = answer_classic(
                app, vs, bm25, reranker, provider, model, client, question
            )
        else:
            answer, sources, meta = answer_agent(
                app, vs, bm25, reranker, tools, provider, model, client, question
            )
        verdict, reason = judge(model, client, question, answer)
    except Exception as e:
        answer, sources = f"[harness 异常] {type(e).__name__}: {e}", []
        verdict, reason = "❌", f"harness 异常: {e}"
    return {
        "id": qid,
        "faction": item["faction"],
        "question": question,
        "verdict": verdict,
        "judge_reason": reason,
        "time": f"{time.time() - t0:.1f}s",
        "meta": meta,
        "sources": sources,
        "answer": answer,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", choices=["classic", "agent"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--provider", default="DeepSeek")
    args = ap.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("缺少 DEEPSEEK_API_KEY 环境变量")

    _, model = _PROVIDERS[args.provider]
    questions = load_questions(args.limit)
    print(f"[qa_bench] path={args.path} n={len(questions)} workers={args.workers} model={model}")

    app, vs, bm25, reranker, tools = init_resources()
    ctx = (app, vs, bm25, reranker, tools, args.path, args.provider, model)

    results, done = [], 0
    lock = Lock()
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, ctx, q): q for q in questions}
        for fut in as_completed(futs):
            r = fut.result()
            with lock:
                results.append(r)
                done += 1
                print(f"[{done}/{len(questions)}] #{r['id']:>3} {r['verdict']} "
                      f"({r['faction']}) {r['question'][:28]}", flush=True)

    results.sort(key=lambda x: x["id"])
    counts = {"correct": 0, "partial": 0, "wrong": 0, "total": len(results)}
    for r in results:
        counts["correct" if r["verdict"] == "✅" else
               "partial" if r["verdict"] == "⚠️" else "wrong"] += 1

    degraded_n = sum(1 for r in results if r.get("meta", {}).get("degraded"))
    summary = {
        "path": args.path,
        "provider": args.provider,
        "results": counts,
        "accuracy": round(counts["correct"] / max(counts["total"], 1) * 100, 1),
        "degraded_count": degraded_n,
        "wall_time": f"{time.time() - t_start:.1f}s",
    }
    out = {"summary": summary, "details": results}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 汇总 =====")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"写入 {args.out}")


if __name__ == "__main__":
    main()
