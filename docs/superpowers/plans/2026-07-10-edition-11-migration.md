# 11 版迁移改动计划（v1，执行中）

> 2026-07-10 用户裁决：本项目目标版本切换到 **11 版**（2026-06-20 生效），十版内容归档。
> 本文档 = 版本对比 + 现状盘点 + 分阶段改动方案。
>
> **执行进度（2026-07-10 晚，D1-D5 全按推荐拍板）**：
> - ✅ S1 语料重组：27 个 11 版文件回灌 data/、十版规则 3 本入 archive/10th_rules/，
>   共 61 本；corpus_manifest.json + ingest edition/layer 元数据落地；--rebuild 已启动
>   （5571 chunks：11版 rules 141 / overlay 1801 / points 267 / balance 68 / event 13 +
>   10版 codex-base 3281 含黑图书馆 920；refined 缓存全命中，零 LLM 费用）
> - ✅ S3 快速项：fight_order 回翻 11 版 active-first（12.04）+ COUNTEROFFENSIVE 按 p57
>   改写 + CLI/UI/persona 版本措辞；666 测试绿。S3 剩余：24 章 USR 逐条审计
> - ✅ S4 先行项（D4）：MFM 官方实时站 2026-07-10 重抓，1224/1224 一致 0 过期；
>   7 个 MFM-only 单位（含 titan-legions 解析 0 条）待 DB 迁移补数据表
> - ✅ S2 代码侧：edition/layer 标签贯穿 context/来源展示/agent 透传 + 版本仲裁 prompt
>   （54e09a2a）；检索质量实测待新索引
> - ✅ S3 审计+实现：USR 审计报告（specs/2026-07-10-edition-11-usr-audit.md）；B 类修正
>   已落地（22a17905：Stealth 掩体化/间接固定阈值/Heavy 条件/Blast X/Cleave/lethal 披露），
>   686 测试绿。~~S3 残留~~ **S3 残留三项已收口（2026-07-11，691 测试绿）**：
>   B6 PSYCHIC 确认 11 版新增并建模（忽略不利命中修正）、dev 致命池不再吃"受伤-1"减伤
>  （24.10 序列结束直接施加）、核心战略审计——Smokescreen 改纯掩体（SMOKE 关键词）、
>   Go to Ground 已从 11 版移除（开关删除+显式披露）
> - ✅ S4 调研：wahapedia 未迁移（wh40k11ed 系 alias，last_update 2026-06-13）；
>   黑图书馆无 11 版（gameId=5 是 Kill Team）；**BSData/wh40k-11e 已建仓且当天仍在推送**
>   （尚无 .cat 落地）——观察项，成熟后走 crosscheck 接入
> - ⏳ 待做：S2 中英跨语检索实测、S5 基准 v2、S6 术语复核
>  （重建后验证已收官——9b799f04 规则层保底检索+引用防编造加固）

---

## 1. 版本判定证据（那批英文官方文档确为 11 版）

- Faction Pack 自述：**"Legal for matched play from 20th June 2026"**、"the first iteration of
  this Faction Pack **for this edition** … designed to **smooth the transition**"（钛帝国包 p1）
- 《Core Rules - New 40K Core Rules》目录含 **SURGING**(21章)/**ACTIONS**(16章) 等非十版章节，
  全书使用 `12.04` 式编号条款，**全书 0 次出现 "Engagement Range"**（十版最高频术语，11 版改用
  engaged/unengaged）
- Fight phase 同步内交替方向与十版相反（详见 §4.2）
- 新阵营 **Adeptus Titanicus**（十版无此 40K 阵营）同时出现在 Faction Pack 集与
  《6月4日分数中文》目录 → 该点数文档 = **11 版军务部野战手册（MFM）v2.7 中文民间译本**；
  《6月4日平衡版中午》= 同批 11 版平衡副本（计谋全局调整）中文译本

## 2. 现状盘点（全部已核实）

**当前 FAISS 索引共 37 本**（`local_vector_store/processed_files.json`）：

| 类别 | 数量 | 明细 |
|---|---|---|
| 十版中文规则类 | 3 | 战锤40K总规则10版老湿腐版1.11、10版40K通用技能速查表1.08、规则注解中文 |
| 十版 codex（中文为主） | 27 | 各阵营 codex（含 死亡守望英文、帝国骑士英文 两本英文版） |
| 11 版已入库 | 7 | 6月4日分数中文（MFM）、6月4日平衡版中午、Event Companion - Dominatus、Faction Pack ×4（Custodes/Titanicus/Deathwatch/Imperial Knights） |

**关键事实：11 版核心规则目前不在索引里。** 它的 PDF 与另外 25 个 Faction Pack 全部在
`archive/en_faction_packs/`（26 个文件，未被 ingest 扫描）；`data_refined/Core Rules - New 40K
Core Rules/` 等目录是当时跑过 refine 留下的缓存（可复用，重建索引时省 LLM 费用）。

其他资产版本归属：

| 资产 | 版本 | 说明 |
|---|---|---|
| `db/wh40k.sqlite`（wahapedia CSV） | 十版 | 全部单位属性/武器/点数 |
| 黑图书馆中文层、BSData 交叉校验 | 十版 | |
| `qa_gold.json` 96 题基准 | 十版 | stat/weapon gold 出自十版 DB |
| `wiki/terms.json` 中英配对、别名层 | 十版 | 单位名跨版本大多稳定 |
| `engines/simulator/` | 十版 | fight_order 今晨刚按十版裁决翻转（215f009d），切 11 版需回翻 |
| `data/总规则.zip`（295MB，49 条目） | 混合 | 原始来源备份：中英双语 codex、10E 官方双语核心规则、6月4日分数**英文**版等，未入库 |

## 3. 最重要的架构结论：11 版不是推倒重来

Faction Pack 原文写明它是"additional rules and clarifications that **supplement your Codex**"
——**十版 codex 在 11 版继续合法**，官方靠三层补丁桥接：Faction Pack（新分队/数据表更新/FAQ）
+ 平衡副本 + 新 MFM。

⇒ 推论：「归档所有十版内容」若把 codex 也归档，会**同时清空全部兵牌数据源和几乎全部中文语料**，
且与 11 版官方设计相悖。真正被 11 版**整体取代**、应该归档的是十版**规则类**文档
（总规则/速查表/规则注解），codex 应保留为"兵牌基底层"。→ 决策点 D1。

## 4. 十版 → 11 版规则对比（对本项目有影响、已核实的）

### 4.1 文档体系
| | 十版 | 11 版 |
|---|---|---|
| 核心规则 | 总规则（无编号条款） | Core Rules 89 页，`24.13` 式编号条款（引用锚点可从页码升级为条款号） |
| 兵牌 | codex | **沿用十版 codex** + Faction Pack 补丁 |
| 点数 | MFM（十版） | 新 MFM（v2.7，中文译本已有） |
| 平衡 | Balance Dataslate | 平衡副本（中文译本已有） |

### 4.2 机制差异（已从 11 版原文核实）
- **Fight phase 同步内交替**：十版从非当前玩家起 → 11 版 "Starting with the player whose turn
  it is"（12.04，当前玩家先）；Remaining Combats 从"把流程推进到该步的玩家"起
- **冲锋仍授予 Fights First**（p37 "each model in your unit has the Fights First ability
  (24.13)" + p39 双冲锋示例）——模拟器 charged→FF 假设可保留
- **Counter-offensive 对应战略改版**（p57：效果变为"获得 Fights First 且必须是下一个被选中
  结算的单位"）——fight_order 的 CO 说明需按新文本改写
- **新机制**：Overrun Fights（未接敌单位可参战）、SURGING（21 章）、ACTIONS 进核心规则（16 章）
- **术语**：Engagement Range → engaged/unengaged

### 4.3 待审计（S3 工作项，本文不定论）
- 攻击序列（04/05 章）与武器/通用技能（24 章 CORE ABILITIES）逐条 vs 十版 → 模拟器 20 词条
  映射逐个确认（速射/热熔/致命破灭/FNP 等语义是否变化）
- Faction Pack 改动了哪些单位的数据表数值（qa_gold 与 DB 的影响面清单）

## 5. 分阶段执行计划

### S1 语料重组 + 重建索引（半天人工 + CPU 数小时）
1. `archive/en_faction_packs/` 27 个文件（11 版核心规则 + 26 Faction Pack）全部移回 `data/`
2. 十版规则类 3 本（总规则10版/速查表/规则注解）移入 `archive/10th_rules/`
3. `ingest.py` 元数据加 `edition`（10/11）与 `layer`（rules/codex-base/overlay/points/balance/event）
   字段，书名→层映射用 manifest 文件维护（不硬编码进代码）
4. `--rebuild`（Faction Pack 系列 data_refined 缓存俱在，LLM 费用≈0，主要是嵌入时间）
5. 验证：索引书目清单 == 预期清单；抽查 3 个规则问题引用落在 11 版核心规则
### S2 检索/生成版本感知（约 1 天）
- 规则条文冲突时 11 版优先并在回答中标注版本；引用格式带条款号（`[Core Rules 12.04]`）
- 实测中文查询 ↔ 英文语料检索质量（BM25 必失配，看 bge-m3 跨语 + 别名扩展够不够；
  不够则考虑 11 版核心规则跑一版中文 refine）
### S3 模拟器 11 版化（1-2 天）
- fight_order 回翻 active-first（引用 12.04 条款号）、CO 说明改写、保留今晨的相位边界修复
- USR 词条 diff 审计（4.3）；全仓 grep「十版」措辞与 rule_refs 逐处更新
- 过渡期未完成前，模拟器输出加"十版口径"警示
### S4 结构库迁移（依赖外部源，时点另定）
- 调研 wahapedia / 黑图书馆 / BSData 的 11 版数据可用性
- 先行项：用《6月4日分数中文》（11 版 MFM）经 `db_compile.mfm` 灌新点数（数据表属性暂沿用十版
  + Faction Pack 补丁披露）；DB 加 edition 维度
### S5 基准迁移
- 冻结现 96 题基准为「十版基线 v1（97.9）」；11 版 DB/点数落地后重生成 qa_gold v2 重跑
### S6 wiki/terms/别名层复核（低优先）
- 单位名跨版本大多稳定；DB 迁移后跑 crosscheck/check_points 复核即可

## 6. 需要拍板的决策点

| # | 决策 | 选项 | 推荐 |
|---|---|---|---|
| D1 | 十版 codex 去留 | A. 保留为兵牌基底层（11 版官方设计如此） / B. 严格全归档（后果：无兵牌数据、无中文语料） | **A** |
| D2 | 英文语料回灌范围 | A. 全部 27 个（核心规则+26 包） / B. 只回灌有对应 codex 的阵营 | **A** |
| D3 | Event Companion（组织赛文档，archive 里还有 Doubles/Teams 两本孤儿缓存） | A. 入库标 layer=event / B. 归档 | A（已入库 1 本，保持） |
| D4 | S4 时机 | A. 等 wahapedia 11 版 / B. 先用 11 版 MFM 点数过渡 | **B** |
| D5 | 总规则.zip 里的英文 codex（帝国骑士英文/灰骑士英文/混沌恶魔英文…） | 是否解压补强英文兵牌语料 | 暂缓，S2 实测后再定 |

## 7. 风险

- **中文问答体验**：11 版规则真源是英文，中文引用体验下降；民间 11 版汉化（MFM/平衡版已有）
  出一本补一本
- **gold 漂移**：Faction Pack 改数值的单位（待 4.3 清单）会让部分十版 gold 失效，S5 前基准
  数字只代表"十版口径"
- **fight_order 已按十版翻转**：S3 前模拟器同步内先攻方向是十版口径（今晨 215f009d），
  与 11 版相反——需尽快随 S3 回翻，避免"新版项目旧版判定"
- **总规则.zip 与散文件疑似重复**（zip 49 条目 vs 曾记录"data/ 49 个 PDF"），S1 移动文件时
  以 data/ 现存文件为准，zip 只作备份源，不重复入库
