# P7-PR20 Space Marines（通用星际战士 Codex 分队）逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Space-Marines/`（Faction Pack VERSION 1.0，Legal from
2026-06-20，"first iteration … all new"）vs `db/wh40k.sqlite`（faction='SM'，星际战士战团/
亚阵营混存——DA/BA/BT/DW 已各自成 PR，本 PR 只做通用 Codex Space Marines 分队）。体裁沿 PR1/PR4-PR19。

## FP 内容面

Space Marines FP 目录（page_001.md）列 **15 个分队**（p2-27），均挂 faction='SM'：

- **13 个现有分队**（DB 已收录，Wahapedia 已滚更，容器名取自 stratagems.detachment）：

  | 分队容器 | 军规（name_en / DB id） | 气质 |
  |---|---|---|
  | Librarius Conclave | Psychic Disciplines（000009784） | 灵能领域 |
  | Armoured Speartip | Rapid Deployment（000010777） | 装甲运输/下车 |
  | Headhunter Task Force | Target Sighted（000010782） | Tank Ace 载具 |
  | Ceramite Sentinels | Adaptive Defence（000010758） | 攻城防御/地形 |
  | Blade of Ultramar | Mastered Doctrines（000010632） | 极限战士/战斗教条 |
  | Hammer of Avernii | Calculated Annihilation（000010620）+ Recalculating（000010621） | 钢铁之手/誓约 |
  | Spearpoint Task Force | Storm-swift Onslaught（000010626）+ Wrath of the First Khan（000010627） | 白色伤疤/机动 |
  | Forgefather’s Seekers | Vulkan’s Quest（000010367） | 火蜥蜴/近距火力 |
  | Emperor’s Shield | Wrath of Dorn（000010459） | 帝国之拳一连/誓约 |
  | Shadowmark Talon | Masters of Shadow（000010463）+ Unparalleled Tactician（000010464） | 暗鸦守卫/潜行 |
  | Bastion Task Force | Interlocking Tactics（000010675） | 联合兵种/auspex |
  | Orbital Assault Force | Rapid-drop Deployment（000010679） | 轨道空降/预备队 |
  | Reclamation Force | Oath of Reclamation（000010683） | 极限战士/目标点 |

  双规则分队（Hammer/Spearpoint/Shadowmark）各有 2 条命名分队规则行，均物化。
  纯编成 RESTRICTIONS 行（000010465/622/628 等，"军队仅含某战团"）为组军约束，
  未单列 abilities（不影响 stratagems/enhancements 对账）。

- **2 个全新迷你分队**（inserts，各 1 规则 + 2 增强 + 3 战略，id 前缀 `fp11e-spacemarines-`）：
  - **Fulguris Task Force**（规则 Skystrike：SPEEDER 关键词 + ingress；增强 Bellicose Weapon
    Spirits / Raptorial Cogitator Core；战略 Data-Link Augury / Reactive Evasion / Anti-Grav Surge）
  - **Subversion Assets**（规则 Nowhere to Hide：PHOBOS/SCOUT 标记 detected；增强 Shroud Field /
    Death in the Dark；战略 Adaptive Operations / Strike from the Shadows / Cloaked Position）
  - A/B 已确认二分队规则名/战略名/增强名在库 0 命中（真全新，Wahapedia 无源）

## A/B 判定汇总

### 真漂移已补：零 text_patches

13 现有分队的分队规则、战略、增强文本与 11 版 FP 逐字一致——Wahapedia 已滚入，**全部免补**。
分队规则 rule_text 逐条核对（FP p3-28 vs DB detachments.rule_text）全 identical；
Librarius Conclave 的 FP page_003.md 系不完整 refine（仅录军规 + 增强清单，漏战略正文），
DB（Wahapedia）为完整 11 版内容——以 **DB 为真源**（CLAUDE.md「先查库，Wahapedia 常已滚更」）。

### removed_11e：零

### fp_new（inserts 13 条）

| 类型 | id | 说明 |
|---|---|---|
| 2 新分队 × (1 规则 + 2 增强 + 3 战略) = 12 | `fp11e-spacemarines-fulguris*` / `fp11e-spacemarines-subversion*` | cost 置空（FP 不含点数） |
| Bastion 漏录战略 Angels Defiant | `fp11e-spacemarines-bastion-s6` | DB Bastion 战略 id 序 002-005,007 缺 006（Angels Defiant，守方 S>T -1 致伤），FP p24 有——synthetic id 补回（守 fp11e- 前缀不变式，非占原 006 数字位） |

### fp_errata（datasheet 数值）：零（本 PR 未落）

**观察项（不落库，datasheet 层次要，非 DSL 阻塞）**：FP Datasheets 段（p29-56）+ Imperial
Armour（p57）+ Rules Updates（p61-64）+ Legends（p65+）含大量兵牌新增/改写（Marneus Calgar in
Armour of Antilochus / Captain Titus / Vulkan He’stan / Aethon Shaan / Suboden Khan / Darnath
Lysander 等新 datasheet，Terminator Assault Squad / Land Speeder / Drop Pod 等重印）——均属
datasheet ability/数值层，本 PR（分队层 DSL）未逐条落，记观察留后续。Librarius Conclave FP p3
所列增强 Temporal Corridor 在 DB 4 增强中无对应行（DB=Prescience/Celerity/Obfuscation/Fusillade），
系 refine 不完整或 FP/Wahapedia 增强清单差异，以 DB 为准（不臆造插行），记观察。

## DSL 编码盘面（spacemarines.json）

**158 项**（18 分队规则 + 84 战略 + 56 增强，含 inserts）全量逐条编码：
**0 encoded / 44 partial / 114 not_modeled**。零新引擎通道、零新态势开关（沿 PR9-19 约定）。
SM 通用分队气质=移动资格/目标点/战斗教条/预备队/重骰1/auspex 标记多，可编率低（44/158 ≈ 28%）。

### 可编（44 partial）盘面

- **守方向 AP 恶化（傲慢之甲）×10**：Librarius/Armoured Speartip/Headhunter/Ceramite/Blade/
  Hammer/Spearpoint/Forgefather/Emperor’s Shield/Shadowmark 各 1（save ap_improve -1，两相位，side=target）
- **守方向 -1 致伤（S>T）×3**：Angels Defiant（Bastion 补录，wound_s_gt_t 两相位）、Malodraxian
  Standard（Emperor 增强，defender_bearer_leading）、Fiery Shield（Librarius，实为 -1 命中，见下）
- **守方向 -1 命中/致伤（射击门）×4**：Evasive Manoeuvres（Spearpoint，-1 命中+-1 致伤射击门）、
  Umbral Raptor / Shroud Field（Stealth=射击门 -1 命中，defender_bearer_leading）、Blind Screen（-1 命中+掩体射击门）
- **守方向 -1 命中（近战门）×1**：Fiery Shield（Librarius，WHEN=战斗阶段，phase_melee 门）
- **守方向 FNP/无效保护/减伤 ×6**：Armour of Antoninus（FNP 5+）、Redoubtable Machine Spirit
  （invuln 5+）、Seals of Reconquest（invuln 5+，单位）、Adamantine Mantle / Augmetic Fortitude
  （damage_reduction 1）——均 defender_bearer_leading 或分队战略无 bearer
- **攻方近战特征值 ×N**：Oath of Macragge（A+1/S+1）、Spiritus Ferrum / Champion of the Feast /
  Spiritus…（A+1）、Spearpoint Paragon（S+1/AP+1）、War-tempered Artifice（S+3）、Blades of Valour
  （AP+1）、Iron Arm（S+1 战略）、Courage and Honour（[LANCE]=melee_charging 致伤+1）、
  Furious Dedication（A+1）——均 phase_melee，多数 bearer_leading，教条/冲锋升级分支不编
- **攻方 [LETHAL HITS]/[SUSTAINED HITS 1]/[无视掩体]（射击门）×N**：Prescient Precision
  （LETHAL 射击门）、Firestorm Coordinators / Veteran of Behemoth / Hunter’s Eye / Shock Deployment
  （SUSTAINED 射击门，多数 bearer_leading，Shock Deployment 加 disembarked_this_turn 门）、
  Spy-skull Data Link / Exemplary Vigilance / Disciplined Extermination / Raptorial Cogitator Core
  （IGNORES COVER 射击门；Disciplined Extermination 另编远程 AP+1）
- **攻方命中 +1（两相位，不挂门）×2**：Ruthless Butchery / Fury of the First（WHEN=射击或战斗，
  两相位均可，故 condition 留空；本单位低于起始编制的致伤分支无载体不编）
- **攻方射击特征值（12" 内 +1 S）×1**：Vulkan’s Quest 军规（ranged_within_12 自含射击门）
- **攻方射击 +1 命中（射击门）×1**：Purgation Doctrine（下车致伤分支不编）

### 未建模（114 not_modeled）——防高估要点（同 PR9-19 复发坑）

- **移动/资格域**（撤退/加速后射击冲锋、ingress、D3+3"/D6" 反应移动、pile in/consolidate、穿越地形、
  disembark 移动）——SM 通用分队最大占比
- **目标点/OC/CP 域**（持续控制目标点、+1 OC、Bombast/Eye CP 回收、Oath of Reclamation 目标点范围门）
- **战斗教条/灵能领域状态机**（Mastered Doctrines/Student of Codex/Veteran 教条分支、Psychic
  Disciplines 五领域、各战略「若某教条/领域激活」分支）——选择状态机无引擎载体
- **预备队/部署/复活域**（Deep Strike、战略预备队、redeploy、Scouts、死后一击、2+ 复活）
- **士气/领导力/标记域**（战斗震慑测验、suppressed/pinned、auspex scanned 标记状态）
- **重骰-1 无载体**（Codex Discipline/Kill Shot/Wrath of Dorn/Interlocking 重投命中或致伤 1）
- **一次性二选一单分支**（Augmented Targeting/Cogitated Ferocity/Light of Vengeance/Auto-Sense
  Coordination/Spear Thrust and Sabre Swing：[LETHAL] 或 [SUSTAINED] 玩家选一）
- **关键词门无载体**：Target Weak Point/Kill Shot/Priority Strike（Monster/Vehicle/Character 二三选
  OR 门）、Tactical Decapitation（对 Character +1 命中）——引擎只能表达「具备单关键词」，裸编过度施加
- **Torrent/[PRECISION] 武器关键词非名字子串**：Immolation Protocols/Immolator（Torrent）、
  Lay Low the Tyrants/Eye of the Primarch（PRECISION）——weapon_filter 名字过滤无法选取
- **远程「超 12"」距离门无载体**：Masters of Shadow 军规、Stunning Fusillade（引擎无「攻击者/目标
  超 12"」的守方/攻方远程距离 tag，裸编近距离过度施加）
- **S≥T 非严格无等价 tag**：Tactical Foresight（原文 S≥T，引擎 wound_s_gt_t 仅 S>T，漏 S=T 档不等价，不编）
- **攻方本单位低于起始编制状态无载体**：Ruthless Butchery/Fury of the First 致伤分支（target_below_*
  读守方战损，非攻方本单位）
- **空间「最近目标 6" 内」/固定致命伤池/单骰操纵/mortal 爆发**：Crucible of Battle、Assail（6D6）、
  Forged in Battle（改骰为 6）、Sensory Assault
- **[ANTI-MONSTER/VEHICLE 5+] 关键词条件暴击**：Fusillade（ANTI 关键词门无载体）
- **侦测/隐蔽/hidden 状态域**：Fulguris/Subversion 各战略与 Death in the Dark（目标 hidden 门）

## 验证

- `pytest tests/ -q`：**1267 passed**（含 test_simulator_dsl_pr20_payload.py 新断言、
  test_db_compile_dsl_apply 计数 1522、test_db_compile_fp_rules inserts 219、pr4 投影三态对账）
- `db_compile fp-rules`：inserts 应用 13（2 新分队 + Bastion Angels Defiant 补回）
- `db_compile dsl-apply`：应用 158 / 指纹让路 0 / 三态 encoded 103 / partial 339 / not_modeled 1080（累计）
- 基准 gold v3（agent 路径）：accuracy **99.0**（correct 95 / partial 1 / wrong 0 / total 96，
  **零硬错**），见 `benchmarks/v3_edition11/qa_agent_results_p7pr20.json`（纯编码 PR——DSL/DB 补丁
  不进 FAISS 检索语料，检索侧零影响，与历史 99.0 基线一致）
- 自审（code-reviewer 子代理）：见「自审修复」节
