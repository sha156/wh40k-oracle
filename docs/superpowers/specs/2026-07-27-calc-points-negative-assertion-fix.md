# 修「工具查不到 → 模型编否定性断言」硬错（基准 #109，2026-07-27）

**结论先说**：#109 由 ❌ 转 ✅，与紧邻基线 `qa_agent_results_points_coverage.json`
逐题对比 **113 题里只有 #109 一条 verdict 变化，其余 112 题零变动**。
成绩 95.6 → **96.5**（109 ✅ / 1 ⚠️ / 3 ❌）。剩下 3 道红全是 #113–#115，
根因是库内点数过期、`mfm --apply` 后自然转绿，**本轮按红线未碰**。
`pytest -q` **2365 passed**（+6 条新用例，逐条验证过对旧实现真会红），
`wiki_engine lint` 0 error / 1 warning，`web` eslint 0 error。**全程零写库**。

---

## 1. 病灶：一次查询失败被升级成了一条事实断言

基准 #109 问「泰坦军团四个泰坦各多少分」，修前系统答：

> 泰坦军团（Adeptus Titanicus）是独立的桌面游戏，并非战锤40K的阵营，因此战犬泰坦、
> 掠夺者泰坦、天罚战争使者泰坦、战将泰坦在战锤40K第11版规则中均无官方点数。
> 建议查阅《Adeptus Titanicus》规则书获取其点数。

这段话里**每一个断言都是错的**：Adeptus Titanicus 是 11 版正经阵营，有官方 Faction Pack、
官方 MFM 有 titan-legions 阵营页、库里有 4 行、wiki 里有 4 页，四个点数库＝官网完全一致
（1100 / 2200 / 2600 / 3500）。

链路只有一步：

| 环节 | 实际发生 |
|---|---|
| agent 选工具 | intent=算 → 选 `calc_points`，把用户原文四个中文名整体传进 `unit_list` |
| `calc_points` | 底层 `db_compile.calc_points` 是**纯 `units.id` 查表**，中文名一律返回 `"未找到该 unit id"` |
| loop | `calc_points` **不在** `_EMPTY_CHECKS` 里 → 不判空 → 不降级 `rag_search` 兜底 |
| 模型 | 拿到一次全空返回，没有任何工具证据，于是凭记忆作答——把「工具没查到」读成了「这些东西不存在于 40K」 |

对照证据：同样四个泰坦**逐个单独问**（#110–#112 同型）全对，因为那条路由走的是
`get_datasheet`，它内部本来就会做名字解析。**错的从来不是数据，是这条空手返回。**

## 2. 改了什么，为什么这么改

### 2.1 `agent/tools.py::calc_points` —— 补上名字解析（根本修法）

评估结论：**代价小、不破坏既有约定，所以做了根本修法而不是只改措辞。**

- 底层 `db_compile/calc_points.py` **一行没动**，仍是纯 id 查表。它被军表/web 侧按
  canonical id 直调（`agent/tools.py:581` 的 `_calc_points_impl(db_path, [cid])`、
  `engines/roster/`），那条约定必须保持。
- 名字解析加在 **agent 包装这一层**：先按 id 查（纯 id 入参的行为**逐字节不变**，
  连解析器都不会被构造），**只对返回「未找到该 unit id」的那几个**走 `entity_resolver`
  取 canonical id 后重查一次。
- 实测四个泰坦的中文名 `entity_resolver` 全部 `confidence=exact` 命中，
  解析成本就是一次已有的单例查询。

顺带解决了目标里的第 3 件事（**多单位漏项**）：四个名字在同一次 `calc_points` 里
全部解析成功、一次性返回四条，模型不再只答一个。修后回答见 §3。

返回值新增三个字段，都是给模型看的：
`query`（这条对应用户原文里的哪个名字）、`resolved_via`（解析到哪个 id、置信度）、
`unresolved: true`（这条确实没解析到）。

### 2.2 `calc_points` 查空时的 note —— 把「查不到 ≠ 不存在」当场说穿

参照本分支 `1efb6e5c` 修 #63 的同型做法（把因果写进注释，防止以后被改回去）：

```python
# ⚠️ 「本工具没查到」和「这个单位不存在」是两件事，工具返回里必须把这句话说穿。
# 基准 #109（一次问四个泰坦的点数）实测：calc_points 只按 units.id 精确查表，四个中文名
# 全部返回「未找到该 unit id」，模型把这个**查询失败**升级成了**否定性事实断言**——
# ...而事实相反：Adeptus Titanicus 是 11 版正经阵营，库里四行点数与官网逐条一致。
_CALC_POINTS_UNRESOLVED_NOTE = (
    "未能把这个名字解析到库内任何单位（本工具按 units.id 精确查表）。"
    "⚠️ 查不到 ≠ 该单位或该阵营不存在，也 ≠ 它没有官方点数——只说明这次名字解析没命中。"
    "请改用 get_datasheet 传用户原文里的中文名重查，或先用 entity_resolver 取 canonical id "
    "再回来算分；全都查不到就如实说「档案缺失」。"
    "禁止据此输出「该单位/阵营不存在」「不属于战锤40K」「无官方点数」这类否定性断言。"
)
```

这条 note 同时挂在**每个** unresolved 单位上和**顶层** `note` 上——顶层那条会点名
哪几个名字没解析到，模型不用自己去数。

### 2.3 `agent/loop.py::_EMPTY_CHECKS` —— 一个都没解析到就降级兜底

```python
"calc_points": lambda r: (not r.get("found")
                          or bool(r.get("units"))
                          and all(u.get("unresolved") for u in r["units"])),
```

判据刻意写成「**全部** unresolved 才算空」：

- **「查到了但库里没点数」不算空**（`MISSING_COST_NOTE`）——那是诚实答案，
  被 `rag_search` 兜底吞掉反而更差。
- 部分命中也不算空——有证据就该拿证据作答。

这条是 §2.1/§2.2 之外的**第三道防线**：万一名字解析也全灭，模型至少拿到的是兜底检索
的原文片段，而不是一片空白 + 自己的记忆。

### 2.4 `agent/llm_client.py` 提示词 —— 一条通用铁律 + calc_points 参数提示

工具侧的 note 只能管 `calc_points` 这一个工具；同样的失效模式在任何工具查空时都可能复发，
所以在 `_NEXT_STEP_CONTRACT` 的铁律段加了通用形式：

```
- **工具查不到 ≠ 该事物不存在**。工具返回 "found": false / "unresolved" / 「未找到」时，
  只说明这条查询路径没命中，必须换工具或换名字再查一次（get_datasheet / entity_resolver /
  rag_search 兜底）。**绝不允许**据此凭记忆输出「这个单位/阵营不存在」「不属于战锤40K」
  「没有官方点数」之类的**否定性事实断言**——查不到就说查不到。
```

`_TOOL_ARG_HINTS["calc_points"]` 补了两句：中文名/英文名/id 都收；一次问多个单位就
全部放进同一个 `unit_list`，**问了几个就要答几个**（针对漏项那一半）。

## 3. #109 修复前后的实际回答对比

| | 修前（`..._points_coverage.json`） | 修后（`..._calc_points_honesty.json`） |
|---|---|---|
| 工具链 | `['calc_points']` | `['calc_points']`（同一条，返回内容变了） |
| verdict | ❌ | ✅ |
| judge 理由 | 「回答声称泰坦军团是独立游戏、四个泰坦在战锤40K第11版中均无官方点数，这与标准答案明确给出的四个具体点数（1100、2200、2600、3500分）相矛盾，属于事实错误」 | 「系统回答完整覆盖了标准答案中四个泰坦的全部官方点数，且数值完全一致，直接回答了问题」 |

**修前回答**：

> 泰坦军团（Adeptus Titanicus）是独立的桌面游戏，并非战锤40K的阵营，因此战犬泰坦、
> 掠夺者泰坦、天罚战争使者泰坦、战将泰坦在战锤40K第11版规则中均无官方点数。
> 建议查阅《Adeptus Titanicus》规则书获取其点数。

**修后回答**：

> 泰坦军团（Adeptus Titanicus）的四个泰坦官方点数如下：
> - 战犬泰坦（Warhound Titan）：1100分
> - 掠夺者泰坦（Reaver Titan）：2200分
> - 天罚战争使者泰坦（Warbringer Nemesis Titan）：2600分
> - 战将泰坦（Warlord Titan）：3500分

四个值与 gold 逐条一致，且**四个都给了**（覆盖面题的另一半要求）。

工具返回层面的前后对比（真库直调）：

| 入参 | 修前返回 | 修后返回 |
|---|---|---|
| `["战犬泰坦"]` | `unit_id="战犬泰坦", points=null, note="未找到该 unit id"` | `unit_id="000000867", name_en="Warhound Titan", points=1100, resolved_via={canonical_id:"000000867", confidence:"exact"}` |
| `["某个根本不存在的单位XYZ"]` | 同上，note 就四个字「未找到该 unit id」 | `unresolved: true` + 顶层 `unresolved: [...]` + 明确禁止否定性断言的 note |
| `["000000867"]`（纯 id） | `points=1100` | `points=1100`（**逐字节不变**，不触发解析器） |

## 4. 逐题 verdict 差异表（vs 紧邻基线）

基线 `benchmarks/v3_edition11/qa_agent_results_points_coverage.json`（113 题 / 95.6）
→ 本轮 `benchmarks/v3_edition11/qa_agent_results_calc_points_honesty.json`（113 题 / 96.5）：

| 题 | 基线 | 本轮 | 工具链变化 | 说明 |
|---|---|---|---|---|
| #109 | ❌ | **✅** | `['calc_points']` → `['calc_points']` | 本轮修的那道 |
| 其余 **112** 题 | — | — | — | **verdict 差异 0 条** |

本轮仍非绿的 4 题，逐条说明：

| 题 | verdict | 是否本轮引入 | 原因 |
|---|---|---|---|
| #41 兽人小子 | ⚠️ | 否 | 既有漂移（`get_entity` exact 命中致 agent 走查表不检索规则书），已在 README 留档；**且它是已知波动题**，见下 |
| #113 基里曼 | ❌ | 否 | 答 320 / gold 355 —— 库内点数过期，`mfm --apply` 后转绿，**本轮按红线不碰** |
| #114 卡尔加 | ❌ | 否 | 答 140 / gold 155 —— 同上 |
| #115 坎托 | ❌ | 否 | 答 90 / gold 80 —— 同上（降价方向） |

**连跑两轮判波动**（同一份代码跑第二遍，结果落 `%TEMP%`，不入库）：

| | 第一轮 | 第二轮 |
|---|---|---|
| 成绩 | 109 ✅ / 1 ⚠️ / 3 ❌ = 96.5 | 109 ✅ / 1 ⚠️ / 3 ❌ = 96.5 |
| 两轮 verdict 差异 | \#41（⚠️→✅）、#42（✅→⚠️） —— 都是 README 早已点名的固定波动题 | |
| **#109** | ✅ | ✅ |
| #113/#114/#115 | ❌ | ❌ |

#109 两轮稳定 ✅，不是波动侥幸。

## 5. 新增测试（每条都验证过对旧实现真会红）

`git stash` 掉 `agent/tools.py` + `agent/loop.py` 后跑新用例：**5 failed, 4 passed**
（4 个 passed 是既有用例），即 5 条新用例全部真的钉住了本轮行为。

| 测试 | 钉住什么 |
|---|---|
| `TestCalcPoints::test_unknown_name_note_forbids_negative_assertion` | **停止条件点名要求的那条**：查不到时 note 必须含「查不到 ≠」「否定性断言」「get_datasheet」，且工具自己绝不给出「不存在」结论 |
| `TestCalcPoints::test_chinese_name_is_resolved_to_id_not_reported_as_unknown` | 中文名要真的解析到 id，且不带 `unresolved` |
| `TestCalcPoints::test_all_names_unresolved_counts_as_empty_for_loop` | 全灭→判空降级；**部分命中不判空**（诚实答案不许被兜底吞掉） |
| `TestCalcPoints::test_resolver_failure_does_not_crash_the_whole_call` | 解析器炸了只让那一个名字变 unresolved，不带崩整次算分 |
| `TestCalcPointsRealDbTitanRegression::test_four_titans_all_resolved_with_official_points` | 真库钉子：四个中文名一次问，必须回四条且＝1100/2200/2600/3500（问四个不许只答一个） |
| `test_llm_client.py::test_next_step_system_prompt_bans_negative_assertions_on_lookup_miss` | 通用铁律真的渲染进发给模型的 system prompt |

## 6. 验证与红线核对

| 项 | 结果 |
|---|---|
| `pytest -q` | **2365 passed**（基线 2359，+6） |
| 基准 | 113 题 109 ✅ / 1 ⚠️ / 3 ❌ = **96.5**，`benchmarks/v3_edition11/qa_agent_results_calc_points_honesty.json` |
| 逐题对比紧邻基线 | **仅 #109（❌→✅），其余 112 题零变动** |
| `python -m wiki_engine lint` | **0 errors**, 1 warnings, 4 info（与基线持平） |
| `cd web && npm run lint` | **0 error**（无输出） |
| 改 gold | **零**。`qa_gold.json` 未改动（`git status` 里没有它） |
| 放宽判分口径 | **零**。`scripts/qa_bench.py` 未改动 |
| 写库操作 | **零**。`db/wh40k.sqlite` SHA-256 = `2DC2108E5E9F58DCEB39F56041250D624951CDEB249AE39225DEB853D555B4DD`，与前两轮报告记录的一致；mtime 仍是 2026-07-27 02:27:39 |
| 临时脚本残留 | **零**。第二轮基准结果写在 `%TEMP%`，仓库根目录无新增文件 |

改动文件：`agent/tools.py`、`agent/loop.py`、`agent/llm_client.py`、
`tests/test_agent_tools.py`、`tests/test_llm_client.py`、本报告、
`benchmarks/v3_edition11/README.md`、结果 json。

> 行尾提醒（复发第 N 次）：Edit 会把 `agent/llm_client.py` / `tests/test_llm_client.py`
> 整文件写成 CRLF，`git diff --stat` 立刻涨到 656/538 行的假 diff。
> 判据是 `git diff --ignore-cr-at-eol --stat` 与 `git diff --stat` 对不上，
> 修法是把文件按 LF 重写一遍（本轮已做，最终 diff 194 插入 / 12 删除）。
