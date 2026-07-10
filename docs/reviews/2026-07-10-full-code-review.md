# 全库代码审查报告（2026-07-10）

- 基线：`overnight-chain` @ bd23e219（= main PR #8 合并内容），**519 测试全绿**（43.9s）
- 方法：6 个并行审查代理（5 模块域 + 1 全库安全），CRITICAL/HIGH 由主会话逐条机械核实（标 ✅ 的为已亲手复现/读码确认）
- 结论：**3 CRITICAL + 18 HIGH + ~17 MEDIUM + ~7 LOW**。所有问题均未被现有 519 个测试捕获——测试盲区本身是系统性问题（ingest.py / app.py 零测试）

---

## 核实中对代理结论的修正

1. **simulator 代理声称 `cli.py -n 0` 直接崩溃 → 不准确**。实测 CLI 路径不崩：`cli.py:124` 的 `if v not in (None, False)` 把 `n=0` 静默过滤掉，回退默认 8000 跑完并输出"正常"结果——**静默改写比崩溃更糟**。真正崩溃的是 agent 工具路径（`{"n": 0}` → `zero-size array` numpy 裸错），已实测复现。
2. **新发现（代理漏报）**：`cli.py:124` 与 `ui/simulator_panel.py:112` 是**同一个 `0 == False` 陷阱的两个实例**——CLI 的 `--seed 0`、`-n 0`、`--fnp 0` 等一切合法 0 值参数都会被静默丢弃回退默认值。
3. `app.py:148-151` DB_ALIASES 静默吞（代理评 CRITICAL）：注释写明"DB 缺失/无表时静默退化"是**有意设计**，但实现捕获了 `Exception` 全集且无任何日志——设计意图只覆盖"缺库"，实现却把所有 bug 一起吞了。降为 HIGH（顶格），修复必要性不变。
4. `pair_llm.py` 裸调 LLM（代理评 CRITICAL）：崩溃真实存在，但书级缓存先落盘缓解了重跑代价，降为 HIGH（顶格）。

---

## CRITICAL

### C1 ✅ PDF 引用页码系统性错一页（off-by-one）
`ingest.py:160-173`（load_pdf）＋ `app.py` 展示侧
PyMuPDFLoader 的 `metadata["page"]` 是 **0 起始**，直传路径从未 +1；而 `llm_refine.py:41` 明确写了 `"page": i + 1`。两条入库路径页码语义不一致，48/49 本未走 refined 管线的书，回答里"第 X 页"全部比实际少 1。**这是"必须引用来源"这一核心承诺的正确性基础**。
修复：`load_pdf` 里 `doc.metadata["page"] += 1`，改后需 `--rebuild` 或迁移旧索引。

---

## HIGH（18 条）

### RAG 主流水线（app.py / ingest.py / llm_refine.py / md_chunker.py）

- **H1 ✅ DB_ALIASES 加载失败静默吞全部异常**（`app.py:148-151`）：1633 条别名扩展可因任意 bug 悄悄失效，无日志无 UI 提示——与 flashrank 事故同反模式。修复：捕获具体异常 + 打日志 + UI 侧比照 `reranker_warning`。
- **H2 ✅ 书目过滤时 `fetch_k` 未设**（`app.py:328-335`）：langchain FAISS 带 filter 检索时先在**全库**取 `fetch_k`（默认 20）个再过滤，小于 `FAISS_TOP_K=30`。冷门书过滤检索可能剩 0~2 条。修复：`search_kwargs["fetch_k"] = max(FAISS_TOP_K*5, 200)`。
- **H3 增量入库无删除机制**（`ingest.py:370-394`）：文件变化重入库时旧 chunk 不删，新旧并存互相矛盾。修复：merge 前按 source 找旧 id 调 `delete()`。
- **H4 空 refined 页文件被误判"已完成"**（`md_chunker.py:81-131` + `ingest.py:313-320`）：`chunk_markdown` 返回 `[]` 而非 `None`，既不回退 PDF 抽取又写入 processed_log，该书 0 chunk 永久跳过。修复：空结果也返回 `None` 触发回退。
- **H5 `_split_oversize` 无 `###` 子标题时不切分**（`md_chunker.py:19-31`）：纯文字长章节可合并成上万字符巨型 chunk，嵌入被截断无告警。修复：无锚点时按字符数硬切。
- **H6 `st.cache_resource` 与"刷新页面"提示矛盾**（`app.py:239,282,562-564`）：缓存跨会话存活到进程死亡，按 UI 提示刷新页面拿到的还是旧索引。修复：提示改"重启服务"或加 `.clear()` 按钮。
- **H7 `--chinese-only` 把 fallback 页计入覆盖率**（`llm_refine.py:136-156`）：失败回退页永不重试。修复：覆盖率统计排除 `fallback=True` 页。
- **H8 ✅ TLS 证书校验全进程禁用**（`ingest.py:42-56`，安全）：monkeypatch `requests.Session.request` 强制 `verify=False`，模型下载全程暴露于 MITM（本机 hosts 曾被劫持）。修复：改为信任 Clash 根证书 / 限定 hf-mirror.com 单 host。

### simulator / UI / CLI

- **H9 ✅ `n<=0` 未校验**（`sequence.py:285` 等）：agent 工具路径 `{"n":0}` → numpy 裸错 JSON；`{"n":-5}` → `negative dimensions`。已实测复现。修复：`simulate` 入口 `if n <= 0: raise ValueError(可读中文提示)`。
- **H10 ✅ `0 == False` 参数过滤陷阱 ×2**（`ui/simulator_panel.py:112`、`cli.py:124`）：seed=0 / n=0 等合法 0 值被 `v not in (None, False)` 静默丢弃回退默认——UI 显示种子 0 实跑 1234，可复现性被静默破坏。修复：改 `if v is not None and v is not False`。
- **H11 ✅ `_parse_loadout` 未捕获 `ValueError`**（`cli.py:16-27`，被 UI 复用）：`"Shoota:"`/`"Shoota:abc"` → 裸 traceback；UI 侧异常发生在 `simulate_combat` try/except **之外**，整个面板崩溃。修复：解析失败返回可辨识错误走 `st.error` 分支。

### wiki_engine / wiki_compile

- **H12 ✅ `pair_llm.py:63-66` LLM 裸调无重试**：一次限流/超时让整条 pair 命令崩溃，本次精确匹配结果全部不落盘；持久性失败会卡死后续所有书。修复：比照 `synthesize.py` 加重试 + 单书失败隔离继续。
- **H13 canonical 同名条目 dict 静默覆盖**（`pair.py:50-51`）：跨阵营同名单位 last-write-wins，错配阵营或误判 unmatched。同模式亦在 `terms.py:47`、`crosslinks.py:343`。修复：`Dict[str, List[...]]` + faction 消歧。
- **H14 crosslinks 自引用防护按名字不按路径**（`crosslinks.py:274-292`）：terms.json 全局别名可生成指向页面自身的 wikilink。修复：排除"目标路径 == 当前页路径"。
- **H15 lint 扫描自己生成的 lint-report.md**（`lint.py:29-47`）：断链报告里的 `[[...]]` 字样被下次 lint 当断链，假阳性永久自我复现，`errors>0` 使 CI 门禁永远无法归零。修复：复用 `scan_wiki_pages` 的 skip_names 排除集。
- **H16 synthesize 重跑静默覆盖人工编辑**（`synthesize.py:530-561`）：缓存失效/prompt 升级后无条件 `write_text`，Obsidian 里的人工修正无声丢失。修复：内容哈希检测"已被人工改过"则跳过并报冲突。

### db_compile / agent / qa_bench

- **H17 ✅ crosscheck `GROUP BY u.name_en` 裸列 + 无 faction 维度**（`crosscheck.py:84-87`）：SQLite 裸列取值未定义；跨阵营同名单位被折叠，另一条永远不进比对池——交叉校验假阴性。修复：`GROUP BY name_en, faction_id` + 显式聚合。
- **H18 ✅ qa_bench 机械判分跨字段拼凑假阳性**（`qa_bench.py:470-499`）：多值字段各自独立命中即判对，不要求同一武器记录。已实测：gold(S=5,AP=-1) vs 答案两把武器 (5,-2)/(10,-1) → 判 ✅。**直接影响 99.0 基准分可信度**，stat/weapon 类题需重跑核实。修复：按记录整体匹配。

另 3 条 HIGH 从属上述模块：BSData `.cat` 解析失败静默跳过无计数（`crosscheck.py:62-77`）、MFM `check_points` 对同阵营重名单位 dict 覆盖漏检（`mfm.py:219-226`，与 `apply_points` 已修的坑不对称）、中文别名同名碰撞静默覆盖且 matched 虚计（`aliases.py:44-117`）；以及 `llm_client.py:30-43` 工具参数提示表缺 `judge_fight_order`/`simulate_combat` 关键字段致两工具实际难被 LLM 正确调用、`fetch_blacklibrary_details.py:57-68` 三连吞异常无日志。

---

## MEDIUM（摘要，~17 条）

| 位置 | 问题 |
|---|---|
| `blacklibrary.py:30-61` | 抓到 total 却不对账；空 data 一律当正常翻页结束 |
| `build.py:74-99, 271-359` | CSV 缺列处理不一致（硬崩 vs 跳过）；建库先删旧库无原子替换，中途崩溃留残缺 db |
| `downloads.py:90-172` | 渲染成功但结果为空（反爬页）会被判成"全部下架" |
| `agent/tools.py:142-156` | `unit_list` 传字符串被逐字符拆解，返回 `found: True` 的胡乱查询 |
| `agent/loop.py:125-143` | final 步骤 content 为空仍算成功（degraded=False） |
| `agent/loop.py:149-167` | 未知工具可重试、工具异常直接放弃降级——恢复策略不一致（有测试锁定，属设计取舍） |
| `agent/tools.py:26-35` | 无锁单例，qa_bench 6 线程并发首调重复构造 |
| `archive_old_pdfs.py:119-151` | 4 位数字版本号伪造成年份跨格式比较，"0308">"0115" 纯属巧合（假归档事故同族风险；当前 data/ 全为 8 位日期暂未触发） |
| `profile.py:172` | `resolved_models or 1` 把显式 0 静默改 1，与 sequence.py"不打幽灵模型"原则冲突 |
| `abilities.py:68` + `context.py` | 分类器解析出的 `Effect` 对象无任何消费者，"opt-in 开关"实为死代码，用户需手动重敲数值 |
| `sequence.py:152-156` | `target.effects` 只消费 `phase=="hit"`，wound/save 阶段防守 Effect 会被静默丢弃（当前无生产者，架构缺口） |
| `fight_order.py` | "Fights Last" 机制在 data_refined 全部官方源中 0 命中，却以"核心规则"字样背书（E2 抵消逻辑本身与 page_040.md 核对一致） |
| `crosslinks.py:341-346` | 重复实现 terms.json 解析且缺 isinstance 防护，非常规 JSON 崩整个 CLI |
| `build_outputs.py:35-37` | frontmatter 解析失败的页面从所有 lint 规则和索引里静默消失 |
| `ingest_op.py:62` | `pairing.json` 硬编码相对路径；`find_affected_pages`/`cascade_updates` 定义了从未调用，log.md 级联列永远是 `-` |
| `synthesize.py:584` | `except ImportError: return None` 无日志，缺依赖包被误报成"缺 API key" |
| `terms.py:12-33` | `review_needed.md` 人工批注每次重跑被整体覆盖 |
| `.githooks/`（安全） | pre-commit/pre-push 防泄漏钩子从未接入：`git config core.hooksPath .githooks` 一条命令修复 |

## LOW（摘要）

- 全库 `write_text` 非原子写入（关键产物建议临时文件 + `os.replace`）
- `extract.py:84-86` 无前置实体的 `<!--CONT-->` 页静默丢弃
- `mfm.py` 两套重试逻辑参数不一致；`downloads.py` HEAD 失败无聚合统计
- `import_blacklibrary_aliases.py:38-44` dry-run 缺 DB 存在性检查，会凭空建空库文件
- `context.py` `build_context`/`SimContext` 死代码
- `crosscheck.py` ET 解析无实体膨胀防护（数据源为本地 clone，风险低）
- `llm_client.py:264-271` want_json 盲重试放大瞬时故障调用量

## 安全审查通过项

无密钥泄漏（全库 + 99 提交历史 diff 核实）；`.streamlit/secrets.toml`/.env 从未入库但为明文真 key（建议按纪律轮换、二存一）；SQL 全参数化；subprocess 全列表参数无 shell=True；无 eval/exec/pickle；路径拼接均有 slugify/stem 防护；LLM 输出渲染无 unsafe_allow_html。

## 测试覆盖缺口

- `ingest.py`、`app.py` **零测试**（C1/H1/H2/H3 全部藏身于此）
- `update.py`、`blacklibrary.py`、`schema.py`、`community_aliases.py` 无测试
- `crosscheck.py` 只测纯函数，两条 HIGH 所在的读库/读文件函数未覆盖
- `_options_from_inputs`（seed=0 bug 所在）无测试
- 建议补：别名碰撞、同阵营重名、4 位版本号混格式、"长正文零 ### 标题"等针对性用例

## 修复优先级建议

- **P0（正确性地基，先修）**：C1 页码、H18 qa_bench 判分（修完重跑 gold 基准验证 99.0）、H1 DB_ALIASES 日志、H2 fetch_k
- **P1（可复现崩溃/静默改写）**：H9 n 校验、H10 两处 0==False、H11 loadout 解析、H12 pair_llm 重试
- **P2（数据管线诚实性）**：H3/H4/H7、H13-H17、db_compile 三条 HIGH、githooks 一条命令
- **P3**：TLS 收窄（H8）、MEDIUM 批量、测试补课
