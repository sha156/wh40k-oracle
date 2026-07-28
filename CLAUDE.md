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

# 生成物只准由正规命令产出（测试一律写临时目录，跑完 git status 必须干净）
.\.venv\Scripts\python.exe -m wiki_engine keywords          # wiki/indexes/keywords.{md,json}
.\.venv\Scripts\python.exe -m wiki_engine lint              # 0 error 才算过
```

### 重建库后中文层的复现路径（`db/wh40k.sqlite` 是 gitignored，别靠库里现有的东西）

```powershell
.\.venv\Scripts\python.exe -m db_compile build   # 重建后自动跑 restore_authority_layers
```

`build` → `update.restore_authority_layers` → `stage_zh_details` → `blacklibrary.populate_zh_details`，
从**本地缓存** `db_sources/blacklibrary/details.json`（gitignored，刷新走
`scripts/fetch_blacklibrary_details.py`，需网络）灌回 `unit_zh_detail` 与 `units.name_zh`。
2026-07-27 实测：已提交代码 + 当前缓存 → 1135 行（`matched 939 / matched_by_zh 7 / unmatched 131`），
**中文名桥那 8 行一个不少**，所以「库里有、代码里没有」的风险在这一层不存在。
钉死用例 `tests/test_db_compile_zh_coverage.py::TestRealCorpus::test_zh_name_bridge_survives_a_db_rebuild`
（在库的副本上重跑，真库零改动）。

## 架构与技术栈

- `ingest.py`：PDF（`data/`）→ PyMuPDF 提取 → SemanticChunker 分块 → bge-m3 嵌入 → FAISS（`local_vector_store/`）
- `app.py`：Streamlit 界面；检索链 = FAISS + BM25（jieba 中文分词）+ 查询别名扩展（sqlite aliases
  `load_alias_expansions` + 少量硬编码）+ RRF 融合 + **11版规则层保底**（单独按 `layer=rules` 过滤强塞
  最高真源进上下文，`RULES_FLOOR_FETCH_K` 防冷门英文术语跨语饥饿）→ LLM（deepseek-chat / glm-4-flash）。
  FlashRank 重排默认关闭（`USE_RERANKER=False`）：实测 ms-marco 系列（含 MultiBERT）对中文重排差于 RRF 顺序
- `hf_embeddings_compat.py`：HuggingFaceEmbeddings 兼容层
- 模型缓存在 `opt/`（bge-m3、ms-marco-MiniLM-L-12-v2 等），CPU 推理
- 嵌入走 hf-mirror 镜像 + Clash 代理（127.0.0.1:7897），相关环境变量在 ingest.py 顶部设置

## 当前进度（2026-07-28 更新）

**✅ 词条解释层这条线已全部并入 main**（PR #67 + #68，main `dc5248a6`）：
pytest **2398**、基准 **115 题 100.0 零硬错**、`mfm --check` 1319/1319 过期 0、
wiki lint 0 error / 1 warning、前端 lint 0 error。
**收官检查点与冷启动交接见 `docs/superpowers/plans/2026-07-28-codex-wiki-line-checkpoint.md`**
（含四种互斥诚实性错法的锚点题、46 条点数 apply 的八步流程、8 份排查报告索引、剩余非阻塞项）。

未完成任务全景见 `docs/superpowers/plans/2026-07-12-remaining-tasks.md`
（⚠️ 其中「Titan Legions 7 单位缺兵牌」已于 2026-07-27 证伪，勿再照此派活）。

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
- **核心规则与变更清单已接进网页**（2026-07-26，分支 `feat/codex-wiki`）：图鉴从三页签扩到
  **五页签**（单位 / 武器词条 / 分队 / 核心规则 / 规则变更）。新增 `web_api/core_rules_browse.py`
  与 `changelog_browse.py` + 四条只读路由 `/codex/rules[/{slug}]`、`/codex/changelog[/{slug}]`；
  块级契约加 **`details` 可嵌套块**（核心规则每节「中文正文 + 官方英文原文折叠」）与行内
  **`em`**。变更清单首页会把 index 一览表与 28 个阵营页**逐条对账**（条目数 / 新增数 /
  页是否都在），差额 503 点名——592 与 128 是这页的头条断言。2286 测试绿、lint 0 error、
  next build 通过、浏览器目检两页签（含折叠展开、明细页计数）。**两个坑**：
  ① 按 `## ` 切小节必须先认 `<details>` 深度——英文原文自带 `## ` 标题 57 处，
  不认就把折叠腰斩、24 章切出 213 节而非 156，且折叠个数一个不少（计数骗人）；
  ② 单星号斜体只能按「整行成对」处理，通用行内配对会误吃 `5*` 脚注与 PDF 残留落单星号。
- **兵牌中文技能覆盖已对账收口**（2026-07-27）：黑图缓存刷到 07-27（源侧 +2 条记录、
  43 条正文改写、**0 条从空变成有**），补中文名桥（英文名只差单复数/头衔前缀时靠中文名接）。
  绝对数：`unit_zh_detail` 1125→**1129** 行、units 缺行 590→**586**、空 `abilities_json`
  **16→16**（已回黑图 live 逐个复核，源里就是空的）。新增 `python -m db_compile zh-coverage`
  把 units 全表无遗漏归 5 类（和恒等于 1715）。补不到的一律**逐字退回英文**，
  报告与完整名单见 `docs/superpowers/specs/2026-07-27-zh-abilities-coverage.md`。
  顺带逮到 `zh_weapons` 真 bug：库内射程写 `Melee`、黑图写「近战」，数值指纹首位
  永远对不上 → **近战 Pass A 全盘失效**，一直靠「两边各只剩一把」的 Pass B 兜底
  （所以一把近战的单位全对、两把以上整组留英文，指标看着很健康）。归一后指纹配对
  4085→**5341**，现役武器中文 4718/4721→**4721/4721**
- **lint warning 通道已疏通 + 重复单位已排查 + 基准扩到 104 题**（2026-07-27）：
  ① alias-conflicts 由 **593 条逐条 warning 聚合成 1 条摘要**（`0 error / 1 warning / 4 info`），
  完整名单进生成物 `wiki/alias-conflicts.md`（593 组 / 901 实体）——**是聚合不是降级**，
  严重度仍是 warning、一组都没少查；配了「50 组重名 + 1 条真 warning」的合成用例钉住
  「真问题不再被淹没」。同时**去掉 `lint-report.md` 的生成时间戳**（内容不变则字节不变），
  消除「跑一次 lint 就脏一次工作区」的假 diff。
  ② `python -m db_compile zh-coverage --dup`（`db_compile/dup_units.py`，只读 `mode=ro`）：
  库内 **11 组 22 行**疑似重复，成因是**上游 Wahapedia 按「书」建模**（附册重印主书条目，
  link 带 `-1` 消歧后缀），只有 `Hellflayer(s)` 那组是新旧版共存；**一行数据都没改**，
  报告 `docs/superpowers/specs/2026-07-27-duplicate-units-audit.md`。
  ③ `qa_gold.json` 96→**104 题**（v3.2）：新增 #101-#108 覆盖词条含义/词条参数/技能正文
  内嵌词条/诚实性，8 题全 ✅（连跑两轮一致），gold 出处逐条写在各题 `note`。
  ⚠️ #41/#63 相对 07-24 基线掉分**经 revert 对照跑证实与本轮无关**（共有 96 题逐题 verdict
  差异为 0），是本分支更早提交（黑图中文层刷新改 `unit_zh_detail` → agent 路由变化）造成的
  既有漂移，详见 `benchmarks/v3_edition11/README.md`
- **#63 既有漂移已定因并修复**（2026-07-27）：根因不在数据层而是 `agent/tools.py` 里
  **两条各自合理的接线凑成死胡同**——`get_entity` 多候选时 note 原文「需向用户反问确认」
  指挥模型把问题退回用户，而 `loop._EMPTY_CHECKS` 按评审 #25 把 ambiguous 判为非空、
  经典链兜底不触发 → **不降级也不作答**，检索源 0 个判 ❌。官方中文名铺开后
  「坦克指挥官」才开始匹配到 3 个候选，把这条死路走通。修法只改 note 措辞
  （指挥模型逐个候选重查，反问降级为兜底），不动 `_EMPTY_CHECKS`。
  104 题逐题对比**仅 #63 变化（❌→✅），其余 103 题零变动**，98.1→**99.0 零硬错**；
  护栏 `tests/test_agent_tools.py::TestGetEntity` 两条（已验证改回旧措辞会红）。
  结果 `benchmarks/v3_edition11/qa_agent_results_ambiguous_note_fix.json`
- **泰坦军团「缺兵牌」查明是伪缺口 + MFM 千分位静默丢行已修**（2026-07-27）：
  泰坦军团**一共就 4 个单位**（官网 MFM 4 条、`data/Faction Pack Adeptus Titanicus.pdf`
  10 页里 4 张兵牌、库里 4 行齐全），逐字段核对 PDF **全对**（属性/36 条武器/技能/
  受损/装备/点数），图鉴页 Playwright 目检 4/4 非空壳，**本轮零数据改动、零新建兵牌**。
  传闻的「7 个」实际是**被解析器静默丢掉的行数**：官网四位数分数写作 `2,200 pts`，
  `db_compile/mfm.py` 的 `(\d+) pts` 对千分位逗号零容忍且不报错 → 库内 7 个 ≥1000 分
  单位（4 泰坦 + 灵族幽魂/幻影泰坦 + 钛族 Manta）**从未被官方点数校验过**。
  已修正则 + 加与行数正交的 `count_unit_headers`「有表头却 0 行」断裂探测
  （`MfmParseBroken`，不重试、不冒充网络失败、写盘前 raise）。
  `mfm --check` 1236→**1243 可比 / 1243 一致 / 过期 0**（+7 全对）。
  混沌泰坦 4 个**建不了也不该建**：PDF p2 `TITANICUS TRAITORIS` 明示复用同一张兵牌
  换两个关键词、用同一份点数。报告
  `docs/superpowers/specs/2026-07-27-titan-legions-datasheet-audit.md`。
  **点名遗留**：`Frame` 关键词全库缺失（19 个 FP + Core Rules 共 318 处，库内 0 个单位有）
  ——是 Wahapedia 镜像的系统性丢失，只补 4 个泰坦会让全库口径分裂，需独立做全库反灌对账
- **MFM 全站重抓与点数校验已收官**（2026-07-27）：修完千分位正则后做了一次**全站重抓**
  （非上一轮的 `--slug` 定点补抓），30 阵营逐个行数对账**零差额**（1716→1716，逐条
  `(单位,档位,模型数)` 键新增/消失/变价皆 0），`count_unit_headers()` 独立交叉验证
  **30/30 页表头数 = 去重单位数**，明星单位证伪法全部命中。`mfm --check`
  **1243 可比 / 1243 一致 / 过期 0 / db_unparsed 0**；那 7 个 ≥1000 分单位
  （4 泰坦 + 灵族幽魂/幻影泰坦 + 钛族 Manta）**7/7 与官网一致**——数值本来就对，
  静默丢行的代价是「对不对无人知晓」。`mfm_only` 5 个全有已知解释（4 混沌泰坦共用兵牌
  + Eradicator 变体装配名）。**未 apply**：差异为 0，库副本试跑证明
  `units_updated=0`、点数变化 0 条，apply 唯一效果是给那 7 个补 `points_json["mfm"]`
  溯源块——而该键在 `keyword_index.py` / `zh_weapons.py` / `web_api/codex.py` /
  `dup_units.py` **四处被当「现役」判据**，补它会翻转现役口径并需 wiki 重生成，超出本轮。
  报告 `docs/superpowers/specs/2026-07-27-mfm-refetch-points-verification.md`。
  **顺带查出同一失效模式的第二处实例**（`_KEEP_SECTIONS` 白名单太窄，漏掉含基里曼的
  子阵营小节）——**已于同日修完，见下条**
- **MFM `_KEEP_SECTIONS` 覆盖缺口已修**（2026-07-27）：30 页**全部** h3 小节逐个做
  数据判定（不靠小节名猜），改法是删掉整段白名单、换成**逐单位可自解释规则**——
  「主小节（UNITS/FORTIFICATIONS）的行全收；其余小节的行**只在该单位没被主小节
  定过价时**才收」。主小节已有 ⇒ 第二套价（`INQUISITOR` 55/65）丢；主小节没有 ⇒
  该阵营列在子标题下的自己的单位（基里曼）收。被排除的 502 表头判成：
  **纳入 60**（SM 战团英雄 19 + HARLEQUINS 8 + YNNARI 11 + 四个 LEGIONS 小节 22），
  **仍排除 442**（战团页整段重印 399，与主小节 **399/399 全重叠**；imperial-agents
  条件价 29，**29/29 全重叠**；DETACHMENTS 14，**0 个分数行**）。
  ⚠️ **四个 LEGIONS 小节的判定推翻了直觉**：那 22 个单位全都在 `chaos-daemons` 页
  也有价，单看像盟友借调价——但**库把它们建模成按阵营各自独立的行**（`great unclean
  one` 同时有 CD 行和 DG 行），DG 那行的权威价就在 death-guard 页。比对结果印证：
  **CD 行全对、DG/TS/WE/EC 行 20 条过期**（有人管的行是对的，没人管的行烂掉了）。
  `mfm --check` **1243/1243/过期 0 → 1319 可比 / 1273 一致 (96.5%) / 过期 46**，
  `mfm_only` 仍 5 无新增、`db_unparsed` 0；**旧 1243 条一条没退化**
  （新增 76 = 新一致 30 + 新过期 46，46 条全属本轮纳入名单）。
  46 条过期含**基里曼 340→355**、Suboden Khan 115→90、Lord of Change 285→320 等，
  官网原文多带 ▲/▼ 标记＝本版刚改价、Wahapedia 镜像没跟上。
  顺带把 `count_unit_headers()` 改成**不走小节筛选**（原先与被校验对象共享前提，
  对整段误伤全无感知）。缓存 1716→2514 行（战团差异价现在真的留在 json 里了，
  比对时由 `_rows_by_faction` 通用页优先丢弃）。2359 测试绿（+6 新用例，
  对旧实现跑 4 条真会红）。报告
  `docs/superpowers/specs/2026-07-27-mfm-section-coverage-fix.md`。
  **未 apply**：库副本逐字段试跑显示 apply 会改 46 条档位点数 + 46 个顶层 points
  （含 `AE/Troupe 580→85` 这类 Wahapedia 累加和→基准档最小值的大幅语义修正）
  **+ 给 67 个单位新写 `points_json["mfm"]`＝翻转现役口径**，需连 wiki 重生成一起做；
  副本上已验证 apply 后收敛到 **1319/1319/过期 0**，路径通，留给独立一轮
- **#109「工具查不到→模型编否定性断言」硬错已修**（2026-07-27）：`calc_points` 底层是纯
  `units.id` 查表，四个泰坦中文名全空 → 又不在 `loop._EMPTY_CHECKS` 里（不判空不降级）
  → 模型把**查询失败**升级成**事实断言**「泰坦军团是独立桌游、不是 40K 阵营、无官方点数」
  （而库＝官网，1100/2200/2600/3500 都在）。三层修法：① **根本修法**——名字解析加在
  `agent/tools.py::calc_points` 这层包装，底层 `db_compile/calc_points.py` 一行没动
  （军表/web 按 canonical id 直调的约定保持），只对返回「未找到该 unit id」的走
  `entity_resolver` 重查，**纯 id 入参行为逐字节不变**，顺带解决多单位漏项；
  ② 仍解析不到时 note 直说「查不到 ≠ 不存在」并指路重查、明令禁止否定性断言（因果写进注释，
  同 #63 的 `1efb6e5c` 做法）；③ `_EMPTY_CHECKS` 加 `calc_points`（**全部**没解析到才判空，
  「查到了但没点数」是诚实答案不许被吞）+ `_NEXT_STEP_CONTRACT` 加通用铁律防其他工具复发。
  基准 95.6→**96.5**，113 题**仅 #109（❌→✅）其余 112 题零变动**，两轮稳定；2365 测试绿
  （+6 用例，stash 掉实现后 5 failed 验证过真会红）。报告
  `docs/superpowers/specs/2026-07-27-calc-points-negative-assertion-fix.md`。
  **仍红的 #113/#114/#115 是库内点数过期，等 `mfm --apply` 拍板后转绿，未碰**
- **「模糊匹配静默命中不相干单位」已修**（2026-07-27）：`entity_resolver("Flamestorm Drake")`
  （一个**不存在**的名字）以 difflib ratio 0.606 命中 `Firestorm Redoubt` 并报 fuzzy +
  canonical_id，`get_entity` 于是 **found=True** 地端回另一张真实兵牌——比 #63/#109/#118
  都隐蔽，因为**每一层都是成功路径**（数据真实、渲染正常）。**先量分布再定判据**
  （2590 条查询三类样本）：两类命中的 ratio 区间**重叠**（真纠错 min 0.750 / 造名 max 0.846），
  且**调高 cutoff 会让情况变坏**——滤掉竞争命中把「多命中 ambiguous(不给 id)」变成
  「单命中 fuzzy(给 id)」，造名被接受 56→79。改用**绝对字符编辑距离 ≤2**
  （真纠错 max 2 vs 造名 median 6）**＋「查询串是命中名子串」单向豁免**（简称；
  只按距离切会把 #63「坦克指挥官」的两个正主滤掉、翻成 fuzzy 报 Commander Farsight）。
  实测每轴不劣于改动前：造名给出 id **57→3**、真纠错单命中 490→1368、简称误配 102→58。
  工具边界透出 `suggestions` 并把「猜测」说死 + 被接受的 fuzzy **必须声明**。
  ⚠️ `_EMPTY_CHECKS` 只放行 `entity_resolver`/`get_entity`，**`get_datasheet` 故意不放行**
  ——实测放行会让 #4/#62 当场 ✅→❌（真实单位、名字不在结构库索引里，答案靠经典链从 PDF 捞，
  即注释里点名的「回归 7 题」防线）：**结构库 ≠ 全部语料**。新增基准 #119（qa_gold v3.5，
  既有 114 题逐字段零改动），四题锚点 #63/#109/#118/#119 两轮全 ✅，2391 测试绿。
  报告 `docs/superpowers/specs/2026-07-27-fuzzy-silent-mismatch-fix.md`
- **中文名桥可复现性已固化 + 测试不再写仓库产物**（2026-07-27）：① 上一轮补进库的两个中文名
  （死神军阴谋团武士 / 文崔斯连长）查明**不依赖任何未提交改动**——已提交代码 + 本地
  `details.json` 缓存重跑 `populate_zh_details` 稳定得到 1135 行、6 个目标单位全在
  （`db_compile build` 经 `restore_authority_layers` 走的就是这条，复现命令见上「运行方式」）；
  `1129→1135` 变的是**缓存**不是代码。哪 6 个是新的有**两条独立证据**对上：条目数算术
  （新 6 行 16 条 + 旧 2 行 5 条 = 桥共 21）与 HEAD 的 wiki 页 grep（只有克拉维克·莫恩、
  装备重型武器的天灾查得到）分界线完全重合。护栏 `test_zh_name_bridge_survives_a_db_rebuild`
  在库副本上重跑，真库零改动。② `EXPECTED_ZH_ITEMS` 3280→**3296**，注释逐单位写明来源。
  ③ `test_generate_index_is_complete_and_linked` 从前直接写 `wiki/indexes/`——跑一次 pytest
  工作区就脏、下一轮 gnhf "Working tree is not clean" 秒退；`keyword_index.generate` 加
  `out_root`（**读真 wiki 判断链、写临时目录**，默认相等⇒正常生成逐字节不变），
  产物改由正规命令 `python -m wiki_engine keywords` 重生成。2392 测试绿、两处 lint 0 error、
  全量 pytest 后 git status 干净。报告
  `docs/superpowers/specs/2026-07-27-zh-bridge-reproducibility-and-test-artifacts.md`
- **#113/#117「数据来源路由」已修，基准两轮 99.1 / 100.0 零硬错**（2026-07-27）：表象是
  「答案来自 PDF 而非结构库」，但**根因不是路由偏好选错工具**——模型两次都第一时间查了
  结构库，是**查空后被 `loop._EMPTY_CHECKS` 降级到经典链（纯 PDF 检索）**送过去的。
  ⚠️ 诊断关键：`meta.tool_calls` 末尾那个 `rag_search` **不是模型调的**，是 `loop._fallback`
  自己追加的（`loop.py:245`）——「序列里有 rag_search」是**降级的指纹**，只看工具名会把
  「模型偏好查 PDF」这个错结论坐实，必须记入参与返回摘要。
  ① **#113**：`get_datasheet("罗伯特·基里曼")` 一步就降级——库内 `_zh_to_id` 存的是
  `罗伯特.基里曼`（**半角句点**；实测 30 个键用 `·` / 6 个用 `.`，**库内自己就不统一**），
  写法不同 → 只判 `fuzzy`，而 `datasheet.find_datasheet` 出于防错配**只信 exact** →
  数值权威路径整条查不到 → 降级 → 民间译本 PDF 的冻结旧值 320（官方 355）。
  修在**归一化层**而非放宽 fuzzy：`entity_resolver` 加 `_sep_normalized()` + `_zh_norm_to_id`
  （冲突键记 None 拒绝猜），命中判 **exact**（判 fuzzy 等于没修）；`FUZZY_MAX_EDITS`
  那道防线一个字节没动。实测 71 个归一键 / **0 冲突 / 0 既有键退化** / 新增 34 个可解析变体。
  ② **#117**：`get_entity(战将泰坦)` **已经成功**，第二步 `get_keyword_definition("Frame")`
  查空触发降级，**把第一步的成果一并丢弃**，只剩 PDF 片段 → 照 Faction Pack 原文答
  「Frame 在库中可查」（库内实为 6 个关键词无 Frame）。修法：该工具移出 `_EMPTY_CHECKS`
  （判据沿用既有区分——**纯映射工具**的「没查到」本身即实质答案，**数据查表工具**
  `get_datasheet` 仍**不**放行，那是「回归 7 题」防线）+ `_KEYWORD_NOT_FOUND_NOTE`
  双向禁止（不许断言关键词不存在，也不许把 PDF 内容说成「库里查得到」）。
  **未削弱 `rag_search`**：仍参与 33/32 题（基线 35，减少的正是不再需要降级的那几题）。
  两轮逐题对比**零退化、差异全为改善**（基线→r2 仅 #41/#42 已知波动 + #113/#117 转 ✅），
  四题锚点 #63/#109/#118/#119 全程 ✅，**#117 两轮均 ✅ 不再摆动**；2398 测试绿
  （+6 用例，stash 掉源文件后 4 条真会红）、两处 lint 0 error。报告
  `docs/superpowers/specs/2026-07-27-data-source-routing-fix.md`
- **剩余**：上述 6 个单位的 wiki **兵牌页**尚未按新中文层重生成（词条索引已跟上，lint 0 error 不阻塞）。
  #41 兽人小子 ⚠️ 漏项（非硬错）——`get_entity` 现在 exact 命中致 agent 走兵牌查表
  不再检索规则书，改它要动「查表 vs 检索」路由偏好，波及面大。基准扩充长期滚动。
  wiki 收尾候选：武器词条页的「规则页 NN.NN · 正文页待上线」现在可以
  真接成到核心规则章节页的链接了。
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
