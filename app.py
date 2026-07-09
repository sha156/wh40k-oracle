"""
app.py — 战锤40K规则书 RAG 问答系统
=====================================
架构：
  检索层：FAISS 向量检索 + BM25 关键词检索（jieba 中文分词）→ RRF 融合
          查询扩展：常见社区译名 → 库内规则书译名（UNIT_ALIASES）
  重排层：默认关闭（实测 ms-marco 系列对中文重排差于 RRF 顺序，见 USE_RERANKER 注释）
  生成层：DeepSeek / ZhipuAI（可在侧边栏切换）
  界面层：Streamlit 聊天 UI + 元数据过滤 + 来源引用

运行：
  .\.venv\Scripts\streamlit.exe run app.py
"""

from __future__ import annotations

import os
import time
import json
import sys
from pathlib import Path

# ── 镜像设置（必须在 HuggingFace 相关导入前）──
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import jieba
    import streamlit as st
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from flashrank import Ranker, RerankRequest
    from hf_embeddings_compat import build_huggingface_embeddings
except ModuleNotFoundError as exc:
    missing_pkg = exc.name or "required package"
    raise ModuleNotFoundError(
        f"Current Python environment is missing `{missing_pkg}`: {sys.executable}\n"
        "Start Streamlit with the project virtualenv instead:\n"
        r"  .\.venv\Scripts\python.exe -m streamlit run app.py"
    ) from exc

# ══════════════════════════════════════════════
#  全局配置
# ══════════════════════════════════════════════
VECTOR_STORE_PATH = Path("local_vector_store")
DATA_DIR          = Path("data")
EMBED_MODEL_NAME  = "BAAI/bge-m3"
EMBED_MODEL_CACHE = "./opt"


def resolve_embed_model() -> str:
    """优先返回本地完整快照的绝对路径，避免 sentence-transformers 联网核对模型。

    代理不稳时（Clash 抽风），HF 会对 hf-mirror 发 HEAD 请求核对模型并重试到超时，
    导致嵌入初始化失败。模型已缓存时直接传本地快照目录（含 modules.json 的完整 ST 模型）
    即走离线加载；找不到本地快照才回退到线上名（首次下载）。
    """
    snapshots = Path(EMBED_MODEL_CACHE) / "models--BAAI--bge-m3" / "snapshots"
    if snapshots.is_dir():
        for snap in sorted(snapshots.iterdir()):
            if (snap / "modules.json").exists():
                return str(snap.resolve())
    return EMBED_MODEL_NAME
RERANKER_MODEL    = "ms-marco-MiniLM-L-12-v2"   # FlashRank 本地模型名
# 实测（2026-07-04，16 个失败案例基准）：ms-marco 系列（含 MultiBERT 多语言版）
# 对中文查询的重排效果差于 RRF 融合顺序（命中@8：RRF 13/14 vs MultiBERT 12/14），
# 且旧代码调用 reranker.rank() 在 flashrank 0.2.x 下从未生效，77% 基线即纯 RRF。
# 故默认关闭；换用真正的中文重排模型（如 bge-reranker）时再开。
USE_RERANKER      = False

# 检索参数
FAISS_TOP_K   = 30   # 向量召回数量
BM25_TOP_K    = 15   # BM25 召回数量
RERANK_TOP_N  = 8    # Rerank 后保留数量


# ══════════════════════════════════════════════
#  中文分词（BM25 用）
# ══════════════════════════════════════════════
# BM25Retriever 默认按空格分词（text.split()），对中文完全无效——
# 整句变成一个 token，关键词永远匹配不上。必须用 jieba 分词。
_BM25_STOPWORDS = frozenset(
    "的 了 是 和 与 或 在 各 其 该 之 为 有 无 多少 什么 怎么 如何 哪些 请 吗 呢 "
    "、 。 ， ？ ！ ： ； （ ） 「 」 【 】 | - ? , . ( )".split()
)


def chinese_tokenize(text: str) -> list[str]:
    """jieba 搜索引擎模式分词 + 去停用词，用于 BM25 建索引和查询。"""
    return [
        tok for tok in jieba.cut_for_search(text)
        if tok.strip() and tok not in _BM25_STOPWORDS
    ]


# ══════════════════════════════════════════════
#  常见社区译名 → 库内规则书实际译名
# ══════════════════════════════════════════════
# 规则书来自不同汉化组，同一单位的译名与社区常用叫法不一致。
# 检索前把库内译名追加到查询里（扩展而非替换），BM25 和向量都受益。
# 各映射均已对照 PDF 原文确认（英文原名标注在注释中）。
# 说明：单位级社区俗名已统一进 sqlite aliases 表（DB_ALIASES，见下），classic 与 agent
# 共用同一份。这里只保留 **武器名/短语级检索提示**——它们不是单位、进不了 units 外键的
# aliases 表，但对查询召回有用。
UNIT_ALIASES = {
    "卡巴利特战士": "阴谋团武士",       # Kabalite Warriors（黑暗灵族）
    "卡巴利特":     "阴谋团",
    "激素虫":       "刀虫",             # Hormagaunt（泰伦虫族）
    "铁皮大壮":     "死死无畏机甲",     # Deff Dread（兽人）
    "重武器小队":   "重武器班",         # Heavy Weapons Squad（星界军）
    "卫兵小队":     "卡迪安突击队 步兵班",  # Shock Troops / Infantry Squad（星界军）
    "死亡翼":       "死翼",             # Deathwing（黑暗天使）
    "虫族武士":     "泰伦武士",         # Tyranid Warriors（泰伦虫族）
    "赫尔松铁御":   "赫卡顿陆行要塞",   # Hekaton Land Fortress（沃坦联盟）
    "弹射器":       "星镖枪 shuriken catapult",  # 星镖枪译名差异（艾达灵族，#48）
    "离子爆破者":   "Ion blaster",      # 沃坦远行者先锋武器（#83）
}

# 把双侧译名注册进 jieba，避免专有名词被切碎
for _k, _v in UNIT_ALIASES.items():
    jieba.add_word(_k)
    for _w in _v.split():
        jieba.add_word(_w)

# ══════════════════════════════════════════════
#  wiki/terms.json：P0 双语术语表 → 查询扩展
#  中文单位名命中时追加英文 canonical 名，让 BM25/向量能召回英文 Faction Pack 页
# ══════════════════════════════════════════════
from wiki_compile.terms import load_term_aliases

TERM_ALIASES = load_term_aliases(Path(__file__).parent / "wiki" / "terms.json")
for _zh in TERM_ALIASES:
    jieba.add_word(_zh)

# ══════════════════════════════════════════════
#  sqlite aliases 表（1633 条）→ 查询扩展
#  与 agent 的 EntityResolver 共用同一份别名库，消除「两套并行别名体系」漂移。
#  DB 缺失/无表时静默退化为空 dict，classic 仍可用 UNIT_ALIASES/TERM_ALIASES。
# ══════════════════════════════════════════════
from db_compile.aliases import load_alias_expansions

_DB_PATH = Path(__file__).parent / "db" / "wh40k.sqlite"
try:
    DB_ALIASES = load_alias_expansions(_DB_PATH)
except Exception:
    DB_ALIASES = {}
for _a in DB_ALIASES:
    jieba.add_word(_a)


def expand_query(query: str) -> str:
    """查询扩展：命中社区译名/术语表/别名库时，追加库内规范名与英文名（保留原词）。"""
    extras = [v for k, v in UNIT_ALIASES.items() if k in query]
    extras += [v for k, v in TERM_ALIASES.items() if k in query]
    extras += [v for k, v in DB_ALIASES.items() if k in query]
    if not extras:
        return query
    return query + "（" + "，".join(dict.fromkeys(extras)) + "）"


def resolve_flashrank_cache_dir(base_cache_dir: str, model_name: str) -> str:
    """
    兼容手工解压导致的嵌套目录：
      正常期望：opt/model_name/<model files>
      实际常见：opt/model_name/model_name/<model files>
    """
    base_dir = Path(base_cache_dir)
    model_dir = base_dir / model_name

    if not model_dir.exists():
        return str(base_dir)

    if list(model_dir.glob("*.onnx")):
        return str(base_dir)

    nested_model_dir = model_dir / model_name
    if list(nested_model_dir.glob("*.onnx")):
        return str(model_dir)

    for onnx_file in model_dir.rglob("*.onnx"):
        if onnx_file.parent.name == model_name:
            return str(onnx_file.parent.parent)

    return str(base_dir)

# ══════════════════════════════════════════════
#  Streamlit 页面配置（必须第一个 st 调用）
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="战锤40K 战术参谋部",
    layout="wide",
    page_icon="⚔️",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════
#  辅助函数：Reciprocal Rank Fusion (RRF)
# ══════════════════════════════════════════════
def reciprocal_rank_fusion(
    faiss_docs: list[Document],
    bm25_docs: list[Document],
    k: int = 60,
) -> list[Document]:
    """
    将 FAISS 和 BM25 的结果通过 RRF 算法融合。
    RRF 得分 = Σ 1/(k + rank_i)，k=60 是经验值。
    返回去重后按分数降序排列的 Document 列表。
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    def _doc_id(doc: Document) -> str:
        # 用 source + page + 内容前50字符 作为唯一键
        return f"{doc.metadata.get('source','')}_{doc.metadata.get('page',0)}_{doc.page_content[:50]}"

    for rank, doc in enumerate(faiss_docs, start=1):
        did = _doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        doc_map[did] = doc

    for rank, doc in enumerate(bm25_docs, start=1):
        did = _doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        doc_map[did] = doc

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[did] for did in sorted_ids]


# ══════════════════════════════════════════════
#  资源加载（缓存，只初始化一次）
# ══════════════════════════════════════════════
@st.cache_resource(show_spinner="⚙️ 正在启动机械神教数据核心...")
def load_resources():
    """加载嵌入模型、FAISS 向量库、Reranker。"""
    # 1. 嵌入模型
    embeddings = build_huggingface_embeddings(
        model_name=resolve_embed_model(),
        cache_folder=EMBED_MODEL_CACHE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 16},
    )

    # 2. 向量库
    vectorstore = None
    if (VECTOR_STORE_PATH / "index.faiss").exists():
        vectorstore = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    # 3. Reranker（FlashRank，纯本地，无需联网）
    reranker = None
    reranker_warning = None
    if not USE_RERANKER:
        return embeddings, vectorstore, None, None
    try:
        reranker_cache_dir = resolve_flashrank_cache_dir(
            EMBED_MODEL_CACHE,
            RERANKER_MODEL,
        )
        reranker = Ranker(
            model_name=RERANKER_MODEL,
            cache_dir=reranker_cache_dir,
        )
    except Exception as e:
        reranker_warning = f"FlashRank 加载失败，将退化为 RRF 排序：{e}"

    return embeddings, vectorstore, reranker, reranker_warning


# ══════════════════════════════════════════════
#  BM25 索引构建（从 FAISS docstore 提取 docs）
# ══════════════════════════════════════════════
@st.cache_resource(show_spinner="📚 构建关键词索引...")
def build_bm25(_vectorstore):
    """
    从 FAISS docstore 提取所有 Document，构建 BM25 索引。
    注意：_vectorstore 前加下划线告诉 Streamlit 不要对其做哈希。
    """
    if _vectorstore is None:
        return None
    try:
        # 从 FAISS docstore 提取所有文档
        all_docs = list(_vectorstore.docstore._dict.values())
        if not all_docs:
            return None
        retriever = BM25Retriever.from_documents(
            all_docs, k=BM25_TOP_K, preprocess_func=chinese_tokenize,
        )
        return retriever
    except Exception as e:
        st.warning(f"BM25 索引构建失败（将只使用向量检索）: {e}")
        return None


# ══════════════════════════════════════════════
#  混合检索核心函数
# ══════════════════════════════════════════════
def hybrid_retrieve(
    query: str,
    vectorstore,
    bm25_retriever,
    reranker,
    filter_books: list[str] | None = None,
) -> list[dict]:
    """
    混合检索流程：
      1. FAISS 向量召回（可带元数据过滤）
      2. BM25 关键词召回
      3. RRF 融合去重
      4. FlashRank 精排
    返回格式化的 passage 列表，每项含 text / book / source / page。
    """
    # ── 查询扩展（社区译名 → 库内译名）──
    query = expand_query(query)

    # ── FAISS 检索（支持按 book 过滤）──
    faiss_docs: list[Document] = []
    try:
        search_kwargs: dict = {"k": FAISS_TOP_K}
        if filter_books:
            # FAISS filter 用 lambda 过滤元数据
            search_kwargs["filter"] = {
                "book": {"$in": filter_books}
            }
        retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
        faiss_docs = retriever.invoke(query)
    except Exception as e:
        st.warning(f"FAISS 检索出错: {e}")

    # ── BM25 检索 ──
    bm25_docs: list[Document] = []
    if bm25_retriever:
        try:
            bm25_docs = bm25_retriever.invoke(query)
            # 若开启了过滤，手动过滤 BM25 结果
            if filter_books:
                bm25_docs = [
                    d for d in bm25_docs
                    if d.metadata.get("book") in filter_books
                ]
        except Exception as e:
            st.warning(f"BM25 检索出错: {e}")

    # ── RRF 融合 ──
    merged = reciprocal_rank_fusion(faiss_docs, bm25_docs)

    if not merged:
        return []

    # ── FlashRank 精排 ──
    passages = [
        {
            "id": str(i),
            "text": doc.page_content,
            "meta": doc.metadata,
        }
        for i, doc in enumerate(merged)
    ]
    if reranker is None:
        top_passages = passages[:RERANK_TOP_N]
    else:
        try:
            rerank_req = RerankRequest(query=query, passages=passages)
            # flashrank 0.2.x 的方法名是 rerank（旧版为 rank）
            rank_fn = getattr(reranker, "rerank", None) or reranker.rank
            ranked = rank_fn(rerank_req)
            top_passages = ranked[:RERANK_TOP_N]
        except Exception as e:
            st.warning(f"Rerank 出错，使用 RRF 结果: {e}")
            top_passages = passages[:RERANK_TOP_N]

    # ── 组装返回结果 ──
    results = []
    for p in top_passages:
        meta = p.get("meta", {})
        results.append({
            "text":   p["text"],
            "book":   meta.get("book", "未知"),
            "source": meta.get("source", ""),
            "page":   meta.get("page", "?"),
        })
    return results


# ══════════════════════════════════════════════
#  LLM 工厂
# ══════════════════════════════════════════════
def get_llm(provider: str, api_key: str, temperature: float):
    """根据选择的 provider 返回对应 LLM 实例。"""
    if provider == "DeepSeek":
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            temperature=temperature,
            streaming=True,
        )
    elif provider == "ZhipuAI (GLM-4)":
        # ZhipuAI 兼容 OpenAI 接口
        return ChatOpenAI(
            model="glm-4-flash",
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            temperature=temperature,
            streaming=True,
        )
    else:
        raise ValueError(f"未知 provider: {provider}")


# ══════════════════════════════════════════════
#  Prompt 模板
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """\
你是一名专业的战锤40K第十版规则顾问，代号「铁幕」。
你的任务是根据下方【规则档案】回答指挥官的问题。

━━ 强制执行规则 ━━
① **必须引用来源**：每条核心信息后标注 [《书名》第X页]，例如 [《黑暗天使》第14页]。
② **数据优先展示**：兵种属性（M/T/SV/W/LD/OC）、攻击属性（A/BS/S/AP/D）必须用表格或粗体展示。
③ **不得编造**：若档案中无相关信息，直接回复"档案缺失，建议查阅原始规则书"。
④ **语言风格**：中文回答，冷静专业，允许偶尔使用40K术语（如"黄金宝座"、"机械教义"）。
⑤ **格式规范**：使用 Markdown，关键词加粗，列表整齐。

━━ 规则档案 ━━
{context}
"""

HUMAN_PROMPT = "{question}"


def build_prompt_template() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human",  HUMAN_PROMPT),
    ])


def format_context(passages: list[dict]) -> str:
    """将 passages 格式化为提示词中的 context 字符串。"""
    parts = []
    for i, p in enumerate(passages, 1):
        page_info = f"第{p['page']}页" if p["page"] != "?" else ""
        header = f"【档案 {i}】《{p['book']}》{page_info}"
        parts.append(f"{header}\n{p['text']}")
    return ("\n\n" + "─" * 40 + "\n\n").join(parts)


# ══════════════════════════════════════════════
#  侧边栏 UI
# ══════════════════════════════════════════════
def render_sidebar(vectorstore) -> tuple[str, str, float, list[str] | None, bool]:
    """渲染侧边栏，返回 (provider, api_key, temperature, filter_books, use_agent)。"""
    with st.sidebar:
        st.markdown("## ⚔️ 战术终端设置")
        st.divider()

        # ── API 配置 ──
        st.markdown("### 🔑 LLM 配置")
        provider = st.selectbox(
            "选择 LLM",
            ["DeepSeek", "ZhipuAI (GLM-4)"],
            help="DeepSeek 性价比高；ZhipuAI GLM-4 对中文更友好",
        )

        # 从 secrets 或环境变量读取默认 key
        default_key = ""
        try:
            default_key = st.secrets.get("OPENAI_API_KEY", "") or ""
        except Exception:
            default_key = os.getenv("OPENAI_API_KEY", "")

        api_key = st.text_input(
            "API Key",
            value=default_key,
            type="password",
            help="DeepSeek: sk-xxx | ZhipuAI: 在 bigmodel.cn 获取",
        )
        temperature = st.slider(
            "Temperature（创造性）",
            min_value=0.0, max_value=1.0, value=0.1, step=0.05,
            help="越低越精准，越高越发散。规则查询建议 0.0~0.1",
        )

        st.divider()

        # ── 实验：Agent 模式（L5 编排层）──
        st.markdown("### 🧪 实验功能")
        use_agent = st.checkbox(
            "Agent 模式",
            value=False,
            help=(
                "开启后走 L5 Agent 编排层：意图分类 → 工具调用（查 wiki/术语/算分）"
                "→ 合成带引用的答案，工具查不到时静默降级到经典混合检索。"
                "默认关闭，走现有 FAISS+BM25→RRF→LLM 经典链（流式）。"
            ),
        )

        st.divider()

        # ── 书目过滤 ──
        st.markdown("### 📚 规则书过滤")
        filter_books = None

        if vectorstore is not None:
            # 从 FAISS docstore 提取所有 book 名
            try:
                all_docs = list(vectorstore.docstore._dict.values())
                book_names = sorted(set(
                    d.metadata.get("book", "未知")
                    for d in all_docs
                    if d.metadata.get("book")
                ))
            except Exception:
                book_names = []

            if book_names:
                selected = st.multiselect(
                    "仅搜索选定规则书（留空=全部）",
                    options=book_names,
                    default=[],
                    help="选择后只从指定规则书中检索，精度更高",
                )
                filter_books = selected if selected else None
            else:
                st.info("无法读取书目列表")
        else:
            st.warning("知识库尚未构建")

        st.divider()

        # ── 检索参数 ──
        st.markdown("### ⚙️ 检索参数")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("FAISS 召回", FAISS_TOP_K)
            st.metric("BM25 召回", BM25_TOP_K)
        with col2:
            st.metric("最终保留", RERANK_TOP_N)
            st.metric("排序", "RRF" if not USE_RERANKER else "FlashRank")

        st.divider()

        # ── 知识库管理 ──
        st.markdown("### 🗄️ 知识库管理")
        st.info(
            f"📂 PDF 数量：{len(list(DATA_DIR.glob('*.pdf')))}\n\n"
            f"🧠 索引状态：{'✅ 已构建' if vectorstore else '❌ 未构建'}"
        )
        if st.button("🔄 重建知识库（运行 ingest.py）", use_container_width=True):
            st.code("python ingest.py --rebuild", language="bash")
            st.warning("请在终端中手动执行以上命令，完成后刷新页面。")

        st.divider()
        st.caption("⚔️ 为皇帝而战，在数据中寻找真理。")

    return provider, api_key, temperature, filter_books, use_agent


# ══════════════════════════════════════════════
#  Agent 模式（L5 编排层）接线
# ══════════════════════════════════════════════
def build_agent_tools(vectorstore, bm25_retriever, reranker, filter_books):
    """构造注入了「本进程已加载资源」的工具集。

    用当前已加载的向量库/BM25/reranker 绑定 rag_search，替换 agent.tools 里
    会 _import_app() 重新 import app.py 的默认实现——后者在 Streamlit 运行时会
    二次触发 st.set_page_config 而抛异常。其余 10 个工具沿用 agent.tools 默认实现。
    """
    from agent.tools import TOOLS as BASE_TOOLS

    def _bound_rag_search(query: str) -> dict:
        passages = hybrid_retrieve(
            query=query,
            vectorstore=vectorstore,
            bm25_retriever=bm25_retriever,
            reranker=reranker,
            filter_books=filter_books,
        )
        return {
            "found": bool(passages),
            "passages": passages,
            "note": None if passages else "未检索到相关段落",
        }

    return {**BASE_TOOLS, "rag_search": _bound_rag_search}


def _normalize_agent_sources(sources) -> list[dict]:
    """归一化 AgentResult.sources 供展示/历史：final 给 {book,page}，
    rag 兜底给 passages（含 source）。同书同页去重。"""
    seen: set = set()
    out: list[dict] = []
    for s in sources or []:
        if not isinstance(s, dict):
            continue
        book = s.get("book", "未知")
        page = s.get("page", "?")
        key = (book, page)
        if key in seen:
            continue
        seen.add(key)
        out.append({"book": book, "page": page, "source": s.get("source", "")})
    return out


def render_agent_answer(user_input, provider, api_key, temperature, tools):
    """Agent 分支：跑 AgentLoop（非流式），渲染意图/工具链/降级标记。

    返回 (response_text, unique_sources, degraded)。degraded=True 时不渲染答案，
    交由调用方转经典链作答（保证 Agent 模式答案质量不劣于经典链）。
    """
    from agent.context import SessionContext
    from agent.llm_client import OpenAICompatLLMClient
    from agent.loop import AgentLoop

    if "agent_session" not in st.session_state:
        st.session_state.agent_session = SessionContext()

    with st.status(
        "🧠 Agent 编排中（意图分类 → 工具调用 → 合成）...", expanded=False
    ) as status:
        t0 = time.time()
        try:
            llm = OpenAICompatLLMClient(
                api_key=api_key, provider=provider, temperature=temperature,
            )
            result = AgentLoop(llm=llm, tools=tools).run(
                user_input, session=st.session_state.agent_session,
            )
        except Exception as e:
            status.update(label="❌ Agent 执行失败", state="error")
            st.error(f"Agent 执行失败：{e}")
            st.stop()
        dt = time.time() - t0
        trace = " → ".join(result.tool_calls) if result.tool_calls else "（无工具调用）"
        st.write(f"意图：**{result.intent}** ｜ 工具链：{trace} ｜ {dt:.2f}s")
        status.update(
            label="↩️ 工具未命中，转经典检索链" if result.degraded else "✅ Agent 作答完成",
            state="error" if result.degraded else "complete",
        )

    if result.degraded:
        st.info("ℹ️ Agent 未能用结构化工具作答，自动转经典混合检索链（结果见下）。")
        return None, None, True

    st.markdown(result.answer)
    unique_sources = _normalize_agent_sources(result.sources)
    if unique_sources:
        with st.expander(f"📎 引用来源（{len(unique_sources)} 处）", expanded=True):
            for src in unique_sources:
                name = Path(src.get("source", "")).name
                tail = f" — `{name}`" if name else ""
                st.markdown(
                    f"- **《{src.get('book', '未知')}》** 第{src.get('page', '?')}页{tail}"
                )
    return result.answer, unique_sources, False


def render_classic_answer(
    user_input, provider, api_key, temperature, filter_books,
    vectorstore, bm25_retriever, reranker,
):
    """经典链分支：混合检索 → 流式生成 → 来源。返回 (response_text, unique_sources)。"""
    status = st.status("🔍 正在检索规则档案...", expanded=False)

    with status:
        st.write("📡 FAISS 向量召回 + BM25 关键词召回...")
        t0 = time.time()
        passages = hybrid_retrieve(
            query=user_input,
            vectorstore=vectorstore,
            bm25_retriever=bm25_retriever,
            reranker=reranker,
            filter_books=filter_books,
        )
        t_retrieve = time.time() - t0
        st.write(f"✅ 检索完成，获取 {len(passages)} 条档案 ({t_retrieve:.2f}s)")

        if not passages:
            status.update(label="⚠️ 未找到相关档案", state="error")
            st.warning("未在知识库中找到相关规则，请检查知识库是否构建完整。")
            st.stop()

        st.write(f"🤖 调用 {provider}...")
        try:
            llm = get_llm(provider, api_key, temperature)
        except Exception as e:
            status.update(label="❌ LLM 初始化失败", state="error")
            st.error(f"LLM 初始化失败: {e}")
            st.stop()

        status.update(label="✅ 档案就绪，正在生成回答...", state="complete")

    context_text = format_context(passages)
    prompt_template = build_prompt_template()
    chain = prompt_template | llm | StrOutputParser()

    response_text = st.write_stream(
        chain.stream({"context": context_text, "question": user_input})
    )

    source_list = [
        {"book": p["book"], "source": p["source"], "page": p["page"]}
        for p in passages
    ]
    seen = set()
    unique_sources = []
    for s in source_list:
        key = (s["book"], s["page"])
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)

    with st.expander(f"📎 引用来源（{len(unique_sources)} 处）", expanded=True):
        for src in unique_sources:
            st.markdown(
                f"- **《{src['book']}》** 第{src['page']}页 "
                f"— `{Path(src['source']).name}`"
            )
    return response_text, unique_sources


# ══════════════════════════════════════════════
#  主界面
# ══════════════════════════════════════════════
def main():
    # ── 标题 ──
    st.markdown(
        "<h1 style='text-align:center'>⚔️ 战锤40K 战术参谋部</h1>"
        "<p style='text-align:center;color:gray'>Hybrid RAG · BGE-M3 · FlashRank Reranker</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── 加载资源 ──
    try:
        embeddings, vectorstore, reranker, reranker_warning = load_resources()
    except Exception as e:
        st.error(f"❌ 资源加载失败：{e}")
        st.stop()

    if reranker_warning:
        st.warning(reranker_warning)

    # ── BM25 索引 ──
    bm25_retriever = build_bm25(vectorstore)

    # ── 侧边栏 ──
    provider, api_key, temperature, filter_books, use_agent = render_sidebar(vectorstore)

    # ── 知识库未就绪 ──
    if vectorstore is None:
        st.warning(
            "📭 知识库尚未构建。\n\n"
            "请先在终端运行：\n```\npython ingest.py\n```\n"
            "完成后刷新此页面。"
        )
        st.stop()

    # ── API Key 检查 ──
    if not api_key:
        st.warning("⚠️ 请在侧边栏填写 API Key。")
        st.stop()

    # ── 聊天历史 ──
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "指挥官，战术参谋部已就绪。\n\n"
                    "您可以询问任何战锤40K第十版规则问题，例如：\n"
                    "- 「黑暗天使的信仰天使数据卡是什么？」\n"
                    "- 「混沌星际战士的混乱符文规则是什么？」\n"
                    "- 「黄金宝座护卫队的拯救掷骰如何计算？」"
                ),
            }
        ]

    # ── 渲染历史消息 ──
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # 渲染历史消息的来源引用
            if msg.get("sources"):
                with st.expander("📎 引用来源", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f"- **《{src['book']}》** 第{src['page']}页 "
                            f"`{Path(src['source']).name}`"
                        )

    # ── 用户输入 ──
    if user_input := st.chat_input("询问规则、数据卡、战术技巧..."):
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # ── 生成回答 ──
        with st.chat_message("assistant"):
            if use_agent:
                agent_tools = build_agent_tools(
                    vectorstore, bm25_retriever, reranker, filter_books,
                )
                response_text, unique_sources, degraded = render_agent_answer(
                    user_input, provider, api_key, temperature, agent_tools,
                )
                if degraded:
                    # Agent 工具未命中 → 转经典链 LLM 合成，保证不劣于经典
                    response_text, unique_sources = render_classic_answer(
                        user_input, provider, api_key, temperature, filter_books,
                        vectorstore, bm25_retriever, reranker,
                    )
            else:
                response_text, unique_sources = render_classic_answer(
                    user_input, provider, api_key, temperature, filter_books,
                    vectorstore, bm25_retriever, reranker,
                )

        # ── 保存到历史 ──
        st.session_state.messages.append({
            "role":    "assistant",
            "content": response_text,
            "sources": unique_sources,
        })


if __name__ == "__main__":
    main()
