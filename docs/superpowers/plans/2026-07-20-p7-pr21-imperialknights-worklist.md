# P7-PR21 帝国骑士 fp_rules + DSL 逐条 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Imperial Knights/`（27 页，VERSION 1.0，Legal from
2026-06-20，"first iteration … all new"）vs `db/wh40k.sqlite`（faction='QI'）。体裁沿
PR1/PR4-PR20。

## FP 内容面

- **4 个分队**：
  - **Dominus Foebreakers**（规则 Rain of Devastation：DOMINUS 攻击地形区域内目标命中+1 +
    增强 Blessed Plate（+1 T）/Archeotech Autoloaders（重投武器 A 骰）+ 战略 Ground-Shaking
    Strides（+2" M）/Foebreaker Firestorm（[BLAST] 去 BLAST + A+1）/Fire Shocked（战栗-1））
    ——**库 0 命中，真全新** → fp_new inserts。
  - **Throne-bonded Outriders**（规则 Driven From Their Lairs：受 Bondsman 影响的 ARMIGER
    远程 [IGNORES COVER] + 增强 Gyro-optimised Actuators（MOBILE）/Ancestral Overbleed
    （守望/英勇介入 -1CP）+ 战略 Neural Lash（解战栗）/Helm Conditioning（Bondsman 18"）/
    Honoured to Serve（射击不阻行动））——**库 0 命中，真全新** → fp_new inserts。
  - **Questor Forgepact**（Cogbound Alliance）——DB 已收录完整分队（1 规则 + 6 战略 + 4 增强）。
  - **Freeblade Company**（Knights of Legend）——DB 已收录完整分队，逐字一致**免补**。
- **Datasheets**：Knight Destrier（新）+ Imperial Armour（Acastus Asterius/Porphyrion、
  Cerastus Lancer/Castigator/Acheron/Atrapos、Questoris Magaera/Styrix、Armiger Moirax）
  ——datasheet/兵牌层，非本 PR 范围（DSL 只编分队规则 + 战略 + 增强）。
- **Rules Updates**（p26-27）+ FAQ。

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，1 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010494006 TACTICAL FOIL（Valourstrike Lance） | drifted | Rules Updates 明列 Target 段 9"→8"；库现 9"，取库现 text_zh 精确 .replace 保留 HTML |

### 已滚入/已满足免补（identical）

- **Rules Updates 其余**逐项核对库现已逐字 11 版：
  - **Bold Gallantry**（Valourstrike Lance 规则）：库现 000010492 = FP change-to 全文一致。
  - **Run Them Through! Target**：库现 000010494002 = "…not been selected to fight this phase"。
  - **Full Tilt Target**（Valourstrike Lance）：库现 000010494004 = "…not been selected to move…"。
  - **OC → 10**：Canis Rex / Knight Castellan / Crusader / Defender / Errant / Gallant /
    Paladin / Preceptor / Valiant / Warden **十骑士库现 OC 均已 '10'**（models 表核对），免补。
- **Questor Forgepact / Freeblade Company** 两现有分队 DB 已收录，Freeblade Company 逐字一致。

### removed_11e：零

### fp_new（inserts 12 条）

2 全新分队各 1 规则 + 2 增强 + 3 战略，synthetic id `fp11e-imperialknights-dominus-*` /
`fp11e-imperialknights-throne-*`。增强 cost 置空（FP/MFM 均无源，诚实置 NULL）。

| 分队 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|
| Dominus Foebreakers | Rain of Devastation | Blessed Plate / Archeotech Autoloaders | Ground-Shaking Strides / Foebreaker Firestorm / Fire Shocked |
| Throne-bonded Outriders | Driven From Their Lairs | Gyro-optimised Actuators / Ancestral Overbleed | Neural Lash / Helm Conditioning / Honoured to Serve |

### 观察项（不落库，非本 PR 阻塞）

- **Questor Forgepact 分队差异**：FP p3 精炼文本呈现的 Cogbound Alliance（Assisted Targeting
  光环 + Sacristan Pledge 在 Tech-Priest + Mechanicus Allies 500 平点）与库现（Divine
  Inspiration + Forge World Allies 250/500/750 分档）措辞不同；且 FP p3 仅列 2 增强 + 3 战略
  （In the Shadow of Giants 等），而真实 40k 分队须 4 增强 + 6 战略，故 FP 精炼页为**不完整**捕获。
  Freeblade Company 库现与 FP 逐字一致（证 Wahapedia 已滚入 11 版 FP），据此裁定库现 Questor
  Forgepact 为权威完整 11 版态，不据不完整 FP 精炼页重写整分队（避免污染完整库、且 DB 补丁不入
  FAISS 检索、不影响检索）。差异记观察，留后续以干净原文核。
- **Datasheet 层**：Knight Destrier + 9 Imperial Armour 单位 datasheet 技能（Ram Jets /
  Thundercharge / Saturation Fire / Bondsman 各变体 / Storm of Bolts / Searing Flames /
  Macro-extinction / Grav-pinned / Damaged 段等）、Damaged 段整改（OC-5/命中-1）——datasheet
  技能层不落本 PR，记观察。
- **Towering / Frame 关键字**：沿 S4 裁定（Towering 测距词、Frame 只删不加），不落库。

## DSL 编码盘面（imperialknights.json）

79 项（9 分队规则 + 42 战略 + 28 增强，含 fp_new）全量逐条编码。帝国骑士为超重型步行机甲
（Vehicle/Titanic/Walker）阵营，气质=光环/移动/据点/预备队/Bondsman 从属/治疗/CP 经济，
**可编率低：0 encoded / 18 partial / 61 not_modeled**。零新引擎通道、零新态势开关。

### 可编子集（18 partial）

- **守方**：传奇骑士/英勇不退 FNP 6+（fnp）、圣所 invuln 5+、旋转离子盾 invuln 4+（射击门）、
  受祝甲板 T+1（t_improve）、破枪反制近战 S>T 致伤-1（melee_wound_s_gt_t）、以责为盾被射击
  AP 恶化1（save/ap_improve/-1，射击门）。
- **攻方**：贯穿！[LANCE]（wound/modify/+1，melee_charging）、复仇誓约 [LETHAL HITS]
  （hit/auto_wound，射击门）、巨神轰炸/银怒战旗 [SUSTAINED HITS 2]（hit/extra_hits/2，
  射击/近战门）、削减其众 [RAPID FIRE 1]（attacks/modify/+1，half_range）、勇气美德近战
  命中+1（phase_melee）、坚定优势近战重投命中（hit/reroll/fail，phase_melee）、机械专注无视
  命中骰减值（hit/ignore_hit_mods，两相位）、正义使者近战 A+2/命中+1（phase_melee）、猎手之眼
  [IGNORES COVER]（射击门）、雷霆践踏 Feet +1 AP（weapon_filter="feet"，phase_melee）。

### 阶段门纪律（防四度复发的 staged-WHEN HIGH）

- 射击授予的武器技能一律挂 `phase_shooting`/`half_range`（否则近战跑时泄漏到近战武器）；
  近战技能挂 `phase_melee`；[LANCE] 挂 `melee_charging`（仅冲锋回合致伤+1）。
- 反向：持续性守方 buff（FNP/invuln/T+1）与两相位效果（英勇不退射击或近战、傲慢式 AP、机械
  专注两相位）**不加相位门**（原文未要求，过度加门=欠建模亦是事实错误）。

### 防高估不编（61 not_modeled 主因）

- **位置/状态门无载体**：防线上（Dauntless Defenders/Drive Them Out/Gate Warden 三增强）、
  地形区域内（Rain of Devastation）、受 Bondsman 影响（Driven From Their Lairs/Spearhead
  四增强）——引擎只表达"有关键字"，裸编会过度施加。
- **重投1（非重投失败）**：神圣启示/Strength From Exile/Knight of Opus Machina/Purgation's
  Hand/Mentor's Pride——引擎重投语义仅"重投失败"。
- **仅致命伤 FNP**：Omnissiah's Grace（引擎伤害非致命伤来源）。
- **三关键词 OR**：Titanic Duel（MONSTER/TITANIC/WALKER，target_has_keyword 仅一关键词）。
- **射击×关键词无复合 tag**：Wyrmslayer Divination（对 FLY 重投）。
- **仅射击相位 S>T**：Survivor of Strife（wound_s_gt_t 无相位分量会波及近战、melee 变体相位相反）。
- **授予异模型**：Valourstrike Lance 四"Bearer of the …"增强（作用于所选另一 IK 模型）。
- **[ASSAULT]/[PRECISION]/移动/据点/战栗/预备队/CP/W/治疗/去 BLAST/设定攻击次数** 类无载体。

## 门禁

- `pytest tests/ -q`：**1288 passed**（新增 tests/test_simulator_dsl_pr21_payload.py 21 用例 +
  dsl_apply/fp_rules 计数更新）。
- `db_compile fp-rules`：文本应用 1 / 补录插行 12；`dsl-apply`：79 条投影零指纹让路
  （全库 encoded 103 / partial 357 / not_modeled 1141）。
- 基准 gold v3（agent 路径）：**96/96 correct，accuracy 100.0，零硬错**
  （benchmarks/v3_edition11/qa_agent_results_p7pr21.json；degraded_count 34 为软降级检索回退，
  非硬错，纯编码 PR 不触 FAISS、检索不变）。

## 自审（code-reviewer）结论

**APPROVE，0 CRITICAL / 0 HIGH / 2 MEDIUM**。核心排查目标 staged-WHEN 阶段门陷阱**未复发**：
18 条 partial 的射击/近战武器技能门、[LANCE] 的 melee_charging、持续性守方 buff 的"不加门"
全部正确。

- **MEDIUM #1（STEADFAST SUPERIORITY 000010498004 重投语义）**：审查者因 OCR 缓存无该页文本
  无法核实。据库现物化源核对——EFFECT 为 "you can **re-roll the Hit roll**"（整骰重投=重投失败），
  **非** "re-roll a Hit roll of 1"，故 `(hit, reroll, ["fail"])` 编码正确，无需改动（假警报）。
- **MEDIUM #2（THIN THEIR RANKS 000010507005 half_range 无相位分量）**：审查者明确此为**既有
  系统性引擎局限**（与已并 orks.json "Dead Shiny Shootas" id 000009991003 同模式），非本 PR 引入
  的回归；修复需注册 `shooting_half_range` 复合 tag=新引擎通道，超出零新通道纯编码 PR 范围，记
  观察留后续。CLI `--phase melee --half-range` 组合为理论泄漏路径，Web 前端仅在 shooting 置
  half_range 故主链安全。
