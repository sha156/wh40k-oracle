# P7-PR16 灰骑士 fp_rules/fp_errata 逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Grey Knights/`（19 页，Legal from 2026-06-20，Version 1.0，
"first iteration … all new"）vs `db/wh40k.sqlite`（faction='GK'）。体裁沿 PR1/PR4-PR15。

## FP 内容面

- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Argent Assault**（规则 Dauntless Champions：PALADIN 近战 S<T→致伤+1；增强 Psychic
    Celerity 冲锋骰+1 / Vigilance of Titan 侦测+6"；战略 Truesilver Aegis 对致命伤 FNP4+ /
    A Threat Ended 近战 [PRECISION] / Aura of Vengeance 敌近战 [HAZARDOUS]）
  - **Fires of Purgation**（规则 Searing Soulflame：被钉住敌战栗-1；增强 Precognicient
    Volleys 快速射击5+ / Boons of Deimos 远程 +2 S；战略 Soul-Locked 撤退仍可射 /
    Focused Immolation 远程 [DEV]+[SUSTAINED] / Spiritsear D3+1 致命伤）
  - **Immaterial Interdiction**（规则 Echojump：射击后涌动 D6+1"；增强 Predestined
    Coordinates 首回合切入 / Astral Overlap Stealth；战略 Blades from the Beyond 近战
    [LANCE] / By Thought Alone 动作后仍可射 / Responsive Displacement 普通移动 D3+3"）
  - A/B 已确认 3 分队规则名/战略名在库 0 命中（真全新，Wahapedia 无源）
- **1 个重印分队**：**Warpbane Task Force**（规则 Hallowed Ground + 4 增强 + 6 战略）——
  DB 已收录（id 000009776/000009777*/000009778*），逐字一致**免补**（Wahapedia 已滚入）
- **7 个 codex 分队**（Void Purge Force/Baneslayer Strike/Banishers/Brotherhood Strike/
  Hallowed Conclave/Sanctic Spearhead/Augurium Task Force）——DB 已收录，FP 未复述其全文，
  仅经 Rules Updates 定点勘误（见下）
- **Datasheets**（Grey Knights Thunderhawk Gunship / Dreadnought / Relic Razorback /
  Brother-Captain Stern / Kaldor Draigo / Servitors + Imperial Armour/Legends）——均已在库，
  reprint 免补
- **Rules Updates**（p.9）：见 A/B 判定

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，1 条）

| 行 | 判定 | 说明 |
|---|---|---|
| enhancements 000010352002 Eye of the Augurium（Hallowed Conclave） | drifted | p.9 "Change to:"：旧「每战轮 Fire Overwatch/Heroic Intervention 0CP、可越用例」→ 11 版「Heroic Intervention 无视本阶段其他用例、-1CP、不阻其他单位使用」（取库现 description 为 from 精确替换） |

### datasheet 数值漂移（fp_errata stat_patches，3 条）

| 行 | 判定 | 说明 |
|---|---|---|
| models 000000398 Stormraven Gunship（m） | drifted | p.9：**M `20+"` → `14"`**（同段去 AIRCRAFT 关键词——观察项） |
| models 000001363 Stormhawk Interceptor（m） | drifted | p.9：**M `20+"` → `'-'`**（同兽人 4 飞机先例，去 Hover——观察项） |
| models 000001364 Stormtalon Gunship（m） | drifted | p.9：**M `20+"` → `'-'`**（去 Hover——观察项） |

**观察项（不落库，datasheet 关键词/技能 RAG 层次要，非 DSL 阻塞，留后续）**：
① Combat Manifestation（Brotherhood Strike）效果段 `3"→6"`——**库现已是 6"**（Wahapedia 已滚入），
免补；② Stormtalon/Stormhawk 去 Hover、Stormraven 去 AIRCRAFT、Brotherhood Chaplain 加 Leader、
Land Raider×3/Razorback/Rhino/Stormhawk/Stormraven/Stormtalon 加 FRAME 关键词——关键词层只增删
不改数值，同兽人 FRAME×8 先例记观察；③ Stormtalon/Stormhawk OC→'-'——全库无-OC 一律存 '0'
（引擎不消费 OC，功能等价保留，同兽人先例，非阻塞）；④ Brotherhood Techmarine Guardians of
the Machine 技能改写——datasheet ability 层，本 PR 未逐条落，记观察。

### 已滚入/已满足免补（identical）

- **Warpbane Task Force 全套**（规则 Hallowed Ground + 4 增强 + 6 战略）——库现逐字一致
- **6 datasheets + Imperial Armour/Legends**——均已在库
- Combat Manifestation 3"→6"——库现已 6"

### removed_11e：零（无分队被 FP 移除，重印无删减）

### fp_new（inserts 18 条）

3 分队 ×（1 rule + 2 enhancements + 3 stratagems），synthetic id `fp11e-gk-{argent,fires,immaterial}`。
cost 置空（FP 不含点数，MFM 缓存无该增强数据，诚实置空）。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Argent Assault | fp11e-gk-argent | Dauntless Champions | Psychic Celerity / Vigilance of Titan | Truesilver Aegis / A Threat Ended / Aura of Vengeance |
| Fires of Purgation | fp11e-gk-fires | Searing Soulflame | Precognicient Volleys / Boons of Deimos | Soul-Locked / Focused Immolation / Spiritsear |
| Immaterial Interdiction | fp11e-gk-immaterial | Echojump | Predestined Coordinates / Astral Overlap | Blades from the Beyond / By Thought Alone / Responsive Displacement |

## DSL 编码盘面（greyknights.json）

**98 项**（11 分队规则 + 53 战略 + 34 增强，含 inserts）全量逐条编码。
灰骑士为灵能/传送/精英近战阵营，可编率中等：**14 encoded / 10 partial / 74 not_modeled**。
零新引擎通道（延续纯编码 PR 序列）。

### encoded（14）——落既有通道且无残量

| 类 | 条目 | 通道 |
|---|---|---|
| 战略 | APPOINTED HOUR | hit crit_threshold 5（命中5+暴击，双阶段） |
| 战略 | FOREWARNED EVASION | 守方 hit modify -1（射击+战斗均适用） |
| 战略 | ARMOURED AEGIS（Baneslayer） | 守方 fnp 4 |
| 战略 | PSYBOLT AMMUNITION | save ap_improve 1（weapon_filter=storm bolter） |
| 战略 | SHINING VEIL | 守方 save cover（Stealth，phase_shooting） |
| 战略 | GIANTS OF THE BATTLEFIELD | attacks modify +1（phase_melee） |
| 战略 | Focused Immolation（fp） | wound mortal_pool（[DEV]）+ hit extra_hits 1（[SUSTAINED]），phase_shooting |
| 战略 | Blades from the Beyond（fp） | wound modify +1（[LANCE]，melee_charging） |
| 增强 | Shield of Admonishment | 守方 hit modify -1（phase_melee） |
| 增强 | The Sixty-sixth Seal | save ap_improve 1（phase_shooting） |
| 增强 | Sanctic Reaper | attacks modify +3（phase_melee） |
| 增强 | Phial of the Abyss | 守方 save cover（Stealth，phase_shooting） |
| 增强 | Boons of Deimos（fp） | wound s_improve +2（远程，phase_shooting） |
| 增强 | Astral Overlap（fp） | 守方 save cover（Stealth，phase_shooting） |

### partial（10）——可编子集落 effects，残量逐条注记

| 条目 | 已编 | 未建模残量 |
|---|---|---|
| AGGRESSIVE ANTICIPATION | hit ignore_hit_mods（忽略命中/BS 负修正） | 忽略正修正无收益不建模 |
| PURGATION PATTERN | hit extra_hits 1（[SUSTAINED]，phase_shooting） | 深入奇袭登场前提（假设） |
| POINT-BLANK PURGATION | wound reroll（storm bolter [TWIN-LINKED]） | [PISTOL]（接战中射击）无载体 |
| ABOMINUS-CLASS TARGETS | wound modify +1（对 MONSTER/VEHICLE 各一条） | 二关键字 OR，同具双关键字目标会双计（现实近乎不存在） |
| SANCTIFIED SLAUGHTER | hit extra_hits 1（[SUSTAINED]，melee_charging） | 「已有 SUSTAINED 则改暴击5+」条件升级无载体 |
| SANCTIFIED KILL ZONE | wound reroll（假设净化者=完整重投） | 非净化者仅重投1、圣化之地区域态假设 |
| AEGIS ETERNAL | 守方 save invuln 4（phase_shooting） | 圣化之地区域态假设 |
| Grimoire of Conjunctions | wound s_improve +4（近战） | 每场一次触发时机假设 |
| Shield of Prophecy | 守方 wound t_improve +2 | 每战轮一次触发时机假设 |
| Spiritus Machina | wound reroll（射击，开关 disembarked_this_turn） | 下车前提由开关声明 |

### not_modeled（74）——宁漏不错编，防高估

- **严格 S<T（无精确载体）**：Dauntless Champions（引擎仅 melee_s_lte_t(S≤T)，S=T 边界过度施加）
- **射击限定 S>T（无射击门控 tag）**：SHINING RESOLVE（wound_s_gt_t 无阶段门，裸挂近战误放行，
  同兽人「刀枪不入」/PR13「闪避协议」先例）
- **[PSYCHIC] 关键词武器筛选（非名字子串不可选）**：Channelled Force、Truesilver Channelling
- **仅致命伤/仅伤害1 FNP（无法条件化）**：TRUESILVER WILL、Truesilver Aegis、WARDING CHANT
- **重投1（非重投失败）**：Hallowed Ground、Fury of Titan、Sigil of the Hunt
- **ANTI-X / [PRECISION] / 每次致伤+1致命伤（非暴击转化）**：CHAOS BANE、A Threat Ended、
  Radiant Champion
- **致命伤爆发/治疗/移动/深入奇袭/预备队/战栗/冲锋骰/CP/OC/侦测/守望/动作**：其余大量条目
  （灵能/传送阵营主体机制）

## 结论

DB 11 版对齐：1 text_patch（Eye of the Augurium）+ 3 stat_patch（3 飞机 M）+ 18 fp_new inserts，
零 removed_11e。DSL 98 条全量三态编码（14/10/74），零新引擎通道。全库 1213 测试绿，
投影三态对账 encoded 103 / partial 269 / not_modeled 907（GK +14/+10/+74）。
