# 模块 8 审查报告：测试质量抽查

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：`tests/` 全目录（87 文件，AST 扫描 1789 测试函数 / 3563 assert）+ `dsl_payloads/`
  28 阵营 2889 条目（524 带 condition 门）交叉对账。
- 方法：三个机械扫描脚本（AST 恒真/无断言/吞断言/skip/mock 扫描、门控成对性对账、
  源模块引用对账）+ 7 个核心测试文件逐行深读 + 2 次定向 pytest。
- 结论先行：**0 CRITICAL、0 HIGH、2 MEDIUM（同根因）、3 LOW、1 NOTE**。这套测试基本面
  显著高于常见水准：恒真断言 0、无断言测试 0、被吞断言 0、xfail 0、mock 无一打在被测
  逻辑本体、共享可变状态无、计数守卫全锚在独立字面量（非同义反复）。真问题是一处
  系统性纪律漂移：门控成对性纪律 PR26 才落成结构护栏，PR4-PR25 早期阵营缺逐条钉死。

---

## F1（MEDIUM，CONFIRMED，已修复 2026-07-24）：早期阵营（PR4-PR25 中 21 文件）门控载荷条目缺任何回归锚——198/524 条零测试引用

> 追记：按本报告建议落全局结构锚——`scripts/gen_dsl_condition_anchor.py` 快照 524 条
> 门控条目到 `tests/data/dsl_condition_anchor.json`，`tests/test_dsl_condition_anchor.py`
> 双向对账（删门/加门/换相位均检出，F2 一并消掉）。

- **位置**：`test_simulator_dsl_pr4_payload.py`~`pr21`、`pr23`~`pr25`（逐 id condition
  钉死断言计数全 0）；对照 pr22/pr26-pr31 各有逐 id `tuple(f.condition) == (...)`。
- **机械证据**：524 条带 condition 的载荷中 198 条的 id 在全部 `test_simulator_*.py`
  中一次都不出现。分布：TAU 4、SM 系 41、AC 17、DG 10、DRU 18、EC 22、GK 8、ORK 23…
- **失效场景**：对早期阵营 payload 的误编辑（删门、`phase_melee`→`phase_shooting`、
  裸 `target_has_keyword` 回潮）静默通过——现有守卫只锁三态计数、通道白名单、
  text_sha256（锁原文非 effects）。这正是历史五次同型 HIGH（漏阶段门过度施加）的回归
  通道，且早期阵营编在纪律成型之前，先验出错率更高。
- **建议修法**：一个全局结构锚测试——遍历 `dsl_payloads/*.json` 把 `(faction, id) →
  sorted(condition tuples)` 快照锁进 checked-in JSON 清单，改动须显式更新清单。

## F2（MEDIUM，CONFIRMED，已修复 2026-07-24，随 F1 全局结构锚一并消掉）：43 条相位门条目「双保险全缺」

- **机械口径**（三层对抗过滤后）：411 条 phase 门中，108 双向成对、86 单向，剔除错相位
  物理惰性的 23 条 + 所在文件有结构钉死的，剩 43 条「行为测试只有正向 + 无结构钉死 +
  错相位泄漏可观测」。清单存 scratchpad `mod8/phase_gate_pairs.json`；重灾 TAU 14、
  TS 4、DRU 4、SM 5。
- **失效场景**：与 F1 同型，但这 43 条「看起来有测试」，更易被误判已覆盖。
- **建议修法**：并入 F1 的全局结构锚即可同时消掉。

## F3（LOW，CONFIRMED，已修复）：test_roster_validate.py 一处恒真断言

- **位置**：`tests/test_roster_validate.py:171-172`——`assert "strike_force(2000)" in
  " ".join(...) or r.total_points <= 2000`：该 fixture 只有 80 点，左支对空串成员测试
  永假、右支 `80<=2000` 永真，整条恒真。
- **修法（已实施）**：删 `or` 逃生门，直接断言 unknown_size warn 的 message 含
  `strike_force(2000)`。
- **注**：该文件在模块 3 修复中已被 F1 强化点数改动触碰，此恒真断言一并修正。

## F4（LOW，CONFIRMED，已修复）：dsl_apply 对账测试注释账目（2782）与断言（2889）漂移

- **位置**：`tests/test_db_compile_dsl_apply.py:276-285`——注释逐 PR 列账合计 2782，
  断言 `== 2889`，差 107 为 GSC PR25 漏列。断言本身机器对账有效。
- **修法（已实施）**：注释补 GSC PR25 = 107 一行（与模块 4 L4 同一发现）。

## F5（LOW，CONFIRMED，仅记录）：覆盖缺口——CLI 装配层与 wiki 批量生成层零测试

| 未被任何测试引用 | 体量 | 风险点 |
|---|---|---|
| `db_compile/__main__.py` | 21.7 KB | 全部 CLI 子命令装配零测试（MFM 解析器本体有测试，参数接线没有）|
| `wiki_engine/from_db.py` 批量层 | generate_faction/generate_all/main | slug 撞名 -2、全阵营迭代、1715/25 对账锚缺位 |
| `wiki_engine/operations/*` | 8.3 KB | 零引用 |

- **注**：本次模块 6 F1 修复已给 `generate_faction`/`generate_all` 补了 gen_hashes
  保护的行为测试（`TestGenHashesProtection`），部分缓解此缺口。engines/simulator、
  roster、web_api、agent、db_compile 其余、wiki_engine 核心全部有测试引用（已核无误）。

## F6（NOTE）：46 个 skip 全依赖 gitignored 真库；35 文件依赖 cwd 相对路径

- 45 处 `skipif(not DB.exists())` + 1 streamlit skip，理由全写明、无 xfail、无滥用。
  但在无 `db/wh40k.sqlite` 的环境（新克隆/CI），28 个载荷对账层 + roster/web_api 集成
  层静默缩水，「全绿」≠「全跑」。建议若上 CI 加一个断言 skip 数为 0 的 job。

---

## 已核无误清单（核法附）

| 类别 | 核法 | 结果 |
|---|---|---|
| 恒真断言（assert True/or True/len>=0） | AST 逐节点判型 | 0 命中（F3 的 `or` 逃生门是唯一，已修）|
| 无 assert 的测试函数 | AST，pytest.raises/fail 计有效 | 0 命中 |
| try/except 吞断言 | AST 追踪 handler 是否捕 AssertionError 不 re-raise | 0 命中 |
| mock 打在被测本体 | 逐条人工核 21 处 patch 目标 | 全是协作者（sleep/OpenAI/上游函数）|
| 共享可变状态/共享 sqlite 写 | grep 全部写语句 + os.environ + chdir | 写全在 tmp_path；真库只读；env 走 monkeypatch |
| 计数守卫同义反复 | 逐个溯源期望值 | 2889/216/582/2091、198、74 全独立手写字面量 |
| 蒙特卡洛容差 | 全量分布统计 | 主流 abs=0.02（N=60000）；最松 0.15 出现 1 次且期望 2.0，带宽 < 最小效应量 |

## 机械扫描统计

- 文件 87 / 测试函数 1789 / assert 3563 / pytest 收集（本次修复后 1891）
- 门控对账：带门 524（相位门 411）→ 双向 108 / 单向 86 / 无行为测试 217 / 全库零引用
  198 / 双保险全缺 43

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | F1/F2 同根因，记录在案 |
| LOW | 3 | F3/F4 已修，F5 部分缓解 |
| NOTE | 1 | F6 |

## 遗留建议（按性价比排序）

1. **一个全局结构锚测试**同时消 F1+F2：`dsl_payloads` 全量 `(id → condition tuples)`
   快照对账（覆盖 524 条门控的全部回归面）。
2. `from_db.generate_faction` slug 撞名测试 + 1715 总量对账锚（T4 wiki 全量编译铺开前）。
3. 把「新载荷 PR 必带 SHOOTING_ONLY/MELEE_ONLY/NO_PHASE_GATE 三向清单」写进 P7 工作单
   模板，防止纪律再漂移。
