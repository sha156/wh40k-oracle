"""S2 中英跨语检索实测 harness（11 版迁移收尾）。

目的：验证中文规则查询能否命中 11 版英文核心规则原文（layer=rules/edition=11）。
对每条查询对比两路：
  A. 纯向量跨语召回（similarity_search，无 BM25、无规则层保底）——看 bge-m3 裸跨语能力；
  B. 生产混合检索（hybrid_retrieve：查询扩展 + FAISS + BM25 + RRF + 规则层保底）。
产出：每查询 top-8 的 book/edition/layer/page + 三项聚合指标，写入 JSON 供报告引用。
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

REPO = Path(r"D:\Project\py\RAG")
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import app  # noqa: E402  （导入即设 HF 镜像；__main__ 守卫下不跑 UI）
from langchain_community.retrievers import BM25Retriever  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from hf_embeddings_compat import build_huggingface_embeddings  # noqa: E402

# 11 版重点查询集（覆盖 S6 大改 + 核心机制；纯中文，模拟真实用户提问）
QUERIES = [
    ("掩体效果", "躲在掩体里对射击有什么好处？"),
    ("隐蔽Stealth", "隐蔽这个技能是什么效果？"),
    ("灵能攻击", "灵能武器可以无视命中修正吗？"),
    ("特殊保护", "特殊保护和护甲保存怎么一起判定？"),
    ("曲射间接火力", "曲射武器怎么判定命中？"),
    ("忽视掩体", "忽视掩体的武器有什么用？"),
    ("近战先攻顺序", "近战阶段谁先攻击，怎么决定顺序？"),
    ("接战范围", "接战范围是多少英寸？"),
    ("深入打击距离", "深入打击的单位要部署在离敌人多远？"),
    ("战略预备队", "战略预备队最晚第几回合必须上场？"),
    ("飞行翱翔", "飞行单位移动有什么特殊规则？"),
    ("速射", "速射武器在半射程内有什么加成？"),
    ("致命一击", "致命一击这个技能是什么效果？"),
    ("暴击命中", "命中骰掷出6是什么结果？"),
    ("战斗休克", "战斗休克测试什么时候进行？"),
    ("无痛", "无痛技能怎么减少伤害？"),
    ("冲锋先攻", "冲锋的单位在近战里能先打吗？"),
    ("坚守射击", "坚守射击（守望）怎么命中？"),
    ("冲锋距离", "冲锋要掷几个骰子决定距离？"),
    ("致命伤", "致命伤会被护甲挡住吗？"),
    ("攻击序列", "一次攻击要经过哪些步骤？"),
    ("目标控制OC", "目标控制值OC是用来做什么的？"),
    ("危险武器", "危险武器开火后会怎样？"),
    ("命中修正上限", "命中骰的修正有上限吗？"),
    ("毁灭打击", "毁灭打击（devastating wounds）暴击后怎么结算？"),
]


def load():
    emb = build_huggingface_embeddings(
        model_name=app.resolve_embed_model(),
        cache_folder=app.EMBED_MODEL_CACHE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 16},
    )
    vs = FAISS.load_local(str(app.VECTOR_STORE_PATH), emb,
                          allow_dangerous_deserialization=True)
    all_docs = list(vs.docstore._dict.values())
    bm25 = BM25Retriever.from_documents(
        all_docs, k=app.BM25_TOP_K, preprocess_func=app.chinese_tokenize)
    return vs, bm25


def brief(meta):
    ed = meta.get("edition")
    ly = meta.get("layer")
    if not ed or not ly:
        fb = app.classify_book(meta.get("book", ""), app._CORPUS_MANIFEST)
        ed = ed or fb["edition"]
        ly = ly or fb["layer"]
    return {"book": meta.get("book", "?"), "edition": ed, "layer": ly,
            "page": meta.get("page", "?")}


def run():
    vs, bm25 = load()
    rows = []
    for tag, q in QUERIES:
        # A. 纯向量跨语（无扩展、无 BM25、无保底）
        raw = vs.similarity_search(q, k=8)
        raw_top = [brief(d.metadata) for d in raw]
        # B. 生产混合检索（含扩展/BM25/RRF/规则层保底）
        prod = app.hybrid_retrieve(q, vs, bm25, None)
        prod_top = [{"book": r["book"], "edition": r["edition"],
                     "layer": r["layer"], "page": r["page"]} for r in prod]
        rows.append({"tag": tag, "query": q, "raw": raw_top, "prod": prod_top})
        # 逐条打印
        raw_rules = sum(1 for r in raw_top if r["layer"] == "rules")
        prod_rules = sum(1 for r in prod_top if r["layer"] == "rules")
        raw_e11 = sum(1 for r in raw_top if str(r["edition"]) == "11")
        prod_e11 = sum(1 for r in prod_top if str(r["edition"]) == "11")
        print(f"[{tag}] 纯向量: rules={raw_rules} e11={raw_e11} 顶1={raw_top[0]['book'][:16]}"
              f"({raw_top[0]['edition']}/{raw_top[0]['layer']}) | "
              f"生产: rules={prod_rules} e11={prod_e11} 顶1={prod_top[0]['book'][:16]}"
              f"({prod_top[0]['edition']}/{prod_top[0]['layer']})")

    # 聚合
    def agg(key):
        n = len(rows)
        any_rules = sum(1 for r in rows if any(x["layer"] == "rules" for x in r[key]))
        any_e11 = sum(1 for r in rows if any(str(x["edition"]) == "11" for x in r[key]))
        top1_e11 = sum(1 for r in rows if str(r[key][0]["edition"]) == "11")
        top1_rules = sum(1 for r in rows if r[key][0]["layer"] == "rules")
        return {"n": n, "any_rules": any_rules, "any_e11": any_e11,
                "top1_e11": top1_e11, "top1_rules": top1_rules}

    summary = {"raw": agg("raw"), "prod": agg("prod")}
    print("\n=== 聚合 ===")
    for k, s in summary.items():
        print(f"{k}: 命中rules层 {s['any_rules']}/{s['n']} | 含11版 {s['any_e11']}/{s['n']} | "
              f"top1是11版 {s['top1_e11']}/{s['n']} | top1是rules {s['top1_rules']}/{s['n']}")

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("s2_probe_result.json")
    out.write_text(json.dumps({"rows": rows, "summary": summary},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果写入 {out}")


if __name__ == "__main__":
    run()
