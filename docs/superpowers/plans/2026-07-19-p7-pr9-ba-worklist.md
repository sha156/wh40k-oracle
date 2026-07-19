# P7-PR9 圣血天使 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Blood Angels/`（29 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR1/PR4-PR8 裁定：
**FP 完整重印即整体替换**（未收录旧条目标 removed_11e）；change-list 外科应用；
fp_new 走 inserts 补录（fp11e-ba-* synthetic id）。

**结构注意**：圣血天使沿 PR6 BT 先例为 SM 子阵营（无独立阵营行，faction='SM'，
faction_keywords 含 Blood Angels）。本 PR 所有补丁按 BA 分队清单圈定：
Liberator Assault Group / The Lost Brethren / The Angelic Host / Angelic
Inheritors / Rage-cursed Onslaught（在库 5）+ Legacy of Grace / Encarmine
Speartip / Wrath of the Doomed（fp_new 3）。

## FP 内容面

- 5 分队：Legacy of Grace / Encarmine Speartip / Wrath of the Doomed（**全新**，
  各 1 规则 + 2 增强 + 3 战略）+ Angelic Inheritors / Rage-cursed Onslaught
  （**完整重印**——Wahapedia 已整分队收录，规则/战略/增强逐字一致零漂移零删减）
- 10 张 **Legends 兵牌**（p10-29）：Brother Corbulo / Captain Tycho / DC 磁抓龙 /
  DCM 爆弹枪 / DCM 爆弹枪跳包 / Furioso 无畏 / Gabriel Seth / 智库无畏 /
  Tycho the Lost / 跳包圣血祭司——**全部在库**，数值/武器逐格一致；技能层 5 处
  真漂移（见下）
- Rules Updates（p9）：3 既有分队限制句 + AoC 措辞 + Angelic Host 增强/战略
  3 条 + 兵牌 6 类 + FAQ 1 条（Sanguinor 多单位接战：可以）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，9 条——全在兵牌技能层）

| 行 | 判定 | 说明 |
|---|---|---|
| abilities 000003835_a1 Black Rage（DC 磁抓龙，Legends） | drifted | **Legends 版语义**：任意攻击重骰命中 + 仅 12" 牧师条款（DB 被滚成主表版 melee+6"/12"——Rules Updates 的 Black Rage 改写只点名 6 张主表，Legends 全文重印为准） |
| abilities 000003836_a1 Black Rage（DCM 爆弹枪） | drifted | 同上（unit 措辞版） |
| abilities 000003837_a1 Black Rage（DCM 爆弹枪跳包） | drifted | 同上 |
| abilities 000000153_a2 Black Rage（Tycho the Lost） | drifted | 同上（model 措辞版） |
| abilities 000003835_a2 Frenzied Reprisal | drifted | 整替：被击后自由射/打 → **once per turn 近战阶段被攻后可出手（即使已打过）且必须下一个被选** |
| abilities 000000166_a2 Driven By Fury（主表 DC 无畏） | drifted | 整替：Driven by Fury move 自带流程 → 11 版核心 **surge move D6+2"**（触发改「损失伤」） |
| abilities 000002285_a2 Visions of Heresy（DCM 爆弹步枪） | drifted | 整替：0CP 坚守/英勇介入+重骰 → **重骰冲锋 + 坚守/英勇介入 -1 CP** |
| abilities 000000156_a2 Miraculous Saviour（Sanguinor） | drifted | 整替：预备队接战部署 → **(Once per battle, per army) 排除第一轮 + ingress move 必须接战**（FAQ：可同时接战多单位） |
| enhancements 000009190005 Gleaming Pinions | drifted | 整替：once per turn 9" 触发 → **对方移动阶段 8" 内 + 未接战 → Normal move 6"** |

### 已滚入/已满足免补（identical）

- **Angelic Inheritors 全套**（规则 000009834 天使遗产 + 6 战略 + 4 增强）与
  **Rage-cursed Onslaught 全套**（规则 000010644 Maddened Ferocity + 6 战略 +
  4 增强）逐字一致——Wahapedia 已收录 11 版态
- **主表 Black Rage ×6**（DC Captain ×2 / DC Marines ×3 / DC 无畏）：DB 已是
  11 版语义（melee 重骰 + 6" BA 人物或 12" 牧师条款），与 Rules Updates 仅
  「a model in this unit / this model」类体裁差异——语义等价免补
- AoC ×5（三既有分队 + 两重印分队副本）均已 'worsen AP by 1' 措辞；三既有分队
  规则行的**限制句已在**；DESCENT OF ANGELS 已 6"；DEATH FROM THE SKIES 已
  11 版全文
- 圣血卫队武器：encarmine blade WS2+ / spear A4 WS2+ 均已滚入
- 10 张 Legends 兵牌属性/武器全格一致（含 Blood Song/Dead Man's Hand/
  Heaven's Teeth/Blood Reaver/Blood Lance 特色武器全数值）

### removed_11e：零（两重印分队无删减）

### fp_new（inserts 18 条）

- **Legacy of Grace**（p2，fp11e-ba-grace-*）：det 规则 Legacy of the Angel
  （INFANTRY CHARACTER 加速/冲锋 +1，排除 COMMANDER DANTE；GRACE tag）——
  **⚠ 与天使继任者规则同名（GW 复用规则名）**，insert 同名守卫需
  `expect_duplicate_name` 显式豁免旗标（本 PR 扩展，守卫哲学不变：默认拦，
  豁免须带证据注记）+ 战略 MARTIAL PARAGON（LETHAL/SUSTAINED 二选一）/
  SOUL-DARKENED FURY（撤退强制 desperate escape）/ AURA OF THE ANGEL'S GRACE
  （被射击 5+ InSv）+ 增强 BLOOD BOIL（灵能 ANTI-非巨兽载具 5+ + 重骰伤害）/
  AUREOLE OF THE ANGEL（-3" 侦测）
- **Encarmine Speartip**（p3，fp11e-ba-speartip-*）：det Wrath of Angels
  （圣血卫队撤退可射/可冲）+ 战略 JUDGEMENT OF THE GOLDEN HOST（冲锋后 3+
  致命伤）/ INEXORABLE VALOUR（敌撤退后 D3+3" 移动）/ BLINDING BLURS OF
  VENGEANCE（被射击获隐匿）+ 增强 ANGELIC EXECUTIONER（近战 LETHAL/SUSTAINED
  二选一）/ SHADOW OF ABOMINATION（一次性近战 +1 D）
- **Wrath of the Doomed**（p4，fp11e-ba-doomed-*）：det Fanatical Celerity
  （死亡连加速自伤 D3+1 换可冲锋；DOOMED tag）+ 战略 DEATH BEGETS VENGEANCE
  （灭我连队者被恨：死亡连对其致伤 +1）/ NO BARRIER TO RETRIBUTION（MOBILE）/
  RAGE-FUELLED RESPONSE（被射击后 surge D6"）+ 增强 INSTINCTIVE INTERCEPTION
  （英勇介入 -1 CP）/ ON THE ARCHTRAITOR'S BRIDGE（近战 +2 A）
- 增强点数一律 cost=NULL（沿 PR4-PR8 AAC 裁定）

### fp_errata（兵牌数值/关键词层）——本 PR 零条目

- Sanguinary Priest「Remove 'Leader' add 'Support'」与跳包版 FP 直印 Support：
  DB 无 core abilities 结构化载体——沿 PR6 BT Castellan 裁定记观察项
- Baal Predator FRAME 关键词新增跳过（沿 S4/PR5-PR8 裁定）
- DCM 爆弹枪关键词 "Death Compamy"（FP 与 DB 同拼——FP 原文即笔误，同错不动）

### 中文名（name_patches 49 条）

- 有源配对（圣血天使 10 版 DavidZ V1.05 refine，zh_source=codex-10e，内容核实）：
  - det 规则 4：猩红饥渴（Red Thirst/解放者突击队）/ 崇高战殁（A Noble Death
    in Combat/迷失兄弟连）/ 炽翼翔空（Upon Wings of Fire/天使战群）/ 天使遗产
    （Legacy of the Angel/天使继任者）
  - 战略 24（4 codex 分队 × 6）：解放者（天使优雅/蔑视甲胄/野蛮回响/赤红狂怒/
    侵袭猛攻/无情突击）+ 迷失兄弟连（荣光牺牲/蔑视甲胄/最终复仇/狂怒猛攻/
    迷失盛怒/暴怒冲动——DavidZ 题 WRAITHFUL 已归 WRATHFUL）+ 天使战群（无拘热忱/
    蔑视甲胄/天使牺牲/武艺典范——DavidZ 题 EXEMPLAR 已归 EXEMPLARS/天使降临/
    死从天降）+ 天使继任者（聚焦怒火/蔑视甲胄/乍现优雅/为荣耀而战/巨翼荫蔽/
    直击燃空——后两条 DavidZ 英题笔误 DESENT OF ANGELS/DEATH FROM THE SKIES，
    经效果正文核实实为 IN THE SHADOW OF GREAT WINGS/UNTO THE BURNING SKIES）
  - abilities 13：黑怒 ×10（4 Legends 补丁行 + 6 主表行）/ 狂怒驱使（Driven By
    Fury）/ 大叛乱幻视（Visions of Heresy）/ 奇迹救赎（Miraculous Saviour）
- 自译标记（zh_source=self-translation-11e）：det 规则 000010644 癫狂凶暴
  （Maddened Ferocity，Rage-cursed 11e 新规则名）+ Rage-cursed 战略 5（严酷警示/
  无觉暴走/撕成碎片/不死之责/赤红之怒；蔑视甲胄沿既有译名）+ abilities 狂乱反噬
  （Frenzied Reprisal，Legends 磁抓龙版 codex 无源）+ inserts 自带 name_zh
  （新分队全套：天使遗产沿用/天使之怒/狂热神速 + 战略增强 9 条）
- enhancements 表无 name_zh 列，增强中文名在 DSL payload 层（沿 PR8 约定）

### 观察项（不阻塞）

- **GRACE/DOOMED tag 分队互斥**——军表域约束 DB 无载体，插入行 rule_text 保留
  原句 + DSL not_modeled 注记（沿 PR7 HOST/PR8 ENGINES 先例）
- Sanguinary Priest（含跳包版）core Leader→Support 无库面载体；DSL 编码时对
  领队类技能加 not_modeled 注记（沿 PR6）
- Legacy of the Angel 规则名跨分队复用（Legacy of Grace vs 天使继任者）——
  检索层同名两行属正常态；DSL 层按 det row id 物化互不干扰
- FAQ（Sanguinor ingress 可同时接战多单位）——语义澄清无库面改动
- Gabriel Seth「Flesh Tearers 视同 BA 但不可与其他 BA Epic Hero 同军」——
  军表域约束，DSL not_modeled 注记
