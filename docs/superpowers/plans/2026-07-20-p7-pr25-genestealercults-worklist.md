# P7-PR25 基因窃取者教派（Genestealer Cults）逐行 A/B 工作单（2026-07-21）

对照源：`data_refined/Faction Pack Genestealer Cults/`（11 版 Faction Pack，Legal from
2026-06-20，共 11 页）vs `db/wh40k.sqlite`（faction='GC'）。体裁沿 PR1/PR4-PR24。分两迭代：
**迭代 1（本文已落）= DB 11 版对齐（fp_rules + fp_errata）**；迭代 2 = 全量 DSL 编码 +
基准 + 自审 + 补齐本工作单的「DSL 编码盘面」章节。

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
| 10 | abilities | 000008501 | Cult Ambush（军规） | ①标记放置 9"→8" ②标记被踢除 9"→8" ③补「Cult Ambush 单位不在第三轮末自动阵亡」④增援改为「对手移动阶段结束做 ingress move、贴底接触标记、首轮即可」 |
| 11 | abilities | 000000510_a2 | Summon the Cult（Acolyte Iconward） | 几何 9"→8" |
| 12 | abilities | 000000513_a1 | Brood Surge（Hybrid Metamorphs） | 整条重写为 11 版 surge move 体裁（D6"），十版的「尽量靠近最近敌军 / 无喷火器改 6" / 士气崩溃禁用」条款一并删除 |
| 13 | abilities | 000001570_a2 | Hypersensory Abilities（Kelermorph） | 完整重印，唯一实质差异几何 9"→8" |
| 14 | abilities | 000002525_a2 | Planted Explosives（Reductus Saboteur） | 几何 9"→8"（库现文此处用弯引号 ”，替换保形） |
| 15 | abilities | 000001569_a1 | Creeping Shadow（Sanctus） | 重写：去「每回合一次」、几何 9"→8"、移动类型放宽；移动距离 6" 不变 |
| 16 | abilities | 000001569_a2 | Cloaked Assassin（Sanctus） | 第二句 → 11 版 snap shooting 体裁（过守火战略并入 snap shooting） |

### 真漂移已补：fp_errata weapon_patches（4 条）

FP p8「爆破弹类 Range 改 6"」，库沿用十版 8"。落账前脚本校验「unit_id+武器名唯一命中
且现值 ∈ {from, to}」：

| unit_id | 单位 | 武器 | range |
|---|---|---|---|
| 000003716 | Acolyte Hybrids With Hand Flamers | Demolition charges | 8 → **6** |
| 000000521 | Goliath Rockgrinder | Demolition charge cache | 8 → **6** |
| 000000516 | Goliath Truck | Demolition charge cache | 8 → **6** |
| 000002525 | Reductus Saboteur | Demolition charges | 8 → **6** |

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

## DSL 编码盘面（genestealercults.json）

**迭代 2 待落。** 盘面规模预估 **106 条** = 13 分队规则（10 库内 + 3 fp_new）+ 57 战略
（48 库内 + 9 fp_new）+ 36 增强（30 库内 + 6 fp_new）。约定同 PR9-PR24：零新引擎通道、
零新态势开关、零新 condition tag——纯编码 PR。
