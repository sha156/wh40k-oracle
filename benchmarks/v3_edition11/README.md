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

## 与 v1（97.9，benchmarks/v1_10th/）的关系

v1 与 v3 成绩不可直接比较（7 题 gold 语义变了 + 语料从 37 本十版换成 61 本分层）。
v3 修复后 99.0 且零硬错，11 版口径下已超过十版基线水平。
