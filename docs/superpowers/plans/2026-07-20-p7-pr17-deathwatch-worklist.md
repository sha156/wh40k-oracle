# P7-PR17 死亡守望 fp_rules/fp_errata 逐行 A/B 工作单（2026-07-20）

对照源：`data_refined/Faction Pack Deathwatch/`（28 页，Legal from 2026-06-20，Version 1.0，
"first iteration … all new"）vs `db/wh40k.sqlite`。体裁沿 PR6/PR16。

## 阵营定位（关键）

死亡守望 11 版为 **ADEPTUS ASTARTES 战团**（FP 首句 "If your Army Faction is Adeptus Astartes,
you can use this Black Spear Task Force Detachment rule"），内容挂 **faction='SM'**、分队
**Black Spear Task Force**：

- 军规 **Kill Teams**（abilities id `000009792`，混编单位取多数 T）
- 分队规则 **Mission Tactics**（abilities/detachments id `000008521`，Furor/Malleus/Purgatus 三选一）
- 6 战略（`000008523002`–`007`，detachment='Black Spear Task Force'）
- 4 增强（`000008522002`–`005`，detachment_name='Black Spear Task Force'）

**旧十版 Agents of the Imperium（AoI）内容不在本阵营范围**：DB 的 `AoI` 阵营下 Ordo Xenos
Alien Hunters / Ordo Malleus / Ordo Hereticus / Imperialis Fleet / Interdiction Team /
Veiled Blade / Voidship's Company 等分队是审判庭（Inquisition）军队内容，FP 未触及，勿动。

## FP 内容面

- **1 个分队** Black Spear Task Force（军规 + 分队规则 + 6 战略 + 4 增强）——DB 已收录，
  逐字一致（Wahapedia 已滚入 11 版）
- **Datasheets**（Watch Master / Watch Captain Artemis / Deathwatch Veterans / Deathwatch
  Terminator Squad / Corvus Blackstar / Fortis / Indomitor / Spectrus / Talonstrike / Decimus
  Kill Team + Deathwatch Armoury 武器卡）——均已在库
- **无 Rules Updates 勘误页**（FP 为 Version 1.0 首版，全部"regarded as new"，无 "Change to" 段）

## A/B 判定汇总

### 真漂移已补：零（fp_rules text_patches 0 条 / fp_errata stat_patches 0 条）

DB 现值与 FP 11 版逐项一致，无补丁。

### 已滚入/已满足免补（identical）

| 类 | 行 | 判定 |
|---|---|---|
| 军规 | Kill Teams（000009792） | 库现文本 == FP 军规「混编 Kill Team 取多数 T」逐字一致 |
| 分队规则 | Mission Tactics（000008521） | Furor [SUSTAINED HITS 1] / Malleus [LETHAL HITS] / Purgatus 暴击→[精准] 逐字一致 |
| 战略 ×6 | ARMOUR OF CONTEMPT / ADAPTIVE TACTICS / HELLFIRE / KRAKEN / DRAGONFIRE / SITE-TO-SITE | 库现文本逐字一致（触发/目标/效果/限制段全对） |
| 增强 ×4 | Thief of Secrets / Osseus Key / Beacon Angelis / The Tome of Ectoclades | 库现 description 逐字一致 |
| datasheet 数值 | Watch Master M6 T4 Sv2+ W5 4++ / Artemis M6 T4 Sv3+ W4 4++ / Veterans T4 Sv3+ W2 / Terminators M5 T5 Sv2+ W3 4++ / Corvus M14 T10 Sv3+ W14 / Fortis T4 W2 / Indomitor T6 W3 / Spectrus T4 W2 / Talonstrike / Decimus | 库现 models 表全部与 FP 一致 |

**FP refined OCR 观察项（不影响判定）**：`page_010/011/018/026` 若干数据卡表格 refined 时字段
错位/两档互换（如 Talonstrike「重型/普通 Intercessor」T 值互换、Decimus「Gravis/Sergeant」互换、
Corvus 有一 legends 变体显示 M20+）——经与 `db/wh40k.sqlite` models 表 A/B，**DB 为真值**，
FP refined 表格系分栏解析错位，非真实漂移，免补。

### removed_11e：零（无分队/数据卡被 FP 移除）

### fp_new：零（无全新分队/数据卡——Black Spear 及全部 datasheet 均已在库，reprint 免补）

## DSL 编码盘面（deathwatch.json）

**12 项**（2 abilities[军规+分队规则] + 6 战略 + 4 增强）全量逐条编码。
死亡守望为 SM 战团，规则以任务战术选择 / 移动 / 部署 / 誓约 / 元规则为主，可编率低：
**0 encoded / 4 partial / 8 not_modeled**。**零新引擎通道、零新态势开关**（延续 PR9-16 约定）。

### partial（4）——可编子集落 effects，残量逐条注记

| 条目 | 侧 | 已编 | 未建模残量 |
|---|---|---|---|
| Thief of Secrets（增强） | 攻 | 近战 S+1 / D+1 / AP 改善1（phase_melee 门，requires bearer_leading） | 战斗内击杀后永久升 +2 为战局状态机无载体（仅编基础 +1）；限携带者模型附属整体注入会高估 |
| KRAKEN ROUNDS（战略） | 攻 | 射击远程武器 AP 改善1（phase_shooting 门） | 射程 +6 寸（几何域） |
| DRAGONFIRE ROUNDS（战略） | 攻 | 远程武器 [无视掩体]（phase_shooting 门） | [ASSAULT]（加速后仍可射）移动域 |
| ARMOUR OF CONTEMPT（战略） | 守 | 被攻 AP 恶化1（save ap_improve -1，condition 空=两相位） | 触发时机=选中目标后，点名即假设已用 |

**门控核对（双向）**：
- Thief / KRAKEN / DRAGONFIRE 均为「近战武器」或「远程武器」限定 → 分别挂 `phase_melee` /
  `phase_shooting` 门，防跨相位误施加（正向门控）。
- ARMOUR OF CONTEMPT 原文「射击或战斗阶段…被攻 AP 恶化」双相位适用 → **不加**相位门
  （condition 空），避免反向过度门控（PR13 反方向 MEDIUM 先例：原文没说要门就不加门）。

### not_modeled（8）——宁漏不错编，防高估

| 条目 | 原因 |
|---|---|
| Kill Teams（军规） | 混编单位取多数/最高 T——引擎守方单一 T，无载体；运输搭乘为部署域 |
| Mission Tactics（分队规则） | Furor/Malleus/Purgatus 三选一持续声明无开关载体（遵零新通道约定不新增开关），无条件编入任一会过度施加；Purgatus 暴击→[精准] 为攻击分配域 |
| ADAPTIVE TACTICS（战略） | 为单位单独指定任务战术——同依赖任务战术开关载体 |
| HELLFIRE ROUNDS（战略） | [ANTI-INFANTRY 2+]/[ANTI-MONSTER 5+] 为射击×目标关键词，无射击×关键词复合 tag（裸 target_has_keyword 近战误放行）；暴击致伤阈值下调仅配 [毁灭伤害] 时转伤 |
| SITE-TO-SITE TELEPORTATION（战略） | 撤出战场入预备队+授深入打击——预备队/部署/移动域 |
| Osseus Key（增强） | 敌载具领导力测验→命中-1/不能射击——领导力测验/条件分支/射击资格域 |
| Beacon Angelis（增强） | 深入打击+0CP快速切入——部署/预备队域 |
| The Tome of Ectoclades（增强） | 额外第二誓约目标——誓约为全局标记态+重投命中，P7 编码范围外 |

## 结论

DB 11 版对齐：**零漂移**（0 text_patch / 0 stat_patch / 0 fp_new / 0 removed_11e）——
Black Spear Task Force 全套规则/战略/增强 + 全部 datasheet 数值与 FP 逐项一致（Wahapedia 已滚入），
FP refined 的数据卡 OCR 错位经 A/B 确认 DB 为真值免补。DSL 12 条全量三态编码（0/4/8），
零新引擎通道、零新开关。全库 **1229 测试绿**，投影三态对账
**encoded 103 / partial 273 / not_modeled 915**（死亡守望 +0/+4/+8）。
