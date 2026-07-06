# wh40k-oracle · 战锤40K 规则智库

面向战锤40K（Warhammer 40,000）规则的本地 AI 问答系统。把汉化规则书 PDF 结构化入库，用**混合检索 + 双语术语扩展 + LLM 生成带引用的中文回答**，全程本地嵌入、可切换云端 LLM。

> 项目正从「纯 RAG 问答」演进为**战锤宇宙垂类 AI**（规则专家 + 对局模拟 + 军表实验室）。当前仓库已落地检索问答与两条数据结构化流水线，v2 蓝图见 `docs/superpowers/`。

## 它能做什么

- **规则问答**：中文提问 → 检索相关规则页 → LLM 生成回答，附**书名 + 页码**引用
- **混合检索**：FAISS 向量 + BM25 关键词（jieba 中文分词）+ RRF 融合
- **查询扩展**：社区译名别名（`UNIT_ALIASES`）+ 双语术语表（`wiki/terms.json`），中文单位名自动补英文官方名，提升召回
- **书目过滤**：可只在指定规则书内检索
- **Web 界面**：Streamlit 聊天式问答

## 架构总览

```
        ┌── data/ 原始 PDF（多汉化组，版式各异）
        │
  ingest.py ──► PyMuPDF 提取 ──► 分块 ──► bge-m3 嵌入 ──► FAISS
        │                                                    │
        │   （可选前置）llm_refine.py：LLM 按战锤 schema      │
        │   把兵牌页重排成结构化 Markdown → data_refined/     │
        │                                                    ▼
  app.py ── 查询 ─► FAISS + BM25(jieba) + RRF ─► 查询扩展 ─► LLM ─► 带引用回答
                          ▲
                          └── wiki/terms.json（wiki_compile 产出的双语术语表）
```

三条流水线：

| 流水线 | 入口 | 作用 |
|---|---|---|
| **检索问答** | `app.py` / `ingest.py` | PDF → 向量库 → 混合检索 → LLM 回答 |
| **LLM PDF 重构** | `llm_refine.py` | 把被 PyMuPDF 拍扁的兵牌属性表/武器表，用 LLM 重排成结构化条目（一个单位 = 一个 `##`），按页内容哈希缓存 |
| **双语术语表** | `python -m wiki_compile` | 扫 `data_refined/` 实体 → 以 Wahapedia 官方英文名为锚做中英配对 → `wiki/terms.*`，接入检索查询扩展 |

## 技术栈

| 模块 | 方案 |
|---|---|
| PDF 解析 | PyMuPDF |
| 分块 | SemanticChunker / 按 `##` 条目分块（重构后） |
| 嵌入 | `BAAI/bge-m3`（本地 CPU 推理） |
| 向量库 | FAISS |
| 关键词检索 | BM25 + jieba 中文分词 |
| 融合 | Reciprocal Rank Fusion (RRF) |
| 重排 | FlashRank（**默认关闭**：实测 ms-marco 系列对中文重排差于 RRF 顺序，见 `CLAUDE.md`） |
| LLM | DeepSeek `deepseek-chat` / 智谱 `glm-4-flash`（OpenAI 兼容接口，可切换） |
| 术语锚点 | Wahapedia wh40k10ed CSV |
| 前端 | Streamlit |

## 运行要求

- Windows + PowerShell
- **Python 3.9**（项目 `.venv` 为 3.9；代码已避免 3.10+ 语法）
- 首次需联网下载 bge-m3 模型（走 hf-mirror 镜像）
- 建议 ≥ 16 GB 内存（CPU 嵌入推理）

## 快速开始

```powershell
# 1. 依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置 API key（走环境变量，不落盘）
copy .env.example .env    # 填入 DeepSeek / 智谱 key

# 3. 把 PDF 规则书放进 data/，构建索引
.\.venv\Scripts\python.exe ingest.py            # 增量
.\.venv\Scripts\python.exe ingest.py --rebuild  # 清空重建

# 4. 启动 Web 界面
.\run_streamlit.ps1
```

### 可选：LLM 结构化流水线

```powershell
# 兵牌页 LLM 重构（需 DEEPSEEK_API_KEY），产出 data_refined/<书名>/
.\.venv\Scripts\python.exe llm_refine.py

# 双语术语表：扫实体 → 下载 Wahapedia → 中英配对 → 生成 wiki/terms.*
.\.venv\Scripts\python.exe -m wiki_compile extract
.\.venv\Scripts\python.exe -m wiki_compile fetch-canonical   # 需代理
.\.venv\Scripts\python.exe -m wiki_compile pair --llm        # LLM 兜底需 DEEPSEEK_API_KEY
.\.venv\Scripts\python.exe -m wiki_compile terms
```

## 项目结构

```text
.
├── app.py                   # Streamlit 应用：混合检索 + 查询扩展 + LLM 回答
├── ingest.py                # PDF 入库与索引构建（优先读 data_refined/）
├── llm_refine.py            # LLM PDF 重构流水线（兵牌页 → 结构化 Markdown）
├── refine_prompt.py         # 战锤领域重构 prompt
├── md_chunker.py            # 重构结果按 ## 条目分块
├── hf_embeddings_compat.py  # HuggingFaceEmbeddings 兼容层
├── wiki_compile/            # 双语术语表流水线（extract→canonical→pair→terms）
├── wiki/terms.json|md       # 产出：中英术语表（接入检索）
├── tests/                   # pytest 测试
├── docs/superpowers/        # v2 设计蓝图与实现计划
├── data/                    # 原始 PDF（不入库）
├── data_refined/            # LLM 重构结果（试点入库，其余本地）
├── local_vector_store/      # FAISS 索引（不入库）
└── opt/                     # 模型缓存（不入库）
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

## 数据与版权

规则书 PDF 来自多个汉化组，属受版权保护内容；`data/` 原始 PDF 与绝大部分 `data_refined/` 结构化结果**不纳入仓库**，仅本地使用。仓库内仅保留一本《钛帝国十版 CODEX》试点重构结果用于演示。请勿用于再分发。

## 路线图

当前（已完成）：检索问答链、LLM PDF 重构试点、P0 双语术语表并接入检索。

规划中（`docs/superpowers/` v2 蓝图）：技能效果 DSL + 蒙特卡洛对局模拟、军表验表与点评、Karpathy LLM-Wiki 知识组织、FastAPI + 前端网站化。
