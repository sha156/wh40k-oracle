# 战锤40K 规则书 RAG 问答系统

基于本地知识库的战锤40K规则问答项目。系统会把 `data/` 目录中的 PDF 规则书切分、向量化并建立 FAISS 索引，在查询时结合向量检索、BM25 关键词检索、RRF 融合和 FlashRank 重排，再调用 LLM 生成带来源引用的中文回答。

## 功能概览

- 本地知识库构建：扫描 `data/` 下的 PDF，提取文本并建立向量索引
- 混合检索：`FAISS + BM25 + RRF`
- 本地重排：`FlashRank`
- Web 界面：基于 Streamlit 的聊天式问答页面
- 来源引用：回答中展示书名和页码
- 书目过滤：可只检索指定规则书

## 技术栈

| 模块 | 方案 |
|---|---|
| PDF 解析 | `PyMuPDFLoader` |
| 分块 | `SemanticChunker` |
| 嵌入模型 | `BAAI/bge-m3` |
| 向量库 | `FAISS` |
| 关键词检索 | `BM25` |
| 融合 | `Reciprocal Rank Fusion` |
| 重排 | `FlashRank / ms-marco-MiniLM-L-12-v2` |
| LLM 接口 | `langchain-openai` |
| 前端 | `Streamlit` |

## 项目结构

```text
.
├── app.py                   # Streamlit Web 应用
├── ingest.py                # PDF 入库与索引构建脚本
├── hf_embeddings_compat.py  # HuggingFaceEmbeddings 兼容层
├── run_streamlit.ps1        # 使用项目 .venv 启动 Streamlit
├── requirements.txt         # 依赖列表
├── data/                    # 放置 PDF 规则书
├── local_vector_store/      # FAISS 索引与增量处理记录
├── opt/                     # 模型缓存目录
├── fix_model.py             # FlashRank 模型下载/修复辅助脚本
└── download_bge.py          # 旧版辅助脚本，默认流程不依赖
```

## 运行要求

- Windows + PowerShell
- Python 3.10 及以上
- 推荐使用项目虚拟环境 `.venv`
- 首次下载模型需要可用网络
- 建议至少 16 GB 内存

## 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果你已经有 `.venv`，只需要激活并安装依赖即可。

## 准备 PDF 数据

把需要入库的规则书 PDF 放到 `data/` 目录，例如：

```text
data/
├── 核心规则.pdf
├── 黑暗天使.pdf
├── 混沌星际战士.pdf
└── 星际战士.pdf
```

## 构建知识库

增量构建：

```powershell
.\.venv\Scripts\python.exe ingest.py
```

全量重建：

```powershell
.\.venv\Scripts\python.exe ingest.py --rebuild
```

自定义 PDF 目录：

```powershell
.\.venv\Scripts\python.exe ingest.py --data-dir D:\path\to\pdfs
```

构建完成后会在 `local_vector_store/` 生成：

- `index.faiss`
- `index.pkl`
- `processed_files.json`

## 启动应用

推荐使用项目内脚本启动，这样不会误用系统 Python 或 Conda 环境：

```powershell
.\run_streamlit.ps1
```

等价命令：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

默认访问地址：

```text
http://localhost:8501
```

如果 8501 端口被占用：

```powershell
.\run_streamlit.ps1 --server.port 8508
```

## API Key 配置

应用当前会按以下顺序读取 API Key：

1. Streamlit secrets 中的 `OPENAI_API_KEY`
2. 进程环境变量 `OPENAI_API_KEY`
3. 侧边栏手动输入

推荐方式是使用 `.streamlit/secrets.toml`：

```toml
OPENAI_API_KEY = "你的 API Key"
```

也可以在启动前设置环境变量：

```powershell
$env:OPENAI_API_KEY = "你的 API Key"
.\run_streamlit.ps1
```

注意：当前代码不会自动读取根目录 `.env` 文件。只有你自己先把环境变量导入到当前终端，或改代码引入 `python-dotenv`，`.env` 才会生效。

## 使用说明

启动成功后，你可以：

- 在侧边栏选择 LLM 提供商：`DeepSeek` 或 `ZhipuAI (GLM-4)`
- 输入 API Key
- 选择是否只检索部分规则书
- 在聊天框直接提问规则问题

应用会：

1. 从 FAISS 进行语义召回
2. 从 BM25 进行关键词召回
3. 用 RRF 合并结果
4. 用 FlashRank 做精排
5. 让 LLM 基于检索片段生成答案

## RAG 的局限性

这个项目能提高查规则的效率，但它并不好用到可以“无脑信任”的程度。对战锤40K这类规则密集、例外很多、措辞很关键的领域，RAG 有几个天然短板：

- 检索不到就答不好。相关段落如果没被召回，后面的 LLM 再强也只能基于不完整上下文作答。
- 分块会破坏上下文。规则条文、附注、限制条件、例外条款可能被切到不同 chunk，导致回答只抓到一半。
- PDF 解析不稳定。表格、双栏排版、页眉页脚、勘误页、数据卡格式，都会影响文本提取质量。
- 关键词很敏感。同一个规则换一种问法，召回结果可能明显变差，尤其是中英混杂、俗称、简称很多时。
- 多跳推理能力有限。涉及“主规则 + 数据卡 + FAQ/勘误 + 特殊阵营规则”联合判断时，RAG 很容易漏条件。
- 规则优先级不好处理。战锤规则里常见“一般规则 vs 特例规则”“旧版文本 vs 新版勘误”，RAG 不一定能稳定判断谁优先。
- 会出现“看起来对，其实不严谨”的答案。LLM 很擅长把话说顺，但顺不代表规则判断正确。
- 来源引用不等于答案可靠。模型可能引用了对的书和页码，但解释过程仍然有偏差。
- 知识库会过时。只要 PDF 没更新，FAQ、勘误、平衡补丁、新版数据卡都不会自动反映进去。
- 延迟和成本都不低。一次问答通常要走检索、融合、重排、生成，速度不如直接全文搜索，稳定性也更依赖模型和网络。

更直接地说，这个项目更适合：

- 快速定位可能相关的规则页
- 给出一个初步解释
- 帮你缩小人工核对范围

它不适合：

- 作为比赛裁定依据
- 代替玩家自己核对原文
- 在复杂规则冲突场景下直接下最终结论

如果你想把它用得更稳，比较现实的做法是把它当成“规则检索助手”，而不是“规则裁判”。看到答案后，最好始终回到原书页码和勘误文本做最终确认。

## 已处理的兼容性问题

这个仓库当前已经处理了两个常见问题：

### 1. 启动时误用了错误的 Python 环境

如果你直接运行系统里的 `streamlit run app.py`，很容易落到全局 Python / Conda 环境，导致缺少 `langchain-huggingface`，或者 `torch` 版本不对。

当前 `app.py` 已经加了保护提示，但正确做法仍然是：

```powershell
.\run_streamlit.ps1
```

### 2. FlashRank 模型目录嵌套

有些压缩包会解压成这种结构：

```text
opt/
└── ms-marco-MiniLM-L-12-v2/
    └── ms-marco-MiniLM-L-12-v2/
        └── flashrank-MiniLM-L-12-v2_Q.onnx
```

当前代码已经兼容这种目录结构。即使 FlashRank 加载失败，也会自动降级为仅使用 RRF 排序，页面仍可启动。

## 常见问题

### Q1：启动时报 `ModuleNotFoundError: No module named 'langchain_huggingface'`

你大概率用了错误的解释器。不要用系统 `streamlit`，改用：

```powershell
.\run_streamlit.ps1
```

### Q2：启动时报 FlashRank 模型找不到

先尝试直接启动当前版本，代码会自动识别嵌套目录。如果模型确实没下载下来，再运行：

```powershell
.\.venv\Scripts\python.exe fix_model.py
```

### Q3：页面提示“知识库尚未构建”

说明 `local_vector_store/` 中没有可用索引。先执行：

```powershell
.\.venv\Scripts\python.exe ingest.py
```

### Q4：8501 端口被占用

换一个端口启动：

```powershell
.\run_streamlit.ps1 --server.port 8508
```

### Q5：模型下载很慢或失败

代码里已经设置了 `HF_ENDPOINT=https://hf-mirror.com`。如果你的网络环境不适用，需要自行调整镜像、代理或 SSL 设置。

`ingest.py` 当前还硬编码了这两项代理：

```python
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"]  = "http://127.0.0.1:7897"
```

如果你本机没有这个代理，请先修改 [ingest.py](/D:/Project/py/RAG/ingest.py#L38) 和 [ingest.py](/D:/Project/py/RAG/ingest.py#L39)。

## 开发说明

- `app.py` 中的嵌入模型、检索参数和重排参数都在文件顶部配置
- `ingest.py` 支持增量构建，依赖 `processed_files.json` 判断文件是否变化
- `hf_embeddings_compat.py` 用于兼容不同版本的 LangChain/HuggingFace 包结构

## 当前默认命令

```powershell
# 1. 激活环境
.\.venv\Scripts\Activate.ps1

# 2. 构建知识库
.\.venv\Scripts\python.exe ingest.py

# 3. 启动应用
.\run_streamlit.ps1
```
