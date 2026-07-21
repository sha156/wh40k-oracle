# P7-PR29 星界军（Astra Militarum）11 版对齐 + DSL 全量编码工作单

- 日期：2026-07-21
- 分支：`feat/p7-pr29-astramilitarum`
- 阵营代码：`faction='AM'`（`detachments` / `stratagems` / `enhancements.faction_id`）
- FP 真源：`data/Faction Pack Astra Militarum.pdf`（VERSION 1.0，2026-06-20 生效，共 156 页）
  · refine 缓存 `data_refined/Faction Pack Astra Militarum/`
- 产物：`dsl_payloads/astramilitarum.json`（122 条）、`db_compile/fp_rules_patches.json`（+29 条）、
  `tests/test_simulator_dsl_pr29_payload.py`（68 测试）
- 零新引擎通道、零新态势开关（纯编码 PR），零 `fp_errata`

---

## 一 · FP 内容面

156 页里**规则层只在 p1-p10 与 p27-p28**，其余 p11-p26 / p29-p156 全是 datasheet
（Imperial Armour 与 Legends 占大头），沿死亡守望 / 圣血修女 / 帝国代理先例不落本 PR。

| FP 页 | 分队 | 库内状态 | 判定 |
|---|---|---|---|
| p2 | **Abhuman Auxiliaries** | 库无 | `fp_new` 整分队补录（1 规则 + 2 增强 + 3 战略） |
| p3 | **Bridgehead Strike** | 库有（十版 4 增强 + 6 战略） | **11 版整页重印**：5 条 `text_patch` + 5 条 `removed_11e` |
| p4 | **Designation Force** | 库无 | `fp_new` 整分队补录（1 规则 + 2 增强 + 3 战略） |
| p5-p6 | Steel Hammer | 库有 | 逐字一致 → **免补** |
| p7-p8 | Armoured Infantry | 库有 | 逐字一致 → **免补** |
| p9-p10 | Grizzled Company | 库有 | 仅 ADDITIONAL ARMOUR 持续期漂移 → 1 条 `text_patch`，其余免补 |
| p27-p28 | RULES UPDATES / FAQS | — | 5 条 change-to：4 条落 `text_patch`，1 条已滚入免补 |

**11 版分队定式已换代**：新写法的分队一律是 **1 条分队规则 + 2 增强 + 3 战略**
（Abhuman Auxiliaries / Bridgehead Strike / Designation Force 三页完全同构），
而十版沿用页（Steel Hammer / Armoured Infantry / Grizzled Company）仍是 4 增强 + 6 战略。
Bridgehead Strike 从 4+6 缩到 2+3 就是这次 `removed_11e` 的全部来源。

> **refine 缓存陷阱（本次实测）**：`page_003.md` / `page_004.md` 乍看「只有 3 条战略」像被截断，
> 回原 PDF（PyMuPDF）核对后确认 **refine 是忠实的**，FP 原文就只有 3 条——
> 是 11 版分队变小了，不是页面丢内容。**先回 PDF 再下判断**，别按十版体量假设缺页。
> 反过来 `page_008.md` 是**真截断**（COMBINED FIRE 的 EFFECT 段与 OPENING SALVO 整条丢失）
> 且 `page_008.meta.json` 仍写 `verify_ok: true` ——本次两条战略的正文均回 PDF p8 取全后编码，
> 见下方「遗留观察项」。

---

## 二 · A/B 判定汇总

### 2.1 `text_patches`（12 条，全部落库成功、零让路）

| # | 表.列 | id | 条目 | 漂移 |
|---|---|---|---|---|
| 1 | detachments.rule_text | 000009799 | Fire Zone Purge | 整段替换：十版「从预备队上场**或从运输载具下车**的回合 +1 命中」→ 11 版「WARLORD 从句（BATTLELINE/+1 OC）+ 本回合被摆放上场时 +1 命中」 |
| 2 | detachments.rule_text | 000009868 | Masters of Camouflage | p27 change-to：删去十版的 `(e.g. because it is wholly within a RUIN)` 举例从句 |
| 3 | enhancements.description | 000009801002 | Bombast-class Vox-array | 判据由「单位内有装备 master vox 的模型」→「本单位有 Master Vox 战备技能」 |
| 4 | enhancements.description | 000009801003 | Priority-drop Beacon | 整段改写：Deep Strike 时机放宽 → **ingress move**（11 版新术语） |
| 5 | stratagems.text_zh | 000009802003 | FIRING HOT | 措辞重构（机制不变），WHEN 改「被选中射击时」 |
| 6 | stratagems.text_zh | 000009802005 | SERVO-DESIGNATORS | **双改**：受益方 AM INFANTRY → MILITARUM TEMPESTUS；效果「目标不得享掩体」→ 攻方武器获 `[IGNORES COVER]` |
| 7 | stratagems.text_zh | 000009802007 | ON MY POSITION | WHEN 由「对手近战阶段末」→「对手**冲锋**阶段末」；TARGET 改 engaged REGIMENT |
| 8 | stratagems.phase | 000009802007 | ON MY POSITION | phase 列随 WHEN 归位 `Fight phase` → `Charge phase` |
| 9 | stratagems.text_zh | 000010638007 | ADDITIONAL ARMOUR | 持续期「直到该攻击单位攻击完毕」→「直到阶段结束」 |
| 10 | stratagems.text_zh | 000009862005 | SWIFT INTERCEPTION | p27 change-to：9" → 8" |
| 11 | stratagems.text_zh | 000009870003 | DRAW THEM OUT | p27 change-to：9" → 8" |
| 12 | stratagems.text_zh | 000009870006 | TANGLEFOOT GRENADES | 整段改写：「以本单位为冲锋目标 -2」→「所选 12" 内敌军宣告冲锋 -1」 |

### 2.2 `deactivations`（5 条，`removed_11e`）

Bridgehead Strike 11 版整页重印未收录：
`000009801004` Shroud Projector、`000009801005` Advance Augury（增强）；
`000009802002` BELLICOSA DROP、`000009802004` FIRE AND RELOCATE、`000009802006` AERIAL EXTRACTION（战略）。
原文保留，只置 `fp_status`；这 5 行**不进 payload**。

### 2.3 `inserts`（12 条，`fp11e-am-*`）

| 分队 | 行 |
|---|---|
| Abhuman Auxiliaries | `fp11e-am-abhuman`（规则 Absolutist Principles）、`-e1` Sharp Eyes, Light Fingers、`-e2` Exemplar of Duty、`-s1` THICK-SKULLED OBDURANCE、`-s2` LOW PROFILE、`-s3` STIRRED TO ACTION |
| Designation Force | `fp11e-am-designation`（规则 Designated Targets）、`-e1` Long-range Scout、`-e2` Recon Star、`-s1` CLOSE-RANGE DETECTION、`-s2` TRIGGERED ALERTS、`-s3` SUMP-SMOG SCREEN |

增强 `cost` 一律置空（FP 不含点数，MFM 缓存无增强数据——诚实置空，勿猜）。

### 2.4 免补（identical / 已滚入）

- Steel Hammer 的 1 规则 + 4 增强 + 6 战略、Armoured Infantry 的 1 规则 + 4 增强 + 6 战略、
  Grizzled Company 的 1 规则 + 4 增强 + 5 战略（ADDITIONAL ARMOUR 除外）——逐字一致。
- p27 的 Siege Regiment · Artillery Support · **Creeping Barrage change-to**：库现文已逐字为
  11 版（Wahapedia 已滚入 shaken 机制），**唯一一条不落补丁的 RULES UPDATES 项**。
- `tests/test_simulator_dsl_pr29_payload.py::test_reprinted_detachments_left_untouched`
  用 FP 正文判据短语 + 「这三分队的战略/增强 id 不得出现在 text_patch 清单里」双向锁死免补结论。

### 2.5 无法落账的一项（诚实披露）

`detachments` 表**不在** `fp_rules._DEACTIVATE_TABLES` 白名单内（该白名单只含
`stratagems` / `enhancements`）。Bridgehead Strike 在库里有**两条**分队规则行——
`000009798` Only the Best 与 `000009799` Fire Zone Purge——而 11 版整页重印只收录后者。
`Only the Best` 疑为 11 版删除，但**无法打 `removed_11e` 标记**，故：
① 保留原行不动；② 在 DSL 条目 `det000009798` 的 `not_modeled_notes_zh` 里写明；
③ 本工作单记录。它本身是「重掷命中骰 1」，无论如何都是 `not_modeled`，不影响模拟结果。

---

## 三 · DSL 编码盘面

**122 条 = 1 军规 + 14 分队规则 + 65 战略 + 42 增强**
（战略 62 库内 − 3 `removed_11e` + 6 `fp_new`；增强 40 库内 − 2 + 4）

| 三态 | 条数 | 占比 |
|---|---|---|
| `encoded` | **13** | 10.7% |
| `partial` | **20** | 16.4% |
| `not_modeled` | **89** | 73.0% |

星界军可编率低是**阵营气质决定的**：它的核心机制是**命令（Orders）**——军规「指挥之声」
是六道命令择一、按军官逐单位下达、带每战轮条数上限 + 6" 范围 + 士气门；
分队层再叠上移动域（Iron Tread / Blazing Advance / Burst of Speed…）、预备队域、
目标点经济、登舰行动舱门。这几类全无引擎载体，故 `not_modeled` 占七成。

### 3.1 `encoded`（13 条）

| id | 条目 | 通道 | 门 |
|---|---|---|---|
| det000009860 | Armoured Fist（分队规则） | wound/modify +1 | `phase_shooting` × `disembarked_this_turn` |
| 000008381005 | FIELDS OF FIRE | save/ap_improve +1 | `phase_shooting` |
| 000009390002 | BRUTAL TRAINING | attacks/modify +1、wound/s_improve +1 | `phase_melee` |
| 000009802003 | FIRING HOT | wound/s_improve +1、save/ap_improve +1 | `ranged_within_12` × `weapon_filter=hot-shot` |
| 000009858004 | FLARE BURST | hit/reroll | `ranged_within_12` |
| 000009866006 | FURIOUS CANNONADE | save/ap_improve +1 | `ranged_within_12` |
| 000009866007 | ABLATIVE PLATING（守方） | damage/damage_reduction 1 | `phase_shooting` |
| 000010638004 | VETERAN SHARPSHOOTERS | save/ignores_cover | `phase_shooting` |
| 000010638007 | ADDITIONAL ARMOUR（守方） | save/ap_improve −1 | `phase_shooting` |
| 000010788002 | ENGINE OF WRATH | attacks/modify +6、save/ap_improve +2 | `phase_melee` |
| 000010788005 | SHATTERING SALVO | save/ignores_cover | `phase_shooting` |
| 000010788007 | ACCURACY UNDER PRESSURE | hit/reroll | `phase_shooting` |
| 000010792007 | OPENING SALVO | wound/modify +1 | `phase_shooting` × `disembarked_this_turn` |

### 3.2 `partial`（20 条，均带残量注记）

- **分队规则 2**：Purge-Sweep Protocols（舱门几何按恒满足）、Masters of Camouflage
  （第二从句「另有掩体来源时 Sv+1」会与本条第一从句自我叠加，故只编掩体本体）。
- **战略 11**：STALWART PROTECTOR、DUCK AND COVER、SERVO‑DESIGNATORS、FURIOUS FUSILLADE、
  CLEAR AND SECURE、COURAGEOUS DIVERSION、PURGING FIRE、MORDIAN MINUTE、COMBINED FIRE、
  THICK-SKULLED OBDURANCE、SUMP-SMOG SCREEN。
- **增强 7**：Drill Commander、Legacy Sidearm、Sacred Unguents、Smoke Grenades、
  Indomitable Steed、Omnissian Unguents (Aura)、Exemplar of Duty。

残量三大类：① 目标点 / 光环 / 遮挡可见性 / 舱门等**几何前提**按恒满足处理（高估）；
② **攻方或守方自关键词门**（引擎只有目标关键词门），注入到任何单位都会生效，适用性使用者自查；
③ **只作用于携带者本人**的增强被按单位面注入，多模型单位会高估。

### 3.3 `not_modeled` 主要类别（89 条）

| 类别 | 条数级 | 代表 |
|---|---|---|
| 命令（Orders）域 | 21 | 军规「指挥之声」、无情纪律、中队指挥、天鹰之眼、特勤老兵、灵活指挥… |
| 移动 / 搭乘 / 冲锋资格域 | ~20 | 铁履、炽烈突进、爆发速度、快速疏散、仓促撤离、ingress move、surge move |
| 预备队 / 部署 / 重新部署 | ~10 | 威压降临、扰频立场、侦察骑兵、游击荣勋、Scouts、Infiltrators |
| 登舰行动舱门 | 4 | 闲手、封锁、诡雷致盲手雷、卧倒！ |
| 目标点经济 / 士气 / CP | ~8 | 绝不后退！、大胆领导、凋敝火力、惊惧毒气手雷、舰载老兵 |
| 11 版侦测距离 / hidden | 5 | 指定目标、近距侦测、锐眼巧手、低伏身形 |
| 防高估（有通道但门无载体） | ~12 | 见 3.4 |

### 3.4 防高估清单（**有引擎通道、但被无载体的前置门锁死 → 一律不编**）

1. **重掷特定点数「1」**：Only the Best / Ruthless Discipline 第二从句 / Veteran Crew。
   引擎 `hit|wound reroll` 只有「重掷全部失败骰」一种语义，裸编高估。
2. **负关键词门**：Born Soldiers 第一从句「排除 MONSTER/VEHICLE」——引擎只能表达「有关键词」。
3. **射击 × 目标关键词**：Born Soldiers 第二从句、SUPPORTING ORDNANCE。
   只有通用 `target_has_keyword`（近战会误放行）与 `melee_target_has_keyword`，无射击侧复合 tag。
4. **多选一状态**：军规六道命令、Artillery Support 三选一、Aquilan Eye / Spec Ops Veteran
   新增的**可选**命令——裸编任一分支等于把多选一当恒开。
5. **攻方自身战损档**：FINAL HOUR（本单位低于半编）。开关 `target_below_half` 是守方档。
6. **攻方自身抵达态**：Fire Zone Purge（本回合被摆放上场）。分队规则条目**非 opt-in**
   （`select_entries` 选中分队即自动施加），裸编 = 全军每个射击阶段恒享 +1 命中。
7. **严格 S<T 且跨相位**：Elimination Force。`melee_s_lte_t` 既含 `S==T` 又丢掉射击侧，双向失真。
8. **重掷伤害骰**：Titan Killer。damage 通道只有 `modify` / `damage_reduction`。
9. **交战范围命中惩罚豁免**：Ceaseless Cannonade。引擎射击序列**本就不施加**该惩罚，
   裸编 `ignore_hit_mods` 会**凭空造出**加成。
10. **暴击致伤触发效果**：AGAINST THE ODDS。引擎只有 `wound/crit_threshold`（改阈值），
    无「暴击后施加效果」通道。
11. **攻击序列外致命伤 / 自伤**：ON MY POSITION、MINEFIELD。
12. **跨方负面状态**：Tripwires（守方给敌方攻方挂 stunned）。

### 3.5 阶段门纪律（双向核对结论）

- **该加的加**：18 条 WHEN 落单一相位的挂 `phase_shooting`，2 条挂 `phase_melee`。
- **不该加的不加**（反方向守卫）：WHEN 写「对手射击阶段**或**近战阶段」的
  DUCK AND COVER / THICK-SKULLED OBDURANCE、以及常驻型（掩体 / FNP / 光环 / 手枪 A+2）
  **一律不加相位门**——过度加门＝欠建模，同属事实错误。
  掩体的射击专属由引擎自身承担（`effect_params.py` 的
  `if cover_active and stance.phase == "shooting"`），DSL 不重复加门。
  `test_duck_and_cover_hit_penalty_applies_in_both_phases` 用两相位行为断言给这个决定背书。
- **本次新落一条判据（自审 HIGH，同型第五次）**：
  `half_range` 与 `stationary` 两个 tag **只读态势字段、不自含相位门**
  （对比 `ranged_within_12` 的 `stance.phase == "shooting" and ...`）。
  原文限「远程武器」却只能挂这两个 tag 的条目（FURIOUS FUSILLADE / Drill Commander），
  在「近战模拟 + 该开关仍开着」时会误放行。本 PR 不为一条加新复合 tag，
  改为**一律降 `partial` 并把过度施加写进注记**，并加两道守卫：
  `test_phase_blind_tag_entries_are_partial_and_disclosed`（结构）+
  `test_furious_fusillade_leaks_into_melee_as_disclosed`（把已披露的泄漏钉成可执行事实——
  将来引擎补了复合 tag，这条会红，提示回来收紧编码）。

---

## 四 · 验证

| 项 | 结果 |
|---|---|
| `python -m db_compile fp-rules` | text 应用 12 / 幂等 137 / **让路 0**；失效 5；插行 12 |
| `python -m db_compile dsl-apply` | 幂等 2476、指纹让路 0、跳过 0；全库三态 171 / 520 / 1785 |
| `python -m pytest tests/ -q` | **1673 passed**（PR 前基线 1605，+68） |
| gold v3 基准（`--path agent`） | **97.9，0 硬错**（94 ✅ / 2 ⚠️ / 0 ❌），`benchmarks/v3_edition11/qa_agent_results_p7pr29.json` |
| code-reviewer 自审 | 0 CRITICAL / 1 HIGH / 4 MEDIUM / 4 LOW → HIGH 与 3 个 MEDIUM 已修，其余转观察项 |

### 4.1 基准两条 ⚠️ 的逐题核对（非回归）

本 PR 是纯编码 + DB 文本层补丁，**不进 FAISS 检索语料**，检索侧零影响。
最终一轮的两条 ⚠️ 是 **#41 / #42**，与既有记录的固定波动题名单**完全重合**。

跑了两轮做交叉验证（自审修复前后各一轮），两轮都是 97.9 / 0 硬错，但**波动题换了人**：

| 轮次 | ⚠️ 题号 |
|---|---|
| 第一轮（自审修复前） | #19（星际战士 · 连长招牌技能）、#42 |
| 最终轮（自审修复后） | **#41、#42** |

- **#19 两轮之间自己翻回 ✅**——第一轮它的 `sources` 列表与紧邻基线
  `qa_agent_results_p7pr28.json` **逐项字节一致**（检索侧完全没变），差异只在 LLM 综合时
  改成列举各型连长变体而没点名「战斗之仪」。翻回 ✅ 坐实了这是纯生成侧不确定性。
- **#42（兽人 · 兽人小子格斗武器）**：答案正文与基线**同一句**（S4 AP0），
  只是判官时而改口说「漏了 Big choppa / Choppa / Power klaw」。兽人兵牌本 PR 未触碰。
- **#41**：记忆中早已登记的固定波动题，本 PR 未触碰该阵营数据。

三题分属星际战士 / 兽人 / 帝皇之子，**没有一题属于星界军**，且本 PR 改动的
DSL payload 与 DB 文本补丁均不进向量索引。判**无回归**。

---

## 五 · 遗留观察项（不阻塞，未落本 PR）

1. **`data_refined/.../page_008.md` 真截断**：COMBINED FIRE 的 EFFECT 段与 OPENING SALVO
   整条缺失，而 `page_008.meta.json` 仍是 `verify_ok: true, fallback: false`。
   本 PR 的两条编码已回原 PDF p8 取全正文，**DSL 无误**；但 RAG 检索侧该页是残页，
   问「协同火力 / 首轮齐射」会拿到截断上下文。**建议重跑该页 refine 并重新 ingest**。
   （同时说明 `verify_ok` 这道自检对「尾部截断」不敏感，值得单独加长度/结构校验。）
2. **`SERVO‑DESIGNATORS` 名字含 U+2011 不换行连字符**（上游 Wahapedia 原样）。
   `dsl._norm_token` 只归一弯撇号，不归一 `‑ – —`（而 `fp_rules._norm_text` 归一了），
   所以 CLI/网页用 ASCII 连字符点名这条战略会「无匹配」。修法很小（把同一组连字符归一
   加进 `_norm_token`），但属引擎侧改动，与本 PR「纯编码」定位不符，**留作独立小 PR**。
3. **p27-p28 的 datasheet 层改动未落**：Tempestus Scions / Tempestus Aquilons 的 BS→3+、
   Krieg Heavy Weapons Squad laspistol Range→12"、Catachan / Krieg Command Squad 补武器格、
   Kasrkin 武器表增删、28 个单位加 `FRAME` 关键词、以及若干技能改写。
   沿死亡守望 / 圣血修女 / 帝国代理先例，datasheet 层不落本 PR（本 PR 零 `fp_errata`）。
   `FRAME` 沿 S4 裁定跳过（测距词）。
4. **`name_patches` 未做**：星界军 `detachments` / `stratagems` 的 `name_zh` 仍全 NULL
   （仅 `fp_new` 的 2 规则 + 6 战略自带中文名）。补中文名需逐条对十版中文 codex refine 缓存
   配对并避让已注册 `name_zh`，属独立工作量，不落本 PR。
5. **`enhancements` 表无 `name_zh` 列**（`fp_rules._INSERT_COLUMNS` 即如此），
   故全部 42 条增强条目的 `name_zh` 均为 `null`——这是表结构决定的，不是漏填。
