# P7-PR7 帝皇之子 fp_rules/fp_errata 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Emperor S Children/`（10 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态）。体裁沿 PR1/PR4/PR5/PR6 裁定：
**FP 完整重印即整体替换**；change-list 外科应用；fp_new 走 inserts 补录。

## FP 内容面

- 4 分队：Elegant Brutes / Frenzied Host / Spectacle of Slaughter（**全新**，各
  1 规则 + 3 战略 + 2 增强）+ Court of the Phoenician（**完整重印**——Wahapedia
  已收录整分队：2 规则行 + 6 战略 + 4 增强，无删减仅漂移）
- 1 兵牌：Defiler（EC 版 000004208 **整表已在库**，M12/T11/W18/OC5 与 FP 一致零动作）
- Rules Updates（p9）：6 既有分队 8 条 + 兵牌 8 条；FAQ 3 条（p10）

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，11 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010655007 CATALYTIC STIMULUS | drifted | 重印：EFFECT 段 Stimulus move 自带流程 → 11 版核心 **surge move of up to D6"** |
| stratagems 000010655003 PRIDEFUL SUPERIORITY | drifted | **cp_cost 2→1**（重印 CP 互换；扩 `_TEXT_TARGETS` 新增 ("stratagems","cp_cost") 通道，守卫同构） |
| stratagems 000010655002 CONTEMPTUOUS DISREGARD | drifted | **cp_cost 1→2**（与上互换） |
| enhancements 000010010002 Empyric Suffusion | drifted | 整替：0CP 英雄干预（6" 内友军色孽单位）→ **本单位被英雄干预时该次 -1 CP** |
| stratagems 000010015007 ARMOUR OF ABHORRENCE | drifted | EFFECT 段整替：targets a model in your unit → **targets your unit**（11 版口径） |
| stratagems 000009999005 DARK VIGOUR | drifted | TARGET 段 9"→**8"** 外科 |
| enhancements 000010002002 Faultless Opportunist | drifted | 整替：0CP 可重复 → **-1 CP 且不占用其他单位的使用** |
| stratagems 000010019007 VENGEFUL SURGE | drifted | EFFECT 段整替：Surge move 自带流程 → **surge move D6" + 非神眷冠军可重骰距离** |
| stratagems 000010019006 REFUSAL TO BE OUTDONE | drifted | 整替：+2 冲锋骰 → **12" 内接战敌军宣冲：重骰冲锋 + 必须接战**（BT 誓言同款结构） |
| abilities 000004090_a1 Scuttling Horrors | drifted | 整替：once per turn 9" 内 → **对方移动阶段 8" 内 + 自身未接战**（Chaos Spawn EC） |
| abilities 000004081_a1 Lethal Obsession | drifted | 整替：全弹同目标冲锋重骰 → **射击后选一被命中单位：冲锋重骰 + 必须接战之**（Chaos Terminators EC） |

### 已滚入/已满足免补（identical）

- **Court of the Phoenician 重印其余全部**：det 000010652 Sensational Performance /
  000010653 Master of the Pageant、PRIDEFUL/CONTEMPTUOUS/SINUOUS/CLOSE-QUARTERS/
  EUPHORIC 文本、4 增强（Tears of the Phoenix / Exalted Patron / Soulstain Made
  Manifest / Spiritsliver）——Spiritsliver 的 FP refine 截断段经原始 PDF 复核与 DB 一致
- ONTO THE NEXT 000010007002（WHEN/TARGET 已 11 版）；Mechanised Murder det 000010005
- Fulgrim **Serpentine 已在库**（000004077_a3，FP "add ability" Wahapedia 已加，文本逐字同）
- 武器三条全滚入：Flawless Blades Blissblade A=4 / Infractors+Tormentors Power sword S=5
- Heldrake EC Sv 已 3+

### removed_11e：零（Court 重印无删减）

### fp_new（inserts 18 条）

- **Elegant Brutes**（p2，fp11e-ec-brutes-*）：det Eager to Kill（EC TERMINATOR 落场
  回合冲锋 +1）+ 战略 DELIGHT IN AGONY（被 S>T 攻击致伤 -1）/ PSYCHEDELIC SOULFLAME
  （攻击 +2 S）/ WARP PLUNGE（战略预备队）+ 增强 Cacophonic Accompaniment（深打 +
  远程 [IGNORES COVER]）/ Frenzied Ferocity（[SUSTAINED HITS 1]）
- **Frenzied Host**（p3，fp11e-ec-host-*）：det Frantic Focus（BATTLELINE 加速/撤退
  回合攻击 +1 S；HOST tag 互斥注记）+ 战略 POSSESSIVE MANIA（目标点上被攻 AP-1）/
  AGONISED CACOPHONY（敌侦测 +6"）/ ABSOLUTE SENSORY OVERLOAD（射击不破 hidden）
  + 增强 Euphoric Crown（近战 +1 S）/ Howling Plate（远程 +1 AP）
- **Spectacle of Slaughter**（p4，fp11e-ec-spectacle-*）：det Entitled to Victory
  （FLAWLESS BLADES Fights First）+ 战略 HONOUR IS FOR FOOLS（近战 [PRECISION]）/
  SINGLE-MINDED STRIKE（冲锋穿越模型）/ INTOXICATED BY TRIUMPH（敌撤退后 D3+3" 移动）
  + 增强 Eager Patrons（+2" M）/ Beguiling Grotesquerie（免疫 snap shooting）
- 增强点数一律 cost=NULL（沿 PR4/PR5/PR6 AAC 裁定）

### fp_errata（兵牌数值/关键词层，Heldrake EC 000004092）

- M `20+"`→`12"` stat patch + **keyword_patches 删 Aircraft**（沿 PR5 WE Heldrake 同款）
- OC 0→'-' 不补（沿 PR5 格式差异裁定）；FRAME 新增跳过（Chaos Land Raider/Rhino，沿 S4）

### 中文名（name_patches 51 条）

- 有源配对（帝皇之子 10 版老湿腐 V1.05 refine，zh_source=codex-10e，中英对照标题）：
  - 军规 abilities 000009994 Thrill Seekers = 嗜欲恶徒
  - det 规则 7：优雅狂速（Quicksilver Grace/水银邪军）/ 绝伦剑术（Exquisite
    Swordsmanship/无双剑客）/ 机械化屠戮（Mechanised Murder/开膛车履）/ 魔性强化
    （Daemonic Empowerment/纵欲狂欢）/ 敬献黑暗亲王（Pledges to the Dark Prince/
    自负骄子）/ 斗技争宠（Internal Rivalries/色孽宠儿）
  - 战略 36（6 分队 × 6，码表见补丁文件；老湿腐 EN 标题笔误已归一：EMBRANCE→EMBRACE、
    VENGENFUL→VENGEFUL、HEIGHTED→HEIGHTENED、TEFFRIFYING→TERRIFYING、
    CRUEL RADIERS→CRUEL RAIDERS、CAPRCIOUS→CAPRICIOUS、ECSTATIC SLAUGHER→SLAUGHTER）
- 自译标记（zh_source=self-translation-11e）：Court of the Phoenician 面——det 规则
  惊艳献演（Sensational Performance）/ 盛典主宰（Master of the Pageant）+ 6 战略
  （催化激涌/傲然无敌/轻蔑无视/魅升灵焰→欣快激励/近身酷刑/蜿蜒突进）+ inserts 自带
  name_zh（新分队全套）
- Sublime Strike / Dark Radiance（库内有、FP 无源、codex 无源）名字留空宁缺勿错

### 观察项（不阻塞）

- **page_005 refine 缓存截断**（Spiritsliver 段止于 "Add 1 to"）——本单已用原始 PDF
  复核补全语义；该页需重跑 refine（与 tau page_020 同桶）
- FAQ 3 条（Unbound Arrogance 主将不在场誓约 0→1 / Terrifying Crescendo 可叠加 /
  Daemonic Empowerment×自带 SUSTAINED 武器 5+ 暴击）——语义澄清无库面改动，DSL 注记引用
- Frenzied Host 的 **HOST tag 互斥**（不能与另一 HOST 分队同取）——军表域约束，
  DB 无载体，插入行 rule_text 保留原句 + DSL not_modeled 注记
- Sublime Strike 分队（4 战略 + 2 增强 + det Dark Radiance）在库但不在本 FP——
  文本不动，DSL 按阵营全扫口径照常编码
