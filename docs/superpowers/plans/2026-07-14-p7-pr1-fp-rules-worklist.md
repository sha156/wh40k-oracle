# P7-PR1 钛帝国规则文本漂移工作单（十版 DB vs 11 版 Faction Pack 逐行 A/B）

> 2026-07-14 产出。上游 spec：`docs/superpowers/specs/2026-07-14-p7-faction-dsl-pilot-design.md` §三。
> 比对方法：DB 文本去 HTML 标签，双方归一化（弯撇号→直撇号、U+2011/en-dash→'-'、空白折叠、小写）后
> 做 token 级 diff，全部结论经脚本机械核验（`scratchpad/compare_fp.py`），非目测。
> FP refine 缓存关键页（page_002/003/004/019/020）已逐页与 `data/Faction Pack Tau Empire.pdf`
> 原始 PyMuPDF 提取文本对过——page_002-004、019 忠实；**page_020 截断**（见"意外发现"第 1 条）。
> 机器版补丁草稿：scratchpad `fp_rules_patches_draft.json`（8 条 drifted，from_text 直接取自 DB 保证逐字节一致）。

## 统计摘要

| 结论 | detachments (10) | stratagems (44) | abilities (1) | 合计 |
|---|---|---|---|---|
| identical（Wahapedia 已滚入 11 版） | 1 | 1 | 1 | **3** |
| drifted（真漂移，进补丁 JSON） | 4 | 4 | 0 | **8** |
| not_in_fp（FP 未提及，十版文本 11 版仍现行） | 5 | 30 | 0 | **35** |
| review_needed（FP 完整重印未收录，疑被 11 版删除） | 0 | 9 | 0 | **9** |
| 合计（对账：55 = 3+8+35+9） | 10 | 44 | 1 | **55** |

另有 **fp_new 5 条**（不占 DB 行）：Advanced Acquisition Cadre 整个新分队（1 规则行 + 3 战略）
+ Auxiliary Cadre 新战略 Guided by Unity。

## 分队映射表（detachments 9 条规则行 ↔ 8 个战略分队名）

分队名拼写以 `enhancements.detachment_name` 为准（含弯撇号 Mont’ka）。id 相邻性与增强表双重印证。

| 分队名（战略/增强表用） | 规则行 id | 规则名（detachments.name_en） | 战略 id 段 | 战略数 | FP 覆盖方式 |
|---|---|---|---|---|---|
| Kauyon | 000008441 | Patient Hunter | 000008443xxx | 6 | p19 change-list |
| Mont’ka | 000008810 | Killing Blow | 000008812xxx | 6 | p19 change-list |
| Retaliation Cadre | 000008814 | Bonded Heroes | 000008816xxx | 6 | p19 change-list |
| Kroot Hunting Pack | 000008818 / 000008819 / 000008820 | Hunter’s Instincts / Skirmish Fighters / KEYWORDS（噪声行） | 000008822xxx | 6 | 未提及（p20 FAQ 提到 Hidden Hunters，佐证分队仍现行） |
| Starfire Cadre | 000009635 | Markerlight Precision | 000009637xxx | 4 | 未提及（见观察项 4） |
| Kroot Raiding Party | 000009644 | Guerrilla Ambushers | 000009646xxx | 4 | 未提及（见观察项 4） |
| Auxiliary Cadre | 000009838 | Integrated Command Structure | 000009840xxx | 6 | **p3 完整重印（整段替换体裁）** |
| Experimental Prototype Cadre | 000009982 | Superior Craftsmanship | 000009984xxx | 6 | **p4 完整重印（整段替换体裁）** |
| （FP 新增）Advanced Acquisition Cadre | — 无 DB 行 — | Expert Fieldcraft | — 无 DB 行 — | FP 3 条 | **p2 完整新分队，fp_new** |

Kroot Hunting Pack 一个分队占 3 条规则行（含噪声行），这就是"9 条真规则行对 8 个分队"的由来。

## 总表（55 行逐行结论）

### detachments（faction='TAU'，10 行）

| id | name_en | 结论 | FP 页 | 摘要 |
|---|---|---|---|---|
| 000008441 | Patient Hunter | identical | page_019 | FP change-to 与 DB 归一化后逐字一致，Wahapedia 已滚入 |
| 000008810 | Killing Blow | **drifted** | page_019 | 仅缺交叉引用 "(see For the Greater Good)"，语义无变化 |
| 000008814 | Bonded Heroes | **drifted** | page_019 | AP 加成门槛 9"→**8"**，实质数值改动 |
| 000008818 | Hunter’s Instincts | not_in_fp | — | Kroot Hunting Pack 规则，FP 未提及 |
| 000008819 | Skirmish Fighters | not_in_fp | — | Kroot Hunting Pack 规则，FP 未提及 |
| 000008820 | KEYWORDS（噪声行） | not_in_fp | — | 内容是真规则（Carnivore 得 Battleline），命名是 Wahapedia 抓取噪声，处置见下节 |
| 000009635 | Markerlight Precision | not_in_fp | — | Starfire Cadre 规则，FP 未提及（合法性观察项 4） |
| 000009644 | Guerrilla Ambushers | not_in_fp | — | Kroot Raiding Party 规则，FP 未提及（合法性观察项 4） |
| 000009838 | Integrated Command Structure | **drifted** | page_003 | 整段改写：Targeting Triangulation/18" 限瞄 → prey-marked/detection range/hidden 新机制 |
| 000009982 | Superior Craftsmanship | **drifted** | page_004 | +6" 射程适用面从全军 T’AU EMPIRE 收窄为 **BATTLESUIT CHARACTER units** |

### stratagems（faction='TAU'，44 行）

| id | detachment | name_en | 结论 | FP 页 | 摘要 |
|---|---|---|---|---|---|
| 000008443002 | Kauyon | A TEMPTING TRAP | not_in_fp | — | |
| 000008443003 | Kauyon | POINT-BLANK AMBUSH | not_in_fp | — | |
| 000008443004 | Kauyon | COORDINATE TO ENGAGE | not_in_fp | — | |
| 000008443005 | Kauyon | COMBAT EMBARKATION | not_in_fp | — | |
| 000008443006 | Kauyon | PHOTON GRENADES | **drifted** | page_019 | WHEN 段："has declared a charge"→"has selected its charge target" |
| 000008443007 | Kauyon | WALL OF MIRRORS | not_in_fp | — | |
| 000008812002 | Mont’ka | PINPOINT COUNTER-OFFENSIVE | not_in_fp | — | |
| 000008812003 | Mont’ka | AGGRESSIVE MOBILITY | not_in_fp | — | |
| 000008812004 | Mont’ka | FOCUSED FIRE | not_in_fp | — | |
| 000008812005 | Mont’ka | COMBAT DEBARKATION | not_in_fp | — | |
| 000008812006 | Mont’ka | PULSE ONSLAUGHT | not_in_fp | — | |
| 000008812007 | Mont’ka | COUNTERFIRE DEFENCE SYSTEMS | not_in_fp | — | |
| 000008816002 | Retaliation Cadre | FAIL-SAFE DETONATOR | not_in_fp | — | |
| 000008816003 | Retaliation Cadre | STIMM INJECTORS | not_in_fp | — | |
| 000008816004 | Retaliation Cadre | THE SHORTENED BLADE | identical | page_019 | FP 勘误 "3"→6""，DB 已是 6"（Wahapedia 已滚入） |
| 000008816005 | Retaliation Cadre | THE ARRO’KON PROTOCOL | not_in_fp | — | |
| 000008816006 | Retaliation Cadre | THE TORCHSTAR GAMBIT | not_in_fp | — | |
| 000008816007 | Retaliation Cadre | GRAV-INHIBITOR FIELD | not_in_fp | — | |
| 000008822002 | Kroot Hunting Pack | JOIN THE HUNT | not_in_fp | — | |
| 000008822003 | Kroot Hunting Pack | A TRAP WELL LAID | not_in_fp | — | |
| 000008822004 | Kroot Hunting Pack | EMP GRENADES | not_in_fp | — | |
| 000008822005 | Kroot Hunting Pack | THE GRISLY FEAST | not_in_fp | — | |
| 000008822006 | Kroot Hunting Pack | GUERRILLA WARRIORS | not_in_fp | — | |
| 000008822007 | Kroot Hunting Pack | HIDDEN HUNTERS | not_in_fp | — | p20 FAQ 直接引用该战略，佐证十版文本仍现行 |
| 000009637002 | Starfire Cadre | FIRING LINE | not_in_fp | — | DB 文本含 OCR 噪声 "PATHfINDER"（观察项 5） |
| 000009637003 | Starfire Cadre | RETREATING FIRE | not_in_fp | — | 同上 |
| 000009637004 | Starfire Cadre | RESPONSIVE VOLLEY | not_in_fp | — | 同上 |
| 000009637005 | Starfire Cadre | PULSE BARRAGE | not_in_fp | — | 同上 |
| 000009646002 | Kroot Raiding Party | BOARDING BLADES | not_in_fp | — | |
| 000009646003 | Kroot Raiding Party | SWEEPING AMBUSH | not_in_fp | — | |
| 000009646004 | Kroot Raiding Party | BRUTE FORCE | not_in_fp | — | |
| 000009646005 | Kroot Raiding Party | TANGLEBOMB BOLAS | not_in_fp | — | |
| 000009840002 | Auxiliary Cadre | EXPERIMENTAL MODIFICATIONS | **drifted** | page_003 | 11 版重写：时机改为"selected to attack"，效果缩写为 "+1 AP" |
| 000009840003 | Auxiliary Cadre | MULTISENSORY SCANNING | review_needed | page_003（缺席） | FP 完整重印仅 3 战略，本条未收录，疑删除 |
| 000009840004 | Auxiliary Cadre | INTERLOCKING MANOUEVRES | review_needed | page_003（缺席） | 同上 |
| 000009840005 | Auxiliary Cadre | PHEROMONE WAYPOINTS | review_needed | page_003（缺席） | 同上 |
| 000009840006 | Auxiliary Cadre | ALIEN EXPERTISE | **drifted** | page_003 | 11 版重写：从"全军 Advance 后可射/可冲"收窄为"本次 advance move 不妨碍冲锋" |
| 000009840007 | Auxiliary Cadre | GUIDED FIRE | review_needed | page_003（缺席） | 未收录；FP 新战略 GUIDED BY UNITY 定位相近但名称与效果均不同（S 加成 vs [LETHAL HITS]），不能按更名漂移处理 |
| 000009984002 | Experimental Prototype Cadre | AUTOMATED REPAIR DRONES | review_needed | page_004（缺席） | FP 完整重印仅 1 战略，本条未收录，疑删除 |
| 000009984003 | Experimental Prototype Cadre | REACTIVE IMPACT DAMPENERS | review_needed | page_004（缺席） | 同上 |
| 000009984004 | Experimental Prototype Cadre | EXPERIMENTAL WEAPONRY | review_needed | page_004（缺席） | 同上 |
| 000009984005 | Experimental Prototype Cadre | EXPERIMENTAL AMMUNITION | **drifted** | page_004 | 11 版重写：目标收窄为 BATTLESUIT CHARACTER，RESTRICTIONS 段删除 |
| 000009984006 | Experimental Prototype Cadre | THREAT ASSESSMENT ANALYSER | review_needed | page_004（缺席） | 未收录；且 11 版 Experimental Ammunition 已删掉与它互斥的 RESTRICTIONS，侧面印证其不复存在 |
| 000009984007 | Experimental Prototype Cadre | NEUROWEB SYSTEM JAMMER | review_needed | page_004（缺席） | 同上 |

### abilities（1 行）

| id | name_en | 结论 | FP 页 | 摘要 |
|---|---|---|---|---|
| 000008439 | For the Greater Good | identical | page_019 | FP change-to 与 DB 归一化后逐字一致（含 "(excluding FORTIFICATION..." 仅大小写差异），无需补丁——与已知样张结论一致 |

## drifted 条目 before/after 全文对照（8 条）

以下 before 为 DB 现存原文（含 HTML 原样），after 为拟替换的 11 版文本（保持 DB HTML 风格）。
与 `fp_rules_patches_draft.json` 逐条对应。

### 1. detachments 000008810 · Killing Blow（Mont’ka）· FP page_019 · change-list应用

唯一差异：插入交叉引用 "(see For the Greater Good)"。语义无变化，但按"DB 必须是 11 版现行文本"口径仍应补。

**before（DB）：**
> During the first, second and third battle rounds, ranged weapons equipped by `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` models from your army have the [ASSAULT] ability. During the first, second and third battle rounds, while a unit is a Guided unit, its ranged weapons have the [LETHAL HITS] ability.

**after（11 版）：**
> During the first, second and third battle rounds, ranged weapons equipped by `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` models from your army have the [ASSAULT] ability. During the first, second and third battle rounds, while a unit is a Guided unit **(see For the Greater Good)**, its ranged weapons have the [LETHAL HITS] ability.

### 2. detachments 000008814 · Bonded Heroes（Retaliation Cadre）· FP page_019 · change-list应用

实质数值改动：AP 加成门槛 9"→8"。除此之外 FP change-to 全文与 DB 归一化后一致。

**before（DB）：**
> Each time a T’au Empire Battlesuit model from your army makes a ranged attack that targets a unit within 12", improve the Strength characteristic of that attack by 1. If that attack targets a unit within **9"**, improve the Armour Penetration characteristic of that attack by 1 as well.

**after（11 版）：**
> Each time a T’au Empire Battlesuit model from your army makes a ranged attack that targets a unit within 12", improve the Strength characteristic of that attack by 1. If that attack targets a unit within **8"**, improve the Armour Penetration characteristic of that attack by 1 as well.

### 3. detachments 000009838 · Integrated Command Structure（Auxiliary Cadre）· FP page_003 · 整段替换

已知样张，全文改写：两个子技能全部换掉（Targeting Triangulation 光环 AP 加成 → Harnessed Alien Instincts
prey-marked/detection range；Localised Stealth Projectors 从 18" 限瞄改为 hidden 保持），并新增 AUXILIARIES
分队 tag 互斥句。prey‑marked 的 U+2011 不换行连字符已归一为 ASCII '-'。

**before（DB）：**
> Kroot and Vespid Stingwings units from your army have the following ability:`<br><br>``<b>`Targeting Triangulation (Aura):`</b>` While an enemy unit is within 9" of and visible to this unit, each time a ranged attack made by a friendly `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` model (excluding `<span class="kwb">`KROOT`</span>`, `<span class="kwb">`VESPID`</span>` `<span class="kwb">`STINGWINGS`</span>` and Titanic models) targets that enemy unit, improve the Armour Penetration characteristic of that attack by 1.`<br><br>`T’au Empire units (excluding `<span class="kwb">`KROOT`</span>` and `<span class="kwb">`VESPID`</span>` `<span class="kwb">`STINGWINGS`</span>` units) from your army have the following ability:`<br><br>``<b>`Localised Stealth Projectors (Aura):`</b>` While a friendly `<span class="kwb">`KROOT`</span>` or `<span class="kwb">`VESPID`</span>` `<span class="kwb">`STINGWINGS`</span>` unit is wholly within 6" of and visible to this unit, that `<span class="kwb">`KROOT`</span>` or `<span class="kwb">`VESPID`</span>` `<span class="kwb">`STINGWINGS`</span>` unit can only be selected as the target of a ranged attack if the attacking model is within 18".

**after（11 版）：**
> Friendly KROOT/VESPID STINGWINGS units have the following ability:`<br><br>``<b>`Harnessed Alien Instincts:`</b>` In your Shooting phase, this unit can select one visible enemy unit within 12". That enemy unit is prey-marked:`<br>`- While a unit is prey-marked, that unit has +3" detection range.`<br><br>`Friendly GHOSTKEEL BATTLESUIT/STEALTH BATTLESUITS units have the following ability:`<br><br>``<b>`Localised Stealth Projectors (Aura):`</b>` When a friendly KROOT/VESPID STINGWINGS unit within 6" of this unit has shot, those attacks do not prevent that unit from being hidden.`<br><br>`This detachment has the AUXILIARIES tag and cannot be taken with another AUXILIARIES detachment.

### 4. detachments 000009982 · Superior Craftsmanship（Experimental Prototype Cadre）· FP page_004 · 整段替换

实质收窄：+6" 射程从"全军 T’AU EMPIRE models"缩到"BATTLESUIT CHARACTER units"，并新增 RETALIATION tag 互斥句。

**before（DB）：**
> Add 6" to the Range characteristic of ranged weapons equipped by `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` models from your army

**after（11 版）：**
> Friendly BATTLESUIT CHARACTER units’ ranged attacks have +6" R.`<br><br>`This detachment has the RETALIATION tag and cannot be taken with another RETALIATION detachment.

### 5. stratagems 000008443006 · PHOTON GRENADES（Kauyon）· FP page_019 · change-list应用（仅 WHEN 段）

已知样张。FP 原文 WHEN 段用小写 "charge phase"，照录不擅改。TARGET/EFFECT 保持 DB 原文。
注意：新 WHEN（"selected its charge target"）与旧 TARGET 措辞（"selected as one of the targets of that
charge"）之间存在时序张力，FP 只改了 WHEN，本工作单不越权改 TARGET，PR2 编码时留意。

**before（DB，仅列 WHEN 段）：**
> `<b>`WHEN:`</b>` Your opponent’s Charge phase, just after an enemy unit has **declared a charge**.

**after（11 版，仅列 WHEN 段）：**
> `<b>`WHEN:`</b>` Your opponent’s charge phase, just after an enemy unit has **selected its charge target**.

（TARGET/EFFECT 段不变，完整替换文本见 JSON。）

### 6. stratagems 000009840002 · EXPERIMENTAL MODIFICATIONS（Auxiliary Cadre）· FP page_003 · 整段替换

**before（DB）：**
> `<b>`WHEN:`</b>` Your Shooting phase or the Fight phase.`<br><br>``<b>`TARGET:`</b>` One Kroot or Vespid Stingwings unit from your army that has not been selected to shoot or fight this phase.`<br><br>``<b>`EFFECT:`</b>` Until the end of the phase, improve the Armour Penetration characteristic of weapons equipped by models in your unit by 1.

**after（11 版）：**
> `<b>`WHEN:`</b>` Your Shooting phase or the Fight phase, when a friendly KROOT/VESPID STINGWINGS unit is selected to attack.`<br><br>``<b>`TARGET:`</b>` That KROOT/VESPID STINGWINGS unit.`<br><br>``<b>`EFFECT:`</b>` Your unit’s attacks have +1 AP.

### 7. stratagems 000009840006 · ALIEN EXPERTISE（Auxiliary Cadre）· FP page_003 · 整段替换

实质改动：十版效果是"全军 T’AU EMPIRE 单位 Advance 后仍可射击，Kroot/Vespid 还可冲锋"；11 版收窄为
"该 Kroot/Vespid 单位这次 advance move 不妨碍其宣告冲锋"（不再给射击、不再覆盖全军）。

**before（DB）：**
> `<b>`WHEN:`</b>` Your Movement phase.`<br><br>``<b>`TARGET:`</b>` One `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` unit from your army.`<br><br>``<b>`EFFECT:`</b>` Until the end of the turn, your unit is eligible to shoot in a turn in which it Advanced. If it is a Kroot or Vespid Stingwings unit, until the end of the turn, your unit is eligible to declare a charge in a turn in which it Advanced as well.

**after（11 版）：**
> `<b>`WHEN:`</b>` Your Movement phase, when a friendly KROOT/VESPID STINGWINGS unit is selected to make an advance move.`<br><br>``<b>`TARGET:`</b>` That KROOT/VESPID STINGWINGS unit.`<br><br>``<b>`EFFECT:`</b>` That move does not prevent your unit from being eligible to declare a charge.

### 8. stratagems 000009984005 · EXPERIMENTAL AMMUNITION（Experimental Prototype Cadre）· FP page_004 · 整段替换

实质改动：目标从"任意 T’AU EMPIRE 未射击单位"收窄为 BATTLESUIT CHARACTER；原与 Threat Assessment
Analyser 互斥的 RESTRICTIONS 段随 11 版文本删除（TAA 本身在 FP 重印中已不存在）。

**before（DB）：**
> `<b>`WHEN:`</b>` Your Shooting phase.`<br><br>``<b>`TARGET:`</b>` One `<span class="kwb">`T’AU`</span>` `<span class="kwb">`EMPIRE`</span>` unit from your army that has not been selected to shoot this phase.`<br><br>``<b>`EFFECT:`</b>` Select one of the following to apply to your unit until the end of the phase:`<br><ul><li>`Improve the Strength characteristic of ranged weapons equipped by models in your unit by 1.`</li><li>`Improve the Strength and Armour Penetration characteristics of ranged weapons equipped by models in your unit by 1, and those weapons have the [HAZARDOUS] ability.`</li></ul><br>``<b>`RESTRICTIONS:`</b>` You cannot target the same unit with the Experimental Ammunition and Threat Assessment Analyser Stratagems in the same phase.

**after（11 版）：**
> `<b>`WHEN:`</b>` Your Shooting phase, when a friendly BATTLESUIT CHARACTER unit is selected to shoot.`<br><br>``<b>`TARGET:`</b>` That BATTLESUIT CHARACTER unit.`<br><br>``<b>`EFFECT:`</b>` Your unit’s ranged attacks have:`<br><ul><li>`+1 S.`</li><li>`OR: +1 S, AP and [HAZARDOUS].`</li></ul>`

## review_needed 9 条（人工裁定项）

> **✅ 已裁定（2026-07-16，用户裁 A：重印即整体替换）**：9 条均视为 11 版已删除，
> `fp_rules_patches.json` 新增 `deactivations` 段置 `stratagems.fp_status='removed_11e'`
> （原文保留可回滚，name_en 守卫防 id 复用）。裁定前补充核证：重拉 Wahapedia 现网
> Stratagems.csv——9 条虽仍在现网，但同批 drifted 条文本仍是十版旧措辞、GUIDED BY UNITY
> 与 Advanced Acquisition Cadre 均缺席，证明 Wahapedia 尚未消化 FP p3/p4，"现网仍在"
> 不构成反证；FP 原文重印语义 + Experimental Ammunition 删互斥 RESTRICTIONS 侧证成立。
> 将来 Wahapedia 滚更这两页时 text_patches 三态守卫会自动让路告警，届时复核本裁定。
> P7 DSL 对账枚举与消费者应排除 fp_status='removed_11e' 行。

**共同背景**：FP 对 Auxiliary Cadre（p3）和 Experimental Prototype Cadre（p4）采用**完整重印体裁**——
整页给出 DETACHMENT RULES + ENHANCEMENTS + 全部战略，与 datasheet 侧 "This datasheet replaces the …
datasheet found in Codex" 的替换语义一致（page_010 明文）。已对 PDF 原文逐页核实，refine 缓存无内容丢失：
p3 确实只有 3 条战略（Experimental Modifications / Alien Expertise / Guided by Unity），p4 确实只有
1 条战略（Experimental Ammunition）。**按替换语义，未被重印收录的旧战略在 11 版应视为不存在**；但
本工作单的四分类口径里 "not_in_fp = 十版文本仍现行" 是为 change-list 体裁设计的，直接套用会得出
"这 9 条仍合法"的相反结论。两种读法冲突，宁可上报不擅断。

**建议处置**：按"FP 重印即整体替换"裁定这 9 条为 11 版已删除；fp_rules 不改文本，另加失效标记
（如新列 `fp_status='removed_11e'` 或进 fp_rules_patches 的 deactivate 清单），P7 DSL 对账枚举时排除。
若用户裁定保守处理，则维持原文并在 DSL 载荷标 not_modeled + 注记"11 版存废存疑"。

| id | name_en | DB 原文要点（完整原文见 DB，此处摘 EFFECT） | FP 侧证据 |
|---|---|---|---|
| 000009840003 | MULTISENSORY SCANNING | 重掷伤害骰 1（Kroot/Vespid 可全重掷） | p3 重印无此条 |
| 000009840004 | INTERLOCKING MANOUEVRES | 战斗阶段末 6" Normal move 或 Fall Back | p3 重印无此条 |
| 000009840005 | PHEROMONE WAYPOINTS | Advance 不掷骰改 +6" 移动 | p3 重印无此条 |
| 000009840007 | GUIDED FIRE | 射击武器 +1 S（近 Kroot/Vespid 则 +2） | p3 重印无此条；新条 GUIDED BY UNITY（9" 内 [LETHAL HITS]）名称效果均不同，不构成更名对应 |
| 000009984002 | AUTOMATED REPAIR DRONES | 回复 D3+1 伤 | p4 重印无此条 |
| 000009984003 | REACTIVE IMPACT DAMPENERS | S>T 时命中方 -1 伤害骰 | p4 重印无此条 |
| 000009984004 | EXPERIMENTAL WEAPONRY | 攻击次数骰可重掷 | p4 重印无此条 |
| 000009984006 | THREAT ASSESSMENT ANALYSER | 选发 [SUSTAINED HITS 1]/[LETHAL HITS]（或全要+[HAZARDOUS]） | p4 重印无此条；且 11 版 Experimental Ammunition 已删除与其互斥的 RESTRICTIONS，侧面印证 |
| 000009984007 | NEUROWEB SYSTEM JAMMER | 只能被 18" 内射击选中 | p4 重印无此条 |

## fp_new 5 条（FP 有、DB 无）

### Advanced Acquisition Cadre（page_002，整个新分队）

DB `detachments`/`stratagems`/`enhancements` 均无任何行。若 PR1 决定补录（建议补，否则 P7 对账枚举
永远缺一个分队），需要新 id 段。规则原文（refine 与 PDF 一致）：

1. **分队规则 Expert Fieldcraft**：In your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit is selected to shoot, those ranged attacks do not prevent your unit from being hidden.
2. **战略 MARKER BEACON（1CP）**：WHEN: End of your Movement phase. TARGET: One friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit. EFFECT: Select one objective your unit is controlling. That objective is secured.
3. **战略 MICRODRONE SUPPORT（1CP）**：WHEN: Your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit starts an action. TARGET: That unit. EFFECT: That action does not prevent your unit from being eligible to shoot.
4. **战略 AUTOREACTIVE CAMOUFLAGE（1CP）**：WHEN: Your opponent’s Shooting phase, when an enemy unit targets a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit, if that friendly unit is hidden. TARGET: That unit. EFFECT: Your unit has +1 Sv.

（另有 2 条增强 Negation Emitters / Unmasking Suite，enhancements 表事，超出本单三表范围，一并记录备 PR4。）

### Auxiliary Cadre 新战略（page_003）

5. **GUIDED BY UNITY（1CP）**：WHEN: Your Shooting phase, when a friendly T’AU EMPIRE unit (excluding KROOT/VESPID STINGWINGS units) is selected to shoot. TARGET: That T’AU EMPIRE unit. EFFECT: Your unit’s ranged attacks that target a unit within 9" of a friendly KROOT/VESPID STINGWINGS unit have [LETHAL HITS].

## 噪声行处置建议（detachments 000008820 'KEYWORDS'）

- 内容本身是**真规则**：Kroot Hunting Pack 的 Battleline 授予（"If you select this Detachment, Kroot
  Carnivore units from your army have the Battleline keyword."），FP 未改动，11 版仍现行——**不删**。
- 噪声只在命名层：Wahapedia 把版面小节标题 "KEYWORDS" 当规则名抓了下来，会污染检索与 P7 对账枚举。
- 建议：PR1 fp_rules 顺手把 `name_en` 改为可读名（如 `Keywords: Kroot Carnivores Battleline`，或
  `Pack Keywords (Kroot Hunting Pack)`），文本不动；P7 DSL 枚举时按 spec §零 F10 口径将其算进
  "TAU 非噪声行全集"之外单列，DSL 状态直接 not_modeled（编制层规则，模拟器无消费点）。

## 意外发现与观察项

1. **page_020.md refine 缓存截断（中优先级，建议重跑该页）**：refine 文件在 Stealth Battlesuits
   Forward Observers 条目中途戛然而止（末行 "…until"）。与 PDF 原文对照，缺失内容包括：Forward
   Observers change-to 的后半句、**Homing Beacon 9"→8" 勘误**、Razorshark/Sun Shark 加 FRAME 关键词
   + M/OC 改 '-'、Sun Shark Pulse Bombs 全文改写、**The Twin Lance Neocapacitor Shields 全文改写**、
   两条 FAQ。这些都是 datasheet/abilities 层的勘误，不影响本单 55 行结论，但属于 remaining-tasks T2
   对账同类问题（Astra 截断的翻版），且 Twin Lance 勘误与 FP p5 新 datasheet 直接相关。
2. **Wahapedia 滚入方向确实混杂**：FTGG、Patient Hunter、Shortened Blade（3"→6"）已滚入 11 版；
   Killing Blow 交叉引用、Bonded Heroes 9"→8"、Photon Grenades WHEN、Aux/EPC 全部重写**未**滚入。
   逐行比对的前提假设成立，任何"整表按方向批处理"的捷径都会错。
3. **FP p19 有 4 条增强勘误超出本单三表范围**，备 PR4：Through Unity, Devastation（Kauyon）、
   Coordinated Exploitation（Mont’ka）、Strike Swiftly 第二句（Mont’ka）、Puretide Engram Neurochip
   （Retaliation Cadre）——全部是 change-to 体裁，落 `enhancements.description`。
4. **Starfire Cadre 与 Kroot Raiding Party 在 FP 中零提及**（既无重印也无 change-list）。这两个是
   十版数字增补分队；11 版 FP 的"extra detachments"清单里没有它们，合法性存疑。按本单口径记
   not_in_fp（文本不动），但建议列入 T1-4 类外部源观察项，等 GW app/后续 FP 迭代确认存废。
5. **DB 侧 OCR/抓取噪声**（非漂移，PR1 可顺手修）：Starfire 4 条战略的 "PATHfINDER"；000009635
   Markerlight Precision 的 "MARKERLiGHT"。另 FP p40 的 "Crisis Starsycthe Battlesuits" 是 FP 侧原文拼写。
6. **11 版新机制词汇**（hidden / detection range / prey-marked / secured objective / "selected to
   attack" / advance move / Resolve Pre-battle Abilities step）集中出现在三个重印分队页，PR2/PR3 编码
   这些条目前需先确认 11 版核心规则语料里这些机制有对应词条，否则 DSL 只能 not_modeled。
7. **datasheet 层勘误清单**（p19-20，超出本单范围，备后续 datasheet/abilities 对账）：Crisis Sunforge
   ability、9 个载具加 FRAME 关键词、Ethereal 加 FACTION 行、Firesight Team、Kroot Trail Shaper ×2、
   Pathfinder Target Uploaded、Riptide Nova Charge + Ion Accelerator 武器档、Stealth Battlesuits ×2、
   Razorshark/Sun Shark、Twin Lance（后五项部分内容在 refine 缓存里缺失，见第 1 条）。
