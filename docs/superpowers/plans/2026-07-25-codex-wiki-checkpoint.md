# 检查点：codex 扩成真 wiki（2026-07-25 收官，2026-07-26 官方中文层续）

> 这份文件是给**下一次会话**看的：当前处在哪、怎么验、还剩什么、从哪接着做。
> 设计与决策记录见同目录 `2026-07-25-codex-wiki-expansion.md`（蓝图），本文只讲状态。

## 1. 当前状态

| 项 | 值 |
|---|---|
| 分支 | `feat/codex-wiki`（已推 origin，**未合 main**） |
| HEAD | 2026-07-26 核心规则中文化 + 规则变更清单 |
| 测试 | **2234 passed**（本线开工前基线 1968；核心规则中文化 +22、变更清单 +13） |
| wiki lint | **0 error** / 593 warning（全是 alias-conflicts）/ 4 info |
| wiki 规模 | **4950 页**（开工前 1828） |
| 中文名覆盖 | 战略 989/1681、增强 547/1058、分队容器 123/324（2026-07-26 官方中文层） |
| 核心规则 | 24 章 **156 节**（原 137，补回 19 节），中文正文 + 英文折叠 |
| 规则变更清单 | **592 条**官方改动，其中 **128 条**为 v1.0→v1.1 增量 |

本线 6 个提交，按依赖顺序：

```
198f2e7f  PR-0 地基（穿越守卫 / USR 错译 / 语料层级 / 宪法登记）
926465cd  PR-1 武器词条索引 + 别名大修
0f09ae35  PR-2 分队 / 战略 / 增强三类实体页 + 数据层修复
b25b3780  PR-4 web /codex「分队」页签 + 块级契约
d639995b  PR-5 核心规则全文 24 章 137 节
1dd8b6b3  收官归档（CLAUDE.md 进度 + 蓝图状态）
0dde9c12  本检查点
ddd442ee  GW 官方简体中文语料落地（34 个 PDF）+ 全库译名改用官方
53f35a20  官方中文实体名指纹配对（只出映射文件，不写库）
（本次）  官方中文名落库 + 3063 实体页重生成
```
（PR-3「十版汉化正文叠加」按用户裁决取消，蓝图里保留了"为什么不做"。）

## 2. 一条命令复现全部产物

所有 wiki 内容都是**确定性生成**的，删了能重建：

```powershell
# 中文名是从库里读的：这一步不跑，实体页会退回英文/旧译名，而生成器照样报"成功写 3063 页"
.\.venv\Scripts\python.exe -m db_compile official-zh --apply   # 官方中文名 → 库（秒级、离线）

.\.venv\Scripts\python.exe -m wiki_engine keywords     # 词条索引 → indexes/keywords.{md,json}
.\.venv\Scripts\python.exe -m wiki_engine entities     # 分队/战略/增强 3063 页
.\.venv\Scripts\python.exe -m wiki_engine core-rules   # 核心规则 24 章（中文正文 + 英文折叠）
.\.venv\Scripts\python.exe -m wiki_engine changelog    # 规则变更清单 index + 28 阵营页
.\.venv\Scripts\python.exe -m wiki_engine crosslinks   # 注入交叉链接（⚠ 4900 页约 15 分钟）
.\.venv\Scripts\python.exe -m wiki_engine build        # 重建 index.md + 阵营索引
.\.venv\Scripts\python.exe -m wiki_engine lint         # 体检，必须 0 error
```

验收基线：`pytest -q` ≥ **2234 passed**；lint **0 error**；
`find wiki -name '*.md' | wc -l` = **4950**（units 1715 / stratagems 1681 /
enhancements 1058 / detachments 324 / core-rules 概念页 82 / sections 24 /
changelog 29）。

## 3. 产物路径

| 内容 | 生成器 | 产物 |
|---|---|---|
| 武器词条索引 + 反查 | `wiki_engine/keyword_index.py` | `wiki/indexes/keywords.md`（人读）+ `.json`（web 层数据源） |
| HTML → Markdown | `wiki_engine/html_md.py` | —（被下面两个复用） |
| 分队/战略/增强 | `wiki_engine/entity_pages.py` | `wiki/factions/<阵营>/{detachments,stratagems,enhancements}/`、`wiki/core-rules/stratagems/`（28 条核心战略） |
| 核心规则全文（中英） | `wiki_engine/core_rules.py` + `core_rules_zh.py` + `pdf_sections.py` | `wiki/core-rules/sections/<NN>-<slug>.md` |
| 规则变更清单 | `wiki_engine/changelog.py` | `wiki/changelog/index.md` + `changelog/factions/<slug>.md` |
| web 块级渲染 | `web_api/wiki_blocks.py` + `wiki_browse.py` | 路由 `/codex/factions/{fid}/detachments[/{slug}]` |
| web 词条 | `web_api/keywords.py` | 路由 `/codex/keywords[/{slug}]` |
| 前端 | `web/src/components/codex/{KeywordIndex,DetachmentBrowser,Blocks}.tsx` | `/codex` 三个二级页签 |

## 4. 还剩什么（全部非阻塞）

1. **核心规则章节页与规则变更清单都没接进网页**。PR-4 的块级渲染器（`wiki_blocks.py`）
   已经通用，加 `/codex/rules/{chapter}` 与 `/codex/changelog` 两条路由 + 前端页签即可，
   是最短的一块收尾。注意核心规则页正文里有 `<details>` 折叠块，
   块级契约要么支持它、要么把中英拆成两个块。
2. **lint 的 593 条 alias-conflicts 占满了整个 warning 通道**（100%；官方中文名铺开后
   由 553 涨到 593，新增的 36 条全是同一条战略在多个阵营各有一页、中文名自然重名）。
   基本不可行动。建议聚合成 1 条摘要 warning + 单出一份重名报告，
   否则会训练人忽略 lint——项目已有「误报致人不再看」的教训。
3. **64 条 fp11e 分队 + 200 条 fp11e 战略缺容器名 / type**。
   这些是 Faction Pack 新分队，Wahapedia 无源，只能人工补进
   `db_compile/fp_rules_patches.json` 的 inserts（白名单已开好）。
   **禁止**按 id 前缀去撞它们的战略行——那是被明确否掉的推断法。
4. ~~**分队中文名覆盖 0/324**~~ **已办（2026-07-26）**：GW 官方简体中文包按数值指纹
   配对 → 落库 → 重生成实体页。现覆盖 **分队 123/324、战略 989/1681、增强 547/1058**；
   官方顶掉的 P7 人工译名降为页面 alias（295 页）。上限是结构性的：GW 免费发的是
   阵营包补充（只含新增分遣队），codex 正文的战略/强化不白送——剩下的仍只能人工译，
   且必须按 11 版 FP。落库层 `db_compile/official_zh_apply.py`，坑见其顶注。
5. **新页面未进 FAISS**。`ingest.py --rebuild` 没跑，检索侧零影响；
   如果要让规则问答检索到这些页，需另行 ingest（注意：wiki 是 L2 层，
   FAISS 索引的是 L0/L1 的 PDF，两者是不同的层，改动前先想清楚要不要混）。

## 4b. 官方中文这条线的三件——**已全部完成**（2026-07-26）

第 1 件（映射落库 + 重生成实体页）完成于 `609be102`；第 2、3 件本轮完成。

### 第 2 件 · 核心规则 24 章中文化 ✅

`wiki/core-rules/sections/` 24 章现在是**中文正文 + 英文原文折叠**（`<details>`）。
中文来自官方 88 页全译本，与「正文一律官方英文」的裁决不冲突——那条拒的是**十版汉化组**
译本，这份是 **GW 官方 11 版中文**，同档权威。

新增两个模块：

| 模块 | 职责 |
|---|---|
| `wiki_engine/pdf_sections.py` | 官方 PDF → 按 `NN.NN` 节号切分，中英共用；侧边栏剥离、分栏、跨行标题 |
| `wiki_engine/core_rules_zh.py` | 中文 88 页 → 156 节 + 中文目录 24 章；`format_zh_text` 把 PDF 折行还原成段落 |

**跨语言对账逮出了英文侧积压的 19 节缺失**。中英两版是同一套官方编号，
`cross_check_report()` 要求两侧节号集合完全相等（实测 156 = 156、双向差集空）。
这条对账不依赖任何单侧的排版假设，因此发现了 `unextracted_hints()` **完全无感**的两类缺失：

- **切分正则漏 6 节**：`## COMMAND RE-ROLL 15.02 (1CP)` 节号后还挂着 CP 花费，
  而 `_SECTION` 与 `_SECTION_HINT` 都要求「节号在行尾」——**探测器与被测正则共用同一条
  假设，一起瞎**。第 15 章 11 条核心计谋当时只切出 1 条。
- **refine 产物丢节号 13 节**：`1. SELECT WEAPONS 04.01` 被 refine 改写成
  `**1. SELECT WEAPONS**:`，节号没了就配不上中文。这 13 节的英文改用**英文 PDF 直提**兜底
  （`merge_bilingual` 里标 `en_from_pdf`，页面上注明）。

### 第 3 件 · 规则变更清单 ✅

`wiki_engine/changelog.py` → `wiki/changelog/`（index + 28 个阵营页），
CLI `python -m wiki_engine changelog`。**592 条官方改动，其中 128 条标 🆕**。

真源是每个阵营包自带的「规则更新」章节，逐条照抄、不作推断。
**v1.1 增量的判据是 PDF span 的红色**（`0xa31418`）——官方导言写明「凡是在本阵营包初版
发布之后所作的修订，均将以红色高亮显示」。手上只有 v1.1 一版、没有 v1.0 可 diff，
红色是唯一的一手证据。版式判据全部来自 PDF 自身的字号/字体/字色，不靠正则猜标题。

口径要分清：本页收的是官方**文字**改动；兵牌数值与规则文本的 10→11 漂移是另一条线，
早已落在 `db_compile/fp_errata_patches.json` 与 `fp_rules_patches.json`，两者不要混读。
（交接文档提到的「CP 两侧皆知 477 条中有 2 条不等」属于后者的口径，未并入本清单。）

## 5. 下次动这块之前必须知道的（原三件 + 中文化踩出来的四条）

### 中文 PDF 直提这条线（2026-07-26 新增）

4. **分栏必须按 x0 聚类，不能按页宽等分**。第 16 页侧边栏在 x0≈107、正文在 x0≈187，
   页宽 454 等分的分界是 227，两者都落进左半列，按 y 一排就把侧边栏逐行插进了正文。
5. **「侧边栏」的判据是栏宽占页宽的比例，基准不能取最宽栏**。计谋页是双栏卡片、
   两栏都是正文；而第 57 页的页脚横幅横跨整页 323pt，取它当基准会让 176pt 的
   计谋正文栏只剩 0.55 被判成侧栏——**29 个小节的正文整段跑进侧边栏，页面上只剩标题**。
6. **页眉页脚只能按长度滤，不能按页边位置滤**。计谋卡片标题在 y=29.8、页码在 y=28.3，
   相差 1.5pt，几何上分不开；按 6% 页高划页眉带会连着切掉 9 个真小节。
7. **找小节标题前要先遮蔽侧边栏内容**。侧栏里的「另请参见」整列都是 `▪[额外攻击] 24.11`
   这样的节号引用，被版式折行的第二行不带项目符号、长得和真标题一模一样——
   `3.结算攻击 04.03` 的正文范围因此被截断在它自己的侧边栏里，**整节正文变成空字符串**，
   而且中英两版一起空、对账也发现不了。

### 原有三件

1. **`detachments` 表存的是「分队规则名」不是「分队容器名」**。容器名的真源是官方
   `Detachment_abilities.csv` 的 `detachment` 列（已恢复成 `detachment_name` 列）。
   **禁止按 id 邻接反推归属**——实测四个样本错一个（Pactbound Zealots 的规则
   被认成 Combat Doctrines），一页写着错误分队规则的 wiki 比没有这页糟得多。
2. **从半结构化文本抽条目，必须配一条反向对账**。核心规则切章三轮漏切
   （粗体包裹标题 / 粗体在序号外 / 行尾控制字符），**每次生成器都报"成功写 24 页"、
   页面打开也完整**。探测器留在 `core_rules.py::unextracted_hints()`，别删。
3. **PDF 提取残留的控制字符会让匹配静默失败**。`## [CLOSE-QUARTERS] 24.07\x08`
   行尾那个退格符让第 24 章少了 10 条词条。任何 PDF/OCR 来源的文本，解析前先清控制字符。

## 6. 用户裁决（不要当成待办捡起来）

- **三类实体页与规则章节页的正文一律官方英文**，中文只用于名称。
  技术上有零 LLM 的中文化路径（`data_refined/` 32 个汉化目录、814 个结构化中文战略块、
  612 块可按英文名匹配），但那是**十版**译本，与 11 版有漂移（FP added_11e 200 /
  removed_11e 47）。用户明确选择「宁可英文也要与官网一致」。
- **FAQ 本轮不做**（`data/archive/总规faq6月20日中文.pdf` 的版本核查一并搁置）。
