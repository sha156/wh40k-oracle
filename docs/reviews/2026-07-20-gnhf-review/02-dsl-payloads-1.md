# 模块 2 审查报告（第 1 部分）：dsl_payloads/ 对照引擎语义

- 日期：2026-07-21（GNHF 全库深度审查，迭代 5；迭代 2-4 因 API 中断零产出）
- 范围（本部分）：
  1. **五个仅有自审的最新阵营逐条深读**：darkangels（22 条带效果）、spacemarines（44）、
     imperialknights（18）、imperialagents（19）、votann（19）——共 122 条带效果条目，
     逐条与 DB 原文（stratagems.text_zh 的 WHEN/TARGET/EFFECT、enhancements.description、
     detachments.rule_text）对照核对阶段门/条件方向/参数值/weapon_filter/status 诚实性；
  2. **全 19 阵营机械扫描**：相位门扫描（287 条带效果战略条目的 WHEN 子句 vs condition 门）、
     全量 parse 校验（1779 条全过 dsl.load_payload_file）、条件方向/侧别扫描（0 命中）、
     weapon_filter 对 DB weapons.name_en 命中性（5/5 命中）。
- 工具：`scripts/dump_entries.py`（payload×DB 原文对照 dump）、`scripts/scan_phase_gates.py`
  （WHEN 子句相位一致性，**不信 DB.phase 列**——实测该列不可靠，votann BRËKKEKNOTS
  标 "Shooting phase" 而 WHEN 原文是两相位）、`scripts/scan_semantics.py`（parse+方向+filter）。
- 结论先行：**2 个 CONFIRMED HIGH（均为阶段门缺失的已知复发家族，已当场修复，
  pytest 1351 全绿）**；1 MEDIUM、2 LOW 记录不修。五阵营其余 117 条逐条核对无误——
  含 4 处「冲锋阶段触发→只剩近战」推演全部正确挂门（UNBREAKABLE LINES / AUGMETIC
  FORTITUDE / FURIOUS DEDICATION / GRAVITRONIC PULSE），历史最顽固缺陷类在这五个
  阵营的正向样本上已被 worker 学会。

---

## M2-HIGH-1（CONFIRMED，已修）：imperialagents DISPLACER FIELD 漏射击门——近战模拟白拿 4+ 无效保护

- **位置**：`dsl_payloads/imperialagents.json` 条目 `stratagems:000009139006`（修复前
  effects[0].condition=[]）
- **原文证据**（db stratagems.text_zh id=000009139006）：
  > WHEN: Your opponent's Shooting phase, just after an enemy unit has selected its
  > targets. … EFFECT: **Until the end of the phase**, models in your unit have a
  > 4+ invulnerable save …
  触发窗与持续期都锁死在对手射击阶段，效果不可能延伸到战斗阶段。
- **引擎路由**：`effect_params.py:312-336` 守方 effects 循环对每条过 `_cond_true`，
  condition=[] 恒放行 → `p.target_invuln=4` 在 **melee 相位同样折进有效保存**。
- **失效场景**：近战模拟中点名 DISPLACER FIELD（守方 AoI 人物），目标凭空获得 4+
  无效保护——sv 无甲角色被近战 AP-6 攻击时未保存率从 100% 错降到 50%，防御力翻倍。
- **对照组（同 WHEN 全部挂了门）**：同为「对手射击阶段+持续至阶段末」的守方战略，
  imperialknights ROTATE ION SHIELDS（4+ invuln，`cond=['phase_shooting']`）、
  LET DUTY BE YOUR SHIELD、darkangels HIGH-SPEED FOCUS、spacemarines EVASIVE
  MANOEUVRES、votann WEAVEWËRKE BUTTRESS——全库口径一致，唯此条漏挂。
- **verdict**：CONFIRMED（机械扫描逮出 + 引擎路由逐行核实 + 修复前后成对测试差分）。
- **修复**：condition 补 `["phase_shooting"]`，note 补推演说明。成对测试
  `tests/test_simulator_gnhf_review.py::TestModule2PhaseGates`
  （射击相位 unsaved/wounds≈1/2 照常生效 / 近战相位 ≈1.0 不再施加）。

## M2-HIGH-2（CONFIRMED，已修）：worldeaters DAEMONIC STRENGTH 裸 target_has_keyword——射击模拟对凶兽/载具错加 D+1

- **位置**：`dsl_payloads/worldeaters.json` 条目 `stratagems:000010083003`（修复前两条
  effects 的 condition=`["target_has_keyword","monster"/"vehicle"]`）
- **原文证据**（db stratagems.text_zh id=000010083003）：
  > WHEN: **Fight phase**. … EFFECT: **Until the end of the phase**, each time an
  > attack made by a model in your unit is allocated to an enemy model … add 1 to
  > the Damage characteristic …
- **引擎路由**：`_cond_true` 的 `target_has_keyword` 分支只查目标关键词、不看相位
  （`effect_params.py:88-89`）→ 射击相位对 MONSTER/VEHICLE 目标照样 +1 Damage。
  引擎为此场景**专门注册过复合 tag** `melee_target_has_keyword`
  （`effect_params.py:45-47` 注释原话："裸 target_has_keyword 会在射击误放行"）。
- **失效场景**：任何 WE 攻击单位（如带远程武器的载具/机兵）点名该战略、射击 VEHICLE
  目标 → 每次未过保攻击伤害 D+1（D1 武器伤害翻倍）。这是 PR10 岿然阵列 / PR11 帝皇的
  处刑者 / PR12 致命首秀 / PR14 巨兽蛮汉 之后**第五次同型缺陷**（P7-PR5 录入早于
  该 tag 家族固化成军规，铺量前样本，本次补扫逮出）。
- **verdict**：CONFIRMED（机械扫描逮出 + 引擎路由核实 + 修复前后成对测试差分）。
- **修复**：两条 condition 改 `melee_target_has_keyword`（monster/vehicle 各一），note
  补 WHEN 推演。成对测试同上 class（近战对 monster damage/unsaved≈2.0 / 射击 ≈1.0 /
  近战对非 monster ≈1.0 三向差分）。

## M2-MEDIUM-1（已裁决，升级并入第 2 部分 M2-HIGH-3）：votann DISPERSED FORMATION 与 spacemarines BLIND SCREEN 同文异编——Stealth+掩体只编一份

> **2026-07-21 裁决（见 02-dsl-payloads-2.md）**：查 11 版核心规则 24.33/13.08/24.18
> 原文后定谳——Stealth 的全部效果=授予掩体收益（二元状态），**两条都不对**：
> SM 双编=双重计费、votann 单编但走错通道（hit-1 不吃 [IGNORES COVER] 抵消、
> 不与地形掩体去重）。连同同型 3 条（Umbral Raptor/Shroud Field/Wings of Shadow）
> 升级为 CONFIRMED HIGH 家族缺陷，5 条已全部修复。以下为裁决前的原始记录。

- **位置**：`dsl_payloads/votann.json` `stratagems:000010440007`（只编 Stealth 的
  hit-1，note 称"掩体与匿踪同向，为避免双重叠加只编一份"）vs
  `dsl_payloads/spacemarines.json` `stratagems:000010681006` BLIND SCREEN
  （**两份都编**：hit modify -1 + save cover）。两条规则原文的效果句
  法几乎逐字相同（"your unit has the Stealth ability and … models … have the
  Benefit of Cover against that attack"）。
- **引擎语义**：Stealth 走命中骰修正桶（`hit_mod`，夹 ±1），掩体走 BS 特征值桶
  （`bs_delta`，13.08 折算、不夹）——`effect_params.py:362-387` 两桶**分层净算不合并**，
  编两份不会"双重叠加"进同一夹取，votann 的省编理由与引擎实现不符。
- **影响**：votann 该战略少算一档 BS 惩罚（保守方向欠建模，PR13 冷酷狂热同类）；
  或者反过来 SM 版是过度编码——取决于 11 版 Stealth 与掩体收益是否同源（语料内
  13.08/24.33 未见去重条款）。两条必有一条不对，方向存疑故 PLAUSIBLE、记录待裁。
- **建议**：查 11 版核心规则 Stealth 定义后统一两处口径；若判叠加成立，votann 补
  `("save","cover")` 一条并补成对测试。

## M2-LOW-1（记录）：DSL 授予武器词条沿用引擎原生编码、不额外挂相位门——依赖玩家不给近战模拟开射程类开关

- **实例**：imperialknights THIN THEIR RANKS（RAPID FIRE 1 → `(attacks,modify,+1)`
  cond=`half_range`）、deathguard MORTARION'S TEACHINGS（HEAVY → `(hit,modify,+1)`
  cond=`stationary`）。两者 WHEN 均为本方射击阶段，编码与 keywords.py 武器原生词条
  完全一致（`keywords.py:73-76,101-104`）。
- **暴露面**：DSL 注入面是整个 loadout（含近战武器）——近战模拟若同时打开
  half_range/stationary 开关，近战武器会错享 +1A/+1 命中。需要「近战模拟 + 射程/驻停
  开关」的自相矛盾输入才触发，且与武器原生词条的跨相位行为同构，故 LOW 记录不修。
- **对照**：scan_phase_gates.py 已把 `half_range/long_range/indirect` 从
  「两相位误报」白名单剔除后仍归入射击门集合——后续新增此类条目时按本条口径复核。

## M2-LOW-2（记录）：机械扫描的 3 个已否证候选（防复发备查）

1. deathguard CLOUD OF FLIES（hit-1 无门）：WHEN=对手射击阶段但效果持续 **until the
   end of the turn**——对手随后战斗阶段近战攻击同样吃 -1，无门是**正确**编码
   （扫描器不解析持续期从句，人工裁定否证）。
2. greyknights PSYBOLT AMMUNITION（ap_improve 无门）：weapon_filter='storm bolter'
   只注入远程武器，近战模拟天然不选用 → 无门无害；encoded 标注诚实。
3. blacktemplars SPOOR OF THE UNHOLY（ignores_cover 挂 phase_shooting 被扫描器判
   "两相位却挂门"）：规则限定 ranged weapons 且掩体折算本就只在射击相位生效
   （`effect_params.py:374`），挂门正确；同条 ignore_hit_mods 两相位未挂门也正确。

---

## 机械扫描结果汇总（全 19 阵营）

| 扫描 | 覆盖 | 结果 |
|---|---|---|
| parse 全量校验（tag/op 白名单、参数形状、status 一致性、开关注册表） | 1779 条 | 全过（校验层在 load 期强制，无绕过路径） |
| 战略 WHEN 相位门一致性 | 287 条带效果战略 | 7 旗 → 2 CONFIRMED HIGH（已修）+ 1 LOW + 4 否证 |
| 条件方向/侧别（S/T tag 跨侧、target 侧正号 hit/wound/ap、attacker 侧负号 ap 等 8 类） | 全部 effects | 0 命中（模块 1 MEDIUM-1 的 S/T 跨侧暴露面复扫仍为零） |
| weapon_filter 命中性 vs db.weapons.name_en | 五阵营 5 个 filter | 5/5 命中（plasma×87 / shotpistol×1 / cane-rapier×1 / feet×15 / storm bolter） |

## 五阵营逐条深读要点（117 条无误样本中的关键核对）

- **冲锋触发→近战门推演（历史最顽固类）4/4 正确**：SM UNBREAKABLE LINES、
  SM AUGMETIC FORTITUDE、SM FURIOUS DEDICATION、votann GRAVITRONIC PULSE 的 note
  均显式写了"对手回合相位序中射击在冲锋前，触发后仅剩近战"推演。
- **[LETHAL HITS] 语义核实**：`(hit,auto_wound)` = 暴击命中自动致伤（`sequence.py:291-297`
  lethal_mask=crit_hit），非"全命中自动致伤"——DA/SM/IK/AoI 各 LETHAL 条目编码正确。
- **ARMOUR OF CONTEMPT 系（×10+ 副本）**：WHEN 两相位 + AP 恶化 -1 无门，与守方
  `(save,ap_improve)` 负参并入攻方特征值累计（净算夹 ≤0，模块 1 已核）一致。
- **S>T 延迟 tag 三处（DA Dutiful Tenacity / SM Malodraxian Standard / SM Angels
  Defiant / votann WEAVEFIELD FLARE）**：均挂 (wound,modify)+`wound_s_gt_t`，与原文
  "S>T 时致伤-1"逐字对应；IK LANCEBREAKER 因 WHEN=Fight phase 正确用 melee 变体。
- **status 诚实性**：encoded 条目（votann×6 / AoI×4 / GK PSYBOLT 等）逐条核对效果
  全落 effects 且手算等价；「设定值（SET）无载体不编增量」（THUNDERSTOMP A=8/12、
  ARBITRARY EXECUTION A=2、Armour of Antoninus Sv=2+）三处全部正确拒编不高估。

## 遗留与移交

1. **DB 投影未刷新**：本次修的两条真源在 `dsl_payloads/*.json`，DB
   `stratagems.effect_dsl_json` 仍是旧投影（运行时 `profile.load_unit_dsl` 读 DB）。
   本任务**禁止写库**，需在允许写库的会话跑 `.venv\Scripts\python.exe -m db_compile
   dsl-apply` 刷新投影（幂等，带 restore 挂载）。刷新前 CLI/网页模拟对这两条仍旧行为，
   payload 级测试已锁住真源正确性。
2. 模块 2 第 2 部分（可选）：14 个更早阵营的逐条深读——它们都过了各自 PR 的对抗性
   复审，本次全库机械扫描（相位门/方向/parse）已覆盖其最高危缺陷类且仅逮出
   worldeaters 一处；如需再抽查，优先 tau（guided 复合 tag 家族）与 deathguard
   （afflicted 门家族）的 condition 方向。
3. M2-MEDIUM-1 的 Stealth×掩体叠加裁决需查 11 版核心规则原文（检索链可答），
   裁定后统一 votann/spacemarines 两处口径。
