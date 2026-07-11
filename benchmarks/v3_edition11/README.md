# 11 版基线 v3（2026-07-11 起用）

- **gold**：根目录 `qa_gold.json`（meta.version=v3, edition=11）。迁移审计见
  `docs/superpowers/specs/2026-07-11-qa-gold-v3-edition11-audit.md`：规则类 7 题 +
  #41 按 11 版更新，stat/weapon 78 题零漂移。
- **qa_agent_results_baseline.json**：v3 基线 **93.8**（90✅ / 2⚠️ / 4❌，agent 路径，
  2026-07-11 run2，wiki 术语页 11 版化之后）。
- **qa_agent_results_run1_prewikifix.json**：run1 91.7——wiki core-rules 术语页仍为十版
  时的成绩，#86/#88 因 get_keyword_definition 读到旧版规则被扣；11 页术语页升级后转绿。

## 与 v1（97.9，benchmarks/v1_10th/）的差距核因

两轮 v3 稳定复现的 4 个 ❌ 全部是**实体解析缺陷**（非版本迁移、非 gold 漂移，gold 未变的题）：

| 题 | 现象 | 根因 |
|---|---|---|
| #23 混沌教徒 | 抓成"诅咒教徒 Accursed Cultists"（T4≠gold T3） | 同阵营近名混淆 |
| #48 复仇者小队 | 抓成"破坏者小队"，答"无弹射器" | 缺"复仇者小队"别名（应 Dire Avengers） |
| #65 机械教游侠 | 抓成灵族"游侠"（SV5+≠gold 4+） | 跨阵营同名 Rangers 消歧缺失 |
| #76 死亡连无畏 | 抓 Faction Pack 磁力勾爪变体（T9≠基础型 T10） | 11 版 overlay 变体数据表 vs 基础型消歧缺失 |

另 2 ⚠️（#19 连长多型号赘述 / #42 兽人格斗武器只列 1 把）为作答风格/覆盖度波动。
v1 与 v3 成绩不可直接比较（7 题 gold 语义变了 + 语料从 37 本十版换成 61 本分层）。
