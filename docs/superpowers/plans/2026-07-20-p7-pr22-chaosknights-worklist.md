# P7-PR22 混沌骑士 fp_rules 逐行 A/B 工作单 + DSL 编码盘面（2026-07-21）

对照源：`data_refined/Faction Pack Chaos Knights/`（25 页，FACTION PACK VERSION 1.0，
Legal from 2026-06-20，"first iteration — all content should be regarded as new"）
vs `db/wh40k.sqlite`（`faction='QT'`）。体裁沿 PR1/PR4-PR21/PR24。

> **前置修复（本分支附带）**：main 的 HEAD `ccb59209` 是一次半完成的 merge
> （`feat/p7-pr18-spacewolves` → main），把冲突标记 `<<<<<<< / ======= / >>>>>>>`
> 直接提交进了 `db_compile/fp_rules_patches.json` + `tests/test_db_compile_fp_rules.py`
> + `tests/test_db_compile_dsl_apply.py`，导致 pytest **收集期即 SyntaxError**，全库无法跑。
> 本 PR 先按「HEAD（PR1..PR24）∪ PR18 太空野狼」结构化合并收口：JSON 侧序列化前做了
> 逐字节 round-trip 断言保证 HEAD 原文零改写，只并入分支独有的 4 text_patches +
> 10 deactivations + 17 inserts；测试侧把两边的计数与 id 集合取并集
> （inserts 249∪17=266、deactivations 30∪10=40、投影 1779+64=1843）。
>
> 另清掉了 gitignored 库里上一轮崩溃迭代残留的 **12 行 `fp11e-chaosknights-*` 孤儿投影**
> （2 分队 + 6 战略 + 4 增强，任何补丁文件里都没有对应条目）——沿既有纪律「清孤儿行而非改测试」。

## FP 内容面

FP 目录（page_001）声明 4 个分队，页 7-24 为 Imperial Armour 兵牌，页 25 为 Rules Updates。

- **2 个全新分队**（inserts，各 1 规则 + 2 增强 + 3 战略）：
  - **Bastions of Tyranny**（p2）：规则 Annihilate the Unworthy（KNIGHT TYRANT 打战栗目标
    命中 +1）；增强 Pterrorshade Rookery（+6" 侦测范围）/ Hate-filled Dominion（重投随机 A）；
    战略 Rune-cursed Stronghold（对致命伤 FNP 5+）/ Pitiless Focus（撤退后仍可射击）/
    Intimidating Reminder（敌单位 suppressed：攻击命中 -1）
  - **Hunting Warpack**（p3）：规则 Scenting Fear（每战斗轮一次 +6" 侦测范围，带 WAR DOGS
    tag 互斥）；增强 Soul-spoor Auspicator（HUNTSMAN +6" R）/ Snarling Rivalry
    （EXECUTIONER 远程 [IGNORES COVER]）；战略 Insensate Bloodthirst（近战 FNP 5+）/
    Leash of the Masters（射击后仍可 action）/ Stalking Focus（被远程攻击 AP 恶化 1）
  - A/B 已确认两个分队规则名/战略名在库 0 命中（真全新）
- **1 个完整重印分队**：**Iconoclast Fiefdom**（p4）——11 版把它整个重建成新的紧凑体例
  （1 规则 + 2 增强 + 3 战略），与库现存的十版内容（1 规则 + 4 增强 + 6 战略）**内容不同**，
  按 PR6 黑色圣堂 / PR18 太空野狼「完整重印替换」先例处理
- **1 个重印一致分队**：**Helhunt Lance**（p5-p6，1 规则 + 4 增强 + 6 战略）——逐条与库现文
  一致（Wahapedia 已滚入），**免补**
- **Rules Updates**（p25）：8 条 QT 条目逐条 A/B —— **全部已滚入，零 text_patch**
- **Imperial Armour Datasheets**（p7-p24，18 页）+ Knight Abominant Warp Storms 改动——
  datasheet 层，沿死亡守望/圣血修女先例不落本 PR（观察项）

### page_003 refine 截断回退

`page_003.md` 尾部在 STALKING FOCUS 的 EFFECT 处截断（止于 "Ranged attacks that target your"）。
按既有纪律回原 PDF（`data/Faction Pack Chaos Knights.pdf`，PyMuPDF 取第 3 页）补全：
> EFFECT: Ranged attacks that target your unit have ‑1 AP until that enemy unit has attacked.

## A/B 判定汇总

### 真漂移已补（fp_rules text_patches，3 条 —— 全部来自 Iconoclast Fiefdom 完整重印）

| 表 | 判定 | 说明 |
|---|---|---|
| detachments 000009764 `name_en` | drifted | 分队规则名 **Dreaded Masters → Wretched Thralls**：11 版规则只剩 WRETCHED THRALLS 一条，十版的 Dreaded Masters（Dread Tyrants 光环 + Dark Sacrifice）整段删除（沿 PR6 黑色圣堂重印换名先例，与 rule_text 整替配套） |
| detachments 000009764 `rule_text` | drifted | 整替：十版「Dread Tyrants 光环 + Dark Sacrifice 献祭换 [LETHAL HITS]/[SUSTAINED HITS 1] + 按战斗规模分档的 Damned 点数上限（250/500/750）」→ 11 版「Damned 上限统一 **500 点** + 友方 DAMNED **重投领导力检定**」 |
| stratagems 000009766002 AVENGE THE MASTERS! | drifted | 目标与施加方双漂移：十版「TARGET=刚被摧毁的己方骑士单位；Damned **模型**的攻击」→ 11 版「TARGET=**摧毁者敌军单位**；Damned **单位**的攻击」；marked 至战斗结束语义不变 |

### 重印未收录（fp_rules deactivations，removed_11e，9 条）

Iconoclast Fiefdom 十版条目，11 版完整重印未收录（原文保留、只打失效标记）：

| 表 | id | 名称 |
|---|---|---|
| stratagems | 000009766003 | WRETCHED MASSES |
| stratagems | 000009766004 | SOUL HUNGER |
| stratagems | 000009766005 | UNRESTRAINED RAGE |
| stratagems | 000009766006 | WORTHLESS CHATTEL |
| stratagems | 000009766007 | PRESERVE THE IDOLS |
| enhancements | 000009765002 | Profane Altar |
| enhancements | 000009765003 | Pave the Way |
| enhancements | 000009765004 | Tyrant's Banner |
| enhancements | 000009765005 | Diabolical Resilience |

### 补录插行（fp_rules inserts，16 条，id 前缀 `fp11e-chaosknights-`，cost 置空）

| 分队 | 规则 | 增强 | 战略 |
|---|---|---|---|
| Bastions of Tyranny（全新） | `-bastions` | `-bastions-e1/e2` | `-bastions-s1/s2/s3` |
| Hunting Warpack（全新） | `-hunting` | `-hunting-e1/e2` | `-hunting-s1/s2/s3` |
| Iconoclast Fiefdom（重印新增） | —（走 text_patch） | `-iconoclast-e1/e2` | `-iconoclast-s1/s2` |

Iconoclast 的两条增强 `detachment_id` 用库内真实分队 id `000000989`（分队本身已在库，
不造合成分队行）；两个全新分队的增强 `detachment_id` 用合成分队 id。
`cost` 一律置空（FP 不含点数、MFM 缓存无增强数据，诚实置空勿猜）。

### 已滚入 / 已满足免补（identical）

- **Rules Updates（p25）8 条逐条核对，全部已是 11 版态**：
  - ARMY RULES · Harbingers of Dread「Darkness」→ 库现文即 "This model has the Stealth ability."
  - HOUNDPACK LANCE · Animalistic Rage WHEN 段 → 库现文已含 "that has not been selected to attack this phase"
  - HOUNDPACK LANCE · Harrying Hounds TARGET `9"` → 库现文已是 **8"**
  - INFERNAL LANCE · Malefic Surge / Unnatural Fortitude → 库现文已是「选一项持续到阶段结束」两支
  - INFERNAL LANCE · Hellforged Construction EFFECT → 库现文已是 "worsen the Armour Penetration characteristic of that attack by 1"
  - LORDS OF DREAD · Claimed for the Dark Gods WHEN → 库现文已是 "Start of your Command phase."
  - LORDS OF DREAD · Mirror of Fates → 库现文已逐字为 11 版新文（**自审 MEDIUM 复核判为假警报**：
    复核 agent 无 shell、用二进制 grep 在 sqlite 文件里搜到 5 处 "Lord of Deceit" 便判定本行未更新；
    直接 `SELECT description FROM enhancements WHERE id='000010308006'` 证实库现文即 11 版文本，
    那 5 处命中分属 000010704004 / 000010672002 / 000010466003 / 000008490005 四条**其它阵营**
    增强与 000000461_a2 一条 ability，与本行无关。→ 免补）
  - TRAITORIS LANCE · Imperious Advance EFFECT → 库现文已含 "(the Super-heavy Walker ability does not apply while using this Stratagem)"
- **Helhunt Lance 全套**（Masters of the Pack 规则 + 4 增强 + 6 战略）逐条一致。其中
  Goaded Beast 的 FP 文写作压缩式 "make a surge move of up to D6\""、库现文写作 11 版核心
  surge move 展开式，语义同 → identical
- **零 fp_errata**（本 FP 的数值层改动全落在 p7-p24 的 Imperial Armour 兵牌，属观察项）

**观察项（不落库，datasheet / RAG 层，非 DSL 阻塞，留后续）**：
① p7-p24 的 Imperial Armour 兵牌 9 个单位（Chaos Acastus Knight Asterius / Porphyrion、
Chaos Cerastus Knight Lancer / Castigator / Acheron / Atrapos、Chaos Questoris Knight
Magaera / Styrix、War Dog Moirax）；② Knight Abominant 的 Warp Storms 改动
（移动阶段末 9" 内每敌单位 D6，3+ 吃 D3 致命伤）。

## DSL 编码盘面（`dsl_payloads/chaosknights.json`）

**覆盖面**：QT 全部 8 分队规则 + 39 战略 + 28 增强 = **75 条**
（= 库内 8 + 44 + 32 = 84 行 减去 9 行 removed_11e）。removed_11e 行**零覆盖**，沿 PR18 先例。

**三态：4 encoded / 16 partial / 55 not_modeled**。零新引擎通道、零新态势开关（纯编码 PR）。

混沌骑士与帝国骑士（PR21，0/18/61）气质同源——超重型步行机甲，技能重心在 Dread 技能选择、
Empowered 状态机、光环共享、侦测范围、致命伤/治疗、移动/据点/CP 经济，可编率同样低。

### encoded（4）

| 条目 | 分队 | 编码 |
|---|---|---|
| HELLFORGED CONSTRUCTION | Infernal Lance | 守方 (save, ap_improve, -1) × `phase_melee` |
| WARP VISION | Infernal Lance | 攻方 (save, ignores_cover) × `phase_shooting` |
| DIABOLIC BULWARK | Infernal Lance | 守方 (save, invuln, 4) × `phase_shooting` |
| BEASTHIDE MANIFESTATION | Helhunt Lance | 守方 (save, ap_improve, -1)，两相位不加门 |

### partial（16）

| 条目 | 分队 | 编码 | 残量 |
|---|---|---|---|
| Marked Prey（分队规则） | Houndpack Lance | (hit, extra_hits, 1)，两相位 | 限 WAR DOG + 指挥阶段点名 + 建军条款 |
| CONQUERORS WITHOUT MERCY | Traitoris Lance | (save, ap_improve, +1) × `melee_charging` | 后半句战栗检定 |
| DISDAIN FOR THE WEAK | Traitoris Lance | (fnp, 6) × `phase_melee` | 对战栗模型改 FNP 5+ 的状态门 |
| STORM OF DARKNESS | Traitoris Lance | (save, cover) × `phase_shooting` | Stealth+掩体两从句收敛为一份 |
| Veil of Medrengard | Traitoris Lance | (save, invuln 4)×射击 + (save, invuln 5)×近战 | 限携带者（`defender_bearer_leading`） |
| Knight Diabolus | Infernal Lance | (hit, bs_improve, 1) × `phase_melee` | [LANCE] 挂 Empowered；限携带者（`bearer_leading`） |
| Fleshmetal Fusion | Infernal Lance | (wound, t_improve, 1)，两相位 | D1 护甲骰 +1 挂 Empowered；限携带者 |
| RUNES OF DISDAIN | Lords of Dread | (damage, damage_reduction, 1)，两相位 | 限 CHARACTER 单位 |
| Blessing of the Dark Master | Lords of Dread | (save, cover) × `phase_shooting` | 一次性伤害改 0（SET）；限携带者 |
| HUNGRY FOR COMBAT | Houndpack Lance | (hit, crit_threshold, 5) × `phase_melee` | 须 2+ WAR DOG 单位同接战 |
| Panoply of the Cursed Knight | Houndpack Lance | (save, ap_improve, -1)，两相位 | 限携带者 |
| MERCILESS FUSILLADE | Helhunt Lance | (hit, extra_hits, 1)，两相位 | 强制同目标 + 至多两 WAR DOG 同享 |
| INTIMIDATING REMINDER | Bastions of Tyranny | 守方 (hit, modify, -1)，两相位 | suppressed 状态按已生效建模 |
| Snarling Rivalry | Hunting Warpack | (save, ignores_cover) × `phase_shooting` | 限 EXECUTIONER 单位 |
| INSENSATE BLOODTHIRST | Hunting Warpack | (fnp, 5) × `phase_melee` | 限 WAR DOG 单位 |
| STALKING FOCUS | Hunting Warpack | 守方 (save, ap_improve, -1) × `phase_shooting` | 限 WAR DOG + 须在目标标记范围内 |

### 阶段门纪律（本 PR 的双向核对）

- **单相位 WHEN → 必加门**：Fight phase 战略（HELLFORGED CONSTRUCTION / DISDAIN FOR THE
  WEAK / HUNGRY FOR COMBAT / INSENSATE BLOODTHIRST）挂 `phase_melee`；对手射击阶段战略
  （DIABOLIC BULWARK / STORM OF DARKNESS / STALKING FOCUS）与原文明写 Ranged/远程武器的
  （WARP VISION / Snarling Rivalry / Blessing of the Dark Master）挂 `phase_shooting`。
- **冲锋分量 → `melee_charging`**：CONQUERORS WITHOUT MERCY 的 WHEN 是 Fight phase 且目标
  须本回合冲锋过 —— 顺 WHEN 往后推「触发后本回合还剩哪些阶段能生效」＝只剩近战，且须冲锋，
  故落复合门（不是裸 `charging`，否则射击阶段会误放行）。
- **两相位 WHEN → 不得加门**（过度加门＝欠建模，同属事实错误）：BEASTHIDE MANIFESTATION /
  MERCILESS FUSILLADE（「射击阶段或近战阶段」）、RUNES OF DISDAIN、Marked Prey /
  Panoply / Fleshmetal Fusion / INTIMIDATING REMINDER（原文无相位措辞）一律 `condition: []`。
- **携带者限定必须挂开关**：5 条 bearer 增强分别挂 `bearer_leading` / `defender_bearer_leading`，
  否则「仅携带者模型」的加成会对整单位无条件注入（over-application）。
  反面：Snarling Rivalry / Soul-spoor Auspicator 原文是 "This unit's ranged attacks"
  （UPGRADE 整单位生效），**不挂** bearer 开关。

### not_modeled 的主因分布（55 条）

防高估不编，逐条带 `not_modeled_notes_zh`：

- **目标战栗（Battle-shocked）态**：引擎只有 `target_below_starting` / `target_below_half`
  战损档，无战栗态 → Annihilate the Unworthy 裸编 hit+1 会对所有目标过度施加
- **负关键词门**：CRUSHED LIKE VERMIN 的「排除 MONSTERS/VEHICLES」——引擎只能表达
  「有关键词」，裸编即过度施加
- **重投「1」（非重投失败）**：TITANIC DUEL、Final Howl
- **仅对致命伤的 FNP**：FERAL ARROGANCE、RUNE-CURSED STRONGHOLD（fnp 通道不分伤害来源）
- **Empowered / Dread 状态机与二选一单分支**：Malefic Surge 全家（含 Profane Symbiosis、
  Knight Diabolus / Fleshmetal Fusion / Bestial Aspect 的后半句）、Paragons of Terror、
  Aspect of the Beast、Malevolent Heraldry
- **SET 非增量**：Putrid Carapace 的 Sv 设定 2+、Blessing of the Dark Master 的伤害改 0
- **随机 A 的重投**：Hate-filled Dominion（attacks 通道只有 modify/blast 增量）
- **侦测范围（detection range）**：Scenting Fear、Pterrorshade Rookery、Coursing Thralls
- **异单位 / 异模型授予**：Avenge the Masters!（施加于友方 DAMNED）、Cruel Lashmaster、
  Iconoclast Idol、Throne Tyrannicus、Octagram of Conjuration、Masters of the Pack（光环自反射）
- **域外**：移动/冲锋/surge、据点与控制等级、CP 经济、预备队/部署、action、治疗、
  致命伤池、战栗检定、出手顺序、建军点数上限

## 验证

- `pytest tests/ -q` → **1430 passed, 0 failed**（含新增
  `tests/test_simulator_dsl_pr22_payload.py` 43 条：结构/DB 对账/指纹 + 攻守双向引擎级差分
  + `TestHonestyBoundaries` 对 10 个高频过度建模陷阱的反向断言）
- `python -m db_compile fp-rules` 二次运行全幂等：文本 112 / 中文名 291 / 失效标记 49 /
  插行 282，**让路 0、跳过 0、无效 0**
- `python -m db_compile dsl-apply`：applied 0 / already **1918**（1843 + 75），
  **fingerprint_mismatch 0、skipped 0**，三态 122 encoded / 413 partial / 1383 not_modeled
- 基准 `qa_bench.py --path agent`（gold v3，96 题）：**94 correct / 2 partial / 0 wrong，
  accuracy 97.9，零硬错**，产物 `benchmarks/v3_edition11/qa_agent_results_p7pr22.json`。
  与紧邻的 PR24 基线**逐题判定完全一致**（同样 94/2/0、同样 ⚠️ 落在 #41/#42、
  degraded_count 同为 34）——两道波动题都是**兽人**兵牌题（Boyz 技能漏项 / 近战武器档漏项），
  与混沌骑士无关；DSL/DB 补丁不进 FAISS 检索语料，检索侧零影响 → **确认非回归**
- 自审（code-reviewer）：**0 CRITICAL / 0 HIGH**；1 MEDIUM（Mirror of Fates）复核证实为
  假警报（见上）；1 LOW（缺工作单文档）即本文件
