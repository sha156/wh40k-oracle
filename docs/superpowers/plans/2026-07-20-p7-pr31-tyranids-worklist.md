# P7-PR31 吞噬者（Tyranids）Faction Pack A/B 工作单 + DSL 编码盘面

- **分支**：`feat/p7-pr31-tyranids`
- **阵营**：Tyranids，DB `faction='TYR'`（`enhancements.faction_id='TYR'`）
- **FP 版本**：Faction Pack Tyranids v1.0，2026-06-20 起适用于竞技对局，31 页
- **语料**：`data_refined/Faction Pack Tyranids/page_001..031.md`；
  **page_019 的 refine 缓存尾部截断**，整块漏掉 5 个 RULES UPDATES 条目，
  已回原 PDF（`data/Faction Pack Tyranids.pdf`，PyMuPDF）逐条捞回（见 §一.4）
- **结论一句话**：DB 已滚入约七成 11 版内容；真漂移 16 条文本补丁 + 6 条 removed_11e
  + 13 条 fp_new inserts；DSL 全量编码 **124 条（16 encoded / 19 partial /
  89 not_modeled）**，零新引擎通道、零新态势开关（只复用既有的 `bearer_leading` 与
  `defender_bearer_leading` 两个通用假设门）

---

## 一、FP 内容面（31 页逐页归类）

| 页 | 内容 | 处置 |
|---|---|---|
| 1 | 封面 + 目录 | — |
| 2 | **Ambush Predators** 全新分队（1 规则 + 2 增强 + 3 战略） | fp_new inserts ×6 |
| 3 | **Talons of the Norn Queen** 全新分队（1 规则 + 2 增强 + 3 战略） | fp_new inserts ×6 |
| 4 | **Warrior Bioform Onslaught** 11 版整页重印（1 规则 + 2 增强 + 3 战略） | text ×5 + deact ×6 + insert ×1 |
| 5-6 | **Subterranean Assault**（1 规则 + 4 增强 + 6 战略） | 与库现文逐字一致 → **免补** |
| 7-14 | Datasheets：The Red Terror / Tyranid Prime with Lash Whip / Raveners / Hyperadapted Raveners | 库内已有（Wahapedia 已滚更）→ 观察项 |
| 15-18 | Imperial Armour：Harridan / Hierophant | 库内已有 → 观察项 |
| 19-21 | **RULES UPDATES + FAQS** | 见 §一.3 / §一.4 |
| 22-31 | Legends：Dimachaeron / Sky-slasher Swarms / Malanthrope / Barbed & Scythed Hierodule | 库内已有 → 观察项 |

### 一.1 两个全新分队（库内 0 命中，已核）

`SELECT id FROM stratagems WHERE detachment='Ambush Predators' AND id NOT LIKE 'fp11e-%'`
与 enhancements 同查均返回空；`Talons of the Norn Queen` 同。故按 fp_new 补录，
id 前缀 `fp11e-tyranids-`，`cost` 诚实置空（FP 无点数、MFM 缓存无增强数据）。
该前置判据已钉成测试 `test_new_detachments_have_zero_prior_db_rows`。

### 一.2 Warrior Bioform Onslaught 整页重印（十版 4 增强 + 6 战略 → 11 版 2 + 3）

沿 2026-07-16 裁定「FP 完整重印即整体替换」，同 PR5/PR6/PR8/PR18/PR22/PR28/PR29/PR30 先例。

| FP 条目 | 库内对应 | 判定 |
|---|---|---|
| 分队规则 LEADER-BEASTS | `000009736` | **drifted** — 删掉十版「未受战斗震撼时 OC 3」从句 |
| 增强 ELEVATED MIGHT | `000009737005` | **drifted** — 整条改写（十版「加速回合可冲锋」→ 11 版「近战重掷致伤 + AP+1」） |
| 增强 OCULAR ADAPTATION | `000009737003` | **drifted** — 「任意攻击 +1 命中」收窄为「近战攻击 +1 命中」 |
| 战略 SYNAPTIC MICRONODES | `000009738005` | **drifted** — WHEN 改移动阶段结束、EFFECT 改 11 版「目标点被确保」术语 |
| 战略 PARASITIC PAYLOAD | `000009738006` | **drifted** — TARGET 放宽到全体 TYRANID WARRIORS、删掉「目标本回合不得享有掩体」 |
| 战略 ALIEN PHYSIOLOGY | 无同名行 | **fp_new** — `fp11e-tyranids-wbo-s1` |
| —（未收录） | `000009738002` SYNAPTIC AMPLIFICATION | **removed_11e** |
| —（未收录） | `000009738003` SPONTANEOUS HYPERCORROSION | **removed_11e** |
| —（未收录） | `000009738004` RESTORATIVE IMPULSE | **removed_11e** |
| —（未收录） | `000009738007` SYNAPTIC SHIELD | **removed_11e**（其「S>T 则致伤 -1」机制由 ALIEN PHYSIOLOGY 承接：改名 + 由「仅远程 + 无尽群兽配对」放宽到「射击与近战通吃」，故按重印替换而非改名处理） |
| —（未收录） | `000009737002` Synaptic Tyrant | **removed_11e** |
| —（未收录） | `000009737004` Sensory Assimilation | **removed_11e** |

### 一.3 RULES UPDATES（page_019 refine 版可见部分）

| 条目 | 库内 id | 判定 |
|---|---|---|
| 军规 Shadow in the Warp | `abilities 000000707` | **identical** → 免补 |
| 军规 Synapse | `abilities 000000705` | **identical** → 免补 |
| Assimilation Swarm / Feed the Swarm | `detachments 000008411` | **identical** → 免补 |
| Assimilation Swarm / Instinctive Defence | `enhancements 000008412003` | **drifted** — 英勇干预由 `0CP` 改为 `-1 CP` |
| Crusher Stampede / Enraged Behemoths | `detachments 000008403` | **identical** → 免补 |
| Crusher Stampede / Untrammelled Ferocity | `stratagems 000008422005` | **identical** → 免补 |

### 一.4 ⚠️ refine 截断段：page_019 尾部整块漏掉的 5 条（PyMuPDF 兜底捞回）

`data_refined/.../page_019.md` 在 `Untrammelled Ferocity` 的第二个项目符号处硬截断
（`…on a 1, your unit is Battle-sh`），此后整块 5 个条目在 md 里**完全不存在**。
回原 PDF 第 19 页取全文后逐条 A/B：

| 条目 | 库内 id | 判定 |
|---|---|---|
| Synaptic Nexus / Reinforced Hive Node Effect | `stratagems 000008556005` | **identical** → 免补 |
| **Unending Swarm / Insurmountable Odds** | `detachments 000008407` | **drifted** — 十版整段 Surge move 描述 → 11 版核心 `surge move of up to D6"` 术语 |
| **Vanguard Onslaught / Hypersensory Scillia, Target Section** | `stratagems 000008418005` | **drifted** — TARGET 段两处 `9"` → `8"`（EFFECT 段的 `6"` FP 未改，**不许连坐**） |
| Vanguard Onslaught / Neuronode | `enhancements 000008417005` | **identical** → 免补 |
| **Datasheets / Biovores, Seed Spore Mine** | `abilities 000000491_a1` | **drifted** — `9"` → `8"`（同句 `48"` 投放半径 FP 未改，不许连坐） |

> **教训复用**：`verify_ok:true` 抓不到页尾截断（PR29 已记）；本 PR 是**同一坑的加强版**
> ——截断处之后不是"半句话"，而是**整块 5 个条目静默消失**，其中 3 条是真漂移。
> 判据：RULES UPDATES 页只要 md 结尾不是 FAQS 或下一节标题，一律回 PDF 复核。

### 一.5 DATASHEETS 层（page_019 尾 + page_020）逐条 A/B

| 条目 | 库内 | 判定 |
|---|---|---|
| Broodlord / Parasite of Mortrex 加 `SYNAPSE` + FACTION 技能 | `units 000000463` 等 | **already** — 库内 Broodlord 关键词已含 SYNAPSE → 免补 |
| **Carnifexes / Blistering Assault** | `abilities 000000490_a1` | **drifted** — 整条改写为核心 surge move 术语 |
| Exocrine / bio-plasmic cannon S→9 | `weapons` | **already**（库现值 S=9）→ 免补 |
| Hive Tyrant / Onslaught | `abilities 000000460_a2` | **identical** → 免补 |
| **Harpy / Spore Mine Cysts** | `abilities 000000485_a1` | **drifted** — 触发时机由「结束普通移动」改为「对手近战阶段结束」，孢子雷放置 `9"`→`8"` |
| Hive Tyrant · Winged Hive Tyrant / Will of the Hive Mind | `abilities 000000460_a1` 等 3 行 | **非语义措辞差**（库 `that usage of that Stratagem` vs FP `that use of that Stratagem`）→ **不落补丁**，此处披露 |
| Mawloc / Raveners / Trygon 加 `VANGUARD INVADER` | `units` ×6 | **already** → 免补 |
| Neurolictor 加 `SYNAPSE` | `units 000003885/000002753` | **already** → 免补 |
| Norn Assimilator 加 `HARVESTER` | `units 000002752` | **already** → 免补 |
| Psychophage：M→12" / Bio-stimulus 改写 / 加 `SMOKE` / 爪牙 A→6 AP→-2 | `models`+`weapons`+`abilities`+`units` | **already**（四项库现值全对）→ 免补 |
| **The Swarmlord / Malign Presence** | `abilities 000000461_a2` | **drifted** — 删掉「须为 WARLORD」前提、改每回合一次主动技能；十版指向 2024 平衡数据板的设计者注记随之作废 |
| Tyrannofex / Rupture Cannon D→D6+6 | `weapons` | **already** → 免补 |
| Trygon / Subterranean Tunnels | `abilities 000000493_a1`/`000003887_a1` | **identical** → 免补 |
| **Sporocyst / Seed Mucolids** | `abilities 000000498_a1` | **drifted** — `9"`→`8"`（同句 `18"` 投放半径不许连坐） |
| **Termagants / Skulking Horrors** | `abilities 000000468_a1` | **drifted** — 整条改写：限定到对手移动阶段、`9"`→`8"`、删「每回合一次」 |
| **Von Ryan's Leapers / Pouncing Leap** | `abilities 000002693_a1` + `000003888_a1` | **drifted** — `0CP` → `-1 CP` 且改为不阻断其他单位本阶段使用；库内 TYR 版与 GC 共用版两行同名同文，**一起补** |
| Harpy · Hive Crone：移除 Hover、M 与 OC → `'-'` | `models 000000485/000000486` | **观察项，不落本 PR**（见下） |

**Harpy / Hive Crone 的 `'-'` 裁定（沿既有先例，不新裁）**：
- `OC → '-'`：P7-PR5 已就同型改动裁过「功能等价且库无 `'-'` 先例，防下游 int 解析破坏」
  （见 `db_compile/fp_errata_patches.json` 的 `_comment`），此裁定继续适用；
- `M → '-'`：P7-PR30 把灵族 Crimson Hunter / Hemlock 的**同型 M·OC→`'-'`** 明确列为
  观察项未落库，本 PR 沿同一先例保持一致；
- `Remove 'Hover'`：库内 Hover 是 `owner_id` 为空的核心技能行（`abilities 000008342`），
  与 Harpy/Hive Crone 之间无关联行，"移除"无可施加对象。

→ **本 PR 零 fp_errata**（同 PR9/PR20/PR23/PR26/PR30）。

### 一.6 FAQS（page_020-021，13 问）

全部是裁决性问答，不改任何条目正文，不落补丁。其中两条与本 PR 判定互证：
- 「Subterranean Assault 分队下由隧道标记登场时 Mawloc 的 Terror from the Deep 是否触发？→ 否」
  ——佐证 Subterranean Assault 在 11 版仍现役（非被替换分队）；
- 「Venomthrope 的 Foul Spores 是否给含 Hive Tyrant 的合并单位 Stealth？→ 否，该单位有
  MONSTER 关键词而技能排除 MONSTER」——负关键词门，与既有「负关键字门无载体」判据一致。

---

## 二、A/B 判定汇总

| 类别 | 条数 |
|---|---|
| `text_patches`（真漂移） | **16**（分队规则 2 + 增强 3 + 战略 3 + 兵牌技能 8） |
| `deactivations`（removed_11e） | **6**（WBO 重印未收录：战略 4 + 增强 2） |
| `inserts`（fp_new） | **13**（两全新分队各 1 规则 + 2 增强 + 3 战略 = 12，WBO 新增战略 1） |
| `name_patches` | 0（本 PR 不做中文名配对；FP 全新条目的 `name_zh` 随 insert 一次写入） |
| `fp_errata` | **0**（见 §一.5） |
| `identical` / `already`（免补） | 19 条逐条核过（§一.3/§一.5/§一.6） |

复现命令：

```powershell
.\.venv\Scripts\python.exe -m db_compile fp-rules     # 幂等：应用 0 / 幂等 181
.\.venv\Scripts\python.exe -m db_compile dsl-apply    # 幂等：应用 0 / 幂等 2782
```

---

## 三、DSL 编码盘面（124 条）

### 三.1 总览

| 表 | 条数 | encoded | partial | not_modeled |
|---|---|---|---|---|
| `abilities`（2 军规 + 14 分队规则） | 16 | 0 | 2 | 14 |
| `stratagems`（60 库内 + 7 fp_new） | 67 | 11 | 9 | 47 |
| `enhancements`（37 库内 + 4 fp_new） | 41 | 5 | 8 | 28 |
| **合计** | **124** | **16** | **19** | **89** |

零新引擎通道（全部 `(phase, op)` 都在既有白名单内）、零新态势开关
（只复用注册表里既有的 `bearer_leading` / `defender_bearer_leading`）。

### 三.2 14 个分队容器 → 分队规则行映射

`detachments` 表存的是**规则名**不是分队名（三种口径混存的既有坑）。映射按
「规则 id 与增强 id 邻接（N, N+1）」反推，再用 FP 正文互证：

| 容器（`stratagems.detachment`） | 规则行 id | 规则名 |
|---|---|---|
| Invasion Fleet | `000008356` | Hyper-adaptations |
| Crusher Stampede | `000008403` | Enraged Behemoths |
| Unending Swarm | `000008407` | Insurmountable Odds |
| Assimilation Swarm | `000008411` | Feed the Swarm |
| Vanguard Onslaught | `000008415` | Questing Tendrils |
| Synaptic Nexus | `000008420` | Synaptic Imperatives |
| Tyranid Attack | `000009680` | Xeno-Terror |
| Boarding Swarm | `000009689` | Priority Predation |
| Biotide | `000009698` | Unstoppable Swarm |
| Infestation Swarm | `000009723` | Half-Glimpsed Shadows |
| Warrior Bioform Onslaught | `000009736` | Leader-beasts |
| Subterranean Assault | `000010146` | Surprise Assault |
| Ambush Predators | `fp11e-tyranids-ambush` | Mindhunger |
| Talons of the Norn Queen | `fp11e-tyranids-norn` | Higher Imperatives |

### 三.3 ⚠️ 跨阵营共用容器名（本 PR 新增判据）

`Infestation Swarm` 是 **TYR / GC 共用的登舰行动分队**：库里另有 `faction='GC'` 的
同名同容器副本 4 战略 + 2 增强（`000009477002-005` / `000009476002-003`）。
前序阵营（AE/AM/CSM…）的容器名都唯一，其对账测试直接写
`WHERE detachment IN (...)` 不带 faction 过滤；**本阵营照抄会把 GC 的 6 行算成"漏编"**。

处置：对账测试一律加 `faction='TYR'` / `faction_id='TYR'` 过滤，并新增反向守卫
`test_shared_boarding_detachment_gc_rows_are_out_of_payload`
（断言这 6 行不在 TYR 载荷内，留给未来的 GC PR）。

### 三.4 encoded 16 条

| id | 名称 | 通道 | 相位门 |
|---|---|---|---|
| `000008349003` | ADRENAL SURGE | `hit/crit_threshold 5` | `phase_melee` |
| `000008409004` | TEEMING MASSES（守） | `hit/modify -1` | 无（两相位） |
| `000008422003` | RAMPAGING MONSTROSITIES | `hit/reroll fail` | `phase_melee` |
| `000008422006` | SWARM-GUIDED SALVOES | `save/ignores_cover` + `hit/ignore_hit_mods` | `phase_shooting` |
| `000008556005` | REINFORCED HIVE NODE（守） | `save/ap_improve -1` | 无（两相位） |
| `000009682002` | BIO-ACID SURGE | `hit/extra_hits 1` | `phase_melee` |
| `000009691002` | LITHE KILLERS（守） | `save/invuln 5` | `phase_melee` |
| `000009700005` | ONRUSHING HORDE（守） | `hit/modify -1` | `phase_shooting` |
| `000009725002` | HYPERADRENAL REFLEXES（守） | `save/invuln 4` | `phase_melee` |
| `000009738006` | PARASITIC PAYLOAD | `save/ignores_cover` | `phase_shooting` |
| `fp11e-tyranids-wbo-s1` | ALIEN PHYSIOLOGY（守） | `wound/modify -1` | `wound_s_gt_t` |
| `000010148004` | ENFILADING EMERGENCE | `hit/extra_hits 1` + `save/ignores_cover` | 无（持续期跨两相位） |
| `fp11e-tyranids-norn-s2` | LESSER PREY | `wound/s_improve 2` | `phase_melee` |
| `000008417003` | Chameleonic（守） | `save/cover` | `phase_shooting` |
| `000009737003` | Ocular Adaptation | `hit/modify 1` | `phase_melee` |
| `fp11e-tyranids-norn-e2` | Synaptoprescience（守） | `save/invuln 4` | 无（未限相位） |

### 三.5 partial 20 条（可编子集 + 残量注记）

| id | 名称 | 编了什么 | 未建模残量 |
|---|---|---|---|
| `det000009723` | Half-Glimpsed Shadows | 远程命中 -1 | 「攻方在 6" 以外」负向距离门无载体（近距高估）；受益者自关键词门 |
| `det000009736` | Leader-beasts | 5+ 无效保护 | 受益者自关键词门；关键词授予无载体 |
| `000008349002` | RAPID REGENERATION | FNP 6+ | 突触范围内升 FNP 5+ 的分支 |
| `000008409005` | SWARMING MASSES | `[SUSTAINED HITS 1]` | 15 模型档暴击阈值（攻方自身编制门） |
| `000008413002` | BROODGUARD IMPULSE | 致伤 +1 | 只对「刚消灭本方 HARVESTER 的那个敌军单位」（恒满足，高估） |
| `000008413005` | ABLATIVE CARAPACE | FNP 5+ | 目标点范围内升 FNP 4+ 的分支 |
| `000008413006` | SECURE BIOMASS | `[LETHAL HITS]` | HARVESTER 时的暴击阈值 5+ 分支 |
| `000008418002` | SURPRISE ASSAULT | 命中 +1 | 战斗震撼失败则致伤 +1；指定敌军单位恒满足 |
| `000008422004` | SAVAGE ROAR | 命中 -1 | 战斗震撼失败则致伤 -1 |
| `000009700004` | SWARM HUNTERS | 重掷命中 | 突触范围前提恒满足（高估）；可见性从句 |
| `000008348005` | Adaptive Biology | FNP 5+ | 仅携带者；战损后升 FNP 4+ |
| `000008404005` | Monstrous Nemesis | 对 MONSTER/VEHICLE 近战致伤 +1 | 仅携带者 |
| `000008408003` | Naturalised Camouflage | 远程掩体 | 受益者是另选的三个单位；只持续首轮 |
| `000008412005` | Parasitic Biomorphology | 近战 S+1 | 首杀后近战 A+1 的持久增益 |
| `000008417004` | Stalker | 命中 +1、致伤 +1 | 仅携带者；指定敌军单位恒满足 |
| `000008421004` | Synaptic Control | 伤害 -1 | 仅携带者 |
| `000009681003` | Reinforced Carapace | 伤害 -1 | 仅携带者（原文括注亦明确只影响该模型） |
| `000009737005` | Elevated Might | 近战重掷致伤 + AP+1 | 仅携带者 |
| `000010147005` | Trygon Prime | 近战 S+1、WS 改善 1 | 仅携带者；SYNAPSE 关键词授予 |

### 三.6 not_modeled 88 条的成因分布

| 成因 | 条数（约） | 代表条目 |
|---|---|---|
| 移动域（普通移动 / surge / 巩固 / 涌入 / M 修正） | 18 | 不可逾越之势、跃进、冲垮、缠缚弹、不懈饥饿 |
| 预备队与部署域（战略预备队 / 深入打击 / 重新部署 / 登场轮次） | 14 | 包抄、遁入地底、异形狡诈、震颤感知、先锋智识 |
| 治疗与复活域 | 8 | 喂养虫群、补充群兽、无尽虫群、贪婪饥饿、再生怪物 |
| 突触范围位置态 | 7 | 军规突触、突触传导、突触支点、突触信标、适应性优化 |
| 战斗震撼与士气 | 7 | 军规扭曲阴影、异种恐怖、弥漫恐惧、卡里斯的哀心 |
| 冲锋与射击资格域 | 7 | 探寻触须、覆盖本能、虫巢视界、超涌腺、灵能痕迹感知 |
| 目标点控制与 CP 经济 | 6 | 突触微节点、泰伦形变、不祥临在、突触战略、本能防御 |
| 死后反打 / 移除时机 | 4 | 死亡狂乱、肾上腺屠杀、暴怒后备、噬菌孢子 |
| 定额致命伤池（不依附攻击序列） | 4 | 重压冲击、窒息之影、腐蚀内脏 |
| **防高估**（见 §三.7） | 15 | 见下表 |
| 其他（编制约束、11 版侦测/隐蔽域、可见性） | 8 | 单形态捕食者、超感适应、隐光伪装 |

### 三.7 防高估清单（有通道但**故意不编**，逐条给理由）

| 条目 | 有什么通道 | 为什么仍不编 |
|---|---|---|
| 军规 **Synapse** 第二款 | `wound/s_improve 1` | 整条挂在「本单位处于我军突触范围内」的位置态前提；裸编＝对任何吞噬者攻方无条件 +1 S（已钉成测试 `test_synapse_melee_strength_is_disclosed_not_encoded`） |
| **Surprise Assault**（分队规则） / IRRESISTIBLE WILL / Mindhunger | `hit/reroll`、`wound/reroll` | 原文是「只重掷 1」，与引擎「重掷全部失败骰」不等价（显著高估） |
| **Perfectly Adapted** | 同上 | 每回合单颗骰重掷，无等价通道 |
| **CATALYTIC BIOFORTIFICATION** / **Null Nodules** | `fnp/fnp` | 仅对致命伤 / 仅对灵能攻击的 FNP，裸编会当成通用 FNP |
| **Hyper-adaptations** / **Synaptic Imperatives** / PREDATORY IMPERATIVE / IMPERATIVE DOMINANCE | 多个 | 军队级三选一，无选择载体；全编＝三项同时施加 |
| **Enraged Behemoths** | `hit/modify`、`wound/modify` | 加值前提是**攻方自己**低于满编/半编；引擎的 `target_below_*` 讲的是守方，裸编方向写反 |
| **SWARMING MASSES** 的 15 模型档 | `hit/crit_threshold` | 攻方自身编制门无载体（已降 partial 并注记） |
| **Piercing Talons** | `save/ap_improve` | 「仅暴击致伤的那几发」无条件 tag，裸编会给全部攻击 AP+1 |
| **Power of the Hive Mind** | `weapon_filter` + `wound/s_improve` + `save/ap_improve` | `[PSYCHIC]` 是关键词界定的武器集合，`weapon_filter` 只能按名字子串选，选不中 |
| **Destabilising Predation** | `wound/crit_threshold` + `target_has_keyword` | `[ANTI-CHARACTER 2+]` 限**远程**攻击，但引擎没有「射击 × 目标关键词」复合 tag（只有近战向的 `melee_target_has_keyword`），裸编会让近战也吃到 2+ 暴击致伤 |
| **EXPENDABLE BIOMASS** | `hit/modify -1` | 条款核心是「解锁一次本不可能的射击」，只编那条 -1 命中会把整体语义写反成纯减益 |
| **PRESERVATION IMPERATIVE** | `attacks/blast` | 该通道只在攻方侧有消费点，守方侧无对应点 |
| **ASSASSIN BEASTS** | — | `[PRECISION]` 属分配域，引擎不建模附着角色 |
| **COUNTERPREDATION** | `wound/s_improve`、`save/ap_improve` | 「目标处于 hidden 状态」不是「若…则更好」的增量分支，而是**整条效果的唯一开关**；引擎无守方 hidden 的攻方向 tag（`defender_hidden` 只给守方向条目开闸），且 WHEN 是「近战阶段被选定作战」＝已在接战范围内，11 版侦测规则下目标几乎不可能仍 hidden ——恒满足化等于近乎全程虚增一档 S 与一档 AP（自审 MEDIUM-1 由 partial 改判 not_modeled） |

> **本 PR 新增判据**：区分「EFFECT 段的**增量分支**」与「EFFECT 段的**唯一开关**」。
> 前者（「若……则改为 FNP 4+」）可只编基础档并注记降 partial；后者（整条效果被一个
> 无载体的前提门住）必须整条 not_modeled ——按恒满足编码不是"高估一点"，而是把一条
> 在真实对局里几乎不触发的规则当成常驻加成。判断法：去掉那个前提后，剩下的还是不是
> 原文承诺的效果？是（只是少了增益上限）→ partial；不是（整条凭空成立）→ not_modeled。

### 三.8 相位门双向核对（本 PR 的四次同型 HIGH 防线）

**该加的**（WHEN 落在单一相位 / 原文限某类武器）——13 条挂 `phase_melee`、7 条挂
`phase_shooting`，逐条清单见测试 `TestPhaseGating.MELEE_ONLY` / `SHOOTING_ONLY`。

**不该加的**（反方向核对，PR13 MEDIUM 同型）——13 条**不加门**，因为：
- WHEN 明写「对手射击阶段**或**近战阶段」/「我方射击阶段**或**近战阶段」：
  快速再生、蜂拥成群、涌动群兽、剥离甲壳、突袭强攻、强化虫巢节点；
- 原文根本未限相位：战兽领主、育种守卫本能、适应性生理、潜行者、突触控制、
  强化甲壳、突触预知；
- **ENFILADING EMERGENCE 的持续期判据**：WHEN=移动阶段结束，持续到「我方**下一个**
  近战阶段结束」——顺 WHEN 往后推，本回合射击阶段与近战阶段都在持续期内，故不加门
  （已钉成 `test_enfilading_emergence_spans_both_phases`）。

**关键词门的相位版本**：Monstrous Nemesis 用自含近战门的 `melee_target_has_keyword`，
不用裸 `target_has_keyword`（后者会在射击阶段误放行——这是 PR10/11/12/14 四次同型
HIGH 的关键词版）。测试 `test_no_bare_target_has_keyword_anywhere` 全库扫描守住。

---

## 四、验证

| 项 | 结果 |
|---|---|
| `python -m db_compile fp-rules` | 文本 应用 16 / 让路 0 / 跳过 0；失效 6；插行 13 |
| `python -m db_compile dsl-apply` | 应用 124 / 指纹让路 0 / 跳过 0 |
| `python -m pytest tests/ -q` | **全绿**（新增 `tests/test_simulator_dsl_pr31_payload.py`） |
| 基准 `qa_bench.py --path agent` | **97.9，0 hard error**（94 correct / 2 partial / 0 wrong）；与紧邻基线 `qa_agent_results_p7pr30.json` **逐题 verdict 差异为空集**，两条 ⚠️ 仍是既有固定波动题 #41/#42。纯编码 PR：DSL/DB 补丁不进 FAISS 索引，检索侧零影响 |

## 四.1 自审（code-reviewer 子代理）与整改

裁定 **0 CRITICAL / 0 HIGH / 4 MEDIUM / 8 LOW**。四类最高危缺陷（阶段门泄漏、
encoded 掉从句、漏写 FP 真漂移、写出假补丁）均为零。已整改：

| 编号 | 问题 | 处置 |
|---|---|---|
| MEDIUM-1 | COUNTERPREDATION 把「整条效果的唯一开关」按恒满足编码 | **改判 not_modeled**，并把「增量分支 vs 唯一开关」的判据写进 §三.7 与测试 `test_counterpredation_sole_gate_is_not_modeled` |
| MEDIUM-2 | 攻方侧漏挂既有 `bearer_leading`，导致同文件内攻/守披露不对称（守方 Chameleonic 拒注入并披露，攻方 Ocular Adaptation 零提示直通） | 6 条攻方携带者型增强全部补挂；护栏升级为 `test_bearer_leading_on_every_enhancement_with_effects`（含自然化伪装这一「受益者是另选单位」例外的显式白名单）+ `test_attacker_enhancement_requires_bearer_toggle` |
| MEDIUM-3 | 6 个名字带 `_only` 的行为测试只有正向断言 | 逐条补上反相位负向断言 |
| MEDIUM-4 | `test_melee_only_entries_gated` 允许集过宽（三选一），会放过「凭空多出目标关键词限制」的退化 | 收紧为 `== ("phase_melee",)` |
| LOW-1 | `text_patches` 无总数/查重断言（deact 与 inserts 都有） | 新增 `test_real_patches_file_text_patches_shape`（总数 181 + `(表, id, 列)` 查重 + 溯源与目标文本非空；`from_text` 允许空串以兼容 PR27 的上游空壳行归位） |
| LOW-3 | `Trygon Prime` 被直译成自造的「三角兽首领」，会原样进用户报告 | 改为保留英文 `Trygon Prime` 并注明「库内无既定中文译名，不自造」 |
| LOW-4 | `突触驱策` 在战略与增强上撞名 | 增强改称「突触刺棒（Synaptic Goad）」并注明与战略的区别 |

两条新护栏在写完后**当场逮到了两个真实边界**（不是走过场）：
① 自然化伪装的受益者是另选的三个单位，不该挂 bearer 门（PR28-PR30 反复钉过的判据）；
② PR27 的 AdM 上游空壳行归位补丁 `from_text` 本就是空串，靠空 from 做幂等守卫。
两处都按既有语义放宽断言并写明理由，而不是改数据迁就测试。

未整改（记为后续批次）：LOW-2（`test_fingerprints_match_db` 只覆盖带 effects 的条目）、
LOW-5（通道白名单在测试里手抄了第二份）、LOW-6（`to_text` 关键词标记风格不统一）、
LOW-7/LOW-8（见 §五）。

---

## 五、遗留观察项（不阻塞，不落本 PR）

1. **Harpy / Hive Crone 的 M·OC → `'-'` 与移除 Hover**（§一.5），沿 PR5/PR30 先例暂缓。
2. **Will of the Hive Mind 的 `usage` vs `use`** 非语义措辞差（3 行），不落补丁。
3. **Genestealer Cults 侧的 Infestation Swarm 6 行**（§三.3）留给未来的 GC PR。
4. **FP page_007-018 / page_022-031 的 datasheet 与 Legends 兵牌层**（The Red Terror /
   Hyperadapted Raveners / Harridan / Hierophant / Dimachaeron / Sky-slasher Swarms /
   Malanthrope / 双 Hierodule）库内均已有对应单位，沿死亡守望 / 圣血修女 / 灵族先例
   不落本 PR，仅作观察项。
5. **`data_refined/Faction Pack Tyranids/page_019.md` 的截断**建议重跑 refine
   （本 PR 已用 PyMuPDF 兜底取全，DB 层无缺口，但缓存本身仍是残页）。
