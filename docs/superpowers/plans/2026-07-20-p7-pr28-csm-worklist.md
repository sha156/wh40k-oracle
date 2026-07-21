# P7-PR28 混沌星际战士 fp_rules 逐行 A/B 工作单 + DSL 编码盘面（2026-07-21）

对照源：`data_refined/Faction Pack Chaos Space Marines/`（102 页，FACTION PACK VERSION 1.0，
Legal from 2026-06-20，"first iteration — all of the following content should be regarded as new"）
vs `db/wh40k.sqlite`（`faction='CSM'`）。体裁沿 PR1/PR4–PR27。

## FP 内容面

| 页段 | 内容 |
|---|---|
| p1 | 目录页（声明 9 分队 / 10 兵牌 / Rules Updates / Legends） |
| p2 | **Cabal of Chaos 11 版完整重印**（Empyric Wellspring 改写 + 2 增强 + 3 战略）——库内仍十版旧文 |
| p3 | **全新分队 Devotees of Destruction**（Rain of Ruin：1 规则 + 2 增强 + 3 战略） |
| p4 | **全新分队 Murdertalon Raiders**（Prey on the Weak：1 规则 + 2 增强 + 3 战略，带 NIGHTMARE 互斥标签） |
| p5-p6 | Warpstrike Champions（Warp Portals + 4 增强 + 6 战略）——库内已有 |
| p7-p8 | Cult of the Arkifane（Soul Forge Boons + 4 增强 + 6 战略）——库内已有 |
| p9-p10 | Creations of Bile（Experimental Augmentations + 4 增强 + 6 战略）——库内已有，**p10 refine 截断** |
| p11-p12 | Nightmare Hunt（Terror Made Manifest + 4 增强 + 6 战略）——库内已有 |
| p13-p14 | Huron’s Marauders（Tyrannical Motivation + 4 增强 + 6 战略）——库内已有 |
| p15-p16 | Renegade Warband（Slaves to None / Vendetta / Twisted Doctrine + 4 增强 + 6 战略）——库内已有 |
| p17-p36 | 新兵牌 10 张：Kravek Morne / Mutilators / Defiler / Huron Blackheart / Masters of the Maelstrom / Red Corsairs Raiders / Red Corsairs Reave-Captain / Nemesis Claw / Raptors / Warp Talons |
| p37-p38 | **Rules Updates**（8 个分队条目改写 + 一批兵牌勘误） |
| p39 | FAQs（3 条裁定说明，零规则文本改动） |
| p40-p102 | **Legends 兵牌 32 张** + Legends 单位选项页 |

库内 `faction='CSM'` 共 **18 个分队容器**（Pactbound Zealots / Veterans of the Long War /
Deceptors / Renegade Raiders / Dread Talons / Fellhammer Siege-host / Chaos Cult /
Soulforged Warpack / Creations of Bile / Cabal of Chaos / Nightmare Hunt / Huron’s Marauders /
Renegade Warband / Warpstrike Champions / Cult of the Arkifane 十五个正式分队 +
Infernal Reavers / Underdeck Uprising / Champions of Chaos 三个**登舰行动（Boarding Actions）分队**）。
登舰行动分队是独立游戏模式、不在 FP 范围内，**不作 removed_11e**，但纳入 DSL 编码盘面
（沿 tau / orks / imperialagents / chaosdaemons / admech 先例）。

### 分队规则行 → 分队容器的映射（21 行 → 18 分队）

`detachments` 表存的是**规则名**（不是分队名），需按 id 邻接推定归属：
库内体例是 `规则行 = 增强前缀 - 1`、`增强前缀 = 战略前缀 - 1`。
三个分队规则行数 > 1：**Chaos Cult**（Desperate Devotion + KEYWORDS）、
**Renegade Warband**（Slaves to None + Vendetta + Twisted Doctrine）；
唯一不合邻接体例的 `000008362 Marks of Chaos` 由排除法归到 **Pactbound Zealots**（Codex 原书一致）。

> **payload 的 `detachment` 字段一律填「分队容器名」**（不是规则名、也不留 null）。
> 全库 22 个 payload 里 13 个用容器名、6 个用规则名、3 个用 null——只有容器名能让
> `select_entries` 正确按所选分队过滤，本 PR 取正确口径并加了
> `test_detachment_field_matches_container_names` 常驻守卫。

### refine 截断逐条回原 PDF 复核

`page_010.md` 在 `## DIABOLIC REGENERATION` 标题处**硬截断**——Creations of Bile 第 5 战略正文
与第 6 战略（AUTOSTIMULANTS）全部丢失。回原 PDF（`data/Faction Pack Chaos Space Marines.pdf`
第 10 页，PyMuPDF `get_text("text")`）逐字取全：两条战略正文与库内**逐字一致** ⇒ 免补。

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，13 条）

| 表 | id | 名称 | 判定 |
|---|---|---|---|
| detachments | 000010150 | Empyric Wellspring | 整替：十版「每次 Dark Pact 后在 Leaping Warpflame / Monstrous Manifestation **二选一**（各带 9" 邻接门）」⇒ 11 版「射击阶段 PSYKER 发动 Dark Pact ⇒ 远程 **+1 S**；战斗阶段 DAEMON PRINCE 发动 Dark Pact ⇒ 近战 **+2 S / +1 AP**」（FP p2） |
| detachments | 000008362 | Marks of Chaos | Restrictions 第 2 条 `A Character unit` ⇒ `A CHARACTER/EPIC HERO unit`（FP p37）；同页 TRANSPORT 条库内已有 ⇒ 免补 |
| enhancements | 000010151002 | Touched by the Warp | 整替：十版「获得 Psyker 关键词」⇒ 11 版「本模型有 PSYKER **且武器获 [PSYCHIC]**」（FP p2） |
| enhancements | 000008964003 | Falsehood | 第三句删「in the Reinforcements step of」（FP p37） |
| stratagems | 000010740007 | PORTAL OF SPITE | EFFECT 整替：十版「若最近合法敌军单位是冲锋目标之一则 +2 冲锋骰」⇒ 11 版「**无条件** +2 to charge rolls」（FP p6） |
| stratagems | 000010689006 | TO THE FAVOURED THE SPOILS | EFFECT 整替为 11 版核心术语 `surge move of up to D6"`（FP p14） |
| stratagems | 000008965006 | RELENTLESS PURSUIT | TARGET 触发距离 **9" → 8"**（FP p37） |
| stratagems | 000008973006 | SCREAMING DESCENT | `must take a Battle-shock test` ⇒ `makes a battle-shock roll`（FP p37） |
| stratagems | 000008986005 | UNSTOPPABLE RAMPAGE | TARGET 收窄：`HERETIC ASTARTES VEHICLE` ⇒ `HERETIC ASTARTES **DAEMON** VEHICLE`（FP p37） |
| stratagems | 000008986006 | PREDATORY PURSUIT | 两处：TARGET 同上收窄 + 距离 **9" → 8"**（FP p37） |
| stratagems | 000008961004 | BRINGERS OF DESPAIR | WHEN `Start of the Fight phase` ⇒ `Fight phase.`（FP p37） |
| stratagems | 000008961004 | BRINGERS OF DESPAIR | `cp_cost` **2 → 1**（FP p37 明文 `CP Cost: change to '1CP'`） |
| stratagems | 000008961007 | MILLENNIA OF EXPERIENCE | TARGET 触发距离 **9" → 8"**（FP p37） |

### 真漂移已补（fp_errata，1 stat + 1 keyword）

| 类型 | 单位 | 字段 | 判定 |
|---|---|---|---|
| stat | Heldrake（CSM 版 000000961） | m | `20+"` → `12"`（FP p37）——**OC 0→'-' 不补**（功能等价且库无 `'-'` OC 先例，防下游 int 解析破坏，同 WE/EC/TS 三版 Heldrake 处理） |
| keyword | Heldrake（CSM 版 000000961） | keywords | remove `Aircraft`（FP p37） |

> CSM 版 Heldrake 是 S4 的 25 条飞机移动补丁与 PR5 关键词补丁的**漏网**（WE/EC/TS 三个
> 阵营的同名兵牌当时都补了，CSM 的没补）——逐阵营 FP 扫一遍才逮到。

### 假警报 / 让路（不落补丁）

| 项 | 裁决 |
|---|---|
| **UNHOLY FORTITUDE 疑似 1CP → 2CP** | **不补**：`page_008.md` 的 refine 把该行标成 `(2CP)`，但 PDF p8 的 CP 是**浮动文本框**（页尾一串 `1CP 1CP 1CP 1CP 1CP 2CP`），顺序不跟正文走。全页只有一个 2CP，而库内 `SOUL-TALLY OFFERING` 已是 2CP、`UNHOLY FORTITUDE` 是 1CP——归位后自洽，判定 refine 标错行。已加常驻守卫 `test_unholy_fortitude_cp_not_touched` |
| Chaos Land Raider / Predator ×2 / Rhino / Vindicator / Khorne Lord of Skulls / Noctilith Crown 加 `FRAME` 关键词 | **不补**：`keyword_patches` 层策略明定「主列表只删不加」（新增关键词属重印整表体裁，走 new_units / 上游滚更） |
| Master of Executions `Remove 'Leader' add 'Support'` | **不补**：核心技能层，库 `abilities` 表只存兵牌特有技能，无核心技能行可补 |
| FAQ（p39，3 条） | 纯裁定说明，零规则文本改动 ⇒ 零 text_patch |

### 已滚入 / 已满足免补（identical）

- **Chaos Cult KEYWORDS（000008980）/ Warped Foresight（000008981005）/ UNFAILINGLY
  OBDURATE（000008969002）/ CONTEMPTUOUS DISREGARD（000008961003）/ Eager for
  Vengeance（000008960002）**：FP p37 的 change-to 与库现文本**逐字一致** ⇒ 免补
- **FEEDING FRENZY（000008986007）**：FP p37 的 TARGET change-to 与库现文本一致 ⇒ 免补
- **Warpstrike Champions / Cult of the Arkifane / Creations of Bile / Nightmare Hunt /
  Huron’s Marauders / Renegade Warband 六个分队**：除上表条目外逐条重印一致 ⇒ 免补
- **Lord Discordant on Helstalker**（M 14" / 特殊保护 4+ / Impaler chainglaive A5 WS2+ S8 AP-3 D3）、
  **Vashtorr’s hammer 双档**、**Chaos Predator Destructor Armoured tracks WS 4+**：
  库现值已等于 FP change-to（Wahapedia 已滚入 6 月勘误）⇒ 免补

### 重印未收录（deactivations，9 条）

FP p2 的 Cabal of Chaos 是**完整重印**（分队规则 + 2 增强 + 3 战略），库内仍是十版
4 增强 + 6 战略。差集按 PR4/PR22 既有裁定标 `removed_11e`（原文保留、不进 payload）：

| 表 | id | 名称 |
|---|---|---|
| enhancements | 000010151003 / 000010151004 / 000010151005 | Eyes of Z’desh / Mind Blade / Infernal Avatar |
| stratagems | 000010152002 / 000010152003 / 000010152004 | BALEFUL BLESSING / NO REST IN DEATH / MUTATION’S CURSE |
| stratagems | 000010152005 / 000010152006 / 000010152007 | SOULSEEKERS / UNHOLY HASTE / SHROUD OF CHAOS |

> 判据：11 版三条战略（INFERNAL VIGOUR / FLESHY CURSE / WREATHED IN WARPFLAME）与旧三条
> （NO REST IN DEATH / MUTATION’S CURSE / SOULSEEKERS）**名称与正文双双不同**——按整体替换
> 处理（删旧 + 插新），不做「同一条改名」的合并。

### 补录插行（fp_rules inserts，16 条，id 前缀 `fp11e-csm-`，cost 置空）

| 分队 | 规则 | 增强 | 战略 |
|---|---|---|---|
| Cabal of Chaos（p2，重印新增） | —（规则走 text_patch） | `-cabal-e1`（Conduit of Chaos） | `-cabal-s1/s2/s3` |
| Devotees of Destruction（p3，重火力系） | `-devotees`（Rain of Ruin） | `-devotees-e1/e2` | `-devotees-s1/s2/s3` |
| Murdertalon Raiders（p4，跳跃背包系） | `-murdertalon`（Prey on the Weak） | `-murdertalon-e1/e2` | `-murdertalon-s1/s2/s3` |

- A/B 已确认 2 个分队规则名 + 5 增强名 + 9 战略名在库内**同组 0 命中**，不需 `expect_duplicate_name`
  旗标。⚠️ 两处**跨组同名**（`UNDYING HATRED` 已存在于 Renegade Warband；`Prey on the Weak`
  已存在于 Nightmare Hunt 战略层）——插行守卫按 `(name, 分组列)` 判重，跨分队/跨表同名不触发，
  已实测应用 16/16 零让路
- `detachments.name_en` 按库内体例存**规则名**，分队名进 `stratagems.detachment` /
  `enhancements.detachment_name`

**观察项（不落库，datasheet / RAG 层，非 DSL 阻塞，留后续）**：
① FP p17-p36 的 10 张新/重印兵牌（Kravek Morne 等）；② p40-p102 的 32 张 Legends 兵牌与
Legends 单位选项；③ p38 的兵牌技能层改写（Abaddon Dark Destiny / Accursed Cultists Howling
Horde surge / Cypher / Fabius Bile Chirurgeon / Daemon Prince Lord of Chaos / Obliterators
Warp Rift Firepower / Warp Talons Warp Strike / Traitor Guardsmen Twisted Defence Force /
Chaos Rhino·Land Raider Transport 段 / Chaos Rhino Wargear 段），本 PR 只做分队层，兵牌技能层
留待专项；④ FRAME / Support 等核心技能层缺列。

## DSL 编码盘面（`dsl_payloads/csm.json`）

**覆盖面**：1 条军规 + 20 个分队容器 = **24 条 abilities（军规 1 + 分队规则 23）+ 105 战略
+ 68 增强 = 197 条**（库内 1 + 21 + 96 + 63 = 181 行，加 fp_new 2 + 9 + 5 = 16 行）。
9 条 `removed_11e` 行按既有约定**不进 payload**（全库 6 个阵营的 58 条 removed_11e 无一进 payload）。

**三态：19 encoded / 44 partial / 134 not_modeled**。零新引擎通道、零新态势开关（纯编码 PR），
只复用既有的 `bearer_leading` / `defender_bearer_leading` / `disembarked_this_turn` /
`advanced_or_fell_back` 四个假设开关。

### 可编率为何偏低：阵营气质

混沌星际战士是「**黑暗契约状态机 + 士气恐惧 + 移动资格**」气质阵营。四类主干机制全无引擎载体：

1. **黑暗契约（军规）+ 混沌之印**：每次攻击可发动契约，成功后在 [LETHAL HITS] /
   [SUSTAINED HITS 1] **二选一**，再按军队组建时选的**五神印之一**触发不同暴击分档——
   两重状态门叠加。连带 10+ 条条目（Marks of Chaos / TOUCH OF THE ARKIFANE /
   Voice of the Octed / Eye of Tzeentch / NEVER OUTGUNNED 等）一并 not_modeled。
   另有 **Desperate Pact**（Chaos Cult 系）与 **契约调用**（Soulforged 系）两套并行状态机。
2. **Battle-shock 士气链**：Terror Descends / Terror Made Manifest / Dread Talons 与
   Nightmare Hunt 两整套分队的核心门控都是「敌军是否士气崩溃」——引擎无士气状态。
3. **移动资格域**：「加速后可射击/冲锋」「撤退后可射击/冲锋」「surge / Rush / Normal move」
   在 105 条战略里出现 30+ 次，全部无载体（Twisted Doctrine 的 Default to Doctrine 亦然）。
4. **目标点经济与几何**：Raiders and Reavers / RUINOUS RAID / Ironbound Enmity /
   INFERNAL ALTARS / RENEGADE CLAIM / WARP-TAINTED——引擎无目标点。

### encoded（19 条）

| 表 | id | 名称 | 通道 |
|---|---|---|---|
| stratagems | fp11e-csm-cabal-s3 | WREATHED IN WARPFLAME | save/ignores_cover · `phase_shooting` |
| stratagems | 000009774002 | MONSTROUS VISAGES | hit/modify -1（守方）· 无门（两相位） |
| stratagems | 000010744003 | BALEFIRE BOON | save/ap_improve +1 · 无门（两相位） |
| stratagems | 000010744007 | UNHOLY FORTITUDE | wound/t_improve +1（守方）· `phase_shooting` |
| stratagems | 000008977006 | STEADFAST DETERMINATION | fnp/fnp 5（守方）· `phase_shooting` |
| stratagems | 000010689005 | REAVERS’ FLURRY | attacks/modify +1 · **`melee_charging`** |
| stratagems | 000009504002 | INVETERATE MURDERERS | wound/modify +1 · **`melee_s_lte_t`** |
| stratagems | 000009504003 | LOW CUNNING | wound/modify -1（守方）· **`wound_s_gt_t`** |
| stratagems | 000008358004 | PROFANE ZEAL | wound/reroll fail · 无门（两相位） |
| stratagems | 000008969002 | UNFAILINGLY OBDURATE | save/ap_improve -1（守方）· 无门（两相位） |
| stratagems | 000010695006 | CORRUPTED MUNITIONS | save/ap_improve +1 · `phase_shooting` |
| stratagems | 000008961003 | CONTEMPTUOUS DISREGARD | save/ap_improve -1（守方）· 无门（两相位） |
| stratagems | 000010740002 | EMPYRIC DISLOCATION | save/ap_improve -1（守方）· 无门（两相位） |
| stratagems | 000010740003 | ARMOUR OF CORRUPTION | damage/damage_reduction 1（守方）· **`phase_melee`** |
| stratagems | 000010740006 | SIEGEBREAKER STRIKE | save/ignores_cover · `phase_shooting` |
| stratagems | fp11e-csm-murdertalon-s1 | PLUNGING TALONS | wound/modify +1（[LANCE]）· **`melee_charging`** |
| enhancements | 000008972003 | Night’s Shroud | save/cover（守方）· `phase_shooting` + `defender_bearer_leading` |
| enhancements | 000010694003 | Eyes of the Hunter | save/ignores_cover · `phase_shooting` + `bearer_leading` |
| enhancements | fp11e-csm-murdertalon-e1 | Shadowcowl Talisman | save/invuln 5（守方）· `defender_bearer_leading` |

### partial（44 条，残量已逐条写进 `not_modeled_notes_zh`）——重点条目

| 表 | id | 名称 | 已编 | 残量 |
|---|---|---|---|---|
| abilities | det000008959 | Focus of Hatred | hit/reroll fail | 仇恨焦点是每指挥阶段点名的单一敌军单位（按恒满足处理，高估）；排除 DAMNED 的攻方自关键词门 |
| abilities | det000008967 | Raiders and Reavers | save/ap_improve +1 | 目标点几何（高估）；[ASSAULT] |
| abilities | det000008984 | Debt to the Soul Forge | wound/modify +1 · `phase_shooting`；attacks/modify +2 · `phase_melee` | DAEMON VEHICLE 自关键词门；契约可选 + Ld -1 + 失败致命伤 |
| abilities | det000010150 | Empyric Wellspring | s_improve +1 · `phase_shooting`；s_improve +2 与 ap_improve +1 · `phase_melee` | 两从句各自的攻方自关键词门（PSYKER / DAEMON PRINCE）会同时注入（高估）；Dark Pact 状态 |
| abilities | det000010640 | Terror Made Manifest | hit/modify +1 · `target_below_half` | 其余 3 条从句全依赖士气状态 |
| abilities | det000010692 | Vendetta | hit/reroll fail | 同 Focus of Hatred |
| abilities | det000010742 | Soul Forge Boons | save/invuln 5（守方） | 两条关键词授予；5+ 只给 SOUL FORGE（守方自关键词门） |
| abilities | detfp11e-csm-devotees | Rain of Ruin | hit/modify +1 · **`stationary`**（[HEAVY]） | HAVOCS/OBLITERATORS 自关键词门；`stationary` tag 不含相位门，近战开驻停会误放行 |
| stratagems | 000010642002/3 | TALONS SUNK DEEP / PREY ON THE WEAK | ap_improve +1 / hit/reroll fail · `target_below_half` | 原文是「士气崩溃 **和/或** 低于半编」——士气分量无载体（**保守欠建模**方向） |
| stratagems | 000009774004 | SPECIMENS FOR THE SPIDER | wound/reroll fail · **`melee_target_has_keyword(character)`** | 战后士气检定串 |
| stratagems | 000009513003 | FLEETING MIGHT | wound/mortal_pool（[DEVASTATING WOUNDS]） | Dark Pact 触发状态 |
| stratagems | 000008961006 | LET THE GALAXY BURN | save/ignores_cover · `phase_shooting` | Torrent 攻击数**置 6**（特征值 SET 无通道） |
| enhancements | 000008976003 | Iron Artifice | wound/crit_threshold 4 · **`target_has_keyword(vehicle)`** | [ANTI-FORTIFICATION 4+] 分支；仅携带者 |
| enhancements | 000010739005 | Tzagulla | attacks +1 / s_improve +1 / ap_improve +1 | 仅携带者；预备队入场当回合 +1 伤害分档 |

### 阶段门纪律（双向核对）

- **WHEN 落在单一相位** ⇒ 挂 `phase_shooting` / `phase_melee`（13 + 8 条，见测试
  `TestPhaseGating.SHOOTING_ONLY` / `MELEE_ONLY`）
- **WHEN 写「射击阶段**或**近战阶段」/「每次攻击」** ⇒ **一律不加门**（24 条，见 `BOTH_PHASES`）。
  过度加门＝欠建模，同属事实错误——反方向也写了守卫断言
- **阶段性 WHEN 顺 WHEN 往后推**：`ARMOUR OF CORRUPTION` 的 WHEN=战斗阶段、持续「到回合结束」——
  战斗是回合**最后一个**攻击阶段，故本回合仍只有近战可受益 ⇒ `phase_melee`
- **[LANCE] 用复合 tag**：`PLUNGING TALONS` / `Conduit of Chaos` / `REAVERS’ FLURRY`
  必须 `melee_charging`，裸 `charging` 会在射击阶段误放行（PR5 先例）
- **同一分队规则的两条从句各挂各的门**：`Empyric Wellspring` 第一从句 `phase_shooting`、
  第二从句 `phase_melee`，测试 `test_empyric_wellspring_two_clause_gates` 逐组断言

### 防高估清单（明确不编，均有常驻守卫）

- **单一相位 × 目标战损/士气档无复合 tag**（PICK THEM OFF / PITILESS CANNONADE /
  DEPTHLESS CRUELTY / PITILESS HUNTERS）——裸挂战损 tag 会在另一相位误放行，只挂相位门
  又丢掉战损前提，**两个方向都错** ⇒ 整条 not_modeled（`test_single_phase_times_target_state_not_encoded`）
- **射击 × S>T 无复合 tag**（Iron Fortitude / UNDYING HATRED(Devotees)）——引擎只有
  `wound_s_gt_t`（无相位门）与 `melee_wound_s_gt_t`（近战向）⇒ not_modeled
- **「三关键词任一」析取**（SOUL-TALLY OFFERING：CHARACTER/MONSTER/VEHICLE）⇒ not_modeled
- **重掷特定点数「1」**（Marks of Chaos 的 CHAOS UNDIVIDED 支 / Prey on the Weak 分队规则）
  与**单骰单次重掷**（Mark of Legend）——引擎 reroll 只有「重掷全部失败骰」语义
- **多选一单分支**（黑暗契约 / 神印五选一 / 实验性增体六选一 / 暴君的鞭策二选一 /
  HARDENED KILLERS 三选一 / NEVER OUTGUNNED 二选一）
- **攻方自身战损档**（PERSISTENT ASSAILANTS 第二段 / Incendiary Goad；引擎 `target_below_*` 是目标侧）
- **按武器名清单过滤**（BLACK CRUSADE 的 bolt pistol/boltgun/combi-bolter；`weapon_filter` 只认单个子串）
- **特征值 SET**（Torrent A=6 / Bastion Plate 伤害置 0）
- **方向错位**（Warp Tracer：受益者是「携带者射击**之后**」的其他攻击方；Dark Majesty：
  减益作用在敌方攻击我方的方向上）
- 复活 / 出手顺序（Fights First）/ 单次触发 / CP / 士气 / 移动 / 冲锋 / 预备队 /
  外部致命伤池 / 关键词授予 / 可见性 / 舱门 / 治疗 / 侦测范围。

### 光环型增强的开关口径

`bearer_leading` 的语义是「携带者正**率领本单位**」。受益者是**范围内另一友军单位**的
三条光环增强（Forge’s Blessing 12" / Tempting Addendum 3" / Rabble Rouser 6"）**不挂**
bearer 开关，改在注记里披露「引擎按当前单位即受益单位处理（高估）」——挂 bearer 会把语义写反。
反方向守卫 `test_aura_entries_have_no_bearer_toggle`。

## 验证

| 项 | 结果 |
|---|---|
| `python -m db_compile fp-rules` | 文本应用 13 / 幂等 124 / 让路 0；失效标记应用 9 / 幂等 49 / 让路 0；插行应用 16 / 幂等 318 / 让路 0 |
| `python -m db_compile fp-errata` | 属性应用 1 / 关键词应用 1 / 让路 0 / 跳过 0 |
| `python -m db_compile dsl-apply` | 全库 **2354** 条投影（158 encoded / 500 partial / 1696 not_modeled），指纹让路 0 / 跳过 0 |
| payload ↔ DB 对账 | 197 / 197，漏编 0 / 多编 0（`TestDbReconciliation` 四条常驻） |
| `python -m pytest tests/ -q` | **1605 passed**（新增 `tests/test_simulator_dsl_pr28_payload.py` 53 条） |
| gold v3 基准 | **100.0，hard error = 0**（96 correct / 0 partial / 0 wrong；`benchmarks/v3_edition11/qa_agent_results_p7pr28.json`） |

### 基准逐题对账（vs 紧邻基线 PR27 recheck = 99.0）

唯一 verdict 变动：**#41 ⚠️ → ✅**——正是记忆中的固定波动题名单（#41/#42/#63/#86）成员，
方向是**变好**。`degraded_count` 两次均为 34（结构性特征，未漂）。本 PR 是纯编码 PR，
**DSL / DB 补丁不进 FAISS 检索语料**（未 ingest ⇒ 检索侧零影响），零 wrong 亦与基线一致。

## 自审（code-reviewer 子代理）

| 级别 | 数量 | 处理 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 0 | — |
| LOW | 0 | — |

子代理逐条复核了：① 24 条「两相位不加门」条目的 WHEN 原文（双向核对）；
② 「目标点范围内」从句的全 payload 横扫（4 处判法一致，均 partial + 高估注记）；
③ 9 条 deactivations 无一泄漏进 payload；④ 13 条 text_patch / 16 条 insert 与 FP 页逐字对照；
⑤ 计数断言与真源一致。另独立发现并确认 `Empyric Wellspring` 的 `+2 S` 分量只在 FP p2 有源
（Wahapedia CSV 镜像仍是十版），系 text_patch 先落库后编码的正确顺序产物。

## 复用教训

1. **refine 的「浮动 CP 标签」不可信**：PDF 里战略的 CP 是独立文本框，`get_text` 按几何顺序
   吐在页尾（`1CP 1CP 1CP 1CP 1CP 2CP`），refine 会按正文顺序**逐条配对**而错位。
   凡 FP 页的 CP 与库内不符，先数「整页有几个非 1CP」再与库内已有的非 1CP 行比对，
   自洽就判 refine 标错、不要补。本 PR 因此避免了一条假补丁（UNHOLY FORTITUDE）。
2. **`detachments` 表存的是规则名不是分队名**：映射靠 `规则 → 增强 → 战略` 的 id 邻接体例
   （N, N+1, N+2），多规则分队（Chaos Cult 2 条、Renegade Warband 3 条）与不合体例的孤例
   （Marks of Chaos）用排除法 + Codex 常识收口。全库 22 个 payload 对 `detachment` 字段
   有三种口径（容器名 13 / 规则名 6 / null 3），**只有容器名能让 `select_entries` 正确过滤**。
3. **同名兵牌的勘误要逐阵营扫**：Heldrake 在 WE/EC/TS 三个阵营都补过 M 与 AIRCRAFT，
   CSM 版（000000961）却是漏网——`fp_errata_patches.json` 里按 `unit` 名 grep 一遍
   就能发现同名不同 id 的缺口。
4. **11 版掩体在命中侧不在保存侧**（13.08：恶化 BS 1 点，射击专属）——写 Stealth /
   [IGNORES COVER] 的行为测试时要断言 `hits/attacks` 而不是 `unsaved/wounds`，
   否则测试会以「掩体没生效」的假象失败。本 PR 有 4 条测试因此改写。
5. **一个分队规则行可能含多条互斥从句**（Empyric Wellspring 的 PSYKER 支与 DAEMON PRINCE 支）：
   两支各自的相位门不同，必须**逐从句挂门**并在注记里明说「两支会同时注入到同一攻方」——
   只挂一个门或合并成一条都会错。
