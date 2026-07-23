# 模块 3 审查报告：engines/roster/ 军表系统

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：`engines/roster/` 全部 6 文件（compose_rules / contracts / critique / points /
  validate / __init__），调用入口（web_api/roster.py、web_api/main.py 五端点、
  web_api/contract.py、agent/tools.py、前端 roster.ts / page.tsx / RosterUnitRow.tsx），
  数据面 db/wh40k.sqlite 只读（units 1715、enhancements 实测 1058 条——CLAUDE.md 记
  927，P7 铺量期 fp 补丁有新增；cost NULL 131 条）。
- 方法：全文通读 + 5 个机械核实脚本实跑（强化点数入分/全库 1715 单位档位解析扫描/
  未知 id 行为/enhancements 重名与 critique 端到端/跨阵营混编与 loadout 边界），
  规则真源比对 MFM 中文版与设计文档。
- 结论先行：**1 个 HIGH（CONFIRMED，已修复）**、2 个 MEDIUM、4 个 LOW。
  历史 CRITICAL 复发区（点数档位解析）全库扫描零错价守住；纯近战 0 攻击陷阱已被
  critique 正确防住。核心问题：强化点数完全不参与总分与合法性判定。

---

## F1（HIGH，CONFIRMED，已修复）：强化点数不计入总分，超分军表被判合法

- **位置**：`engines/roster/validate.py:31-34`、`engines/roster/points.py:86-88`
- **证据**（修复前）：`validate()`/`critique()` 全程只累加单位点数；`enhancements.cost`
  （810 条 >0，最高 20 点）仅用于归属名单校验与前端下拉展示，从不进入 `total_points`，
  前端也不本地补加。机械复现：Eye of the Primarch（cost=10）挂上后
  `total_points=150, legal=True`，10 点凭空消失。**现有测试 `test_legal_roster`
  断言 `total_points == 150`，把漏洞钉成了预期行为**。
- **规则依据**：MFM 中文版（`data_refined/6月4日分数中文/page_007.md:15-20`）明确列出
  分遣队强化逐条点数——MFM 列点数的唯一目的就是计入军队总分；设计文档第 47 行也要求
  「抽强化名+点数+归属分队」。
- **失效场景**：竞技压线组建——1990 点单位 + 20 点强化 = 实际 2010 > 2000，系统显示
  「1990/2000，合法」，用户带非法表上桌。3 个强化时误差可达 ~60 点。
- **修法（已实施）**：`validate()` 新增 `_enhancement_points`——按 detachment 目录查
  cost 累加进 total（points_over 判定同步生效）；cost 拿不到（无分队数据/不属于当前
  分队/库中 cost NULL 的 131 条）→ `enh_unpriced` surfaced_only WARN「未计入总分」，
  不静默计 0。契约无需改（issues 透传）。critique 的性价比分母（unit.points）是否含
  强化另行裁定，本次不动（已注记）。
- **测试**：`test_legal_roster` 期望值 150→160（修正被钉成规格的 bug）；新增
  `test_enhancement_points_push_over_limit`（24×80+70=1990 挂 20 点强化 → 2010 判超分
  / 卸下强化合法，成对）、`test_enhancement_unpriced_surfaced_not_counted`（拿不到价
  → warn 且不计入）。web_api 侧 `test_validate_legal_and_camelcase` 同步 160。

## F2（MEDIUM，PLAUSIBLE，已修复 2026-07-24）：Rule of Three 的 BATTLELINE/DT 豁免写成「无上限」，违背设计文档「不确定则 warn」裁决

> 追记：豁免且 >3 份 → `rot_exempt_uncapped` surfaced warn（validate ④），上限查证
> 前不再静默豁免；测试 `test_rot_exempt_over_three_surfaced_not_silent`（一正一负）。

- **位置**：`engines/roster/compose_rules.py:87-98`
- **说明**：设计文档写「battleline / dedicated transport 例外，上限更高」（非无上限），
  风险表明确处置「查 11 版核心规则确切上限写常量；不确定的 warn 不 error」。实现直接
  静默豁免（`return None`）。十版对应规则为 6 份上限；11 版编制规则不在语料内
  （Core Rules PDF 无 MUSTER 章节），正是设计文档要求 warn 的「不确定」情形。
  8×Intercessor 判 legal 且无任何提示。
- **建议修法**：查证 11 版官方 App/Wahapedia 编制规则后写常量；查证前对超 3 份发
  surfaced_only warn「豁免上限未查证」。

## F3（MEDIUM，CONFIRMED，已修复 2026-07-24）：未知 canonical_id 被编造成事实性 ERROR 断言，违反诚实降级红线

> 追记：`unit_keywords_bulk` 不再为未知 id 补空集；validate 发 `unit_not_found`
> surfaced warn 并跳过 warlord 资格/RoT/强化 CHARACTER/档位归因等编造断言。测试
> `test_unknown_unit_honest_degradation` + `test_unknown_unit_does_not_suppress_known_unit_checks`。

- **位置**：`engines/roster/validate.py`（warlord/强化关键词断言）+
  `compose_rules.py:63`（unit_keywords_bulk 对查不到的 id 补空集）
- **失效场景**：对不存在的 id，系统断言「X 非 CHARACTER，不能任 WARLORD」「该模型数
  不在点数档位内」——三条消息全部撒谎（单位根本不存在，系统无从知道它是不是
  CHARACTER）。触发面是过期引用：DB 重建/单位删除后前端 localStorage 旧军表命中此路径。
- **建议修法**：区分「id 不在 units 表」，发 `unit_not_found` surfaced_only 告警并跳过
  关键词类断言与档位文案。

## F4（LOW，CONFIRMED，仅记录）：阵营/分队归属完全不校验且不披露

- SM 军表塞 Tau Broadside → `legal=True, issues=[]`。设计清单本就未含此项（设计边界
  而非实现走样），但报告零披露，与 critique 的 not_modeled 披露惯例不对称。
- **建议修法**：最低成本加固定 surfaced_only info「阵营/分队归属未校验」；正解按
  `units.faction_id` 比对发 ERROR。

## F5（LOW，CONFIRMED，已修复 2026-07-24）：非法 loadout 静默清空后，critique 误报「未指定 loadout」

> 追记：web_api critique_roster 按输入侧事实改写 note（「非法已丢弃」vs「未指定」），
> 引擎契约不动；测试 `test_critique_discarded_loadout_note_not_misattributed`（成对）。

- `_to_loadout` 任一项非法 → 整体 `()`，critique note 却说「未指定 loadout」——用户明明
  填了，归因被带偏。正常前端路径不触发。
- **建议修法**：`_to_loadout` 返回 `(loadout, ok)` 或 note 区分「非法被丢弃」与「未提供」。

## F6（LOW，PLAUSIBLE，已随模块 7 修复）：/roster/critique 无军表规模上限，重计算请求长期持有并发闸

- 与模块 7 HIGH-1 同根因，已由 `RosterIn.units max_length=60` + models/loadout 封顶
  一并堵上（commit 见模块 7）。

## F7（LOW，CONFIRMED，已修复 2026-07-24）：agent 工具层军表 stub 文案过期（「计划于 P6 实现」）

- 与模块 5 MEDIUM-3 同一发现，见该报告。

---

## 已知高危点核查结果（负结果也有价值）

1. **points_json 档位解析（历史 CRITICAL 复发区）——已核无误**：仍是严格
   `(\d+)\s*models?` + 纯档优先。全库 1715 单位机械扫描：desc 首数字≠档位数 0、
   单 desc 多匹配 0、cost 非 int 0；无法定价仅 4 个复合 datasheet（诚实 surfaced）；
   qualified 兜底采纳 15 条逐条目检无错价。军表链路内无第二处档位解析（simulator
   assembly 的宽松正则只用于模拟器默认模型数，不参与定价）。
2. **编制约束边界**：0 点单位正确入档；多档位单位档位外 → surfaced warn（有测试）；
   EPIC HERO ≤1、非 battleline ≤3 正确；附队 leader 附着未建模但 10/11 版语义下单独
   计数恰好正确；未知规模档显式 surfaced。
3. **critique 接模拟器——已核无误**：纯近战 loadout 被 `_has_phase_weapons` 正确导向
   近战相评估（不是 0 伤射击相）；乱写武器名 → assessed=False + 诚实 note；全文无裸
   except，无静默降级。
4. **enhancements 数据**：归属/唯一/CHARACTER/EPIC HERO/≤3 全部实现且有测试；同分队
   重名 0；点数参与校验缺失即 F1（已修）。

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 1 | 已修复 + 成对测试 |
| MEDIUM | 2 | 记录在案 |
| LOW | 4 | 1 条已随模块 7 修复，3 条记录在案 |

## 遗留建议

1. F2 建议趁 Wahapedia/官方 App 可达时一次性查证 11 版 battleline/DT 上限落常量。
2. F3/F5 属同类「归因文案撒谎」，可合并一个小 PR：数据缺口消息只说系统知道的事实。
3. 「把 bug 钉成规格的测试期望值」值得进 learn-notes（test_legal_roster 150 反例）。
