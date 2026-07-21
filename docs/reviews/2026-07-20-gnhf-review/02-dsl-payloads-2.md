# 模块 2 审查报告（第 2 部分，模块 2 收官）：dsl_payloads/ 更早阵营抽查 + Stealth 裁决

- 日期：2026-07-21（GNHF 全库深度审查，迭代 6）
- 范围（本部分）：
  1. **第 1 部分遗留 M2-MEDIUM-1 的裁决**：查 11 版核心规则原文裁定 Stealth×掩体
     同文异编——裁决结果升级为 **M2-HIGH-3 家族缺陷（CONFIRMED，5 条已修）**；
  2. **两个高危 condition 家族的更早阵营深读**（第 1 部分移交清单指定优先级）：
     tau 全部 32 条带效果条目（guided/markerlight/战轮门复合 tag 家族）、
     deathguard 全部 24 条带效果条目（target_afflicted 门家族），逐条对照 DB 原文；
  3. weapon_filter 命中性补扫（tau×3 + deathguard×1）。
- 结论先行：**1 个 CONFIRMED HIGH 家族缺陷（5 条 payload 条目、4 个文件），已当场
  修复并补 6 条成对测试**；tau/deathguard 56 条深读全部无误。模块 2（dsl_payloads
  对照引擎语义）至此收官：五个仅自审阵营 122 条深读（第 1 部分）+ 全 19 阵营三类
  机械扫描（第 1 部分）+ 两个高危 condition 家族 56 条深读（本部分）+ Stealth
  家族全库横扫（本部分）。

---

## M2-HIGH-3（CONFIRMED，已修）：Stealth 按十版语义编成 hit-1——11 版 Stealth 的全部效果是「授予掩体收益」

### 规则真源（裁决依据）

- **STEALTH 24.33**（`data_refined/Core Rules - New 40K Core Rules/page_085.md:2-3`）：
  > If every model in a unit has this ability, each time a ranged attack targets that
  > unit, **that unit has the benefit of cover against that attack (13.08)**.
- **BENEFIT OF COVER 13.08**（`page_050.md:16-17`）：
  > Each time a ranged attack targets a unit that has the benefit of cover against it,
  > **worsen the BS characteristic of that attack by 1**.
- **[IGNORES COVER] 24.18**（`page_082.md:20`）：
  > the target cannot have the benefit of cover against that attack (13.08),
  > **including from rules that give a model or unit the benefit of cover (e.g. Stealth)**.

三条合读：11 版 Stealth ≠ 十版的「被远程攻击命中-1」——它的**全部**效果就是授予
13.08 掩体收益，这是一个**二元状态**（有或没有，与地形来源不叠加），且被武器侧
[IGNORES COVER] 点名整体抵消。

### 缺陷家族（全库横扫 19 阵营的 Stealth 编码，两个阵营口径并存）

正确阵营（9 条，均编单份 `(save, cover)`）：custodes×2、drukhari×2、greyknights×3、
necrons×1、orks×1、thousandsons×1。

错误阵营（5 条，编成 `(hit, modify, -1)` 十版残留语义，全部 `manual-2026-07-20`
即最近五个仅自审 PR 的产物）：

| 条目 | 修复前编码 | 备注 |
|---|---|---|
| spacemarines `stratagems:000010681006` BLIND SCREEN | hit-1 **和** cover 双编 | 最重：基线即双重计费 |
| votann `stratagems:000010440007` DISPERSED FORMATION | 仅 hit-1（note 自称"避免双重叠加只编一份"，但选错了通道） | 第 1 部分 M2-MEDIUM-1 本体 |
| spacemarines `enhancements:000010466004` Umbral Raptor | 仅 hit-1 | |
| spacemarines `enhancements:fp11e-spacemarines-subversion-e1` Shroud Field | 仅 hit-1 | |
| darkangels `stratagems:fp11e-da-darkflight-s2` Wings of Shadow | 仅 hit-1 | |

BLIND SCREEN 与 DISPERSED FORMATION 的 EFFECT 原文逐字同文（"your unit has the
Stealth ability and each time a ranged attack targets your unit, models in your unit
have the Benefit of Cover against that attack"）——两个从句在 11 版收敛为**同一个**
二元状态，正确编码是一份 `(save, cover)`，第 1 部分记录的"两条必有一条不对"实为
**两条都不对**。

### 失效场景（错通道的三个可观测差异，引擎路由证据）

引擎接线：`effect_params.py:221` `p = _WeaponParams(cover=stance.target_in_cover)`
（掩体开关种进布尔），`:321-322` DSL `(save,cover)` 置同一布尔（**天然去重**），
`:373-375` `cover_active = p.cover and not p.ignores_cover` 折 BS 恶化 1；
而 hit-1 走 `:315-320` 命中骰修正桶（±1 夹取）。差异：

1. **与地形掩体开关双重计费**：守方开 `target_in_cover` 再注入 Stealth 条目——
   应仍是一档惩罚（BS4+→命中 1/3），错通道叠成 BS 恶化+命中-1（→1/6，防御力翻倍）；
2. **不吃 [IGNORES COVER] 抵消**：24.18 点名 Stealth 也被抵消，`ignores_cover`
   只清 cover 桶不清 hit_mod——攻方带该词条武器时惩罚应整体消失，错通道仍 -1；
3. **BLIND SCREEN 双编**：无需任何开关，基线即 hit-1+BS-1 双重惩罚（1/6 而非 1/3）。

- **verdict**：CONFIRMED（核心规则三条原文合读 + 引擎路由逐行 + 修复前后成对测试差分）。
- **修复**：5 条统一改单份 `(save, cover)`（phase_shooting 门保持），note 写明
  11 版语义与「勿编成 hit-1」防复发提示。成对测试
  `tests/test_simulator_gnhf_review.py::TestModule2StealthChannel` 共 6 条：
  BLIND SCREEN 单档惩罚 1/3（修复前 1/6）/被 [IGNORES COVER] 抵消回 1/2；
  DISPERSED FORMATION 与地形掩体去重 1/3/被抵消回 1/2；Wings of Shadow 正负成对；
  Umbral Raptor 开关点亮 1/3/未点亮不注入 1/2（Shroud Field 同文件同形，家族覆盖）。
- **root cause 备注**：与 PR10-PR14 的「阶段门缺失」不同，这是**新的复发家族**——
  「USR 语义按十版肌肉记忆编码，未查 11 版重定义」。11 版改动过语义的 USR
  （掩体从保存侧挪命中侧、Stealth 并入掩体）是后续铺量 PR 的高危区。

## tau 深读（32 条带效果条目，全部无误）

重点核对 guided 复合 tag 家族的 condition 方向，全部与原文一致：

- **FTGG 军规**：`guided_vs_spotted`（BS+1）/`guided_markerlight`（[IGNORES COVER]，
  须观察员带 Markerlight）双条款分 tag 编码，与原文两从句逐一对应；
- **COORDINATE TO ENGAGE 与 guided 硬互斥**（`conflicts: ['guided']`）——FTGG 原文
  "excluding Observer units"（观察员不为 Guided），既有审查加固（PR3-H1）仍在位；
- **Kauyon/Mont'ka 战轮门**：`detachment_rounds_shooting`/`detachment_rounds_guided`
  复合 tag 自含相位+受引导判定；Precision of the Patient Hunter 的"第三轮起"复用
  Kauyon 窗口（3-5 轮，5 轮制下等价）有 note 披露；
- **观察员视角翻转**（Through Unity, Devastation / Coordinated Exploitation：增强挂
  观察员领袖、编码从受益方视角施加）均显式披露假设；
- 距离/战损/空间类前提（Bonded Heroes 12″/8″ 档、Hunter's Instincts 满编/半编档、
  A TEMPTING TRAP 陷阱点等）全部走假设开关或 opt-in 披露，无静默高估；
- EXPERIMENTAL AMMUNITION 二选一只编无风险模式 A、Prototype Weapon System 固定
  LETHAL 模式有 note——诚实性无误。

## deathguard 深读（24 条带效果条目，全部无误）

重点核对 target_afflicted 门家族：

- **Nurgle's Gift**：T-1 挂 `target_afflicted` 开关（感染态由玩家声明，传染范围
  逐轮变化不可建模）；瘟疫三选一仅编骨疽疟且以 AP 特征值等价编码（护甲面数学
  等价、特保不受影响——等价失效条件已在既往记录）；颅蛆枯萎（守方向）显式披露
  未接入；
- CHINKS IN THE ARMOUR / CREEPING BLIGHT / Eye of Affliction 的 afflicted 门方向
  与原文（Contagion Range 内 / Afflicted 目标）一致；
- CLOUD OF FLIES 无相位门（until end of the **turn**）维持第 1 部分否证裁定；
- GRIM REAPERS 排除 MONSTER/VEHICLE 为负关键字门无载体——opt-in 战略以「点名
  时自查目标合法性」note 承载，与全库口径一致；
- 守方条目（GROTESQUE FORTITUDE t_improve、DISGUSTINGLY RESILIENT/Foul
  Constitution damage_reduction、Rejuvenating Swarm wound_s_gt_t、Revolting
  Regeneration FNP）通道与侧别全部正确（wound_s_gt_t 在守方消费点
  `effect_params.py:345-349` 延迟判定，模块 1 的跨侧暴露面复扫仍为零）。

## weapon_filter 命中性补扫

| filter | DB weapons.name_en 命中 | 裁定 |
|---|---|---|
| tau 'airbursting fragmentation projector' | 5 行 | 命中 |
| tau 'flamer' | 398 行（全库） | 命中；宽子串风险已在 note 披露（作用面仅限本单位 loadout，需玩家单列目标武器） |
| tau 'plasma rifle' | 10 行 | 命中 |
| deathguard 'Plague Wind' | 2 行 | 命中 |

## 模块 2 收官汇总

- 覆盖：五个仅自审阵营 122 条深读 + 全 19 阵营机械扫描 1779 条（第 1 部分）
  + tau/deathguard 高危 condition 家族 56 条深读 + Stealth 家族 14 条全库横扫（本部分）。
- 缺陷账：**3 个 CONFIRMED HIGH 全部已修**（M2-HIGH-1 DISPLACER FIELD 相位门、
  M2-HIGH-2 DAEMONIC STRENGTH 关键词裸门、M2-HIGH-3 Stealth 十版语义残留家族
  5 条）+ 1 MEDIUM（升级并入 HIGH-3，不再单列）+ 2 LOW（记录不修）。
  成对测试累计 11 条（5+6），全量 pytest 1357 绿。
- **DB 投影未刷新**（遗留同第 1 部分）：本次 5 条修复真源在 `dsl_payloads/*.json`，
  运行时 `profile.load_unit_dsl` 读 DB 的 `effect_dsl_json` 旧投影——需在允许写库的
  会话跑 `.venv\Scripts\python.exe -m db_compile dsl-apply` 刷新（幂等）。
