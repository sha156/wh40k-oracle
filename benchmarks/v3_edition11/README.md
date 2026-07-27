# 11 版基线 v3（2026-07-11 起用）

- **gold**：根目录 `qa_gold.json`（meta.version=v3, edition=11）。迁移审计见
  `docs/superpowers/specs/2026-07-11-qa-gold-v3-edition11-audit.md`：规则类 7 题 +
  #41 按 11 版更新，stat/weapon 78 题零漂移。
- **现行基线 = 99.0**（95✅ / 1⚠️ / 0❌，`qa_agent_results_after_entity_fixes.json`，
  2026-07-11 run4）。唯一 ⚠️ = #42 题面歧义（"格斗武器"按字面答 Close combat weapon
  行，数值正确；gold 期望列全 4 把近战武器）——风格噪声，与十版 v1 的 2⚠️ 同类。

## 达成路径（四轮，逐轮核因）

| 轮 | 分数 | 状态 | 修了什么 |
|---|---|---|---|
| run1 | 91.7 | `..._run1_prewikifix.json` | —（暴露 wiki 术语页十版残留：#86/#88 引用已出索引的《10版速查表》） |
| run2 | 93.8 | `..._baseline.json` | wiki core-rules 11 个术语页 11 版化 → #86/#88 转绿 |
| run3 | 96.9 | `..._run3_alias_only.json` | community 别名 4 条（#23/#48/#76 转绿；撞名单位经 canonical id 直取） |
| run4 | **99.0** | `..._after_entity_fixes.json` | 修 `_TOOL_ARG_HINTS` 截短指令（#65 转绿） |

## 四个实体解析缺陷的最终定因与修法

| 题 | 根因 | 修法 |
|---|---|---|
| #23 混沌教徒 | 库内无此别名且 Cultist Mob **三行撞名**（CD/CSM/QT） | community 别名 → canonical id 直取 000000946（CSM 本尊） |
| #48 复仇者小队 | 缺别名（库内名「狂暴复仇者」），resolver 候选全错 | community 别名 → Dire Avengers |
| #65 机械教游侠 | **提示词自伤**：`_TOOL_ARG_HINTS` 教 LLM"不要带阵营前缀"，把连写限定名截成「游侠」→ 精确命中灵族 Rangers confident 错答 | 别名 → 000000848（AdM，两行撞名）+ 改提示词：连写限定名整串传、仅「XX的YY」所属格才拆 |
| #76 死亡连无畏机兵 | 「机兵」后缀无别名 → ambiguous 降级 → 经典链被 FP 磁力勾爪**变体**数据表抢答（11版仲裁偏好放大） | community 别名 → Death Company Dreadnought，走查表路径（T=10） |

防回归：`tests/test_db_compile_entity_resolver.py::TestRealDbCommunityAliasRegression`
（真库四条断言）+ `TestPopulateCommunityAliases`（canonical id 直取单测）。

## v3.2（2026-07-27）：+8 题词条/中文层/诚实性

`qa_gold.json` 从 96 题扩到 **104 题**（meta.version=v3.2）。新增 #101-#108 覆盖本轮上线的
词条解释层与中文技能对账，每题 gold 的出处写在该题的 `note` 字段里，逐条可回真源核对：

| 题 | 类型 | 考什么 | gold 出处 |
|---|------|--------|-----------|
| #101 | rule | 【致命一击】含义 + 11版自动造伤由强制改可选 | `wiki/core-rules/lethal-hits.md`（24.23） |
| #102 | rule | 【速射1】vs【速射2】差别（额外攻击骰数） | `wiki/core-rules/rapid-fire.md`（24.30） |
| #103 | rule | 【连击3】一次暴击共算几下命中（4 下） | `wiki/core-rules/sustained-hits.md`（24.36） |
| #104 | ability | 强征小队「帝国法律」内嵌的两个词条 | db `abilities`『Imperial Law』(000002685) |
| #105 | ability | 强征小队「罪魂扫描仪」加哪个词条 | db `abilities`『Soulguilt Scanner』(000002685) |
| #106 | rule | 【手枪】≡【近身/近距离】，PISTOL 非作废残留 | `wiki/core-rules/pistol.md` + `indexes/keywords.md` 过渡期节 |
| #107 | ability | **诚实性**：蝎式沙丘运输车库内无中文技能层，只有英文原文，不许编中文 | db `abilities`(000001650)；`unit_zh_detail` 无该 id |
| #108 | ability | **诚实性/版本**：「横扫敌阵」11版是 S/D 各+1，答旧版 D3 致命伤即错 | db `abilities`(000001144) + `unit_zh_detail`(000004101) 中文层 |

结果 `qa_agent_results_gnhf_kw_zh.json`：**102✅ / 1⚠️ / 1❌ = 98.1**，8 道新题全 ✅（连跑两轮一致）。

**⚠️ #41/#63 的掉分不是这批新题带来的，也不是本轮改动带来的。** 对照实验：把本轮改动
（`wiki_engine/models.py`、`lint.py`、`qa_gold.json`）全部 checkout 回 HEAD 后重跑原 96 题，
结果同样是 `{41: ⚠️, 63: ❌}`（97.9），与本轮 104 题 run 的**共有 96 题逐题 verdict 差异为 0**。
所以这两题相对 2026-07-24 的 `qa_agent_results_refine_fabfix.json`（100.0）是**本分支更早的提交**
造成的既有漂移，需单独定因：

- **#41 兽人小子**：检索源从基线的 8 个（Core Rules / 兽人10版中文 / 黑图书馆）变成 1 个
  （官方结构库 db）——是**路由变了**（agent 改走兵牌查表而非规则检索），答案因此没提
  「抢好东西去 / 保镖」两条被问要点，判 ⚠️ 漏项。
- **#63 坦克指挥官**：全 96 题里**唯一没有 gold 的题**（走 intrinsic judge），本轮 agent 反问
  「你指哪一个坦克指挥官」而不作答，按 judge 铁律「答非所问」判 ❌。检索源 0 个。

两题都指向同一个可疑变更面：黑图中文层刷新改了 `unit_zh_detail` → 兵牌工具返回内容变化 →
agent 工具路由/消歧行为变化。**本轮不修**（超出三件事的范围），点名留档。

## #63 已定因并修复（2026-07-27，`qa_agent_results_ambiguous_note_fix.json`）

上面留档的「消歧行为变化」定因到了一处**自相矛盾的接线**，不在数据层而在 `agent/tools.py`：

- `get_entity` 解析出多候选时，返回的 `note` 原文是「译名有多个候选，**需向用户反问确认**：…」——
  等于工具亲口指挥模型把问题退回用户；
- 同时 `loop._EMPTY_CHECKS` 按评审 #25 的裁决把 ambiguous 判为**非空**（候选是实质回复，
  不该降级 classic），于是经典链兜底**也不会触发**。

两条单独看都合理，凑在一起就成了「**不降级、也不作答**」的死胡同：模型照 note 反问用户，
检索源 0 个，judge 按「答非所问」判 ❌。这也解释了为什么基线时它是好的——基线上
`get_entity` 没解析出候选（走 empty → 降级 classic → rag_search 命中 8 源）；官方中文名铺开后
「坦克指挥官」开始能匹配到 3 个候选（黎曼鲁斯 / 罗格多恩 / 远见指挥官），才把这条死路走通。

修法（只改 note 措辞，不动 `_EMPTY_CHECKS`，评审 #25 通道原样保留）：让 note 指挥模型
**逐个候选重新调用 `get_entity`**，反问用户降级为查证之后的兜底。修后工具链变成
`[get_entity, get_entity, rag_search]`——第二次候选查询返回空 → 兜底正常触发 → 回到基线的
8 个检索源与带页码的正确答案。

| 指标 | 修前 `..._gnhf_kw_zh.json` | 修后 `..._ambiguous_note_fix.json` |
|---|---|---|
| 成绩 | 102✅ / 1⚠️ / 1❌ = 98.1 | **103✅ / 1⚠️ / 0❌ = 99.0** |
| 104 题逐题 verdict 差异 | — | **仅 #63（❌→✅），其余 103 题零变动** |

回归护栏：`tests/test_agent_tools.py::TestGetEntity` 两条——
`test_ambiguous_note_orders_recheck_not_bounce_to_user`（note 必须先指挥重查、且已验证
把 note 改回旧措辞它会红）与 `test_ambiguous_still_counts_as_non_empty_for_loop`
（评审 #25 通道不许被顺手改回降级）。

**仍留档未修：#41 兽人小子 ⚠️**（漏项，非硬错）。它是另一套机制——`get_entity("兽人小子")`
现在 `confidence=exact` 直接命中 `000000016`，agent 因此走兵牌查表而不再检索规则书，
漏掉「抢好东西去 / 保镖」。改它要动「查表 vs 检索」的路由偏好，波及面远大于本次 note 措辞，
不在本轮范围。

## v3.3（2026-07-27）：+9 题点数/覆盖面/诚实性

`qa_gold.json` 从 104 题扩到 **113 题**（meta.version=v3.3）。新增 #109-#117 补上前两轮暴露、
而旧 104 题**一道也覆盖不到**的那类问题——「数据没错，但校验器根本没看它」。
gold **一律取官方 MFM 实时站**（2026-07-27 15:14 快照，缓存 `db_sources/mfm/mfm_points.json`），
逐条出处写在各题 `note` 字段。完整报告 `docs/superpowers/specs/2026-07-27-qa-gold-v33-points-coverage.md`。

| 题 | 类型 | 考什么 | gold | verdict |
|---|---|---|---|---|
| #109 | points | 一次问**四个**泰坦点数（多单位覆盖面） | 1100 / 2200 / 2600 / 3500 | ❌（**不是点数问题**，见下） |
| #110 | points | 幽魂泰坦 Revenant Titan | 1100 | ✅ |
| #111 | points | 幻影泰坦 Phantom Titan | 2100 | ✅ |
| #112 | points | 蝠鲼 Manta | 2100 | ✅ |
| #113 | points | 罗伯特·基里曼（库 340 已知过期） | **355** | ❌（预期内） |
| #114 | points | 安提洛克斯战甲卡尔加（库 140 已知过期） | **155** | ❌（预期内） |
| #115 | points | 坎托战团长（库 90 已知过期，**降价**方向） | **80** | ❌（预期内） |
| #116 | rule | 覆盖面：泰坦军团恰好 4 个单位、混沌泰坦复用同一张兵牌 | — | ✅ |
| #117 | ability | **诚实性**：战将泰坦库内关键词清单里没有 `Frame`，要照实说缺口 | — | ✅ |

#110-#112 与 #109 里的四个泰坦，都是当初被 MFM 解析器千分位正则静默丢行的 7 个 ≥1000 分单位；
#113-#115 是被 `_KEEP_SECTIONS` 白名单整段切掉、点数至今过期的战团/子阵营专属角色。

结果 `qa_agent_results_points_coverage.json`：**108✅ / 1⚠️ / 4❌ = 95.6**。
与紧邻基线 `..._ambiguous_note_fix.json` 逐题对比：**共有 104 题 verdict 差异 0 条**（零回归），
分数下降 100% 来自新题。连跑两轮：113 题里只有既有波动题 #41（⚠️→❌）变化，**9 道新题两轮完全一致**。

**#113-#115 三题的红是库内点数过期的真实反映，`mfm --apply` 后会自然转绿**（副本试跑已验证
apply 后 `--check` 收敛到 1319/1319/过期 0）。gold 没有为了分数好看而改成库内值。
本轮**全程未写库**（无 `mfm --apply`/`--fetch`，`db/wh40k.sqlite` SHA-256 与上一轮报告记录的一致）。

**#109 的红是本轮新逮到的硬错，与点数无关**（那四个值库=官网）：一次问四个单位时 agent 选了
`calc_points`，它只按 `units.id` 查、对中文名返回「未找到该 unit id」，模型把这个升级成了
「Adeptus Titanicus 是独立桌游、不是 40K 阵营、四个泰坦在 11 版无官方点数」这种**否定性事实断言**。
逐个单独问（#110-#112 同型）则全对。本轮不修，留作独立课题。

## #109 已定因并修复（2026-07-27，`qa_agent_results_calc_points_honesty.json`）

上面留档的「工具查不到 → 模型编否定性断言」是**诚实性硬错**，不是点数问题
（那四个值库＝官网）。链路只有一步：`calc_points` 底层是纯 `units.id` 查表，四个中文名
全部返回「未找到该 unit id」；`calc_points` 又不在 `loop._EMPTY_CHECKS` 里，不判空、
不降级兜底；模型拿着一次全空返回，把**查询失败**升级成了**事实断言**
——「泰坦军团是独立桌游、不是 40K 阵营、四个泰坦在 11 版无官方点数」。

修法三层（详见 `docs/superpowers/specs/2026-07-27-calc-points-negative-assertion-fix.md`）：

1. **根本修法**：`agent/tools.py::calc_points` 补名字解析——底层 `db_compile/calc_points.py`
   一行没动（仍是纯 id 查表，军表/web 侧按 canonical id 直调的约定保持），只在 agent 包装层
   对返回「未找到该 unit id」的那几个走 `entity_resolver` 重查。纯 id 入参的行为逐字节不变。
   四个泰坦中文名实测全部 `confidence=exact`，一次调用返回四条——**漏项那一半也一并解决**。
2. **措辞修法**（同 #63 的 `1efb6e5c` 做法，因果写进注释防被改回）：仍解析不到时的 note 直说
   「查不到 ≠ 该单位或该阵营不存在，也 ≠ 它没有官方点数」，指路 `get_datasheet`/`entity_resolver`
   重查，并明令禁止输出「不存在 / 不属于 40K / 无官方点数」这类否定性断言。
3. **通道修法**：`_EMPTY_CHECKS` 加 `calc_points`——**全部**名字都没解析到才判空降级兜底；
   「查到了但库里没点数」是诚实答案，不许被 `rag_search` 吞掉。
   另在 `_NEXT_STEP_CONTRACT` 铁律段加了通用形式，覆盖其他工具的同型复发。

| 指标 | 修前 `..._points_coverage.json` | 修后 `..._calc_points_honesty.json` |
|---|---|---|
| 成绩 | 108✅ / 1⚠️ / 4❌ = 95.6 | **109✅ / 1⚠️ / 3❌ = 96.5** |
| 113 题逐题 verdict 差异 | — | **仅 #109（❌→✅），其余 112 题零变动** |
| #109 回答 | 「泰坦军团…并非战锤40K的阵营…均无官方点数」 | 四个点数逐条列出，1100/2200/2600/3500 全对 |

连跑两轮：#109 两轮均 ✅（不是波动侥幸），两轮唯二差异是 #41/#42 这两道早已点名的固定波动题。
**#113/#114/#115 仍红**——库内点数过期的真实反映，`mfm --apply` 后自然转绿，本轮按红线未碰。

回归护栏：`tests/test_agent_tools.py::TestCalcPoints` 四条 +
`TestCalcPointsRealDbTitanRegression`（真库四泰坦点数钉子）+
`tests/test_llm_client.py::test_next_step_system_prompt_bans_negative_assertions_on_lookup_miss`。
`git stash` 掉实现后跑新用例 **5 failed**，逐条验证过对旧实现真会红。

## v3.4（2026-07-27）：4 个查询类工具「查不到/空结果」路径排查（`qa_agent_results_empty_path_audit.json`）

排查 `get_datasheet` / `rag_search` / `entity_resolver` / `get_keyword_definition` 四个
「按名字取数据」工具的空手路径（措辞 / `_EMPTY_CHECKS` 双向 / 下一步指引），
排查表与逐条证据见 `docs/superpowers/specs/2026-07-27-query-tools-empty-path-audit.md`。
两处确认缺陷已修（`entity_resolver` 空手补 note；`rag_search` 把「环境故障」与「零命中」
分流并加 `error` 标志），判空口径一行未动。

新增 **#118**（地狱兽 Helbrute 同名跨阵营，gold 取库内四行 CSM 130 / DG 110 / TS 110 /
WE 120，四行 `points_json["mfm"]` 溯源块与顶层 points 一致）。qa_gold 113 → **114 题**。

成绩 114 题 **110 ✅ / 1 ⚠️ / 3 ❌ = 96.5**。**既有 113 题逐题零退化**：❌ 仍是且仅是
#113/#114/#115（库内点数过期，等 `mfm --apply`）；#41 由 ⚠️ 变 ✅（已点名的固定波动题，
本轮没碰它那条路由，不算本轮功劳）。

**#118 当前 ⚠️，是如实披露的新缺陷而非 gold 问题**：`get_datasheet` 的歧义守卫只长在
`name_en` 精确匹配上（`db_compile/datasheet.py:205-216`），**中文名**走
`entity_resolver.resolve()` → `_zh_to_id`（`setdefault` 先入者胜）→ `exact` → 静默返回
其中一张兵牌，`reason`/`candidates` 全无；而提示词恰恰要求模型直接传中文名
（`agent/llm_client.py:98-100`）——评审 #25 要防的「静默取一」在主路径上没有生效。
#118 记录里 `tool_calls: ["get_datasheet"]`、`degraded: false`、只答 120（吞世者那张），
英文名 `get_datasheet("Helbrute")` 则正常抛 ambiguous + 4 候选预览。修它要动
`find_datasheet` 中文分支并整轮重跑基准，留给独立一轮。

回归护栏：`tests/test_agent_tools.py::TestEntityResolverEmptyPathHonesty` 3 条 +
`TestRagSearchFailureStatesAreDistinguishable` 4 条；把 `agent/tools.py` 恢复到 HEAD 后
跑这两个类 **5 failed / 2 passed**（那 2 条是故意两边都绿的负向守卫：加 note 不许动判空口径、
正常命中不许被打上 error），逐条验证过对旧实现真会红。

## v3.5（2026-07-27）：#118 同名跨阵营不消歧已修（`qa_agent_results_same_name_disambig[_run2].json`）

上一节点名的缺陷已修，且**根因与上一节的诊断一致**：歧义守卫只长在 `name_en` 精确匹配上，
中文名走 `entity_resolver.resolve()` → 扁平的 `_zh_to_id` → `exact` → 静默四选一。

修法**不动 resolver 的返回语义**（实测会让 **212 个**跨阵营同名中文名从 exact 翻成
ambiguous，而 `find_datasheet` 只信 exact → 那 212 个名字全部返回 None，直接把一片题
推向「因歧义拒答」），改为在工具边界**严格追加式**补报：新增只读
`db_compile/datasheet.py::same_name_factions()` 按 unit_id 反查同名兄弟行（仅阵营数 > 1
才算歧义，同阵营重印行不误报），`get_datasheet` / `calc_points` 拿到结果后追加
`same_name_other_factions`（各候选的阵营 + 点数，全部取自结构库）与一条同时防住
gold 三种判错情形的 note。`found` 仍为 True、已查到的数值照常返回，**纯 canonical id
入参行为逐字节不变**（军表/web 的既有约定，有专门用例钉死）。

连跑两轮均 **96.5**，对照 `qa_agent_results_r9_salvage.json` **共有题 verdict 差异 = 1**，
即 **#118 ❌ → ✅**；两轮之间差异 0（连已知波动的 #41/#42 都没互换）。
三题互斥锚点全部站住：#118 ①（不说阵营）❌→✅、#63 ②（因歧义拒答）✅→✅、
#109 ③（凭记忆编否定断言）✅→✅。仍红的 #113/#114/#115 是库内点数过期，本轮按红线未碰。
全程未改 gold、未写库。报告
`docs/superpowers/specs/2026-07-27-same-name-cross-faction-disambiguation.md`。

回归护栏：`tests/test_agent_tools.py::TestSameNameCrossFactionDisambiguation` 5 条 +
`TestSameNameCrossFactionRealDb`（真库四张 Helbrute 点数钉子）。`git stash` 掉
`agent/tools.py` + `db_compile/datasheet.py` 后跑这两个类 **4 failed / 2 passed**
（那 2 条是故意两边都绿的负向守卫：同阵营重印不算歧义、纯 id 入参行为不变），
逐条验证过对旧实现真会红。逐题对比脚本 `scripts/compare_bench_runs.py`。

## 与 v1（97.9，benchmarks/v1_10th/）的关系

v1 与 v3 成绩不可直接比较（7 题 gold 语义变了 + 语料从 37 本十版换成 61 本分层）。
v3 修复后 99.0 且零硬错，11 版口径下已超过十版基线水平。
