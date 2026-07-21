# P7-PR30 灵族（Aeldari）fp_rules 逐行 A/B 工作单（2026-07-21）

对照源：`data_refined/Faction Pack Aeldari/`（71 页，Legal from 2026-06-20，"first
iteration … all new"）vs `db/wh40k.sqlite`（faction='AE'）。体裁沿 PR1/PR4-PR29。

## FP 内容面

FP 目录：Detachments 2-11（Armoured Warhost / Fateful Performance / Path of the
Outcast / Twilight Flickers / Serpent's Brood / Eldritch Raiders / Corsair Coterie）、
Datasheets 12-21（Prince Yriel / Kharseth / Vyper / Starfang / Corsair Skyreavers）、
Imperial Armour 22-25、Rules Updates 22-24、Legends Datasheets 25+。

- **1 个 11 版整页重印分队**：**Armoured Warhost**——FP 只收 1 规则 + 2 增强 + 3 战略
  （11 版分队定式），且措辞整体 11 版化。库现是十版 1 规则 + 4 增强 + 6 战略。
  按 2026-07-16 用户裁 A（FP 完整重印即整体替换）：收录条目落 text_patch、
  未收录条目落 removed_11e。
- **3 个 11 版全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Fateful Performance**（规则 Acrobatic Onslaught + 增强 A Foot in the Future /
    Mistweave + 战略 Heroes' Fall / Exit the Stage / Deceptive Feint）
  - **Path of the Outcast**（规则 Far-Reaching Doom + 增强 Camouflaged Snipers /
    Assassins' Eye + 战略 Eldritch Suppression / Casting Back the Veil /
    Nomads of the Hidden Way）
  - **Twilight Flickers**（规则 Dance of Distortion + 增强 Shadowfall Masks /
    Prelude Performer + 战略 Presaged Rehearsal / Captivating Performance /
    Phantasmal Mirage）
- **3 个重印分队**：Serpent's Brood（p6-p7）/ Eldritch Raiders（p8-p9）/
  Corsair Coterie（p10-p11）——十版体裁完整重印（4 增强 + 6 战略未裁剪），
  逐字 A/B 后仅 3 条真漂移，其余免补。
- **Rules Updates**（p22-p23）：12 条分队层 + 18 条 datasheet 层。
- **Datasheets / Imperial Armour / Legends**：datasheet 层，本 PR 不落（观察项）。

### 关键裁定：Fateful Performance 是全新分队，不是 Ghosts of the Webway 改名

FP 的 Fateful Performance 与库内 Ghosts of the Webway 共用分队规则名
**Acrobatic Onslaught**，且两个增强/战略名（Mistweave / Heroes' Fall /
Exit the Stage）也重名，形似「重印改名」。三条反证坐实其为并存的全新分队：

1. FP p22 RULES UPDATES 明列 `GHOSTS OF THE WEBWAY DETACHMENT · Tricksters' Retort
   Stratagem, Target Section · Change 9" to 8"`——GotW 在 11 版仍在被勘误，未被取代。
2. 两条 Acrobatic Onslaught 正文不同：FP 版带 `ACROBATIC` 互斥标签、**无**
   TRAVELLING PLAYERS 段（Troupe 获 BATTLELINE/OC2 + 三个同名角色上限）；
   库现版恰恰相反。
3. Twilight Flickers 同样带 `ACROBATIC` 互斥标签——11 版新增的 ACROBATIC 分队族
   （Fateful Performance + Twilight Flickers）与旧 Harlequins 分队并存。

处置：insert 三分队，Acrobatic Onslaught 行挂 `expect_duplicate_name` + 证据注记
（`detachments` 的同名守卫分组是 `(name_en, faction)`，不挂会被误拦）。

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，16 条）

#### Armoured Warhost 11 版整页重印（6 条）

| 行 | 判定 | 说明 |
|---|---|---|
| detachments 000009768 Skilled Crews | drifted | 整替：删掉「Aeldari Vehicle Fly 单位重掷加速骰」从句，只剩 `Friendly AELDARI VEHICLE units' ranged attacks have [ASSAULT]` |
| enhancements 000009769002 Guiding Presence | drifted | 整替：`9"`→`6"`、选中面 model→**unit**、加 visible、效果限**远程**攻击 |
| enhancements 000009769004 Spirit Stone of Raelyth | drifted | 整替：治疗时点 Command phase→**Movement phase**（移动起止时），措辞 11 版化 |
| stratagems 000009770002 LAYERED WARDS | drifted | 整替：WHEN 由「致命伤被分配后」→「单位承受一点致命伤时」；EFFECT 去掉「直到阶段结束」限定 |
| stratagems 000009770006 SOULSIGHT | drifted | 整替：三项单骰重掷改为无序列表；删掉 fast dice rolling 附注 |
| stratagems 000009770004 VECTORED ENGINES | drifted | 整替：WHEN 由「Fly 载具撤退后」→「载具作撤退移动时」；EFFECT 改「该移动不剥夺射击资格」 |

#### 重印分队里的真漂移（3 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000010650006 WEAVING STRIDE（Serpent's Brood） | drifted | TARGET `within 9"` → **`8"`** |
| enhancements 000010704004 Archraider（Corsair Coterie） | drifted | Lord of Deceit 由「每次对手用战略即 +1CP」→ **「每回合一次，且改为可选（you can use this ability）」** |
| stratagems 000010705007 VENGEFUL SORROW（Corsair Coterie） | drifted | EFFECT 整替为核心术语 **surge move**（`Your unit can make a surge move of up to D6+1"`），删掉十版自造的 surge 展开段 |

#### RULES UPDATES（p22，7 条）

| 行 | 判定 | 说明 |
|---|---|---|
| stratagems 000009928004 SKYBORNE SANCTUARY（Aspect Host） | drifted | TARGET 加 **unengaged**；EFFECT 删掉「不在交战范围内」重复判据 |
| stratagems 000009900003 SKYBORNE SANCTUARY（Warhost） | drifted | 同上（FP 分两处列出，同一改法） |
| detachments 000009918 Strength from Death（Devoted of Ynnead） | drifted | Lethal Surge 整替为 **surge move of up to D6+1"**（十版的「Lethal Surge move + 掷 D6+1 + 可进交战范围」展开段全删） |
| stratagems 000009916005 TRICKSTERS' RETORT（Ghosts of the Webway） | drifted | TARGET `within 9"` → **`8"`** |
| stratagems 000009924004 UNSHROUDED TRUTH（Seer Council） | drifted | TARGET 段灵能者光环 `within 9"` → **`8"`**（⚠️ EFFECT 段「离所有敌军模型 9" 以上重新部署」FP **未改**，定点 replace 不连坐） |
| enhancements 000009907005 Higher Duty（Spirit Conclave） | drifted | 整替：「每回合一次 + 9"」→ **「对手移动阶段 + 8" + 本单位须未交战」** |
| stratagems 000009904005 DARING RIDERS（Windrider Host） | drifted | EFFECT `within 9" horizontally` → **`8"`** |

### 已滚入/已满足免补（identical）

- **RULES UPDATES 其余 5 条**：Army Rules 的 Star Engines（TRIGGER/EFFECT 库现文已逐字
  11 版）、Devoted of Ynnead 的 Lethal Intent（已是 `Normal move of up to D6+1"`）、
  Guardian Battlehost 的 Breath of Vaul（库现文与 change-to 逐字一致）、Warhost 的
  Fire and Fade Restrictions（已是 11 版态）、Windrider Host 的 Overflight
  （WHEN/TARGET/EFFECT 三段均已 11 版）。
- **Serpent's Brood**：分队规则 Boons of the Brood + 4 增强 + 5 战略（除 WEAVING
  STRIDE）与库现文逐字一致。
- **Eldritch Raiders**：2 条分队规则（Yriel's Own / Veterans of the Void）+ 4 海盗增强
  + 6 战略全部逐字一致，**零漂移**。
- **Corsair Coterie**：2 条分队规则（Relentless Raiders / Veterans of the Void）+ 3 增强
  + 5 战略逐字一致。
- **四个登舰行动分队**（Khaine's Arrow / Protector Host / Wraiths of the Void /
  Star-dancer Masque）：FP 未收录（登舰行动是独立赛制），库现文不动。

### removed_11e（deactivations 5 条）

Armoured Warhost 11 版重印未收录：

| 表 | id | 名字 |
|---|---|---|
| enhancements | 000009769003 | Harmonisation Matrix |
| enhancements | 000009769005 | Guileful Strategist |
| stratagems | 000009770003 | SWIFT DEPLOYMENT |
| stratagems | 000009770005 | CLOUDSTRIKE |
| stratagems | 000009770007 | ANTI‑GRAV REPULSION |

### fp_new（inserts 18 条）

3 规则 + 6 增强 + 9 战略，synthetic id 前缀 `fp11e-aeldari-`，增强 cost 置空
（FP 不含点数、MFM 缓存无增强数据，诚实置 NULL 而非猜）。

| 分队 | id 前缀 | 规则 | 增强 ×2 | 战略 ×3 |
|---|---|---|---|---|
| Fateful Performance | fp11e-aeldari-fateful | Acrobatic Onslaught（挂 expect_duplicate_name） | A Foot in the Future / Mistweave | HEROES' FALL / EXIT THE STAGE / DECEPTIVE FEINT |
| Path of the Outcast | fp11e-aeldari-outcast | Far-Reaching Doom | Camouflaged Snipers / Assassins' Eye | ELDRITCH SUPPRESSION / CASTING BACK THE VEIL / NOMADS OF THE HIDDEN WAY |
| Twilight Flickers | fp11e-aeldari-twilight | Dance of Distortion | Shadowfall Masks / Prelude Performer | PRESAGED REHEARSAL / CAPTIVATING PERFORMANCE / PHANTASMAL MIRAGE |

### fp_errata：零（观察项）

FP p23 的 datasheet 层改动沿死亡守望 / 圣血修女 / 混沌骑士 / 混沌恶魔 / 帝国机械教 /
混沌星际战士 / 星界军先例**不落本 PR**，逐条记为观察项：

- Crimson Hunter / Hemlock Wraithfighter：加 `FRAME` 关键字、M 与 OC 改 `'-'`
  （全库无 `-` OC 一律存 `'0'`，按 PR14 裁定功能等价保留）
- Ynnari Incubi 的 demiklaives（single blade）AP → `-2`
- Warlock Conclave / Warlock Skyrunners：Keywords 删 `CHARACTER`、Leader 段改 Bodyguard
  合并语义、Runes of Battle 改 `[IGNORES COVER]`
- Falcon / Wave Serpent 运输容量整替、Starweaver / Ynnari Venom 的登载条款、
  Warlock 的 Leader→Support、Rangers 的 Path of the Outcast 9"→8"、
  Asurmen / Baharroth / Yvraine / Corsair Voidreavers / Shadowseer / Farseer 兵牌技能改写、
  Aspect Shrine Token 能力整替
- p12-p21 的 5 张新 datasheet（Prince Yriel / Kharseth / Vyper / Starfang /
  Corsair Skyreavers）与 p22-p25 Imperial Armour、p25+ Legends——datasheet 层

## DSL 编码盘面（dsl_payloads/aeldari.json）

**182 项 = 1 军规 + 21 分队规则（18 库内 + 3 fp_new）+ 100 战略（91 库内 + 9 fp_new，
含 Army Rules 容器下的 6 道灵动机动行）+ 60 增强（54 库内 + 6 fp_new）**，
三态 **21 encoded / 25 partial / 136 not_modeled**。零新引擎通道、零新态势开关
（第七个连续纯编码 PR）。

灵族气质＝**战斗专注令牌 × 灵动机动 × 移动/预备队机动**。军规「战斗专注」是令牌经济 +
六道灵动机动（疾风之速 / 掠影 / 星辰引擎 / 突袭 / 抓住时机 / 隐没），全部落在移动域与
射击资格域；分队规则与战略也大量围绕移动、预备队进出、目标点控制、命运骰池、CP 经济、
死后反打与复活、过度警戒、侦测距离（11 版 hidden 机制）做文章——**全部无引擎载体**，
故 not_modeled 占 75%。

### 可编子集（21 encoded）

守方向：虚空幽魂 ×3（命中 -1，两相位）、闪电般的反应、幻影力场（携带者所在单位命中 -1）、
螺旋闪避（4+ 无效保护）、虚空石（5+ 无效保护）、灵骨装甲（伤害 -1）、阴森韧性（致伤 -1）、
微光石（远程致伤 -1）、伊瑞尔的表率（近战 FNP 5+）。
攻方向：刃之专注（冲锋近战重掷命中）、集火扫射（射击致伤 +1）、疾刺（近战重掷致伤）、
集中火力（射击 AP +1）、彼岸之刃（近战 [DEVASTATING WOUNDS]）、殷尼德之凝视
（Eldritch Storm 获 [DEVASTATING WOUNDS]，weapon_filter 锁死作用面）、灵视（Ynnari，
远程 [LETHAL HITS] + [IGNORES COVER]）、迅捷突击 / 预兆彩排（[LANCE]）、
无情杀手（伤害 +1，两相位）。

### 阶段门纪律（双向核对，测试有成对断言）

- WHEN 落在**单一**相位 → 挂 `phase_shooting` / `phase_melee`（12 条 + 11 条，
  测试 `SHOOTING_ONLY` / `MELEE_ONLY` 名单锁死）。
- WHEN 写「（对手/我方）射击阶段**或**近战阶段」、或原文根本未限相位 → **一律不加门**
  （16 条，测试 `NO_PHASE_GATE` 名单锁死）。过度加门＝欠建模，同属事实错误
  （PR13 反方向 MEDIUM 的同型判据）。
- 冲锋后触发（刃之专注 / 两条 [LANCE]）→ 用自含近战门的 `melee_charging`；
  测试另有 `test_no_bare_charging_tag_anywhere` 硬拦裸 `charging`
  （PR10/11/12/14 四次同型 HIGH 的护栏）。
- `half_range` 不自含相位门 → 唯一挂它的浪人伏击降 **partial** 并注明
  「须只在射击模拟下开启」（沿 PR29 狂暴排射先例）。

### 防高估（明确不编的类别）

| 类别 | 代表条目 |
|---|---|
| 「只重掷 1」/ 单骰重掷 / 伤害骰重掷 | 凯因之恩、灵视（Armoured Warhost）、沃尔之息、战士之路、殷尼德的使者、海盗应得的（基础从句） |
| 仅对特定伤害来源的 FNP | 层叠守护（仅致命伤）、守护符文（仅致命伤/灵能/[DEV] 暴击） |
| 特征值置数（非加值） | 无可逃避的厄运（Wailing Doom 射程 18"、伤害 8） |
| 多选一 / 择 N | 战士之路、超凡精准、蛇群之牙、獠牙之嘲、智慧之袍 |
| 「射击阶段 × 目标关键词」无复合 tag | 异种弹药（[ANTI-MONSTER/VEHICLE 5+] 限远程）、刺客之眼（对 CHARACTER +1 AP 限远程） |
| 「射击阶段 × S<T」无 tag | 再大的猎物（且原文是严格小于，非 ≤） |
| `[PSYCHIC]` 是武器关键词而非名字，weapon_filter 选不中 | 灵能毁灭者、预视打击 |
| 攻方**自身**战损档（引擎 target_below_* 是目标侧） | 殷尼德的使者第二分支 |
| 战斗中动态获得的令牌/状态标记 | 亡者的牧者的「复仇亡魂」令牌（同痛楚令牌型机制）、相位圣殿令牌 |
| 「成功命中即暴击」（阈值随 BS/WS 浮动，固定阈值无法等价） | 谋杀的戏谑 |
| 「已带某关键词才升级」的装配态分档 | 闪电火力第二分支 |
| 忽略 AP / 伤害 / S / 特征值层修正 | 预言者之眼（整条不编）、战士专注与灵视（只编命中骰分量，降 partial） |
| 移动 / 预备队 / 部署 / 冲锋 / 士气 / 目标点 / CP / 令牌 / 侦测距离 / 过度警戒 / 死后反打 / 复活 / 登载 | 绝大多数 not_modeled 条目 |

### 高估披露（partial 里按恒满足处理的前提）

- 目标点几何（不惜一切代价的防御、守护齐射、护盾节点、坚决防御、海盗应得的、
  斗篷与阴影）
- 登舰行动舱门几何（守护构装、艾尔达奈什之路）
- 光环几何 + 受益者是「范围内的另一友军单位」（圣所符文 9"、指引临在 6"、迷雾符文 12"、
  预警 / 无可逃避的命运的灵能者 9"）
- 攻/守方自关键词门（坚决防御的 GUARDIANS/DIRE AVENGERS、不惜一切代价的防御的四类模型、
  蛇群之赐的 HARLEQUINS MOUNTED/VEHICLE、扭曲之舞的 HARLEQUINS）
- 携带者本人限定（艾尔达奈什之路、借来的活力、病态之力、谋杀之相、织者的哀嚎）——
  引擎按单位面注入，多模型单位会高估，须以携带者单模型 loadout 模拟才等价
- 预备队入场状态（自天而降）
- weapon_filter 子串过选（手里剑风暴的 `shuriken` 会连带选中 shuriken rifle 等
  原文未列的武器）

### 适用面纪律（自审复核后重申，已落成测试护栏）

自审（code-reviewer）提出「11 条 encoded 战略的 TARGET 段带窄关键词限制却未注记」的
HIGH。**复核后判为不成立**，但把判据钉成了测试：

- 战略与增强是 **opt-in** 条目：`select_entries` 必须被点名才入选，所以原文 TARGET 段的
  单位类型限制（「One HOWLING BANSHEES or STRIKING SCORPIONS unit」/「排除 WRAITH
  CONSTRUCT」）是**玩家选择**，点名即声明，不计作未建模残量。
  跨 PR 证据（回查已并入 main 的载荷）：星界军 BRUTAL TRAINING（One MILITARUM
  TEMPESTUS unit）、FURIOUS CANNONADE（One Squadron unit）、混沌星际战士 BALEFIRE
  BOON（One Soul Forge unit）、死灵 QUANTUM DEFLECTION（One NECRONS VEHICLE unit）、
  METHODICAL MURDER（One NECRONS unit **excluding Monsters and Vehicles**）——
  全部是 `encoded`。本 PR 若降级会与 25 个已并载荷的判法相左。
- 分队规则相反：它**非 opt-in**（分队一匹配就自动施加），「Each time a〈窄关键词〉
  模型/单位……」限定的是**受益者集合**而非玩家选择；引擎无攻/守方自关键词门，注入到
  任何攻/守方都会生效，必须逐条注记并降 partial——本 PR 4 条（坚决防御 / 不惜一切代价
  的防御 / 蛇群之赐 / 扭曲之舞）。
- 例外面：战略里「受益面窄于或异于 TARGET 单位」的从句仍须注记（海盗应得的的完整重掷
  只给 ANHRATHE 单位）。

护栏：`test_self_keyword_note_only_on_non_opt_in_entries`（自关键词注记只许出现在 det
前缀的分队规则行上，且必须是 partial；opt-in 条目反面名单一并锁死）+
`test_narrower_than_target_clause_is_disclosed`。

### bearer 开关纪律（沿 PR29 最新判据）

`bearer_leading` / `defender_bearer_leading` 的语义是**「携带者正率领本单位」**：
只有幻影力场（携带者所在单位）与微光石（携带者所率相位战士单位）挂开关；
「只给携带者本人」与「受益者是范围内另一友军单位」的条目**一律不挂**
（测试 `test_aura_and_bearer_only_entries_have_no_bearer_toggle` 用 9 条反面名单锁死）。

## 验证

- `python -m db_compile fp-rules`：text 16 / deact 5 / inserts 18 全部 applied，零 mismatch。
- `python -m db_compile dsl-apply`：全库 2658 条（+182），三态
  encoded 192 / partial 545 / not_modeled 1921，零指纹让路零跳过。
- `pytest tests/ -q`：**1735 passed**（新增 `tests/test_simulator_dsl_pr30_payload.py` 62 项）。
- gold v3 基准：`benchmarks/v3_edition11/qa_agent_results_p7pr30.json` —— **97.9，
  零硬错（correct 94 / partial 2 / wrong 0）**，与 PR29 基线逐题 verdict 完全一致。

  ⚠️ 波动题记录（诚实披露）：同一份库与载荷跑了两次。第一次 96.9（correct 93 /
  partial 3 / wrong 0），唯一变动是 **#86「深入打击的完整规则是什么？」由 ✅ 转 ⚠️**；
  第二次 97.9 回到基线。逐题 diff + 检索源核对确认这是**检索侧波动而非回归**：
  第一次 #86 的 sources 是《太空死灵规则》《沃坦联盟》《钛帝国十版》等散块，
  第二次/PR29 则直接命中《Core Rules》第 80 页——同一问题在 agent 路径上命中的
  文档块不同导致判分不同。本 PR 是纯编码 PR，DSL/DB 补丁**不进 FAISS 索引**
  （未 ingest），检索侧零影响；#86 亦是记忆里已登记的既有波动题。
