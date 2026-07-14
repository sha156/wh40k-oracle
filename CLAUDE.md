# 战锤40K 规则书 RAG 问答系统

基于本地知识库的战锤40K规则问答：PDF 规则书 → 向量化入库 → 混合检索 → LLM 生成带引用的中文回答。

**版本定位（2026-07-10 裁决）：现行第 11 版**（2026-06-20 生效）。11 版官方沿用十版 codex
（Faction Pack 原文 "supplement your Codex"），语料按层组织：11版核心规则（rules，规则唯一真源）
+ Faction Pack（overlay 补丁）+ MFM/平衡版（points/balance）+ 十版 codex（codex-base 兵牌基底）。
层级清单：`corpus_manifest.json`；迁移计划与进度：`docs/superpowers/plans/2026-07-10-edition-11-migration.md`。
模拟器已按 11 版对齐（先攻判定、掩体命中侧惩罚、USR 审计均完成）。

## 运行方式

```powershell
# 必须用项目虚拟环境（系统 python 是 3.9，不支持本项目语法）
.\.venv\Scripts\python.exe ingest.py            # 增量构建索引
.\.venv\Scripts\python.exe ingest.py --rebuild  # 清空重建
.\run_streamlit.ps1                             # 启动 Web 界面（app.py）

.\.venv\Scripts\python.exe -m wiki_compile extract          # 扫描实体清单
.\.venv\Scripts\python.exe -m wiki_compile fetch-canonical  # 下载 Wahapedia CSV（需代理）
.\.venv\Scripts\python.exe -m wiki_compile pair --llm       # 中英配对（LLM兜底需 DEEPSEEK_API_KEY）
.\.venv\Scripts\python.exe -m wiki_compile terms            # 生成 wiki/terms.*
```

## 架构与技术栈

- `ingest.py`：PDF（`data/`）→ PyMuPDF 提取 → SemanticChunker 分块 → bge-m3 嵌入 → FAISS（`local_vector_store/`）
- `app.py`：Streamlit 界面；检索链 = FAISS + BM25（jieba 中文分词）+ 查询别名扩展（sqlite aliases
  `load_alias_expansions` + 少量硬编码）+ RRF 融合 + **11版规则层保底**（单独按 `layer=rules` 过滤强塞
  最高真源进上下文，`RULES_FLOOR_FETCH_K` 防冷门英文术语跨语饥饿）→ LLM（deepseek-chat / glm-4-flash）。
  FlashRank 重排默认关闭（`USE_RERANKER=False`）：实测 ms-marco 系列（含 MultiBERT）对中文重排差于 RRF 顺序
- `hf_embeddings_compat.py`：HuggingFaceEmbeddings 兼容层
- 模型缓存在 `opt/`（bge-m3、ms-marco-MiniLM-L-12-v2 等），CPU 推理
- 嵌入走 hf-mirror 镜像 + Clash 代理（127.0.0.1:7897），相关环境变量在 ingest.py 顶部设置

## 当前进度（2026-07-14 更新）

未完成任务全景见 `docs/superpowers/plans/2026-07-12-remaining-tasks.md`。

- **11 版迁移已正式收官**（2026-07-12，PR #16）：S1-S7 全部完成，refine 缓存对账零差额
  （索引 5652 chunks），基准 gold v3 = 99.0 零硬错。LLM PDF 重构（`llm_refine.py` +
  `data_refined/` 哈希缓存）已全量铺开，设计见
  `docs/superpowers/specs/2026-07-02-llm-pdf-refine-design.md`
- **蓝图 P6 军表系统已完成**（2026-07-14，PR #24-#30）：`engines/roster/` 验表（点数+编制
  约束）+ 点评（接模拟器强度评估）+ enhancements 数据层（927 条）+ web 页签，两轮审查修复清零。
  陷阱：points_json 档位解析必须严格 `(\d+)\s*models?` + 纯档优先；装配成功≠有输出
- **P8 网站化四页签 4/4 收官**：聊天 / 图鉴 / 模拟器 / 军表实验室（Next.js + FastAPI，
  契约真源 `answer.ts` + Pydantic camelCase 镜像）
- **剩余**：T4 · P7 阵营技能 DSL 逐条编码 + wiki 全量编译（现仅钛帝国/吞世者 2 阵营）+
  基准扩充（长期滚动）；T5 · Stage 5 部署；T6 · 分支清理。非阻塞遗留：67 个 verify_warn
  页人工核查、军表 PR1c 文本解析、外部源观察项（BSData-11e / Wahapedia 11版 / 黑图书馆）

## 数据事实（2026-07-10 语料重组后）

- `data/` 下 61 个 PDF：11 版英文官方（Core Rules + 26 Faction Pack + Event Companion +
  Terrain）、11 版中文民间译本（6月4日分数=MFM v2.7、6月4日平衡版）、十版 codex 兵牌基底
  （中文为主 + 死亡守望/帝国骑士英文版）；`总规则.zip`（295MB）是原始来源备份，不入库
- 被 11 版整体取代的十版规则类 3 本（总规则/技能速查表/规则注解）在 `archive/10th_rules/`；
  旧版本重复 codex 在 `archive/`（勿回灌）
- PDF 来自多个汉化组（老湿腐/DavidZ/双子星/kasa/官方），版式各异，勿用固定正则解析
- 官方点数以 mfm.warhammer-community.com 实时站为真源（`db_compile mfm --fetch/--check/--apply`），
  2026-07-10 校验 1224/1224 一致。S4 已落账：`db/wh40k.sqlite` 已是 11 版数值真源（Wahapedia 滚更并入
  6 月勘误），`db_compile/fp_errata.py` 外科补真漂移（25 飞机移动 + 3 FW 单位 + 2 武器格 + 插 3 兽人新单位），
  带 from 守卫、挂 restore_authority_layers 防重建丢；CLI `python -m db_compile fp-errata`

## 约定

- API key 一律走环境变量（`DEEPSEEK_API_KEY` 等），不落盘
- `data_refined/` 的页级缓存带 prompt 版本号，改 prompt 后可选择性重跑
- 根目录的 `*.log` / `*.err` / `*.out` / `temp.pdf` 是运行产物，不要提交
