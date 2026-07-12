# T2 refine 缓存全量对账与补齐（11 版迁移收尾）

> 2026-07-12。remaining-tasks 计划 T2：三次会话零散发现的 refine 缓存缺口从未统一清点，
> 写对账脚本查真实缺口 → 只补缺口页 → 增量 ingest。验收：对账零差额、内容可检索。

## 方法

- `scripts/refine_reconcile.py`（纯审计、不联网）：每本 PDF 物理页 vs `data_refined/<书>/`
  缓存，逐页分七类——ok / skipped（源 <20 字合法跳过）/ missing / fallback / stale / truncated
  （缓存 md < 源文本 30% 且源 >300 字）/ verify_warn（数字校验未过）。
  缺口 = missing+fallback+stale；疑点 = truncated+verify_warn。
- `scripts/refine_gaps.py`：读对账结果，missing 页直接 refine、truncated 页删缓存后强制重跑；
  lang 从各书已缓存页的 `prompt_version` 自动推断（v1-en→en / v1→zh）。

## 首轮对账发现（"先核实现状"的回报）

| 类别 | 数量 | 定位 |
|---|---|---|
| missing | 105 | **几乎全是 Faction Pack Astra Militarum 第 51-156 页**——该 11 版 Faction Pack 2/3 内容从未 refine（当年批量在第 50 页中断），`load_refined_book` 逐页 glob 只加载 1-50 页，**后半兵牌/计谋从未进检索索引**（不回退原文，是静默漏页） |
| truncated | 14 | 散在 9 本；含 Core Rules p19（源 2655 字→缓存仅 59 字，截断在句中）、p42 等 |
| fallback / stale | 0 | 无失败重跑、无内容漂移 |
| verify_warn | 67 | 数字校验未过的既有质量标记，散在多本（内容在，非覆盖缺口）——**另列质量核查项，不在本次补齐范围** |

**推翻了记忆里的两条外推**：① "Core Rules 缺 12 页(3/6-7/26-27…)" 实为源 <20 字的**合法空白/图页跳过**，
非缺口（对账正确归为 skipped）；② 唯一被点名的 "page_019 提取残缺" 证实是**截断**（59/2655 字）。

## 根因与修复

**截断根因**：refine 用的 `deepseek-v4-pro` 是**推理模型**，`max_tokens` 同时覆盖 reasoning +
正文；`max_tokens=4096` 对推理开销大的长规则页会把正文截断（finish_reason=length）。
→ 提到 `MAX_TOKENS=8192`（llm_refine.py）。样张验证：Core Rules p19 重跑后 **2655 字源→2698 字**、
零数字超出、结构完整。

**补齐执行**（`scripts/refine_gaps.py`）：Astra 51-156（105 页）+ 14 截断页强制重跑。
结果 **done=119 / failed=0 / verify_warn=0**（无失败、无造数）。

## 增量 ingest 与验证

- `ingest.py`（增量，非 rebuild）检测到 10 本指纹变化的书，`delete_stale_chunks` 先删旧
  1147 chunk（覆盖 10 个重处理来源）再合并 1228 新 chunk——**无重复**。
- 索引总 chunk **5571 → 5652**；Astra Militarum **~50 页 → 152 chunk 覆盖 1-155 页**。
- 端到端检索验证：Astra 第 127 页内容（Malcador Defender 坦克兵牌，属原缺失后半）经生产
  `hybrid_retrieve` 成功召回（命中 p127/p123）——**缺口内容确已可检索**。

## 验收

- [x] 复跑对账：**missing 0 / fallback 0 / stale 0 / truncated 0**（零差额）。
- [x] 补齐 119 页，0 失败 0 造数。
- [x] 增量 ingest 无重复（1147 删 + 1228 加 = 净 +81，总 5652）。
- [x] 缺口内容生产路径可检索（Astra 后半兵牌）。
- [x] 709 测试绿。
- 遗留（非本次范围）：67 verify_warn 数字校验疑点，作独立质量核查项——内容在库、
  可检索，仅数字需人工比对原文（`scripts/refine_reconcile.py` 的 verify_warn 桶可随时复查）。

## 工具（可复跑）

- `scripts/refine_reconcile.py [out.json]`：全库对账，产差额清单。
- `scripts/refine_gaps.py <reconcile.json>`：按对账补齐 missing/truncated（需 DEEPSEEK_API_KEY）。
