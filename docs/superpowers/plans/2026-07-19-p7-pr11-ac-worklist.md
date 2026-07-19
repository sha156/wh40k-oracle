# P7-PR11 卡斯托迪斯 fp_rules 逐行 A/B 工作单（2026-07-19）

对照源：`data_refined/Faction Pack Adeptus Custodes/`（35 页，Legal from 2026-06-20，
"first iteration … all of the following content should be regarded as new"）vs
`db/wh40k.sqlite` 现值（Wahapedia 滚更态，faction='AC'）。体裁沿 PR1/PR4-PR10 裁定。

## FP 内容面

- **3 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Might of the Moritoi**（规则 March of the Honoured Dead + 增强 Interred Expertise /
    Auramite Sarcophagus + 战略 Flawless Construction / Unstoppable Advance /
    Prioritised Eradication）
  - **Silent Hunters**（规则 Skin-Crawling Disorientation + 增强 Encircling Hunter /
    Psyk-Out Grenades + 战略 Deathsong Scythes / Umbral Prosecution / Synchronised Inferno）
  - **Tharanatoi Hammerblow**（规则 The Hammer Falls + 增强 Mnemo-locked Shrine Cipher /
    Efficient Aggression + 战略 Hardened Resolve / Unleash the Lions / Electroexorcist
    Saturation）
  - A/B 已确认三者规则名/战略名/增强名在库**全 0 命中**（真全新）
- **2 个重印分队**：Lions of the Emperor（规则 Against All Odds + 6 战略 + 4 增强）、
  Solar Spearhead（规则 Auric Armour + 6 战略 + 4 增强）——DB 已收录、逐字一致**免补**
- **Imperial Armour 兵牌**（p9-34）+ **Rules Updates**（p35）+ FAQ

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，2 条）

| 行 | 判定 | 说明 |
|---|---|---|
| enhancements 000008930004 Martial Philosopher（Auric Champions） | drifted | 第三句整改：加「in your opponent's Movement phase」+ 触发距离 `9"` → **`8"`**（Rules Updates p35） |
| stratagems 000008922006 Taloned Pincer（Talons of the Emperor） | drifted | TARGET 段 `within 9"` → **`within 8"`**（Rules Updates p35 点名 9→8） |

### fp_errata：零

**所有 datasheet 数值/武器格已 11 版态一致，无补丁**：
- Shield-Captain on Dawneagle Jetbike T=7/W=8、Vertus Praetors T=7/W=5 均已滚入
- Salvo launcher（S10/AP-3/D6+1/[TWIN-LINKED]）、Vertus hurricane bolter（AP-1/D2）已滚入
- Quicksilver Execution 技能（2+ 每模型 2 致命伤）已 11 版态；Shoulder the Mantle 全文一致
- **观察项（不落库）**：① Valerian 加 Deep Strike——CORE 能力本 schema 无载体（同 PR10
  Firing Deck）；② FRAME 关键字 ×4（Anathema Psykana Rhino / Dawneagle Jetbike /
  Venerable Land Raider / Vertus Praetors）——fp_errata keyword_patches 机制**只删不加**
  主关键字列表（PR5 裁定），无法补 FRAME，且引擎无 FRAME 用途，记观察项

### 已滚入/已满足免补（identical）

- **Rules Updates 文本**：Assemblage of Might 规则（000008929）、Martial Mastery 首段
  （000008393）、Castellan's Mark 增强、Shoulder the Mantle 战略、Champion of the Imperium
  增强（仅差「(see left)」交叉引用体裁）——均已 11 版态一致
- **两重印分队全套**：Lions of the Emperor（Against All Odds 规则 + Defiant to the Last /
  Gilded Champion / Manoeuvre and Fire / Peerless Warrior / Swift as the Eagle /
  Unleash the Lions 6 战略 + 4 增强）、Solar Spearhead（Auric Armour 规则含 Moritoi
  Ancients/Keywords 子节 + Emperor's Vengeance / Flawless Construction / Punishment
  Inescapable / Relentless Persecution / Unstoppable / Wrathful Advance 6 战略 +
  Adamantine Talisman / Augury Uplink / Honoured Fallen / Veteran of the Kataphraktoi
  4 增强）——逐字一致

### removed_11e：零

### fp_new（inserts 18 条）

3 rules + 6 enhancements + 9 stratagems，synthetic id `fp11e-ac-*`。点数 `cost` 置空。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Might of the Moritoi | fp11e-ac-moritoi | March of the Honoured Dead | Interred Expertise / Auramite Sarcophagus | Flawless Construction / Unstoppable Advance / Prioritised Eradication |
| Silent Hunters | fp11e-ac-silent | Skin-Crawling Disorientation | Encircling Hunter / Psyk-Out Grenades | Deathsong Scythes / Umbral Prosecution / Synchronised Inferno |
| Tharanatoi Hammerblow | fp11e-ac-tharanatoi | The Hammer Falls | Mnemo-locked Shrine Cipher / Efficient Aggression | Hardened Resolve / Unleash the Lions / Electroexorcist Saturation |

**跨分队复用名**：Flawless Construction（Might of the Moritoi 新 vs Solar Spearhead 既有）、
Unleash the Lions（Tharanatoi 新 vs Lions of the Emperor 既有）——insert 去重键
(name_en, detachment) 因分队不同天然不撞，无需 expect_duplicate_name。

## DSL 编码盘面（custodes.json）

98 项（11 分队规则 + 53 战略 + 34 增强，含 inserts）全量逐条编码。卡斯托迪斯为精英
近战/载具阵营，可编率预计高于千子：大量命中/致伤/S/AP/A 特征值增益、[LANCE]/[PRECISION]/
[RAPID FIRE]/[BLAST]/[TWIN-LINKED]、无效保护无（金甲无 invuln 增益类）、FNP、守方 S>T 被伤
-1、+1 T 等。防高估候选：重骰1类（Interred Expertise/Auric Armour/Honoured Fallen——
重骰1≠重骰失败不编）、幸存反打（Defiant to the Last/Emperor's Vengeance）、按敌模型数动态
（Fierce Conqueror 每 5 敌 +2A）、once-per-battle 复活（Superior Creation）、移动/预备队/
目标控制类。
