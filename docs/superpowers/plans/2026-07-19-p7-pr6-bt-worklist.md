# P7-PR6 黑色圣堂 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Black Templars/`（5 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR1/PR4/PR5 裁定：
**FP 完整重印即整体替换**（未收录旧条目标 removed_11e）；change-list 外科应用；
fp_new 走 inserts 补录（fp11e- 前缀 synthetic id）。

**结构注意**：黑色圣堂在 Wahapedia/DB 体系下无独立阵营行，全部挂 `faction='SM'`
（faction_keywords 含 Black Templars）。本 PR 所有补丁按 BT 范围圈定，不越界改
其他战团共享行（如 DA/DW 各自的 Terminator Squad Teleport Homer 留给 SM FP 铺量时处理）。

## FP 内容面

- 3 分队：Marshal's Household（**全新**）/ The Living Miracle（**全新**，无战略仅
  1 增强）/ Wrathful Procession（**完整重印**——10 版 Grotmas「狂热祷文」三选一祷文
  机制被拆解：Chant of Deathless Devotion 升格为唯一分队规则且收窄为 CHAPLAIN，
  Rite of Perfervid Wrath 降格为战略）
- 0 兵牌新表（Defiler 类补录本 FP 没有）
- Rules Updates（p5）：军规誓言 1 条 + 既有分队/战略 2 条 + 兵牌技能 3 条 +
  关键词 2 类 + 核心技能变更 1 条；**无 FAQ 节**

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，11 条）

| 行 | 判定 | 说明 |
|---|---|---|
| abilities 000008526 军规 Templar Vows | drifted | Abhor the Witch, Destroy the Witch 誓言段外科替换：重骰冲锋改为「12" 内有敌 PSYKER 可选发动：重骰冲锋 + 必须接战 PSYKER」双弹点结构 + [PRECISION] 措辞改 melee attacks |
| detachments 000009842 rule_text | drifted | **完整重印整体替换**：Zealous Litanies 三选一祷文机制废弃 → Chant of Deathless Devotion（友方 CHAPLAIN 5+ InSv 对远程攻击）+ Restrictions 保留 |
| detachments 000009842 **name_en** | drifted | 'Zealous Litanies' → 'Chant of Deathless Devotion'（重印后规则名整个换掉；**扩 `_TEXT_TARGETS` 白名单新增 ("detachments","name_en")**，守卫逻辑与文本补丁完全同构） |
| stratagems 000009844002 FUELLED BY FAITH | drifted | 重印：WHEN/TARGET 收窄 CHAPLAIN（suffers a mortal wound），EFFECT FNP 5+→**4+** against mortal wounds |
| stratagems 000009844004 CASTIGATE THE DEMAGOGUES | drifted | 重印：TARGET 改 CHAPLAIN selected to fight；EFFECT 措辞改 melee attacks have [PRECISION] |
| enhancements 000009843005 Benediction of Fury | drifted | 重印：11 版措辞 This model's melee attacks have [DEVASTATING WOUNDS]（10 版为 bearer's melee weapons have the ... ability） |
| stratagems 000010393006 HERESY BEGETS RETRIBUTION | drifted | EFFECT 段整替：Retribution move 自带流程 → 11 版核心 **surge move of up to D6"** |
| detachments 000010395 Purge and Sanctify | drifted | 第二弹点整替：Righteous Zeal move 措辞 → **surge move + 就近目标点结算**（改选最近 objective 为 surge target 的替代结算） |
| abilities 000002795_a2 Sigismund's Heir | drifted | 整替：+2 冲锋骰 → 「12" 内有敌 CHARACTER 可选发动：重骰冲锋 + 必须接战 CHARACTER」+（Once per battle, **per army**）接战 CHARACTER 时近战 [DEVASTATING WOUNDS] |
| abilities 000002799_a1 Righteous Zeal | drifted | 整替：Righteous Zeal move 自带流程 → 11 版核心 **surge move of up to D6+2"** |
| abilities 000004138_a1 Teleport Homer | drifted | 外科：not within **9"** of any enemy models → **8"**（仅 BT 版 Terminator Squad 000004138；DA/DW/突击终结者等共享同名技能行不在 BT FP 授权范围） |

### 已滚入/已满足免补（identical）

- **Land Raider Crusader 加 LAND RAIDER 关键词**：000004139（BT 版）与 000000066
  keywords_json 均已含 "Land Raider"——Wahapedia 已滚入，零动作
- 新分队所涉单位均在库：Sword Brethren Squad 000002798 / Emperor's Champion
  000002795 / Execrator 000004135 / Crusade Ancient 000004136

### removed_11e（deactivations 7 条，Wrathful Procession 完整重印未收录）

- stratagems：BRUTE FERVOUR 000009844005 / ARMOUR OF CONTEMPT 000009844003 /
  VOICE OF DEVOTION 000009844007 / RELENTLESS MOMENTUM 000009844006
- enhancements：Pyrebrand 000009843002 / Sacred Rage 000009843003 /
  Taramond's Censer 000009843004

### fp_new（inserts 10 条）

- **Marshal's Household**（p2，id 组 fp11e-bt-marshals-*）：det 规则 Faith-Fuelled
  Resolve（SWORD BRETHREN SQUAD +1 OC）+ 战略 SLAYERS OF ABOMINATIONS（近战对
  MONSTER/VEHICLE +2 S）/ BLADE OF DETESTATION（冲锋后每接战模型掷 D6，4+ 致命伤
  上限 6）/ UNSPARING EXECUTION（撤退强制 desperate escape mode，战斗震慑 -1 hazard）
  + 增强 Fervent Exemplars（冲锋骰 +1）/ Inheritors of Sigismund（Fights First）
- **The Living Miracle**（p3，id 组 fp11e-bt-miracle-*）：det 规则 Anointed Champion
  （帝皇冠军近战可重骰 1 命中 + 1 致伤；本分队增强不占全军上限）+ 增强 Guiding Omens
  （首轮开始时三选三：六种圣兆技能——含 DEVASTATING WOUNDS 一次性/侦测 -3"/+2 A/
  被近战 [HAZARDOUS]/英雄干预 -1 CP/撤退 2+ D6 致命伤）
- **Wrathful Procession 重印新增**（p4，id 组 fp11e-bt-wrathful-*）：战略 RITE OF
  PERFERVID WRATH（CHAPLAIN 近战 +1 S）+ 增强 Adaptable Executioner（EXECRATOR
  近战 [CLEAVE 1] 或 [PRECISION] 二选一）
- 增强点数一律 cost=NULL（FP 不含点数、MFM 缓存无增强数据——沿 PR4/PR5 AAC 裁定诚实置空）

### fp_errata（兵牌数值/关键词层）——本 PR 零条目

- **Castellan / Crusade Ancient 核心技能 Remove 'Leader' add 'Support'**：DB 无
  core abilities 结构化载体（abilities 表只存命名技能；datasheets.leader_head/footer
  是展示层自由文本，无引擎消费者）——**无库面落点，记观察项**，等 Support 机制建模
  或 Wahapedia 滚入
- **FRAME 关键词新增跳过**（Gladiator×3/Impulsor/Land Raider Crusader/Repulsor×2）：
  沿 S4/PR5 裁定（测距词，引擎/检索无消费者）

### 中文名（name_patches 32 条）

- 有源配对（双子星黑色圣堂 codex V1.20 refine，zh_source=codex-10e）：
  - det 规则 4：热忱圣怒（Righteous Fervour）/ 净化！圣化！（Purge and Sanctify）/
    震慑突袭（Shock and Awe，神锤突击队=Godhammer Assault Force）/ 不朽忠诚祷言
    （Chant of Deathless Devotion——源自 codex 祷文名，重印升格后沿用）
  - 战略 24：狂热同袍 6（虔信推进/铁血矢志，恪尽职守！/为了帝皇的荣誉！/虔信之仇/
    异端必遭严惩！/无畏十字军）+ 复仇特遣队 6（拒绝倒下/洗罪祷言/扫清异端/
    重拾我们的荣誉！/颂扬圣者/狂热干预）+ 神锤突击队 6（永不停歇的进军/迅猛突袭/
    神皇铁拳/聚焦仇恨/谴责音阵/祝圣外壳）+ 愤怒巡游队 6（信仰驱动/严惩煽动者 +
    removed 行也配：狂热蛮力/蔑视战甲/虔诚之声/势不可挡——原文保留在库可检索，配名有益）
  - abilities 4：圣堂誓言（Templar Vows）/ 西吉斯蒙德传人（Sigismund's Heir）/
    正义狂热（Righteous Zeal）/ 传送信标（Teleport Homer）
- 自译标记（zh_source=self-translation-11e）：inserts 自带 name_zh——
  元帅家臣团（Marshal's Household）/信仰淬炼之毅（Faith-Fuelled Resolve）/
  屠灭邪物/憎恨之刃/无情处决；活体神迹（The Living Miracle）/受膏勇士
  （Anointed Champion）；极端怒火仪式（Rite of Perfervid Wrath，codex 祷文名沿用）
- enhancements 表无 name_zh 列，增强中文名不在本层（沿 PR1 结构约定）

### 观察项（不阻塞）

- Castellan / Crusade Ancient「Leader→Support」核心技能变更无库面载体（见上）；
  DSL 编码时对两单位的领队类技能加 not_modeled 注记
- 双子星 codex 的「执罚者」（page_019）与 DB Execrator=执裁者 用词分歧——DB 现值
  已有不冲突，不动
- Vowed Target（000008773）初判误归 BT——实为暗黑天使 Inner Circle Task Force 的
  分队规则（战略家族 000008775xxx 佐证），不入 BT 范围；10 版 BT 的 Righteous
  Crusaders 分队在 DB 无行（Wahapedia 只载现行四个 Grotmas 系分队）
- 六圣兆中文名（神皇之器/邪径先知/凶暴神视/复仇预兆/圣佑降临/审判先声）用于
  DSL 注记与开关文案（自译）
- 审查 MEDIUM 备忘（PR7+）：`engines/simulator/sequence.py` 已 787 行、逼近 800
  上限——下个阵营再加延迟条件类通道前先拆模块（候选：_gather_params/_resolve_weapon
  独立成文件，或延迟致伤合并逻辑外移）
