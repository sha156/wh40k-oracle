# 模块 5 审查报告：检索链与入库管线

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：app.py / ingest.py / llm_refine.py / hf_embeddings_compat.py / agent/
  （loop.py、llm_client.py、tools.py 非 simulate 部分、context.py），及其直接依赖
  db_compile/aliases.py、md_chunker.py 的接口面。
- 方法：全文精读，逐个 except 分支核「吞了什么、有没有留痕」（flashrank 历史
  CRITICAL 同反模式排查）；机械复现脚本 3 个（Fake LLM 复现 Agent 循环歧义短路 /
  只读 unpickle 5652 chunks 核 RRF 去重键碰撞 / 只读 sqlite 量测 get_datasheet
  JSON 尺寸 vs 截断阈值）。未调外网、未写索引与缓存。
- 结论先行：**1 个 HIGH（CONFIRMED，已修复）**、6 个 MEDIUM、6 个 LOW、1 个 INFO。
  检索链主干（FAISS+BM25→RRF→规则层保底）总体健康：BM25 与 FAISS by construction
  同源、规则层保底 fetch_k 覆盖全库、reranker 关闭路径干净、refine 缓存键含 prompt
  版本、代理 env 污染面已收窄。

---

## HIGH-1（CONFIRMED，已修复）：Agent 循环把 ambiguous 当空结果短路降级，消歧路径整条死代码

- **位置**：`agent/loop.py:39-47`（`_EMPTY_CHECKS`）+ `loop.py:196-197`；受害方
  `agent/tools.py:193-211`（get_datasheet 的 candidates_preview）、`tools.py:111-114`
  （get_entity 反问 note）、`agent/llm_client.py:112-116`（提示词重查铁律）。
- **证据**（修复前）：`"get_datasheet": lambda r: not r.get("found")`——ambiguous
  返回也是 found=False，循环在 LLM 看到结果**之前**就 `_fallback` 降级 classic。
  提示词却写着「工具返回 "reason": "ambiguous" 时必须再调一次工具……按阵营从
  candidates 里选一个候选名原样重查」。
- **失效场景**：用户问「Helbrute 的韧性是多少」（同名单位存在于 CSM/WE/EC/TS 四阵营）。
  评审 #25 专门构造的各候选属性预览、提示词重查铁律、get_entity 的「需向用户反问确认」
  note——全部永远不会执行。get_entity / entity_resolver 的歧义分支同理。
- **复现**：Fake LLM + Fake 工具脚本输出 `degraded=True`、get_datasheet 仅被调一次、
  `LLM 是否见到过 ambiguous 工具结果 = False`；`tests/test_agent_loop.py` 原无任何
  ambiguous 用例，矛盾无测试覆盖。
- **修法（已实施）**：`_EMPTY_CHECKS` 判空谓词区分语义——
  `get_datasheet`：`not found and reason != "ambiguous"`；
  `get_entity`：`not found and resolved_via.confidence != "ambiguous"`；
  `entity_resolver`：`not canonical_id and not candidates`。
- **测试**：`tests/test_agent_loop.py::TestAmbiguousIsNotEmpty`（5 条：datasheet
  ambiguous 写回 messages 且重查成功不降级 / 普通查无仍降级（负向）/ entity
  ambiguous 达 LLM / resolver 有候选达 LLM / resolver 无候选仍降级（负向））。

## MEDIUM-1（CONFIRMED，仅记录）：`_render_loop_message` 4000 字符截断，Agent 模式下 rag_search 工具返回仅 38% 可见

- **位置**：`agent/llm_client.py:170-172`
- **失效场景**：循环内 rag_search 8 条 passages 的 JSON 实测 10567 字符，截断后 LLM
  只见前 2-3 条——同一问题走 classic 链能看到完整 8 条。get_datasheet 也有 8% 单位
  （60 抽样中 5 个，max=5509）超阈值，被截掉的恰是 JSON 尾部武器表/点数档位。
  截断有「（已截断）」标记披露非静默，故不评 HIGH。
- **建议修法**：按工具分阈值（rag_search/get_datasheet 提到 12000-16000，deepseek-chat
  64k 上下文足够）；或对 rag_search 只保前 N 条完整 passages。

## MEDIUM-2（CONFIRMED，仅记录）：RRF 去重键前缀 50 字符碰撞，真实索引 5 组不同 chunk 同键

- **位置**：`app.py:240-242`（`_doc_id` = source_page_content[:50]）
- **失效场景**：md_chunker 超长条目拆出 `## 标题` 与 `## 标题（续）` 两 chunk，英文标题
  ≥47 字符时同键。RRF 里 `doc_map[did]` 后写覆盖先写，分数合并虚高、其中一个 chunk
  被静默丢弃。真实索引命中 5 组，含 CUSTODIAN GUARD WITH ADRASITE AND PYRITHITE
  SPEARS（属性表 vs 技能续块）、DEATH COMPANY MARINES WITH BOLTGUNS AND JUMP
  PACKS（属性表 vs 装备续块）——问这几个单位属性题时档案里可能只剩「续」块。
- **建议修法**：去重键改整段内容哈希（md5）或 docstore id；修后把碰撞检查固化成
  pytest（全库同键组数 == 0）。

## MEDIUM-3（CONFIRMED，仅记录）：Agent 工具 validate_roster / critique_roster 仍打桩「未建模，计划于 P6 实现」——P6 已于 2026-07-14 上线

- **位置**：`agent/tools.py:616-621`；对照 `web_api/roster.py`（真实接线）
- **失效场景**：聊天页贴军表问「帮我验一下」→ 得到「未建模，计划于 P6 实现」——系统对
  用户陈述过时假事实（军表页签就在隔壁跑着）。`SessionContext.remember_roster` 因此
  永远无人调用。
- **建议修法**：薄封装 `engines.roster` 或至少改 note 为「请使用军表实验室页签」。

## MEDIUM-4（CONFIRMED，仅记录）：get_datasheet 按 canonical id 查询实际查不到，参数名与 docstring 承诺失真

- **位置**：`agent/tools.py:171-179`；根因 `db_compile/datasheet.py:186-216`
  （find_datasheet 无 `units.id` 直查分支）
- **失效场景**：LLM 按提示词先 entity_resolver 拿 canonical_id 再传 get_datasheet →
  found=False → 命中判空降级。机械验证：`get_datasheet("000000882")` → found=False。
- **建议修法**：find_datasheet 开头加 `WHERE u.id = ?` 直查分支（lookup_datasheet
  已具备，一行接线）。

## MEDIUM-5（PLAUSIBLE，仅记录）：llm_refine 不检查 finish_reason，截断页正常入缓存

- **位置**：`llm_refine.py:102-123`；`llm_refine.py:88-91` 注释自证问题存在
- **失效场景**：长页耗尽 token 预算 → 正文中途截断但非空 → 通过「非空即成功」→
  `verify_numbers` 只查数字超集（截断不引入新数字，恒通过）→ `verify_ok: true` 入缓存。
  T2 曾靠人工对账逮到 14 个截断页；防线仍只有事后对账。
- **建议修法**：检查 `finish_reason == "length"` 即失败进重试/兜底，meta 记录
  finish_reason。

## MEDIUM-6（PLAUSIBLE，仅记录）：ingest.py 未复用 resolve_embed_model，代理抽风即构建失败

- **位置**：`ingest.py:238-241`；对照 `app.py:56-68`（app 侧已修的同一个坑）
- **建议修法**：把 resolve_embed_model 提到 hf_embeddings_compat.py 两处共用。

## LOW（6 条，仅记录）

1. **增量构建不清理已删除/归档 PDF 的旧 chunk**（`ingest.py:316-330`）：归档后旧规则
   继续参与检索直到手动 --rebuild。建议对 processed_log 与现存文件集合的差集执行清理。
2. **llm_refine 缓存键不含 model**（`llm_refine.py:62-72`）：换模型不 bump prompt
   版本时旧缓存被沿用。建议 `is_cached` 加 `meta.model == MODEL`。
3. **app.py 顶层硬导入 flashrank**（`app.py:37`）：为关闭的功能付启动硬依赖。建议惰性导入。
4. **get_datasheet 黑图书馆叠加层裸 `except Exception: pass`**（`tools.py:218-231`）：
   schema 变更/数据损坏也被吞。建议收窄为 OperationalError + 其余打日志。
5. **classify_intent 静默回退默认意图 + OpenAI 客户端未设 timeout**
   （`llm_client.py:256-257, 241-243`）：建议失败打一行 stderr、构造时传 timeout=60。
6. **TERM_ALIASES 损坏静默空表**（`wiki_compile/terms.py:52-65`）：与 DB_ALIASES 的
   告警待遇不一致。建议比照加告警。

INFO：`app.py:81` 注释说规则层「仅 141 个 chunk」，实测 145（无害）。

---

## 已核无误项（核法附后）

| 审查点 | 结论 | 核法 |
|---|---|---|
| BM25 与 FAISS 不同步风险 | 无此风险 | build_bm25 直接从 `vectorstore.docstore._dict` 建索引 by construction 同源；「重载索引」按钮成对 clear 两个 cache_resource |
| 规则层保底 fetch_k 饥饿 | 无误 | 全库 5652 ≤ RULES_FLOOR_FETCH_K=8000，layer=rules 145 条全数可进候选池 |
| refine 缓存 prompt 版本误用 | 无误 | is_cached 严格比对 prompt_version（zh/en 分版），fallback 页不算 cached |
| ingest 环境变量污染 | 无误 | 代理 env 只在 ingest 进程内生效；TLS monkeypatch 以 hostname 精确限定 hf-mirror；llm_refine 的 DeepSeek 走显式 httpx.Client(proxy=...) |
| 增量去重误删 | 无误 | delete_stale_chunks 只删本次成功产出新 chunk 的 source，processed_log 落盘成功后才保存 |
| ingest 对账 | 有 | 成功/失败计数 + 失败清单 + 分层 chunk 统计均打印 |
| USE_RERANKER=False 关闭路径 | 干净 | load_resources 提前 return None；hybrid_retrieve 对 None 直接取 RRF 顺序 |
| st.session_state 并发/重入 | 无误 | 每会话独立；共享 cache_resource 只读查询 |

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 1 | 已修复 + 成对测试 |
| MEDIUM | 6 | 记录在案 |
| LOW | 6 | 记录在案 |

## 遗留建议

1. HIGH-1 修复后建议跑一次 gold 基准，确认 Helbrute 类同名歧义题从「降级 classic」
   变为「候选消歧作答」。
2. MEDIUM-2 修去重键后把碰撞检查固化成 pytest 对账测试。
3. Agent 工具文档与实现已现 3 处漂移（MEDIUM-3/4），建议加轻量一致性冒烟测试。
