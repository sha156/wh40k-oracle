"""scripts/qa_bench.py — QA 回归 harness。

对清洗后的 96 题（题面 + 权威 gold answer 来自 qa_gold.json）跑指定路径，
用 LLM judge 判 ✅/⚠️/❌，输出聚合分与逐题结果。

题集清洗（2026-07-09）：原 qa_100 中删 4 道假题（米卡多主战坦克/探矿者/赫尔松铁御/
铁皮大壮，实体在权威库不存在）+ 改 2 道（瘟疫机蜂、泰伦武士，纠正乱码/翻译名）。
每题补 gold answer（stat/weapon 来自 db/wh40k.sqlite；ability/rule 来自黑图书馆
datasheet 与 data_refined 核心规则），judge 由「凭感觉 intrinsic」升级为「对标 gold」：
数值/规则与 gold 不符即 ❌，不再被自信的幻觉答案蒙混。仅 Q63 无干净源，回落 intrinsic。

路径：
  classic = 现有混合检索链（app.hybrid_retrieve → LLM 合成），基线复现，用于校准 judge
  agent   = L5 Agent 编排层（agent.loop），完全镜像 app.py 的 Agent 模式：
            先跑 AgentLoop；若降级则转经典链合成（保证不劣于经典）

判分说明：题有 gold answer 时用 judge_gold 对标权威标准答案打分（数值/规则错即 ❌）；
无 gold 的题（仅 Q63）回落 intrinsic judge。同一 judge 逻辑同判两条路径 → 对比公平。

用法（需 Clash 代理 + DEEPSEEK_API_KEY）：
  export HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897
  DEEPSEEK_API_KEY=sk-xxx .venv/Scripts/python.exe scripts/qa_bench.py \
      --path agent --out qa_agent_results.json [--limit N] [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import warnings

warnings.filterwarnings("ignore")

QA_SOURCE = REPO_ROOT / "qa_gold.json"

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


# ── 分层评测（--layered）：把单一总分拆成检索层 / 生成层两列 ──────────────
# 检索判：只看「检索到的段落里有没有足够信息回答本题」——不看最终答案。
_RETRIEVAL_JUDGE_SYSTEM = """你是战锤40K规则问答系统的检索质检员。给定【问题】与
系统检索到的【段落】（原始规则书片段）。只判断这些段落本身是否含有回答问题所需的信息，
完全不要看、也不要猜系统最终会怎么回答：
✅ = 段落里明确含有回答该问题所需的关键信息（具体数值/规则条文）；
⚠️ = 段落沾边但信息不全，只能回答一部分；
❌ = 段落与问题无关，或未检索到任何段落。
输出格式：第一行只写 ✅ 或 ⚠️ 或 ❌，第二行一句话理由。"""

# 生成判：在「段落已给定」的前提下，看答案是否忠实、正确、完整、标注来源。
_GENERATION_JUDGE_SYSTEM = """你是战锤40K规则问答系统的生成质检员。给定【问题】、系统
检索到的【段落】、以及系统据此生成的【回答】。假定段落就是可用的全部依据，判断回答的质量：
✅ = 回答忠实于段落、正确且完整地回答了问题，并标注了《书名》页码来源；
⚠️ = 回答部分正确 / 信息不全 / 未直接命中 / 来源模糊 / 有明显冗余但主旨对；
❌ = 回答与段落矛盾（编造/幻觉）、答错、答非所问，或段落里明明有却说「档案缺失」。
输出格式：第一行只写 ✅ 或 ⚠️ 或 ❌，第二行一句话理由。"""

_MAX_PASSAGE_CHARS = 1200  # 每段落喂给 judge 的截断上限，控 token


def _format_passages_for_judge(passages):
    if not passages:
        return "（未检索到任何段落）"
    lines = []
    for i, p in enumerate(passages, 1):
        book = p.get("book", "未知")
        page = p.get("page", "?")
        text = (p.get("text") or p.get("content") or "").strip()
        lines.append(f"[段落{i} 《{book}》 p{page}] {text[:_MAX_PASSAGE_CHARS]}")
    return "\n\n".join(lines)


def judge_retrieval(model, client, question, passages):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _RETRIEVAL_JUDGE_SYSTEM},
            {"role": "user", "content": f"【问题】{question}\n\n【段落】\n"
                                        f"{_format_passages_for_judge(passages)}"},
        ],
        temperature=0.0, max_tokens=120, stream=False,
    )
    text = resp.choices[0].message.content
    return parse_verdict(text), (text or "").strip().replace("\n", " ")[:200]


def judge_generation(model, client, question, passages, answer, gold=None):
    gold_line = f"【标准答案】{gold}\n\n" if gold else ""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _GENERATION_JUDGE_SYSTEM +
             ("\n若提供【标准答案】，以其为准判定数值/规则是否正确。" if gold else "")},
            {"role": "user", "content": f"【问题】{question}\n\n{gold_line}【段落】\n"
                                        f"{_format_passages_for_judge(passages)}\n\n"
                                        f"【回答】{answer}"},
        ],
        temperature=0.0, max_tokens=120, stream=False,
    )
    text = resp.choices[0].message.content
    return parse_verdict(text), (text or "").strip().replace("\n", " ")[:200]


def classify_stage(retrieval_verdict, generation_verdict):
    """把 (检索判, 生成判) 归到瓶颈桶，定位『伤害死在哪一步』。

    生成对了就算成功；否则按检索层判定归因：检索没捞到→怪检索，捞到了还答错→怪生成。
    """
    if generation_verdict == "✅":
        return "ok"
    if retrieval_verdict == "❌":
        return "retrieval_miss"
    if retrieval_verdict == "✅":
        return "generation_error"
    return "partial_retrieval"


def summarize_layered(results):
    """把逐题的两轴判分聚合成两列报告 + 瓶颈桶。纯函数，可单测。"""
    total = len(results)
    retr = {"hit": 0, "partial": 0, "miss": 0}
    gen = {"correct": 0, "partial": 0, "wrong": 0}
    stages = {"ok": 0, "generation_error": 0, "retrieval_miss": 0,
              "partial_retrieval": 0}
    gen_ok_given_retr_hit = 0
    retr_hit_total = 0
    for r in results:
        rv, gv = r["retrieval_verdict"], r["generation_verdict"]
        retr["hit" if rv == "✅" else "partial" if rv == "⚠️" else "miss"] += 1
        gen["correct" if gv == "✅" else "partial" if gv == "⚠️" else "wrong"] += 1
        stages[classify_stage(rv, gv)] += 1
        if rv == "✅":
            retr_hit_total += 1
            if gv == "✅":
                gen_ok_given_retr_hit += 1
    pct = lambda n, d: round(n / d * 100, 1) if d else None  # noqa: E731
    return {
        "total": total,
        "retrieval": retr,
        "generation": gen,
        "stages": stages,
        "retrieval_accuracy": pct(retr["hit"], total),
        "generation_accuracy": pct(gen["correct"], total),
        "conditional_gen_accuracy": pct(gen_ok_given_retr_hit, retr_hit_total),
    }


def load_questions(limit=None):
    data = json.loads(QA_SOURCE.read_text(encoding="utf-8"))
    items = [
        {"id": d["id"], "faction": d["faction"], "question": d["question"],
         "gold": d.get("gold"), "gold_type": d.get("gold_type")}
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


def retrieve_and_answer_classic(app, vs, bm25, reranker, model, client, question):
    """经典链，但返回带原文的完整段落（供检索层 judge），而非仅 book/page。"""
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
        temperature=0.1, max_tokens=1600, stream=False,
    )
    return resp.choices[0].message.content, passages


def run_one_layered(ctx, item):
    """经典链分层评测：检索判 + 生成判两轴，各一次 judge 调用。"""
    app, vs, bm25, reranker, _tools, _path, provider, model = ctx
    client = make_client(provider)
    qid, question = item["id"], item["question"]
    t0 = time.time()
    try:
        answer, passages = retrieve_and_answer_classic(
            app, vs, bm25, reranker, model, client, question
        )
        rv, r_reason = judge_retrieval(model, client, question, passages)
        gv, g_reason = judge_generation(
            model, client, question, passages, answer, gold=item.get("gold")
        )
    except Exception as e:
        answer, passages = f"[harness 异常] {type(e).__name__}: {e}", []
        rv, r_reason = "❌", f"harness 异常: {e}"
        gv, g_reason = "❌", f"harness 异常: {e}"
    return {
        "id": qid,
        "faction": item["faction"],
        "question": question,
        "retrieval_verdict": rv,
        "retrieval_reason": r_reason,
        "generation_verdict": gv,
        "generation_reason": g_reason,
        "stage": classify_stage(rv, gv),
        "time": f"{time.time() - t0:.1f}s",
        "sources": _dedup_sources(passages),
        "answer": answer,
    }


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


# ── 对标 gold 的判分（qa_gold.json 提供权威标准答案）─────────────────────
# 用于 ability/rule 类（自由文本要点）判分；stat/weapon 类走下方两段式机械判分。
_GOLD_JUDGE_SYSTEM = """你是战锤40K规则问答系统的答案质检员。给定【问题】、从权威规则库
提取的【标准答案】、以及系统【回答】。以标准答案为准判定系统回答：
✅ = 系统回答覆盖了标准答案的关键事实/要点，且直接回答了问题；
⚠️ = 部分正确（问了多个要点只答对一部分 / 主旨对但漏项 / 有小误但方向对）；
❌ = 与标准答案矛盾（事实或规则错误）、答非所问、或声明「未找到/档案缺失」。

判分铁律（务必遵守，避免冤判）：
1. 只看事实是否与标准答案一致，**不要求措辞、单位符号、来源格式一致**（M=10" 与「10寸」等价）。
2. **回答比标准答案更详细、多给了没问到的信息，一律不扣分**——只要被问的要点答对就是 ✅。
3. 遗漏被问到的要点时判 ⚠️（漏项），**不要因为漏项就判 ❌**。
4. 只有当回答与标准答案的关键事实**矛盾**、或完全答非所问、或声明档案缺失，才判 ❌。

示例：
- 标准答案「T=8。光学折射：可将那次攻击的D变为0」，回答「鬼覆战斗服T为8；光学折射能在对手造伤后把该次攻击伤害D变为0」→ ✅（要点齐全，多出的细节不扣分）。
- 标准答案含 A、B 两个要点，回答只答对 A、没提 B → ⚠️（漏项，不判 ❌）。
- 标准答案「W=16」，回答「W为12」→ ❌（与标准答案矛盾）。
- 回答「档案缺失，建议查阅规则书」→ ❌。

输出格式：第一行只写 ✅ 或 ⚠️ 或 ❌，第二行一句话理由。"""


def judge_gold(model, client, question, gold, answer):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _GOLD_JUDGE_SYSTEM},
            {"role": "user", "content": f"【问题】{question}\n\n【标准答案】{gold}\n\n"
                                        f"【回答】{answer}"},
        ],
        temperature=0.0, max_tokens=120, stream=False,
    )
    text = resp.choices[0].message.content
    return parse_verdict(text), (text or "").strip().replace("\n", " ")[:200]


# ── 两段式机械判分（stat/weapon 类：LLM 只抽数值，程序做比对）─────────────
# 动机：属性/武器数值题的 gold 是确定值，靠 LLM judge「凭感觉」比对会产生随机噪声与
# 系统性冤判（多报没问的字段被判❌、漏项判❌而非⚠️）。改为：① 从 gold 机械解析出被问
# 字段的标准值；② LLM 仅从回答中「抽取」它给出的对应数值（低判断力任务）；③ 程序按
# 归一化 token 逐字段比对，确定性给分。多武器/多模型（同字段出现多次）无法机械对齐，
# 返回 None 交回 LLM judge。

# 单个 datasheet 的属性/武器字段代码（多字符在前，避免 SV 被拆成 S+V）。
_GOLD_KV = re.compile(r"(WS|BS|SV|LD|OC|AP|M|T|W|S|D)\s*=\s*([^\s；;，,。]+)")
_STAT_KEYS = ("WS", "BS", "SV", "LD", "OC", "AP", "M", "T", "W", "S", "D")

_FIELD_LABEL = {
    "M": "M(移动)", "T": "T(韧性)", "SV": "SV(护甲保护)", "W": "W(生命)",
    "LD": "LD(领导)", "OC": "OC(目标控制)", "WS": "WS(近战技)", "BS": "BS(弹道技)",
    "S": "S(力量)", "AP": "AP(穿甲)", "D": "D(伤害)",
    "INV": "特殊保护(不可侵犯/invuln 保护值)",
}

_ASK_INV_WORDS = ("特殊保护", "不可侵犯", "无敌保护", "异能力场", "invuln", "invulnerable")
_ASK_SYNONYMS = {
    "移动": "M", "韧性": "T", "护甲": "SV", "救护": "SV", "生命": "W", "伤口": "W",
    "领导": "LD", "目标控制": "OC", "近战技": "WS", "弹道技": "BS", "力量": "S",
    "强度": "S", "穿甲": "AP", "穿透": "AP", "伤害": "D",
}


def _stat_token(value):
    """把一个属性/武器值归一化成可比对的 token。

    去掉移动单位（寸/"）、多余文字与标点，抽出首个规范数值 token；把连续 '+' 折成一个
    （特殊保护 5++ 与 5+ 等价）。抽不出返回 None（表示该值不是规范数值，交 LLM 判）。
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    for junk in ('"', "”", "“", "″", "′", "'", "寸", "吋", "inch", "英寸"):
        s = s.replace(junk, "")
    # 各种破折号统一成 ASCII，便于把「无（此项）」的多种写法归一
    for dash in ("—", "–", "－", "―"):
        s = s.replace(dash, "-")
    m = re.search(r"\d*d\d+(?:\+\d+)?|-?\d+\+*|无|-", s)
    if not m:
        return None
    tok = re.sub(r"\++", "+", m.group(0))
    # 裸破折号 = 该项无（如无特殊保护），与「无」等价——统一成「无」避免把
    # 「特殊保护：-」冤判为与标准「无」不符（#29 瘟疫战士）。
    return "无" if tok == "-" else tok


def parse_gold_fields(gold):
    """从 gold 文本解析出 {字段代码: 原始值}。多武器/多模型或含无法解析的值时返回 None。"""
    if not gold:
        return None
    fields = {}
    inv = re.search(r"特殊保护\s*=\s*([^\s；;，,。]+)", gold)
    if inv:
        fields["INV"] = inv.group(1)
    for key, val in _GOLD_KV.findall(gold):
        if key in fields:
            return None  # 同字段重复 → 多武器/多模型，机械对齐不了
        fields[key] = val
    if not fields:
        return None
    if any(_stat_token(v) is None for v in fields.values()):
        return None  # gold 里混入长段文字，交 LLM
    return fields


def asked_fields(question):
    """从问题文本推断被问了哪些字段（拉丁代码 + 中文同义词 + 特殊保护）。"""
    q = question or ""
    found = set()
    if any(w in q for w in _ASK_INV_WORDS):
        found.add("INV")
    for run in re.findall(r"[A-Za-z]+", q):
        up = run.upper()
        if up in _STAT_KEYS:
            found.add(up)
    for syn, field in _ASK_SYNONYMS.items():
        if syn in q:
            found.add(field)
    return found


def _aligned_tokens(value):
    """返回 (是否多值 list, 逐下标归一化 token 列表)。

    与 _answer_tokens 不同：**不丢弃**解析不出的元素（保留 None 占位），
    维持「第 i 个元素属于第 i 把武器/子单位」的下标对齐——记录匹配依赖它。
    """
    if isinstance(value, list):
        return True, [_stat_token(v) for v in value]
    return False, [_stat_token(value)]


def decide_mechanical(gold_fields, required, extracted):
    """纯函数：按归一化 token 逐字段比对，给出 (verdict, reason)。

    每个被问字段，extracted 里可以是单值或多值（回答覆盖多个子单位/多把武器）；
    任一答案值与标准值一致即算该字段命中——避免机械抽取器在多实体答案里
    抽错行，把答对的题冤判为错（#62 卡迪安重武器班、#95 噪音战士）。

    评审 H18 修复——记录匹配：被问字段含多值（list）时，各 list 按下标对齐成
    「记录」（抽取 prompt 已约定各字段数组按武器/子单位顺序对齐），✅ 额外要求
    **存在某个下标 i 使所有被问字段在记录 i 上同时命中**。堵住跨字段拼凑假阳性：
    gold(S=5,AP=-1) vs 答案两把武器 (S5,AP-2)/(S10,AP-1)——S、AP 各自都出现过
    标准值，但没有一把武器同时满足，不得判 ✅。标量字段视为对所有记录生效；
    list 下标越界视为该记录缺该字段。全标量情况保持原行为。

    - 任一被问字段答了值但无一与标准一致 → ❌
    - 被问字段全部命中且存在同时满足的记录 → ✅
    - 各字段独立命中但无任何记录同时满足 → ⚠️（跨字段拼凑，存疑不给 ✅）
    - 部分命中、其余漏答（无矛盾）→ ⚠️
    - 被问字段全部漏答 → ❌（答非所问）
    """
    wrong, matched, missing = [], [], []
    per_field = {}  # f -> (is_list, aligned_tokens, gold_tok)
    for f in required:
        gold_tok = _stat_token(gold_fields.get(f))
        is_list, aligned = _aligned_tokens(extracted.get(f))
        per_field[f] = (is_list, aligned, gold_tok)
        ans_tokens = [t for t in aligned if t is not None]
        if not ans_tokens:
            missing.append(f)
        elif gold_tok in ans_tokens:
            matched.append(f)
        else:
            wrong.append((f, extracted.get(f), gold_fields.get(f)))
    if wrong:
        detail = "；".join(f"{f} 答「{a}」≠标准「{g}」" for f, a, g in wrong)
        return "❌", f"数值不符：{detail}"
    if matched and not missing:
        list_fields = [f for f in required if per_field[f][0]]
        if list_fields:
            n_rec = max(len(per_field[f][1]) for f in list_fields)

            def _hit_at(f, i):
                is_list, aligned, gold_tok = per_field[f]
                if is_list:
                    return i < len(aligned) and aligned[i] == gold_tok
                return aligned[0] == gold_tok  # 标量对所有记录生效

            if not any(all(_hit_at(f, i) for f in required) for i in range(n_rec)):
                return "⚠️", ("各被问字段虽各自出现过标准值，但没有任何一条武器/"
                              "子单位记录同时满足全部字段（疑似跨字段拼凑，存疑不判对）")
        return "✅", f"被问字段全部正确：{'/'.join(matched)}"
    if matched and missing:
        return "⚠️", f"正确：{'/'.join(matched)}；漏答：{'/'.join(missing)}"
    return "❌", f"未回答被问字段：{'/'.join(missing)}"


def _coerce_value_list(v):
    """把抽取结果里单个字段的值规整成列表：None→[]、标量→[标量]、列表原样。

    列表内的 null 占位元素**保留**（不再剔除）：抽取 prompt 约定用 null 占位
    维持多武器下标对齐，decide_mechanical 的记录匹配（H18）依赖这个对齐。
    """
    if v is None:
        return []
    if isinstance(v, list):
        return list(v)
    return [v]


def extract_answer_fields(model, client, question, answer, fields):
    """LLM 仅做抽取（不判断）：从回答中抽出各字段的**全部**原文数值，缺失返回空数组。

    回答可能覆盖多个子单位/多把武器（同一字段出现多个不同数值），因此每个字段抽成数组。
    对齐约定（评审 H18，记录匹配的前提）：原 prompt 只要求「抽出全部数值」未约定顺序，
    现明文要求各字段数组按武器/子单位出现顺序对齐（第 i 个元素属于第 i 把武器，
    缺失用 null 占位），decide_mechanical 才能按下标把各字段拼回同一条记录整体比对。
    """
    labels = "、".join(f"{f}={_FIELD_LABEL.get(f, f)}" for f in fields)
    sys_prompt = (
        "你是数据抽取器，只做抽取不做判断。从【回答】中抽取它明确给出的下列字段数值，"
        "字段清单（代码=含义）：" + labels + "。\n"
        "回答可能涉及多个子单位或多把武器，同一字段可能出现多个不同数值。\n"
        "以 JSON 对象返回，键为字段代码，值为该字段在回答中出现的**所有**原文数值组成的数组"
        '（如 {"S": ["10", "5"], "AP": ["-2", "-1"]}，元素形如 "10寸"、"2+"、"-4"、"D6"、"无"）；'
        "若回答没有明确给出某字段，该键返回空数组 []。不要推断或补全，只照抄回答里的数字。\n"
        "【对齐要求】回答涉及多把武器/多个子单位时，各字段数组必须按武器/子单位在回答中"
        "出现的顺序对齐：所有字段数组的第 i 个元素都属于同一把（第 i 把）武器/子单位；"
        "某把武器没给出某字段时，该位置用 null 占位，保持各数组下标一一对应。"
    )
    user = f"【问题】{question}\n\n【回答】{answer}\n\n只输出 JSON 对象。"
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": sys_prompt},
                  {"role": "user", "content": user}],
        temperature=0.0, max_tokens=300, stream=False,
    )
    try:
        resp = client.chat.completions.create(
            response_format={"type": "json_object"}, **kwargs
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content or ""
    try:
        obj = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        obj = json.loads(m.group(0)) if m else {}
    return {f: _coerce_value_list(obj.get(f) if isinstance(obj, dict) else None)
            for f in fields}


def judge_gold_mechanical(model, client, question, gold, answer):
    """stat/weapon 类两段式判分。返回 (verdict, reason)；无法机械判分时返回 None。"""
    gold_fields = parse_gold_fields(gold)
    if not gold_fields:
        return None
    asked = asked_fields(question)
    required = [f for f in gold_fields if f in asked] or list(gold_fields)
    extracted = extract_answer_fields(model, client, question, answer, required)
    return decide_mechanical(gold_fields, required, extracted)


def run_one(ctx, item):
    app, vs, bm25, reranker, tools, path, provider, model = ctx
    client = make_client(provider)  # 每线程独立 client
    qid, question = item["id"], item["question"]
    t0 = time.time()
    meta = {}
    judge_method = None
    try:
        if path == "classic":
            answer, sources = answer_classic(
                app, vs, bm25, reranker, provider, model, client, question
            )
        else:
            answer, sources, meta = answer_agent(
                app, vs, bm25, reranker, tools, provider, model, client, question
            )
        gold = item.get("gold")
        gold_type = item.get("gold_type")
        verdict = reason = None
        if gold:
            # stat/weapon：先尝试两段式机械判分（确定性、消除 judge 随机噪声与冤判）
            if gold_type in ("stat", "weapon"):
                mech = judge_gold_mechanical(model, client, question, gold, answer)
                if mech is not None:
                    verdict, reason = mech
                    judge_method = "mechanical"
            # ability/rule 或机械判分不适用 → LLM 对标 gold（含 few-shot 防冤判）
            if verdict is None:
                verdict, reason = judge_gold(model, client, question, gold, answer)
                judge_method = "llm_gold"
        else:
            verdict, reason = judge(model, client, question, answer)
            judge_method = "intrinsic"
    except Exception as e:
        answer, sources = f"[harness 异常] {type(e).__name__}: {e}", []
        verdict, reason = "❌", f"harness 异常: {e}"
        judge_method = "error"
    return {
        "id": qid,
        "faction": item["faction"],
        "question": question,
        "gold": item.get("gold"),
        "gold_type": item.get("gold_type"),
        "judged_against_gold": bool(item.get("gold")),
        "judge_method": judge_method,
        "verdict": verdict,
        "judge_reason": reason,
        "time": f"{time.time() - t0:.1f}s",
        "meta": meta,
        "sources": sources,
        "answer": answer,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", choices=["classic", "agent"], default="classic")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--provider", default="DeepSeek")
    ap.add_argument("--layered", action="store_true",
                    help="分层评测：检索层/生成层两列（仅经典链）")
    args = ap.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("缺少 DEEPSEEK_API_KEY 环境变量")

    if args.layered and args.path != "classic":
        raise SystemExit("--layered 目前仅支持 --path classic（agent 路径检索散在工具调用里，待扩展）")

    _, model = _PROVIDERS[args.provider]
    questions = load_questions(args.limit)
    mode = "layered" if args.layered else args.path
    print(f"[qa_bench] mode={mode} n={len(questions)} workers={args.workers} model={model}")

    app, vs, bm25, reranker, tools = init_resources()
    ctx = (app, vs, bm25, reranker, tools, args.path, args.provider, model)

    worker = run_one_layered if args.layered else run_one
    results, done = [], 0
    lock = Lock()
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(worker, ctx, q): q for q in questions}
        for fut in as_completed(futs):
            r = fut.result()
            with lock:
                results.append(r)
                done += 1
                if args.layered:
                    print(f"[{done}/{len(questions)}] #{r['id']:>3} "
                          f"检索{r['retrieval_verdict']} 生成{r['generation_verdict']} "
                          f"[{r['stage']}] ({r['faction']}) {r['question'][:24]}", flush=True)
                else:
                    print(f"[{done}/{len(questions)}] #{r['id']:>3} {r['verdict']} "
                          f"({r['faction']}) {r['question'][:28]}", flush=True)

    results.sort(key=lambda x: x["id"])

    if args.layered:
        summary = {"path": "classic", "mode": "layered", "provider": args.provider,
                   **summarize_layered(results),
                   "wall_time": f"{time.time() - t_start:.1f}s"}
    else:
        counts = {"correct": 0, "partial": 0, "wrong": 0, "total": len(results)}
        for r in results:
            counts["correct" if r["verdict"] == "✅" else
                   "partial" if r["verdict"] == "⚠️" else "wrong"] += 1
        degraded_n = sum(1 for r in results if r.get("meta", {}).get("degraded"))
        summary = {
            "path": args.path, "provider": args.provider, "results": counts,
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
