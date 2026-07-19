# P7-PR13 死灵 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Necrons/`（56 页，Legal from 2026-06-20，
"first iteration … all new"）vs `db/wh40k.sqlite`（faction='NEC'）。体裁沿 PR1/PR4-PR12。
注：Phaeron's Armoury 战略页（Particle Pulse/Cosmic Storm）refine 截断，已从
`data/Faction Pack Necrons.pdf` 原 PDF 第 4 页恢复全文。

## FP 内容面

- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Hand of the Dynasty**（规则 Hypermotility Protocols：IMMORTALS/WARRIORS 远程
    [ASSAULT] + advance→action + 增强 Enlivened Sentinels（Scouts 5"）/Tools of
    Dominion（IMMORTALS 远程 [RAPID FIRE 1]）+ 战略 Dominance Protocols（+1 OC）/
    Will of the Conqueror（据守）/Nanosaturation（snap 射击））
  - **Skyshroud Spearhead**（规则 Transdimensional Deployment：TOMB BLADES Deep Strike
    + ingress→+1 命中 + 增强 Recursive Reanimation（+1 重生）/Deepening Madness
    （DESTROYER CULT MOUNTED 远程 [ASSAULT]）+ 战略 Omnilocked Strafing（撤退射击）/
    Swift as Death（移动）/Evasive Protocols（S>T -1 致伤））
  - **The Phaeron's Armoury**（规则 Empowered Engines：TITANIC FLY +6"M + 增强
    Prelocational Optimiser（Monolith 传送后 [LETHAL]/[SUSTAINED]）/Mortality Shroud
    （战意光环）+ 战略 Subsurface Quantumweave（-1 AP 守方）/Particle Pulse（侦测）/
    Cosmic Storm（OBELISK/TESSERACT Tesla Sphere +1 AP））
  - A/B 已确认三者规则名/战略名在库**全 0 命中**（真全新）
- **4 个重印分队**：Starshatter Arsenal（Relentless Onslaught 000009748）、Cryptek
  Conclave、Cursed Legion、Pantheon of Woe——DB 已收录、逐字一致**免补**
- **Datasheets**（8 单位：Canoptek Macrocytes/Tomb Crawlers/Geomancer/4 C'tan/Nekrosor
  Ammentar）——**均已在库**（Wahapedia 已滚入），reprint stat blocks 免补
- **Rules Updates**（p29-30）+ Imperial Armour/Legends Datasheets（reprint 免补）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，4 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000008547005 Reactive Subroutines（Canoptek Court） | drifted | TARGET `within 9"` → **`8"`** |
| abilities 000000552_a1 Eternity Gate（Monolith） | drifted | 整改：旧「Reinforcements step·6"内·不可冲锋」→ **「movement phase（除首轮）·ingress move·6"内·不可冲锋」**（加除首轮 + ingress） |
| abilities 000002358_a2 Tunnelling Horrors（Ophydian Destroyers） | drifted | 出场距离 `9"` → **`8"`** |
| abilities 000000555_a1 Transdimensional Displacement（Transcendent C'tan） | drifted | 出场距离 `9"` → **`8"`** |

### datasheet 数值/关键字漂移（fp_errata，3 条）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000000545 Doom Scythe（m） | drifted | **M `20+"` → `'-'`**（去 Hover 后无 Normal move；OC 免改已 '0'） |
| models 000000544 Night Scythe（m） | drifted | **M `20+"` → `14"`**（改悬停载具） |
| units 000000544 Night Scythe（keyword remove） | drifted | 删 **AIRCRAFT** 关键字 |

**观察项（不落库）**：① FRAME 关键字 ×10（Annihilation Barge/Catacomb Command Barge/
Convergence of Dominion/Ghost Ark/Monolith/Night Scythe/Obelisk/Tesseract Vault/
Triarch Stalker/Seraptek）——keyword_patch 机制只删不加主关键字；② Night Scythe 加 Hover
（CORE 能力无 schema 载体，同 PR11 Deep Strike）；③ Silent King 关键字重组（复杂结构改
不落）；④ 6 Cryptek（Chronomancer/Geomancer/Orikan/Plasmancer/Psychomancer/Technomancer）
Core 去 Leader 加 Support——ability 关键字层，非 stat/text，记观察项；⑤ Night Scythe
Invasion Beams 追加句、Silent King Relentless March 微差（DB 已改名 + 有 excluding
Monster）——datasheet ability 层次要，暂记观察项。

### 已滚入/已满足免补（identical）

- **Rules Updates 文本**：Annihilation Protocol 规则（DESTROYER CULT 近敌 +1 AP 段已在）、
  Worthy Foes 规则、Hyperphasing 战斗规模表、Cosmic Precision 战略 TARGET、Territorial
  Obsession 战略 TARGET、Cynosure of Eradication 战略 EFFECT、Living Lightning（Plasmancer
  18"/4D6/4+）——均已 11 版态一致
- **4 重印分队全套** + **8 新 datasheet 单位**（已在库）+ Imperial Armour/Legends
  datasheets——逐字一致 / reprint 免补

### removed_11e：零

### fp_new（inserts 18 条）

3 rules + 6 enhancements + 9 stratagems，synthetic id `fp11e-nec-*`。点数 `cost` 置空。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Hand of the Dynasty | fp11e-nec-hand | Hypermotility Protocols | Enlivened Sentinels / Tools of Dominion | Dominance Protocols / Will of the Conqueror / Nanosaturation |
| Skyshroud Spearhead | fp11e-nec-skyshroud | Transdimensional Deployment | Recursive Reanimation / Deepening Madness | Omnilocked Strafing / Swift as Death / Evasive Protocols |
| The Phaeron's Armoury | fp11e-nec-phaeron | Empowered Engines | Prelocational Optimiser / Mortality Shroud | Subsurface Quantumweave / Particle Pulse / Cosmic Storm |

## DSL 编码盘面（necrons.json）

145 项（16 分队规则 + 79 战略 + 50 增强，含 inserts）全量逐条编码。死灵为机械/重生/
高斯武器阵营，可编率中高：远程 [ASSAULT]（Hypermotility/Deepening Madness——射击资格类
不建模，但 [RAPID FIRE]/[LETHAL/SUSTAINED/DEV/IGNORES COVER] 可编）、守方 S>T 被伤-1
（Evasive Protocols 走 wound_s_gt_t）、守方 -1 AP（Subsurface Quantumweave 走 ap_improve）、
减伤（Chrono-impedance Fields）、Tesla Sphere +1 AP（weapon_filter）。防高估：重生协议
（Reanimation Protocols 全阵营核心机制无载体）、重骰1（Dread Majesty）、Power Matrix/
Command Protocols 区域态、ingress/深入/移动/据点/战意类、[ASSAULT] 射击资格非伤害增益。
