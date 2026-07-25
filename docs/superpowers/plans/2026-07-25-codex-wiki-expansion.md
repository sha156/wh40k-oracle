# 把 codex 扩成真 wiki —— 施工蓝图

> 2026-07-25 立项。诉求原话：「我需要我的 codex 像一个 wiki 一样，有总规则，有族规则，团则(分队)等等，
> 比如武器词条要有索引，有 faq 等等，像一个真实 wiki 一样，现在只有单位有点太单薄了」，并点名
> `data/11版40K通用技能速查表.pdf`。
>
> 用户已拍板：**两层都做**（`wiki/` markdown 知识层 + web 图鉴页），板块优先级
> **武器词条索引 > 分队/战略/增强 > 总规则全文**；FAQ 本轮不进主线。
>
> 术语约定：「团则」= **Detachment（分队）**——11 版分队定式 = 1 分队规则 + 3 增强 + 6 战略。（已确认）

## 0. 决策记录（2026-07-25 用户裁决）

| # | 问题 | 裁决 | 影响 |
|---|---|---|---|
| Q0 | 「团则」指分队吗 | **是，分队规则** | PR-2 按分队排 |
| Q1 | 十版汉化正文叠加 | **不要——要和官网保持一致** | **PR-3 取消**。三类实体正文一律官方英文；中文只用于名称（库 `name_zh` + `dsl_payloads` 11 版编码译名） |
| Q2 | FAQ 板块 | **暂时不弄** | PR-6 出局；`总规faq6月20日中文.pdf` 的版本核查一并搁置 |
| Q3 | 执行顺序 | **按优先级** | PR-0 → PR-1 → PR-2 → PR-4 → PR-5 |

Q1 的连带后果（必须记住）：**这个 wiki 的三类新实体页正文会是英文的**。这是用户明确选择的
「宁可英文也要与官网一致」，不是偷懒或没做完——任何后续会话都不要"顺手把它翻译了"。

---

## 1. 一句话判断

**不是新范围，是蓝图欠账。** v2 蓝图 `docs/superpowers/specs/2026-07-04-40k-universe-ai-v2-design.md:86-104`
早就把 `factions/<阵营>/{units,stratagems,detachments,enhancements}` + `faq/` 写进 L2 目录结构，
`:389` 更明写「图鉴 wiki 浏览器：阵营→单位/**技能/分队**」。实际只做了 units。

**且路径层与 schema 层是现成的**：`wiki_engine/models.py:292` 的 `entity_page_path` 已支持
`unit/stratagem/detachment/enhancement` 四型，`build_outputs.py:164` 的 `type_order` 四型齐全——
**唯一缺口是生成器**（`wiki_engine/from_db.py:294` 硬编码 `type="unit"`）与内容。

`git log --all --diff-filter=A -- "wiki/factions/*/stratagems/*" …` = **空**，从未开工，不存在半成品要清理。

---

## 2. 事实基线（全部实测，非估算）

### 2.1 现有资产

| 项 | 实测值 | 命令/证据 |
|---|---|---|
| wiki markdown 总页数 | 1828（units 1715 + core-rules 81 + 索引类） | `find wiki -name '*.md' \| wc -l` |
| 阵营目录 | 25（只有 `units/` 一个子目录） | `find wiki/factions -mindepth 2 -maxdepth 2 -type d` |
| lint 现状 | 0 error / 277 warning（几乎全是 alias-conflicts）/ 4 info | `wiki/lint-report.md:6-10` |
| pytest 基线 | **1968 passed**（CLAUDE.md 写的 1936 已过时） | `.venv\Scripts\python.exe -m pytest -q` 73s |
| web 图鉴页 | 单文件 253 行、10 个 `useState`、**零路由**（未 import `next/navigation`，刷新即丢） | `web/src/app/codex/page.tsx` |
| web markdown 渲染 | **不存在**。运行时依赖只有 `next`/`react`/`@fontsource` 三个 | `web/package.json` |
| `/wiki/{path}` 路由 | 已存在但**前端零消费、测试零覆盖**——最低成本接入点 | `web_api/main.py:345-354` |

### 2.2 sqlite 内容可得性（`db/wh40k.sqlite`）

| 表 | 行数 | 中文名覆盖 | 中文正文覆盖 | 备注 |
|---|---|---|---|---|
| `stratagems` | 1682 | 426 / 1682 | **0** | `text_zh` 全英文 HTML，字段名骗人 |
| `detachments` | 348 | 106 / 348 | **0** | `rule_text` 全英文，284 条含 HTML；`enhancements_json` 全空（死列） |
| `enhancements` | 1058 | **0** | **0** | `cost` 927 非空 |
| `abilities` | 4009 | — | — | `owner_id IS NULL` 402 条，其中 19 条是**阵营军队规则**（`text_zh LIKE 'If your Army Faction%'`：Waaagh!/Synapse/Oath…） |
| `weapons` | 9314 | — | — | `keywords_json` = 武器词条索引的骨架 |
| `zh_keyword_glossary` | 80 | 80/80 | — | 4 条 `obs=1`（自动补的，含**错译**，见 §2.4） |

**分队容器口径**（三方案打架处，已实测裁决）：
`enhancements.detachment_name` distinct **323** ∪ `stratagems.detachment` distinct **322** = **324**，
交集 **321**。strat-only 唯一一条是伪容器 `'Army Rules'`（剔除），enh-only 2 条
（`Sanctified Orators`、`The Living Miracle`，待核）。→ **真容器 321 + 2 待核**。

### 2.3 武器词条（用户第一优先级板块）

- 归一化后（`split(',') + strip + upper`）**80 个档位 token**，剥掉数字后缀 = **49 个基础词条**。
  不归一化会得到 518 个假 distinct。
- **(武器, 词条) 对 = 10092 条**——这就是「反查：哪些武器带这个词条」的数据量。
- Top：PISTOL 1066 / RAPID FIRE 955 / BLAST 860 / TWIN-LINKED 833 / DEVASTATING WOUNDS 686。
- **`wiki/core-rules/` 只覆盖 49 个里的 18 个**，缺 31 个。但这 31 个要分开看：
  - **12 个是 ANTI-X 变体**（ANTI-VEHICLE/ANTI-INFANTRY…）→ 归到已有 `anti.md` 做参数化档位表，不各开一页；
  - **3 个是数值档位**（RAPID FIRE D、RAPID FIRE D6+、SUSTAINED HITS D）→ 归到母页；
  - **3 个是真·11 版新增缺页**：`CLEAVE`（横扫）、`CLOSE-QUARTERS`（近距离，取代十版 PISTOL）、`PSYCHIC`（灵能，343 把武器带它却没有页）；
  - **13 个是单位特有武器词条**（BUBBLECHUKKA、C'TAN POWER、DEAD CHOPPY、HARPOONED、IMPALED、OVERCHARGE…）→ **不是通用 USR**，索引里必须与通用 USR 分区显示，否则等于骗读者。

### 2.4 用户点名的那本 PDF：目前是全语料质量最差的一本

`data/11版40K通用技能速查表.pdf`（5 页，11 版中文 USR 全表，带官方节号 24.01–24.38，约 35 条）：

- **没进 `corpus_manifest.json`**（`grep -c 速查` = 0）→ 按 `defaults` 落成 `edition:10 / layer:codex-base`，
  **一本 11 版规则文档被标成十版兵牌基底**；
- **`data_refined/` 下没有它的产物**（只有 `10版40K通用技能速查表1.08`）→ `ingest.py` 回退裸 PyMuPDF 提取进的索引；
- 它是**唯一的 11 版中文 USR 权威正文**（`横扫 CLEAVE 24.06`、`近距离 CLOSE-QUARTERS 24.07` 全在里面）。

同时 `zh_keyword_glossary` 里 `HARPOONED → 额外攻击` 是**错译**（与 `EXTRA ATTACKS` 撞名，`obs=1` 说明是自动补的猜测值）。

### 2.5 被三份独立方案集体误判、经实测推翻的一条

三份方案都断言「规则正文的中文翻译在这个仓库里一份都不存在」。**错。**

`data_refined/` 下 **32 个中文汉化目录**，其中 **269 页含结构化中文战略块，共 814 块**，字段完全对齐：

```
## 终极狂飙 CAREEN!（1CP）
**技能来源**：兽人：战争部落     ← detachment
**技能分类**：传奇伟业           ← type
**使用时机**：…                  ← WHEN
**使用对象**：…                  ← TARGET
**效果**：…                      ← EFFECT
```
（证据：`data_refined/兽人10版中文老湿腐版1.09/page_002.md:1-30`）

**按英文名归一化匹配实测：814 块命中 612 块，覆盖 DB 里 639 行战略（38%）。**
未命中的两类：标题纯中文无英文（`干翻它`）、refine OCR 错字（`DESERATION OF WORLDS`）——模糊匹配可再捞一部分。

性质：**十版汉化组译本**，非官方、可能与 11 版漂移（FP `added_11e` 200 / `removed_11e` 47）。
所以它不是「不能用」，而是「**要挂版本门禁地用**」——有 book+pages 可写进 `sources`，符合 §7 无源不落笔。

另有 `dsl_payloads/*.json` **28 文件 2889 条全中文条目**（P7 阵营 DSL 编码的副产品），
含分队/战略/增强的中文名与中文注记——是补 `enhancements` 那 0/1058 中文名的现成来源。

---

## 3. 目标信息架构

### 3.1 页面类型全集

| 类型 | 数据源 | 生成方式 | 页数 | 零 LLM | 落点 |
|---|---|---|---|---|---|
| unit（存量） | sqlite | 已有 | 1715 | ✅ | `wiki/factions/<阵营>/units/` |
| core-rule（存量） | 已有 | 只加 `category` 六分区，**不重生成** | 81 | ✅ | `wiki/core-rules/` |
| core-rule 补页 | `11版40K通用技能速查表.pdf` | 人工搬运（3 页） | +3 | ✅ | 同上（cleave / close-quarters / psychic） |
| **keyword-index** | `weapons.keywords_json` + `zh_keyword_glossary` + 引擎建模清单 | 确定性 | 1 总索引 + 49 词条反查块 | ✅ | `wiki/indexes/keywords.md` |
| army-rule | `abilities` `owner_id IS NULL` + `'If your Army Faction%'` | 确定性 | 19 | ✅ | `wiki/core-rules/` + `category: army-rule`（**不建新目录、不加 type 枚举，省一整轮 §10**） |
| detachment | 容器 321 + `detachments.rule_text` | 确定性 + HTML→MD | 321 | ✅ | `wiki/factions/<阵营>/detachments/` |
| stratagem | `stratagems` | 确定性 | 1682 | ✅ | `…/stratagems/` |
| enhancement | `enhancements` | 确定性 | 1058 | ✅ | `…/enhancements/` |
| 中文正文叠加层 | `data_refined/` 32 中文目录 814 块 + `dsl_payloads` 2889 条 | 归一化匹配 + 数值门禁 | 覆盖 639 战略 | ✅ | 叠进上三类页的折叠块 |
| core-rules 总规则章节 | `data_refined/Core Rules…`（11 版英文）+ `战锤40K总规则10版老湿腐版1.11`（十版中文） | 确定性切章 + 对照 | ~24 章 | ✅ | `wiki/core-rules/sections/` |
| faq（本轮不做） | `data/archive/总规faq6月20日中文.pdf` | 正则 | ~82 | ✅ | `wiki/faq/` |

新增合计 ≈ **3100 页，全部零 LLM**。

### 3.2 web 侧形态

`/codex` 从「阵营 → 单位 → 兵牌」三层，改成带 URL 深链的 wiki：

```
/codex                          阵营总览 + 全局搜索
/codex/keywords                 武器词条索引（分组：通用 USR / 单位特有）
/codex/keywords/[slug]          词条页 + 反查「哪些武器带它 → 哪些单位」
/codex/[faction]                阵营首页（军队规则 / 分队 / 单位 / 战略 / 增强 五区）
/codex/[faction]/units/[slug]   兵牌（现有 Datasheet 组件）
/codex/[faction]/detachments/[slug]   分队页（规则 + 3 增强 + 6 战略聚合）
/codex/[faction]/stratagems/[slug]
/codex/rules/[section]          总规则章节
```

**不引前端 markdown 库**（会破「后端 tokenize、前端零解析」的全站纪律，且 wiki 含 `[[wikilink]]`、
转义竖线表格等自定义语法）。改为后端把 md 编译成块级契约
`{t:"h2"|"p"|"table"|"callout", inline: Inline[]}`，复用现有 `web_api/richtext.py` + `components/ui/Rich.tsx`，
前端加 `components/codex/Blocks.tsx`。

**顶栏不加第 5 个页签**（`SiteHeader.tsx:5` 的 `NAV_ITEMS` 第 5 项会挤爆 `max-w-[1100px]`），走 codex 内二级导航。

---

## 4. PR 切分

每个 PR 独立可验收。**验收 = `pytest -q` 不低于基线 1968 且 `wiki_engine lint` 0 error。**

### PR-0 地基（半天，不出新内容）

| 改动 | 文件 | 理由 |
|---|---|---|
| 目录穿越守卫改 `Path.is_relative_to` | `web_api/main.py:352` | 现为字符串前缀比较，**实测 `path="../wiki_engine/from_db"` 通过守卫**（`D:\…\RAG\wiki_engine\…` 以 `D:\…\RAG\wiki` 开头）。这条路由 PR-4 要正式启用，先补 |
| 修 `HARPOONED → 额外攻击` 错译 | `db_compile/zh_weapons.py` + glossary | 与 `EXTRA ATTACKS` 撞名，`obs=1` 是自动猜的 |
| `11版40K通用技能速查表.pdf` 登记层级 | `corpus_manifest.json` | 现被标成 `edition:10/codex-base`，是**用户点名的那本书** |
| wiki 宪法登记三型正文模板 | `wiki/CLAUDE.md` §1/§3/§4 | §10 扩展协议第 1 步，跳步后果已发生过 |
| 新增测试 | `tests/test_web_api_wiki_route.py` | `/wiki/*` 现在测试零覆盖 |

验收：`pytest -q` ≥1968；穿越用例返回 404。

### PR-1 武器词条索引（用户第一优先）

- 新 `wiki_engine/keyword_index.py`：归一化（**必须 `split(',')+strip+upper`**）→ 49 基础词条 + 80 档位 → 反查表。
- `wiki/indexes/keywords.md`：分区索引（通用 USR 36 / 单位特有 13），每条给：中文名、英文名、11 版节号、
  携带武器数、代表单位、**引擎是否已建模**（从 `engines/simulator/keywords.py` 取，诚实标注）。
- 补 3 页 core-rule（cleave / close-quarters / psychic），正文源 = 用户点名的速查表 PDF；ANTI-X 与数值档位并入母页做档位表。
- `wiki_engine/crosslinks.py` 补 `PSYCHIC→灵能` 等别名（343 把武器带 PSYCHIC，`psychic-attacks` 页当前被引用 0 次 = 死页）。
- web：`web_api/keywords.py` + 两路由 + `contract.py` 镜像 + `/codex/keywords` 页面。

验收：`distinct 词条数 == 索引条目数 == 49`；`sum(每词条武器数) == 10092`；lint 0 error。

### PR-2 分队 / 战略 / 增强骨架（确定性渲染，正文暂为英文）

- 新 `wiki_engine/html_md.py`：`<b>/<br>/<ul>/<span class="kwb">` → markdown，kwb 喂 `_resolve_known_alias` 转 `[[…]]`；
  白名单外的标签落 `review_needed.md` 不静默吞。
- `from_db.py:294` 的 `type="unit"` 提为参数，加 `render_stratagem/render_detachment/render_enhancement`。
- 阵营目录**必须用 `from_db.py:30 FACTION_DIRS`(25) 而非 `models.py:28 FACTION_NAMES`(21)**——
  `tests/test_wiki_models.py:313` 钉死 `ORK=欧克蛮人`，用错会多建空目录。
- 中文名：库内 `name_zh`（426 战略 / 106 分队）+ `dsl_payloads` 2889 条回填（补 enhancements 的 0/1058）。
- `lint.py` 加三型必填校验，`missing-points`（`:180` 硬编码 `type=='unit'`）对新型豁免。
- **对账**：三表行数 vs 页数逐阵营写 `wiki/log.md`，差额 ≠ 0 即失败退出。

验收：先出 3 页样张人工确认格式再铺量；`.gen_hashes.json` 由 1715 增至预期且不覆盖人工页；lint 0 error。

### ~~PR-3 中文正文叠加~~ —— **已取消（用户裁决 Q1）**

技术上可行（`data_refined/` 32 中文目录 814 块、612 命中、零 LLM），但用户要求与官网保持一致，
十版汉化译本与 11 版存在漂移，不叠。**保留此节只为记录"为什么不做"，防止后续会话把它当成待办捡起来。**

### PR-4 web wiki 化（把前三个 PR 的页面变成能浏览的网站）

- `/codex/[[...slug]]` 动态路由（现在零路由，刷新即丢）。
- 新 `web_api/wiki_blocks.py`：md → 块级契约；新 `components/codex/Blocks.tsx`。
- e2e：`web/e2e/wiki.spec.ts`（baseURL 必须 `localhost` 不是 `127.0.0.1`，Chrome 跨端口会掐）。

### PR-5 总规则全文

- 11 版英文 Core Rules 按 §01–24 切章（`data_refined/Core Rules…` 已逐页 refine）；
- 叠十版中文总规则（`data_refined/战锤40K总规则10版老湿腐版1.11`）做对照，同 PR-3 门禁；
- 11 版中文 USR 正文用速查表 PDF 覆盖。

### PR-6 FAQ（用户本轮未勾，列为可选）

---

## 5. 数据缺口表

| 缺口 | 证据 | 补齐路径 | 阻塞？ |
|---|---|---|---|
| **11 版中文核心规则正文** | `data/` 无此书，中文只有分数/平衡版/5 页速查表 | 速查表覆盖第 24 章 USR；其余需 LLM 译写 + 数字门禁 | 不阻塞 wiki，阻塞「全中文规则书」 |
| 分队编制/限制字段 | `detachments` 仅 6 列，`enhancements_json` **0/348 非空（死列）** | Wahapedia 11 版滚更 / BSData-11e | 阻塞分队页「限制」段 → **本轮该段不写** |
| 11 版新 USR 真实分布 | DB 是十版骨架：`CLEAVE`/`CLOSE-QUARTERS` 各仅 1 把武器 | 等 Wahapedia 11 版，或从 FP 兵牌 refine 反解析 | 不阻塞，但索引统计**必须标口径** |
| 汉化译文 ↔ 11 版漂移 | FP `added_11e` 200 / `removed_11e` 47 | PR-3 数值门禁 + `_zh_drift.md` 滚动清 | 不阻塞（漂移条降级为不显示） |
| `enhancements` 无中文名列 | 0/1058 | PR-2 渲染期 join `dsl_payloads`；长期加列 | 不阻塞 |
| detachment 容器真源 | `enh.detachment_id ∈ det.id` 仅 82/1058；`detachments` 存的是**规则名**不是容器名 | 加 orphan 对账测试 | 不阻塞，**必须加测试** |
| TS↔Pydantic 契约无机械比对 | `tests/test_web_api_stage3.py:172` 只断言两个键存在 | PR-4 顺手补 | 不阻塞 |

---

## 6. 硬约束（照抄 `wiki/CLAUDE.md`，违反即返工）

1. **§10 五步不跳**：先改宪法 → 改 `models.py` → 样张 → lint → 全量 build + `log.md` 留痕。
2. **§7 无源不落笔**：每页 `sources: [{book, pages}]`；查不到写「（源文本未提供）」，禁止按记忆补数值。
3. **`.gen_hashes.json` 人工编辑保护**（`from_db.py:310`）：新生成器必须挂同一套，否则手工修正被静默抹掉。
4. **生成物禁手改**：`index.md`、`factions/*/index.md`、`lint-report.md`、`terms.*`、`review_needed.md`。
5. **禁止预埋红链**（红链是 lint error 不是 TODO）；链接一律 `[[core-rules/xxx.md|中文名]]` 根相对格式。
6. **批量必对账**：目标数 vs 实际数，差额要报。
7. 项目 venv 是 **Python 3.9.1**（实测）——不能用 `str | None` 语法，`Path.is_relative_to` 可用（3.9 引入）。

---

## 7. 待定（施工中遇到再决）

**alias-conflicts 要不要从 warning 降为 info？** 现有 277 条，扩容 3100 页后（分队名/战略名大面积
跨阵营重名，如各阵营都有同名战略）预计涨到四位数，lint 报告会失去可读性。
到 PR-2 铺量时若确实爆掉，再决定「降级为 info + 单出一份重名报告」。**不预先改，先看真实数字。**

**11 版速查表与现有译名的 3 处风格冲突**（PR-0 施工时发现，未改）：
速查表写「忽视掩体 / 迅猛冲锋 / 喷射」，现库按黑图多数派用「无视掩体 / 骑枪 / 洪流」。
两边都是汉化组译名、都不是 GW 官方中文，且 aliases 已同时收录两种写法（检索不受影响）。
改动会波及 1715 页兵牌的技能列渲染，**本轮不动**，留作独立决策。

---

## 8. 明确不做（及理由）

- **LLM 译写 11 版规则正文**：造数风险高（`2026-07-24-refine-fabrication-fix.md` 的教训），且本轮有零 LLM 路径。
- **lore / meta tier 榜**：v2 蓝图 `:21-26` 已排除。
- **missions / maps**：未走 §10 扩展协议。
- **FAQ 逐条 11 版有效性裁决**：单独立项。
- **FAQ 与速查表进 FAISS**：`corpus_manifest` 登记 + `ingest` 单开一 PR，不与本线混。
- **wiki 在线编辑**：只读浏览，写入仍走生成器。
