# P7-PR24 钢铁联盟（Leagues Of Votann）逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Leagues Of Votann/`（11 版 Faction Pack，Legal from
2026-06-20）vs `db/wh40k.sqlite`（faction='LoV'）。体裁沿 PR1/PR4-PR23。分两迭代：
迭代 1 = DB 11 版对齐（fp_rules），本迭代 = 全量 DSL 编码 + 基准 + 自审 + 本工作单。

## FP 内容面（迭代 1 已落）

- **3 个全新分队**（fp_new inserts，各 1 规则 + 2 增强 + 3 战略 = 18 条），synthetic id
  `fp11e-votann-{trailblazers,farseekers,hearthguard}`，cost 置空：
  - **Armoured Trailblazers**（规则 Sagitaur Spearhead：SAGITAUR Scouts 6" + 增强
    Saturation Rounds（远程 [IGNORES COVER]）/Optimised Attack Lines（MOBILE）+ 战略
    Coordinated Crossfire（重骰 1）/Outflanking Armour（预备队 ingress）/Built to Last
    （远程 S>T 被伤 -1））
  - **Farseekers**（规则 Eye of the Hunt：HERNKYN 12" 内远程 +1 命中 + 增强 Pan-Spectral
    Lockons/Shroudwërke Talismans（侦测范围）+ 战略 Scornful Analysis（[IGNORES COVER]）/
    No Shot Wasted（[LETHAL HITS]）/Economy of Motion（移动））
  - **Hearthguard Covenant**（规则 Avatars of the Ancestors：KÂHL/EINHYR 系 9" 内远程重骰
    致伤 1 + 增强 High Kâhl/Ironskein（复用 Hearthband 名，dedup 键含 detachment 无冲突）+
    战略 BRËKKEKNOTS（invuln4）/Fury of the Hearth（+1S）/Materialisation Matrices（深部署））
  - A/B 已确认三分队规则名/战略名在库 0 命中（真全新，Wahapedia 未滚入）
- **9 个已收录分队**：Void Salvagers / Hearthfire Strike / Hearthband / Needgaârd /
  Persecution / Dêlve Assault Shift / Brandfast / Hearthfyre Arsenal / Mercenary——
  DB 已由 Wahapedia 滚入，逐字一致或仅几何/触发漂移

## A/B 判定汇总（迭代 1）

### 真漂移已补（fp_rules text_patches，2 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010448002 SECURE POSITIONS（Brandfast） | drifted | WHEN 增补 `if units from your army have Hostile Acquisition` 前置从句 |
| stratagems 000010440006 CLAIMSTAKER REFLEX（Persecution） | drifted | TARGET `within 9"` → **`8"`**（几何漂移，本 payload not_modeled） |

### removed_11e：零

### fp_new（inserts 18 条）

见上「FP 内容面」——det=N/enh=N+1/strat=N+2 consecutive-block 映射，容器名 ↔ 规则名
经 enhancements.detachment_name 桥接落定。

## DSL 编码盘面（votann.json）

**109 项**（12 分队规则 + 59 战略 + 38 增强，含 inserts）全量逐条编码。零新引擎通道、
零新态势开关、零新 condition tag——纯编码 PR（沿 PR9-23 约定）。

**三态：6 encoded / 13 partial / 90 not_modeled（21 带效果 ≈ 19%）。**

钢铁联盟为矮人耐战/精准射击阵营，气质=YP（Yugana Points）经济、誓言（Hostile
Acquisition⇄Fortify Takeover）、审判标记（Judgement token）、assailed·pinned·suppressed
状态门、预备队、移动、据点——故可编率低。

### encoded（6）

| id | 名 | 编码 |
|---|---|---|
| 000009538002 | 织焰照明弹 WEAVEFIELD FLARE | 守方 被伤 -1（wound_s_gt_t，两相位） |
| 000009824002 | 护盾结界 BRËKKEKNOTS（Hearthband） | 守方 invuln 4 |
| 000009538003 | 全谱视觉仪 PAN-SPECTRAL VISUALISER | 远程 [IGNORES COVER] + 无视命中修正 |
| fp11e-votann-farseekers-s1 | 轻蔑剖析 SCORNFUL ANALYSIS | 远程 [IGNORES COVER] |
| fp11e-votann-farseekers-s2 | 弹无虚发 NO SHOT WASTED | 远程 [LETHAL HITS] |
| fp11e-votann-hearthguard-s1 | 护盾结界 BRËKKEKNOTS（Hearthguard） | 守方 invuln 4 |

### partial（13，编可建模子集 + 逐条注残量）

| id | 名 | 编 | 残量 |
|---|---|---|---|
| 000009538005 | 重能脉冲 GRAVITRONIC PULSE | 守方近战反击命中 -1（phase_melee） | 先攻剥夺 / 冲锋触发门 |
| 000009824007 | 炉火之怒 FURY OF THE HEARTH（Hb） | 远程 +1 S | YP→[SUSTAINED HITS 1] |
| 000009823003 | 震荡多重发生器 Quake Multigenerator | 守方来袭命中 -1（两相位） | 射击触发门 / TITANIC 排除 |
| 000010436002 | 虚空硬化 VOID HARDENED | 守方 被攻 AP 恶化 1（两相位） | Fortify Takeover 誓言前置假设 |
| 000010436003 | 坚守荣誉 HONOUR OF THE HOLD | 近战 AP +1（phase_melee） | YP→AP +2 |
| 000010436005 | 先祖裁决 ANCESTRAL SENTENCE | 远程 [SUSTAINED HITS 1] | YP→[SUSTAINED HITS 2] |
| 000010440007 | 分散阵型 DISPERSED FORMATION | 守方匿踪 远程命中 -1 | 掩体加成（避免与匿踪双重叠加不叠编） |
| 000010444006 | 织能扶壁 WEAVEWËRKE BUTTRESS | 守方 被伤 -1（仅射击相位） | Hostile Acquisition 誓言前置假设 |
| 000010447003 | 特里瓦格电子植入体 Trivärg | 下车回合 远程 [SUSTAINED HITS 2] | YP 替代触发分支 |
| 000010452002 | 毫厘不爽 UNWAVERING ACCURACY | 无视命中修正 | 无视致伤/AP 修正无通道 |
| fp11e-votann-trailblazers-e1 | 饱和弹幕 Saturation Rounds | 远程 [IGNORES COVER] | SAGITAUR 关键字假设 |
| fp11e-votann-farseekers | 远索者 Eye of the Hunt（分队规则） | 12" 内远程 +1 命中 | HERNKYN 关键字假设 |
| fp11e-votann-hearthguard-s2 | 炉火之怒 FURY OF THE HEARTH（Hg） | 远程 +1 S | YP→[SUSTAINED HITS 1] |

### not_modeled（90）— 无载体归类

- **重骰 1**（≠重骰失败，引擎无载体）：Methodical Annihilation / HUNTR'S MARK /
  ILLUMINATED PRIORITY / Coordinated Crossfire / Avatars of the Ancestors / Oathband
  系多条 OPTIMAL EXPENDITURE·PRIVATEER ARSENAL·CYBERSTIMM 等
- **YP（Yugana Points）经济**：增伤/SH 升级/复活/据点换 CP，均资源门无载体
- **状态门无载体**：assailed（EXPOSED FLAWS / Eye for Weakness）、pinned、suppressed
  限 MONSTER/VEHICLE（Graviton Vault——守方无攻击者关键字 tag）、Judgement token
  （JUDGED AND PUNISHED / Obsessive Drive）
- **负关键字门**（排除 MONSTERS/VEHICLES）：Guerrilla Adepts / DELAYED-FIRE ROUNDS /
  WALL OF STEEL——引擎只表达「有关键字」，裸编过度施加
- **双关键字析取**：SUPERIOR CRAFTSMANSHIP（+1 伤害 vs MONSTER **或** VEHICLE）无单一复合 tag
- **限远程×S>T**：Built to Last——无 shooting_wound_s_gt_t 复合 tag，裸 wound_s_gt_t 会
  在近战误放行（对照 WEAVEFIELD FLARE 两相位可用 = 正确编码）
- **关键字授予无战斗数值**：[PISTOL]（Point-Blank Fire）/[PRECISION]（Auxiliary
  Contract）/[DEVASTATING WOUNDS]、MOBILE、BATTLELINE、深入部署
- **三选一自由改选**：Masterful Construction（每相位改选 [DEV]/[LETHAL]/[SH1]）——编入任一即代玩家选择
- **W 特征值提升**：Ironskein（+2W）×2——引擎无 W 提升通道
- **光环定位门**：Firebase Control（火力基地 [SUSTAINED HITS 1]，需在 TRANSPORT 6" 内）/
  Quake Supervisor（炮兵 3" 内）——分队规则自动施加会对所有单位过度施加
- **誓言态**（Hostile Acquisition⇄Fortify Takeover 切换）/**CP**/**预备队**/**侦测范围**/
  **据点 OC**/**移动·地形·过守火**域——非战斗链

## 门禁

- `.venv\Scripts\python.exe -m pytest tests/ -q` → **1338 passed**（+24 新 pr24 payload 测试）
- `python -m db_compile dsl-apply` → 应用/幂等 1779、**指纹让路 0**、跳过 0
- 基准 gold v3 = 见 VERIFIED 标记（DSL/DB 补丁不进 FAISS 检索语料，检索侧零影响）
- code-reviewer 自审 → CRITICAL/HIGH 清零（详见提交说明）
