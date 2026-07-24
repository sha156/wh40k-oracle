# refine 造数修复：verify_warn 67→37，30 页虚构兵牌数值清零（2026-07-24）

> 承接 `2026-07-12-t2-refine-cache-reconcile.md`。T2 对账把 verify_warn 桶列为
> "疑点应人工核"但未逐页核。本轮核实：verify_warn 不是格式噪声，而是精准逮到了
> `llm_refine` 的**系统性造数**——在图片型/被拆分的兵牌页上，refine LLM 凭 40K
> 记忆虚构了原文根本没有的属性/武器/技能数值。

## 根因

`refine_prompt.py` 的兵牌模板给了完整的属性表 + 武器表列头，禁令虽写了"禁止添加原文
没有的内容"，但在**提取文本只剩单位名+编制+关键词**（属性/武器数值是图片，或在被拆分
的对页另一半）的页面上，LLM 照模板把数值从记忆里填了进去。`<!--CONT-->` 续页尤其高发。

`verify_numbers`（md 数字多重集 ⊄ 源文本）正是为逮这个设计的，它把 67 页标了
`verify_ok=False`。

## 对账分类（67 页）

用"纯造数字" = md 里出现但源文本 **0 次**的 token 作判据：

| 类别 | 页数 | 判据 | 处理 |
|---|---|---|---|
| 🔴 真造数 | **30** | 纯造数字 ≥1 | 硬化 prompt 后重跑，造数全部 0→清零 |
| ✅ 纯结构性 | 37 | 纯造数字 =0 | 不动：每个数字源里都有，仅 markdown 重排（列表序号/`[连击1]` 武器技能标/表分隔）使计数偏移 |

> 注：初判用"纯造≥2 且含表格"逮到 27 页；复核发现该阈值过严，漏了 3 页无表格但
> 造了技能/属性数值的（Necrons p50 虚构 `Invulnerable Save: 4+` + `6"` 光环；
> 太空死灵 p49 属性 OC 被写成 2 实为 1；吞世者 p32 虚构了第二张 `135分` 兵牌）。
> 收严为"纯造≥1"后全部纳入。纯造=0 的 37 页复核确认零漏网。

## 修复

1. **`refine_prompt.py` 加最高铁律**（中英双份，`PROMPT_VERSION` v1→v2、
   `PROMPT_VERSION_EN` v1-en→v2-en，使全部页缓存失效）：源文本无 M/T/SV/... 数值时，
   兵牌**只输出名字/编制/关键词，绝不从记忆补数值/技能描述**，宁可结构不完整。
2. **`scripts/refine_pages_fabricated.py`**：定向重跑造数页（自 `verify_ok=False` +
   纯造≥1 判据自动圈定），逐页读现有 `meta.prompt_version` 决定用 CN/EN 硬化 prompt
   （EN 官方 FP 与 CJK 名的"帝国骑士英文"都对），走同一 deepseek-v4-pro + 代理通道，
   重跑后 `verify_numbers` 复验。
3. **`scripts/verify_warn_triage.py`**：只读分诊助手，逐 token 给源计数 vs md 计数 +
   所在行，供人工核。

样张先行（圣血天使 p28 / Orks p31）确认硬化后虚构表消失、真实名字/编制保留，再批量。

## 验收

- verify_warn：**67 → 37**，剩余 37 页复核纯造数字 = 0（确定无害）
- 30 页逐页 `verify_numbers` 造数 count 全部 → 0
- 增量 ingest（refined_fingerprint 变更自动触发相关书重嵌）
- 基准 gold v3 回归：见下方运行记录
- pytest：无测试 pin `PROMPT_VERSION` 常量（`test_llm_refine.py` 的 `"v1"` 是自含
  fixture，测缓存逻辑不受版本 bump 影响）

## 遗留

- 37 页纯结构性 verify_warn 是 `verify_numbers` 的已知误报形态（markdown 重排使某数字
  计数超源），非数据错误，可长期挂着或后续给 `verify_numbers` 加"结构性数字白名单"降噪。
- 数值真源仍是 `db/wh40k.sqlite` + `wiki_engine/from_db.py`（官网一致）；本轮修的是
  **检索层**的 refined 文本不再把虚构数值当"有出处的事实"喂回答 LLM。
