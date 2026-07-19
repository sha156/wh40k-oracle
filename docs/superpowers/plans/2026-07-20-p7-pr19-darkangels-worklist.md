# P7-PR19 黑暗天使（Dark Angels）逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Dark Angels/`（16 页，Legal from 2026-06-20，"first
iteration … all new"）vs `db/wh40k.sqlite`（faction='SM'，黑暗天使为 ADEPTUS ASTARTES 战团，
无独立阵营行）。体裁沿 PR1/PR4-PR17。

## FP 内容面

黑暗天使 8 个分队：

- **5 个现有分队**（DB 已收录，Wahapedia 已滚更）：
  - **Company of Hunters**（军规 Masters Of Manoeuvre id 000008777）— Ravenwing 机动
  - **Inner Circle Task Force**（军规 Vowed Target id 000008773）— Deathwing 宣誓目标点
  - **Unforgiven Task Force**（军规 Grim Resolve id 000008770）— 通用 OC/[LETHAL HITS]
  - **Lion’s Blade Task Force**（军规 In The Lion’s Claws id 000009732）— Ravenwing+Deathwing
  - **Wrath of the Rock**（军规 Dutiful Tenacity id 000010154）— 通用（S>T -1 致伤守方向）
- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略，id 前缀 `fp11e-da-`）：
  - **Dark Age Arsenal**（规则 Invocations of Ancient Fury：等离子武器 +1 S + 增强 Petition of
    Stability（+6" 射程）/ Entreaty of Perpetual Ardour（snap 5+）+ 战略 Searing Bursts（seared
    -2"M）/ No Sacrifice Too Great（[HAZARDOUS] 等离子 +1 S）/ Revelation of Guilt（等离子 +1 命中））
  - **Darkflight Pursuit**（规则 Black-Winged Vigilance：RAVENWING FLY 远程 [IGNORES COVER] +
    增强 Thundercowl Turbines（ingress）/ Nightforged Battery（重投 A/危险）+ 战略 Skyborne
    Surveillance（侦测）/ Wings of Shadow（Stealth）/ We Are Vengeance（D3+3" 移动））
  - **Interrogation Conclave**（规则 Dread Catechism：CHAPLAIN 击杀触发战斗震慑 + Sower of Dread
    光环 -1 Ld + 增强 Limitless Zeal（+1 冲锋）/ Inescapable Interrogation（远程 [IGNORES COVER]）
    + 战略 Exacting Punishment（[PRECISION]）/ Terrifying Zeal（Ld 测验→-1 命中）/ Wages of
    Cowardice（D3+3" 移动））
  - A/B 已确认三分队规则名/战略名/增强名在库 0 命中（真全新）

## A/B 判定汇总

### 真漂移已补：零 text_patches

5 现有分队的分队规则、战略、增强文本与 11 版 FP 逐字一致——Wahapedia 已滚入 6 月勘误，**全部免补**。
逐项核对（FP page 5-9 vs DB）：

| 分队 | 规则/战略/增强 | 判定 |
|---|---|---|
| Company of Hunters | Masters of Manoeuvre 规则（加速/撤退后射击 + Outrider→Battleline）、6 战略、4 增强（含 Mounted Strategist Ravenwing 版） | identical（FP p9 Rules Updates 已在库） |
| Inner Circle Task Force | Vowed Target 规则（Defensive/Aggressive + DW 步兵 +1 致伤）、Relic Teleportarium 6"、6 战略、4 增强 | identical（FP p9 已在库） |
| Unforgiven Task Force | Grim Resolve 规则（战斗震慑 OC→1 + 指挥 +1 OC）、Armour of Contempt、6 战略、4 增强 | identical（"instead of '-'" vs 库 "instead of 0" 为 DB 约定差异非语义漂移，免补） |
| Lion’s Blade Task Force | In The Lion’s Claws 规则、6 战略、4 增强 | identical（FP p5-6 逐字一致） |
| Wrath of the Rock | Dutiful Tenacity 规则、6 战略、4 增强 | identical（FP p7-8 逐字一致） |

### datasheet 数值漂移（fp_errata stat_patches，2 条）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000000239 Nephilim Jetfighter（m） | drifted | **M `20+"` → `'-'`**（FP p9 去 Hover 后 M→'-'；OC 免改，全库无-OC 一律存 '0'，DB 约定功能等价，同兽人/死灵飞机例） |
| models 000000240 Ravenwing Dark Talon（m） | drifted | M `20+"` → `'-'`（同上） |

**weapon 数值免补（identical）**：FP p10-11 Legends 全部武器档已在库逐字一致——Mace of
Absolution（DW Knights `4/2+/6/-2/2`、DW Strikemaster `5/2+/6/-1/3`）、Calibanite Greatsword
（strike `4/3+/6/-2/2`、sweep `5/3+/6/-2/1`）、Plasma Storm Battery（standard `36"/D6+1/3+/8/-2/2`、
supercharge `.../9/-3/3`）、Fealty（strike `8/2+/12/-4/4`、sweep `16/2+/6/-3/2`）——Wahapedia 已滚更。

**观察项（不落库，datasheet ability/关键词 RAG 层次要，非 DSL 阻塞，留后续）**：① 关键词增删——
Black Knight combat weapon +[DEVASTATING WOUNDS]、Land Speeder Vengeance/Ravenwing Darkshroud/
Sammael +FRAME、Nephilim/Dark Talon 去 Hover（仅删关键词）；② ability 文本改——Deathwing Teleport
Homer 9"→8"、Watcher in the Dark 重写、Lion El’Jonson/Sammael/Ravenwing Command Squad ability
重写；③ Ravenwing Talonmaster / Deathwing Strikemaster / Deathwing Command Squad 三 Legends
datasheet（数值与库一致，reprint 免补）——均属 datasheet ability/元数据层，本 PR 未逐条落，记观察。

### removed_11e：零

### fp_new（inserts 18 条）

3 分队 × (1 规则 + 2 增强 + 3 战略) = 18，synthetic id `fp11e-da-*`。cost 置空（FP 不含点数）。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Dark Age Arsenal | fp11e-da-arsenal | Invocations of Ancient Fury | Petition of Stability / Entreaty of Perpetual Ardour | Searing Bursts / No Sacrifice Too Great / Revelation of Guilt |
| Darkflight Pursuit | fp11e-da-darkflight | Black-Winged Vigilance | Thundercowl Turbines / Nightforged Battery | Skyborne Surveillance / Wings of Shadow / We Are Vengeance |
| Interrogation Conclave | fp11e-da-conclave | Dread Catechism | Limitless Zeal / Inescapable Interrogation | Exacting Punishment / Terrifying Zeal / Wages of Cowardice |

## DSL 编码盘面（darkangels.json）

**73 项**（8 分队规则 + 33 战略 + 32 增强，含 inserts）全量逐条编码：**0 encoded / 22 partial /
51 not_modeled**。零新引擎通道、零新态势开关（沿 PR9-17 约定）。SM 战团气质=移动/目标点/士气/
预备队规则多，可编率低（22/73 ≈ 30%）。

### 可编（22 partial）盘面

- **守方向 AP 恶化 ×5**：5 分队各有 Armour of Contempt（save ap_improve -1，两相位，side=target）
- **守方向 -1 命中 ×2**：High-Speed Focus（射击门）、Wings of Shadow（Stealth=射击门 -1 命中）
- **守方向 -1 致伤 ×2**：尽责坚韧军规（wound_s_gt_t 两相位）、坚不可摧的战线（phase_melee 门——
  WHEN=对手冲锋阶段末、持续至回合结束，对手相位序中射击在冲锋之前，触发后本回合仅剩战斗阶段能生效，
  故门控近战避免过度施加到射击阶段。**审查 HIGH 修复**：原编无条件两相位属 staged-WHEN 漏阶段门，已补 phase_melee）
- **守方向 FNP**：Pennant of Remembrance（fnp 6+，defender_bearer_leading；4+ 战斗震慑升级不编）
- **攻方近战特征值 ×3**：第一军团之武（A+1/S+1/D+1）、卡利班军械（D+1）、远古兵刃（S+2/AP+1/D+1）
  ——均 phase_melee + bearer_leading，battle-shock 升级不编
- **攻方 [LETHAL HITS] ×2**：不赦之怒（全武器 auto_wound 两相位）、死翼勇士（近战 auto_wound +
  bearer_leading）——暴击阈值 5+/battle-shock 升级不编
- **攻方 [IGNORES COVER] ×2**：火力戒律（+ASSAULT/HEAVY 不编）、无从遁形的审讯（bearer_leading）
- **攻方射击特征值/命中 ×2**：远古时代圣械（远程 +2 S 射击门）、照明射击（Deathwing +1 致伤射击门）
- **攻方等离子 weapon_filter ×2**：远古怒火祈唤军规（等离子 +1 S）、罪愆昭示（等离子 +1 命中射击门）
- **黑翼戒备军规**：RAVENWING FLY 远程 [IGNORES COVER]（射击门）

### 未建模（51 not_modeled）——防高估要点

- **移动/资格域**（撤退后射击、加速后冲锋、ingress、D3+3" 移动、pile in/consolidate、水平穿越地形）
- **目标点/OC/CP 域**（Vowed 目标点范围门、Grim Resolve OC、Stalwart +1 OC、Eye of Unseen CP）
- **士气/领导力域**（战斗震慑测验、Sower of Dread -1 Ld、Terrifying Zeal Ld 测验分支）
- **部署/预备队/复活域**（深入打击、战略预备队、Shroud of Heroes 满血复活、死后一击）
- **重骰-1 无载体**（Martial Mastery 重投致伤 1）、**mortal 爆发**（Wrath of the Lion）
- **负关键词门无载体**：Lion’s Will（本单位非 DW/RW/Vehicle 才 +1 命中）、Terrifying Zeal（排除
  MONSTER/VEHICLE）——引擎只能表达"具备关键词"，裸编过度施加
- **复合关键词无载体**：Talon Strike（INFANTRY/MOUNTED CHARACTER 才 +1 致伤）
- **[HAZARDOUS] 关键词非名字子串**：No Sacrifice Too Great（weapon_filter 名字过滤会误放行非危险档）
- **射击×S>T 无复合载体**：Unmatched Fortitude（wound_s_gt_t 两相位通用，裸编近战过度施加）
- **空间分支互斥**：Strength in Unity（依赖敌方处于 Ravenwing/Deathwing 接战范围，单目标模拟无法表达）
- **攻方本单位低于起始编制/战斗震慑自身状态无载体**：Stubborn Tenacity
- **snap shooting/侦测/射程/攻击次数重投**（Entreaty、Skyborne、Petition、Nightforged）
- **誓约标记机制**（Inescapable Justice 宣誓目标转移——不在 P7 编码范围，P5 分类披露层处理）

## 验证

- `pytest tests/ -q`：**1247 passed**（含 test_simulator_dsl_pr19_payload.py 18 断言、
  test_db_compile_dsl_apply 计数 1364、test_db_compile_fp_rules inserts 206、pr4 投影三态对账）
- `db_compile fp-errata`：属性应用 2（Nephilim/Dark Talon M→'-'）
- `db_compile fp-rules`：inserts 应用 18（3 新分队）
- `db_compile dsl-apply`：应用 73 / 指纹让路 0 / 三态 encoded 103 / partial 295 / not_modeled 966
- 基准 gold v3（agent 路径）：accuracy 100.0（correct 96 / partial 0 / wrong 0 / total 96，
  零硬错），见 `benchmarks/v3_edition11/qa_agent_results_p7pr19.json`（纯编码 PR——DSL/DB 补丁
  不进 FAISS 检索语料，检索侧零影响；较历史 99.0（95/1/0）的抬升为波动题良性摆动）
- 自审（code-reviewer 子代理）：1 HIGH / 1 MEDIUM / 1 LOW，**全部已修**：
  - HIGH：坚不可摧的战线（000008389007）漏阶段门 → 补 phase_melee（见上）
  - MEDIUM：Nephilim/Dark Talon 的 OC 0→'-' 未补且无守卫注释 → fp_errata src 补录 OC 不补理由
    （功能等价 + 库无 '-' OC 先例，同 Heldrake 处理）
  - LOW：Shroud of Heroes 注记"满血复活"不准 → 改为"默认带 3 伤、战斗震慑时满血"
