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
- **T4 · P7 阵营技能 DSL 逐条编码已全量收官**（2026-07-24 确认，PR4–PR31）：**28/28 阵营**
  全部编码入 `dsl_payloads/*.json`，每条带 encoded/partial/not_modeled 诚实标记；1907 测试绿。
  编码判据沉淀在 auto-memory `p7-faction-dsl-pilot.md`（阶段门/负关键字门无载体 not_modeled
  等 30+ 条铺量坑）。**wiki 全量编译已完成**（sqlite 驱动 `wiki_engine/from_db.py`，
  25 阵营 1715 单位，f09dacfb，官网一致 by construction）
- **refine 造数已核查修复**（2026-07-24）：verify_warn 逮到 refine 在图片型/被拆分兵牌页
  凭 40K 记忆虚构数值——硬化 `refine_prompt.py`（v1→v2 铁律：源无数值时只输出名字/编制）
  + `scripts/refine_pages_fabricated.py` 重跑 30 页清零，verify_warn 67→37（余 37 纯结构性
  误报，纯造数字=0）。报告 `docs/superpowers/specs/2026-07-24-refine-fabrication-fix.md`
- **T5 · Stage 5 部署已落地**（2026-07-25）：`docker compose up` 起 api+web 两服务，
  镜像只装代码、`opt/`(4.5G)+`local_vector_store/`+`db/`+`wiki/` 全部 `:ro` 挂宿主机，
  端口只绑 127.0.0.1、非 root、torch 走 CPU 源（否则白背 2G nvidia 依赖）、`workers=1`
  （模型缓存在进程内）。新增 `web_api/preflight.py`（启动核对资产，缺卷在日志吼+落
  `/healthz.ready`，防"卷没挂上→全部静默降级"）与 `web_api/ratelimit.py`（两档固定窗口，
  heavy=/chat+/simulate+/roster/critique，XFF 默认不信；限流须挂在 CORS **之前**）。
  1936 测试绿。设计与验收 `docs/superpowers/specs/2026-07-25-stage5-deploy.md`。
  ⚠ **镜像尚未真实构建验证**（本机 Docker Desktop 守护进程未起），验收表最后一行是待办
- **codex 扩成真 wiki 已收官**（2026-07-25，分支 `feat/codex-wiki`，PR-0/1/2/4/5）：
  wiki 从「只有兵牌页」扩到 **7900+ 页**——武器词条索引（46 词条 / 2731 条现役反查，
  `wiki/indexes/keywords.{md,json}`，判据来自 `data/11版40K通用技能速查表.pdf`）、
  分队/战略/增强三类实体页（324/1681/1058，`wiki_engine/entity_pages.py` + `html_md.py`）、
  11 版核心规则全文 24 章 137 节（`wiki/core-rules/sections/`，`core_rules.py`）；
  web `/codex` 加「武器词条」「分队」两个二级页签（`wiki_blocks.py` 把 md 编译成块级契约，
  前端零解析、不引 markdown 库）。**正文一律官方英文**（用户裁决：宁可英文也要与官网一致，
  不叠十版汉化译本），中文只用于名称。2125 测试绿、lint 0 error。
  设计与决策见 `docs/superpowers/plans/2026-07-25-codex-wiki-expansion.md`。
  **三个必知坑**：① `detachments` 表存的是分队**规则名**不是**容器名**（容器名真源在官方
  CSV 的 detachment 列，曾入库丢失；**禁止按 id 邻接反推**）；② 从半结构化文本抽条目
  必须配反向对账（核心规则切章三轮漏切每次都报"成功"）；③ PDF 残留控制字符（0x08）
  会让行尾匹配静默失败
- **GW 官方简体中文层已贯通到 wiki 页**（2026-07-26，分支 `feat/codex-wiki`）：
  官方下载页可切简体中文 → `data/官方中文/` 收 34 个官方 PDF → `db_compile/official_zh.py`
  按**数值指纹**配对出映射（战略 464 / 强化 234 / 分队容器 123，`official_zh_names.json`）
  → `db_compile/official_zh_apply.py` 投影进库（战略 `name_zh` 426→728、强化**新加
  name_zh 列** 0→249、容器中文名进新表 `detachment_names_zh`）→ 重生成 3063 实体页
  （中文名：战略 759→989、增强 381→547、分队 0→123）。权威级别按 wiki 宪法 §6
  「GW 官方中文 > 汉化组 > 社区」，官方顶掉的 P7 人工译名**不删**，降为页面 alias（295 页）。
  CLI `python -m db_compile official-zh --apply [--dry-run]`，已挂进 update 管线与
  restore（排在 fp_rules 之后，否则低权威覆盖高权威且页面上看不出来）。
  **三个坑**：① 分队容器中文名只能走独立表——123 个键撞 `stratagems.detachment` 是
  123/123，撞 `detachments.detachment_name` 只有 63/123，挂那张表会静默丢 60 个；
  ② 落库以行级 `*_by_id` 为准，英文名键表达不了「同一英文名在不同包里不同官方译名」
  （蔑视战甲 / 蔑视甲胄），只能整条丢；③ `db_compile enhancements --apply` 的
  INSERT OR REPLACE 会清空 name_zh/DSL 投影列（已改成报数并提示补跑两条投影命令）
- **核心规则 24 章中文化 + 规则变更清单已完成**（2026-07-26，分支 `feat/codex-wiki`）：
  新增 `wiki_engine/pdf_sections.py`（官方 PDF → 按节号切分，中英共用）、
  `core_rules_zh.py`（官方中文 88 页全译本，156 节）、`changelog.py`（规则变更清单）。
  ① **核心规则页改为中文正文 + 英文原文折叠**：配对键是官方节号，
  `cross_check` 实测中英各 156 节、双向差集为空。这条**跨语言对账**顺带逮出英文侧
  积压的 **19 节缺失**——切分正则漏 6（`## COMMAND RE-ROLL 15.02 (1CP)` 节号后带 CP
  花费，第 15 章 11 条核心计谋只切出 1 条）＋ refine 产物丢节号 13（`1. SELECT WEAPONS
  04.01` 被改写成 `**1. SELECT WEAPONS**:`），后者用英文 PDF 直提兜底。
  ② **规则变更清单** `wiki/changelog/`（index + 28 阵营页）：592 条官方改动，
  其中 **128 条标 🆕 = v1.0→v1.1 增量**——判据是 PDF span 的**红色**（`0xa31418`），
  官方导言写明「初版发布之后所作的修订均以红色高亮显示」，不是靠 diff 两版猜的
  （手上只有 v1.1）。CLI `python -m wiki_engine changelog`。
  wiki 4921→**4950 页**，2234 测试绿，lint 0 error / 593 warning（与基线持平）。
- **剩余**：基准扩充（长期滚动，agent gold v3 现 96/96=100.0 零硬错，#41/#42 为固定波动题）。
  wiki 收尾候选：核心规则章节页与 changelog 接进网页；lint 的 alias-conflicts 占满
  warning 通道（官方中文名铺开后更多），宜聚合成摘要 + 单独重名报告。
  非阻塞遗留：军表 PR1c 文本解析、外部源观察项（BSData-11e / Wahapedia 11版 / 黑图书馆）。
  T6 分支清理已实际完成

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
