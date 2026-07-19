# P7-PR8 死亡守卫 fp_rules/fp_errata 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Death Guard/`（17 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR1/PR4/PR5/PR6/PR7 裁定：
**FP 完整重印即整体替换**（未收录旧条目标 removed_11e）；change-list 外科应用；
fp_new 走 inserts 补录（fp11e- 前缀 synthetic id）。

## FP 内容面

- 3 分队：Contagion Engines（**全新**，UNIQUE: ENGINES tag）/ Paragons of
  Putrescence（**全新**）/ Flyblown Host（**完整重印**——10 版 6 战略 + 4 增强
  瘦身为 11 版体裁 1 规则 + 3 战略 + 2 增强，规则名 Verminous Haze 沿用但效果
  整个换掉：Scouts 5"+Stealth → 至多两个 PLAGUE MARINES 单位 Infiltrators）
- 6 兵牌：Defiler DG 000004209 / DG Possessed 000001045 / DG Chaos Lord
  000001037 / DG Chaos Lord in Terminator Armour 000001038 / DG Cultists
  000001043 / DG Sorcerer in Terminator Armour 000001041——**整表已在库且逐格
  与 FP 一致零动作**（属性/武器/技能全核）；唯 4 张（Lord/LordTDA/Cultists/
  Sorcerer）faction_keywords 空缺，见 fp_errata 节
- Rules Updates（p7）：军规 2 条 + Tallyband 增强 1 条 + 兵牌 4 类；FAQ 1 条

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，9 条）

| 行 | 判定 | 说明 |
|---|---|---|
| detachments 000009728 Verminous Haze | drifted | **完整重印整体替换**：Scouts 5"+Stealth（DG 步兵除瘟疫行尸）→ 宣布战斗阵容时至多两个 PLAGUE MARINES 单位获 Infiltrators + FLYBLOWN tag 互斥句 |
| stratagems 000009730002 NAUSEATING PAROXYSMS | drifted | 重印：TARGET 收窄 DG Infantry→**PLAGUE MARINES**（engaged 措辞）；EFFECT battle-shock test subtracting 1 → **battle-shock roll with -1** |
| stratagems 000009730004 EYE OF THE SWARM | drifted | 重印：EFFECT 整替 [PISTOL]（excluding Blast）→ **[CLOSE-QUARTERS]**；WHEN 改 selected to shoot |
| stratagems 000009730005 DRONING HORROR | drifted | 重印：EFFECT 整替 重骰命中1/半程重骰命中 → **重骰命中1 + 半程重骰致伤1** |
| enhancements 000009729003 Insectile Murmuration | drifted | 重印：DG Infantry model → **PLAGUE MARINES unit only**；条件改 within Contagion Range of a friendly unit |
| enhancements 000009729005 Plagueveil | drifted | 重印：EFFECT 整个换掉：目标点上 18" 外不可被选为射击目标 → **-3" detection range** |
| abilities 000008396 Nurgle's Gift (Aura) 军规 | drifted | 两处合一整替：① Skullsquirm Blight "makes an attack"→"makes a **melee** attack"（全文仅 1 处，安全）② CONTAGION RANGE 节图片段后插入 **'Contagion Range cannot be greater than 12" after modifiers.'** |
| abilities 000001371_a2 Death Approaches | drifted | 整替：In your Movement phase, when→**Each time**；other enemy units **9"→8"** |
| enhancements 000010135002 Beckoning Blight | drifted | 外科：instead of more than **9"→8"**（其余逐字同） |

### 已滚入/已满足免补（identical）

- **6 张兵牌全格一致**（Defiler DG 含 Scuttling Walker/Barrage of Filth 技能文本、
  12 武器格；Possessed 含 Diseased Icon/Infectious Bloodshed；两 Lord 含
  Desiccation Conduit；Cultists 武器 6 格；Sorcerer 含 Putrescent Vitality/
  Pestilent Familiar）——Wahapedia 已滚入
- Typhus Eater Plague 000001053_a2（18" 排除 Lone Operative 版本已逐字 11 版）
- Chaos Predator Destructor 的 Predator autocannon S 已 =9（全阵营 5 行同）

### removed_11e（deactivations 5 条，Flyblown Host 完整重印未收录）

- stratagems：VERMIN CLOUD 000009730003 / ENERVATING ONSLAUGHT 000009730006 /
  MYPHITIC INVIGORATION 000009730007
- enhancements：Droning Chorus 000009729002 / Rejuvenating Swarm 000009729004
  （注意：**Paragons 分队有同名新增强但效果不同**——S>T 攻击 -1 致伤 vs 旧版
  每阶段回满 W，走 inserts 新行，不复用旧行）

### fp_new（inserts 12 条）

- **Contagion Engines**（p2，fp11e-dg-engines-*）：det Warped and Rusted Animus
  （4 类载具单位获 CONTAGION ENGINE tag + 远程 [ASSAULT]）+ 战略 FRESH VECTORS
  （重骰致伤1）/ BLOODRUST DELUGE（选一可见敌单位临时 Afflicted）/ SOULROT FLUX
  （脱离接战 D6 致命伤阶梯）+ 增强 Parasitic Woe-Reaper（战后治疗 D3）/
  Lancet of the Worldsore（MOBILE）
- **Paragons of Putrescence**（p4，fp11e-dg-paragons-*）：det Hypervirulent
  Strains（CHARACTER 传染范围 +3" 上限 12"）+ 战略 TERRITORIAL INFECTION（+1 OC）/
  AGGRAVUS SPASMS（敌 +6" 侦测）/ SIMULTANEOUS CONTAMINATION（行动不碍射击）+
  增强 Rejuvenating Swarm（**11 版新效果**：S>T 攻击 -1 致伤，排除 TERMINATOR）/
  Host of the Hybridised Pox（一次性第二瘟疫）
- 增强点数一律 cost=NULL（沿 PR4-PR7 AAC 裁定）

### fp_errata（兵牌数值/关键词层）

- **faction_keywords 补缺 4 张**：DG Chaos Lord 000001037 / Lord TDA 000001038 /
  Sorcerer TDA 000001041 / Cultists 000001043 的 faction_keywords 为空 `[]`——
  全库 1715 单位仅此 4 例，FP 明印 "Faction Keywords: Death Guard"，且
  profile.py 把 faction_keywords 并进 raw_keywords（DSL 条件按关键词匹配会静默
  漏），系真缺口。**扩 keyword_patches 支持 add_faction 通道**（幂等守卫：已含
  目标词跳过；只补空缺不覆盖）
- FRAME 关键词新增跳过（Chaos Land Raider/Predator×2/Rhino/Miasmic Malignifier/
  Plagueburst Crawler，沿 S4/PR5/PR6/PR7 裁定：测距词无消费者）

### 中文名（name_patches：军规 1 + det 规则 7 + 战略 42 + 补 Death Approaches）

- 有源配对（死亡守卫 10 版老湿腐 V1.1 refine，zh_source=codex-10e，中英对照标题
  或内容核实）：
  - 军规 abilities 000008396 Nurgle's Gift = 纳垢赐福（codex 正文引用体）
  - det 规则 7：世界之瘟（Worldblight/恶毒容器=Virulent Vectorium）/ 毒雾轰炸
    （Miasmic Bombardment/莫塔里安之锤）/ 多重感染（Manifold Maladies/传染冠军）/
    瘟疫军团（Reverberant Rancidity/唤魔记账官）/ 无尽尸群（Numberless Horde/
    蹒跚尸群）/ 致命发作（Deadly Vectors/死亡之主亲选）/ 虫害毒雾（Verminous
    Haze/蝇息疫军——名沿用，重印后指 11 版新文本）
  - 战略 42（7 codex 分队 × 6，含 removed 行也配——原文保留在库可检索，配名有益）；
    老湿腐 EN 标题变体已按 DB id 归一：BLESSING→BLESSINGS OF FILTH、GRIP OF
    WALKING POX→GRIP OF THE WALKING POX
  - abilities 000001371_a2 Death Approaches 死亡将至（老湿腐死亡守卫终结者页，
    落补丁前再核原文页；无源则留空）
- 自译标记（zh_source=self-translation-11e）：inserts 自带 name_zh——传染引擎
  （Contagion Engines）面：锈蚀狂躁兵魂（Warped and Rusted Animus）/ 新鲜病媒 /
  血锈倾盆 / 魂腐涌流；腐熟贤范（Paragons of Putrescence）面：超毒瘟株
  （Hypervirulent Strains）/ 领地感染 / 剧痛痉挛 / 同步污染
- 三个 index/Grotmas 期分队（Vectors of Decay/Sevenfold Offerings、Unclean
  Uprising/Relentless Spread、Arch-Contaminators/Inescapable Corruption）及其
  14 战略：中文 codex 无源，宁缺勿错留空
- enhancements 表无 name_zh 列，增强中文名不在本层（沿 PR1 结构约定）

### 观察项（不阻塞）

- **ENGINES/FLYBLOWN tag 互斥**（不能与另一同 tag 分队同取）——军表域约束，DB 无
  载体，插入行 rule_text 保留原句 + DSL not_modeled 注记（沿 PR7 HOST tag 先例）
- FAQ 1 条（Spore-laced Shock Waves 不逐轮反复致伤）——语义澄清无库面改动，
  DSL 注记引用
- 老湿腐 codex 里 BLOOMING PESTILENCE 与 PLAGUESURGE 中文同为「瘟疫爆发」——
  源即如此，照录不消歧
- Nurgle's Gift 军规 CONTAGION RANGE 节是 Wahapedia 图片（3 张 img），12" 上限句
  插在图片段与 AFFLICTED 节之间的文本位
- 审查 MEDIUM 备忘（沿 PR6）：sequence.py 已近 800 行——本 PR 新通道若需动
  sequence 先评估拆分（PR6 备忘的候选：_gather_params/_resolve_weapon 外移）
