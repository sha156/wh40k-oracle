# P7-PR26 混沌恶魔 fp_rules 逐行 A/B 工作单 + DSL 编码盘面（2026-07-21）

对照源：`data_refined/Faction Pack Chaos Daemons/`（151 页，FACTION PACK VERSION 1.0，
Legal from 2026-06-20，"first iteration — all content should be regarded as new"）
vs `db/wh40k.sqlite`（`faction='CD'`）。体裁沿 PR1/PR4-PR24。

## FP 内容面

FP 目录（page_001）声明 7 个分队；实际版面分三段：

| 页段 | 内容 |
|---|---|
| p2-p3 | 军规（Shadow of Chaos / Daemonic Manifestation / Daemonic Terror / Daemonic Pact） |
| p4-p12 | **Index 段**：Daemonic Incursion（1 规则 + 6 战略 + 4 增强）、Shadow Legion（2 规则 + 6 战略 + 4 增强） |
| p13 | **PDF 原页即空白**（refine 未产页非截断——PyMuPDF 取第 13 页返回空串，已复核） |
| p14-p119 | Index 兵牌 53 个单位（106 页） |
| p120-p122 | **3 个全新紧凑分队**：Cavalcade of Chaos / Lords of the Warp / Warptide |
| p123-p130 | **4 个神祇分队**：Blood Legion / Scintillating Legion / Plague Legion / Legion of Excess |
| p131 | Rules Updates（**只有 11 条 FAQ，零规则改动**） |

库内 `faction='CD'` 另有 **4 个登舰行动（Boarding Actions）分队**——Dread Carnival /
Infernal Onslaught / Pandaemoniac Inferno / Rotten and Rusted，外加 Daemonic Incursion
的登舰变体（分队规则 Unnatural Energies，`detachment_id=000000953`，与 Index 版
`000000779` 同名异 id）。登舰行动是独立游戏模式、不在 FP 范围内，**不作 removed_11e**，
但纳入 DSL 编码盘面（沿 tau / orks / imperialagents 先例）。

### 疑似漂移逐条回原 PDF 复核

refine 的 `page_004/005/123` 文本有三处与库现文不一致，且其中两处（8" vs 9"、
DISCIPLES 第二条项目符号缺失）**看起来像 OCR/截断**，因此全部回原 PDF
（`data/Faction Pack Chaos Daemons.pdf`，PyMuPDF）逐字复核：

| 疑点 | PDF 复核结论 |
|---|---|
| Warp Rifts 落点 `instead of more than 8"` | **真漂移**（PDF p4 原文即 8"，非 OCR 误读 9→8） |
| DISCIPLES OF BE'LAKOR 只剩 1 条项目符号 | **refine 漏行**：PDF p5 有第二条「SHADOW LEGION HERETIC ASTARTES 模型获 Deep Strike」，库现文已含 → 免补 |
| Murdercall 触发半径 `within 8"` | **真漂移**（PDF p123 原文即 8"） |

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，5 条）

| 表 | id | 名称 | 判定 |
|---|---|---|---|
| detachments | 000008436 | Warp Rifts | 深入打击落点门槛 **9" → 8"**（11 版核心 Deep Strike 距离下调），并入 FP 的断句逗号；其余从句（Shadow of Chaos / 8 个大恶魔点名 / 共享神祇关键词 / 6" 落点）逐字一致 |
| detachments | 000009978 | First Prince of Chaos | 双分支漂移：① **PENUMBRAL PUPPETRY** 十版「任何攻击瞄准本单位命中 -1」→ 11 版「本单位获 **Stealth**，且**近战**攻击瞄准本单位命中 -1」（射击侧改由 Stealth=掩体承载）；② **SHADOW'S CARESS** 十版「敌不能用火力守望战略射击本单位」→ 11 版「敌不能以 **snap shooting** 攻击瞄准本单位」。MURDERER'S COWL / GLOAM ROT / DISCIPLES OF BE'LAKOR 逐字一致，未动 |
| detachments | 000009813 | Murdercall | 三处漂移：① 新增相位限定「在对手移动阶段」；② 触发半径 **6" → 8"**；③ 触发移动类型由「Normal 或 Advance 移动」放宽为「任何移动」。库现文的 surge move 展开式与 FP 压缩式语义同（沿 PR22 Goaded Beast 先例），保留不动 |
| stratagems | 000009979006 | SHADE PATH | 整替：十版「对手冲锋阶段敌宣告冲锋后 → 目标须是被冲方 → 冲锋骰 **-2**」→ 11 版「对手冲锋阶段**开始时** → 目标任选己方 Shadow Legion 单位 → 点名 12" 内一个可见敌单位，其冲锋骰 **-1**」；Nurgle 追加战栗检定从句不变 |
| stratagems | 000009816006 | FOOLS' FLIGHT | 整替：十版「目标须本可合法冲锋该敌单位 → 立即结算一次只打该单位的冲锋，且不获冲锋加成」→ 11 版「目标只需未接战且在 6" 内 → 宣告一次冲锋，选靶时只能选本阶段撤退过、且在最大距离内的敌单位」 |

### 重印未收录（deactivations）：**0 条**

FP 对 6 个现有分队（Daemonic Incursion / Shadow Legion / Blood Legion /
Scintillating Legion / Plague Legion / Legion of Excess）全部是**逐条重印**，
无任何删减条目，故零 `removed_11e`。

### 补录插行（fp_rules inserts，18 条，id 前缀 `fp11e-chaosdaemons-`，cost 置空）

| 分队 | 规则 | 增强 | 战略 |
|---|---|---|---|
| Cavalcade of Chaos（p120，MOUNTED 系） | `-cavalcade`（Unholy Avalanche） | `-cavalcade-e1/e2` | `-cavalcade-s1/s2/s3` |
| Lords of the Warp（p121，CHARACTER 系） | `-lordswarp`（Loci of Power） | `-lordswarp-e1` | `-lordswarp-s1/s2/s3/s4` |
| Warptide（p122，BATTLELINE 系） | `-warptide`（Shudderblink） | `-warptide-e1/e2` | `-warptide-s1/s2/s3` |

- A/B 已确认 3 个分队规则名 + 5 增强名 + 10 战略名在库**基本 0 命中**；唯一例外
  **Swollen with Power** 与 CSM 登舰增强 `000009503003` 同名异 id（内容完全不同），
  挂 `expect_duplicate_name` 旗标放行（沿 PR9 Legacy of the Angel 先例）
- 三个分队的战略/增强数量不齐（3/2、4/1、3/2）是 FP 原版面即如此（紧凑分队体例，
  沿 PR14 Rollin' Deff 先例），非漏录

### 已滚入 / 已满足免补（identical）

- **Daemonic Incursion**（Index）：6 战略（CORRUPT REALSPACE / WARP SURGE / DRAUGHT OF
  TERROR / DENIZENS OF THE WARP / THE REALM OF CHAOS / DAEMONIC INVULNERABILITY）
  + 4 增强（A'rgath / The Everstave / The Endless Gift / Soulstealer）逐条一致
- **Shadow Legion**：Thralls of the First Prince（建军条款 500/1000/1500 + 关键词授予）
  + 其余 5 战略 + 4 增强逐条一致
- **Blood Legion**：Blood Tainted + 其余 5 战略 + 4 增强逐条一致
- **Scintillating Legion / Plague Legion / Legion of Excess**：分队规则 + 各 6 战略
  + 各 4 增强**全套逐条一致**（含 Fates in Flux 的 Designer's Note 与
    Sensory Excruciation 的 Designer's Note）
- **Rules Updates（p131）**：11 条全部是 FAQ（Pink/Blue Horrors Split、Be'lakor 与
  Warp Rifts 的落点交互、Shadow of Chaos 无目标点时的判定、Insane Bravery 与
  LEGIONES DAEMONICA、Daemonic Pact 单位是否吃军规），**零规则文本改动 → 零 text_patch**
- **零 fp_errata**：本 FP 的数值层改动全落在 p14-p119 的 Index 兵牌，沿死亡守望 /
  圣血修女 / 混沌骑士先例作观察项，不落本 PR

**观察项（不落库，datasheet / RAG 层，非 DSL 阻塞，留后续）**：
① p14-p119 的 Index 兵牌 53 个单位（含 Be'lakor 的 Shadow Form 四选一、Pink/Blue
Horrors 的 Split、Giant Chaos Spawn / Spined Chaos Beast / Pox Riders / Plague Toads
等 Legends 与 Forge World 单位）；② 军规四条（Shadow of Chaos / Daemonic
Manifestation / Daemonic Terror / Daemonic Pact）——`abilities` 军规层，沿 PR22
先例本 PR 只覆盖分队规则 + 战略 + 增强。

## DSL 编码盘面（`dsl_payloads/chaosdaemons.json`）

**覆盖面**：CD 全部 13 个分队容器 = **17 分队规则 + 66 战略 + 39 增强 = 122 条**
（= 库内 14 + 56 + 34 = 104 行，加 fp_new 3 + 10 + 5 = 18 行）。
CD 零 `removed_11e` 行，故无零覆盖条目。

**三态：1 encoded / 25 partial / 96 not_modeled**。零新引擎通道、零新态势开关（纯编码 PR），
只复用既有的 `bearer_leading` / `defender_bearer_leading` 两个通用假设开关。

混沌恶魔是**「区域态 + 战栗 + 召唤/预备队」气质阵营**——军规 Shadow of Chaos、
Daemonic Manifestation / Terror、Flux token、Surge move、深入打击落点、复活/治疗、
致命伤池全无引擎载体，可编率是历次最低之一（1/122 encoded，与千子 PR10 的灵能重型
范式同源）。

### encoded（1）

| 条目 | 分队 | 编码 |
|---|---|---|
| INCORPOREAL TERRORS `000009548005` | Daemonic Incursion（登舰） | 守方 (hit, modify, -1) × `phase_shooting` |

判据：原文只有一条 EFFECT 从句（「本阶段内瞄准本单位的攻击命中骰 -1」），目标限定只到
`LEGIONES DAEMONICA`（＝本阵营全体，无神祇子关键词），WHEN 单相位门自含 —— 全从句落地
且零未建模限制，故为本 PR 唯一 `encoded`。

### partial（25）

| 条目 | 分队 | 编码 | 主要残量 |
|---|---|---|---|
| Seductive Gambit（分队规则） | Legion of Excess | (hit, reroll fail) × `melee_charging` | 放弃 Fights First 的代价 + 重投致伤「1」 |
| DRAUGHT OF TERROR | Daemonic Incursion | (save, ap_improve, +1) 两相位 | 对战栗目标重投致伤 |
| CHANNELLED WRATH | Shadow Legion | (wound, modify, +1) × `melee_charging`（[LANCE]） | KHORNE 支 AP+1（己方关键词分支） |
| ENCROACHING DARKNESS | Shadow Legion | (save, ignores_cover) × `phase_shooting` | 限本回合自预备队抵达 + 双单位点名 |
| PYROGENESIS | Scintillating Legion | (wound, s_improve, 2) 两相位 | Flux token 强化支（+3 S 且 AP+1） |
| SEEPING VIRULENCE | Plague Legion | (hit, crit_threshold, 5) × `phase_melee` | 限 NURGLE |
| FEVER VISIONS | Plague Legion | (hit, modify, +1) 两相位 | 战栗检定 + 限 NURGLE |
| ARCHAGONISTS | Legion of Excess | (wound, modify, +1) × `phase_melee` | 限 SLAANESH |
| OVERWHELMING EXCESS | Legion of Excess | 守方 (hit, modify, -1) 两相位 | 限 SLAANESH |
| SEDUCTIVE WHISPERS | Dread Carnival（登舰） | 守方 (hit, modify, -1) × `phase_melee` | 限 SLAANESH |
| FOUL RESILIENCE | Rotten and Rusted（登舰） | 守方 (fnp, 5) 两相位 | 限 NURGLE、排除 NURGLINGS（负关键词门） |
| CALL TO MURDER | Lords of the Warp | (attacks, modify, +1) × `melee_charging` | 限 KHORNE CHARACTER、排除 MONSTER |
| SKIRLING MAGICKS | Lords of the Warp | (hit, auto_wound) × `phase_shooting`（[LETHAL HITS]） | 限 TZEENTCH CHARACTER、排除 MONSTER |
| A'rgath, the King of Blades | Daemonic Incursion | (attacks, modify, +1) + (wound, s_improve, +1)，均 × `phase_melee` | Shadow of Chaos 内改 +2；限携带者 + KHORNE |
| The Endless Gift | Daemonic Incursion | 守方 (fnp, 5) 两相位 | 仅携带者模型（单模型口径）+ 限 NURGLE |
| The Everstave | Daemonic Incursion | (wound, s_improve, +1) × `phase_shooting` | 射程 +3"；Shadow of Chaos 内改 +2/+6"；限携带者 + TZEENTCH |
| Slaughterthirst (Aura) | Blood Legion | (wound, modify, +1) × `melee_charging`（[LANCE]） | 光环几何假设 + 限 KHORNE、排除 MONSTER |
| Fury's Cage | Blood Legion | (hit, reroll fail) + (wound, reroll fail)，均 × `phase_melee` | **自伤 D3+1 致命伤代价不建模 → 净收益被高估** |
| False Majesty (Aura) | Legion of Excess | (wound, modify, +1) × `phase_melee` | 光环几何假设 + 限 SLAANESH、排除 MONSTER |
| Dreaming Crown (Aura) | Legion of Excess | (hit, modify, +1) × `phase_melee` | 同上 |
| Font of Spores (Aura) | Plague Legion | (save, ap_improve, +1) 两相位 | 光环几何假设 + 限 NURGLE、携带者须 MONSTER |
| Neverblade | Scintillating Legion | (wound, s_improve, 2) + (attacks, modify, +1) + (save, ap_improve, +1) + (hit, modify, +1)，均 × `phase_melee` | 限携带者 + TZEENTCH MONSTER |
| Fatal Caress | Dread Carnival（登舰） | (wound, crit_threshold, 5) × `phase_melee` | 仅携带者模型（单模型口径） |
| Fulgurating Presence | Pandaemoniac Inferno（登舰） | 守方 (hit, modify, -1) 两相位 | 仅针对瞄准携带者的攻击（单模型口径） |
| Bane-forged Weapons | Warptide（新） | (wound, s_improve, +1) 两相位 | 限 BATTLELINE（UPGRADE 整单位，**不挂** bearer 开关） |

### 阶段门纪律（本 PR 的双向核对）

- **单相位 WHEN → 必加门**：战斗阶段战略（SEEPING VIRULENCE / ARCHAGONISTS /
  SEDUCTIVE WHISPERS）挂 `phase_melee`；对手射击阶段战略（INCORPOREAL TERRORS）与
  原文明写 ranged / 你的射击阶段的（ENCROACHING DARKNESS / SKIRLING MAGICKS /
  The Everstave）挂 `phase_shooting`；原文写 melee weapons / melee attack 的
  （A'rgath / Neverblade / Fatal Caress / False Majesty / Dreaming Crown / Fury's Cage）
  挂 `phase_melee`。
- **阶段性 WHEN → 顺 WHEN 往后推可生效阶段，落 `melee_charging` 复合门**（本 PR 4 条）：
  - **Seductive Gambit**：「结束冲锋移动后声明，持续到回合结束」——冲锋阶段之后本回合
    只剩战斗阶段，故 `melee_charging`（裸 `charging` 会在射击阶段误放行，裸 `phase_melee`
    会在非冲锋回合误放行）
  - **CALL TO MURDER**：WHEN 明写「本回合冲锋移动过的单位被选中出手」，同上
  - **CHANNELLED WRATH / Slaughterthirst**：授予的是 **[LANCE]**，其规则语义本身即
    「本回合冲锋过时致伤骰 +1」——挂裸 `phase_melee` 会让非冲锋回合白拿 +1，属过度施加
- **两相位 WHEN → 不得加门**（过度加门＝欠建模，同属事实错误，PR13 反方向 MEDIUM 教训）：
  DRAUGHT OF TERROR / PYROGENESIS / FEVER VISIONS / OVERWHELMING EXCESS /
  FOUL RESILIENCE（原文均写「你的射击阶段**或**战斗阶段」）、Font of Spores /
  Bane-forged Weapons / Fulgurating Presence / The Endless Gift（原文无相位措辞）
  一律 `condition: []`。
- **携带者/光环限定必须挂开关**：11 条增强分别挂 `bearer_leading` /
  `defender_bearer_leading`，否则「仅携带者」或「光环 6" 内」的加成会对整单位无条件注入。
  反面：Bane-forged Weapons 原文是 UPGRADE「This unit's attacks」（整单位生效），**不挂**
  bearer 开关——测试有正反两条断言护住。

### not_modeled 的主因分布（96 条）

防高估不编，逐条带 `not_modeled_notes_zh`：

- **己方神祇关键词互斥分支**：First Prince of Chaos（MURDERER'S COWL / PENUMBRAL
  PUPPETRY / GLOAM ROT / SHADOW'S CARESS / DISCIPLES 五条按 Khorne/Tzeentch/Nurgle/
  Slaanesh/Undivided 分流）——引擎无「己方单位神祇关键词」门，裸编任一支会对其余三神
  过度施加（沿 PR17 Mission Tactics 三选一先例）
- **Flux token 经济**：Fates in Flux 军规级 token 收支 + Inescapable Eye + 5 条战略的
  token 强化支
- **区域态（Shadow of Chaos）**：CORRUPT REALSPACE / IMPOSSIBLE ECLIPSE /
  Melancholic Miasma / 各增强的「在 Shadow of Chaos 内改为 +2」分支
- **战栗检定（Battle-shock）**：ABJECT HORROR / PLAGUE OF WOES / SENSORY EXCRUCIATION /
  Cankerblight / Maggot Maws / Melancholic Miasma
- **仅重投「1」（非重投失败）**：DAEMONIC INVULNERABILITY、FATE SYPHONING
- **仅对特定伤害来源的 FNP**：Improbable Shield（仅灵能攻击与致命伤）
- **SET 非增量**：SHEATHED IN BRASS（Sv 设定 3+）、Endless Gift 登舰版与
  Swollen with Power（W 特征值 +2，引擎无 Wounds 通道）
- **远程 × S>T 无复合 tag**：Warptide 的 INCORPOREAL ENTITIES（沿 PR24 BUILT TO LAST
  先例——裸 `wound_s_gt_t` 会在近战误放行）
- **负关键词门**：Cankerblight（排除 MONSTERS/VEHICLES）
- **第三方几何门**：Living Flame（须目标在**友军**接战范围内才有 [SUSTAINED HITS 1]）
- **异单位授予 / 异单位减益**：THIEVES OF PAIN、Mutagenic Flames、Toxic Miasma、
  Spite Made Manifest（令敌方武器获 [HAZARDOUS]，攻击方自伤从守方侧无载体）
- **域外**：移动 / 冲锋骰 / surge move / ingress / 预备队 / 部署落点 / 据点与控制等级 /
  CP 经济 / 侦测范围 / 治疗与复活 / 致命伤池 / 出手顺序（Fights First）/
  摧毁后反打 / Deadly Demise / 绝望逃脱 / 舱门与战术机动（登舰行动专有）

## 验证

- `pytest tests/ -q` → **1487 passed, 0 failed**（含新增
  `tests/test_simulator_dsl_pr26_payload.py` 57 条：结构/DB 对账/11 版补丁落库断言/指纹
  + 攻守双向引擎级差分 + `TestHonestyBoundaries` 对 15 个高频过度建模陷阱的反向断言）
  - 前置清理：gitignored 的 `db/wh40k.sqlite` 跨分支共用，带进了并行 `genestealercults`
    分支的 **107 行孤儿投影**（94 行清投影列 + 13 行 `det*` 物化行整行删除），
    打红 `test_simulator_dsl_pr4_payload::test_projection_counts_match_payload`。
    沿既有纪律「清孤儿行而非改测试」处理，清完 0 孤儿。
- `python -m db_compile fp-rules` 二次运行全幂等：文本 117 / 中文名 291 / 失效标记 49 /
  插行 300，**让路 0、跳过 0、无效 0**
- `python -m db_compile dsl-apply`：applied 0 / already **2040**（1918 + 122），
  **fingerprint_mismatch 0、skipped 0**，三态 123 encoded / 438 partial / 1479 not_modeled
- 基准 `qa_bench.py --path agent`（gold v3，96 题），跑两次：
  - 首跑 `benchmarks/v3_edition11/qa_agent_results_p7pr26.json`：**94 correct / 2 partial /
    0 wrong，accuracy 97.9，零硬错**，⚠️ 落在 #42（兽人近战武器档）与 #86（深入打击完整规则）
  - 复核跑 `benchmarks/v3_edition11/qa_agent_results_p7pr26_recheck.json`：
    **95 / 1 / 0，accuracy 99.0，零硬错**，⚠️ 仅剩 #41（兽人小子），#86 恢复 ✅
  - 与紧邻的 PR22 基线（94/2/0、97.9、⚠️ 在 #41/#42）比：**总分持平或更好、零硬错不变**。
    #86 逐题复核确认为**检索侧波动非回归**：该题 8 个引用源里**零条混沌恶魔来源**
    （首跑抓到的是死灵/沃坦/钛/灰骑士页，PR22 抓到的是 Core Rules p80），
    答案正文也未提及 Warp Rifts；且 DSL/DB 补丁不进 FAISS 检索语料、本 PR 未跑 ingest、
    `local_vector_store/` 零改动 → 检索侧零影响，复核跑即恢复 ✅ 佐证之
- 自审（code-reviewer）：**0 CRITICAL / 0 HIGH / 0 MEDIUM，APPROVE**。1 LOW：
  4 个登舰行动分队的 5 条（含本 PR 唯一 encoded 的 INCORPOREAL TERRORS）源文不在
  git 跟踪的 FP 语料里（它们来自 Wahapedia 登舰行动补充，早于本 PR 已在库），
  建议人工核对 —— 已逐条从库 dump 复核：5 条原文与编码逐字对应，
  INCORPOREAL TERRORS 确为单从句 + 无神祇子关键词，`encoded` 判定成立。
