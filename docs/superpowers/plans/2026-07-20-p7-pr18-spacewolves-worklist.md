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

## DSL 编码盘面（`dsl_payloads/spacewolves.json`——本迭代已落账）

编码范围 = `faction='SM'` 下 7 个太空野狼分队的全部**非 removed_11e** 战略/增强
+ 9 行分队规则（materialize 自 `detachments.rule_text`）。
**军规 Oath of Moment（000008350）不收录**：它是全体 ADEPTUS ASTARTES 共享军规、
非太空野狼专属（沿血天使 PR9 先例；黑色圣堂 PR6 收录 Templar Vows 是因其**替换**了
Oath of Moment，本战团不替换）。

**总计 64 条 = 5 encoded / 12 partial / 47 not_modeled**（零新引擎通道、零新态势开关，
连续第七个纯编码 PR）。

| 分队 | 规则 | 战略 | 增强 | 小计（enc/par/nm）|
|---|---|---|---|---|
| Champions of Fenris | 1 | 3 | 2 | 0 / 2 / 4 |
| Legends of Saga and Song | 1 | 3 | 2 | 1 / 0 / 5 |
| Veterans of the Fang | 1 | 3 | 2 | 0 / 1 / 5 |
| Saga of the Great Wolf | 3 | 6 | 4 | 2 / 1 / 10 |
| Saga of the Beastslayer | 1 | 6 | 4 | 1 / 2 / 8 |
| Saga of the Bold | 1 | 6 | 4 | 1 / 3 / 7 |
| Saga of the Hunter | 1 | 6 | 4 | 0 / 3 / 8 |
| **合计** | **9** | **33** | **22** | **5 / 12 / 47** |

### encoded（5 条——效果全落 effects 且等价）

| id | 名称 | 编码 | 相位门推理（WHEN → 可生效相位）|
|---|---|---|---|
| 000010270002 | UNBRIDLED FEROCITY | `wound/modify +1` | WHEN=Fight phase ⇒ 仅近战 → `phase_melee` |
| 000010266002 | INSPIRING PRESENCE | `hit/auto_wound`（[LETHAL HITS]）| WHEN=Fight phase + 面为近战武器 ⇒ `phase_melee` |
| 000010661006 | EYE OF THE PACK | `wound/modify +1` | WHEN=己方射击阶段 ⇒ `phase_shooting`（与上两条构成互补门）|
| fp11e-sw-legends-e2 | Fierce Example | `wound/t_improve +1`（守方）| "This unit has +1 T" 无相位限制 ⇒ **不加门**（加门=欠建模）|
| 000010660005 | Skjald's Foretelling | `wound/modify +1` | [LANCE]=冲锋回合致伤 +1 ⇒ 复合 tag `melee_charging`（射击阶段先于冲锋阶段，永不触发）|

### partial（12 条——可建模子集 + 残量逐条注记）

| id | 名称 | 已编 | 未建模残量 |
|---|---|---|---|
| det000010268 | Legendary Slayers | 对 CHARACTER/MONSTER/VEHICLE 三条 `hit/auto_wound`（关键词门，**不加相位门**：原文 "makes an attack"）| Saga 完成后全体 [LETHAL HITS]（战局累计状态机）|
| fp11e-sw-fenris-s3 | Stalk Between Worlds | `save/cover`（Stealth=11 版掩体）+ `phase_shooting` | 敌武器 [IGNORES COVER] 整体抵消；触发时机假设 |
| 000010266003 | CHAMPION'S GUIDANCE | `hit/reroll fail`，**condition 留空** | "可以重骰"按最优策略=只重骰失败（等价）；WHEN=射击**或**近战 ⇒ 不加相位门 |
| 000010266006 | HEROIC RESOLVE | `damage/damage_reduction 1` + `phase_shooting`（守方）| WHEN 仅敌方射击阶段；限 SW CHARACTER 守方 |
| 000010661002 | THE FOE FORESEEN | `save/ap_improve -1`（守方）**不加相位门** | WHEN=敌方射击**或**近战 ⇒ 两相位均适用；触发时机假设 |
| 000010262004 | OVERWHELMING ONSLAUGHT | `hit/modify -1` + `phase_melee`（守方）| 施放前提（两支 AA 单位交战）按已满足假设 |
| fp11e-sw-fenris-e1 | A Giant Amongst Giants | `wound/s_improve +1` + `phase_melee` | +2 W（攻方无 W 通道）；限携带者模型 |
| fp11e-sw-fang-e1 | Eye of the Hunter | `save/ignores_cover` + `save/ap_improve +1`，均 `phase_shooting` | [ASSAULT]（移动域）|
| 000010269004 | Elder's Guidance | `save/ap_improve +1` + `phase_melee` | 每场一次；限率领 BLOOD CLAWS |
| 000010265002 | Braggart's Steel | `wound/s_improve +2` + `phase_melee` | Boast 达成时 +1 D（战局状态机）；限携带者武器 |
| 000010261003 | Fenrisian Grit | `fnp/fnp 4`（守方）| 仅携带者单模型（整单位目标会高估）|
| 000010261005 | Feral Rage | `attacks/modify +1`（`phase_melee`）+ `attacks/modify +1`（`melee_charging`，引擎侧累加=冲锋 +2）| 限携带者武器 |

态势开关：只用既有 `bearer_leading` / `defender_bearer_leading` 两枚（测试有护栏断言
`used ⊆ {bearer_leading, defender_bearer_leading}`）。

### not_modeled 的主要归因（47 条）

| 归因 | 条数量级 | 代表条目 |
|---|---|---|
| 移动/冲锋/加速/涌动/穿越 | 最大宗 | Shock Cavalry、Thunderous Pursuit、Impetuosity、Fenrisian Ferocity、Battle Instincts、Bounding Advance、Loping Charge |
| 预备队/部署/重新部署 | 5 | Wings of the Blizzard、Coordinated Strike、Hunter's Guile、Chariots of the Storm、Swift Hunter |
| 战意震慑（battle-shock）| 4 | Chilling Howl、Howlmaw、Weaver of Sagas |
| 目标点/OC/CP/战略元规则 | 6 | Runes of Claiming、Territorial Advantage、Thirst for Glory、Skjald、Grimnar's Mark |
| **二选一单分支** | 2 | Grizzled Killers（[SUSTAINED HITS 1] 或 [LETHAL HITS]）、Master of Wolves 的 Ferocious Strike |
| **三选一持续声明态**（无开关载体，沿 PR17 Mission Tactics 裁定）| 2 | Master of Wolves（Hunting Packs）、Grimnar's Command |
| **重投单骰 / 重投 1** | 2 | Heroes All（"re-roll **one** Hit roll"）、Marked for Destruction（"re-roll a Wound roll of **1**"）|
| **仅致命伤 FNP** | 1 | Wolf Totems（引擎 FNP 对全部伤害生效，裸编高估）|
| **攻方关键字门** | 1 | Helm of the Beastslayer（"attack **made by** a CHARACTER/MONSTER/VEHICLE"——引擎关键词条件只读守方，裸编会对全部攻击者过度施加）|
| 双方模型数/战场几何比较 | 2 | Pack's Quarry、Hordeslayer |
| 多武器名过滤（weapon_filter 为条目级单一子串）| 1 | Wolf Master（teeth and claws / Tyrnak / Fenrir 三名并列）|
| 攻击分配域（[PRECISION]）/ 关键字动态授予 / 复活 | 3 | Fangs of the Pack、Birth of a Saga、Thunderwolf's Fortitude |
| 编制/行动/侦测域 | 4 | Old Greymanes、Icy Calm、Blade-keen Senses、Restrictions |

### 落账验证（本迭代）

- `python -m db_compile dsl-apply`：全库 1355 条投影（encoded 108 / partial 285 /
  not_modeled 962），**零指纹让路、零跳过**；再次运行全幂等
- `pytest tests/test_simulator_dsl_pr18_payload.py`：**30 绿**（结构 + DB 对账 +
  攻守双向引擎级差分；每条相位门测试一正一负成对写）
- `pytest tests/`：**1259 绿**（全库零破坏）
- `tests/test_db_compile_dsl_apply.py` 累计断言同步 1291→1355 / 三态 103·273·915 →
  108·285·962

### 基准回归（gold v3，agent 路径）

`benchmarks/v3_edition11/qa_agent_results_p7pr18.json`：**accuracy 99.0（correct 95 /
partial 1 / wrong 0 / total 96），零硬错**，degraded_count 34 与 PR17 持平。

对 PR17（100.0）唯一差异是 **#41「兽人小子（Boyz）是什么单位？」由 ✅ 翻 ⚠️**——
已按约定逐项核对：**两次运行的检索来源列表逐条完全相同**（兽人10版中文 p36/33/46/21 +
黑图书馆 + Core Rules p11/66），答案正文实质等同（同样给出属性/编制/装备/Waaagh! +
Get da Good Bitz，同样未展开 gold 里的「保镖 Bodyguard」条款），差异仅在 LLM 判官的
宽严波动。#41 本就在历史波动题名单内；且本 PR 是纯编码 PR——DSL/DB 补丁不进 FAISS
向量索引（未 ingest），检索侧零影响。**判定：非回归**。

### 环境坑（本迭代实测，记给后来人）

`db/wh40k.sqlite` 是 gitignored 的可重建产物，**跨分支共用同一份**。本工作区曾在
main（payload 数量多于本分支）上跑过 `dsl-apply`，导致本分支库里残留 488 行本分支
真源不存在的投影，直接把 `test_simulator_dsl_pr4_payload.py::test_projection_counts_match_payload`
（DB 投影计数 == 全部 payload 计数）打红——**与本 PR 无关的环境漂移**。处理 = 把这些
孤儿行的 `effect_dsl_json` 清空、`dsl_status` 复位（等价于 `--rebuild` 清零 + restore
链只补回本分支真源）。换分支后需重跑 `dsl-apply`（幂等）。

### 自审结论（code-reviewer 子代理，2026-07-21）

**CRITICAL 0 / HIGH 0 / MEDIUM 1 / LOW 2，结论 APPROVE。**17 条带 effects 的条目逐条
对 FP 原文 + DB 现值做 A/B：相位门方向、参数符号、condition tag、side 归属、toggle
配对全部正确；**历史四次同型 HIGH（漏相位门→过度施加）与 PR13 型 MEDIUM（多余相位门
→欠建模）均未复发**。

已处置：
- **MEDIUM（已修）**：`Master of Wolves`（det000010657）的 not_modeled 注记原本只点了
  Encircling Jaws 与 Ferocious Strike 两个分支、漏点第三支 **Hunter's Eye**（远程命中
  +1，其实有现成通道 `hit/modify +1 × phase_shooting`，只差一个「本大回合狩猎群=
  Hunter's Eye」的互斥声明开关，PR6 圣兆式先例）。已在注记里显式写明该分支、它可编、
  以及本迭代守「零新开关」约定故不编——避免后来者分不清"分析过判不可编"与"漏看"。
  **列为后续补录投入产出比最高项**（零新 condition tag，只需一个新开关）。
- **LOW（已修）**：根目录临时生成脚本/转储（`_gen_sw_payload.py` / `_sw_dump.txt` 等）
  已删除，未进 diff。
- **LOW（同 MEDIUM，已随之修复）**：三选一分支枚举补全。

审查另行核实并归档的边界结论：`Wolf Master`（三具名武器 [LETHAL HITS]）在当前架构下
**只能** not_modeled——`dsl_apply` 对 stratagems/enhancements 走 `UPDATE ... WHERE id=?`，
一个 DB 行只承载一条 payload 条目，拆三条分别 `weapon_filter` 会撞 (table,id) 去重守卫。

### 编码红线复核（沿历史 4 次同型 HIGH 复发坑）——本 PR 双向自查结论

- **正方向（漏门=过度施加）**：全部 17 条带 effects 的条目逐条顺 WHEN 推可生效相位，
  近战触发挂 `phase_melee`/`melee_charging`、射击触发挂 `phase_shooting`，测试成对写
  正负例
- **反方向（多门=欠建模，PR13 型 MEDIUM）**：`Legendary Slayers`（"makes an attack"）、
  `CHAMPION'S GUIDANCE`（射击**或**近战）、`THE FOE FORESEEN`（敌方射击**或**近战）、
  `Fierce Example`（恒定 +1 T）四条**刻意不加相位门**，并在注记里写明理由
