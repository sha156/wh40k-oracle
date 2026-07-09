# 数据架构定论：什么层用什么数据（2026-07-09）

> 背景：项目积累了 6 条数据线（黑图书馆 / 中文 PDF / 英文 PDF / 官方 GW / BSData / Wahapedia），
> 数据流交叉、准确率数字反复波动。本文基于 6 个研究代理对全部代码与数据的实测盘点
> （sqlite 逐表计数、FAISS docstore 解包、gold 评测逐题法证、关键论断交叉裁决）写成，
> 是数据用途的**最终裁决**：每层只用指定数据，其余明确判死或降级。

---

## 一、结论先行

1. **数据不乱，乱的是"同一事实存了多份、消费端各取一份"。** 同一个单位的属性/点数目前
   最多有 **5 份物理副本、4 个点数源**（中文 PDF 印刷分 / Wahapedia 累加分 / MFM 官方分 /
   黑图书馆 score），且实测 **29/919 个单位在 Wahapedia 与黑图书馆之间数值真冲突**。
2. **准确率"一直变"三个来源，按量级排序：评测口径换了三次（±10~15 分）＞ 真实代码/数据
   改进（+3~12 分）＞ LLM judge/生成随机性（每跑 ±2~4 分）。** 旧分数（77/92/95）与
   gold 分数（85.4/80.2）不可横向比。今后 **qa_gold 96 题 + judge_gold 是唯一基准线**。
3. **gold 下 agent（80.2）输 classic（85.4）的真凶不是降级、不是数据**——降级 35 题两条链
   各错 7 道完全打平。真凶是 `agent/loop.py` 允许 LLM **第一步不调任何工具直接作答**：
   16 题零工具直答错 9 道（56% 错误率），全是参数记忆幻觉 + 伪造英文书页引用。
   而**真正走了工具的 45 题，逐题核对后真实错误为 0**（3 个 ❌ 全是 judge 误判）——
   **agent 工具路径是全系统最准的路径**，被一个 loop 缺陷拖垮。
4. 最大化准确率的路径不是再加数据，而是：**修两个 bug（零工具门控、judge 机械比对）→
   把别名和数值收敛成单一真源 → 清掉污染检索的死数据（英文包占索引 31.4%）**。

---

## 二、数据资产盘点（实测）

### 六条外部数据线

| # | 数据源 | 规模（实测） | 新鲜度 | 定位 |
|---|--------|------------|--------|------|
| 1 | **官方 GW**：MFM 分数页 + 下载页 | mfm_points.json 1670 条/30 阵营；downloads manifest 35 个官方 PDF | 2026-07-08 抓取 | **分数最高真源**；下载页做版本监控 |
| 2 | **Wahapedia CSV**（10 张表） | units/datasheets 1712、models 1817、weapons 9307、stratagems 1482 | 07-05/07-07 下载 | **英文结构骨架**（属性/武器/关键词） |
| 3 | **BSData/wh40k-10e**（git clone 36MB） | 48 个 .cat；与 Wahapedia 同名匹配 80.5%、属性一致 98.9%、真分歧 14 处 | 07-08 pull | **只读交叉校验**，永不写库 |
| 4 | **黑图书馆 API**（blackforum） | units.json 1167 单位中英名；details.json 1070 条中文 datasheet → 入库 920 | 07-08 抓取 | **中英别名桥 + 中文原生 datasheet 正文** |
| 5 | **中文汉化 PDF**（data/ 64 本） | → data_refined 4795 chunks（63 本，deepseek 逐页重构） | 版式各异、数值随印刷版本过时 | **规则正文 + 译名来源**；数值不可信 |
| 6 | **英文 Faction Pack PDF**（29 本） | → 1793 chunks，占当前索引 **31.4%** | 已被 Wahapedia/BSData 完全取代 | **该归档没归档**（见第四节） |

### 三个派生存储（真正被查询的东西）

| 存储 | 内容 | 消费方 |
|------|------|--------|
| `db/wh40k.sqlite`（L3，8.4MB/10 表） | Wahapedia 骨架 + MFM 覆写 957/1712 单位分数 + aliases 1633 条（blackforum 921/data_refined 707/community 5）+ unit_zh_detail 920 行黑图中文层 | agent 的 get_datasheet/calc_points/entity_resolver；ingest --rebuild 注入 |
| `local_vector_store/`（L1，5715 chunks） | data_refined 4795（含英文包 1793）+ 黑图书馆渲染 920；原始 PDF 直切 0 | classic 的 FAISS+BM25+RRF |
| `wiki/`（L2） | terms.json 187 对（**可用的 zh+en 仅 62 对，全部来自钛帝国一本试点书**）；factions 仅 2/26 阵营 | classic 查询扩展只吃 terms.json；index/factions 只有默认关闭的 agent 工具在用 |

---

## 三、层 → 数据映射（定论，照此执行）

**核心原则：一类事实只有一个真源，其余数据要么服务别的用途，要么降级为校验。**

| 问题类型 / 功能 | 唯一指定数据 | 明确不许用 |
|----------------|------------|-----------|
| **点数/分数** | `units.points_json` 的 **mfm 块**（官方 MFM 覆写）；未覆盖的 751 个单位取 `min(items.cost)`（Wahapedia 档位最小值） | 中文 PDF 印刷分、黑图书馆 score、Wahapedia 顶层累加和（语义就是错的） |
| **属性 M/T/Sv/W/OC、武器 A/S/AP/D** | `models`/`weapons` 表（Wahapedia），BSData 交叉校验兜底 | 中文 PDF 表格（拍扁+过时）、黑图数值（29/919 与权威源冲突） |
| **中文名→canonical 实体解析** | `aliases` 表（1633 条，三源）——**全系统唯一别名库，classic 和 agent 都必须接** | app.py 硬编码 UNIT_ALIASES（10 条，迁入 aliases 后废弃） |
| **规则正文/技能描述（中文语义检索）** | data_refined 中文 chunks + 黑图书馆 abilities 正文（L1）；wiki 页（试点范围内） | 英文 Faction Pack chunks（归档后自然消失） |
| **英文技能文本（按单位查）** | 目前**断裂**（abilities 表被主键折叠，7158 行关联只剩 48 行）——修好前由 unit_zh_detail.abilities_json 中文层代偿 | — |
| **英文属性正确性校验** | BSData crosscheck（只读，报告落 db/crosscheck_report.json） | — |
| **版本/更新监控** | downloads manifest + MFM fetch（周日 4am 计划任务） | — |
| **译名风格/机翻润色参考** | 中文 PDF（这是它降级后的唯一数据角色） | — |

一句话版本：**数值走 sqlite（官方链），名字走 aliases 表，正文走中文检索层，英文 PDF 全部退场，BSData 只做校验，黑图书馆出"名字和正文"但不出"数值"。**

---

## 四、没用的数据（处置清单）

### 直接删（约 2.8GB，零风险～低风险）

| 目标 | 大小 | 理由 |
|------|------|------|
| `data/总规则.zip` | 296MB | 全仓库无代码消费 .zip；解压产物已在 data/archive/ |
| `opt/models--BAAI--bge-m3` 孤儿快照 9a0624b8 + blob 993b22 | 2.27GB | refs/main 指向 5617 快照（pytorch_model.bin），此快照无 ref 引用。**删前离线跑一次 ingest 验证加载**，别删错 blob（b5e0ce 是在用的） |
| `opt/ms-marco-MultiBERT-L-12` | 162MB | USE_RERANKER=False，且即使开开关加载的也是 MiniLM；实测中文重排差于 RRF |
| `opt/ms-marco-MiniLM-L-12-v2.zip` + `__MACOSX/` + `bge-small-zh-v1.5/`（空） | 22MB+ | 解压残留/废弃占位 |
| `data_blacklibrary/` | 11MB | 与 db_sources/blacklibrary/details.json SHA256 逐字节相同的死副本；**需同步改 `scripts/fetch_blacklibrary_details.py` 的默认输出路径**，否则下次抓取又写回这里造成双副本漂移 |
| 13 个历史 `qa_*.json` + 13 个旧 `.log` | ~2MB | qa_bench 只读 qa_gold.json；历史 run 无消费者（要留曲线就移 archive/） |

### 归档（需要动作 + 必须原子地 --rebuild）

- **29 本英文 Faction Pack PDF + 对应 data_refined 目录**：commit e67a3676 宣称"归档 25 本英文包"
  但**实际只改了 .gitignore，一个文件都没移动**（archive/en_faction_packs/ 是空目录）——典型假修复。
  这些英文 chunk 现占索引 **1793/5715 = 31.4%**，与中文 CODEX 描述同一批单位，在 top-k 里直接
  稀释中文召回。归档后必须 `ingest.py --rebuild`（processed_files.json 的增量机制**不会**删除已
  入库 chunk，只归档不重建 = 静默污染继续存在）。
- 归档前人工复核两本：`帝国骑士英文.pdf` / `死亡守望英文1.01.pdf`——它们对应的**中文版反而在
  archive 里**，疑似当初归档方向搞反。
- `data/Misc - Terrain Area Footprints.pdf`：扫描版无文字层，从未入库，留待二期 OCR。

### 保留但当前无效（知道就行，不必动）

- ms-marco-MiniLM（33MB）：开关重开时的指定模型，随 USE_RERANKER 一起决策。
- wiki/ 的 index.md/factions/core-rules：只有默认关闭的 agent 实验工具消费，暂无害。
- `unit_zh_detail.intro_json`（920 行简介）写而不读；sqlite 里 version/effect_dsl_json 等
  预留列恒 NULL——是蓝图 P4/P5 的占位，不是垃圾。

---

## 五、准确率为什么一直变（法证结论）

完整时间线（全部 DeepSeek judge，temperature=0）：

| 时间 | 分数 | 变化来源 |
|------|------|---------|
| 07-05 | 77%（100 题旧 judge） | 原始基线 |
| 07-06 | classic 92% = agent 92%（degraded=79） | 检索修复（真）＋ judge 重建变宽（intrinsic 只看"自信+有数字+有引用"，**假引用照样给 ✅**）；agent 当时 79 题降级 ≈ classic 换皮，两个 92 相等是必然 |
| 07-08 | 检索 69→81；agent 88→94→95 | get_datasheet/别名层/MFM/意图路由 6 连 commit，**真提升** |
| 07-09 凌晨 | agent 95→91、检索 81→79 | **题面逐字相同、数据只增不减**——这 4 分纯属 judge/生成随机性，铁证 |
| 07-09 13:41 | **gold：classic 85.4 / agent 80.2** | 题集清洗（删 4 假题改 2 题）＋ judge 换成逐值对标 sqlite/黑图权威答案——旧口径下漏放的幻觉与过时数值集体现形 |

**三条纪律（固化）：**
1. gold 96 题 + judge_gold 是唯一基准线，77/92/95 全部作废不可比；
2. 单跑 <3 分的差异不构成任何结论，重要对比跑 3 次取中位；
3. `qa_gold.json` 和 `scripts/qa_bench.py` 的口径改动**必须进 git**（当前都未提交——评测真源
   处于无版本控制状态，误删即不可复现）。

### gold 下 agent 输 classic 的逐题账本（已交叉验证）

- 翻转账本：classic✅→agent❌ **10 题**；agent✅→classic❌ **5 题**；净差 -5 题 = -5.2 分。
- 降级 35 题：agent 错 7、classic 同题错 7，**净差 0**——降级只费时间不丢分。
- 亏损 10 题里 **8 题是零工具直答**（tool_calls=[]、degraded=False）：模型拿九版旧记忆答十版
  数值（莫塔里安 W 答 12，库里两个源都是 16），并伪造"Codex: T'au Empire p89"式引用。
- 工具路径 45 题表面错 3 道，逐题核对 **judge 全部误判**（如 #10 答案逐字包含 gold 要求的效果
  文本，judge 却称"未回答"）——**工具路径真实错误率 0/45**。
- 增益 5 题全是 get_datasheet 权威单值碾压检索（多版本 PDF 混战时 DB 给唯一 M9、别名解析成功）。

---

## 六、最大化准确率的行动清单

### P0：修两个 bug（不动任何数据，预计收益最大）

1. **堵零工具直答**（`agent/loop.py:107-117`）：intent∈{查,判} 且 tool_calls==[] 时拒绝 final
   ——强制先调 get_datasheet/rag_search，或把零工具 final 视同降级转 classic。
   覆盖 agent 19 错中的 9 道 + 消灭伪造引用。**预计 agent 80.2 → 88~90。**
2. **judge 机械化**：stat/weapon 类题改两段式——LLM 只负责从回答里抽取被问数值，正则/程序与
   gold 比对；"多报字段不扣分、漏项判 ⚠️"写进 few-shot。当前至少 6 题冤案（#10/18/42/62/81/95）。
   **预计两条链各 +4~6 分，并把评测噪声压到能看清后续改进的水平。**
3. **评测资产入库**：提交 qa_gold.json、qa_bench.py 的 gold 判分 diff。

### P1：数据收敛成单一真源

4. **别名统一**：classic 的 expand_query 启动时从 sqlite aliases 表载入全部 1633 条
   （替代 10 条硬编码 UNIT_ALIASES）——法证实证 #70/#100 两题别名在 agent 侧生效、classic 侧
   没吃到。顺手补 4 条已确认缺口：战争老大→Warboss、惩罚者机甲→忏悔者机甲、
   弹射器→星镖枪、离子爆破者→Ion blaster。
5. **消灭第 4 点数源**：`build_blacklibrary_docs` 渲染 L1 chunk 时去掉「点数：N」行
   （黑图 score 无版本标记，绕过 MFM 权威链直接流进 classic 回答）。
6. **get_datasheet 冲突告警**：合并 Wahapedia 块与黑图中文块时逐字段 diff，29/919 个不一致
   单位标注"黑图与官方源不一致，以官方为准"——否则单次回答内部自相矛盾。
7. **英文包真归档 + --rebuild**：索引 5715 → ~3900，中文召回提纯（检索层 85% 的失分里
   有版本混战与稀释的直接成分：#14 等离子焚化枪、#25 地狱兽四版本）。
   同批修：`Faction Pack Astra Militarum` 只 refine 了 51/156 页（105 页静默缺失）、
   `get_book_name` 把两本点数 PDF 合并成 book="6月"（331 chunks 引用失真）。
8. **修 abilities 表折叠**（build.py 主键改复合键）：找回 ~3500 条单位→技能关联，
   恢复英文技能真值链。
9. **calc_points 语义统一**：与 datasheet 一致取 `min(items.cost)`，废除累加和。

### P2：管线防呆与评测治理

10. **build/apply 顺序机械防护**：单独跑 `db_compile build` 会静默把 957 个官方分回退成
    Wahapedia 旧值并清空 aliases/unit_zh_detail——build 后自动跑 mfm apply + 别名阶段，
    或 build 单独执行时直接拒绝。
11. **L1/L3 同步**：db_compile 周更后黑图书馆 chunk 不会进 FAISS（只在 --rebuild 时注入），
    把"周更成功 → 提示/自动 --rebuild"接进 update 管线第 12 阶段。
12. **qa_gold v2**：修 #19/#55（"光环"→"招牌技能"口径）、重核 #41（怪异小子↔Boyz 配对可疑，
    Weirdboy 直译恰是怪异小子）；把本次 24 道错题的预期 verdict 做成 judge 校准集。
13. **数值题硬路由**：属性/点数类意图直接 gating 到 get_datasheet（工具路径已证实 0 真错），
    对应蓝图"数值类回答必须来自 SQLite"的反幻觉铁律。

### 预期落点

| 指标 | 当前 | P0 后 | P0+P1 后 |
|------|------|-------|---------|
| agent（gold） | 80.2 | 88~90 | **92+** |
| classic（gold） | 85.4 | 89~91（judge 修复） | ~90（别名+去稀释再加，但 classic 定位降为兜底） |
| 条件生成率 | 94.1~97.5 | — | 维持（捞对就答对，早已达标） |

剩余失分构成会变成：judge 残余噪声 + 题面口径之争 + 真检索长尾——到那时再谈 wiki 全量编译
（L2 目前只覆盖钛帝国一本书的 62 条术语，是蓝图 P1 的欠账，不是当前瓶颈）。

---

## 七、与 v2 蓝图的关系

本文不改蓝图分层（L0-L6 照旧），只是把"每层吃什么数据"从蓝图的应然写成实然并裁决冲突：

- 蓝图第四节"数值权威源 = Wahapedia/BSData"→ 已升级为"**官方 MFM > Wahapedia+BSData 交叉**"（2026-07-08 用户拍板）；
- 蓝图的 aliases 表设计已落地且应成为唯一别名库（本文 P1-4 是把 classic 接上去补完它）；
- 黑图书馆是蓝图定稿后新增的源，本文给它定的角色：**别名桥 + 中文正文层，不做数值源**；
- abilities/DSL 列的 NULL 是 P4/P5 占位，不算数据债；abilities 表折叠（本文 P1-8）是真 bug。

---

## 八、实施记录（2026-07-09，本文 P0-P2 已全部落地）

| 项 | 改动 | 验证 |
|----|------|------|
| **P0-1** 零工具直答门控 | `agent/loop.py`：查/判/算 意图零工具 final → 强制纠偏一次 → 仍零工具则降级 classic | 5 个新单测 + 全套 337 绿 |
| **P0-2** judge 机械化 | `scripts/qa_bench.py`：stat/weapon 78 题两段式（LLM 抽值 + 程序比对），76 题走机械、2 道多武器回落；ability/rule 加 few-shot；`_GOLD_JUDGE_SYSTEM` 明确"多给不扣分/漏项判⚠️" | 20 个新单测；#62/#81/#95 冤案消除 |
| **P1-4** 别名统一 | `app.py` expand_query 接入 sqlite `aliases`（1108 条有效扩展）；`community_aliases` 补 战争老大→Warboss、惩罚者机甲→Penitent Engines；修掉失效的 惩罚者机甲→赎罪引擎 | 别名端到端验证 + 3 单测 |
| **P1-5** 黑图去点数源 | `build_blacklibrary_docs` 去掉「点数：N」行（黑图 score 曾是绕过 MFM 的第 4 点数源） | 已改 SELECT |
| **P1-6** get_datasheet 冲突标注 | `datasheet.diff_core_stats`：官方 vs 黑图 M/T/SV/W 不一致时标注"以官方为准"（全库检出 10 个真冲突，零误报） | 5 单测 + 真数据校验 |
| **P1-7** 英文包归档 | 25 个英文 Faction Pack + Core Rules 英文 → `archive/en_faction_packs/`（保留 Custodes/Titanicus/Deathwatch/Imperial Knights 等无中文对应者）；FAISS 5715→3936 chunks | 重建索引，英文包 chunk 清零 |
| **P1-7** get_book_name | `ingest.py`：改为只剥结尾版本/日期噪声，不再在中间数字截断 | "6月"合名消除，无撞名 |
| **P1-8** abilities 折叠 | `build.py`：链接行改单位内递增序号做主键，保住 3607 条单位→技能关联（70→3677 行，覆盖 1709 单位） | 重建 + 回归单测 |
| **P1-9** calc_points 语义 | 取 `min(items.cost)` 与 datasheet 一致，不取顶层累加和 | 新单测 |
| **P2-10** build 防呆 | `db_compile build` 默认自动补回 MFM/别名/中文层（`restore_authority_layers`），`--no-restore` 才留降级库 | 已跑一次重建验证 |
| **P2-11** L1/L3 同步提示 | update/build 结尾提示需 `ingest.py --rebuild` 同步 FAISS | — |
| **P2-12** qa_gold v2 | #19/#55 光环→招牌技能、#41 怪异小子→兽人小子(Boyz) 去歧义 | — |

未做（超出本轮或需人工决策）：帝国骑士/死亡守望的"中文版反被归档"需先 llm_refine 中文版才能反转（本轮保留英文包避免该阵营从索引消失）；wiki 全量编译（L2 仍只覆盖钛帝国一本，属蓝图 P1 欠账，非当前瓶颈）。
