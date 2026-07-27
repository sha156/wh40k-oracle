# 4 个查询类工具「查不到 / 空结果」路径排查（2026-07-27）

延续 #63（`get_entity` ambiguous 死胡同，`1efb6e5c`）与 #109（`calc_points` 查空 →
模型编否定性断言，`56849c04`）暴露的同一个失效模式——**工具返回的技术性状态被模型翻译成
关于世界的结论**——本轮把同型排查铺到另外 4 个「按名字/查询取数据」的工具上。

排查口径对每个工具固定三项：

- **a 空/失败返回的措辞**：会不会被读成「这个东西不存在」而不是「这条路径没查到」？
- **b `_EMPTY_CHECKS` 覆盖**（`agent/loop.py:42-60`）：**双向**——漏判空（该兜底不兜底，#109）
  与误判空（把有效结果当空而降级，会吞掉诚实答案）。第三态「查到了但结果确实是没有」
  是诚实答案，不该被兜底吞掉。
- **c 有没有指引下一步**：告诉模型换哪个工具 / 换什么参数再查。

## 排查表

| 工具 | a 空返回措辞 | b `_EMPTY_CHECKS` 双向 | c 下一步指引 |
|---|---|---|---|
| `get_datasheet`（`agent/tools.py:273`） | **无问题（措辞对模型不可达）** | **无问题** | **无问题（由降级接管）** |
| `rag_search`（`agent/tools.py:358`） | **已确认缺陷 → 已修** | **无问题（有意不纳入）** | **已确认缺陷 → 已修** |
| `entity_resolver`（`agent/tools.py:90`） | 无问题（原本**没有任何 note**，不存在误导措辞） | **无问题** | **已确认缺陷 → 已修** |
| `get_keyword_definition`（`agent/tools.py:155`） | **无问题** | **无问题** | **无问题（由降级接管）** |

### 判据里反复用到的一条结构事实

`agent/loop.py:209`：

```python
if tool_name != "rag_search" and _is_empty_result(tool_name, result):
    return self._fallback(user_input, intent, tool_calls, reason=f"{tool_name} 空结果")
```

被判空的工具结果**根本不会写进 messages**，模型看不到它的 note，直接由 `_fallback`
接管作答（`loop.py:216-248`，输出固定的「⚠️ 已降级到兜底检索…」诚实文案）。
因此「a 措辞风险」只在**判空判不到的分支**上才是真风险；而 `rag_search` 被这行显式排除，
它是**唯一一个空手结果一定会被模型看到**的工具。

---

## 逐个工具的结论与证据

### 1. `get_datasheet`（`agent/tools.py:273-334`）

- **a**：未命中返回 `agent/tools.py:315` —— `{"found": False, "datasheet": None,
  "note": "库中未找到该单位"}`。措辞已把范围限定在「库中」，但**没有** #109 那句
  「查不到 ≠ 不存在」的显式界线。**判定：有措辞改进空间，但当前对模型不可达** ——
  这条返回满足 `_EMPTY_CHECKS["get_datasheet"]`（`loop.py:52-53`）→ 被 `loop.py:209`
  拦下降级，模型看不到这句话。为避免制造零行为收益的改动，本轮**不改**它；
  留一条点名遗留：若将来 `get_datasheet` 被接到**不降级**的路径上（web / 其它 agent /
  被别的工具内嵌复用），这句措辞必须同步补上界线句。
- **b**：`lambda r: (not r.get("found") and r.get("reason") != "ambiguous")`。
  逐分支核对——`ds is None`（:315）判空 ✓；DB 文件不存在（:289）判空 ✓（基础设施失败
  降级合理）；`reason == "ambiguous"`（:307）判**非空** ✓（评审 #25 通道，模型要按 note
  逐候选重查）；`found=True` 非空 ✓。**双向都正确。**
- **c**：ambiguous 分支的 note（`agent/tools.py:310-313`）本身就是正面样板：
  「请按问题上下文用候选名（含阵营缩写）重查其一；无法确定阵营时，逐一列出各候选数值作答，
  绝不要只挑一个当作唯一答案」，并附 `candidates_preview` 各候选核心属性。
  其余空手分支由降级接管。**无问题。**

### 2. `rag_search`（`agent/tools.py:358-388`）—— 已确认缺陷，已修

- **b 先说**：它**不在** `_EMPTY_CHECKS` 里，且 `loop.py:209` 额外用
  `tool_name != "rag_search"` 把它排除。这是**正确的**：它自己就是兜底目标，
  降级到自己没有意义。**无缺陷。**
- **a / c 的真问题**：正因为 b 的正确设计，它的返回是模型作答前看到的**最后一句话**，
  而修复前三种失败态共用同一个形状 `{"found": False, "passages": []}`：

  | 失败态 | 修复前返回 |
  |---|---|
  | 知识库未构建 | `note: "知识库未构建（local_vector_store 为空），请先跑 ingest.py"` |
  | 调用异常 | `note: f"rag_search 异常: {exc}"` |
  | 检索跑通但零命中 | `note: "未检索到相关段落"` |

  模型无从区分「**语料里没有**」和「**检索管线自己坏了**」，且三者都没有下一步指引——
  这正是 #109 的形状（工具故障被写成「档案里没有这条规则」的否定性事实断言），
  而且这里连 `_EMPTY_CHECKS` 兜底都按设计不存在。
- **实测补充（改变了风险排序）**：`app.hybrid_retrieve` 没有相关度阈值，FAISS 恒返 k 条，
  所以「零命中」分支在正常环境下**几乎不可达**——实测用一个凭空捏造的名字
  （「炽炎风暴龙 Flamestorm Drake 的属性和点数」）检索，返回 `found=True` 共 8 条
  （全是不相关段落）。**真正可达的失败态是环境/异常两条**，它们恰恰是「不该被读成
  内容缺失」的那两条。
- **修法**（`agent/tools.py:344-388`）：按失败性质分流并给机器可读标志。
  - `error: True` = 检索侧环境故障（知识库未构建 `:369`、调用异常 `:386`），
    note 追加 `_RAG_UNAVAILABLE_HINT`（`:351`）：「⚠️ 这是**检索侧环境故障**，
    不是「语料里没有相关内容」——不可据此判断该规则/单位是否存在…禁止输出任何否定性事实断言」。
  - 无 `error` 且 `found: False` = 检索跑通、零命中，note 换成 `_RAG_EMPTY_NOTE`（`:344`）：
    「⚠️ 没检索到 ≠ 该规则或该单位不存在」+ 换关键词/换 `get_datasheet` / `get_entity` /
    `get_keyword_definition` 的下一步 + 禁止否定性断言。
  - 命中时不带 `error`（负向成对，防止把有效结果当故障丢掉）。

### 3. `entity_resolver`（`agent/tools.py:90-104`）—— 已确认缺陷（c 项），已修

- **a**：修复前返回**只有** `canonical_id / name_en / confidence / candidates` 四个键，
  **一句 note 都没有**。既然没有措辞，就谈不上误导措辞——a 项无问题。
- **b**：`loop.py:48-49` `lambda r: (not r.get("canonical_id") and not r.get("candidates"))`。
  对着 `db_compile/entity_resolver.py` 的四个 confidence 出口逐条核：
  `exact`（:130/:139/:142/:148）与 `fuzzy`（:160/:161）带 canonical_id → 非空 ✓；
  `ambiguous`（:120-121 同名跨阵营桶、:163 模糊多命中）无 id 但有候选 → **非空** ✓
  （与评审 #25 一致，候选是实质回复）；`none`（:165）无 id 无候选 → 判空降级 ✓。
  **双向都正确**，且已有成对护栏
  （`tests/test_agent_loop.py:415` / `:429`）。本轮**没有改动判空口径**。
- **c —— 缺陷**：`ambiguous` 是这个工具**唯一会被模型看到**的空手态（`none` 被判空降级），
  而它此前既不降级、也没有任何下一步指引，模型拿到的是一个裸 dict —— 正是 #63
  「不降级也不作答」的形状。横向对照：`get_entity` 已于 `1efb6e5c` 拿到逐候选重查的 note，
  `get_datasheet` 的 ambiguous 分支一直有 note，**本通道里只有 `entity_resolver` 是空白**。
- **修法**（`agent/tools.py:75-104`）：`canonical_id` 为空时按有无候选补两条 note——
  `_RESOLVER_AMBIGUOUS_NOTE`（`:75`）指挥模型把 `名字 (阵营缩写)` 候选串**原样回填**重查
  （`db_compile/entity_resolver.py:132-139` 的消歧语法支持原样回填精确命中），
  并把「反问用户」降级为查证候选之后的兜底；`_RESOLVER_MISS_NOTE`（`:81`）说穿
  「解析不到 ≠ 该单位或该阵营不存在」并指路 `get_datasheet` / `get_entity` / `rag_search`，
  明令禁止否定性断言。**判空口径一行未动**（新增的是 note 键，谓词只读
  `canonical_id` / `candidates`），并配了钉死这一点的用例。

### 4. `get_keyword_definition`（`agent/tools.py:155-180`）

- **a**：`agent/tools.py:180` —— `"未找到该关键词的术语页"`。措辞已限定到
  「术语页」这条具体路径，不是关于世界的断言；`:161` 的「core-rules 目录不存在」
  是明确的基础设施状态。**无问题。**
- **b**：`loop.py:47` `lambda r: not r.get("found")`。函数只有三个出口——目录不存在
  （:161）、slug/名字匹配命中（:170/:178，`found=True` 必带 page）、全表扫完未命中（:180）。
  两个 False 出口都判空 ✓，命中出口非空 ✓。**双向都正确。**
- **c**：两条 False 出口都会被 `loop.py:209` 拦下降级 classic，指引由 `_fallback` 接管，
  模型看不到该返回。**无风险。**

---

## 顺带查到、但**本轮不改**的观察项（留给后续轮次）

0. **【新缺陷 · 已被 #118 钉住】`get_datasheet` 的歧义守卫只挡英文名，中文名入口静默取一。**
   评审 #25 立的规矩是「同名单位存在于多个阵营，静默取一会答错阵营数据」，
   但守卫只长在 `name_en` 那条查询上——`db_compile/datasheet.py:205-216`：

   ```python
   hits = conn.execute(
       "SELECT id, name_en, faction_id FROM units WHERE name_en = ? COLLATE NOCASE", (name,))
   ...
   if len(hits) > 1:
       raise AmbiguousUnitName(...)
   ...
   resolved = r.resolve(name)                      # 中文名从这里走
   if resolved.canonical_id and resolved.confidence == "exact":
       return lookup_datasheet(db_path, resolved.canonical_id)   # ← 单个 id，零歧义信号
   ```

   中文名在 `name_en` 上恒 0 命中 → 落到 `entity_resolver.resolve()` → `_zh_to_id`
   （`db_compile/entity_resolver.py:104` 用 `setdefault`，**先入者胜**）→ `exact` →
   直接返回**其中一张**兵牌，`reason` / `candidates` 一个都没有。
   而提示词恰恰要求模型**直接传用户原文里的中文名**给 `get_datasheet`
   （`agent/llm_client.py:98-100`），也就是说**主路径正好是没有守卫的那条**。

   **证据**：本轮新增基准题 #118「地狱兽（Helbrute）现在多少点？」实测判 ⚠️，
   记录里 `tool_calls: ["get_datasheet"]`、`degraded: false`、答案只给了 120 点
   （= 吞世者那张兵牌），judge 理由「未列出其他三个阵营」；
   而同一个单位用英文名 `get_datasheet("Helbrute")` 会正常抛 ambiguous + 4 个候选预览。
   两条路径的行为不一致，差别就在上面那段代码。

   **本轮不改的原因**：它属于「查到了但只查到一部分」而不是本轮口径里的「查不到/空结果」，
   且修法要动 `find_datasheet` 的中文分支（多命中要抛 `AmbiguousUnitName`），
   会波及所有用中文名问同名跨阵营单位的既有题（如 #25「吞世者的地狱兽…」），
   必须连基准整轮重跑一起做。#118 留在基准里**当红**钉住它，与 #113-#115 同样的处理方式。

1. **`entity_resolver` 的 fuzzy 会静默命中不相干单位。** 实测
   `entity_resolver("Flamestorm Drake")` → `canonical_id=000000918`、
   `name_en="Firestorm Redoubt"`、`confidence="fuzzy"`；`get_entity("Flamestorm Drake")`
   直接 `found=True` 返回 Firestorm Redoubt 的实体页。这是
   `difflib.get_close_matches(cutoff=FUZZY_CUTOFF)` 的正常行为，但对模型而言是
   **一个凭空的名字换回了一张看起来很正经的兵牌**——属于「查错了」而非「查不到」，
   不在本轮三项口径内，且修它要动模糊匹配阈值/提示模型识别 `confidence=="fuzzy"`，
   波及面比本轮大。**点名遗留。**
2. **`rag_search` 恒返 k 条、`found` 恒为 True。** 不相关段落也照样以「检索到依据」的
   形状交给模型（见上文实测）。这是检索质量问题而非空手路径问题，同样点名遗留。

## 改动与验证

- 代码：`agent/tools.py` 两处（`entity_resolver` 补 note；`rag_search` 失败态分流 + `error` 标志）。
  **未动 `agent/loop.py` 的 `_EMPTY_CHECKS`**——四个工具的判空双向都已正确，改它只会引入回归。
- 用例：`tests/test_agent_tools.py` 新增 7 条（`TestEntityResolverEmptyPathHonesty` 3 条、
  `TestRagSearchFailureStatesAreDistinguishable` 4 条）。
  **对旧实现真会红的证据**——把 `agent/tools.py` 恢复到 HEAD 后跑这两个类：

  ```
  FAILED TestEntityResolverEmptyPathHonesty::test_unresolved_note_gives_next_step_and_forbids_negative_assertion
  FAILED TestEntityResolverEmptyPathHonesty::test_ambiguous_note_orders_recheck_not_bounce_to_user
  FAILED TestRagSearchFailureStatesAreDistinguishable::test_zero_hit_note_forbids_negative_assertion_and_gives_next_step
  FAILED TestRagSearchFailureStatesAreDistinguishable::test_pipeline_failure_is_flagged_as_error_not_as_missing_content
  FAILED TestRagSearchFailureStatesAreDistinguishable::test_unbuilt_store_is_flagged_as_error_too
  5 failed, 2 passed, 37 deselected
  ```

  余下 2 条是**故意**两边都绿的负向守卫：`test_note_does_not_change_loop_empty_verdicts`
  （加 note 不许动判空口径）与 `test_successful_hit_carries_no_error_flag`
  （正常命中不许被打上 error）。
- 基准：`qa_gold.json` 113 → **114 题**，新增 **#118**（地狱兽 Helbrute 同名跨阵营消歧
  诚实性，gold 取库内四行 130/110/110/120 且四行 `points_json["mfm"]` 溯源块与顶层
  points 一致）。

  **一处如实披露**：`rag_search` 那条缺陷的触发条件是**检索侧环境故障**
  （知识库未构建 / 调用异常），在正常环境的问答基准里不可达——不可能用一道基准题去
  覆盖它，除非人为破坏环境。该修复由上面 3 条单元测试钉住，**没有**为它硬凑基准题。
  #118 覆盖的是 `entity_resolver` 那条缺陷所在的歧义通道。

## 验证结果

| 项 | 结果 |
|---|---|
| `pytest -q` | **2372 passed**（基线 2365 + 本轮 7 条） |
| `python -m wiki_engine lint` | **0 errors**, 1 warning, 4 info（与基线持平） |
| `cd web && npm run lint` | **本轮未跑通**——见下方「未验证项」 |
| 基准（`--path agent`，114 题） | 110 ✅ / 1 ⚠️ / 3 ❌ = **96.5**，产物 `benchmarks/v3_edition11/qa_agent_results_empty_path_audit.json` |

**既有 113 题逐题对比零退化**：3 个 ❌ 仍是且仅是 #113 / #114 / #115（库内点数过期、
等 `mfm --apply` 拍板，本轮按红线未碰）；其余 110 道既有题全部 ✅——
其中 **#41 由基线的 ⚠️ 变 ✅**，那是 CLAUDE.md 已点名的波动题（兽人小子漏项），
方向是好的，但**不算本轮的功劳**，本轮没有碰过它那条路由。
唯一的新非绿是本轮自己新增的 **#118 ⚠️**，成因见上文观察项 0，属如实披露的已知缺陷，
gold 未作任何迁就。

## 未验证项（如实披露）

`cd web && npm run lint` 在本轮**没有跑出结果**：跑它的那次调用之后，本次会话的
PowerShell 通道整体失效（此后连 `Write-Output "ok"` 都只返回 exit 66、无任何输出），
无法再取到 lint 输出，也无法重跑。本轮**没有改动 `web/` 下的任何文件**
（改动面只有 `agent/tools.py`、`tests/test_agent_tools.py`、`qa_gold.json` 和本文档），
所以前端 lint 状态**应当**与基线（0 error）一致，但这句话本轮**未经机械验证**，
下一轮请先补跑一次。
