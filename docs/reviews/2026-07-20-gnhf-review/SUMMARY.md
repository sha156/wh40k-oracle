# GNHF 全库深度审查 · 总结（SUMMARY）

- 立项：2026-07-20，无人值守 GNHF「8 模块深度审查」（`.gnhf/runs/objective-d-project-33a66c`）
- 收官：2026-07-23，8 模块全部完成，报告落 `docs/reviews/2026-07-20-gnhf-review/`
- 背景：此前无人值守 GNHF 连续合并 20+ 个 P7 阵营 DSL 编码 PR（#39-#56）+ P6 军表 +
  P8 网站化 + wiki 生成器，多数只经 worker 自审。用户明确要求独立复核（历史教训：
  worker 会虚报）。本次审查逐模块独立复核 + 机械复现 + 对抗性自查，CONFIRMED 的
  CRITICAL/HIGH 当场修复 + 成对测试。

## 完成情况

| 模块 | 范围 | 报告 | CRITICAL | HIGH | 处置 |
|---|---|---|---|---|---|
| 1 | engines/simulator/ 引擎本体 | 01-engines-simulator.md | 0 | 2 | 已修（44dd3aed，前批次）|
| 2 | dsl_payloads/ 对照引擎语义 | 02-dsl-payloads-1/2.md | 0 | 2 | 已修（44dd3aed，前批次）|
| 3 | engines/roster/ 军表系统 | 03-engines-roster.md | 0 | 1 | 已修（4dde463c）|
| 4 | db_compile/ 编译管线 | 04-db-compile.md | 0 | 2 | 已修（990ed20a）|
| 5 | 检索链 + agent | 05-retrieval-chain.md | 0 | 1 | 已修（0a16c8a9）|
| 6 | wiki 双管线 | 06-wiki-pipelines.md | 0 | 2 | 已修（16324c9b）|
| 7 | web_api/ FastAPI | 07-web-api.md | 0 | 1 | 已修（bd3b94e1）|
| 8 | 测试质量抽查 | 08-test-quality.md | 0 | 0 | 2 LOW 已修 |

## Finding 总数与严重级分布

| 严重级 | 数量 | 已修 | 记录在案 |
|---|---|---|---|
| CRITICAL | 0 | — | — |
| HIGH | 11 | 11 | 0 |
| MEDIUM | 21 | 3 | 18 |
| LOW | 26 | 4 | 22 |
| NOTE/INFO | 3 | — | 3 |

（模块 1-2 的 4 HIGH 于前批次 44dd3aed 修复；模块 3-8 的 7 HIGH 于本批次修复。）

## 11 个 HIGH 一览（全部 CONFIRMED + 已修 + 成对测试）

1. **M1** `(hit,extra_hits)` 多来源 last-write：DSL 授予的低值 SUSTAINED 降级武器自带高值（41 条暴露）
2. **M1** `(damage,modify)` 多来源 last-write：melta 与 +1 Damage 互吞（19 条暴露）
3. **M2** AoI DISPLACER FIELD 缺阶段门：近战白拿 4+ invuln
4. **M2** WE DAEMONIC STRENGTH 缺阶段门：射击错加 D+1
5. **M3 军表** 强化点数不计入总分：压线超分军表被判合法
6. **M4 db** restore/update 层序缺口：fp_errata 新单位每次重建后点数归 NULL，三道校验静默
7. **M4 db** MFM fetch 无对账护栏 + check「可比 0」报「已完全对齐官方」（7-22 事故复发口）
8. **M5 agent** ambiguous 被判空短路：同名单位消歧通道整条死代码
9. **M6 wiki** from_db 绕过人工编辑保护 + LLM 可反向覆盖官方页（权威倒挂）
10. **M6 wiki** crosslinks 注入无词界无阵营门：125 处词中/跨阵营错链
11. **M7 web** 入参无上限绕过 n 钳制：models/loadout/units 构成算力+内存 DoS

## 主题归纳（值得沉淀的模式）

1. **多来源单值 last-write**（M1/M2 两 HIGH）：多个效果写同一 buff 通道要累加/取极值，
   不是覆盖——铺量类隐蔽坑。
2. **静默绿灯 / 绿灯谎言**（M4 两 HIGH + M5）：对账函数吞异常 = 把坏数据从口径删掉；
   「diffs 为空」有「真对齐」和「没得比」两义，判捷报前必须查样本量。复盘写下的护栏
   只留在记忆/文档 = 没有，要变成代码 raise + 测试断言。
3. **防御性降级吞掉主功能**（M5 + 历史 reranker）：判空降级抢在功能路径信号位之前执行，
   使更晚设计的协议永不触发。
4. **权威方向 / 数据倒挂**（M6 F1 + M3 F1）：LLM 合成不得覆盖官方结构库；强化点数
   要按规则真源（MFM 原文）核对，不信被测试钉成规格的旧值。
5. **限流按真正的放大杠杆设**（M7）：最显眼的参数（n）未必是资源瓶颈（武器数×攻击数）。
6. **门控成对性纪律漂移**（M8 F1/F2）：早期阵营 198 条门控载荷零回归锚，是历史五次
   同型 HIGH 的回归通道——建议全局结构锚快照对账。

## 遗留（非阻塞，未修的 MEDIUM/LOW 记录在各模块报告）

- **wiki 数据正确性**（M6 F3-F7）：武器中文名张冠李戴 89 单位、-2 去重页孤儿、AoI 同名
  档、Ghazghkull invuln 截断、build_outputs 转义漏网——建议合并一个 PR 抽公共
  `parse_wikilink()`，改完全库重跑 from_db→crosslinks→build→lint 并 diff 对账。
- **门控全局结构锚**（M8 F1/F2）：dsl_payloads 全量 `(id → condition tuples)` 快照测试。
- **诚实降级文案**（M3 F3/F5、M5 M3/M4）：数据缺口消息只说系统知道的事实；agent 军表
  工具「计划于 P6」过期文案。
- **11 版编制规则查证**（M3 F2）：battleline/DT 豁免上限落常量。

## 本批次（模块 3-8）交付

- 7 份模块报告（03-08）+ 本 SUMMARY
- 7 个 HIGH 修复 + 27 条成对测试（web_api DoS 封顶、agent 消歧、军表强化点数、db 层序+
  MFM 护栏、wiki 权威保护+注入门）+ 2 条 LOW 测试质量修复
- 全量 pytest **1891 绿**（基线 1864 + 27 新测试）
- 分支 `review/gnhf-modules-3-8`，逐模块「报告 commit + 修复 commit」独立提交
