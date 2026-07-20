# P7-PR23 Imperial Agents（帝国代理）DSL 编码工作单

- 日期：2026-07-20
- 分支：`feat/p7-pr23-imperialagents`
- 阵营：Imperial Agents，DB `faction='AoI'`（factions.name = "Imperial Agents"）
- 真源：11 版 `data_refined/Faction Pack Imperial Agents/`（V1.0，2026-06-20 生效）+ `db/wh40k.sqlite`
- 产物：`dsl_payloads/imperialagents.json`（69 条）、`tests/test_simulator_dsl_pr23_payload.py`、
  `db_compile/fp_rules_patches.json`（+2 text_patches）、本工作单
- 性质：**零新引擎通道 · 零新态势开关 · 零 fp_new**（沿 PR9-22 约定）

---

## 一、FP 内容面（Faction Pack Imperial Agents 45 页）

| 页 | 内容 | 处理 |
|---|---|---|
| 1 | 版本/目录 | — |
| 2-3 | **新分队 Veiled Blade Elimination Force**（Extremis Sanction 军规 + 4 Extremis 能力 + 6 战略） | DB 已有（Wahapedia 滚入）→ **零 fp_new**，A/B 核对后编码 |
| 4-9 | 新数据卡 Inquisitor Kroyle / Aquila Kill Team / Sanctifiers | datasheet 层，不落本 PR |
| 10 | **Rules Updates**（详见二） | 2 text_patches + 若干免补/datasheet 观察项 |
| 11-44 | Legends 数据卡（Ostromandeus/UR-025/Neyam/Janus/Damned Legionnaires/终结者审判官/Karamazov/
  Eisenhorn/Kill Team Cassius/死望终结者/机车队/Proteus/Fortis/Indomitor/Spectrus/Daemonhost/Jokaero） | datasheet 层，不落本 PR |
| 45 | Deathwatch Armoury 武器表 + Kill Team 能力 | datasheet 层，不落本 PR |

阵营气质：审判庭（三大 Ordo）/ 刺客（Officio Assassinorum）/ 死亡守望 / 灰骑士 / 仲裁庭（Adeptus
Arbites）/ 虚空舰（Voidfarers）混编。核心机制=特工部署、预备队/深入打击、据点控制、战意测验、
具体目标声明——**可编率低**（19/69 带效果）。

---

## 二、A/B 判定汇总（DB ↔ 11 版 FP）

### text_patches（2，几何漂移，均不影响 DSL——两条目本 payload 皆 not_modeled）

| id | 条目 | 列 | 漂移 | 依据 |
|---|---|---|---|---|
| 000009127007 | RAPID TACTICAL RELOCATION（Ordo Xenos） | text_zh | `9"`→`8"` | page_010 Rules Updates → Alien Hunters |
| 000009134004 | Gift of the Prescient（Ordo Malleus） | description | `3"`→`6"` | page_010 Rules Updates → Daemon Hunters |

### 免补（库现文即 11 版逐字一致，Wahapedia 已滚入）

- **ARMOUR OF CONTEMPT**（000009127002）/ **TRUESILVER ARMOUR**（000009135005）：FP 改「worsen AP
  by 1」库现文已是该措辞 → 免补（DSL 侧照编 AP 恶化）。
- **Veiled Blade Elimination Force** 整分队（Extremis Sanction + 6 战略 + 4 增强）：DB 已有全部行 → 零 fp_new。

### 零 fp_new / 零 deactivations / 零 fp_errata

FP 唯一「新」分队已在库；无 FP 删除项；datasheet 数值改（见下）沿先例不落本 PR。

### datasheet 层观察项（沿死亡守望/圣血修女先例不落本 PR）

page_010 数据卡改：Corvus Blackstar M12"→14"/去 AIRCRAFT、加 FRAME 关键字（Corvus/Rhino/Chimera/
Immolator）、Callidus Acrobatic Escape 9"→8"、Culexus Etheric Emergence 重写、Imperial Rhino 运载改、
Inquisitor/Draxus Leader 去 DEATHWATCH KILL TEAM、Sisters Immolator invuln 去星号、Vindicare Dead Shot
重写、Voidsmen Navy Bodyguard 改、Ministorum Priest Leader→Support。**均为 datasheet 层，本 PR 不落**（观察项）。

---

## 三、DSL 编码盘面（69 = 4 encoded / 15 partial / 50 not_modeled）

表分布：abilities（分队规则物化）7 · stratagems 38 · enhancements 24。
守方向条目 10（7 带效果）。

### 分队规则（abilities，7）

| id | 规则 | 判定 | 编码 / 未建模主因 |
|---|---|---|---|
| det000009125 | Deathwatch Mission Tactics | not_modeled | 三选一任务战术持续声明无开关载体（零新通道） |
| det000009129 | Root out Heresy | **partial** | 远程 [IGNORES COVER]（phase_shooting）；SUSTAINED vs CHAOS≥5 无复合 tag 不编 |
| det000009133 | Destroy the Daemonic | not_modeled | 重骰命中 1 ≠ 重骰失败，无载体 |
| det000009137 | At all Costs | not_modeled | 二选一 + 具体目标/据点门 |
| det000009359 | Beseechment Codes | not_modeled | 舱门/移动交互域 |
| det000009368 | Chastisor Auto-Vox | not_modeled | 战意测验域 |
| det000009756 | Extremis Sanction | not_modeled | 能力使用次数/建军点数域 |

### 战略（38）— 可编 13（3 encoded / 10 partial），nm 25

| 分队 | encoded | partial | not_modeled |
|---|---|---|---|
| Imperialis Fleet | — | CLOSE-QUARTERS BARRAGE(+S/+AP<12")、DISPLACER FIELD(invuln4) | VIOLENT ACQUISITION(据点门)、MASTERS OF THE VOID、EMPEROR'S WILL、SELFLESS BODYGUARD |
| Interdiction Team | **CRACKDOWN**(近战重骰命中+致伤)、**DUTY AND DEATH**(FNP4) | ARBITRARY EXECUTION([LETHAL]手炮 wf) | INESCAPABLE JUDGEMENT |
| Ordo Hereticus | **DISPENSE JUSTICE**([LETHAL]两相位) | INVIOLATE JURISDICTION(FNP5) | STUN GRENADES(负关键字门)、EXECUTION ORDER、LINE OF FIRE、EXACT PUNISHMENT |
| Ordo Malleus | — | TRUESILVER ARMOUR(AP恶化)、PSYBOLT AMMUNITION([LETHAL]射击) | RITUAL OF WARDING、RITES OF EXORCISM、STEEL HEART、HEXAGRAMMIC WARDS |
| Ordo Xenos | — | ARMOUR OF CONTEMPT(AP恶化)、DRAGONFIRE([IGNORES COVER])、KRAKEN(+AP射击) | ADAPTIVE TACTICS、HELLFIRE(ANTI-X)、RAPID TACTICAL RELOCATION |
| Veiled Blade | — | HYPERSTIMMS(T+1)、WILL-SAPPING SALVO([SUSTAINED]射击) | PRIME TARGET(重骰1)、ORBITAL OVERSIGHT、BLIND GRENADES、ENSNARING TRAP |
| Voidship's Company | — | — | BREACH AND CLEAR、AMMO RATIONS(具体目标)、BOARDING DRILL、SHIP'S WATCH(Overwatch) |

### 增强（24）— 可编 4（1 encoded / 3 partial），nm 20

| 分队 | encoded | partial | not_modeled |
|---|---|---|---|
| Imperialis Fleet | — | — | Clandestine Operation、Combat Landers、Digital Weapons(MW池)、Fleetmaster |
| Interdiction Team | — | — | Manhunter's Helm(具体目标)、Vasov's Auto-Oppressor |
| Ordo Hereticus | **Witch Hunter**(对PSYKER重骰命中) | — | Ignis Judicium、Liber Heresius、No Escape |
| Ordo Malleus | — | Daemon Slayer(近战+1A) | Formidable Resolve、Gift of the Prescient、Grimoire of True Names |
| Ordo Xenos | — | Blackweave Shroud(FNP4携带者) | Amulet of Auto-Chastisement、Beacon Angelis、Universal Anathema(ANTI-X) |
| Veiled Blade | — | — | Decoy Targets、Esoteric Explosives、Intraneural Biotech、Micromelta(ANTI-X) |
| Voidship's Company | — | Heirloom Blade(单剑全特征+1) | Lathimon's Flock |

### 4 条 encoded（零未建模残量）

1. **CRACKDOWN**：Fight phase 近战重骰命中+致伤（reroll fail ×2，phase_melee 门）。
2. **DUTY AND DEATH**：本单位 FNP 4+（守方，两相位无门）。
3. **DISPENSE JUSTICE**：武器 [LETHAL HITS]（auto_wound，两相位无门）。
4. **Witch Hunter**：对 PSYKER 目标重骰命中（hit/reroll，condition target_has_keyword psyker，
   requires bearer_leading）。

### 防高估——刻意不编的坑（应用历次审查蒸馏）

- **重骰 1**（Destroy the Daemonic / PRIME TARGET）：引擎只支持重骰失败，重骰 1 无载体。
- **负关键字门**（STUN GRENADES 的 non-MONSTER/VEHICLE）：引擎只能表达「有关键字」→ 裸编过度施加。
- **ANTI-X 关键字**（HELLFIRE/Universal Anathema/Micromelta）：射击/近战×关键字致伤阈值无复合 tag。
- **[DEVASTATING WOUNDS]/[MELTA]/[PRECISION] 关键字**（Ignis Judicium/RITES OF EXORCISM）：无引擎通道。
- **具体目标声明**（VIOLENT ACQUISITION 据点门 / AMMO RATIONS / Manhunter's Helm）：裸编对所有目标过度施加。
- **致命伤池非攻击链**（Digital Weapons 掷 3D6 生成 MW）：无载体。
- 任务战术选一 / 部署 / 预备队 / CP 经济 / 战意测验 / 移动 / Overwatch 域：全部无战斗链载体。

### 相位门核对（正反两向）

- 射击门（phase_shooting / ranged_within_12）：Root out Heresy、CLOSE-QUARTERS BARRAGE、DRAGONFIRE、
  KRAKEN、PSYBOLT、WILL-SAPPING SALVO —— 均限射击不注入近战。
- 近战门（phase_melee）：Daemon Slayer(+1A)、Heirloom Blade(全特征) —— 限近战不注入射击。
- **两相位无门**（正确不加门，避免反向欠建模）：DUTY AND DEATH(FNP)、DISPENSE JUSTICE([LETHAL])、
  TRUESILVER/ARMOUR OF CONTEMPT(守方 AP 恶化「until attacking unit finished」)、HYPERSTIMMS(T+1)、
  Witch Hunter(reroll vs PSYKER，随目标关键字非相位)。
- **无 staged-WHEN 冲锋后仅近战型条款**（本阵营 ENSNARING TRAP 的 Callidus 冲锋后 +1 致伤依附
  本战略触发的冲锋条件链，无载体 → not_modeled，不落半编）。

---

## 四、门禁

- `dsl-apply`：应用 69，指纹让路 0，跳过 0；三态累计 encoded 107 / partial 372 / not_modeled 1191。
- `fp-rules`：text 应用 2 / 让路 0。
- `pytest tests/ -q`：**1314 passed**（含新 test_simulator_dsl_pr23_payload.py 与更新后的
  test_db_compile_dsl_apply.py 计数 1670）。
- 基准 gold v3（agent 路径）：见 `benchmarks/v3_edition11/qa_agent_results_p7pr23.json`。
  纯编码 PR：DSL/DB 补丁不进 FAISS 检索语料，检索侧零影响。
- 本机 `db/wh40k.sqlite` 为 gitignored 构建产物；开跑前清理了跨分支残留投影（chaosknights 等
  80 条 orphan）使投影层与本分支 payload 一致。
