# 检查点：codex 扩成真 wiki（2026-07-25 收官）

> 这份文件是给**下一次会话**看的：当前处在哪、怎么验、还剩什么、从哪接着做。
> 设计与决策记录见同目录 `2026-07-25-codex-wiki-expansion.md`（蓝图），本文只讲状态。

## 1. 当前状态

| 项 | 值 |
|---|---|
| 分支 | `feat/codex-wiki`（已推 origin，**未合 main**；main 落后 16 个提交） |
| HEAD | `1dd8b6b3` |
| 工作区 | 干净（0 脏文件、0 未推送） |
| 测试 | **2125 passed**（本线开工前基线 1968） |
| wiki lint | **0 error** / 553 warning（全是 alias-conflicts）/ 4 info |
| wiki 规模 | **4917 页**（开工前 1828） |

本线 6 个提交，按依赖顺序：

```
198f2e7f  PR-0 地基（穿越守卫 / USR 错译 / 语料层级 / 宪法登记）
926465cd  PR-1 武器词条索引 + 别名大修
0f09ae35  PR-2 分队 / 战略 / 增强三类实体页 + 数据层修复
b25b3780  PR-4 web /codex「分队」页签 + 块级契约
d639995b  PR-5 核心规则全文 24 章 137 节
1dd8b6b3  收官归档（CLAUDE.md 进度 + 蓝图状态）
```
（PR-3「十版汉化正文叠加」按用户裁决取消，蓝图里保留了"为什么不做"。）

## 2. 一条命令复现全部产物

所有 wiki 内容都是**确定性生成**的，删了能重建：

```powershell
.\.venv\Scripts\python.exe -m wiki_engine keywords     # 词条索引 → indexes/keywords.{md,json}
.\.venv\Scripts\python.exe -m wiki_engine entities     # 分队/战略/增强 3063 页
.\.venv\Scripts\python.exe -m wiki_engine core-rules   # 核心规则 24 章
.\.venv\Scripts\python.exe -m wiki_engine crosslinks   # 注入交叉链接（⚠ 4900 页约 15 分钟）
.\.venv\Scripts\python.exe -m wiki_engine build        # 重建 index.md + 阵营索引
.\.venv\Scripts\python.exe -m wiki_engine lint         # 体检，必须 0 error
```

验收基线：`pytest -q` ≥ **2125 passed**；lint **0 error**；
`find wiki -name '*.md' | wc -l` = **4917**（units 1715 / stratagems 1681 /
enhancements 1058 / detachments 324 / core-rules 概念页 82 / sections 24）。

## 3. 产物路径

| 内容 | 生成器 | 产物 |
|---|---|---|
| 武器词条索引 + 反查 | `wiki_engine/keyword_index.py` | `wiki/indexes/keywords.md`（人读）+ `.json`（web 层数据源） |
| HTML → Markdown | `wiki_engine/html_md.py` | —（被下面两个复用） |
| 分队/战略/增强 | `wiki_engine/entity_pages.py` | `wiki/factions/<阵营>/{detachments,stratagems,enhancements}/`、`wiki/core-rules/stratagems/`（28 条核心战略） |
| 核心规则全文 | `wiki_engine/core_rules.py` | `wiki/core-rules/sections/<NN>-<slug>.md` |
| web 块级渲染 | `web_api/wiki_blocks.py` + `wiki_browse.py` | 路由 `/codex/factions/{fid}/detachments[/{slug}]` |
| web 词条 | `web_api/keywords.py` | 路由 `/codex/keywords[/{slug}]` |
| 前端 | `web/src/components/codex/{KeywordIndex,DetachmentBrowser,Blocks}.tsx` | `/codex` 三个二级页签 |

## 4. 还剩什么（全部非阻塞）

1. **核心规则章节页没接进网页**。PR-4 的块级渲染器（`wiki_blocks.py`）已经通用，
   加一条 `/codex/rules/{chapter}` 路由 + 前端一个页签即可，是最短的一块收尾。
2. **lint 的 553 条 alias-conflicts 占满了整个 warning 通道**（100%）。
   全是同名实体（各阵营都有的兰德掠袭者、核心版 vs 登舰战版同名战略），
   基本不可行动。建议聚合成 1 条摘要 warning + 单出一份重名报告，
   否则会训练人忽略 lint——项目已有「误报致人不再看」的教训。
3. **64 条 fp11e 分队 + 200 条 fp11e 战略缺容器名 / type**。
   这些是 Faction Pack 新分队，Wahapedia 无源，只能人工补进
   `db_compile/fp_rules_patches.json` 的 inserts（白名单已开好）。
   **禁止**按 id 前缀去撞它们的战略行——那是被明确否掉的推断法。
4. **分队中文名覆盖 0/324**。战略 759/1681、增强 381/1058 有中文名（来自 P7 载荷），
   分队容器名一个都没有。要补只能人工译，且必须按 11 版 FP 而非十版译本。
5. **新页面未进 FAISS**。`ingest.py --rebuild` 没跑，检索侧零影响；
   如果要让规则问答检索到这些页，需另行 ingest（注意：wiki 是 L2 层，
   FAISS 索引的是 L0/L1 的 PDF，两者是不同的层，改动前先想清楚要不要混）。

## 5. 下次动这块之前必须知道的三件事

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
