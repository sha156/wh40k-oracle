# P7-PR12 德鲁卡里 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Drukhari/`（21 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态，faction='DRU'）。体裁沿 PR1/PR4-PR11 裁定。

## FP 内容面

- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Exhibition of Slaughter**（规则 Exacting Cruelty + 增强 Periapt of Torments /
    Hyperstimm Trafficker + 战略 Planned Strikes / Sculpting the Stage / Acrobatic Display）
  - **Kabalite Agonysts**（规则 Contracted Harvest + 增强 Towering Arrogance /
    Contempt for Rivals + 战略 Prioritised Victim / Shadows' Reach / Killers from the
    Dark Spires）
  - **Tools of Torment**（规则 Darkest Artifice + 增强 Gnarlskin Experimentor / Elixir
    of the Corpse Courts + 战略 Salting the Wound / Dividends of Agony / Urgent Metamorphosis）
  - A/B 已确认三者规则名/战略名在库**全 0 命中**（真全新）
- **1 个重印分队**：Reaper's Wager（规则 Callous Competition + 6 战略 + 4 增强）——
  DB 已收录、逐字一致**免补**
- **Rules Updates**（p7）+ **Legends Datasheets**（p8+，reprint stat blocks，免补）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，8 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010585007 Enfolding Nightmare（Covenite Coterie） | drifted | EFFECT 整改：旧「Roll D6 移动至最近敌」→ **「surge move D6"」** |
| stratagems 000010577006 Swooping Mockery（Skysplinter Assault） | drifted | TARGET `within 9"` → **`8"`** |
| stratagems 000010577003 Wraithlike Retreat（Skysplinter Assault） | drifted | EFFECT 追加句：**下车同回合可再登上该 TRANSPORT** |
| stratagems 000010581006 A Challenge Met（Spectacle of Spite） | drifted | When/Target/Effect 整改 + 删 Restrictions：旧「对方移动结束·9"·无冲锋加成」→ **「对方移动阶段敌撤退后·未接战 WYCH CULT 于 6"内·冲锋仅可选撤退单位」** |
| abilities 000000659_a2 Skyboard Evasion（Hellions） | drifted | 整改：`9"` → `8"` + 加「对方移动阶段」+「未接战」+ 去 once-per-turn |
| abilities 000004155_a3 Mind Like a Steel Trap（Lady Malys） | drifted | 整改：光环（无限）→ **once per turn**（对方 12"内单位用战略 +1CP） |
| abilities 000000657_a2 Aerialists（Venom） | drifted | EFFECT 追加句：**下车同回合可再登上此 TRANSPORT**（fly 排除句 DB 已有） |
| abilities 000000661_a2 Void Mine（Voidraven Bomber） | drifted | 整改：旧「本战一次·Normal move 越过敌·D6"内 4+→D6 致命伤」→ **「对方战斗阶段结束·24"内可见敌（排除 Lone Op）·D6"内 4+→D6 致命伤」** |

### datasheet 数值漂移（fp_errata stat_patches，2 条）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000000660 Razorwing Jetfighter（m） | drifted | **M `20+"` → `'-'`**（去 Hover 后无 Normal move；'-' 为库既有约定，50 单位用） |
| models 000000661 Voidraven Bomber（m） | drifted | 同上 M `20+"` → `'-'` |

**观察项（不落库）**：① Razorwing/Voidraven OC 免改（FP 印「OC→'-'」但全库无-OC 一律存
'0'，已是）；② Hover 关键字已在库移除（免补）；③ FRAME 关键字 ×5（Raider/Ravager/
Razorwing/Venom/Voidraven）——keyword_patch 机制只删不加主关键字；④ Venom Transport
容量 6 + 拆分单位——datasheet.transport 元数据字段，非 ability/stat，记观察项。

### 已滚入/已满足免补（identical）

- **军规 Corsairs and Travelling Players**（000009974）与 FP 新增段逐字一致（Harlequins/
  Anhrathe 250/500/750）——已 11 版态
- **Connoisseurs of Pain**（Covenite Coterie，000010585006）AP 恶化 + Pain Token 全文一致
- **Reaper's Wager 重印全套**（Callous Competition 规则 + Dance Macabre / Fateful Role /
  Malicious Frenzy / Murderer's Circus / Scintillating Tempo / Shorten the Odds 6 战略 +
  Archraider / Conductor of Torment / Reaper's Cowl / Webway Walker 4 增强）——逐字一致
- **Legends Datasheets**（Raven Strike Fighter 等 stat blocks）——非 Rules Updates 变更项，
  reprint 免补

### removed_11e：零

### fp_new（inserts 18 条）

3 rules + 6 enhancements + 9 stratagems，synthetic id `fp11e-dru-*`。点数 `cost` 置空。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Exhibition of Slaughter | fp11e-dru-exhibition | Exacting Cruelty | Periapt of Torments / Hyperstimm Trafficker | Planned Strikes / Sculpting the Stage / Acrobatic Display |
| Kabalite Agonysts | fp11e-dru-agonysts | Contracted Harvest | Towering Arrogance / Contempt for Rivals | Prioritised Victim / Shadows' Reach / Killers from the Dark Spires |
| Tools of Torment | fp11e-dru-torment | Darkest Artifice | Gnarlskin Experimentor / Elixir of the Corpse Courts | Salting the Wound / Dividends of Agony / Urgent Metamorphosis |

## DSL 编码盘面（drukhari.json）

112 项（13 分队规则 + 61 战略 + 38 增强，含 inserts）全量逐条编码。德鲁卡里为高速
近战/毒刃阵营，可编率中高：[LETHAL HITS]/[SUSTAINED HITS]/[PRECISION]/[DEVASTATING
WOUNDS]/[IGNORES COVER]、+1T（Hyperstimm/Gnarlskin）、5+ 无效保护（Acrobatic Display/
Elixir）、守方 S>T 被伤-1（Darkest Artifice/Gnarlskin 走 wound_s_gt_t）、守方 -1 命中
（Murderer's Circus）、AP 恶化（Connoisseurs of Pain）。防高估：赌局输赢重骰1类
（Callous Competition/Prioritised Victim——重骰1≠重骰失败）、幸存反打（Fateful Role）、
[LETHAL: non-MONSTER/VEHICLE] 负关键字门无载体（Exacting Cruelty/Contracted Harvest——
裸 lethal 会对 monster/vehicle 过度施加）、Pain Token 经济、二选一按单分支（Malicious
Frenzy）、移动/预备队/战意类。
