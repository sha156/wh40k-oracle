# #118「同名跨阵营单位不消歧」修复报告

日期：2026-07-27　分支：`gnhf/40k-d-project-py-rag-bf5362`
基线：pytest 2372 passed / 基准 114 题 109 ✅ / wiki lint 0 error / 前端 lint 0 error

## 1. 病灶：基准 #118 判红的原文

问：**地狱兽（Helbrute）现在多少点？**

第九轮（`qa_agent_results_r9_salvage.json`）的实际回答：

> 地狱兽（Helbrute）当前点数为 **120 分**（1 个模型）。[《战锤40K 11版》兵牌数据]
>
> `meta.tool_calls = ["get_datasheet"]`，`degraded=false`

judge 判词：

> ❌ 回答只给出了一个点数（120分），未说明这是哪个阵营的地狱兽，也未列出其他三个阵营的
> 不同点数，与标准答案要求必须消歧或逐一列出的关键事实矛盾。

正中 gold 列出的判错情形 **①「只报一个点数当成唯一答案、不说明是哪个阵营」**。

## 2. 事实核查：工具到底把 4 张兵牌怎么返回给模型的

先查证据，再动手。库里 `name_en='Helbrute'` 确实是 4 张各自独立的兵牌：

```
units name_en=Helbrute: [('000000954','Helbrute','CSM'), ('000001046','Helbrute','DG'),
                         ('000001021','Helbrute','TS'), ('000002632','Helbrute','WE')]
name_zh:                 4 行全部是「地狱兽」
```

修改前，直接调用工具拿到的**实际返回值**：

| 调用 | 返回 |
|---|---|
| `entity_resolver("Helbrute")` | `canonical_id=null`, `confidence="ambiguous"`, `candidates=[Helbrute (CSM/DG/TS/WE)]` ✅ 如实报歧义 |
| `entity_resolver("地狱兽")` | `canonical_id="000002632"`, `name_en="Helbrute"`, **`confidence="exact"`**, `candidates=[]` ❌ 四选一却报 exact |
| `calc_points(["Helbrute"])` | `unresolved`，**一个点数都不给**，只回候选串 |
| `calc_points(["地狱兽"])` | 单条 `{"points": 120, "resolved_via": {"confidence": "exact"}}` ❌ 悄悄给了吞世者那张 |
| `get_datasheet("地狱兽")`（#118 实走路径） | 单张 WE 兵牌，**返回里没有任何一处提到还有另外 3 张** |

**问题层定位**：不是模型只挑一个说，而是**工具本来就只给了一个，且自称 exact**。

根因在两处「只做了一半」的消歧：

1. `db_compile/datasheet.py::find_datasheet` 只在**英文名**直查 `units.name_en` 多命中时抛
   `AmbiguousUnitName`（评审 #25 的通道）。**中文名根本走不到这个分支**——它落到函数末尾的
   `EntityResolver.resolve()`。
2. `db_compile/entity_resolver.py` 里，英文侧有 `_en_buckets`（「英文名 → 全部 cid」，
   碰撞时如实报 ambiguous），而中文侧 `_zh_to_id` 是**扁平的「中文名 → 单个 cid」字典**——
   4 个 Helbrute 的碰撞在建索引时就被折叠掉了，`resolve("地狱兽")` 只剩一个赢家，
   还带着 `confidence="exact"`。`find_datasheet` 只信 exact，于是稳稳返回吞世者那张。

一句话：**评审 #25 修好了英文那半边，中文这半边的同型缺陷留到了 #118 才暴露。**

## 3. 为什么不在 resolver 层「把中文也改成报 ambiguous」

这是最直觉的改法，但先量了它的面：

```
zh names whose cid collides ACROSS factions: 212
zh names colliding within SAME faction (dup rows): 9
```

**212 个中文名**会从 exact 翻成 ambiguous——瘟疫战士、卡迪安突击队、机械教游侠、
黎曼鲁斯坦克指挥官…… 一大片是 AM/GC、CD/CSM 这类「盟友阵营各自重印同一单位」。
翻掉它们会让 `find_datasheet` 对这 212 个名字**全部返回 None**（它只信 exact），
把一堆现在答得好好的题推向 gold 判错情形 ②（拒答），直接违反「既有 114 题不得退化」。

所以本轮**不动 resolver 的返回语义**，改在工具边界做**严格追加式**的补报。

## 4. 改动

### 4.1 `db_compile/datasheet.py`：新增只读 `same_name_factions(db_path, unit_id)`

按已解析到的 `unit_id` 反查同 `name_en` 的兄弟行，返回 `(id, name_en, faction_id)` 列表。
**只在阵营数 > 1 时返回**——同阵营内的重复行（上游 Wahapedia 按「书」建模的重印，
见 `2026-07-27-duplicate-units-audit.md` 的 11 组 22 行）不是跨阵营歧义，不许误报。

### 4.2 `agent/tools.py::get_datasheet`：补上中文名那半边歧义

拿到兵牌后按 `unit_id` 反查兄弟行；有兄弟行就追加 `same_name_other_factions`
（各候选的 `候选名 / 阵营 / 点数 / 是不是上面回答的那一张`）+ `note`。
**`found` 仍为 `True`，兵牌照常返回**——这是躲开判错情形 ② 的关键。
顺带把 `stat_conflicts` 那句 note 从**覆盖**改成**追加**，否则消歧铁律会被它顶掉。

### 4.3 `agent/tools.py::calc_points`：名字解析成功 ≠ 名字无歧义

- 中文名解析成功的条目：保留已查到的点数，追加同名兄弟行与各自点数；
- 英文名多命中（此前 `unresolved`、一个点数都不给）：新增 `_points_for_candidates()`
  把 `Helbrute (CSM)` 这类候选串逐个解析出点数，整包给模型；
- **纯 canonical id 入参的行为一个字节没变**（军表 / web 按 id 直调的既有约定），
  已由 `test_plain_canonical_id_input_is_unchanged` 钉死。

### 4.4 note 措辞同时防三种判错

```
⚠️ 同名跨阵营：…… 全部候选及各自点数见 same_name_other_factions，均取自结构库，不是记忆。   ← 防 ③
作答时**必须消歧**，二选一：要么把各阵营的数值逐一列出并指出差异，
要么明确写出「以下按 XX 阵营的〈单位名〉回答」。禁止只报其中一个数值却不说明它属于哪个阵营。 ← 防 ①
⚠️ 同时禁止因为有歧义就拒答、或在未给出任何已查证数值前就把问题退回用户提问——
候选和点数本返回里都已给全 ……                                                          ← 防 ②
```

三种错法互斥，一条 note 必须同时挡住；写法沿用 #63 / #109 的做法：把因果写进代码注释。

## 5. 修改后的实际返回值

`get_datasheet("地狱兽")` → `found=true`，`datasheet` 仍是 WE 那张，另附：

```json
"same_name_other_factions": [
  {"candidate": "Helbrute (CSM)", "unit_id": "000000954", "faction": "CSM", "points": 130,
   "is_the_one_answered_above": false},
  {"candidate": "Helbrute (DG)",  "unit_id": "000001046", "faction": "DG",  "points": 110,
   "is_the_one_answered_above": false},
  {"candidate": "Helbrute (TS)",  "unit_id": "000001021", "faction": "TS",  "points": 110,
   "is_the_one_answered_above": false},
  {"candidate": "Helbrute (WE)",  "unit_id": "000002632", "faction": "WE",  "points": 120,
   "is_the_one_answered_above": true}
]
```

四个数值与 gold（CSM 130 / DG 110 / TS 110 / WE 120）逐条一致，**全部来自结构库**。

`calc_points(["Helbrute"])` 由「零点数 + 候选串」变为四个阵营的点数全给。

#109 的四个泰坦回归验证：`calc_points` 返回**逐字段与修改前相同**
（1100 / 2200 / 2600 / 3500，无兄弟行、无新增顶层键）——泰坦只有 TL 一个阵营，不触发本通道。

## 6. 验证

| 项 | 基线 | 本轮 |
|---|---|---|
| pytest | 2372 passed | **2378 passed**（+6） |
| 新增测试对旧实现 | — | **4 failed**（另 2 条是「行为不许变」的反向对照，本就该绿） |
| `python -m wiki_engine lint` | 0 error / 1 warning | **0 error / 1 warning** |
| `cd web && npm run lint` | 0 error | **0 error** |

三题锚点 verdict（逐题对比 `qa_agent_results_r9_salvage.json`）：见下节。

全程**未改 gold**、**未写库**（新增函数只读；未跑任何 `--apply`）。

## 7. 基准逐题对比

对照 `benchmarks/v3_edition11/qa_agent_results_r9_salvage.json`（114 题），
连跑两轮（`..._same_name_disambig.json` / `..._run2.json`，均 96.5，degraded 32）：

```
== run1 vs r9 ==            == run2 vs r9 ==            == run2 vs run1 ==
共有题 verdict 差异数: 1     共有题 verdict 差异数: 1     共有题 verdict 差异数: 0
  #118: ❌ -> ✅              #118: ❌ -> ✅
锚点 #63:  ✅ -> ✅           锚点 #63:  ✅ -> ✅
锚点 #109: ✅ -> ✅           锚点 #109: ✅ -> ✅
锚点 #118: ❌ -> ✅           锚点 #118: ❌ -> ✅
```

**三题锚点前后 verdict**：

| 题 | 方向（gold 判错情形） | r9 基线 | 本轮 run1 | 本轮 run2 |
|---|---|---|---|---|
| #118 | ① 只报一个点数不说阵营 | ❌ | ✅ | ✅ |
| #63 | ② 因歧义拒答/退回用户 | ✅ | ✅ | ✅ |
| #109 | ③ 凭记忆编否定性断言 | ✅ | ✅ | ✅ |

其余 113 题两轮**逐题零变动**——连已知波动的 #41/#42 这次都没互换。
准确率 95.6 → **96.5**。仍红的 #113/#114/#115 是库内点数过期，等 `mfm --apply`
拍板后转绿，本轮未碰（红线要求）。

#118 修复后的实际回答：

> 地狱兽（Helbrute）的点数因阵营而异：
> - **吞世者（World Eaters）**：120 点
> - **混沌星际战士（CSM）**：130 点
> - **死亡守卫（Death Guard）**：110 点
> - **千子（Thousand Sons）**：110 点

judge：✅ 回答完整列出了四个阵营的地狱兽点数，与标准答案完全一致，且明确指出了阵营差异。

## 8. 遗留

`EntityResolver` 中文侧 `_zh_to_id` 仍是扁平表、对 **212 个**跨阵营同名中文名照报
`confidence="exact"`——本轮是在工具边界**补报**歧义，没有修掉这个上游事实。
真要修得在 resolver 建 `_zh_buckets` 并让 `find_datasheet` 把「resolver 报 ambiguous」
也转成 `AmbiguousUnitName`（否则那 212 个名字会全部返回 None）；那是独立一轮的事，
且必须连基准一起重跑。本轮的追加式改法对这 212 个名字都生效（凡解析到的行有跨阵营
兄弟行就披露），只是不改变解析结果本身。

