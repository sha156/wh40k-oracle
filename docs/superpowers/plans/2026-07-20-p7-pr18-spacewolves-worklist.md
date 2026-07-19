# P7-PR18 太空野狼（Space Wolves）逐条 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Space Wolves/`（45 页，VERSION 1.0，Legal from
2026-06-20，"first iteration … all of the following content should be regarded as
new"）vs `db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR6/PR8 裁定：
**FP 完整重印即整体替换**（同名分队规则外科替换 rule_text，未收录旧战略/增强标
removed_11e，新条目走 fp_new inserts）；全新分队整组 inserts（`fp11e-sw-*` 前缀
synthetic id，cost 置空）；FP 未提及的旧 codex 分队保持活跃只按 Rules Updates 补真漂移。

**结构注意**：太空野狼在 Wahapedia/DB 体系下无独立阵营行，全部挂 `faction='SM'`
（faction_keywords 含 Space Wolves）。本 PR 所有补丁按 SW 范围圈定，不越界改其他战团
共享行。CoF 增强的 `detachment_id='000001008'`（沿库现值）。

## FP 内容面

- **4 个 FP 分队**：
  - **Champions of Fenris**（p2）——**同名重印但内容全换**：十版 Terminator 向
    detachment（The Great Wolf Watches 反击 + Terminator OC，6 战略 4 增强）→ 11 版
    INFANTRY CHARACTER 向（Countercharge 规则 + Wolf Totems/Runes of Claiming/Stalk
    Between Worlds 3 战略 + A Giant Amongst Giants/Preyslayer 2 增强）
  - **Legends of Saga and Song**（p3，**全新**）——Terminator 向：Loping Charge 规则
    + Fangs of the Pack/Chilling Howl/Wings of the Blizzard 3 战略 + Thirst for
    Glory/Fierce Example 2 增强
  - **Veterans of the Fang**（p4，**全新**）——Grey Hunter 向：Old Greymanes 规则
    + Grizzled Killers/Icy Calm/Blade-keen Senses 3 战略 + Eye of the Hunter/
    Weaver of Sagas 2 增强
  - **Saga of the Great Wolf**（p6-7）——**完整重印 ≈ 库现值**（Wahapedia 已滚入）：
    Master of Wolves（Hunting Packs 三选一）+ Howling Onslaught + Restrictions 规则、
    6 战略、4 增强全部逐字一致；仅 Grimnar's Mark 增强真漂移（见下）
- **FP 未提及但仍活跃的旧 codex 分队 3 个**（Rules Updates p10 明确仍在更新，非删除）：
  Saga of the Beastslayer / Saga of the Bold / Saga of the Hunter
- **兵牌**：Wolf Scouts（p8）与 Grey Hunters（000000305）均已在库，Wolf Scouts
  数据卡为参考重印，Rules Updates 未列其数值变更 → 视作重印一致（观察项）
- **Rules Updates（p10）**：Saga of the Beastslayer 分队 3 条 + Logan Grimnar/Iron
  Priest/Wolf Guard Headtakers/Wulfen Dreadnought/Fenrisian Wolves 兵牌技能 6 条

## A/B 判定汇总（DB 11 版对齐——本迭代已落账）

### 真漂移已补（fp_rules text_patches，4 条）

| 行 | 判定 | 说明 |
|---|---|---|
| detachments 000009850 CoF 规则 The Great Wolf Watches | drifted | **同名整段替换**：十版 Terminator OC + 反击 → 11 版 INFANTRY CHARACTER 的 Countercharge（英雄干预不占次数）|
| enhancements 000010660002 Grimnar's Mark | drifted | 十版 0CP + 从第二轮起 + 可编队挂 WGT → 11 版 -1CP + 每轮一次 + 不占其它单位次数（删挂载句）|
| stratagems 000010270006 Impetuosity（Saga of the Beastslayer）| drifted | Rules Updates：EFFECT 整替十版 Impetuous move 流程 → 11 版核心 surge move D6" |
| stratagems 000010270005 Thunderous Pursuit（Saga of the Beastslayer）| drifted | Rules Updates：TARGET 距离 9"→8" 外科替换 |

### 已滚入/已满足免补（identical）

- **Saga of the Great Wolf 全组**：规则 Master of Wolves（000010657）/ Howling
  Onslaught（000010658）+ 6 战略 000010661xxx + 3 增强（Howlmaw/Chariots/Skjald）逐字一致
- **Saga of the Beastslayer Rules Updates 两条已滚入**：Wolf-touched 增强
  （000010269002，措辞已 11 版）/ Legendary Slayers 规则 Beastslayer 段（000010268，
  halving 已 11 版）——库现值即目标文本，零动作
- Wolf Scouts / Grey Hunters 数据卡在库，无数值漂移列出

### removed_11e（deactivations 10 条，旧 Champions of Fenris 重印未收录）

- stratagems（6）：PREYTAKER'S EYE 000009852002 / ARMOUR OF CONTEMPT 000009852003 /
  RUNES OF CLAIMING 000009852004 / CHILLING HOWL 000009852005 / STALKING WOLVES
  000009852006 / ONRUSHING STORM 000009852007
- enhancements（4）：Wolves' Wisdom 000009851002 / Foes' Fate 000009851003 /
  Fangrune Pendant 000009851004 / Longstrider 000009851005
- 注：十版 CoF 的 CHILLING HOWL/ONRUSHING STORM 语义在 11 版并入全新分队 Legends of
  Saga and Song（Chilling Howl / Wings of the Blizzard），旧行 removed、新行 insert

### fp_new（inserts 17 条）

- **Champions of Fenris 重印新增**（p2，id 组 fp11e-sw-fenris-*）：战略 Wolf Totems
  （INFANTRY CHARACTER 受致命伤时 FNP 5+ vs mortal）/ Runes of Claiming（占领目标点，
  **带 `expect_duplicate_name`**——同名旧 RUNES OF CLAIMING 已 removed）/ Stalk
  Between Worlds（Stealth）+ 增强 A Giant Amongst Giants（+2W、近战 +1S）/ Preyslayer
  （重投加速+反击骰）；detachment_id 沿库现 000001008
- **Legends of Saga and Song**（p3，id 组 fp11e-sw-legends-*）：规则 Loping Charge
  （TERMINATOR +1 冲锋骰）+ 战略 Fangs of the Pack（TERMINATOR 近战 [PRECISION]）/
  Chilling Howl（战斗震慑）/ Wings of the Blizzard（置入战略预备队）+ 增强 Thirst for
  Glory（TERMINATOR +1 OC）/ Fierce Example（WGT +1 T）
- **Veterans of the Fang**（p4，id 组 fp11e-sw-fang-*）：规则 Old Greymanes（Grey
  Hunter 行动后仍可射击 + 编队拆队）+ 战略 Grizzled Killers（Grey Hunters 近战
  [SUSTAINED HITS 1] 或 [LETHAL HITS] 二选一）/ Icy Calm（加速/撤退后仍可行动）/
  Blade-keen Senses（探测距离 +6"）+ 增强 Eye of the Hunter（远程 [ASSAULT][IGNORES
  COVER]+1AP）/ Weaver of Sagas（解除战斗震慑）
- 增强点数一律 cost=NULL（FP 不含点数、MFM 缓存无增强数据——沿 PR4-16 AAC 裁定诚实置空）
- 自译 name_zh（detachments/stratagems 层）：大步冲锋/群狼獠牙/彻骨长嚎/暴雪之翼；
  灰鬃老将/沙场老杀手/寒冰沉着/锐感如刃；狼图腾/宣索符文/界隙潜行

### fp_errata（兵牌数值/关键词层）——本 PR 零条目

- Rules Updates 的兵牌变更为技能**正文**改动（Logan Grimnar High King of Fenris/Guile
  of the Wolf、Iron Priest Gift of the Iron Wolf、Wolf Guard Headtakers Headhunters、
  Wulfen Dreadnought Bestial Rage、Fenrisian Wolves Predatory Instinct），均为
  移动/致命伤/预备队/CP 域机制，无引擎载体且不被 DSL payload 引用（payload 只编分队
  规则/战略/增强）——沿 BT「无引擎/检索消费者记观察项」裁定，留待数据卡勘误专轮处理

### 落账验证（本迭代）

- `python -m db_compile fp-rules`：文本应用 4 / 失效标记应用 10 / 补录插行应用 17，
  零让路零跳过零无效；再次运行全幂等
- `pytest tests/test_db_compile_fp_rules.py tests/test_db_compile_fp_errata.py`：50 绿
  （已更新 deactivations 30→40、inserts 188→205 计数断言 + id 集）
- `pytest tests/`：**1229 绿**（全库回归零破坏）

## DSL 编码盘面（P7 阵营技能逐条编码——待后续迭代）

DB 11 版对齐已收官，DSL payload `dsl_payloads/spacewolves.json` 待建。编码范围
（faction='SM'，7 分队）：

| 分队 | 规则 | 战略 | 增强 | 编码要点（气质预判）|
|---|---|---|---|---|
| Champions of Fenris | Countercharge（英雄干预，movement/CP 域）| Wolf Totems（FNP vs mortal）/ Runes of Claiming（目标点）/ Stalk Between Worlds（Stealth）| A Giant Amongst Giants（**+2W not_modeled + 近战 +1S 可编**）/ Preyslayer（重投骰）| 多为目标点/移动/元规则 → 低可编率；A Giant 近战 S 特征值通道 |
| Legends of Saga and Song | Loping Charge（冲锋骰）| Fangs of the Pack（**TERMINATOR 近战 [PRECISION]→分配域 not_modeled**）/ Chilling Howl / Wings of the Blizzard | Thirst for Glory（+1 OC）/ Fierce Example（**+1 T 守方可编**）| Fierce Example T 特征值净算；余多 not_modeled |
| Veterans of the Fang | Old Greymanes（行动/编队域）| **Grizzled Killers（Grey Hunters 近战二选一 [SUSTAINED/LETHAL]——二选一单分支慎编）** / Icy Calm / Blade-keen Senses | Eye of the Hunter（**远程 [ASSAULT][IGNORES COVER]+1AP——射击门 partial**）/ Weaver of Sagas | Eye of the Hunter 远程 AP 改善带 phase_shooting 门 |
| Saga of the Great Wolf | Master of Wolves（Hunting Packs 三选一态势，无开关不编）/ Howling Onslaught | 6 战略（多移动/AP恶化/目标点）| Grimnar's Mark / Howlmaw / Chariots / Skjald's Foretelling（[LANCE] 无冲锋载体）| The Foe Foreseen 守方 AP 恶化可编；余低 |
| Saga of the Beastslayer | Legendary Slayers（[LETHAL HITS] 条件 CHARACTER/MONSTER/VEHICLE——**负/正关键字门慎编**）| Unbridled Ferocity（近战 +1 致伤）/ Impetuosity（surge）/ 余移动/射击门 | Braggart's Steel 类（近战 +S/+D）| 近战致伤/特征值可编，Saga 完成动态门 not_modeled |
| Saga of the Bold | Heroes All（重投，Saga 动态）| Inspiring Presence（近战 [LETHAL HITS]）/ 余 | Braggart's Steel（**近战 +2S +条件 +1D**）/ Hordeslayer（+A 条件）/ 余 | 近战 S/A 特征值通道可编，条件 Boast 门 not_modeled |
| Saga of the Hunter | Pack's Quarry（近战 +1 命中，条件门）| Hunters' Trail（consolidate）/ 余移动 | Feral Rage（**近战 +1A + 冲锋后再 +1A**）/ Fenrisian Grit（FNP 4+）/ Wolf Master（[LETHAL HITS] 条件）| Feral Rage 基础 +1A 可编、冲锋增量 melee_charging 门；Fenrisian Grit FNP 可编 |

**编码红线（沿历史 4 次同型 HIGH 复发坑）**：
- **阶段性 WHEN 门控**：战略冲锋后触发（如 Feral Rage 冲锋增量）⇒ 仅剩近战须加
  phase_melee/melee_charging 门；顺 WHEN 推可生效阶段，门控测试一正一负成对写
- 二选一单分支（Grizzled Killers/Ferocious Strike）无条件编入会过度施加 → 慎编或 partial
- 负/正关键字门（Legendary Slayers 的 CHARACTER/MONSTER/VEHICLE、非载体）→ not_modeled
- 射击×关键字 / 远程 S>T / [RAPID FIRE X] / 仅致命伤 FNP / Saga·Boast 动态门 / 目标点 /
  预备队 / 移动 / CP / 战斗震慑 → 无精确载体一律 not_modeled，半编降 partial
- Grizzled Killers/Fangs of the Pack 等 Terminator/Grey Hunters 关键字限定——引擎单位
  侧无关键字过滤载体时，武器面 buff 裸编会过度施加，据情 partial（附注记）或 not_modeled
