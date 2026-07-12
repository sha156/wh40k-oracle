# 项目未完成任务总盘点与执行计划（2026-07-12）

> 依据：11 版迁移计划（2026-07-10）、v2 蓝图 P0-P8 路线图（2026-07-04）、
> 前端 BUILD-PLAN（2026-07-06）、S4-S6 各 spec，以及对当前代码/分支的实地核对。

## ⏸️ 进度 CHECKPOINT（2026-07-12，让"继续"能无损续接）

**✅ T1 + T2 全部完成并已合并 main（PR #16，merge commit `906c25b9`）——11 版迁移正式收官。**
本地 main 与 origin 同步、工作树干净、709 测试绿。四提交：
- `2ad20192` S7 掩体落引擎（save→hit 侧 BS 惩罚 + B6 灵能×掩体）
- `2c3b8e47` S2 跨语实测 + 规则层保底 `RULES_FLOOR_FETCH_K=8000`（25/25）
- `f6c367e8` fp_errata 4 武器格 BSData 裁决（2 补丁 2 假警报）+ 3 新单位别名
- `c4b96cd3` T2 缓存对账（补 Astra 51-156 大缺口 + 14 截断，`MAX_TOKENS=8192`）

**下一步从这里选**（互不依赖，按兴趣挑）：T5 前端 Stage1-2（零后端依赖、正反馈快）
**或** T3 P6 军表系统（补齐 L4 最后一块）。长期滚动 T4（DSL/wiki/基准）；随手 T6 分支清理。

**遗留非阻塞项**（记得但不急）：
- 67 个 verify_warn 页（refine 数字校验疑点，内容在库可检索，`scripts/refine_reconcile.py`
  的 verify_warn 桶可随时拉清单人工比对原文）
- T1-4 外部源观察项（BSData-11e/.cat、Wahapedia 11 版、黑图 11 版、Titan Legions 7 单位缺兵牌）

**关键产物路径**：模拟器 `engines/simulator/`；检索 `app.py`（规则层保底段）；
数据补丁 `db_compile/fp_errata.py`+`fp_errata_patches.json`；缓存工具 `scripts/refine_*.py`、
`scripts/s2_crosslingual_probe.py`；报告 `docs/superpowers/specs/2026-07-12-*.md`；
索引 `local_vector_store/`（5652 chunks，gitignore）；DB `db/wh40k.sqlite`（gitignore，`python -m db_compile fp-errata` 复现补丁）。

## 现状快照（T1+T2 后）

- 语料：61 本 PDF 入库，**5652 chunks**（Astra 补齐后），edition/layer 元数据齐全
- 数值真源：`db/wh40k.sqlite` 已 11 版化（属性一致率 99.85%），fp_errata 补丁层（含武器补丁）挂 restore
- 基准：11 版 gold v3 = **99.0 零硬错**（唯一 ⚠️ #42 多武器列举题）
- 模拟器：**掩体/保存骰已 11 版化**（S7 完成）；fight_order / USR B 类 / PSYCHIC 均 11 版
- 检索：中文查询 25/25 命中 11 版规则层（S2 修复后）
- 测试：**709 绿**；main 干净同步（PR #16 已并）

> **以下 T1/T2 明细已全部完成，保留作实施记录**；未完成的是 T3–T6。

---

## T1 · 11 版迁移收尾（正确性优先，本周第一波）

### 1. 模拟器 11 版核心机制对齐 ★最高优先级（1-2 天）

S6 收官时确认的 11 版大改尚未进引擎，实地核对 `engines/simulator/sequence.py:60-75` 证实：

- **掩体迁到 BS 侧**：现实现是十版"护甲 +1（Sv≤3+ 对 AP0 不享受）"；11 版 13.08 =
  恶化攻击方 BS 1。迁移时需联动：
  - `abilities.py` Stealth（24.33）现走 `save+cover` 通道，掩体改 BS 侧后通道要跟着搬
  - 间接火力（24.19+10.07）固定阈值命中与 BS 无关——掩体改 BS 侧后对 indirect 是否失效需按原文裁定
  - **勘误 B6 交互**：PSYCHIC（24.29）忽略不利命中修正 → 掩体建到 BS 侧后，灵能武器
    RAW 可无视掩体（含隐蔽）——需 `ignore_hit_mods` 覆盖到位并加测试
- **保存骰双重对照审计**：11 版特殊保护并入单次保存骰同时对照 InSv 与 AP 后 Sv（不再择一）。
  现实现 `effective_save` 取更优阈值——静态场景下数学等价，但需逐条核对重骰/
  "护甲保存骰"触发类效果是否产生语义差异，等价则落注释披露，不等价则改
- **S6 其余大改影响面清单**（逐条判"已建/需改/披露未建模"）：接战范围水平 1"→2"、
  近战阶段重构（跟进/重整全阶段步骤、掩杀战斗）、fly 翱翔制、hazardous 重做、
  fire overwatch 重做、Overrun Fights、SURGING
- 验收：701 测试绿 + 新增机制测试；基准 v3 重跑不低于 99.0；CLI/面板披露措辞同步

### 2. S2 中英跨语检索实测（0.5-1 天）——迁移计划唯一显式 ⏳

- 设计 20-30 条中文规则查询（覆盖 11 版新术语：surging/engaged/掩杀/翱翔…），
  验证命中是否落在 11 版英文核心规则正确条款（BM25 必失配，看 bge-m3 跨语 + 别名扩展够不够）
- 不够 → 触发预案：11 版核心规则跑一版中文 refine 入库
- 验收：实测报告落 specs/，命中率量化；若跑中文 refine 则 --rebuild 后基准回归

### 3. 小额收尾包（合计半天）

- [ ] fp_errata 的 4 个疑似武器单格 review_needed 人工裁定（回 Faction Pack 原文对照）
- [ ] 3 个 11 版新单位（Bigboss / Bannernob / Big Mek Dakkarig）中文别名：黑图书馆
      未更新前先手工补 community_aliases，标记来源待替换
- [ ] **更新 CLAUDE.md「当前重点」段落**：LLM PDF 重构描述已过时（refine 缓存已大面积
      存在、S3 已收口），改为指向本计划

### 4. 外部源观察项（不排期，见到信号再动）

- BSData **wh40k-11e** 仓库 .cat 落地 → 走 crosscheck 接入（复用 english-authority 流程）
- Wahapedia 正式挂 11 版 → 复核 fp_errata 补丁层是否可退役（带 from 守卫，冲突会自报）
- **Adeptus Titanicus（titan-legions）数据表缺失**：7 个 MFM-only 单位在库里无兵牌，
  新阵营无十版 codex 可垫底——等外部源，或从 Faction Pack PDF 手工建表（工作量另估）
- 黑图书馆出 11 版 gameId → 刷新中文别名桥

## T2 · 数据完整性（0.5-1 天，可与 T1 并行）

### 5. refine 缓存补齐与全量对账

已知缺口（分散在三次会话发现，从未统一清点）：

- Core Rules 缺 12 页（3/6-7/26-27/44/59-61/75-77）+ page_019 提取残缺
- S4 工作单发现的 5 处精炼缓存截断（需回原 PDF 重跑对应页）
- Astra Militarum 曾只 refine 51/156 页（2026-07-09 记录，**先核实现状再动手**）

做法：写一次性对账脚本（每本 PDF 物理页数 vs `data_refined/<书>/` 缓存页数 + 空/截断页
检测），产出差额清单 → 只对缺口页跑 refine → 增量 ingest。验收：对账脚本零差额，
落 devlog。

## T3 · 蓝图 P6 军表系统（未开工，2-5 天一期）

### 6. engines/roster/ 三件套 + 面板

- 验表（点数合法性/编制约束，点数走 sqlite+MFM 真源）
- 点评档（配置合理性、与模拟器联动的强度评估）
- 实时重算（改一行军表即时重算点数）
- 军表实验室 Streamlit 面板 + 会话上下文（蓝图既定：服务端内存 session）
- 前置已就位：P4/P5 模拟器、calc_points、实体解析器。建议开工前照 P4/P5 惯例先写 spec

## T4 · 蓝图 P7 滚动录入（长期，可穿插做）

### 7. 阵营技能 DSL 逐条编码

- P5 只 surface 名字（宁漏不错裁决）；P7 把阵营军队规则/分队/CP 战略逐条译成 Effect DSL
- 先试点 1-2 个阵营（建议钛帝国——wiki/语料最全）把「录入→测试→dsl_status 标记」流程
  定型，再滚动其余阵营；每条带 encoded/partial/not_modeled 诚实标记

### 8. wiki 全量编译

- `wiki/factions/` 现仅 钛帝国、吞世者 2 个阵营（core-rules 64 页已 11 版化收官）
- 剩余阵营滚动编译；`wiki/review_needed.md` 未配对实体清单人工校对
- 顺手项：4 条存量断链（gnhf 无源例外）修掉或正式豁免

### 9. 基准持续扩充

- #42 多武器列举题型（现唯一 ⚠️）：要么改判分容忍口径，要么扩成专项题组
- 随 P6/P7 落地补军表类、阵营技能类题目

## T5 · 蓝图 P8 网站化（BUILD-PLAN Stage 1-5，可独立推进）

### 10. Stage 1+2：设计系统抽取 + Next.js 聊天页静态版（2-3 天，零后端依赖）

- tailwind tokens（Wahapedia 色板/切角/盾形 clip-path）+ 六个基础组件
- 字体上线红线：Bahnschrift → 自托管 Barlow Condensed/Oswald + Noto Sans SC
- E1-E9 组件化，炮击战斗服 fixture 做永久回归样例；390/768/1280 三档验收

### 11. Stage 3：结构化回答契约 + FastAPI（1-2 天）

- `agent/loop.py` 之上加 response_formatter（工具本就返回 dict，小活）
- `POST /chat`（SSE 先流 trace 再逐槽位）+ `GET /wiki/...`

### 12. Stage 4：三页签

- **图鉴**：无依赖，可立即做
- **模拟器**：P4/P5 已完成——**依赖已解锁**，把「阶段漏斗」可视化复活
- **军表实验室**：等 T3（P6）

### 13. Stage 5：部署

- key 只在服务端 env、限流+CORS、鹰徽自绘更抽象版、不提供原文/库整体下载

## T6 · 仓库卫生（随手，<0.5 天）

### 14. 分支清理

- `overnight-chain` 落后 main 且其成果已全并——确认无未合并提交后删除（本地+远端）
- 已并 main 的 feat/fix 分支（edition11-s3/s5/s6、entity-resolution-v3、review-2026-07-10、
  fp-errata 两支、llm-pdf-refine）批量删
- 3 个 `gnhf/objective-*` 旧链：逐支 `git log main..` 核查有无孤儿提交再决定去留

---

## 建议执行顺序

| 波次 | 内容 | 理由 |
|---|---|---|
| 第一波（本周） | T1-1 模拟器 11 版对齐 → T1-2 S2 跨语实测 → T1-3 小额收尾 + T2 refine 对账 | 正确性缺口优先；做完即可宣布 11 版迁移**正式收官** |
| 第二波 | T5 Stage1-2 前端 **或** T3 P6 军表（二选一按状态挑，互不依赖） | 前端零后端依赖、正反馈快（ADHD 友好）；军表补齐 L4 最后一块 |
| 第三波 | T5 Stage3-4 接后端 + 模拟器/图鉴页签；若第二波选了前端则此处插 T3 | Stage4 军表页签等 P6 |
| 长期滚动 | T4（DSL/wiki/基准）+ T1-4 外部源观察 | 无死线，穿插在各波间隙 |
| 随手 | T6 分支清理 | 任意一次会话顺手做 |

**单点起步建议**：T1-1 的掩体迁移——它是当前唯一已确认「会按旧版规则给错误结论」的
在产缺口（模拟器面板已默认可用），且带着 B6 灵能交互的明确规则依据，范围清晰。
