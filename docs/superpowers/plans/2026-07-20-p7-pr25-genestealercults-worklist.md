# P7-PR25 基因窃取者教派（Genestealer Cults）逐行 A/B 工作单（2026-07-21）

对照源：`data_refined/Faction Pack Genestealer Cults/`（11 版 Faction Pack，Legal from
2026-06-20，共 11 页）vs `db/wh40k.sqlite`（faction='GC'）。体裁沿 PR1/PR4-PR24。分两迭代：
**迭代 1 = DB 11 版对齐（fp_rules + fp_errata）**；**迭代 2 = 全量 DSL 编码 + 基准 + 自审
+ 迭代 1 判定复核**。

> ⚠️ **迭代 2 推翻了迭代 1 的三处判定**（均已回滚/补齐，详见「迭代 2 复核纠正」章节）：
> 4 条爆破弹 Range 补丁方向读反、Cult Ambush 多改一处几何、Final Day 整份重印漏 A/B。
> 教训：refine 产物的「改为 X"」数值必须回原 PDF（PyMuPDF）逐条复核，
> **整份重印的分队要把规则/增强/战略三层都 A/B，不能只核分队规则**。

> page_005.md 的 refine 产物在 ENRAPTURED DAMNATION 处被截断（"forces their enemies to reco"），
> 已按既定兜底走 PyMuPDF 回原 PDF 取全文（Final Day 的 4 条增强全文由此确认）。

## FP 内容面

FP 共 4 个分队 + Rules Updates + 1 张 Legends 兵牌：

| 分队 | 分队规则 | 库内状态 |
|---|---|---|
| Heroes of the Uprising | Killer Reputation | **DB 0 命中 → fp_new** |
| Purestrain Broodswarm | Enemy Within | **DB 0 命中 → fp_new** |
| Xenocult Masses | Hordes of the Faithful | **DB 0 命中 → fp_new** |
| Final Day | Psionic Parasitism | 已收录（`000009826`，Wahapedia 已滚入，逐字一致**免补**） |

库内另有 9 个十版分队（Host of Ascension / Xenocreed Congregation / Biosanctic Broodsurge /
Outlander Claw / Brood Brother Auxilia / Cult Unveiled / Genespawn Onslaught /
Infestation Swarm，及 BROOD BROTHERS 军规块），FP 的 Rules Updates 对其中 5 个打了勘误。

**Legends 兵牌 Tectonic Fragdrill（`000001576`）**：FP p10-p11 整表重印，与库现值逐格
A/B——M `-` / T 11 / Sv 3+ / W 14 / Ld 7+ / OC 0，Fragdrill 近战 A6 WS6+ S12 AP-2 D D6
**全部一致，零补丁**。

## A/B 判定汇总（迭代 1）

### 真漂移已补：fp_rules text_patches（16 条）

生成方式：`from_text` 直接取库现值、`to_text` 由显式子串替换算出，脚本对**每条替换断言
命中且唯一**（哑替换/歧义定位当场炸），杜绝写出 from==to 的假补丁。

| # | 表 | id | 名 | 判定 |
|---|---|---|---|---|
| 1 | stratagems | 000009076006 | STIMULATED BIO-SURGE | EFFECT 整段 → 定值「+2 to charge rolls」（原为按目标数 +1 上限 +3） |
| 2 | stratagems | 000009085002 | IN THE SHADOW OF IRON | EFFECT 几何 9"→8"（WHEN 段的 9” 不在 FP change 范围，不动） |
| 3 | stratagems | 000009085003 | REGIMENTAL REINFORCEMENTS | 完整重印，唯一实质差异标记放置 9"→8" |
| 4 | stratagems | 000009080002 | ALONG SHADOWED TRAILS | TARGET 段重印与库一致免动；EFFECT 几何 9"→8" |
| 5 | stratagems | 000009072006 | THE DOWNTRODDEN RISE | WHEN 由「增援步骤结束」放宽为「对手移动阶段结束」；EFFECT 逐字一致免动 |
| 6 | stratagems | 000009072004 | TIRELESS FERVOUR | EFFECT 改两级列表：①进军/撤退不再阻断宣冲 ②可选分支（重骰冲锋 + 必须与友方 CHARACTER 交战的敌军咬住） |
| 7 | enhancements | 000009075002 | Predatory Instincts | 重写：英雄干预由「0CP 每战斗轮一次」→「-1CP 且不占用本阶段其他单位使用次数」，Infiltrators 保留 |
| 8 | enhancements | 000009084003 | Adaptive Reprisal | 重写：由「9" 内友军 0CP 英雄干预」收窄为「本单位自身英雄干预 -1CP」 |
| 9 | enhancements | 000009067002 | Prowling Agitant | 重写：去「每回合一次」、几何 9"→8"、移动类型放宽为「任何移动」 |
| 10 | abilities | 000008501 | Cult Ambush（军规） | ①标记被踢除 9"→8" ②补「Cult Ambush 单位不在第三轮末自动阵亡」③增援改为「对手移动阶段结束做 ingress move、贴底接触标记、首轮即可」（**迭代 2 回滚**：重生时「放置标记」那一条 FP 原文仍是 9"，迭代 1 误改 8"） |
| 11 | abilities | 000000510_a2 | Summon the Cult（Acolyte Iconward） | 几何 9"→8" |
| 12 | abilities | 000000513_a1 | Brood Surge（Hybrid Metamorphs） | 整条重写为 11 版 surge move 体裁（D6"），十版的「尽量靠近最近敌军 / 无喷火器改 6" / 士气崩溃禁用」条款一并删除 |
| 13 | abilities | 000001570_a2 | Hypersensory Abilities（Kelermorph） | 完整重印，唯一实质差异几何 9"→8" |
| 14 | abilities | 000002525_a2 | Planted Explosives（Reductus Saboteur） | 几何 9"→8"（库现文此处用弯引号 ”，替换保形） |
| 15 | abilities | 000001569_a1 | Creeping Shadow（Sanctus） | 重写：去「每回合一次」、几何 9"→8"、移动类型放宽；移动距离 6" 不变 |
| 16 | abilities | 000001569_a2 | Cloaked Assassin（Sanctus） | 第二句 → 11 版 snap shooting 体裁（过守火战略并入 snap shooting） |

### fp_errata：**零补丁**（迭代 1 的 4 条已回滚）

见「迭代 2 复核纠正」第 ① 条。

### fp_new（inserts 18 条）

三个全新分队各 1 规则 + 2 增强 + 3 战略，synthetic id 前缀
`fp11e-genestealercults-{heroesuprising,purestrainbroodswarm,xenocultmasses}`，
增强 `cost` 诚实置空（FP 不含点数、MFM 缓存无增强数据）。容器名 ↔ 规则名沿 votann 约定：
`detachments.name_en` 存**规则名**、`stratagems.detachment` / `enhancements.detachment_name`
存**容器名**。

- **Heroes of the Uprising**（规则 Killer Reputation：KELERMORPH/LOCUS/REDUCTUS SABOTEUR/
  SANCTUS 获 KILLER，KILLER 攻击可重骰命中 1 与致伤 1 + 增强 Gene-tailored Toxins（+1 D）/
  Contraband Munitions（远程 +2 S）+ 战略 LIVING UP TO LEGEND / SURGING BROODWORSHIP
  （[DEVASTATING WOUNDS]）/ LOYAL TO THE END）
- **Purestrain Broodswarm**（规则 Enemy Within：对手战斗阶段末未交战 PURESTRAIN 进战略预备队
  + 增强 Mark of the Star Children（+1 T / 4+ Sv / 近战 +1 S，UPGRADE 型）/ Talons of the Sire
  （重骰致伤 1）+ 战略 LURK AND STRIKE / CRAWLING HORROR（-6" 侦测范围）/ INHUMAN REACTIONS）
- **Xenocult Masses**（规则 Hordes of the Faithful：指挥阶段地形区内 NEOPHYTE HYBRIDS 回复
  3 伤 + 增强 Inspired to Greatness（重骰伤害骰）/ Devious Disguises（-3" 侦测范围，UPGRADE 型）
  + 战略 EYES OF THE CULT / FANATICAL HAIL（重骰命中）/ SLUNK FROM THE UNDERBELLY（守方 -1 AP））
- A/B 已确认三分队规则名/战略名/增强名在库 **0 命中**（真全新，Wahapedia 只滚入了 Final Day）

### 免补（重印或已滚入，逐字一致）

- 分队规则：Integrated Tactics 的 BROOD BROTHERS 段（`000009083`）、Rapid Takeover
  （`000009078`，FP 的「objective」vs 库的「objective marker」属非语义措辞）、
  Psionic Parasitism（`000009826`）
- 战略：PRIMED AND READIED（库已 2CP）、RETURN TO THE SHADOWS（When/Target 已是 11 版）、
  TUNNEL CRAWLERS（EFFECT 已 6"）
- 增强：Deeds That Speak to the Masses（`000009071004`）
- 兵牌技能：Battlefield Analysis（Nexos `000001571_a1`）、Cult Demagogue（Primus
  `000000509_a1`）——库现文即 FP change-to 全文
- Legends 兵牌 Tectonic Fragdrill 整表（见上）

### removed_11e：零

FP 无删减裁定，`deactivations` 不动。

### 观察项（本 PR 不落，越层）

| FP 条目 | 不落原因 |
|---|---|
| Goliath Rockgrinder / Goliath Truck「Keywords: **Add** 'FRAME'」 | `fp_errata._apply_keyword_patches` 明文规定 keywords 主列表**只删不加**（新增关键词属重印整表体裁，走 new_units/上游滚更）。为一条勘误新开 add 通道属越层，记观察项 |
| Biophagus / Clamavus / Locus / Nexos「Core Abilities：Remove 'Leader', add 'Support'」 | 这 4 张兵牌的 `datasheets.leader_head` 库现值为空串，Leader/Support 核心能力在库内**无载体行**，无处可补 |
| Biophagus「Unit Composition, Wargear」重印 | 与库现 `datasheets.loadout` 唯一差异是 `injector goad**,** alchemicus familiar` → `**;**`（分隔符笔误级），且 `datasheets.loadout` 不在 `fp_rules._TEXT_TARGETS` 白名单内 |
| FAQ 5 问（p9） | 澄清性问答，无库内对应行 |

## 迭代 1 门禁

- `.venv\Scripts\python.exe -m db_compile fp-rules` → 文本 **应用 16 / 幂等 105 / 让路 0 /
  跳过 0 / 无效 0**；补录插行 **应用 18 / 幂等 249 / 让路 0 / 无效 0**
- `.venv\Scripts\python.exe -m db_compile fp-errata` → 武器 **应用 4 / 幂等 3 / 让路 0 /
  跳过 0**；属性/关键词/新单位全幂等
- `.venv\Scripts\python.exe -m db_compile dsl-apply` → 应用 0 / **幂等 1779** / 指纹让路 0
- `.venv\Scripts\python.exe -m pytest tests/ -q` → **1338 passed**，零失败

> ⚠️ 途中逮到一个与本 PR 无关的既存红：`test_simulator_dsl_pr4_payload.py::
> test_projection_counts_match_payload` 因 **gitignored 的 `db/wh40k.sqlite` 跨分支共用**，
> 库里残留 139 行来自未合并分支（太空野狼 PR18 / 混沌骑士 PR22）的孤儿 DSL 投影。
> 按既定处置**清孤儿行而非改测试**（`effect_dsl_json=NULL, dsl_status='not_modeled'`），
> 清理前先证伪「孤儿里没有 GC 行」。

## 迭代 2 复核纠正（推翻迭代 1 的三处判定）

复核方式：把 FP 全 11 页逐页与库现值重新 A/B，凡涉及**具体数值/整段重写**的判定一律用
`PyMuPDF` 回原 `data/Faction Pack Genestealer Cults.pdf` 取原文复核（refine 产物只作索引）。

### ① fp_errata 4 条爆破弹 Range 补丁：方向读反，**全部回滚**

FP p8 原文（PDF 与 refine 两源一致）：

```
Acolyte Hybrids with Hand Flamers, Ranged Weapons
Change the Range characteristic of demolition charges to ‘8"’.
Goliath Rockgrinder, Ranged Weapons        → demolition charge cache to ‘8"’.
Goliath Truck, Ranged Weapons              → demolition charge cache to ‘8"’.
Reductus Saboteur ▪ Demolition Charges: Change Range characteristic to ‘8"’.
```

FP 是**改为 8"**，而库现值本就是 8" → **免补**。迭代 1 误读为「改为 6"」并落了 4 条
`8 → 6` 补丁，等于把正确值改坏。处置：
- `db_compile/fp_errata_patches.json` 删掉这 4 条，改记入 `resolved`（verdict = `DB 正确(8") 不改`）
- 库内 4 行 `weapons.range` 由 6 复位为 8（`000000516_w1` / `000000521_w2` /
  `000002525_w2` / `000003716_w1`），复位脚本带「现值恰为 6 才改」的幂等守卫
- 复核后 `fp-errata` → 武器 **应用 0 / 幂等 3**（回到本 PR 前的基线）

### ② Cult Ambush（`000008501`）多改一处几何：**放置标记那条回滚为 9"**

FP p7 的 change-to 全文里两处几何**不同值**：

| 条款 | FP 原文 | 迭代 1 | 迭代 2 |
|---|---|---|---|
| 重生时「放置一个 Cult Ambush 标记」 | more than **9"** horizontally away | 误改 8" | **回滚为 9"** |
| 敌方模型移动结束触发「移除标记」 | within **8"** of a marker | 9"→8" ✅ | 保持 |

（同页 REGIMENTAL REINFORCEMENTS 的放置几何确是 8"——GW 自身两处不一致，以原文为准。）

### ③ Final Day 整份重印漏 A/B：补 1 条 text_patch

FP p5-p6 是 **Final Day 分队整份重印**（分队规则 + 4 增强 + 6 战略），迭代 1 只核了分队规则
Psionic Parasitism 就判「逐字一致免补」。迭代 2 逐条 A/B 结果：

| 条目 | 判定 |
|---|---|
| Psionic Parasitism / Synaptic Auger / Enraptured Damnation / Vanguard Tyrant / Inhuman Integration | 逐字一致，免补 |
| HYPERFEROCITY / PSI SURGE / AVENGE THE STAR CHILDREN / DARTING ATTACKS / RESISTANCE TUNNELS | 逐字一致，免补 |
| **DIVINE IMPERATIVE（`000009828005`）** | **真漂移 → 第 17 条 text_patch** |

DIVINE IMPERATIVE 整条重写：WHEN 由「你的冲锋阶段」收窄为「友军 GC 单位在**友军已交战
TYRANIDS 单位 12" 内**宣布冲锋时」；TARGET 改为该单位；EFFECT 由十版的「选一敌方单位…
+1 冲锋骰且可重骰」改为两级列表（+1 冲锋骰 / 可选启用「重骰冲锋骰 + 必须与该友军
TYRANIDS 咬住的敌方单位交战」分支）。DSL 侧该条目两版皆 `not_modeled`（冲锋骰域），
编码盘面不受影响。

## DSL 编码盘面（`dsl_payloads/genestealercults.json`）

**107 条 = 8 encoded / 18 partial / 81 not_modeled**（可编率 26/107 = 24.3%）。
表分布：`abilities` 14（13 分队规则物化 + 军规 Cult Ambush 真实行）/ `stratagems` 57 /
`enhancements` 36。**零新引擎通道、零新态势开关、零新 condition tag——纯编码 PR**。

用到的既有通道：攻方 `attacks.modify` / `hit.modify` / `hit.bs_improve` / `hit.reroll` /
`hit.crit_threshold` / `hit.auto_wound` / `wound.modify` / `wound.s_improve` /
`wound.mortal_pool` / `damage.modify` / `save.ap_improve`；守方 `fnp.fnp` /
`damage.damage_reduction` / `hit.modify` / `wound.modify` / `wound.t_improve` /
`save.invuln` / `save.ap_improve`。condition tag：`phase_melee` / `phase_shooting` /
`melee_charging` / `melee_target_has_keyword` / `target_has_keyword`。
开关：`bearer_leading` / `defender_bearer_leading` / `disembarked_this_turn`。

### 录入约定（写进 payload `_comment`，全条目统一）

1. **点名型条目**（战略/增强）的「限某类单位」前提由玩家点名时声明，不另记未建模残量；
2. **「携带者本模型」口径**的效果一律挂 `bearer_leading` / `defender_bearer_leading` 开关
   并把「整单位注入会高估」写进残量；
3. **阶段门按 WHEN 之后本回合还剩哪些阶段能生效推定**——双阶段（「射击阶段或战斗阶段」）
   与「持续至战斗结束」一律**不设**阶段门（反向陷阱：多加门 = 欠建模，同样是事实错误）。

### encoded（8 条）

| id | 名 | 侧 | 效果 | 阶段门推理 |
|---|---|---|---|---|
| `000009828004` | AVENGE THE STAR CHILDREN | 攻 | 命中 +1 / 致伤 +1 | 「until the end of the battle」→ 跨全部阶段，**无门** |
| `000009068002` | COORDINATED TRAP | 攻 | 致伤 +1 | WHEN=射击阶段开始**或**战斗阶段开始 → 无门 |
| `000009068003` | PRIMED AND READIED | 攻 | 暴击命中阈值 5+ | WHEN 双阶段 → 无门 |
| `000009477002` | HYPERADRENAL REFLEXES | 守 | 4+ 无效保护 | WHEN=Fight phase → `phase_melee` |
| `000009080003` | DEVOTED CREW | 守 | 伤害 -1 | WHEN=对手射击阶段**或**战斗阶段 → 无门 |
| `000009080006` | DEFT MANOEUVRING | 守 | 4+ 无效保护 | WHEN=对手射击阶段 → `phase_shooting` |
| `fp11e-…-xenocultmasses-s2` | FANATICAL HAIL | 攻 | 命中重骰（失败骰） | 远程攻击 → `phase_shooting` |
| `fp11e-…-xenocultmasses-s3` | SLUNK FROM THE UNDERBELLY | 守 | 来袭 AP 恶化 1 | 「Ranged attacks that target your unit」→ `phase_shooting` |

### partial（18 条）

| id | 名 | 已编 | 主要未建模残量 |
|---|---|---|---|
| `det000009070` | Unquestioning Fanaticism | 守 FNP 3+（需 `defender_bearer_leading`） | FNP 只给该 CHARACTER 模型本身；进军/冲锋骰重投 |
| `det000009074` | Hypermorphic Fury | 攻 近战 A+1（`melee_charging`） | 冲锋骰 +1；限 ABERRANTS/BIOPHAGUS/PURESTRAIN |
| `det000009475` | Half-Glimpsed Shadows | 守 远程来袭命中 -1（`phase_shooting`） | 「6" 外」距离门无载体，按常态成立假设 |
| `000009076004` | GENE-TWISTED MUSCLE | 攻 致伤 +1 ×2（`melee_target_has_keyword` monster/vehicle） | MONSTER∨VEHICLE 析取拆两条；双关键字目标由 ±1 夹取兜住 |
| `000009461005` | LURKING MENACE | 守 命中 -1（`phase_shooting`） | 「3" 外」距离门 |
| `fp11e-…-heroesuprising-s2` | SURGING BROODWORSHIP | 攻 [DEVASTATING WOUNDS] | 限单位内 KILLER 模型 |
| `000009080004` | CLOSE-RANGE SHOOT-OUT | 攻 [LETHAL HITS]（`phase_shooting`） | 「18" 内」距离门（引擎只有 12"/8" 档） |
| `000009072003` | FRENZIED DEVOTION | 攻 近战 A+1 + WS 改善 1 | [HAZARDOUS] 自伤；「不含 CHARACTER 模型」的模型级豁免 |
| `000009075003` | Biomorph Adaptation | 攻 近战 AP+1 + D+1 | 限携带者模型武器 |
| `000009827004` | Vanguard Tyrant | 攻 近战 S+1 + AP+1 | 限携带者（Winged Hive Tyrant）模型武器 |
| `000009468003` | Miasmic Fumes | 守 命中 -1 + 致伤 -1 | 仅「瞄准携带者本模型」的攻击 |
| `fp11e-…-heroesuprising-e1` | Gene-tailored Toxins | 攻 D+1 | 限携带者模型自身攻击 |
| `fp11e-…-heroesuprising-e2` | Contraband Munitions | 攻 远程 S+2（`phase_shooting`） | `bearer_leading` 假设 |
| `000009067005` | Assassination Edict | 攻 对 CHARACTER 命中 +1 | `bearer_leading` 假设 |
| `000009079004` | Starfall Shells | 守 来袭命中 -1（双阶段） | 前提是携带者已用 cult sniper rifle 命中该单位 |
| `000009079005` | Assault Commando | 攻 远程命中重骰 | 需 `bearer_leading` + `disembarked_this_turn` 双开关 |
| `fp11e-…-purestrainbroodswarm-e1` | Mark of the Star Children | 守 T+1 | 「4+ Sv」是绝对值设定（引擎只有相对改善档）；「近战 +1 S」属攻方向，单条目单侧装不下 |
| `000009071003` | Denunciator of Tyrants | 攻 对 CHARACTER 命中 +1 + 致伤 +1 | `bearer_leading` 假设 |

### not_modeled 的三大桶（81 条）

| 桶 | 条数量级 | 典型条目 | 无载体原因 |
|---|---|---|---|
| **增援/预备队/部署/标记** | ~30 | Cult Ambush 军规、A Perfect Ambush、A Chink in Their Armour、各分队的 Cult Ambush 标记战略、RETURN TO THE SHADOWS/OUTFLANK 等 | 「本回合作为增援登场」的状态**无引擎开关载体**；照 PR6 下车态先例须新增态势开关，本 PR 零新开关 → 裸编会对全部攻击过度施加 |
| **只重骰 1 点 / 二选一分支** | 7 | Killer Reputation、HYPERFEROCITY、SYMBIOTIC DESTRUCTION、VENGEANCE FOR THE MARTYR!、Talons of the Sire… | 引擎重骰通道语义是**重骰失败骰**，「只重骰 1 点」无载体，裸编显著高估；「基础重骰 1 点 + 位置条件升级为完整重骰」属二选一分支，只编升级分支会在前提不成立时高估 |
| **移动/冲锋骰/资格/OC/目标点/士气/CP/治疗/序列外致命伤** | ~44 | 全部 Hatchway 与常规移动类、冲锋骰 ±X、Fire Overwatch、Resurgence points、领导力/战斗震慑测验、D6 致命伤类 | 全在攻击结算链之外 |

另有两类点名原因：**领导力测验的随机条件分支**（Blessed Visages / BIO-HORROR REVELATION /
GROWING DREAD）——把失败分支当恒成立就是过度施加；**跨单位位置门**（Integrated Tactics 的
overlapping fire、Psionic Parasitism 的 Catalyst 光环、Inhuman Integration、Martial
Espionage）——引擎无跨单位链路。

### 11 版侦测范围（detection range）机制

FP 三条新条目（CRAWLING HORROR -6"、EYES OF THE CULT +6"、Devious Disguises -3"）
都作用于 11 版新引入的 detection range，引擎**完全无该机制**，一律 not_modeled 并点名披露。

## 迭代 1 门禁

- `.venv\Scripts\python.exe -m db_compile fp-rules` → 文本 **应用 16 / 幂等 105 / 让路 0 /
  跳过 0 / 无效 0**；补录插行 **应用 18 / 幂等 249 / 让路 0 / 无效 0**
- `.venv\Scripts\python.exe -m db_compile fp-errata` → 武器 **应用 4 / 幂等 3 / 让路 0 /
  跳过 0**（⚠️ 这 4 条即迭代 2 回滚的错误补丁）；属性/关键词/新单位全幂等
- `.venv\Scripts\python.exe -m db_compile dsl-apply` → 应用 0 / **幂等 1779** / 指纹让路 0
- `.venv\Scripts\python.exe -m pytest tests/ -q` → **1338 passed**，零失败

> ⚠️ 途中逮到一个与本 PR 无关的既存红：`test_simulator_dsl_pr4_payload.py::
> test_projection_counts_match_payload` 因 **gitignored 的 `db/wh40k.sqlite` 跨分支共用**，
> 库里残留 139 行来自未合并分支（太空野狼 PR18 / 混沌骑士 PR22）的孤儿 DSL 投影。
> 按既定处置**清孤儿行而非改测试**（`effect_dsl_json=NULL, dsl_status='not_modeled'`），
> 清理前先证伪「孤儿里没有 GC 行」。

## 迭代 2 门禁

- `.venv\Scripts\python.exe -m db_compile fp-rules` → 文本 **应用 0 / 幂等 122 / 让路 0 /
  跳过 0 / 无效 0**（16 + 第 17 条 DIVINE IMPERATIVE，含 Cult Ambush 几何回滚后复跑）；
  补录插行 **应用 0 / 幂等 267 / 让路 0 / 无效 0**
- `.venv\Scripts\python.exe -m db_compile fp-errata` → 武器 **应用 0 / 幂等 3**（GC 零补丁）
- `.venv\Scripts\python.exe -m db_compile dsl-apply` → 应用 0 / **幂等 1886**（1779 + 107）/
  指纹让路 0 / 跳过 0
- `.venv\Scripts\python.exe -m pytest tests/ -q` → **1379 passed**，零失败
  （新增 `tests/test_simulator_dsl_pr25_payload.py` 41 条）
- 自审（code-reviewer 子代理，全 107 条逐条核阶段门双向）：**0 CRITICAL / 0 HIGH /
  1 MEDIUM**（3 条已编条目缺引擎级差分测试，已补齐 Gene-tailored Toxins /
  Denunciator of Tyrants / Vanguard Tyrant 三条，含 Vanguard Tyrant 的射击阶段负例）

## 基准（gold v3，agent 路径）

```
.venv\Scripts\python.exe scripts/qa_bench.py --path agent \
  --out benchmarks/v3_edition11/qa_agent_results_p7pr25.json --workers 6
→ {"correct": 94, "partial": 2, "wrong": 0, "total": 96, "accuracy": 97.9,
   "degraded_count": 34, "wall_time": "68.4s"}
```

**零硬错（wrong=0）；96 题逐题 verdict 与紧邻基线 `qa_agent_results_p7pr24.json`
逐条比对为 0 差异**——两条 ⚠️ 仍是 #41/#42（兽人小子）这对已知固定波动题，
不是本 PR 引入。这与「纯编码 PR 检索侧零影响」的预期一致：DSL 载荷与 DB 补丁
都不进 FAISS 语料（未 ingest），检索结果不可能被本 PR 改动。

> 判回归的正确姿势（沿 PR22 教训）：**比紧邻基线 json 的逐题 verdict，而非绝对分**。
> 97.9 就是本仓当前基线（历史 99.0 是更早语料/gold 版本下的值）。
