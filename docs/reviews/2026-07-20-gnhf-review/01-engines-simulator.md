# 模块 1 审查报告：engines/simulator/（引擎本体）

- 日期：2026-07-20（GNHF 全库深度审查，迭代 1）
- 范围：`engines/simulator/` 全部 15 个源文件（dsl.py / effect_params.py / sequence.py /
  engine.py / fight_order.py / contracts.py / parse.py / keywords.py / abilities.py /
  context.py / assembly.py / profile.py / report.py / cli.py / _spike_allocation.py），
  以及模拟接线入口 `agent/tools.py::simulate_combat_resolved`。
- 方法：全文件逐行通读 + 针对候选缺陷写机械核实脚本（扫描 26 个 dsl_payloads 的通道
  暴露面）+ 复现脚本证实 + 修复后成对回归测试。
- 结论先行：**2 个 CONFIRMED HIGH（均为同型「多来源单值 last-write」缺陷，已当场修复，
  pytest 1346 全绿）**；2 个 MEDIUM、2 个 LOW 记录在案不修。未发现 CRITICAL。
  已知的四类高复发缺陷（阶段门缺失/反方向欠建模/encoded 高估/过度施加）属 payload 侧问题，
  留待模块 2 逐条核对；引擎侧的阶段流转、数值夹取（AP 净算夹 ≤0、T 净算钳 ≥1、致伤修正
  合并夹 ±1）、镜像对局方向判定（first_is_a 布尔而非名字比对）经逐行核验均正确。

---

## HIGH-1（CONFIRMED，已修复）：`(hit, extra_hits)` 多来源单值 last-write，DSL 授予的低值 SUSTAINED 会把武器自带的高值降级

- **位置**：`engines/simulator/effect_params.py:236`（修复前为 `p.sustained = e.params[0]` 裸赋值）
- **证据**：修复前代码
  ```python
  if e.op == "extra_hits" and ok:
      p.sustained = e.params[0]
  ```
  武器 effects 的排列顺序是「武器词条效果在前、DSL 注入效果追加在后」（`dsl.inject_attacker`
  用 `w.effects + entry.effects`）。后写入者无条件覆盖先写入者。
- **失效场景**：武器自带 `[SUSTAINED HITS 2]`，用户点名一条授予 `[SUSTAINED HITS 1]` 的
  战略（payload 扫描证实全库有 **41 条** `(hit, extra_hits)` DSL 条目，如 orks DAKKASTORM、
  bloodangels MARTIAL PARAGON、tau Markerlight Precision 等）→ 引擎按 X=1 结算，
  命中期望从 1/2+2/6 错降到 1/2+1/6。**开一条增益战略反而让输出变低**。
  规则口径（Rules Commentary "Weapon Abilities With Differing Values"）：同能力多实例
  不叠加、取更优值。
- **复现**：构造 `effects=(sustained 2, dsl grant 1)` 调 `_gather_params` → 得
  `DiceExpr(k=1)`（复现脚本输出已记录，脚本用后删除）。
- **修法（已实施）**：新增 `_expect_expr` 期望值比较 helper，`extra_hits` 分支改为
  「仅当新值期望 > 现值期望才覆盖」。见 `effect_params.py:212-219, 236-242`。
- **测试**：`tests/test_simulator_gnhf_review.py::TestSustainedBestOf`（4 条：低值不降级 /
  两种顺序高值胜出 / 单来源不变（负向）/ 蒙特卡洛比率 1/2+2/6）。

## HIGH-2（CONFIRMED，已修复）：`(damage, modify)` 多来源单值 last-write，melta 与 DSL "+1 Damage" 互相覆盖

- **位置**：`engines/simulator/effect_params.py:296`（修复前为 `p.melta_expr = e.params[0]`）
- **证据**：修复前代码
  ```python
  elif e.phase == "damage":
      if e.op == "modify" and ok:
          p.melta_expr = e.params[0]        # DiceExpr（melta）
  ```
  与 P7-PR5 已修复的 `rf_exprs`（attacks 通道，注释原话「旧的单值 last-write 会静默吞掉
  一层」）同型缺陷，但 damage 通道与 sustained 通道当时漏改。
- **失效场景**：payload 扫描证实全库有 **19 条** `(damage, modify)` DSL 条目（黑圣堂
  Paragon of Fury、暗黑天使三件套、钛 EPC 三件套、吞世者 DAEMONIC STRENGTH 等，
  多为 "+1 Damage" 型增强）。带 melta X 的武器（如钛 fusion 系）在半射程内点名此类增强：
  melta 效果在前、DSL 在后 → melta X 被 +1 覆盖，D6+3+1 错算成 D6+1；顺序反过来则
  +1 被吞。规则上 melta 与增强加伤是不同来源修正，必须叠加。
- **复现**：`effects=(melta 3, dsl +1)`、half_range=True → `melta_expr=DiceExpr(k=1)`
  （melta 3 丢失）；顺序反转 → `DiceExpr(k=3)`（+1 丢失）。两方向均复现。
- **修法（已实施）**：字段改为 `dmg_mod_exprs: tuple`（与 rf_exprs 同语义累加），
  `sequence._sample_damage` 逐来源累加采样（兼容旧调用方传 None）。
  见 `effect_params.py:165-168, 293-296`、`sequence.py:95-101`。
  RNG 流不变（相同场景采样调用次数一致），既有蒙特卡洛断言全部保持。
- **测试**：`tests/test_simulator_gnhf_review.py::TestDamageModStacking`（4 条：半射程内
  双来源齐收 / 半射程外 melta 被门控只剩 +1（负向）/ 蒙特卡洛每未过保落伤 5 / 单 melta
  行为不变（负向））。

## MEDIUM-1（CONFIRMED 潜伏，仅记录）：S/T 延迟判定 tag 的 side 错配无校验，跨侧使用会静默变成无条件施加

- **位置**：`engines/simulator/dsl.py:241-247`（校验只限定 `(wound, modify)`，未限定 side）；
  路由侧 `effect_params.py:279`（攻方循环只认 `melee_s_lte_t`）与 `effect_params.py:345-346`
  （守方循环只认 `wound_s_gt_t`/`melee_wound_s_gt_t`）。
- **失效场景**：若未来有人给 **attacker 侧**条目挂 `("wound_s_gt_t",)`（"S>T 时致伤+1"
  型攻方增益完全可能出现），校验放行、`_cond_true` 对该 tag 恒返 True，攻方循环走
  else 分支 `p.wound_mod += ...` ——S>T 分量**不做延迟判定、无条件全程生效**（过度施加）。
  对称地，target 侧挂 `melee_s_lte_t` 会同样绕过 S≤T 判定。
- **核实**：机械扫描 26 个 payload：attacker 侧挂 S>T tag = 0 条、target 侧挂 S≤T tag
  = 0 条——当前零暴露，属潜伏缺口。
- **建议修法**：dsl.py `_parse_effect` 把三个延迟 tag 与 side 绑定校验
  （`melee_s_lte_t`→attacker、`wound_s_gt_t`/`melee_wound_s_gt_t`→target），录入期拒载。

## MEDIUM-2（CONFIRMED 潜伏，仅记录）：`p.sustained`/`crit_threshold` 之外，同型「多来源聚合语义」缺乏系统性护栏测试

- **说明**：本次两个 HIGH 与 PR5 的 rf_exprs 是三次同型缺陷（单值 last-write）。现存聚合
  语义分布：`rf_exprs` 累加（对）、`blast_x` 取 max（对）、`crit_hit_thr`/`crit_wound_thr`
  取 min（对）、`ap_improve`/`s_improve`/`sv_improve`/`t_worsen`/`t_improve` 累加（对）、
  `target_invuln` 取更优（对）、布尔类 or 语义（对）。修复后已无 last-write 残留，但
  没有一条测试系统性断言「每个通道的多来源合成语义」——下次引擎加通道仍可能重犯。
- **建议**：补一条参数化护栏测试，对 `_WeaponParams` 每个数值通道构造双来源用例断言合成
  结果（本次未加，避免超出最小修复范围；可在模块 8 测试质量阶段补）。

## LOW-1（记录）：`table="detachments"` 条目在 dsl.py 校验放行、投影层 skip、模拟装载层不可见

- **位置**：`dsl.py:39`（`_TABLES` 含 "detachments"）vs `db_compile/dsl_apply.py:129-131`
  （非投影表显式 skip 并注记「分队规则落 abilities 新行」）vs `profile.py:152`
  （`load_unit_dsl` 只扫 abilities/stratagems/enhancements 三表）。
- **说明**：设计约定是分队规则以 abilities 新行物化（spec D5），投影层 skip 有报告注记、
  非静默；当前 payload 零条 detachments 条目（机械核实）。但 `_TABLES` 仍接受该值，
  录入者若真写了 table="detachments"，条目会通过校验却永远进不了模拟——三层口径
  不一致，建议要么从 `_TABLES` 摘除、要么在 parse 期给出明确指引报错。

## LOW-2（记录）：间接开火固定阈值路径不承认「暴击必中」，与 conversion 组合时少算

- **位置**：`sequence.py:251-262`——`hit = active & (hr >= need)`，不含
  `hr >= p.crit_hit_thr` 分支；重骰判定 `hr < need` 同样把降阈暴击当失败骰重掷。
- **失效场景**：indirect_fire 与 conversion（long_range 时未修正 4+ 即暴击）同武器组合时，
  未修正 4-5 的骰按规则是暴击命中（暴击必中），引擎按未达 6 判失手。核实：该组合需同一
  武器同时带两词条，武器库中未发现实例，属理论边界；且 11 版「间接开火命中判定与 BS
  无关」的官方措辞下暴击必中是否适用亦存解释空间。仅记录。

---

## 逐项核验通过的重点面（无 finding）

- **阶段流转/武器选择**：`_select_weapons` 按 is_melee 严格二分；跨阶段 loadout 静默滤空
  已在 tools.py:539-545 显式披露（phase_warn），非静默。
- **数值夹取**：AP 净算 `min(0, w.ap - p.ap_improve)` 夹 ≤0（守方恶化不把 AP0 推成正 AP，
  sequence.py:318-322）；T 净算 `max(1, t - t_worsen + t_improve)` 钳 ≥1（sequence.py:304）；
  S/T 延迟分量与基础分量**合并后统一夹 ±1**（wound_mod_raw 机制，sequence.py:310-314）；
  BS 特征值通道与命中骰修正通道分离、各按其规则夹取（effect_params.py:380-387）。
- **掩体（11版 13.08）**：折 bs_neg 且仅射击阶段；IGNORES COVER 抵消、PSYCHIC 按有利方向
  清负修正（bs_neg+hit_neg 双通道）、间接/torrent 天然免疫——三条联动齐全。
- **fight_order/镜像对局**：`FightVerdict.first_is_a` 用对象同一性（`first is a`）判方向，
  调用方 engine.py:123 用布尔不比名字——镜像对局 CRITICAL 修复仍然在位。Fights Last
  出处存疑已在 rule_refs 里如实披露。
- **分配核**：`_spike_allocation` 双实现对拍（scalar oracle vs numpy，400 场景×200 迭代
  精确相等）覆盖不溢出/已损伤优先/逐点 FNP/致命池携带，语义可信。
- **退化输入**：models≤0 / w≤0 全零不打幽灵（run_sequence:371-375）；n≤0 入口拦截
  （engine.py:36, 104）；count≤0 武器不开火（sequence.py:225）。
- **诚实披露对账**：攻守两侧 unconsumed effect notes 挂进 not_modeled（engine.py:41-44）；
  DSL 开关闸门（requires/conflicts/toggle_groups）全部显式披露不静默。

## 修复与验证记录

| 项 | 动作 | 验证 |
|---|---|---|
| HIGH-1 sustained 取更优 | `effect_params.py` 新增 `_expect_expr` + 条件覆盖 | 新测试 4 条 + 复现脚本翻绿 |
| HIGH-2 damage 加值累加 | `melta_expr`→`dmg_mod_exprs` 元组累加，`sequence._sample_damage` 逐来源采样（兼容 None） | 新测试 4 条 + 双向复现翻绿 |
| 全量回归 | `.venv\Scripts\python.exe -m pytest -q` | **1346 passed, 0 failed**（基线 1338 + 新增 8） |

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 2 | 均已修复（pytest 全绿） |
| MEDIUM | 2 | 记录在案（均为零暴露潜伏缺口） |
| LOW | 2 | 记录在案 |
