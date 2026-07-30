# 全库三轮代码审查 · 第 1 轮：核心问答链路

分支 `review/full-audit-2026-07-30`（从 `origin/main` d4fce5d5 开出，逐字节一致）
日期 2026-07-30 ｜ 本文档为**第 1 次迭代产出：只审不改**（无任何实现代码改动）

产出形式（用户已拍板）：**分级清单 + 只修 CRITICAL/HIGH**；MEDIUM/LOW 只记录不动手。

---

## 0. 本轮结论速览

| 分级 | 条数 | 状态 |
|---|---|---|
| CRITICAL | **0** | 本轮未发现（不硬凑） |
| HIGH | **3** | H1/H2/H3 全部**已实测复现**，待后续迭代逐条修复 |
| MEDIUM | 6 | 只记录，不改（M6 为潜在项，库内 0 行触发） |
| LOW | 4 | 只记录，不改 |
| 判为不成立 | 6 | 附反证，见 §4，防下轮重复排查 |

⚠️ **本次迭代未修任何一条**（迭代节奏由 objective 规定：第 1 次只审查）。
因此 §3「改前会红 / 改后转绿」一节目前为空，将在后续迭代逐条补齐；
本文件的 stop-condition 第 (2)(3) 条**尚未满足**。

复现脚本写在系统临时目录（`%TEMP%\audit_r1_repro.py` / `audit_r1_repro2.py`），
未落仓库；下文所有「实际输出」均为这两个脚本的真实运行结果，无一条是杜撰。

---

## 1. 逐文件审查覆盖表

「已审（全文）」= 逐行读完；「已审（定向）」= 按本轮四类风险模式（静默降级 / except 吞异常 /
模糊匹配放行 / 正则白名单边界零容忍）grep 定位后抽读关键函数，未逐行通读。

### 1.1 `agent/`

| 文件 | 行数 | 结论 | 备注 |
|---|---|---|---|
| `agent/tools.py` | 789 | **已审（全文）** | 产出 H3(共因)、M4；`_EMPTY_CHECKS` 相关注释交叉核对 |
| `agent/loop.py` | 194 | **已审（全文）** | 产出 M1；`get_datasheet` 不判空的防线核对为**合理**（§4-A） |
| `agent/llm_client.py` | 249 | **已审（全文）** | 产出 L1；JSON 花括号扫描疑点核对为**不成立**（§4-B） |
| `agent/context.py` | 20 | **已审（全文）** | 纯内存 dataclass，无 IO、无解析，未发现问题 |

### 1.2 `engines/simulator/`

| 文件 | 行数 | 结论 | 备注 |
|---|---|---|---|
| `engine.py` | 132 | **已审（全文）** | 先攻方向用 `first_is_a` 不比名字，正确 |
| `assembly.py` | 145 | **已审（全文）** | 产出 **H3** |
| `sequence.py` | 316 | **已审（全文）** | 未发现缺陷；`count<=0` 在此层处理正确（反证 H3 的责任归属） |
| `effect_params.py` | 348 | **已审（全文）** | 产出 **M5** |
| `parse.py` | 161 | **已审（全文）** | 产出 M6（潜在） |
| `fight_order.py` | 141 | **已审（全文）** | 产出 **M2** |
| `contracts.py` | 152 | **已审（定向）** | 纯 frozen dataclass 契约；随 sequence/effect_params 交叉核对字段语义 |
| `profile.py` | 180 | **已审（定向）** | 只审 `load_*` 的查空/JSON 解析路径（39/169/190 行三处 return None） |
| `keywords.py` | 156 | **已审（定向）** | 只审「未识别词条」出口：确认走 `_ANNOTATE`/`已识别未建模` 披露，非静默丢 |
| `abilities.py` | 205 | **已审（定向）** | 只审 `_FNP_RE` / HTML 剥离两处正则；T1「FNP 99/105 条件式」既有裁决未推翻 |
| `context.py` | 92 | **已审（定向）** | 只审 `build_not_modeled` / `build_toggles_available` 的披露完备性 |
| `report.py` | 65 | **已审（定向）** | 纯聚合，无解析分支 |
| `cli.py` | 297 | **未审** | 原因：命令行外壳，不在「核心问答链路」的用户可达路径上（web/agent 均不经它）；范围控制优先 |
| `_spike_allocation.py` | 337 | **未审** | 原因：分配核已由 P4 spike **双实现对拍 0 误差**验收（见 memory `p4-simulator-spec-and-review`），重审性价比低；本轮改为核对其调用方 `run_sequence` 的入参夹取（已审，正确） |
| `dsl.py` | 525 | **未审** | 原因：P7 已逐条编码 + 28 轮 PR 审查覆盖，且其白名单唯一真源 `ATTACKER_CONSUMED/TARGET_CONSUMED` 在 `effect_params.py`（本轮已审，见 M5）；单轮范围控制 |

### 1.3 `engines/roster/`

| 文件 | 行数 | 结论 | 备注 |
|---|---|---|---|
| `validate.py` | 163 | **已审（全文）** | 诚实降级红线（unknown_ids 跳过断言）实现正确，未发现缺陷 |
| `points.py` | 73 | **已审（全文）** | 严格档位正则 + 纯档优先，正确 |
| `critique.py` | 125 | **已审（全文）** | 产出 **M3**；并确认 H3 的影响面覆盖到点评侧 |
| `compose_rules.py` | 72 | **已审（全文）** | `datasheet_copy_limit` 判定顺序疑点核对为**不成立**（§4-C） |
| `contracts.py` | 47 | **已审（全文）** | 纯契约，未发现问题 |

### 1.4 检索链

| 文件 | 范围 | 结论 | 备注 |
|---|---|---|---|
| `app.py` | 检索/融合/保底部分（L222-459 + `load_resources`/`build_bm25`） | **已审（全文）** | 产出 **H1**、M7(疑似) |
| `app.py` | 其余（UI 渲染 L465-868） | **未审** | 原因：objective 明确只圈「检索/融合/保底部分」，UI 不在本轮范围 |
| `ingest.py` | 386 | **已审（全文）** | 产出 L3、L4 |
| `llm_refine.py` | 273 | **已审（全文）** | 产出 **H2**、L2 |
| `hf_embeddings_compat.py` | 43 | **已审（全文）** | 两层 import 兜底均**抛出**并带指路信息，无静默降级，未发现问题 |

---

## 2. 分级 finding 清单

### 🔴 HIGH

---

#### H1 · 检索管线故障被报成「语料里没有」——`error` 分类形同虚设

**位置**：`app.py:361-362`、`app.py:375-376`、`app.py:390-391`（三处 `except → st.warning`）
配合 `agent/tools.py:529-559`（`rag_search` 的 `error=True` / 零命中二分）

**病灶**：`agent/tools.py` 特意把 rag 的失败态分成两类，并写明动机——

> 三种失败态此前共用同一个形状 `{found: False, passages: []}`，模型无从区分「语料里没有」和
> 「检索管线自己坏了」，很容易把工具故障写成「档案里没有这条规则」的否定性断言（#109 同型）。

但 `hybrid_retrieve` 在**下一层**就把 FAISS / BM25 / 规则层保底的异常**全部内部吞掉**，
只调 `st.warning`。`rag_search` 的 try 块因此永远收不到异常，只能看到一个空列表，
于是走「跑通了但零命中」那条分支。**分类器与被分类对象之间的信号在中间层被截断了**
——这正是本轮要重点扫的「校验器与被校验对象共享前提/信号不正交」形态。

额外放大因素：agent / qa_bench / web_api 都在**非 Streamlit 上下文**里调用它，
`st.warning` 既不抛异常也无处可见（实测确认不抛，见下方输出），运维侧同样零感知。

**复现输入**（`%TEMP%\audit_r1_repro.py` [R1]）：注入一个 `as_retriever().invoke()` 与
`similarity_search()` 均抛 `RuntimeError("FAISS index corrupted")` 的 vectorstore，`bm25=None`。

**实际输出**：
```
  found      = False
  error flag = <缺省 -> 表示「检索跑通了但零命中」>
  note       = 本次混合检索没有命中任何段落（提问措辞/译名与语料用词不一致时最常见）。⚠️ 没检索到 ≠ 该规则或该单位不存在。请换更 ...
  >>> 期望: error=True（管线故障）。实际: !! error 缺省 -> 被当成语料零命中 !!
```

**影响**：索引损坏 / 未构建 / 嵌入模型挂掉等**环境故障**期间，整条链会对每一个问题
稳定给出「本次混合检索没有命中任何段落」+「换个措辞再检」的**内容性结论**，
而 `_RAG_UNAVAILABLE_HINT`（「这是检索侧环境故障，不可据此判断该规则是否存在」）
一次都不会出现。降级答案是「⚠️ 已降级到兜底检索，但仍未找到相关内容」——
用户与模型都被引向「语料里没有」。**分级 HIGH**（诚实性防线整条失效，非单题错答）。

**建议最小修法**：`hybrid_retrieve` 不改对外契约，另回传/抛出检索侧故障信号
（如收集 `errors: list[str]` 或让 `rag_search` 侧探测），由 `rag_search` 据此置 `error=True`。
注意**不要**把 `st.warning` 直接换成 raise——那会让 Streamlit 侧「FAISS 挂了但 BM25 还能用」
的部分可用路径变成整体不可用，属超出修复范围的行为改变。

---

#### H2 · `llm_refine` 对 `finish_reason=length` 零检测——截断页以「完整+校验通过」永久落盘

**位置**：`llm_refine.py:104-126`（`refine_page`）、`llm_refine.py:220-229`（`_work` 落盘）、
`llm_refine.py:62-72`（`is_cached`）

**病灶**：`MAX_TOKENS` 上方的注释亲口承认这个失败模式发生过——

> 4096 对推理开销大的长规则页会把正文截断（finish_reason=length，如 Core Rules p19
> **2655 字源→59 字缓存**）。提到 8192 给正文留足预算，显著降低截断复发。

但修法只是**把阈值调大**，`resp.choices[0].finish_reason` **至今没有任何一处被读取**。
截断产物满足 `content` 非空 ⇒ 直接 return ⇒ 以 `fallback: False` / `verify_ok: <verify_numbers 结果>`
落盘 ⇒ 之后 `is_cached` 永远判命中、永不重跑。

而 `verify_numbers` 是**只查「多出来的数字」的单向校验器**（源里没有的 token 才报），
对「少了一整页内容」在数学上不可能有反应——校验器与被校验对象的信号不正交，
与「切章漏 19 节而探测器全无感知」同型。

**复现输入**（`%TEMP%\audit_r1_repro.py` [R2]）：fake client 返回
`finish_reason="length"` + 内容 `"# ROBOUTE GUILLIMAN\n\n**M** 6"`，源文本 2320 字。

**实际输出**：
```
  源文本长度   = 2320
  返回内容     = '# ROBOUTE GUILLIMAN\n\n**M** 6'
  抛异常了吗   = 否（正常返回）
  verify_numbers -> [] (空表 = verify_ok=True)
  >>> 截断内容会以 fallback=False / verify_ok=True 落盘，is_cached 后续永远跳过重跑
```

**影响**：`data_refined/` 是 `ingest.py` 的**优先语料源**（`load_refined_book` 命中就不走原 PDF）。
一页被截断 ⇒ 该页规则/兵牌内容从向量库里整体消失 ⇒ 表现为「问什么都检索不到」，
而不是任何报错。历史上的 Astra 51-156 页缺口是靠**事后另做一次缓存对账**才发现的，
不是这条管线自己报出来的。**分级 HIGH**（语料完整性 + 静默 + 缓存永久化）。

**建议最小修法**：`refine_page` 读 `finish_reason`，为 `"length"` 时按失败处理（走既有重试，
重试仍截断则抛 `RuntimeError` → 由 `_work` 走 `fallback=True` 兜底路径，从而下次会重跑）。
`finish_reason` 缺失（老 SDK / fake client）时按现状放行，避免误伤。

---

#### H3 · loadout 件数 ≤ 0 → 装配「成功」，端出全 0 的期望伤害报告

**位置**：`engines/simulator/assembly.py:164-184`（`assemble_attacker` 显式 loadout 分支，
`replace(w, count=int(count))` 对 count 不做任何校验）
配合 `agent/tools.py:756`（`usable_in_phase` 只校验阶段，不校验件数）

**病灶**：同一个文件与调用点为「假成功」立了三道防线并写明纪律——

> 与其发一份"成功的"全 0 报告（假成功），不如显式失败并指路（诚实降级纪律）

`no_phase_weapon`（该阶段无武器）、`loadout_required`（多武器未装配）、
`usable_in_phase`（手填纯近战武器打射击）三种都会显式失败。
唯独**件数 ≤ 0 没人管**：`engines/simulator/sequence.py:225` 的引擎层其实处理得完全正确
（`if count <= 0: 不开火`，注释还特意写「非 max(...,1) 幽灵开火」），
于是错误以**最危险的形态**冒出来——引擎诚实地算出 0，工具边界把这个 0 包装成 `ok=True` 的成功报告。

**复现输入**（`%TEMP%\audit_r1_repro.py` [R3]，真库真单位）：
Intercessor Squad → Termagants，射击阶段，`loadout=[["Astartes grenade launcher – frag", 0]]`。

**实际输出**：
```
  探测(无 loadout): loadout_required | pool = ['Astartes grenade launcher – frag', ...]
  loadout=[('Astartes grenade launcher – frag', 0)] -> ok=True
     expected_damage = 0.0 | expected_kills = 0.0
     warning = None
     >>> 「成功的」全 0 报告——正是代码里明令禁止的假成功路径
  loadout 件数 = -5 -> ok=True, dmg=0.0
```
注意 `warning = None`——连一句提示都没有。负数件数（-5）同样一路放行。

**影响**：`simulate_combat` 的 loadout 由 **LLM 从用户自然语言里现编**
（`_TOOL_ARG_HINTS` 里就是 `"loadout": [["武器名", 数量], ...]`），
用户一句「不带爆弹枪」完全可能被写成 `0`。模型拿到 `ok=True` + `expected_damage 0.0`
会照实答「该单位对目标的期望伤害为 0」——**一个自信的错误数字**，
且每一层都是成功路径（数据真实、报告结构完整、渲染正常），正是本轮要重点扫的
「查得到但查错了」形态。影响面同时覆盖 `engines/roster/critique.py:80`
（`_assemble_phases` 同样 `int(c)` 不校验，0 件会被评估成 assessed=True 的 0 伤单位）。
**分级 HIGH**。

**建议最小修法**：在 `assemble_attacker` 的显式 loadout 分支把 `count <= 0` 计入既有
`base.errors`（复用现成的 `errors → ambiguous → 显式失败` 通道，不新增返回形态、
不动引擎、不动 `usable_in_phase`）。

---

### 🟡 MEDIUM（本轮只记录，不修）

#### M1 · `calc_points` 的参数类型错误被判成「空结果」，模型失去改参重试的机会
`agent/loop.py:78-80`。`_EMPTY_CHECKS["calc_points"]` 的第一个分支是 `not r.get("found")`，
而 `calc_points` 的**参数校验失败**分支（`agent/tools.py:322-323`）返回的正是 `found: False`。
实测（[R4]）：`calc_points(unit_list={"name":"基里曼"})` → `_is_empty_result` 返回 **True**
→ 当场降级 classic。模型看不到「参数错误：unit_list 应为单位名列表，收到 dict」这句指路，
而它本来是**完全可以自行改参重试**的。与「未知工具/工具异常写回 messages 让模型改正」
的既有恢复策略不一致。答案本身仍是诚实的降级答案，故不升 HIGH。

#### M2 · 镜像对局下 COUNTEROFFENSIVE 归属用名字判定，答反
`engines/simulator/fight_order.py:142-151`、`agent/tools.py:590-595`。
`FightVerdict` 的字段注释已明令「名字可能相同（镜像对局），调用方必须用本布尔判定方向，
**绝不可比对 first_striker 名字字符串**」——但 `judge` 自己的 counter_offensive 分支
就在比对名字字符串。实测（[R5]）攻守同名 + 守方用 CO：
```
  first_side = attacker
  counter_offensive_note = 地狱兽 本就先打，无需 COUNTEROFFENSIVE。
  对照（名字不同，同样场景）：
  counter_offensive_note = COUNTEROFFENSIVE 需在对手近战阶段、敌方单位刚结算后使用；本 1v1 对 地狱兽B 改变有限 ...
```
用户问的是守方能否插队，系统答的是「你本就先打，不需要」。
只影响建议文案，不影响 `order` / `first_side` 判定，故 MEDIUM。
（这是既往那条 CRITICAL「用名字判方向」**只修了一半**的残留——修在了 `first_is_a`，
没修 CO 分支。与 memory `half-fixed-guard-en-vs-zh` 同型。）

#### M3 · `critique.total_points` 漏计强化点数，与 `validate.total_points` 对同一张军表给出两个总分
`engines/roster/critique.py:160` 用 `sum(u.points or 0)`，而 `validate.py:38-39` 明确
`总分 = 单位点数 + 强化点数`，并写明「漏计会把压线超分表判合法（gnhf 审查模块 3 F1 HIGH）」。
实测（[R7]，真库真强化 Aegis Projector 20 分）：
```
   validate.total_points  = 190  (含强化 20 分)
   critique.total_points  = 170  (漏计强化)
   差额 = 20 == 强化点数 20
```
判死刑的权威在 `validate`（数字正确、会正常报 `points_over`），点评页只是展示，
故不构成「非法表被判合法」，MEDIUM 而非 HIGH。

#### M4 · `get_datasheet` 的裸 `except Exception: pass` 会连 `stat_conflicts` 披露一起吞掉
`agent/tools.py:489-504`。该 try 块同时包住黑图书馆中文层加载**和** `diff_core_stats`
两源数值冲突检测。任一环节异常 ⇒ 静默 pass ⇒ 不仅中文层没了，
「黑图书馆中文层与官方源在部分属性上不一致，数值以官方英文为准」这句**诚实性披露也一并消失**，
且无任何日志。属 CLAUDE.md 明令的「except 分支必须打显眼日志」违例。
**未构造出当前会触发的输入**，按代码形状定级 MEDIUM。

#### M5 · 守方消费点白名单被手抄了第二份，且披露文案已过时
`engines/simulator/effect_params.py:408-419`（`TARGET_CONSUMED`，自称
「白名单唯一真源在此，**不许在别处手抄第二份**」）vs `:450-458`（`_target_effect_consumed`，
就是手抄的第二份）。攻方侧对照组做对了——`unconsumed_attacker_effect_notes:431`
直接引用 `ATTACKER_CONSUMED` 集合。
当前两份内容基本等价（未发现现实分歧），但 `:466-471` 的披露文案**已经落后**：
只列了 fnp/damage_reduction/hit+modify/save+cover/save+invuln/save+sv_improve，
漏掉了 `wound+modify`、`hit+bs_improve`、`wound+t_improve`、`save+ap_improve` 四个已接通的消费点。
危险方向是：将来只往手抄版加分支而漏了真源，会让真正被丢弃的效果**不再被披露**。
MEDIUM（当前无错误输出，属维护性断裂风险 + 文案失真）。

#### M6 · `parse_ap` 无法解析一律归 0，且与 `norm_stat_int` 不对称 —— **潜在，库内 0 行触发**
`engines/simulator/parse.py:93-103`。`parse_ap` 的 `except ValueError: return 0`
把任何无法解析的 AP 当作「无穿甲」，不抛错、不记账、不进 unparsed。
而同文件的 `norm_stat_int` **认得** `*` 脚注（文档里明写 `4*`→4、`5*`→5）。两者不对称：
```
   parse_ap('-1*' ) = 0     norm_stat_int('-1*' ) = -1
   parse_ap('‑1'  ) = 0     norm_stat_int('‑1'  ) = None     # U+2011
   parse_ap('−1'  ) = 0     norm_stat_int('−1'  ) = None     # U+2212
```
这是 `(\d+) pts` 对千分位零容忍那类失效模式的同款形状（静默、方向偏保守、无告警）。

**但必须诚实标注：对真库实测，当前 0 行受影响。** `weapons.ap` 全部取值仅 9 种
（`0/-1/-2/-3/-4/-5/-6/-/-0`），全部解析正确，静默归零行数合计 **0**。
故定级 MEDIUM（潜在），**不升 HIGH**——上游一旦引入 `-1*` 或 unicode 减号才会咬人。

#### M7 · `merged` 为空时直接 return，规则层保底结果被丢弃（**疑似**）
`app.py:396-397`。`rules_docs`（11 版规则层保底，项目里的最高真源）在 FAISS+BM25 融合结果
为空时**根本没机会注入**就 `return []`。构造不出「主检索空而 layer=rules 过滤检索非空」的
现实输入（两者共用同一个 vectorstore），故按 objective 纪律**单列为疑似**，不混进 HIGH。

### 🟢 LOW（只记录）

- **L1** `agent/llm_client.py:180-182`：工具返回超 4000 字被截断（带「…（已截断）」标记）。
  `get_datasheet` 叠加中文层后整包可能超限，数值可能落在被截掉的尾部。有标记、非静默，故 LOW。
- **L2** `llm_refine.py:245-248`：LLM 失败后写入原始文本的兜底页，meta 里写的是 `verify_ok: True`
  ——一个**没被校验过**的页自称校验通过。`is_cached` 靠 `fallback` 字段排除它，功能上不出错，
  但 `_verify_warn_pages` 的口径因此失真。
- **L3** `llm_refine.py:142-163`：`_refine_coverage` 的分母是 PDF 总页数，
  而 `< MIN_TEXT_CHARS` 的空白页永远不产出 `.md`，故覆盖率**在数学上到不了 1.0**；
  空白页超 10% 的 PDF 会被 `--chinese-only`（默认阈值 0.9）反复重扫。
- **L4** `ingest.py:320/378/429-431`：增量去重按 `str(pdf_path)` **原样字符串**匹配
  `metadata["source"]`。默认 `--data-dir data`（相对路径）建的索引，改用绝对路径重跑时
  匹配不上 ⇒ `delete_stale_chunks` 删 0 条 ⇒ 新旧 chunk 并存（正是 H3 修复当初要防的场景）。

---

## 3. 已修项的「改前会红 / 改后转绿」验证输出

**本轮（第 1 次迭代）无任何已修项** —— objective 规定第 1 次迭代只审查不改代码。
H1 / H2 / H3 的修复与配套测试将在后续迭代逐条进行，届时把两次实际输出补进本节。

---

## 4. 判为**不成立**的条目（附反证，防下轮重复排查）

**A. `get_datasheet` 故意不进 `_EMPTY_CHECKS` —— 是防线，不是缺陷。**
`agent/loop.py:65-74` 的注释点名：让近似名抑制降级，会当场把 #4（XV107 燃雨战斗服）与
#62（重武器小队）从 ✅ 打成 ❌，因为两者是**真实存在**的单位、只是名字不在结构库索引里。
判据「结构库 ≠ 全部语料」成立。本轮不动，也不建议动。

**B. `_extract_json_object` 的花括号平衡扫描不认字符串字面量 —— 不产生半成品。**
`agent/llm_client.py:206-218` 逐字符数 `{}`，字符串里出现落单花括号确实会切错位置；
但切出的片段随后交给 `json.loads`，失败抛 `json.JSONDecodeError`，
而它是 **`ValueError` 的子类**，与函数其余出口同型 ⇒ 照常被 `next_step` 捕获并重试一次，
再失败则抛给 `loop.run` 降级。**不存在「返回半成品 dict」的路径**，与 docstring 承诺一致。

**C. `datasheet_copy_limit` 先判豁免后判 EPIC HERO —— 库内无重叠单位。**
`engines/roster/compose_rules.py:93-99` 里 `is_rot_exempt` 排在 `is_epic_hero` 之前，
理论上「既是 EPIC HERO 又是 BATTLELINE」会被判成无上限而非 ≤1。实测全库：
```
EPIC HERO 同时带 BATTLELINE/DEDICATED TRANSPORT 的单位数: 0 []
```
0 个单位触发，不成立。

**D. `_cond_true` 未知 tag 会静默失效 —— 已经修过了。**
`engines/simulator/effect_params.py:153-155` 明确 `raise ValueError`，注释写明
「未知 tag 静默返回 False = 效果静默失效……改为 raise」。不是缺陷。

**E. `simulate` 的 `n<=0` 会裸崩 —— 已有入口校验。**
`engines/simulator/engine.py:36-37` 与 `:104-105` 两处 `raise ValueError`（评审 H9）。

**F. `sequence.py` 对 `count<=0` 幽灵开火 —— 引擎层是对的。**
`engines/simulator/sequence.py:225` 正确返回 0 攻击且注释写明「非 max(...,1) 幽灵开火」。
H3 的责任在**工具边界把 0 包装成成功**，不在引擎；修复不要动这里。

---

## 5. 移交下轮的线索（本轮只记，未动手）

### 移交第 2 轮（数据管线 `db_compile/` `wiki_engine/` `scripts/`）
1. `corpus_manifest.py:59-70` `classify_book`：书名未命中 books/prefixes 时**静默**回退
   `defaults`（`load_manifest` 只在**文件级**缺失时告警，**单本**未登记时一声不吭）。
   新 PDF 入库会拿到默认 edition/layer，而 `layer` 直接决定 app.py 的规则层保底是否选中它。
   建议第 2 轮做一次「manifest 未覆盖书目」的对账并让 ingest 汇总告警。
2. `db_compile/enhancements --apply` 的 `INSERT OR REPLACE` 会清空 `name_zh`/DSL 投影列
   （CLAUDE.md 已记录已改成报数提示，第 2 轮宜确认提示不会被忽略）。
3. `engines/roster/points.py` 与 `engines/simulator/assembly.py` 各有一份 `_MODELS_RE`
   档位解析（前者严格 + 纯档优先，后者宽松 search）。两者服务不同语义所以现状可能是对的，
   但**两份解析规则**这一形状值得第 2 轮连同 `db_compile` 侧的 points_json 写入方一起核。

### 移交第 3 轮（`web_api/` `web/`）
4. `/simulate` 路由把用户 loadout 直传 `simulate_combat_resolved`：H3 修好后需确认
   web 侧对件数 ≤0 的错误形态有渲染（不要出现「后端返回 errors 而前端只认 ok」）。
5. 军表实验室两个页签会同时展示 `validate.total_points` 与 `critique.total_points`
   （M3：同一张表两个数）。修 M3 时需连前端展示一起核对。

---

## 6. 本轮实际数字

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `.venv\Scripts\python.exe -m pytest -q` | **2398 passed, 0 failed** |
| wiki lint | `.venv\Scripts\python.exe -m wiki_engine lint` | **0 error** |
| 工作区 | `git status --porcelain` | 仅本报告一个新文件 |
| 基准 | 未跑 | 本轮**零实现代码改动**（`agent/` 与检索链均未触碰），按 objective 免跑 |

复现脚本：`%TEMP%\audit_r1_repro.py`、`%TEMP%\audit_r1_repro2.py`（系统临时目录，未入仓库）。

---

## 7. 下一次迭代的建议顺序

1. **H3**（改动面最小、边界最清晰：`assemble_attacker` 里把 `count<=0` 并进既有 errors 通道）
2. **H2**（`refine_page` 读 `finish_reason`；注意 fake client 无该字段时要放行）
3. **H1**（改动面最大，涉及 `hybrid_retrieve` 的返回契约，需最后做并单独验证
   Streamlit 侧「部分可用」行为不变）

每条修完立即：配测试 → 实测 stash 掉实现该测试真会红 → 恢复转绿 → 两次输出贴进 §3 →
跑 `pytest -q` + `wiki_engine lint`；H1/H2/H3 只要动了 `agent/` 或检索链就必须跑基准
`qa_bench --path agent` 并与 `qa_agent_results_source_routing_r2.json` 逐题对比，
四题锚点 #63/#109/#118/#119 全 ✅ 且零退化。
