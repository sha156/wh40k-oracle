# P7-PR14 兽人 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Orks/`（85 页，Legal from 2026-06-20，"first
iteration … all new"）vs `db/wh40k.sqlite`（faction='ORK'）。体裁沿 PR1/PR4-PR13。

## FP 内容面

- **1 个全新分队**（inserts，1 规则 + 2 增强 + 3 战略）：
  - **Rollin' Deff**（规则 Thundering Wagons：WAGON 授予 + 重骰冲锋 + advance→6 +
    增强 Boarding Ramps（下车 +1 冲锋）/Targetin' Gizmos（BIG MEK 登载 → 远程
    [IGNORES COVER] + Waaagh 时 [SUSTAINED HITS 1]）+ 战略 Brutal Broadside
    （[RAPID FIRE X]）/Impending Crunch（战意）/Devastating Drift（冲锋近战 [CLEAVE 1]））
  - A/B 已确认规则名/战略名在库 0 命中（真全新）
- **5 个重印分队**：More Dakka! / Taktikal Brigade / Speedwaaagh! / Blitz Brigade /
  Freebooter Krew——DB 已收录、逐字一致**免补**
- **Datasheets**（Bigboss/Bannernob/Wartrakks/Big Mek Dakkarig/Wazdakka/Breaka Boyz/
  Tankbustas）——**均已在库**（Wahapedia 已滚入 + 早前 fp_errata new_units），reprint 免补
- **Rules Updates**（p23-25）+ Imperial Armour/Legends datasheets（reprint 免补）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，9 条）

| 行 | 判定 | 说明 |
|---|---|---|
| detachments 000008867 Da Hunt Is On（Da Big Hunt） | drifted | 第一 bullet 整改：旧「冲锋含 Prey 即重骰」→ **「Prey 12"内 → 重骰 + 须终于与 Prey 接战」**（嵌套结构） |
| detachments 000008875 Try Dat Button（Dread Mob） | drifted | 末段：多来源 [HAZARDOUS] 危险测试失败判定 `1或2` → **`1-3`** |
| stratagems 000008869004 Dat One's Even Bigga!（Da Big Hunt） | drifted | EFFECT：旧「重骰须一目标为 Prey」→ **「重骰后须终于与 Prey 接战」** |
| stratagems 000008882007 Go Get 'Em!（Green Tide） | drifted | EFFECT 整改：旧「Roll D6 移动至最近敌·10+ 重骰」→ **「surge move D6"」** |
| stratagems 000008873007 More Gitz Over 'Ere!（Kult of Speed） | drifted | TARGET `within 9"` → **`8"`** |
| abilities 000000004_a2 Da Jump（Weirdboy） | drifted | 出场距离 `9"` → **`8"`** |
| abilities 000002490_a2 Single-minded Predator（Beastboss Squigosaur） | drifted | 整改：旧「英勇介入 0CP + 无条件复用」→ **「英勇介入 -1CP + 不阻其他单位用」** |
| abilities 000000031_a1 Boom Bomb（Blitza-Bommer） | drifted | 整改：旧「Normal move 越过敌 4+ D6 致命伤」→ **「对方战斗阶段结束·24"内可见敌（排除 Lone Op）·4+ D6 致命伤」** |
| abilities 000000030_a1 Burna Bomb（Burna-Bommer） | drifted | 整改：旧「Normal move 越过敌·去掩体收益」→ **「对方战斗阶段结束·24"内可见敌·[IGNORES COVER] + 每模型 6→1 致命伤」** |

### datasheet 数值漂移（fp_errata stat_patches，4 条）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000000031 Blitza-bommer（m） | drifted | **M `20+"` → `'-'`**（OC 免改已 '0'） |
| models 000000030 Burna-bommer（m） | drifted | M `20+"` → `'-'` |
| models 000000029 Dakkajet（m） | drifted | M `20+"` → `'-'` |
| models 000000032 Wazbom Blastajet（m） | drifted | M `20+"` → `'-'` |

**观察项（不落库，datasheet ability RAG 层次要，非 DSL 阻塞，留后续）**：① FRAME 关键字
×8（Battlewagon/Blitza/Burna/Dakkajet/Hunta Rig/Kill Rig/Stompa/Trukk）——机制只删不加；
② Boss Snikrot Red Skulls/Kunnin' Infiltrator、Big Mek Shokk-boosta（+terrain/desperate
escape 细节）、Boyz Bodyguard（双领袖）、Bomb Squigs 整改、Battlewagon/Stompa transport
容量、Wartrakk 去 Core/Support 段——datasheet ability/元数据层，本 PR 未逐条落，记观察。

### 已滚入/已满足免补（identical）

- **Rules Updates 文本**：军规 Waaagh! 首段、Da Boss Is Watchin' 规则、Mob Mentality
  规则（BOYZ 6+/5+ invuln）、Adrenaline Junkies 规则、Hulking Brutes 战略（AP 恶化）、
  Tide of Muscle 战略、Prophet of Da Great Waaagh!/Da Biggest and da Best/Dead Brutal/
  Piston-driven Brutality/Special Dose 兵牌技能——均已 11 版态一致
- **5 重印分队全套** + 7 新 datasheet 单位（均已在库）+ Imperial Armour/Legends——reprint 免补

### removed_11e：零

### fp_new（inserts 6 条）

1 rule + 2 enhancements + 3 stratagems，synthetic id `fp11e-ork-rollin-*`。cost 置空。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Rollin' Deff | fp11e-ork-rollin | Thundering Wagons | Boarding Ramps / Targetin' Gizmos | Brutal Broadside / Impending Crunch / Devastating Drift |

## DSL 编码盘面（orks.json）

142 项（15 分队规则 + 77 战略 + 50 增强，含 inserts）全量逐条编码。兽人为近战冲锋/
Dakka 阵营，可编率中高：Mob Mentality BOYZ invuln（守方）、大量 +命中/致伤/S/A/AP、
[LETHAL/SUSTAINED/DEV/CLEAVE/RAPID FIRE]、守方 -1 命中/AP 恶化、Waaagh 增益（近战 buff
类可编，Waaagh 状态用 toggle 或注记）、ANTI-X。防高估：Waaagh 状态门（无 toggle 时按注记
/单分支）、冲锋骰/据点/战意/移动/致命伤类、Try Dat Button 随机六选一、[RAPID FIRE X=A]
特殊语义无载体。
