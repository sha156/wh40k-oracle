# P7-PR27 帝国机械教 fp_rules 逐行 A/B 工作单 + DSL 编码盘面（2026-07-21）

对照源：`data_refined/Faction Pack Adeptus Mechanicus/`（26 页，FACTION PACK VERSION 1.0，
Legal from 2026-06-20，"first iteration — all of the following content should be regarded as new"）
vs `db/wh40k.sqlite`（`faction='AdM'`）。体裁沿 PR1/PR4–PR26。

## FP 内容面

| 页段 | 内容 |
|---|---|
| p1 | 目录页（声明 5 分队 / 4 兵牌 / Rules Updates / Legends） |
| p2 | **全新分队 Cohort Acquisitus**（Noospheric Recon：1 规则 + 2 增强 + 3 战略） |
| p3 | **全新分队 Lords of the Forge**（War-Form Mantles：1 规则 + 2 增强 + 3 战略）——**refine 截断** |
| p4 | **全新分队 Luminen Auto-choir**（Cyber-Static Canticles：1 规则 + 2 增强 + 3 战略） |
| p5-p6 | Eradication Cohort（Murderous Imperative + 4 增强 + 6 战略）——库内已有 |
| p7-p8 | Haloscreed Battle Clade（Noospheric Transference + 4 增强 + 6 战略）——库内已有 |
| p9-p16 | 新兵牌 4 张：Thulia Ghuld / Hastarii Exterminators / Hastarii Fusiliers / Servitor Battleclade |
| p17-p18 | **Rules Updates**（军规改写 + 2 分队条目改写 + 一批兵牌勘误 + 1 条 FAQ） |
| p19-p26 | **Legends 兵牌 4 张**：X-101 / Secutarii Hoplites / Secutarii Peltasts / Terrax-pattern Termite |

库内 `faction='AdM'` 共 **10 个分队容器**（Cohort Cybernetica / Data-Psalm Conclave /
Eradication Cohort / Explorator Maniple / Haloscreed Battle Clade / Rad-Zone Corps /
Skitarii Hunter Cohort 七个正式分队 + Electromartyrs / Machine Cult / Response Clade
三个**登舰行动（Boarding Actions）分队**）。登舰行动分队是独立游戏模式、不在 FP 范围内，
**不作 removed_11e**，但纳入 DSL 编码盘面（沿 tau / orks / imperialagents / chaosdaemons 先例）。

### refine 截断逐条回原 PDF 复核

`page_003.md` 在 `SCRIPTURAL PROGNOSIS` 的 `**Target` 处**硬截断**——整个 Lords of the Forge
的第 1 战略后半 + 第 2/3 战略全部丢失。回原 PDF（`data/Faction Pack Adeptus Mechanicus.pdf`
第 3 页，PyMuPDF `get_text("text")`）逐字取全：

| 疑点 | PDF 复核结论 |
|---|---|
| SCRIPTURAL PROGNOSIS 只到 `**Target` | **refine 截断**：PDF 有完整 TARGET/EFFECT（`Attacks that target your unit have -1 AP until that enemy unit has attacked.`） |
| Lords of the Forge 疑似只有 1 战略 | **refine 漏页尾**：PDF 另有 `OVERLOADED SAFEGUARDS` 与 `HOLY AVARICE` 两战略 |
| Cohort Acquisitus（p2）只有 3 战略 | **FP 原版即如此**（紧凑分队体例，非漏抄）——PDF p2 逐字复核确认 |

其余 p4/p5/p6/p7/p8/p17/p18 亦逐页与 PDF 对照，refine 与原文一致。

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，7 条）

| 表 | id | 名称 | 判定 |
|---|---|---|---|
| abilities | 000002087_a3 | Bomb Rack | 整替：十版「每次本模型结束普通移动 → 点名被跨越的敌军单位 → 六 D6，4+ 各 1 致命伤」⇒ 11 版「**在对手战斗阶段结束时** → 点名 **24" 内可见**敌军单位（**排除 Lone Operative**）→ 六 D6，4+ 各 1 致命伤」（FP p17） |
| abilities | 000002085_a3 | Aerial Deployment | 整替：十版「若以 Hover 模式起始于战略预备队 → 可于第 1/2/3 移动阶段增援步骤上场」⇒ 11 版「**在你的第一个移动阶段，本单位可做一次 ingress 移动**」（FP p17；配合同页 Transvector 去 AIRCRAFT） |
| abilities | 000002082_a2 | Tactica Obliqua | 三处漂移：① 删「每回合一次」限；② 触发半径 **9" → 8"**；③ 触发时机由「敌军结束 Normal/Advance/Fall Back 移动」放宽为「**在对手移动阶段**敌军结束**任意**移动」（FP p18） |
| stratagems | 000009746007 | ANALYTICAL DIVINATION | 仅触发距离 **9" → 8"**，其余从句逐字一致（FP p8） |
| stratagems | 000010748005 | THREAT‑COGITATION TARGETERS | **上游空壳行归位**：库内该行 `text_zh` / `detachment` / `phase` **三列皆空**（只剩 id + faction + cp_cost）。FP p6 有全文，逐字补录并归位到 `Eradication Cohort` / `Shooting phase`（三条 text_patch） |

> 为承载上一条，`db_compile/fp_rules.py` 的 `_TEXT_TARGETS` 白名单加了
> `("stratagems","detachment")` 与 `("stratagems","phase")` 两项（沿 PR6 加
> `("detachments","name_en")`、PR7 加 `("stratagems","cp_cost")` 的先例）。
> 回归守卫见 `test_no_orphan_adm_stratagem_outside_detachments`。

### 真漂移已补（fp_errata，3 stat + 1 keyword）

| 类型 | 单位 | 字段 | 判定 |
|---|---|---|---|
| stat | Archaeopter Fusilave (000002087) | m | `20+"` → `-`（FP p17「Change M and OC to '-'」；**OC 0→'-' 不补**，功能等价且库无 '-' OC 先例，防下游 int 解析破坏，同 Heldrake / Ravenwing Dark Talon 处理） |
| stat | Archaeopter Stratoraptor (000002086) | m | 同上 |
| stat | Archaeopter Transvector (000002085) | m | `20+"` → `14"`（FP p17） |
| keyword | Archaeopter Transvector (000002085) | keywords | remove `Aircraft`（FP p17） |

### 假警报 / 让路（fp_errata `resolved`，3 条）

| 单位 | 项 | 裁决 |
|---|---|---|
| Skorpius Disintegrator / Dunerider | Add 'FRAME' keyword | **不补**：`keyword_patches` 层策略明定「主列表只删不加」（新增关键词属重印整表体裁，走 new_units / 上游滚更），故只记录不落补丁 |
| Onager Dunecrawler | Eradication beamer A→3D3, S→10 | **DB 正确不改**：库内两档 A 均已 `3D3`（说明该勘误已由 Wahapedia 滚入），focused 档 S=10 一致、dissipated 档 S=9 属档位差；单行 change-to 无法判定是否要抹平两档，保守不动 |
| Skitarii Marshal / Technoarcheologist / Cybernetica Datasmith / Fusilave / Stratoraptor / Dunerider | Remove 'Leader' add 'Support' / Remove 'Hover' / Add 'Firing Deck 2' | **不补**：均为**核心技能层**，库 `abilities` 表只存兵牌特有技能，无核心技能行可补 |

### 重印未收录（deactivations）：**0 条**

FP 对 10 个库内分队全部是**逐条重印**，无任何删减条目，故零 `removed_11e`。

### 已滚入 / 已满足免补（identical）

- **军规 Doctrina Imperatives（`abilities` 000008382）**：FP p17 的 Protector / Conqueror
  两段 change-to（[HEAVY]+BS改善 / [ASSAULT]+WS改善 + BATTLELINE 邻接条款）与库现文本**逐字一致** → 免补
- **Cyber-Psalm Programming（000008571）**：FP p17 change-to 与库现文本逐字一致 → 免补
- **Veiled Hunter（000008560004）**：FP p17 change-to 与库现文本逐字一致 → 免补
- **Skitarii Marshal Servo-skull Uplink（000002478_a2）** / **Onager Scuttling Walker（000000854_a3）**
  / **Belisarius Cawl 四条技能改写 + M 8" + Solar atomiser A3/D D6** / **Onager 其余 3 把枪**
  / **Ironstrider 双枪** / **Sicarian Infiltrators & Ruststalkers 近战武器** / **Skorpius Disintegrator
  Ferrumite cannon D6+1**：库现值全部已等于 FP change-to（Wahapedia 已滚入 6 月勘误）→ 免补
- **Eradication Cohort / Haloscreed Battle Clade 两分队**（规则 + 各 4 增强 + 各 6 战略）：
  除上表两条外逐条一致 → 免补
- **FAQ（p18，1 条：Auto-divinatory Targeting 与 Protector Imperative 的 BS 修正次序）**：
  纯裁定说明，零规则文本改动 → 零 text_patch

### 补录插行（fp_rules inserts，18 条，id 前缀 `fp11e-admech-`，cost 置空）

| 分队 | 规则 | 增强 | 战略 |
|---|---|---|---|
| Cohort Acquisitus（p2，侦察系） | `-acquisitus`（Noospheric Recon） | `-acquisitus-e1/e2` | `-acquisitus-s1/s2/s3` |
| Lords of the Forge（p3，TECH-PRIEST 系） | `-lordsforge`（War-Form Mantles） | `-lordsforge-e1/e2` | `-lordsforge-s1/s2/s3` |
| Luminen Auto-choir（p4，ELECTRO-PRIESTS 系） | `-luminen`（Cyber-Static Canticles） | `-luminen-e1/e2` | `-luminen-s1/s2/s3` |

- A/B 已确认 3 个分队规则名 + 6 增强名 + 9 战略名在库内 **0 命中**（无同名异 id，不需
  `expect_duplicate_name` 旗标）
- `detachments.name_en` 按库内体例存**规则名**（如 Eradication Cohort 存 `Murderous Imperative`），
  分队名进 `stratagems.detachment` / `enhancements.detachment_name`
- 三个分队均为 3 战略 + 2 增强（紧凑分队体例，FP 原版面即如此，非漏抄）

**观察项（不落库，datasheet / RAG 层，非 DSL 阻塞，留后续）**：
① FP p9-p16 的 4 张新兵牌（Thulia Ghuld / Hastarii Exterminators / Hastarii Fusiliers /
Servitor Battleclade）；② p19-p26 的 4 张 Legends 兵牌；③ FRAME / Support / Firing Deck 2
等核心技能层缺列。

## DSL 编码盘面（`dsl_payloads/admech.json`）

**覆盖面**：1 条军规 + 13 个分队容器 = **14 条 abilities（军规 1 + 分队规则 13）+ 63 战略
+ 40 增强 = 117 条**（库内 1 + 10 + 54 + 34 = 99 行，加 fp_new 3 + 9 + 6 = 18 行）。
AdM 零 `removed_11e` 行，故无零覆盖条目。

**三态：16 encoded / 18 partial / 83 not_modeled**。零新引擎通道、零新态势开关（纯编码 PR），
只复用既有的 `bearer_leading` / `defender_bearer_leading` / `disembarked_this_turn` 三个假设开关。

### 可编率为何偏低：阵营气质

帝国机械教是「**指令切换 + 目标点经济 + 远程增益**」气质阵营。四类主干机制全无引擎载体：

1. **教义指令（军规）**：每战轮在守护 / 征服中**二选一**——引擎无 imperative 状态开关。
   连带 6 条条目（Murderous Imperative / TRANSCENDENT COGITATION / Omnicogitator /
   Cognitive Reinforcement / Cantic Thrallnet / Procedural Elimination）一并 not_modeled。
2. **「获取目标点」经济**：Explorator Maniple 整个分队 + Acquisition At Any Cost 军团规则
   围绕目标点几何展开——引擎无目标点。
3. **重掷「1」**：机械教的招牌增益形态（Acquisition At Any Cost / Murderous Imperative /
   Procedural Elimination / ERADICATION PROTOCOLS / ECHOES OF THE CONDUIT WARS）——
   引擎 `hit/reroll`·`wound/reroll` 只有「重掷失败」一种模式，重掷特定点数无通道。
4. **登舰行动地图机制**（Electromartyrs / Machine Cult / Response Clade 三分队的舱门 /
   可见性 / 权限条目）——地图域无载体。

### encoded（16 条）

| 表 | id | 名称 | 通道 |
|---|---|---|---|
| stratagems | 000008565003 | CHANT OF THE REMORSELESS FIST | wound/modify +1 · `phase_melee` |
| stratagems | 000008565007 | LUMINESCENT BLESSING | save/invuln 4 · `phase_shooting` |
| stratagems | 000009282003 | BALLISTIC SYNCHRONY | hit/auto_wound（[LETHAL HITS]）· `phase_shooting` |
| stratagems | 000009282005 | SAVIOUR SYSTEMS | wound/modify -1（守方）· `phase_shooting` |
| stratagems | 000010748002 | SERVO‑DRIVEN CHARGE | wound/modify +1（[LANCE]）· **`melee_charging`** |
| stratagems | 000008569006 | INCENSE EXHAUSTS | save/cover · `phase_shooting` |
| stratagems | 000009746003 | TARGETING OVERRIDE | hit/crit_threshold 5 · 无门（两相位） |
| stratagems | 000008386002 | BALEFUL HALO | wound/modify -1（守方）· **`phase_melee`** |
| stratagems | 000008386007 | BULWARK IMPERATIVE | save/invuln 4 · `phase_shooting` |
| stratagems | 000008386006 | LETHAL DOSAGE | hit/auto_wound · `phase_shooting` |
| stratagems | 000008561003 | BINHARIC OFFENCE | save/ap_improve +1 · 无门（两相位、全部武器） |
| stratagems | 000008561002 | BIONIC ENDURANCE | fnp/fnp 5 · 无门（两相位） |
| stratagems | 000008561005 | ISOLATE AND DESTROY | wound/modify +1 · `phase_shooting` |
| enhancements | 000008385003 | Malphonic Susurrus | save/cover · `phase_shooting` + `defender_bearer_leading` |
| enhancements | 000008385004 | Peerless Eradicator | hit/extra_hits 1 · `phase_shooting` + `bearer_leading` |
| enhancements | fp11e-admech-luminen-e2 | Electromiasmic Brazier | save/cover · `phase_shooting`（整单位，**不挂** bearer 开关） |

### partial（18 条，残量已逐条写进 `not_modeled_notes_zh`）

| 表 | id | 名称 | 已编 | 残量 |
|---|---|---|---|---|
| abilities | det000009280 | Overload Machine Spirits | save/ap_improve +1 | [HAZARDOUS] 自伤未建模（高估）；「可选使用」按恒用编码 |
| abilities | det000008559 | Stealth Optimisation | save/cover | SKITARII 自关键词门；SICARIAN「攻方不在 12" 内」反向距离门 |
| abilities | detfp11e-admech-lordsforge | War-Form Mantles | save/invuln 4 + fnp/fnp 5 | TECH-PRIEST 自关键词门；Baffling Data Screed（士气 / 隐蔽） |
| abilities | detfp11e-admech-luminen | Cyber-Static Canticles | hit/auto_wound | CORPUSCARII 自关键词门；FULGURITE 治疗 D3 |
| stratagems | 000008573003 | AUTO-DIVINATORY TARGETING | save/ignores_cover | BS 特征值 **SET** 3+（引擎只有相对 bs_improve） |
| stratagems | 000008573007 | BENEVOLENCE OF THE OMNISSIAH | fnp/fnp 6 | 对致命伤改善为 5+ 的分档（欠建模） |
| stratagems | 000008573005 | MACHINE SUPERIORITY | hit/ignore_hit_mods | 撤退后可射击；对致伤 / 伤害 / 保存等其他修正的忽略（欠建模） |
| stratagems | 000008569005 | AUTO-ORACULAR RETRIEVAL | wound/modify +1 · `phase_shooting` | 目标点几何（高估）；挂 `disembarked_this_turn` |
| stratagems | 000008386005 | PRE-CALIBRATED PURGE SOLUTION | hit/reroll fail | 对手部署区几何（高估） |
| stratagems | 000009291004 | PRECOGNITATED FIREFIELDS | hit/extra_hits 1 | BATTLELINE 升 [SUSTAINED HITS 2] 的自关键词分档（**保守欠建模**） |
| stratagems | 000009291002 | RESPONSIVE SHIELDING | save/invuln 4 | 「本单位在目标点范围内」几何（高估） |
| stratagems | fp11e-admech-acquisitus-s1 | DEFECT SCRUTINY | save/ignores_cover | 友军 RECON AUGURY 12" 内的第三单位几何（高估） |
| stratagems | fp11e-admech-lordsforge-s1 | SCRIPTURAL PROGNOSIS | save/ap_improve -1（守方） | 目标点几何（高估）；「直到该敌军单位攻击完毕」的持续期短于整阶段（高估） |
| enhancements | 000010747004 | Belicosa-Class Capacitor Vanes | wound/s_improve +1 · `phase_shooting` | +6" 射程（引擎不建模距离） |
| enhancements | 000010747005 | Omnissiah's Fury | attacks +2 / ap_improve +1 / damage +1 · `phase_melee` | 仅**携带者本人**的近战武器（多模型单位会高估） |
| enhancements | 000009745005 | Inloaded Lethality | attacks +3 / damage +1 · `phase_melee` | 同上 |
| enhancements | 000008568003 | Genetor | save/invuln 4 | 目标点几何（高估） |
| enhancements | 000008568004 | Logis | hit/modify +1 | 目标点几何（高估） |

### 阶段门纪律（双向核对）

- **WHEN 落在单一相位** ⇒ 挂 `phase_shooting` / `phase_melee`（19 + 4 条，见测试
  `TestPhaseGating.SHOOTING_ONLY` / `MELEE_ONLY`）
- **WHEN 写「射击阶段**或**近战阶段」** ⇒ **一律不加门**（10 条，见 `BOTH_PHASES`）。
  过度加门＝欠建模，同属事实错误——反方向也写了守卫断言
- **阶段性 WHEN 顺 WHEN 往后推**：`BALEFUL HALO` 的 WHEN=战斗阶段、持续「到回合结束」——
  战斗是回合**最后一个**攻击阶段，故本回合仍只有近战可受益 ⇒ `phase_melee`
- **[LANCE] 用复合 tag**：`SERVO‑DRIVEN CHARGE` 必须 `melee_charging`，
  裸 `charging` 会在射击阶段误放行（PR5 先例）

### 防高估清单（明确不编）

重掷特定点数「1」· 仅致命伤 FNP（INCANTATION OF THE IRON SOUL）· 特征值 **SET**
（BS 3+ / 伤害置 1 / 伤害置 0）· 多选一单分支（教义指令 / 万机神的祝祷 / Override 四选一 /
UNSHACKLED WRATH 三选一）· **「射击 × 目标关键词」无复合 tag**（Arch-negator [ANTI-VEHICLE]、
Autoclavic Denunciation [ANTI-INFANTRY/MONSTER]——裸 `target_has_keyword` 会在近战误放行）·
**6" 距离档**（ELECTROGHEIST VISITATIONS；引擎只有 8"/12"，8" 档会对 6"–8" 误放行）·
**攻方自身战损档**（MACHINE SPIRIT RESURGENT；引擎 `target_below_*` 是目标侧）·
按 [PISTOL] 关键词挑武器（OMNI-TARGETERS；`weapon_filter` 只认名字子串）·
增强授予整把新武器（TL-4Ø9，属装配层职责）· 复活 / 出手顺序 / 单次触发 / CP / 士气 /
移动 / 预备队 / 外部致命伤池 / 关键词授予 / 可见性 / 舱门。

## 验证

| 项 | 结果 |
|---|---|
| `python -m db_compile fp-rules` | 文本应用 7 / 幂等 117 / 让路 0；插行应用 18 / 幂等 300 / 让路 0 |
| `python -m db_compile fp-errata` | 属性应用 3 / 关键词应用 1 / 让路 0 / 跳过 0 |
| `python -m db_compile dsl-apply` | 全库 2157 条投影（141 → 139 encoded / 456 partial / 1562 not_modeled），指纹让路 0 |
| `python -m pytest tests/ -q` | **1552 passed**（新增 `tests/test_simulator_dsl_pr27_payload.py` 65 条） |
| gold v3 基准 run1 | 97.9，hard error = 0（`benchmarks/v3_edition11/qa_agent_results_p7pr27.json`） |
| gold v3 基准 run2（同分支 recheck） | **99.0，hard error = 0**（`..._p7pr27_recheck.json`）——与 PR26 基线持平 |

### 基准逐题对账（vs 紧邻基线 PR26 recheck）

run1 唯一 verdict 变动：**#42（兽人「兽人小子的格斗武器 S 和 AP」）✅ → ⚠️**，属**已知波动题**
（记忆中的波动题名单 #41/#42/#63/#86）。**同分支连跑第二次（recheck）#42 即回到 ✅，
总分回到 99.0，非 correct 只剩固定波动的 #41**——坐实是生成侧波动而非回归。逐题 diff 佐证：

- 与 AdMech 无关（兽人题），且本 PR 是纯编码 PR——**DSL / DB 补丁不进 FAISS 检索语料**
  （未 ingest ⇒ 检索侧零影响）
- 两次回答的**结论本体逐字相同**（`Close combat weapon S 4，AP 0`）；PR27 那次多输出了一张
  表格和一句「若指砍刀则 S4 AP-1」的补注，触发 LLM 裁判改用更严的「漏项」口径
  （gold 列了 4 把武器，两次回答都只覆盖其中 1–2 把）
- 三次运行（PR26 基线 + PR27 run1 + PR27 run2）均 **wrong = 0**（零硬错），#41 三次都是 ⚠️（固定波动）

## 自审（code-reviewer 子代理）

| 级别 | 数量 | 处理 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 1 | **已修** |
| MEDIUM | 0 | — |
| LOW | 0 | — |

**HIGH（已修）**：`fp11e-admech-lordsforge-s1`（SCRIPTURAL PROGNOSIS）与 `000009291002`
（RESPONSIVE SHIELDING）原标 `encoded`，但两条原文的 TARGET 都含「**within range of an
objective (marker)**」前提，而引擎无目标点几何载体——效果实际被无条件施加。这与本 payload
对**同一从句**的既有处理（Genetor / Logis / AUTO-ORACULAR RETRIEVAL 均降 partial 并注明
「按恒满足处理（高估）」）自相矛盾，也违反「encoded ⇒ 全部从句落地且零残量注记」的判据。
两条已降 `partial` 并补注记（SCRIPTURAL PROGNOSIS 另补一条：「直到该敌军单位攻击完毕」的
持续期短于整阶段，引擎按整阶段生效亦属高估），三态由 18/16/83 改为 **16/18/83**。

同时加了根因守卫 `test_objective_geometry_entries_are_never_encoded`：扫库内原文，
任何含 `objective` 且落了 effects 的条目一律不得标 `encoded`——原有的
`test_encoded_entries_have_effects_and_no_notes` 抓不到这类**缺注记**的漏网。

## 复用教训

1. **refine 截断要看「句子断在半截」而不只看页长**：p3 的 `**Target` 断口没有任何显式截断
   标记，页长（2218 字节）也不异常——是「一个分队只有 1 条战略」这个**体例反常**先引起怀疑，
   回 PDF 才确认丢了两条战略。凡分队条目数不成套，先回原 PDF 复核。
2. **上游空壳行**：`THREAT‑COGITATION TARGETERS` 在库里三列皆空，靠 `detachment` 过滤的
   对账测试会**静默漏掉**它（不在 active 集里，也就不算漏编）。逐条数 FP 战略数（6）
   与库内数（5 + 1 孤儿）才逮到。已加 `test_no_orphan_adm_stratagem_outside_detachments` 常驻守卫。
3. **同一从句在同一 payload 里必须同一判法**：本 PR 的 HIGH 就是「目标点前提」在增强层降了
   partial、在战略层却标 encoded。自审时按**从句关键词横扫全 payload**（而不是逐条读）
   最容易逮到这类内部不一致。
4. **改既有文件前先看它的换行符**：本仓库无 `.gitattributes`、`core.autocrlf=false`，
   LF / CRLF 文件混存（`tests/*.py` 68 CRLF + 15 LF；`dsl_payloads/*.json` 亦混）。
   `db_compile/fp_rules.py`（LF）被工具改写成 CRLF、`fp_errata_patches.json`（LF）被
   Python 文本模式 `json.dump` 写成 CRLF，各自炸出 275 / 821 行的**假全文件 diff**，
   把 2 行 / 62 行的真改动埋掉。收尾前用 `git diff --stat` 对账行数，
   数字离谱就查换行符（`git diff --ignore-all-space --stat` 一比即知），改回原编码再交。
   新建文件不受此限（仓库本就混存）。
