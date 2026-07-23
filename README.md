# wh40k-oracle · 战锤40K 垂类 AI

面向战锤40K（Warhammer 40,000）**第 11 版**的本地知识智库。从"规则书 PDF 问答"起步，已长成四位一体的垂类系统：**规则问答 + 单位图鉴 + 对战模拟 + 军表实验室**，共享同一套官方对齐的结构化数据。全程本地嵌入、可切换云端 LLM，官方点数与规则定期对齐官网。

> 当前定位：现行**第 11 版**（2026-06-20 生效）。语料按层组织——11 版核心规则（规则唯一真源）+ Faction Pack 补丁 + MFM/平衡版点数 + 十版 codex 兵牌基底。设计蓝图见 `docs/superpowers/`。

## 四大能力

| 能力 | 说的话 / 入口 | 底层 |
|---|---|---|
| **规则问答** | "先攻怎么判定？"→ 检索规则页 → LLM 带**书名+页码**引用作答 | 混合检索链 + Agent 工具模式 + 11 版规则层保底 |
| **单位图鉴** | 浏览阵营 → 单位 → 完整兵牌（属性/武器/技能/点数，中英切换） | `db/wh40k.sqlite` 结构库 + 三层中文别名 |
| **对战模拟** | "10 个终结者打 20 个狂热者" → 逐骰蒙特卡洛模拟 | `engines/simulator/`（11 版规则：先攻/掩体命中侧惩罚/USR） |
| **军表实验室** | 粘贴/搭建军表 → 验表（点数+编制约束）+ 强度点评 | `engines/roster/` + 接模拟器做强度评估 |

四大能力都已上网站（`web/` 四页签）。规则问答还内建 **Agent 模式**（默认开启）：LLM 自主调用检索、图鉴、模拟工具，边查边答。

## 架构总览

```
                          官方权威数据层（定期对齐官网）
     ┌───────────────────────────────────────────────────────────┐
     │  MFM 官方点数手册 ─┐                                          │
     │  Wahapedia CSV ───┼─► db_compile ─► db/wh40k.sqlite ◄─ BSData 交叉校验
     │  黑图书馆开放 API ─┘        │        （units/weapons/abilities/       │
     └────────────────────────────┼──────── stratagems/enhancements…11 表）─┘
                                   │              ▲
   data/ 原始 PDF ─► ingest.py ─► FAISS 向量库    │ dsl_payloads/ 28 阵营技能 DSL 投影
        │  (PyMuPDF→llm_refine→bge-m3 嵌入)  │    │
        ▼                                    ▼    ▼
  ┌──────────────────────────────────────────────────────────┐
  │  检索链：FAISS + BM25(jieba) + 查询别名扩展 + RRF 融合       │
  │          + 11 版规则层保底 ─► LLM ─► 带引用中文回答          │
  └──────────────────────────────────────────────────────────┘
        ▲                                    ▲          ▲
        │  engines/simulator（逐骰对战）      │  engines/roster（验表+点评）
        │                                    │
   web_api/（FastAPI）◄──────────────────────┴── web/（Next.js 四页签）
```

## 数据权威层级

数据"正确"不靠单源自证，每类事实定一个唯一真源：

- **点数** → 官方 MFM（`mfm.warhammer-community.com` 实时站）为最高真源，`db_compile mfm` 定期抓取比对；Wahapedia 是结构化镜像（实测曾 44.6% 过期）
- **英文属性** → 社区结构库（Wahapedia）为主，BSData 做第二源交叉校验（实测 ~98.9% 一致，分歧人工裁决）
- **规则正文** → 11 版核心规则 + Faction Pack 补丁为真源
- **中文** → 叠在英文上的翻译层（data_refined 规范译名 + 黑图书馆中英桥 + 社区俗名三源灌 `aliases` 表）
- **阵营技能** → `dsl_payloads/*.json` 是 DSL 唯一真源，投影进 sqlite 供模拟器读取

爬取式管线对上游版式脆弱：`db_compile mfm --fetch` 解析官网 HTML，官网改版会静默丢单位——保鲜纪律是**逐阵营行数对账 + 明星单位存在性证伪**，不轻信解析器自报的成功数。

## 技术栈

| 模块 | 方案 |
|---|---|
| PDF 解析 / 重构 | PyMuPDF + LLM 结构化重排（`llm_refine.py`，按页内容哈希缓存） |
| 嵌入 | `BAAI/bge-m3`（本地 CPU 推理，走 hf-mirror 镜像） |
| 向量库 / 关键词 | FAISS + BM25（jieba 中文分词） |
| 融合 | Reciprocal Rank Fusion (RRF)；FlashRank 重排**默认关闭**（实测中文重排差于 RRF） |
| 结构库 | SQLite（11 表：datasheets/units/models/weapons/abilities/stratagems/detachments/enhancements/aliases/unit_zh_detail…） |
| 阵营技能 | 自研 Effect DSL，28 阵营逐条编码 → 投影进库供模拟器 |
| LLM | DeepSeek `deepseek-chat` / 智谱 `glm-4-flash`（OpenAI 兼容，可切换） |
| 后端 / 前端 | FastAPI（`web_api/`）+ Next.js（`web/`，四页签） |
| 交互问答 | Streamlit（`app.py`，本地快速试） |

## 运行要求

- Windows + PowerShell
- **Python 3.9**（项目 `.venv` 为 3.9.1；代码已避免 3.10+ 语法）
- 首次需联网下载 bge-m3 模型（走 hf-mirror 镜像）；官方数据抓取需代理
- 建议 ≥ 16 GB 内存（CPU 嵌入推理）

## 快速开始

```powershell
# 1. 依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置 API key（走环境变量，不落盘）
copy .env.example .env    # 填入 DeepSeek / 智谱 key

# 3. 构建检索索引（PDF 放进 data/）
.\.venv\Scripts\python.exe ingest.py            # 增量
.\.venv\Scripts\python.exe ingest.py --rebuild  # 清空重建

# 4a. 本地快速问答（Streamlit）
.\run_streamlit.ps1

# 4b. 完整四页签网站（FastAPI + Next.js）
.\.venv\Scripts\python.exe -m uvicorn web_api.main:app --reload   # 后端
cd web; npm install; npm run dev                                  # 前端
```

## 数据管线

```powershell
# 官方点数：抓取 → 比对 → 应用（官方为最高真源，需代理）
.\.venv\Scripts\python.exe -m db_compile mfm --fetch   # 抓官网全部阵营页
.\.venv\Scripts\python.exe -m db_compile mfm --check   # 与库比对出过期分数
.\.venv\Scripts\python.exe -m db_compile mfm --apply   # 写回 units.points_json

# 一键刷新全链：BSData pull → MFM 抓取 → 重建库 → 应用分数 → 别名 → 交叉校验 → 收敛校验
.\.venv\Scripts\python.exe -m db_compile update            # 联网全量
.\.venv\Scripts\python.exe -m db_compile update --offline  # 复用缓存快速本地重建

# 阵营技能 DSL 投影进库
.\.venv\Scripts\python.exe -m db_compile dsl-apply

# 双语术语表：扫实体 → 下载 Wahapedia → 中英配对 → 生成 wiki/terms.*
.\.venv\Scripts\python.exe -m wiki_compile extract
.\.venv\Scripts\python.exe -m wiki_compile fetch-canonical   # 需代理
.\.venv\Scripts\python.exe -m wiki_compile pair --llm        # LLM 兜底需 DEEPSEEK_API_KEY
.\.venv\Scripts\python.exe -m wiki_compile terms
```

> ⚠️ `db_compile build` 重建库会覆盖官方分数/别名/中文层，重建后自动补跑恢复阶段；单独跑过 `mfm --apply` 后若再重建，需重跑。

## 项目结构

```text
.
├── app.py                   # Streamlit 应用：混合检索 + 查询扩展 + LLM 回答
├── ingest.py                # PDF 入库与索引构建（优先读 data_refined/）
├── llm_refine.py            # LLM PDF 重构（兵牌页 → 结构化 Markdown，哈希缓存）
├── agent/                   # Agent 工具模式：LLM 自主调用检索/图鉴/模拟工具
├── engines/
│   ├── simulator/           # 11 版逐骰对战蒙特卡洛模拟
│   └── roster/              # 军表验表（点数+编制约束）+ 强度点评
├── db_compile/              # 结构库编译：mfm/build/crosscheck/dsl-apply/update…
├── dsl_payloads/            # 28 阵营技能 DSL 真源（投影进库）
├── db/wh40k.sqlite          # 结构化真源库（11 表）
├── db_sources/              # 官方源缓存：mfm / wahapedia / bsdata / blacklibrary
├── web_api/                 # FastAPI：/chat /codex /simulate /roster …
├── web/                     # Next.js 四页签前端（聊天/图鉴/模拟器/军表）
├── wiki_compile/            # 双语术语表流水线
├── benchmarks/              # QA 基准（v1_10th / v3_edition11）
├── tests/                   # pytest 测试（86 个测试文件）
├── docs/superpowers/        # 设计蓝图与迁移计划
├── data/  data_refined/     # 原始 PDF / LLM 重构结果（大部分不入库）
├── local_vector_store/      # FAISS 索引（不入库）
└── opt/                     # 模型缓存（不入库）
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

## 数据与版权

规则书 PDF 来自多个汉化组，属受版权保护内容；`data/` 原始 PDF 与绝大部分 `data_refined/` 结构化结果**不纳入仓库**，仅本地使用。仓库内仅保留少量试点重构结果用于演示。请勿用于再分发。

官方点数与规则以 Games Workshop 现行发布为准，本项目仅作个人学习与技术演示，与 Games Workshop 无隶属关系。

## 路线图

**已完成**
- 检索问答链（混合检索 + 双语术语扩展 + 11 版规则层保底 + Agent 工具模式）
- 11 版迁移全线收官（语料分层、检索版本感知、模拟器 11 版化、基准 v3 = 99.0 零硬错）
- 结构化真源库（sqlite 11 表）+ 官方数据管线（MFM 点数 / Wahapedia / BSData 交叉校验 / 一键 update）
- 对战模拟器 + 军表实验室（验表 + 点评）
- 网站化四页签（Next.js + FastAPI，契约真源单点镜像）
- 阵营技能 DSL：28 阵营逐条编码并投影进库

**进行中**
- 阵营技能 DSL 逐条补全 + wiki 全量编译（长期滚动）
- 基准集扩充、部署上线、外部数据源观察（BSData-11e / Wahapedia 11 版滚更）
