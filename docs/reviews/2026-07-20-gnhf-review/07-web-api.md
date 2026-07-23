# 模块 7 审查报告：web_api/ FastAPI 后端 + 契约镜像

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：`web_api/` 全部 11 个模块（main / contract / codex / entity_card / formatter /
  richtext / roster / simulate / structurer / trace），以及与前端契约真源
  `web/src/lib/{answer,sim,roster,codex}.ts` 的逐字段镜像一致性。
- 方法：真读两侧契约文件逐字段 diff；对 simulate/roster 用 `.venv` + 真实
  `db/wh40k.sqlite`（只读）机械复现：`sanitize_options` 边界、`run_simulation`
  内存/耗时随入参扩张、wiki 路径守卫前缀逻辑、SQL 占位符审计。
- 结论先行：**1 个 HIGH（CONFIRMED，已修复）**、2 个 MEDIUM、1 个 LOW。
  既往修复（并发信号量 503 / n 钳制 / `_as_bool` 收严）全部在位且未被绕过；
  SQL 注入面与契约镜像逐字段核无误。

---

## HIGH-1（CONFIRMED，已修复）：`n` 钳制形同虚设——loadout 武器数 / models / 军表单位数无上限，构成算力+内存 DoS

- **位置**：`web_api/simulate.py:39-45, 94-110`（`_as_pos_int` / `sanitize_options`）；
  `web_api/contract.py:237,240,248`（`RosterUnitIn.models`、`loadout`、`RosterIn.units`）；
  `web_api/roster.py:19-37`（`_to_loadout`）
- **证据**（修复前）：`_as_pos_int` 只判 `>0` 无上限；`attacker_models`/`defender_models`/
  `damage_reduction` 直接透传；`_as_loadout`/`_to_loadout` 武器数量与行数均无上限；
  `RosterUnitIn.models` 只有 `ge=1`；`RosterIn.units` 无 `max_length`。
- **失效场景**：`sanitize_options` 的注释明说 `n` 上限是「防把后端当算力用」，但模拟核心
  numpy 数组宽度真正由「武器数 × 每模型攻击数」决定（`sequence.py:231`
  `sample_dice(w.attacks, rng, (n, count))`），Blast 还按守方模型数放大
  （`atk += blast_x * (target.models // 5)`）。机械复现：
  - `sanitize_options({"loadout": [["bolter", 10**9]]})` → 原样通过；
  - `count=800000` 单请求实测 **34.8 秒**（n 已钳到最小）；`count=10^9` 需 TB 级
    numpy 分配 → 进程 OOM；
  - `defender_models=10^9` 是独立杠杆（Blast 放大），无需大 loadout 即 OOM；
  - 军表侧同源叠加：`/roster/critique` 逐单位跑蒙特卡洛且与 `/simulate` 共用
    4 槽信号量——4 个慢请求即令模拟器与点评页签整体不可用。
- **修法（已实施）**：`_as_pos_int` 加 `hi` 参数统一钳制；新增共用常量
  `MODELS_MAX=100` / `WEAPON_COUNT_MAX=400` / `LOADOUT_ITEMS_MAX=40` /
  `_DMG_REDUCTION_MAX=6`（`simulate.py`，roster 侧 import 复用）。超上限视同非法值
  丢弃/整体拒收（与 ≤0 同待遇），**不静默钳**（钳了会悄悄改变模拟语义）；seed 是
  标量不构成 DoS 面，保持不封顶。契约层 `RosterUnitIn.models` 加 `le=100`、
  `loadout` 加 `max_length=40`、`RosterIn.units` 加 `max_length=60`（422 拒收）。
  `_to_loadout` 另防「拆行绕过单件上限」（合并求和后复查）。
- **测试**：`tests/test_web_api_stage4_sim.py::test_sanitize_caps_dos_levers`、
  `tests/test_web_api_roster.py::test_to_loadout_caps_dos_levers` /
  `test_roster_contract_caps`（均一正一负成对）。

## MEDIUM-1（CONFIRMED，仅记录）：`_SESSIONS` 会话存储无界增长，且写入后从不被消费（内存泄漏 + 死功能）

- **位置**：`web_api/main.py:49, 91-94`
- **失效场景**：① `session_id` 由客户端任意提供，`_SESSIONS` 无历史长度上限、无会话数
  上限、无 TTL——变换 `session_id` 反复请求 `/chat` 即令后端内存无限增长；
  ② `loop.run(req.question)` 调用时不传 session/历史（`AgentLoop.run(self, user_input,
  session=None)`），累积的历史从不回喂 LLM——多轮上下文被存储但永不使用，会话支持是假象。
- **建议修法**：若暂不实现多轮，删掉 `_SESSIONS` 写入；若保留，加 LRU 上限 + 历史截断 +
  空闲 TTL，并把 hist 真正传入 `loop.run`。

## MEDIUM-2（CONFIRMED，仅记录）：`/wiki/{path}` 路径守卫用 `startswith` 前缀判断，可越到同级 `wiki*` 目录

- **位置**：`web_api/main.py:280-282`
- **失效场景**：`startswith` 是字符串前缀，不识别路径分隔符边界。
  `path="../wiki_compile/foo"` 解析成 `D:\Project\py\RAG\wiki_compile\foo.md`，字符串
  以 `D:\Project\py\RAG\wiki` 开头 → 通过守卫（已机械复现）。仓库根下确有同级
  `wiki_compile`、`wiki_engine` 目录，其中任意 `.md` 可被读出。父目录逃逸因不以
  `wiki` 开头被正确拦截、且仅限 `.md`，实际危害有限，但守卫存在真实缺陷。
- **建议修法**：`target.resolve().relative_to(wiki_root.resolve())`（ValueError 即拒），
  或 `os.path.commonpath`，而非 `startswith`。

## LOW-1（PLAUSIBLE，仅记录）：`SimReportOut.distribution/funnel/efficiency` 为 `Dict[str, Any]`，不校验前端断言的结构化形状

- **位置**：`web_api/contract.py:199-201` vs `web/src/lib/sim.ts:79-96`
- **说明**：TS 侧是结构化 `SimDistribution{p10,p50,p90,histogram,damage}`，后端镜像放宽成
  `Dict[str,Any]` 原样转发；引擎某分支返回空 `{}` 时前端读 `.p50` 得 undefined。
  属健壮性提示，非缺陷。

---

## 已核无误项（核法附后）

| 项 | 核法 | 结论 |
|---|---|---|
| SQL 注入 | Grep 全部 `execute`；8 处均参数化 `?`，无拼接 | 无注入面 |
| `n` 钳制回归 | `{"n":999999}→20000`、`{"n":1}→100`、`{"n":-5}→None` 实测 | 修复在位 |
| `_as_bool` 收严 | `"false"/"False"/"0"→False`、`"true"→True` 实测 | 修复在位 |
| 并发信号量 503 | `/simulate` 与 `/roster/critique` 共用 `_SIM_SEMAPHORE`，`acquire(blocking=False)` 失败即 503，finally 释放 | 无泄漏无绕过 |
| 契约镜像 | EntityCard/Answer/Sim*/Roster* 逐字段 diff（字段名、驼峰 alias、Optional、Literal、嵌套 reverse） | 未发现漂移 |
| CORS | env 白名单、`allow_credentials=False`、仅 GET/POST | 配置安全 |
| 错误响应泄漏 | HTTPException detail 均通用中文；装配层 fail-closed 不外抛栈 | 不泄内部路径 |
| richtext XSS 面 | `web/src` 全域无 `dangerouslySetInnerHTML`；LLM 输出经 `to_richtext` 结构化 token 由 React 文本节点渲染；DB 字段 `_strip_html` | 无注入 |
| codex/entity_card None 处理 | ds None→404；JSON 解析均 try/except；zh↔en 降级留英文 | 健壮 |
| lang 参数校验 | 非 zh/en → 422 | 已校验 |

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 1 | 已修复 + 成对测试 |
| MEDIUM | 2 | 记录在案 |
| LOW | 1 | 记录在案 |

## 遗留建议

1. `/chat` 端点跑完整 agent loop 同步阻塞且无信号量/超时保护——与 `_SESSIONS` 泄漏
   叠加时值得后续加请求级超时与并发闸。
2. MEDIUM-2 的 `relative_to` 改法一行可落，建议与 MEDIUM-1 一起在后续小 PR 处理。
3. 前端若用 markdown 库渲染 `/wiki` 返回的原始 markdown，需确认该库默认禁用原始 HTML。
