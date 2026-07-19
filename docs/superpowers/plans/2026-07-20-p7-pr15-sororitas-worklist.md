# P7-PR15 圣血修女（Adepta Sororitas）fp_rules 逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Adepta Sororitas/`（24 页，"first iteration …
all new"）vs `db/wh40k.sqlite`（faction='AS'）。体裁沿 PR1/PR4-PR14。

> **进度**：Part 1（DB 11 版对齐）已收官——1 text_patch + 14 inserts 落库、全库
> 1179 测试绿。Part 2（DSL 全量编码 sororitas.json）+ Part 3（基准）+ Part 4
> （自审）为后续迭代。

## FP 内容面

Faction Pack 目录（p.1）：Detachments（p.2-6）· Datasheets（p.7-12）· Rules
Updates（p.13-14）· Legends Datasheets（p.15-24）。

- **3 个全新分队**（inserts，各 1 规则 + N 增强 + M 战略）：
  - **Chorus of Condemnation**（规则 Angelic Judgement：ADEPTA SORORITAS INFANTRY
    FLY「Condemnatory Psalms」谴责+3"侦测 + 增强 Clarion of Urgency（跳跃军牧战略
    预备）/ Symphonic Payload Upgrade（EXORCIST 重骰武器 A）+ 战略 Inspirational
    Battle Canticles（解战栗）/ Harmonised Exorcism（EXORCIST +1 命中）/
    Devastating Reprise（[DEVASTATING WOUNDS]））
  - **Sacred Champions**（规则 Holy Quest：CELESTIAN SACRESANTS +1 BS/WS，REVEREND
    tag + 增强 Writ of Compunction（+1 OC）/ Perfervid Haste（+1" M）+ 战略
    Sanctified Blows（近战 +1 A/S）/ Faithful Fortitude（对致命伤 FNP 5+）/
    Unflinching Determination（[ASSAULT] + 前进/撤退不阻射击冲锋））
  - **Sanctified Orators**（规则 Hymns of Battle：增强不占额度 + CHARACTER +1 Ld +
    增强 Hagiomnifex Upgrade（每回合五选一，其中 Psalm of Righteous Smiting +1 S /
    Chorus of Repudiation 守方 S>T 致伤-1 有战斗链载体）；**无战略**）
  - A/B 已确认三分队规则名/战略名/增强名在库 0 命中（真全新）；synthetic id 前缀
    `fp11e-sororitas-`，cost 置空（FP 无点数，MFM 缓存无增强数据）
- **1 个重印分队 Champions of Faith**（p.5-6）：DB 已收录（det rule 000009830
  Righteous Purpose + 战略 000009832* + 增强 000009831*），逐字一致**免补**
- **Datasheets**（Intranzia Fraye / Sanctifiers / Celestian Insidiants + Legends
  Celestian Sacresant Aveline / Repressor / Battle Sanctum / Crusaders / Death Cult
  Assassins）——datasheet/单位层，非分队规则/战略/增强，**本 PR 未落**（观察项）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，1 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000009030007 Devout Fanaticism（Penitent Host） | drifted | Rules Updates p13：EFFECT 整改「Roll one D6 移动至最近敌」→ 11 版「Your unit can make a surge move of up to D6"」（surge move 术语化，同 PR5 吞世者）；WHEN 同、TARGET 不动（保留库现拼写 'as one or more'） |

### fp_new（inserts 14 条）

3 detachment rules + 5 enhancements + 6 stratagems，synthetic id `fp11e-sororitas-*`。

| 分队 | 规则（det id） | 增强 | 战略 |
|---|---|---|---|
| Chorus of Condemnation | Angelic Judgement（-chorus） | Clarion of Urgency / Symphonic Payload Upgrade | Inspirational Battle Canticles / Harmonised Exorcism / Devastating Reprise |
| Sacred Champions | Holy Quest（-sacred） | Writ of Compunction Upgrade / Perfervid Haste | Sanctified Blows / Faithful Fortitude / Unflinching Determination |
| Sanctified Orators | Hymns of Battle（-orators） | Hagiomnifex Upgrade | —（无战略） |

### 已滚入/已满足免补（identical）——Rules Updates p13-14 逐条核

- **军规 Acts of Faith · Gaining Miracle Dice**：DB abilities 000008466 现文已是
  「At the start of each battle round / Each time an AS unit destroyed」——已 11 版态
- **Bringers of Flame**：Shield of Aversion（AP 恶化，000009034002）、Rites of Fire
  （within 6"+据点 +1 Wound + 战栗，000009034006）、Blazing Ire 2CP（000009034007）、
  Cleansing Flames 2CP（000009034005）、Fervent Purgation 分队规则（[ASSAULT]+6"内
  +1 S，000009032）——**全部逐字一致免补**（Wahapedia 已滚入）
- **Hallowed Martyrs**：Suffering and Sacrifice（强制被指定为目标，000008469003）、
  Divine Intervention（弃 1-3 Miracle dice 复活，000008469002）——**免补**
- **Penitent Host**：Desperate for Redemption 分队规则首段（Vows of Atonement，
  000009028）——首段已一致**免补**（仅 Devout Fanaticism 战略漂移已补，见上）

### removed_11e：零

（FP 为 first iteration，无「完整重印裁定删除」的旧条目）

### 观察项（不落本 PR，datasheet/单位层，非 DSL 阻塞）

1. **datasheet 技能改 8 项**（Rules Updates p13-14）：Dialogus/Dogmata/Hospitaller/
   Imagifier Core「Leader→Support」、Daemonifuge Mysterious Saviours（-1CP 英勇介入）、
   Dominion Squad Righteous Awareness（8"内 D6" Normal move）、Immolator Transport
   分割段、Retributor Storm of Retribution、Triumph of Saint Katherine Solemn
   Procession、Zephyrim Embodied Prophecy（[SUSTAINED]/[LETHAL] 选一，冲锋二选）
   ——均 abilities 表逐单位技能层，RAG 相关但非分队 DSL，留后续
2. **FRAME 关键字 ×4**（Castigator/Exorcist/Immolator/Sororitas Rhino，p14）——
   keyword_patches 候选，但同 PR14 兽人 FRAME 约定「只删不加、无战斗链载体」记观察
3. **3 新 datasheet + 5 Legends 单位**（Intranzia Fraye/Sanctifiers/Celestian
   Insidiants/Aveline/Repressor/Battle Sanctum/Crusaders/Death Cult Assassins）——
   fp_errata new_units 候选（models/weapons/abilities 全套），单位层大任务，留后续

## DSL 编码盘面（sororitas.json）——Part 2 待编，规划

覆盖面 = faction='AS' 全部活跃：**10 分队规则物化 + 44 战略 + 29 增强**（含 14 inserts）。
圣血修女为信仰/奇迹骰驱动阵营，可编率**中低**——大量机制无战斗链载体（Miracle dice
生成/替换、Acts of Faith、Battle-shock、Vows of Atonement 动态、复活/据点/预备队/移动）。

**可走既有通道（预判 encoded/partial）**：
- 守方无效保护 invuln（The Emperor Protects 4++/条件 3++、Refrain of Enduring Faith
  5++、Crusaders 4++）
- 守方 FNP（Shield of Faith/Shield of Denial 对致命伤 6+/5+、Purity of Suffering 4+、
  Fervent Ferocity 4+、Faithful Fortitude 对致命伤 5+、Rituale Nullificatus 4+）
- 守方致伤-1 S>T（Contempt for Death、Chorus of Repudiation）
- 守方命中-1（Shield of Aversion→AP 恶化、Bastion of Faith/Final Testament/Spirit
  of the Martyr 命中-1）
- 近战 +A/+S/+AP/+D（Sanctified Blows、To the Heart of Heresy、Mark of Devotion、
  Through Suffering Strength、Blade of Saint Ellynor、Righteous Rage、Sacred Champions
  Holy Quest +1 WS/BS、Righteous Purpose +1 WS/BS）
- crit 5+（Passion of the Penitent 近战 crit 5+）
- [LETHAL HITS]/[SUSTAINED HITS 1]（Righteous Blows、Suffer Not the Unfaithful 二选一、
  Fire and Fury）、[LANCE]（Faith and Fury）、[DEVASTATING WOUNDS]（Cleansing Flames
  Torrent、Devastating Reprise）、[PRECISION]（Eyes of the Oracle、Blade of Saint Ellynor）
- [ASSAULT]（Fervent Purgation、Unflinching Determination——ASSAULT 无射程/移动增益载体
  则 not_modeled）、+1 命中（Harmonised Exorcism）
- Mantle of Ophelia（伤害改 1 = damage_cap）、Iron Surplice（Sv 2+ + FNP 5+）

**防高估宁漏不错不编（预判 not_modeled）**：
- Miracle dice 全链（生成/替换/弃换/重骰）——奇迹骰机制无载体
- Acts of Faith、Battle-shock 触发/自动成功、Vows of Atonement 动态选择、Righteous
  动态标记（Righteous 门控的 buff 按基础分量编 + 注记，同 Waaagh 状态范式）
- 复活/据点/预备队/移动/超冲锋（surge move）、CP 经济、侦测范围
- 负关键字门（excluding MONSTER/VEHICLE）无载体、[ASSAULT]/[TORRENT×DEV] 需武器筛选
- 阶段性 WHEN 门控严核（战斗阶段触发⇒仅剩近战须挂 phase_melee；射击 buff 挂
  phase_shooting；四次同型 HIGH 教训——顺 WHEN 推可生效阶段，成对写正负门控测试）
