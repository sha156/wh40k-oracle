# 战锤40K 规则书 RAG 问答系统

基于本地知识库的战锤40K规则问答：PDF 规则书 → 向量化入库 → 混合检索 → LLM 生成带引用的中文回答。

## 运行方式

```powershell
# 必须用项目虚拟环境（系统 python 是 3.9，不支持本项目语法）
.\.venv\Scripts\python.exe ingest.py            # 增量构建索引
.\.venv\Scripts\python.exe ingest.py --rebuild  # 清空重建
.\run_streamlit.ps1                             # 启动 Web 界面（app.py）
```

## 架构与技术栈

- `ingest.py`：PDF（`data/`）→ PyMuPDF 提取 → SemanticChunker 分块 → bge-m3 嵌入 → FAISS（`local_vector_store/`）
- `app.py`：Streamlit 界面；检索链 = FAISS + BM25（jieba 中文分词）+ 查询别名扩展（UNIT_ALIASES）+ RRF 融合 → LLM（deepseek-chat / glm-4-flash，OpenAI 兼容接口）。
  FlashRank 重排默认关闭（`USE_RERANKER=False`）：实测 ms-marco 系列（含 MultiBERT）对中文重排差于 RRF 顺序
- `hf_embeddings_compat.py`：HuggingFaceEmbeddings 兼容层
- 模型缓存在 `opt/`（bge-m3、ms-marco-MiniLM-L-12-v2 等），CPU 推理
- 嵌入走 hf-mirror 镜像 + Clash 代理（127.0.0.1:7897），相关环境变量在 ingest.py 顶部设置

## 当前重点：LLM PDF 重构（2026-07 立项）

**问题**：兵牌页（datasheet）的属性表/武器表被 PyMuPDF 拍扁成一维文字流，表头与数值分离，
且 SemanticChunker 会把单位切成两半，导致属性类问题回答不准。

**方案**（详见 `docs/superpowers/specs/2026-07-02-llm-pdf-refine-design.md`）：

1. 新增 `llm_refine.py`：deepseek-chat 按战锤领域 schema 把每页文本重排成结构化
   Markdown（一个单位/战略技能 = 一个 `##` 条目），按页内容哈希缓存到 `data_refined/<书名>/`
2. `ingest.py` 改为优先读 `data_refined/`，按 `##` 标题分块（一个单位 = 一个完整 chunk），
   元数据含 `book`/`unit`/`page`
3. 试点：《钛帝国十版CODEX-20251112.pdf》验证通过后再全量跑 49 本

## 数据事实（已验证）

- `data/` 下 49 个 PDF，47 个有完整文字层；仅《战锤40K总规则10版老湿腐版1.11》和
  《死亡守卫10版中文老湿腐版1.1》部分页面无文本（计划用 glm-4v-flash 兜底，二期）
- PDF 来自多个汉化组（老湿腐/DavidZ/双子星/kasa/官方），版式各异，勿用固定正则解析
- 存在新旧版本共存（艾达灵族 1.13/1.2、钛帝国 0115/1112、吞世者×3、混沌恶魔×3 等），
  计划移入 `data/archive/` 归档，仅最新版入库

## 约定

- API key 一律走环境变量（`DEEPSEEK_API_KEY` 等），不落盘
- `data_refined/` 的页级缓存带 prompt 版本号，改 prompt 后可选择性重跑
- 根目录的 `*.log` / `*.err` / `*.out` / `temp.pdf` 是运行产物，不要提交
