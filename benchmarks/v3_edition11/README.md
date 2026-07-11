# 11 版基线 v3（2026-07-11 起用）

- **gold**：根目录 `qa_gold.json`（meta.version=v3, edition=11）。迁移审计见
  `docs/superpowers/specs/2026-07-11-qa-gold-v3-edition11-audit.md`：规则类 7 题 +
  #41 按 11 版更新，stat/weapon 78 题零漂移。
- **现行基线 = 99.0**（95✅ / 1⚠️ / 0❌，`qa_agent_results_after_entity_fixes.json`，
  2026-07-11 run4）。唯一 ⚠️ = #42 题面歧义（"格斗武器"按字面答 Close combat weapon
  行，数值正确；gold 期望列全 4 把近战武器）——风格噪声，与十版 v1 的 2⚠️ 同类。

## 达成路径（四轮，逐轮核因）

| 轮 | 分数 | 状态 | 修了什么 |
|---|---|---|---|
| run1 | 91.7 | `..._run1_prewikifix.json` | —（暴露 wiki 术语页十版残留：#86/#88 引用已出索引的《10版速查表》） |
| run2 | 93.8 | `..._baseline.json` | wiki core-rules 11 个术语页 11 版化 → #86/#88 转绿 |
| run3 | 96.9 | `..._run3_alias_only.json` | community 别名 4 条（#23/#48/#76 转绿；撞名单位经 canonical id 直取） |
| run4 | **99.0** | `..._after_entity_fixes.json` | 修 `_TOOL_ARG_HINTS` 截短指令（#65 转绿） |

## 四个实体解析缺陷的最终定因与修法

| 题 | 根因 | 修法 |
|---|---|---|
| #23 混沌教徒 | 库内无此别名且 Cultist Mob **三行撞名**（CD/CSM/QT） | community 别名 → canonical id 直取 000000946（CSM 本尊） |
| #48 复仇者小队 | 缺别名（库内名「狂暴复仇者」），resolver 候选全错 | community 别名 → Dire Avengers |
| #65 机械教游侠 | **提示词自伤**：`_TOOL_ARG_HINTS` 教 LLM"不要带阵营前缀"，把连写限定名截成「游侠」→ 精确命中灵族 Rangers confident 错答 | 别名 → 000000848（AdM，两行撞名）+ 改提示词：连写限定名整串传、仅「XX的YY」所属格才拆 |
| #76 死亡连无畏机兵 | 「机兵」后缀无别名 → ambiguous 降级 → 经典链被 FP 磁力勾爪**变体**数据表抢答（11版仲裁偏好放大） | community 别名 → Death Company Dreadnought，走查表路径（T=10） |

防回归：`tests/test_db_compile_entity_resolver.py::TestRealDbCommunityAliasRegression`
（真库四条断言）+ `TestPopulateCommunityAliases`（canonical id 直取单测）。

## 与 v1（97.9，benchmarks/v1_10th/）的关系

v1 与 v3 成绩不可直接比较（7 题 gold 语义变了 + 语料从 37 本十版换成 61 本分层）。
v3 修复后 99.0 且零硬错，11 版口径下已超过十版基线水平。
