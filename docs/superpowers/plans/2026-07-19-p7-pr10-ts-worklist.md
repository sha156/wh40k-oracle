# P7-PR10 千子 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Thousand Sons/`（11 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态，faction='TS'）。体裁沿 PR1/PR4-PR9 裁定：
**FP 完整重印即整体替换**（未收录旧条目标 removed_11e）；change-list 外科应用；
fp_new 走 inserts 补录（fp11e-ts-* synthetic id）。

## FP 内容面

- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Ritual of Regeneration**（规则 Sorcerous Invigoration + 增强 Eruption of Vitality /
    Curse of Life + 战略 Relentless Rebirth / Mutagenic Magicks / Multitudinous Limbs）
  - **Sekhetar Cohort**（规则 Ensorcelled Animus + 增强 Walking Rampart / Occulus Infernum
    + 战略 Arcane Venting / Ectoplasmic Extrusion / Warp Fields）
  - **Servants of Change**（规则 All-Seeing Mutant Hordes + 增强 Unravelled Fates /
    Thicket of Bladed Bone + 战略 Prismatic Displacement / Temporal Instability /
    The Land Writhes）
  - A/B 已确认三者规则名/战略名在库**全 0 命中**（真全新，非上游补录双胞胎）
- **Hexwarp Thrallband**（重印，规则 Flow of Magic + 4 增强 + 6 战略）——DB 已收录
  （detachments 000009740 + enhancements 000009741002-005 + Hexwarp 战略 ×6），
  逐字一致零漂移**免补**
- **Defiler 兵牌**（重印，p7-8）——已在库；Destroyer of Futures 技能逐字一致；
  profile/武器已滚入。（OCR 记录见末尾）
- **Rules Updates**（p9-10）：军队规则 3 仪式 + 4 既有分队外科改 + 14 类兵牌 + FAQ 7 条

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，6 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010198004 Ethereal Phantasm（Changehost of Deceit） | drifted | 目标段 `within 9"` → **`within 8"`**（Rules Updates p9 点名 9→8） |
| stratagems 000010198006 Chronosorcerous Bleed（Changehost of Deceit） | drifted | **整条重写**：DB 旧版「对方冲锋阶段·敌已宣布冲锋后·目标被冲锋单位·该敌冲锋骰 -2」→ FP「对方冲锋阶段**开始时**·目标己方未接战 TS PSYKER/SL·选 12" 内可见敌·该敌宣布冲锋时 **-1** 冲锋骰」 |
| stratagems 000010210006 Ensorcelled Infusion（Warpforged Cabal） | drifted | **cp_cost 1 → 2**（Rules Updates p9 点名 CP Cost→2CP；target/effect 段已 11 版态一致） |
| abilities 000001029_a1 Snarling Protector（Maulerfiend） | drifted | **整替**：DB 旧版「英勇介入 0CP + 无条件冲锋重骰」→ FP「英勇介入 **-1CP** + 不阻其他单位用 + 冲锋重骰**条件化**（12" 内友方接战 PSYKER）且须终于与该 PSYKER 接战的敌」 |
| abilities 000004121_a1 Prophetic Sentinels（Sekhetar Robots） | drifted | **整替**：DB「每**战斗轮** 火力压制/英勇介入 **0CP**」→ FP「每**回合** …… **-1CP**」（时机 + 费用双改） |
| abilities 000004122_a1 Malign Trickery（Tzaangor Enlightened w/ Fatecaster Greatbows） | drifted | **整替**：DB「**每回合** 敌结束移动于 **9"** 内 → D6" Normal move」→ FP「对方移动阶段·敌结束移动于 **8"** 内（去 once-per-turn 上限）→ D6" Normal move」 |

### datasheet 数值/关键字漂移（db_compile/fp_errata.py，2 条落库 + 2 类低优先记录）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000001024 TS Heldrake（stat_patch m） | drifted | **M 20+" → 12"**（Rules Updates p10；WE/EC 副本已 12"，TS 副本未滚入） |
| units 000001024 TS Heldrake（keyword_patch remove） | drifted | 删 **AIRCRAFT** 关键字（WE/EC 副本已删；有 WE Heldrake keyword_patch 首例先例）。**OC 免改**：FP 印「OC→'-'」但全库 178 无-OC 单位一律存 '0'（含 WE/EC Heldrake），DB 约定即 '0'，TS 已是 '0' |
| weapons TS Kairos Fateweaver 000004123 Infernal Gateway – focused witchfire | drifted | **A `D3+6` → `D6+6`**（S/AP/D/keywords 一致；witchfire 非 focused 档一致） |
| Chaos Rhino Firing Deck 2 | 低优先记录 | CORE 能力，本 schema 无 core_abilities 载体（CSM/TS Rhino 均未记录 Firing Deck），simulator 未建模运输射击——**不落库，记观察项** |
| FRAME 关键字 ×5（Chaos Land Raider / Predator Annihilator / Predator Destructor / Rhino / Vindicator） | 低优先记录 | 引擎无 FRAME 用途，纯数据完备性——**记观察项** |

### 已滚入/已满足免补（identical）

- **军队规则 Cabal of Sorcerers 三仪式**（Destiny's Ruin 5 / Temporal Surge 6 /
  Twist of Fate 9）与 Rules Updates p9 改写逐字一致——DB 已 11 版态（Wahapedia 滚更并入）；
  Doombolt（WARP CHARGE 7）未被 Rules Updates 触及
- **Incandaeum**（Grand Coven，000010193003）、**Hex-marked Armour** effect 段
  （Warpforged，000010210002）、**Ensorcelled Infusion** target 段、**Twisted Mirage**
  （Warpmeld，000010202007，已 6"/9"）、**Warpmeld Sacrifice** rule（000010200 双段落）
  ——均已 11 版态一致
- 兵牌技能：**Aetherstride**（Daemon Prince w/ Wings 000004120_a2）、**Marked by Fate**
  （Sorcerer in Terminator Armour 000001017_a2）、**Immaterial Flare**（Mutalith
  000001476_a2）、**Destroyer of Futures**（Defiler 000001030_a2）逐字一致
- **Lord of Change**（000004124）全武器格（Bolt of Change witchfire/focused + Rod of
  Sorcery）、**Infernal Master** inferno bolt pistol 已挂 [PISTOL]、**Chaos Vindicator**
  M 已 9"、**Flamers/Screamers** Ld 已 7+、**Kairos** Infernal Gateway witchfire（非
  focused）档一致——均已滚入
- **Hexwarp Thrallband** 重印全套（规则 + 4 增强 + 6 战略）逐字一致

### removed_11e：零

FP 未删任何既有条目（本次是「新增分队 + 既有条目更新」型 FP，无删减）。

### fp_new（inserts 18 条）

3 rules（detachments 表）+ 6 enhancements（enhancements 表）+ 9 stratagems（stratagems 表），
synthetic id `fp11e-ts-*`。点数 `cost` 置空——FP 不含点数、MFM 缓存无增强数据（诚实置空，勿猜）。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Ritual of Regeneration | fp11e-ts-regen | Sorcerous Invigoration | Eruption of Vitality / Curse of Life | Relentless Rebirth / Mutagenic Magicks / Multitudinous Limbs |
| Sekhetar Cohort | fp11e-ts-sekhetar | Ensorcelled Animus | Walking Rampart / Occulus Infernum | Arcane Venting / Ectoplasmic Extrusion / Warp Fields |
| Servants of Change | fp11e-ts-servants | All-Seeing Mutant Hordes | Unravelled Fates / Thicket of Bladed Bone | Prismatic Displacement / Temporal Instability / The Land Writhes |

## 编码语义参照（FAQ p11，不落库）

- Cabal of Sorcerers 无需回合开始时一次性排序所有仪式：逐个选 model + 选 Ritual 后即结算，
  再重复——**仪式属阵营军规，非分队 DSL 编码对象**（surface 名字，见 P5 裁决）
- Warpmeld Pact 前进后可延迟决定射/冲；Touched by Tzeentch 同理

## OCR 记录（不影响数据）

- `page_008.md` Defiler 页脚误作 `Faction Keywords: Death Guard`（应为 Thousand Sons）——
  refine 串页伪影；Defiler 已在库且 faction 正确，不需处理

## DSL 编码盘面（thousandsons.json）

87 项在库（9 分队规则 + 48 战略 + 30 增强）+ 18 项 inserts = **105 项**全量逐条编码
（modeled / partial / not_modeled 三态）。沿 PR9 通道收敛先例，优先零新引擎通道。
高风险防高估硬裁定候选：仅致命伤 FNP（Relentless Rebirth）、治疗类（Sorcerous
Invigoration/Curse of Life）、Warp Fields（S>T 条件 -1 wound）、二选一分支、Flow of Magic
「wholly within」区域态无载体项。
