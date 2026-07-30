# 全库三轮代码审查 · 第 2 轮：数据管线

> 分支 `review/full-audit-2026-07-30` ｜ 范围 `db_compile/`(23) `wiki_engine/`(23)
> `wiki_compile/`(7) `scripts/`(10) = **63 个 py 文件**
> 产出形式（用户拍板）：审出分级清单 + **只修 CRITICAL/HIGH**；MEDIUM/LOW 只记录不动手。
> 第 1 轮报告：`2026-07-30-audit-round1-core-chain.md`（0 CRITICAL / 3 HIGH 全修 / 6 M / 4 L）

## 0. 本轮结论速览（迭代 1 · 只审查，零实现代码改动）

| 级别 | 条数 | 说明 |
|---|---|---|
| CRITICAL | **0** | 未发现 |
| HIGH | **1** | H1 wiki 索引产物内嵌墙钟时间戳 ⇒ 每次 build 必产 26 页假 diff（已实测复现） |
| MEDIUM | **7**（M1–M7） | 见 §2.2 |
| LOW | 4 | 见 §2.3 |
| 疑似（复现不出/需联网） | 2（M8 / M9） | 见 §2.4，**未混进 HIGH**，也不计入 MEDIUM |
| 判为不成立（附反证） | 5 | 见 §4 |

**本轮的诚实底色**：这条管线被前几轮反复烧过（千分位丢行、`_KEEP_SECTIONS` 误伤、
切章漏 19 节），因此**绝大多数高危形状都已经有防线且防线是活的**——本轮验证了其中好几道
（跨语言节号对账、缓存回归守卫、`cleared_overlay` 报数、`_alloc_slug` 确定性）。
本轮查出的问题里，**只有 H1 是当前就在造成实际损害的**；其余多数是「覆盖面缺口 /
口径分裂，今天恰好没出错」，按项目既有分级习惯落在 MEDIUM。没有硬凑 CRITICAL。

---

## 1. 逐文件审查覆盖表

审查方式说明（objective 明令「不要逐个整篇通读，按风险模式扫」）：
- **模式扫**＝对该文件跑过全部 6 类风险模式的定向 grep（静默 except / 裸 continue /
  `INSERT OR REPLACE` / 时间戳 / 白名单常量 / 解析正则），命中处定点读上下文。
- **定点读**＝在模式扫之上，通读了该文件的关键函数（写库路径 / 解析器 / 对账器）。
- **实测**＝在此之上跑了只读复现脚本（DB 一律 `mode=ro`，脚本写 `%TEMP%`）。

### db_compile/（23）

| 文件 | 覆盖 | 结论 |
|---|---|---|
| `__init__.py` | 定点读 | 1 行，无逻辑 |
| `__main__.py` | 定点读（enhancements / official-zh / mfm 三个 apply 分支） | 无 finding；`cleared_overlay` 告警确实吼出来了 |
| `aliases.py` | 模式扫 | 无 finding；`DELETE ... WHERE source=?` + 保留首个/计 collided，是修过的正确形状 |
| `blacklibrary.py` | 模式扫 | 无 finding；`DELETE WHERE source='blackforum'` 后重灌，层内自洽 |
| `build.py` | 模式扫 + 定点读（`INSERT OR REPLACE` 6 处） | 无 finding；重建整库场景下表是新的，无跨层清列问题；abilities 折叠有注释说明 |
| `calc_points.py` | 定点读 | 无 finding（第 1 轮已审过其 agent 包装层） |
| `community_aliases.py` | 模式扫 | 无 finding |
| `crosscheck.py` | 模式扫 | 无 finding；`tests/test_db_compile_crosscheck.py` 覆盖 |
| `datasheet.py` | 模式扫 | 无 finding |
| `downloads.py` | 模式扫 | `fetched_at` 时间戳写进 **gitignored 缓存**，不是仓库产物，不构成假 diff |
| `dsl_apply.py` | 模式扫 | 无 finding；模块头就写明「只写 DB 的 DSL 会被 rebuild 清零」并挂进 restore |
| `dup_units.py` | 模式扫 + 实测 | **M1**（现役口径分裂） |
| `enhancements.py` | 定点读 | **M6**（无 id 行静默丢 + `inserted` 报过滤后数）；`cleared_overlay` 对账是好的 |
| `entity_resolver.py` | 模式扫 | 无 finding（第 1 轮已深审） |
| `fp_errata.py` | 定点读（三类补丁 + `_insert_new_units`） | **L3**（存在性按 name 判、写入按固定 id REPLACE） |
| `fp_rules.py` | 模式扫 | 无 finding |
| `mfm.py` | 定点读（解析 / 断裂探测 / 缓存守卫 / apply） | **M8（疑似）**；千分位与 `_PRIMARY_SECTIONS` 两处旧伤都已正确修复并有注释 |
| `official_zh.py` | 模式扫 + 大纲通读（1178 行，未逐行） | 无 finding。控制字符/零宽字符清洗、覆盖率地板、整段跳过「规则更新/常见问题」三道都在 |
| `official_zh_apply.py` | 定点读（`_plan` + `apply_official_zh` 全流程） | 无 finding；用 `UPDATE` 不用 REPLACE、写完回查对账、`missing_ids` 报数，是本轮质量最高的写库路径 |
| `schema.py` | 模式扫 | 纯 DDL 常量，无逻辑 |
| `update.py` | 定点读（`_PIPELINE` / `_RESTORE_STAGES` / 两个 runner） | **M4**（restore 清单是人工副本，无结构性断言）；层序注释与测试都在 |
| `zh_coverage.py` | 模式扫 | 无 finding；5 类和恒等于 1715 的设计本身就是反向对账 |
| `zh_weapons.py` | 模式扫 + 定点读（`missing_terms` / `coverage_report`） | **M1** |

### wiki_engine/（23）

| 文件 | 覆盖 | 结论 |
|---|---|---|
| `__init__.py` / `__main__.py` | 定点读 | 各 1–4 行 |
| `_io.py` | 定点读（全文 65 行） | **M7**（`load_gen_hashes` 损坏即返回 `{}` ⇒ 人工编辑保护静默失效）；`atomic_write_text` 的 newline 注释是正确的 |
| `build_outputs.py` | 定点读 + 实测 | **H1** |
| `changelog.py` | 模式扫 + 定点读（对账段 `orphan_lines`） | 无 finding；「没归进任何条目的行要报出来」这条反向对账在，CLI 也吼 |
| `cli.py` | 定点读（entities / core-rules / changelog / keywords / lint 五个分支） | 无 finding；`skipped` 计数与前 5 条都打印 |
| `core_rules.py` | 模式扫 + 定点读（切分正则注释块 + `unextracted_hints`） | 无独立 finding（见 §4 N3：自检确实与抽取器共享前提，但**外部正交守卫已在 pytest 里**） |
| `core_rules_zh.py` | 定点读 + 实测（跑了 cross_check） | 无 finding，实测 156=156 双向差集为空 |
| `crosslinks.py` | 模式扫 | 无 finding |
| `entity_pages.py` | 定点读（`_plan` / `_alloc_slug` / `_write` / 分队段） | 无 finding（见 §4 N1/N2/N5）；**M9（疑似）** 容器 325 vs 页 324 差 1 未定因 |
| `from_db.py` | 模式扫 + 定点读（`FACTION_DIRS`、`points_json` 读取） | 无 finding |
| `html_md.py` | 模式扫 | 无 finding |
| `keyword_index.py` | 定点读（`_current_unit_ids` / `collect`） | **M1**、**L1** |
| `lint.py` | 定点读（全部 6 条规则） | **M2**（断链检查的覆盖面） |
| `models.py` | 定点读（`GENERATED_MD_NAMES` / `FACTION_NAMES`） | 无独立 finding（`FACTION_NAMES` 见 §4 N2） |
| `pdf_sections.py` | 模式扫 + 定点读（`cross_check`） | 无 finding，是本轮见到最好的正交守卫 |
| `synthesize.py` | 模式扫 | 无 finding |
| `operations/__init__.py`、`templates/__init__.py` | 模式扫 | 无逻辑 |
| `operations/archive_op.py` | 模式扫 | 时间戳只进归档目录名，不产假 diff |
| `operations/ingest_op.py` | 模式扫 | 无 finding |
| `operations/lint_op.py` | 模式扫 | 无 finding |
| `operations/query_op.py` | 模式扫 | 无 finding |

### wiki_compile/（7）

| 文件 | 覆盖 | 结论 |
|---|---|---|
| `__init__.py` | 定点读 | 空 |
| `__main__.py` | 定点读 | 无 finding |
| `canonical.py` | 模式扫 | 无 finding（纯下载 + CSV 落盘） |
| `extract.py` | 定点读（全文 127 行） | **L2**（噪声「详解」标题先于主标题时页码静默丢） |
| `pair.py` | 模式扫 | 无 finding |
| `pair_llm.py` | 模式扫 | 无 finding；LLM 兜底失败返回 `[]` 但调用方有计数 |
| `terms.py` | 模式扫 | **L4**（备份文件名带时间戳，只影响备份不影响产物） |

> 全包说明：`wiki_compile` 是 P0 期的术语表管线，现役 wiki 生成已由
> `wiki_engine/from_db.py`（sqlite 驱动）接管。本轮按范围审了，但**不建议投入修复预算**。

### scripts/（10）

| 文件 | 覆盖 | 结论 |
|---|---|---|
| `compare_bench_runs.py` | 模式扫 | 无 finding |
| `fetch_blacklibrary_details.py` | 模式扫 | 无 finding；写的是 gitignored 缓存，有 partial 断点 |
| `gen_dsl_condition_anchor.py` | 模式扫 | 无 finding（写 `dsl_payloads` 锚文件，正规命令产出） |
| `import_blacklibrary_aliases.py` | 模式扫 | 无 finding |
| `qa_bench.py` | 定点读（判分链 `parse_verdict` / `decide_mechanical` / `run_one`）+ 实测 | **M5**（`parse_verdict` 固定顺序偏向 ✅） |
| `refine_gaps.py` | 模式扫 | 无 finding |
| `refine_pages_fabricated.py` | 模式扫 | 无 finding（第 1 轮已审 `llm_refine` 侧） |
| `refine_reconcile.py` | 模式扫 | 无 finding，本身就是对账脚本 |
| `s2_crosslingual_probe.py` | 模式扫 | 无 finding，一次性探针 |
| `verify_warn_triage.py` | 模式扫 | 无 finding |

**未审文件：0 个。** 63/63 全部至少做过模式扫。

---

## 2. 分级 finding 清单

### 2.1 HIGH

#### H1 · wiki 索引产物内嵌墙钟时间戳 ⇒ 每次 `build` 必产 26 页假 diff

- **文件:行**：`wiki_engine/build_outputs.py:78`（`build_global_index`）、
  `wiki_engine/build_outputs.py:160`（`build_faction_index`）
- **复现输入**（只读，脚本在 `%TEMP%\audit_r2_stamp.py`）：

```python
from wiki_engine.build_outputs import build_global_index
fresh   = build_global_index([], Path("wiki")).splitlines()
on_disk = (Path("wiki")/"index.md").read_text(encoding="utf-8").splitlines()
```

- **实际输出**：

```
现在重新生成的第 3 行 : _Last updated: 2026-07-30 16:24 UTC_
仓库里已提交的第 3 行 : _Last updated: 2026-07-27 11:51 UTC_
两者相等? False
带 _Last updated_ 时间戳的已提交索引页: 26
    ['factions/兽人/index.md', 'factions/千子/index.md', 'factions/吞世者/index.md',
     'factions/基因窃取者教派/index.md', 'factions/太空死灵/index.md'] ...
```

  即：**内容一个字节没变，重跑一次 `wiki_engine build` 就有 26 个已提交文件变脏**。
- **影响**：
  1. 这正是 2026-07-27 已经被判为缺陷并修掉过一次的形状——当时的修法是
     「去掉 `lint-report.md` 的生成时间戳……消除『跑一次 lint 就脏一次工作区』的假 diff」
     （CLAUDE.md 有记；本轮实测 `wiki_engine lint` 跑完 `git status` 确实干净，证明那一处修对了）。
     **同一个缺陷在 `index.md` 这 26 页上没有被一并修掉。**
  2. 直接违反本仓库「生成物只准由正规命令产出，跑完 `git status` 必须干净」的纪律，
     并且是 gnhf 无人值守跑「Working tree is not clean 秒退」的已知成因之一
     （auto-memory `gnhf-orchestration-lessons` 点名过）。
  3. 真正的内容变更被 26 行时间戳噪声淹没，review 时看不出「这次到底改了什么」。
- **分级理由**：判 HIGH 而不是 MEDIUM，是因为**同型缺陷已被本项目判过一次是缺陷并修复**，
  这里属于修了一半；且它损害的是整个自动化流程赖以判断「改了没有」的信号。
  它不腐蚀数据，故不是 CRITICAL。
- **修复方向（留给下一次迭代）**：去掉这两处 `_Last updated:` 行（与 `lint-report.md`
  同一修法），配「同内容两次生成字节相同」的护栏测试，并用正规命令
  `python -m wiki_engine build` 重生成这 26 页（预期 diff＝26 文件 × 删 2 行）。

### 2.2 MEDIUM（只记录，本轮不改）

#### M1 · 「现役单位」有两套口径，窄的那套少 141 个在售单位

- **文件:行**：窄口径（仅 MFM）`db_compile/zh_weapons.py:476-481`、`:512-517`、
  `db_compile/dup_units.py:132-145`；宽口径（MFM ∪ 黑图书馆）
  `wiki_engine/keyword_index.py:164-175`、`web_api/codex.py:42-51`
- **实测**（`%TEMP%\audit_r2_current.py`，DB `mode=ro`）：

```
units总数 1715
A(MFM∪黑图, 与 web/keyword_index 一致) = 1170
B(仅 MFM, zh_weapons/dup_units) = 1029
只在 A 里的现役单位数 = 141
A 口径武器中文覆盖: (5879, 5879)
B 口径武器中文覆盖: (4969, 4969)
```

- **影响**：`web_api/codex.py` 的 docstring 已经写明**为什么不能只看 MFM**
  （官方 MFM 没有 Harlequins 那一组，只按 MFM 判会把在售单位误归档）。
  `zh_weapons.missing_terms()` 是「还要人工补译多少」的工单，用窄口径就等于
  **141 个在售单位的缺译永远不会出现在工单里**；`coverage_report()` 的百分比也是
  在窄池上算的——典型的「100% 可能是比得少」。
- **当前影响 = 0**：实测两口径今天**都是 100%**（5879/5879 与 4969/4969），
  所以现在没有被隐藏的缺译。风险是未来新增单位（黑图收录、MFM 未列）会静默漏出工单。
- 故判 MEDIUM 而非 HIGH。

#### M2 · lint 的断链检查覆盖面：4809 条 wikilink 从不被检查

- **文件:行**：`wiki_engine/lint.py:54-64`（`_iter_source_md_files` 排除
  `GENERATED_MD_NAMES`）、`wiki_engine/lint.py:144-175`（`check_index_consistency`
  只查 `wiki/index.md` 一个文件）
- **实测**（`%TEMP%\audit_r2_lintgap.py`）：

```
被 lint 排除在『出链来源』之外的生成物文件: 33
这些文件里的 wikilink 总数: 4809
其中断链数: 0 分布于 0 个文件
```

- **影响**：25 个阵营 `index.md` + `changelog/index.md` + `core-rules/index.md` +
  `indexes/keywords.md` 里的全部出链，既不进 `check_broken_links`（按文件名排除），
  也不进 `check_index_consistency`（只认根 `index.md`）。
  「lint 0 error」这个门禁对 wiki 近一半的链接是**沉默**的。
- **注意不要一刀切**：这个排除本身是 H15 修复（防 lint 扫自己生成的 `lint-report.md`
  里的示例断链、假阳性自我复现）。正确修法是**按内容分**（报告类产物不扫，索引类产物要扫），
  不是删掉排除集。
- **当前影响 = 0**（实测 0 断链），故 MEDIUM。

#### M3 · `corpus_manifest.classify_book` 静默回退 defaults（第 1 轮移交线索 ①，本轮已量化）

- **文件:行**：`corpus_manifest.py:59-70`；汇总侧 `ingest.py:370-374, 410-412`
- **实测**（`%TEMP%\audit_r2_manifest.py`）：`data/` 下 **27 本 PDF 未登记 manifest**，
  全部回退 `{'edition': '10', 'layer': 'codex-base'}`。
- **反向结论（重要）**：这 27 本**逐本核对全部是真十版 codex**
  （兽人/千子/吞世者/圣血天使/…/黑色圣堂），defaults 对它们是**正确**的。
  ⇒ **当前 0 例误分类**，`corpus_manifest.py` 顶部注释「这是 codex 的设计行为而非错误」成立。
- **仍记 MEDIUM 的理由**：`ingest` 的分层汇总是**按层聚合**的
  （`layer_stats["10版/codex-base"] += n`），未登记书目与显式登记成 codex-base 的书
  **在汇总里完全不可区分**——即这份汇总不是这条风险的探测器（风险模式 #2 的形状）。
  新增一本 11 版规则类 PDF 而忘了登记，会静默拿到 `layer=codex-base`，
  从而**不被 app.py 的规则层保底选中**，且没有任何一处会吼。
- **建议修法（不在本轮）**：`load_manifest`/`ingest` 增加一行「N 本书未在 manifest 中登记：…」
  的汇总告警（只报名单，不改分类行为）。
- 补充事实：`data/官方中文/` 那 34 个官方 PDF **不受影响**——`ingest.py:309` 用的是
  `data_dir.glob("*.pdf")`（非递归），子目录不入库。

#### M4 · `_RESTORE_STAGES` 是 `_PIPELINE` 的人工副本，缺结构性断言

- **文件:行**：`db_compile/update.py:483-521`
- **现状**：现有测试逐条点名 3 个阶段（`fp_errata` 先于 `mfm_apply`、
  `fp_rules` 先于 `official_zh`、`official_zh` 必须在 restore 里），
  但**没有**「`_PIPELINE` 里所有写库层都必须出现在 `_RESTORE_STAGES` 里」的通用断言。
- **实测当前无缺口**：`_PIPELINE` 的 10 个写库阶段（fp_errata / mfm_apply / fp_rules /
  official_zh / dsl_apply / aliases / aliases_blackforum / aliases_community /
  zh_details / zh_weapons）**10/10 都在** `_RESTORE_STAGES` 里，顺序也一致。
- **风险**：将来新增一个写库层只挂 `_PIPELINE`，`build` 之后那一层会**静默不恢复**——
  正是注释里说的「单独 build 静默留下降级库」那把脚枪，只是换了个入口。判 MEDIUM。

#### M5 · `qa_bench.parse_verdict` 按固定顺序取标记，判词同时含 ✅❌ 时永远判 ✅

- **文件:行**：`scripts/qa_bench.py:311-321`
- **复现（纯函数）**：

```
parse_verdict('阵营名 ❌ 错误，但数值 ✅ 正确') -> ✅
parse_verdict('回答缺少点数 ❌；其余 ✅')       -> ✅
parse_verdict('❌ 完全错误')                   -> ❌
```

  循环是 `for mark in ("✅","❌","⚠️")`，**先看有没有 ✅**，而不是看**第一个出现**的标记，
  也不是「有 ❌ 就判 ❌」。方向单一地偏向「判对」，而这是全项目「零硬错」的唯一测量仪器。
- **当前影响 = 0（有实证）**：扫 `benchmarks/` 下 **56 个结果文件**的全部 `reason` 字段，
  **同时含 ✅ 和 ❌ 的判词 0 条**——判分模型在历史上从没输出过双标记。
  故判 MEDIUM 而非 HIGH，并明确记「不是靠这条把分数刷高的」。

#### M6 · `apply_enhancements` 对无 id 行静默丢弃，且 `inserted` 报的是过滤后的数

- **文件:行**：`db_compile/enhancements.py:82-87`（`for r in rows if r.get("id")`）、
  `:102`（`"inserted": len(payload)`）、CLI 打印 `db_compile/__main__.py:392`
- **影响**：CSV 上游若换版式导致 id 列错位，这些行会**无声消失**，而 CLI 打印的
  「插入 N 条」是**过滤后**的 N，自己跟自己对得上（风险模式 #1+#2 的组合形状）。
- **缓解**：`--check` 分支确实做 CSV 行数 ↔ 库行数对账，能逮到；但它是**另一个子命令**，
  `--apply` 单跑时没有这道门。判 MEDIUM。

#### M7 · `load_gen_hashes` 登记表损坏即返回 `{}`，人工编辑保护整体静默失效

- **文件:行**：`wiki_engine/_io.py:46-59`；受害方 `wiki_engine/entity_pages.py:518-533`
- **链路**：`.gen_hashes.json` 损坏 → `load_gen_hashes` 返回 `{}` →
  `_write` 里 `registered is None` → **无条件覆盖**，`report["conflicts"]` 恒为空。
  即「检测到人工编辑就跳过覆盖」这道保护在登记表损坏时不是变严而是**整个消失**，
  且 CLI 会照常打印一切正常。
- docstring 自称「安全降级」——方向可议（安全方向应是「宁可不写」或至少吼一声）。
  判 MEDIUM 而非 HIGH：登记表由本地原子写产生，损坏概率低，且 wiki 页本就以生成为主。

#### M8 · （疑似）MFM 断裂探测只覆盖「有表头且 0 行」，覆盖不到**部分**丢行

- **文件:行**：`db_compile/mfm.py:228-234`（`if not rows and heads: raise MfmParseBroken`）、
  `:120-135`（`_parse_section_rows` 要求块内存在 `bg-slate-200 ... font-bold` 档位表头）
- **推理**：某个单位块若只是**缺档位表头 div**（而页面整体仍解析出大量行），
  该单位的全部分数行会被静默丢弃：`rows > 0` ⇒ 不触发 `MfmParseBroken`；
  `count_unit_headers()` 刻意不做等值对账（注释写明「只用于 >0 表头却 0 行 的断裂判定」）
  ⇒ 也不报。`_guard_cache_regression` 的阈值是单阵营 30% / 总量 10%，个别单位掉不到线。
- **为什么列为「疑似」而不是 HIGH**：**本轮没有复现出来**——需要联网抓一份真实
  HTML 才能构造/验证这种版式，而本轮不联网。缓存里只存解析后的行，无法回放。
  按红线「跑不出复现的一律单列为疑似」。

#### M9 · （疑似）分队容器 325 vs 分队页 324，差 1 未定因

- **实测**（`%TEMP%\audit_r2_det.py`）：三表 `(阵营, 容器名)` 并集去重 **325**
  （detachments 260 / stratagems 323 / enhancements 324），
  而 `wiki/factions/*/detachments/` 共 **324** 页、`wiki/core-rules/detachments/` **0** 页。
- **未定因原因**：`generate_all` 的 `containers` 字典构造与我这条 SQL 并集口径未必等价
  （它还带 `no_rule` / `阵营 id 未知` 两个跳过分支），要确认得跑
  `python -m wiki_engine entities` 取报告——**那会重写 wiki 产物，本轮红线禁止**。
  故如实列为疑似 + 未完成项（见 §6）。差额是 1，不是系统性掉行。

### 2.3 LOW（只记录）

- **L1** `wiki_engine/keyword_index.py:196-199`：`keywords_json` 解析失败 `continue`
  且不计数——`tally` 有 `orphan_rows` 桶却没有 `bad_json` 桶。当前库内 0 例。
- **L2** `wiki_compile/extract.py:106-110`：「XX详解」噪声标题若**先于**同名主标题出现，
  `by_key` 尚无该实体 ⇒ 这一页的页码被静默丢弃（同文件 :89-91 的无归属续页是有告警的，
  两处标准不一致）。
- **L3** `db_compile/fp_errata.py:179-204`：存在性判据是 `(faction_id, name_en)`，
  写入却是**固定 `unit_id`** 的 `INSERT OR REPLACE INTO units (... name_zh=NULL,
  points_json=NULL ...)`。若上游哪天用同一个 id 建了**不同名字**的单位，
  判据认不出、REPLACE 会把该行的 `name_zh`/`points_json` 抹成 NULL。
  当前 `fpe_*` 系列 id 与库内无冲突，故 LOW。
- **L4** `wiki_compile/terms.py:44`：备份文件名带 `strftime` 时间戳。只影响备份文件名，
  不进仓库产物，无假 diff。

### 2.4 「疑似」汇总（不进 HIGH）

M8（MFM 部分丢行）、M9（分队差 1）——理由见各条，均**未复现出实际错误输出**。

---

## 3. 已修项的「改前会红 / 改后转绿」验证输出

**本轮迭代 1 零实现代码改动**（objective 规定：第 1 次迭代只做审查）。
故本节**本轮为空**，H1 的修复与其护栏测试的两次输出留待下一次迭代补齐，
届时按红线在此贴出 stash-红 / 恢复-绿 的实际输出。

---

## 4. 判为**不成立**的条目（附反证，防第 3 轮重复排查）

**N1. 「战略库 1681 行但 wiki 只有 1653 页 ⇒ 静默丢 28 条」——不成立。**
反证：那 28 条是 `stratagems.faction` 为空的**通用（核心）战略**，
`entity_pages._faction_zh("")` 返回 `""` ⇒ 落在 `wiki/core-rules/stratagems/`。
实测 `ls wiki/core-rules/stratagems | wc -l` = **28**，1653 + 28 = **1681**，一条不少。
（我最初只统计了 `factions/` 子树，是统计口径错，不是代码丢行。）

**N2. 「`FACTION_NAMES` 只覆盖 21 个 faction_id 而库里有 25 个 ⇒ 白名单误伤整段」——不成立。**
反证：`entity_pages._faction_zh` 用的是 `wiki_engine.from_db.FACTION_DIRS`（**25 个**），
不是 `models.FACTION_NAMES`（21 个）。实测四张表零误伤：

```
FACTION_DIRS: 25  FACTION_NAMES: 21
stratagems:   1681 行 / 24 阵营；FACTION_DIRS 认不出：0 阵营 0 行
enhancements: 1058 行 / 23 阵营；认不出：0 阵营 0 行
units:        1715 行 / 25 阵营；认不出：0 阵营 0 行
detachments:   348 行 / 23 阵营；认不出：0 阵营 0 行
```

**N3. 「跨语言节号对账 `cross_check` 只是手工脚本、没有测试 ⇒ 唯一的正交守卫不在回归里」——不成立。**
反证：`tests/test_wiki_core_rules_zh.py:159 test_zh_en_section_numbers_match` 每次
`pytest` 都真跑（`@needs_zh @needs_en` 的 PDF 本机都在，**未被 skip**），断言
`zh_only == [] and en_only == [] and matched == 156`。本轮另外手工跑了一次确认：

```
$ .venv/Scripts/python.exe -m wiki_engine.core_rules_zh
中文目录 24 章；中文 156 节 / 英文 156 节，配上 156 节
✅ 中英节号完全一致
```

`core-rules` 生成命令自带的两道检查（`empty_chapters` / `unextracted_hints`）
确实与抽取器共享正则前提，但**外部正交信号已经进了回归网**，不构成缺陷。

**N4. 「lint 排除生成物 ⇒ 生成索引里的断链无人管」——部分不成立。**
反证：实测那 4809 条链接**当前 0 断链**；且排除集本身是 H15 的正确修复
（防 lint 扫自己的 `lint-report.md` 造成假阳性永久自我复现）。
保留为 M2（覆盖面缺口），但**不要**用「删掉排除集」的办法修。

**N5. 「`db_compile enhancements --apply` 的 `INSERT OR REPLACE` 会静默清空 `name_zh`/DSL 列」
（第 1 轮移交线索 ②）——不成立。**
反证：`enhancements.py:55-59, 81, 97-99` 逐列统计 REPLACE 前后有值行数，差额进
`cleared_overlay`；`__main__.py:396-401` 无条件打印
「⚠️ INSERT OR REPLACE 清空了叠加列：官方中文名 N 行、DSL 投影 N 行」并给出补跑命令。
**清空是真的，静默不是。** 提示会不会被人忽略属流程问题，不是代码缺陷。

---

## 5. 移交第 3 轮（`web_api/` + `web/`）的线索

1. **现役口径**：`web_api/codex.py:42-51` 用的是宽口径（MFM ∪ 黑图书馆），
   与 `wiki_engine/keyword_index.py` 一致、与 `db_compile/zh_weapons.py`/`dup_units.py` 不一致
   （M1）。第 3 轮若要统一，**基准应取 `web_api/codex.py` 那一套**——它的 docstring
   写了为什么（MFM 没有 Harlequins，只按 MFM 会误归档 199 个在售单位），
   而窄口径那三处没有任何理由说明。
2. **`/codex/rules` 与 `/codex/changelog` 的页数断言**：本轮确认库侧/生成侧数字自洽
   （核心规则 156 节中英对齐、战略 1681 = 1653 + 28）。第 3 轮核前端展示时，
   注意**通用（核心）战略 28 条落在 `core-rules/` 而非任何阵营目录下**——
   若前端只按阵营遍历，这 28 条会在页面上「消失」而后端一条没少。
3. 第 1 轮移交的两条仍然有效且**与本轮无关**：`/simulate` 的
   `loadout_required` 错误文案是否真显示给用户；军表两个页签同时展示两个 `total_points`。

---

## 6. 本轮实际数字

### 迭代 1（只审查，零实现代码改动）

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `.venv\Scripts\python.exe -m pytest -q` | **2418 passed, 0 failed**（113.48s）＝与起跑基线一致 |
| wiki lint | `.venv\Scripts\python.exe -m wiki_engine lint` | **0 errors, 1 warnings, 4 info, 0 auto-fixed / 5 total** |
| 工作区 | `git status --porcelain`（跑完 pytest + lint 之后） | **干净**（lint 重写的 `lint-report.md`/`alias-conflicts.md` 字节不变——反过来印证了 H1 的修法方向是对的） |
| `mfm --check` | 未跑 | 本轮**零改动**，未触碰点数/落库判据，按 objective 免跑 |
| 基准 | 未跑 | 本轮未改库、未改索引、未碰 `agent/`，按 objective 免跑 |

**只读复现脚本**（全部写在系统临时目录 `%TEMP%`，**未入仓库**）：
`audit_r2_manifest.py`、`audit_r2_current.py`、`audit_r2_lintgap.py`、
`audit_r2_faction_gap.py`、`audit_r2_verdict.py`、`audit_r2_stamp.py`、
`audit_r2_recon.py`、`audit_r2_det.py`。DB 一律 `file:...?mode=ro` 只读连接，
**未写 `db/wh40k.sqlite`**、未改 `qa_gold*.json`、未重新生成任何 `wiki/` 产物。

### 未完成项（如实登记）

- **M8（MFM 部分丢行）复现未完成**：需联网抓一份真实 MFM HTML 才能验证/证伪
  「单位块缺档位表头」这个版式是否真实存在。本轮不联网，缓存只存解析后的行、无法回放。
- **M9（分队容器 325 vs 页 324）定因未完成**：定因需要跑
  `python -m wiki_engine entities` 拿 `report["detachments"]["no_rule"]`，
  而那会重写 wiki 产物，触碰本轮红线。留给修复迭代（届时若为修 H1 本就要重生成索引，
  可顺带在同一次正规命令里取报告）。
- **H1 的修复与护栏测试**：按 objective 的迭代节奏留给下一次迭代。

---

## 7. 下一次迭代要做的事

1. 修 **H1**：删 `build_outputs.py:78` 与 `:160` 的 `_Last updated:` 行；
   加护栏测试「同样输入两次生成字节完全相同 / 产物中不含时间戳」，
   实测 stash-红 / 恢复-绿并把两次输出贴进 §3。
2. 用正规命令 `python -m wiki_engine build` 重生成受影响的 26 个 `index.md`，
   在报告里写明 diff 规模（预期：26 文件，每个删 2 行，无其他变化）。
3. 收尾跑 `pytest -q`（预期 2418 + 新增护栏）、`wiki_engine lint`（预期 0 error）、
   `git status`（预期只剩本轮预期内改动），顺带取 M9 的定因报告。
