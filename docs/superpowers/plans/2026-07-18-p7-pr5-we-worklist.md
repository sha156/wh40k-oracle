# P7-PR5 吞世者 fp_rules/fp_errata 逐行 A/B 工作单（2026-07-18）

对照源：`data_refined/Faction Pack World Eaters/`（8 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR1/PR4 裁定：
**FP 完整重印即整体替换**（未收录旧条目标 removed_11e）；change-list 外科应用；
fp_new 走 inserts 补录（fp11e- 前缀 synthetic id）。

## FP 内容面

- 3 分队：Brazen Engines（**全新**）/ Butchers of Khorne（**全新**）/ Vessels of Wrath（**完整重印**）
- 1 兵牌：Defiler（WE 版）
- Rules Updates（p7-p8）：军规 1 条 + 分队/战略 6 条 + 兵牌技能 8 条 + 数值/关键词若干 + FAQ 4 条

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，9 + 兵牌技能 6 = 15 条）

| 行 | 判定 | 说明 |
|---|---|---|
| abilities 000008428 军规 Blessings of Khorne | drifted | Unbridled Bloodlust：re-roll Charge rolls → **+1 to charge rolls**（外科替换单句） |
| stratagems 000008431007 BERZERKER’S WRATH | drifted | Blood Surge move → 11 版核心 **surge move** 术语（TARGET/EFFECT 段整替） |
| stratagems 000010087007 FURY UNLEASHED | drifted | EFFECT 改 disembark move + **surge move D6+2"** |
| detachments 000010081 Brazen Fury | drifted | 能力体改核心 surge move（自带流程/限制句删除） |
| detachments 000009846 Wrath of Khorne | drifted | 完整重印：VESSEL OF WRATH 关键词+规模表机制废弃 → 人物近战 **[CLEAVE 1] 或 +1 AP** 二选一 |
| stratagems 000009848002 ASPIRE TO INFAMY | drifted | 重印：目标改人物单位，效果改 **+1 A、+2 S**（人物模型） |
| stratagems 000009848005 PUNISH THE CRAVEN | drifted | 重印：目标改人物；desperate escape mode / hazard rolls 术语 |
| enhancements 000009847002 Archslaughterer | drifted | 重印：效果整体换新（一次性全赐福激活） |
| enhancements 000009847005 Gateways to Glory | drifted | 重印：限定收窄恶魔亲王；MOBILE + 冲锋 +1 |
| abilities 000004076_a1 Goremongers Loping Speed | drifted | 9"→8" + 触发时机改写 + 删 once per turn |
| abilities 000002627_a1 Khorne Berzerkers Blood Surge | drifted | 改核心 surge move D6+2"（Wahapedia 只滚入了 +2 未换体裁） |
| abilities 000002632_a2 Helbrute Frenzy | drifted | 整改：once per turn 立即再战机制 |
| abilities 000002639_a1 Maulerfiend The Scent of Blood | drifted | 判据从冲锋目标战损改为 **9" 内存在战损敌军** |
| abilities 000002640_a1 Chaos Rhino Meet Any Challenge | drifted | 9"→8" |
| abilities 000002629_a1 Chaos Terminators Bloody Fury | drifted | 整改（FP 名 Blood Fury=DB 行 Bloody Fury 同源）：冲锋重骰附带"必须与最近目标接战" |

### 已滚入免补（identical，Wahapedia 现文即 11 版）

- stratagems 000010079002 SUMMONED BY SLAUGHTER（含 RESTRICTIONS once per battle round）
- stratagems 000010083006 WARP STALKERS
- stratagems 000010083005 RAPID MANIFESTATION（6" 已滚入）
- abilities Exalted Eightbound Rend and Tear / Jakhals+Khorne Berzerkers Icon of Khorne
- weapons Slaughterbound Lacerator and daemonic claw S=10
- **Defiler（WE 000004207）整表已在库**（M14"/OC5 与 FP 一致，无需插）

### removed_11e（deactivations 6 条，Vessels of Wrath 完整重印未收录）

- stratagems：OVERSHADOWED BY NONE / GORY DEDICATION / MEET FORCE WITH FORCE / BRAZEN CONTEMPT
- enhancements：Vox-diabolus / Avenger’s Crown

### fp_new（inserts 13 条）

- **Brazen Engines**（p1）：det Rampaging Terrors + 战略 APOPLECTIC CLARITY / TRAIL OF
  DESTRUCTION / GOADED TO FURY + 增强 Talons of Butchery / Murder-Forged Entity
- **Butchers of Khorne**（p2）：det Adamantine Avalanche + 战略 FOCUSED FEROCITY /
  A TROPHY FOR THE THRONE / WRATH BEYOND REASON + 增强 Sanctified in Slaughter /
  Gore-stained Veterans
- **Vessels of Wrath 重印新增**：战略 SCORN THE WITCH
- 增强点数一律 cost=NULL（FP 不含点数、MFM 缓存无增强数据——沿 PR4 AAC 裁定诚实置空）

### fp_errata（兵牌数值/关键词层）

- **Heldrake（000002641）**：M `20+"`→`12"`（stat patch；S4 25 飞机清单未覆盖 WE）+
  **keyword_patches 新层**删 `Aircraft`（守卫：单位存在/词已不在幂等/只删不加）
- **OC 0→'-' 不补**：功能等价（OC0≡无OC），库内 models.oc 全数值无 '-' 先例，
  强改恐破坏下游 int 解析——记格式差异裁定
- **FRAME 关键词新增跳过**（Chaos Land Raider/Predator×2/Rhino/Lord of Skulls）：
  沿 S4 裁定（测距词，引擎/检索无消费者）

### 中文名（name_patches 53 条）

- 有源配对（DavidZ 吞世者 codex refine，zh_source=codex-10e）：军规 恐虐赐福、
  狂战士战帮全套（无情狂怒 + 6 战略）、怒火容器全套（恐虐之怒 + 6 战略）
- 自译标记（zh_source=self-translation-11e）：其余 6 分队规则名 + 30 战略；
  inserts 自带 name_zh（暴走恐魔/精金雪崩等，亦属自译）
- enhancements 表无 name_zh 列，增强中文名不在本层（沿 PR1 结构约定）

### 观察项（不阻塞）

- FAQ 4 条（Angron×Wrath of Khorne / Disciple of Khorne 不能当 WARLORD /
  Lord on Juggernaut 领队赐福传导 / Summoned by Slaughter 首轮限制）——语义澄清，
  无库面改动，DSL 编码引用为注记
- 六赐福中文名（嗜血癫狂/燃怒活力/全面屠戮/卓越武艺/次元邪刃/斩首一击）用于
  DSL not_modeled 注记与开关文案，源 DavidZ page_001
