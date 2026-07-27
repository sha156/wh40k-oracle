# 数据来源路由：该查库时别去查 PDF（基准 #113 / #117）

2026-07-27 · 分支 `gnhf/40k-d-project-py-rag-bf5362`

## 0. 结论先说

两题红的**表象**是「答案来自 PDF 文档层而非结构库」，但根因不是「路由偏好选错了工具」——
模型两次都**第一时间就去查了结构库**。真正的病灶是：**工具查空 → `loop._EMPTY_CHECKS`
当场降级经典链 → 经典链是纯 PDF 检索**，于是结构库里正确的数字/事实从没进过上下文。

| 题 | 表象 | 实际根因 | 修法 |
|----|------|----------|------|
| #113 | 答 320（民间译本 PDF），库内官方 355 | `get_datasheet("罗伯特·基里曼")` 因**分隔号写法**查空 → 降级 | 解析器加分隔号归一化，让它判 `exact` |
| #117 | 答「Frame 在库中可查」，库内实为 6 个关键词无 Frame | `get_keyword_definition("Frame")` 查空 → 降级，**把已查到的实体结果一并丢弃** | 该工具移出 `_EMPTY_CHECKS` + 补「未收录 ≠ 不存在」note |

**未削弱 `rag_search`**：它仍是模型手里的普通工具，两轮基准里分别参与 33 / 32 题
（基线 35，减少的 3 题正是不再需要降级的那几题）。

## 1. 证据：实际 tool_calls

诊断脚本包住整个 tools dict 记录**入参与返回摘要**（`meta.tool_calls` 只有工具名，不够用），
跑 `answer_agent` 单题。⚠️ 关键观察：**`tool_calls` 末尾那个 `rag_search` 不是模型调的**——
它是 `loop._fallback` 自己追加的（`loop.py:245`），所以「序列里有 rag_search」本身就是降级的指纹。

### #113 · 修前

```
intent: 算   degraded: True
[0] get_datasheet(name_or_id="罗伯特·基里曼")
    -> {found: false, note: "库中未找到该单位"}
-- 降级 → 经典链 → sources: [《6月4日分数中文》p31, 《星际战士10版中文》p47, ...]
-- answer: 「罗伯特·基里曼的官方点数为 320 分」
```

**一步就降级了**。链条：

1. `EntityResolver.resolve("罗伯特·基里曼")` → `confidence="fuzzy"`（不是 exact）
   ——因为库内 `_zh_to_id` 存的键是 **`罗伯特.基里曼`（半角句点）**，题面/用户写的是
   通行的中文间隔号 `·`。实测库内 30 个键用 `·`、6 个用 `.`，**库内自己就不统一**。
2. `datasheet.find_datasheet`（`datasheet.py:252`）**只信 `exact`**——这是防错配的既有守卫
   （注释点名 `机械教游侠→Tech-priest Dominus`），fuzzy 一律拒绝 → 返回 None。
3. `get_datasheet` 落到 `{"found": False, note: "库中未找到该单位"}`，且
   `suggestions` 为空（resolver 给的是 fuzzy 命中不是 suggestions），走不到 `near_miss_only` 分支。
4. `_EMPTY_CHECKS["get_datasheet"]` 命中 → `_fallback` → 经典链 → 民间译本 PDF 的冻结旧值 320。

### #117 · 修前

```
intent: 查   degraded: True
[0] get_entity(name_or_id="战将泰坦")        -> {found: true, ...}     ← 成功！
[1] get_keyword_definition(keyword="Frame")  -> {found: false, note: "未找到该关键词的术语页"}
-- 降级 → 经典链 → sources: [Faction Pack Adeptus Titanicus p9, ...]
-- answer: 「关键词：Vehicle, Walker, Titanic, Towering, Frame, ... Frame 关键词在库中可查」
```

模型**已经查到了实体**，第二步问 Frame 的术语页时查空，降级把第一步的成果**整个丢掉**，
只剩 PDF 片段；PDF 上 Frame 白纸黑字写着，于是模型答「库中可查」——与库内事实恰好相反。
这正是本题要考的诚实性反例。

## 2. 修法与依据

### 2.1 #113 · 分隔号归一化（`db_compile/entity_resolver.py`）

`罗伯特·基里曼` 与 `罗伯特.基里曼` 是**同一个名字的两种写法**，不是模糊匹配。
所以修在**归一化层**而不是放宽 fuzzy 判据——`FUZZY_MAX_EDITS` 那道防线
（造名给出 id 57→3，上一轮成果）**一个字节都不动**。

- 新增 `_sep_normalized()`：抹掉 `·.．•‧・‥/-` 与空白后小写化。
- `__init__` 末尾按最终的 `_zh_to_id` 统一建 `_zh_norm_to_id`（两条中文来源都灌完之后建，
  保证与精确表一致）；**归一键冲突记 `None`**，宁可不解析也不静默取先入者。
- `resolve()` 在精确表之后、其余分支之前查归一表，命中判 **`exact`**
  ——判 exact 是关键，判 fuzzy 等于没修（`find_datasheet` 照样拒绝）。

实测影响面（真实库 1178 个中文键）：

| 指标 | 值 |
|------|-----|
| 归一索引规模 | 71 键 |
| 归一键冲突（判 None，拒绝解析） | **0** |
| 既有精确键回归（仍解析到自己且仍是 exact） | **0 个退化** |
| 新增可精确解析的分隔号变体 | **34** |
| `基里曼`（裸姓氏）仍判 ambiguous | 不变 ✓ |

修后：`resolve("罗伯特·基里曼")` → `exact / 000000138`，
`get_datasheet` → `found=True, points_min=355`。

### 2.2 #117 · `get_keyword_definition` 查空不再降级（`agent/loop.py` + `agent/tools.py`）

判据沿用 `_EMPTY_CHECKS` 里**已经写死的那条区分**（`entity_resolver` vs `get_datasheet`）：

> **纯映射工具**（名字→id、关键词→术语页）的「没查到」**本身就是被问到的那个问题的实质答案**；
> **数据查表工具**（get_datasheet）的「没查到」只说明结构库没索引到，
> 必须放它去查语料（这是注释里点名的「回归 7 题」防线，`get_datasheet` 仍**不**放行）。

`get_keyword_definition` 属于前者，且 #117 问的字面就是「库里查得到吗」。

- 从 `_EMPTY_CHECKS` 移除，原位留注释写明因果与实测 tool_calls。
- `_KEYWORD_NOT_FOUND_NOTE`（同 #109 `_CALC_POINTS_UNRESOLVED_NOTE` 的通道）：
  说穿「未收录 ≠ 官方规则里没有」，指路「问规则含义请改用 `rag_search`」，
  双向禁止——既不许断言该关键词不存在，也不许把 PDF 上的内容说成「库里查得到」。

**不降级 ≠ 够不到 PDF**：`rag_search` 仍在模型的工具表里，note 明写了何时该调它。

## 3. 两轮基准对比

`--path agent`，共 115 题。基线 = `qa_agent_results_mfm_apply_run2.json`。

| 轮次 | ✅ | ⚠️ | ❌ | 准确率 | degraded |
|------|-----|-----|-----|--------|----------|
| 基线 | 111 | 2 | **2** | 96.5 | 35 |
| r1（本轮修后） | 114 | 1 | **0** | 99.1 | 33 |
| r2（本轮修后） | **115** | 0 | **0** | **100.0** | 32 |

`scripts/compare_bench_runs.py` 逐题对比，**差异全部是改善，零退化**：

```
基线 → r1： 差异 3 题   #42 ⚠️→✅   #113 ❌→✅   #117 ❌→✅
基线 → r2： 差异 4 题   #41 ⚠️→✅   #42 ⚠️→✅   #113 ❌→✅   #117 ❌→✅
r1  → r2 ： 差异 1 题   #41 ⚠️→✅（已知波动题）
```

四题锚点 + 本轮目标题：

| id | 基线 | r1 | r2 |
|----|------|----|----|
| #63 | ✅ | ✅ | ✅ |
| #109 | ✅ | ✅ | ✅ |
| #118 | ✅ | ✅ | ✅ |
| #119 | ✅ | ✅ | ✅ |
| **#113** | ❌ | **✅** | **✅** |
| **#117** | ❌ | **✅** | **✅** |

**#117 不再摆动**：两轮均 ✅。唯一的轮间差异是 #41（已知波动题）。

修后 #117 的实际答案（`degraded: False`，两步工具调用，无 rag_search）：

> 战将泰坦在本系统结构库中记录的关键词包括：阵营关键词 Adeptus Titanicus；
> 普通关键词 Warlord Titan、Titanic、Vehicle、Towering、Walker、Imperium。
> 关于【Frame】：结构库中的关键词术语页未收录该词条，因此库里查不到独立的【Frame】定义。
> 但官方兵牌上确实存在该关键词，属于已知的数据缺口。

正好命中 gold 要的三件事：照实给库内清单、说明 Frame 未被收录、不否认官方规则里有它。

## 4. 护栏（+6 用例，2392 → 2398 全绿）

`tests/test_db_compile_entity_resolver.py::TestSeparatorNormalizedZhNames`
- `test_interpunct_variant_of_indexed_name_resolves_exact` —— 断言 **exact**（判 fuzzy 即失败）
- `test_normalization_is_symmetric` —— 反方向与全去分隔号写法
- `test_colliding_normalized_key_refuses_to_guess` —— 冲突键不许猜，各自精确写法不被顶掉
- `test_unrelated_name_still_unresolved` —— 归一化不得顺手放宽「另一个名字」的判定

`tests/test_agent_loop.py::TestKeywordDefinitionMissIsNotEmpty`
- `test_keyword_miss_keeps_prior_findings_and_does_not_degrade` ——
  断言 `degraded is False` **且** LLM 最后一步仍看得见先前查到的实体内容（防「不降级但丢上下文」）
- `test_keyword_miss_note_forbids_negative_assertion` —— note 必须含 `≠` / `rag_search` / `禁止`

**真会红验证**：`git stash` 掉三个源文件后重跑，4 条当场失败
（另 2 条是负向守卫，本就不依赖修复，符合预期）。

## 5. 验证汇总

| 门 | 结果 |
|----|------|
| `pytest -q` | **2398 passed, 0 failed** |
| `python -m wiki_engine lint` | **0 errors**, 1 warning, 4 info（与基线持平） |
| `cd web && npm run lint` | **0 errors** |
| 基准两轮 | 99.1 / **100.0**，#113 #117 均转 ✅ 且不摆动 |
| 逐题对比 | 零退化，差异全为改善 |
| 工作区 | 跑完全量 pytest 后无 `wiki/indexes/` 产物污染（上一轮 C2 成果保持） |

未改 gold、未手工 UPDATE 数据库、未动 `FUZZY_MAX_EDITS` 判据、未削弱 `rag_search`。

## 6. 教训

1. **`tool_calls` 里的 `rag_search` 可能不是模型调的。** `loop._fallback` 会自己追加一个，
   所以「序列末尾有 rag_search」是**降级的指纹**而不是模型的选择。只看工具名列表会把
   「模型偏好查 PDF」这个错误结论坐实——必须记入参与返回摘要才看得出是一步就降级了。

2. **「答案来自 PDF」不等于「路由偏好错了」。** 两题模型都第一时间查了结构库，
   是查空后被降级机制送去 PDF 的。按表象改提示词/工具描述会完全打偏。

3. **降级会丢掉已经查到的东西。** #117 里第一步 `get_entity` 明明成功了，
   第二步查空触发的降级把它一起扔了。判空谓词的作用域是**单个工具的这一次返回**，
   但后果是**整轮上下文清零**——给 `_EMPTY_CHECKS` 加工具时必须按「最坏情况：
   前面所有成果作废」来评估。

4. **归一化和放宽阈值是两件事。** `·` vs `.` 是同名异写，该在归一层判 exact；
   把它交给 fuzzy 会同时放松真正的错配防线。判 exact 还是 fuzzy 在这里是**功能性**的，
   因为下游 `find_datasheet` 只信 exact——「解析到了」不代表「用得上」。

5. **库内数据自己就不统一。** `_zh_to_id` 里 30 个键用 `·`、6 个用 `.`，
   谁也不是错的，错的是假设它统一。改前先数一遍分布（本轮 71 个归一键 / 0 冲突 / 0 退化），
   比事后解释便宜得多。
