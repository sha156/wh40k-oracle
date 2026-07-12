# T5 网站化 进度 CHECKPOINT（2026-07-12）

> 让「继续」能无损续接。BUILD-PLAN：`docs/design/frontend-explorations/BUILD-PLAN.md`；
> Stage 3 设计：`docs/superpowers/specs/2026-07-12-stage3-response-contract-design.md`。

## ✅ 已完成（Stage 1-4 图鉴）

| 阶段 | 内容 | 提交 | PR |
|---|---|---|---|
| Stage 1-2 | 前端设计系统 + 聊天页静态版（Next.js 16/Tailwind 4，E1-E9 组件化） | 30d53537 | #18 已并 |
| Stage 3 后端 | `web_api/` FastAPI——response_formatter 散文→结构化槽位契约 | 56cc8ae1 | #20 已并 |
| Stage 3 前端 | 前端切真调 /chat SSE（渐进渲染闭环） | c5b39467 | #21 待并 |
| Stage 4 图鉴 | `/codex` 阵营→单位→兵牌浏览（复用 Datasheet） | 226f886d | #21 待并 |

**当前分支**：`feat/stage3-frontend-wiring`（含 Stage3 前端 + Stage4 两提交），已推、树干净。
**唯一开着的 PR**：#21（→ main，覆盖 Stage3 闭环 + Stage4 图鉴）。**全库 724 测试绿。**

## 关键设计（续做前必读）

- **契约唯一真源**：`web/src/lib/answer.ts`（前端 TS），后端 `web_api/contract.py`（Pydantic）
  镜像它，`model_dump(by_alias=True)` 出 camelCase JSON 前端零解析。Datasheet 组件聊天页/
  图鉴页零改动复用——加新页签务必复用契约与既有组件。
- **槽位两类**：A 类（trace/entityCard/cites）从工具结果确定性推导零 LLM；B 类（verdict/
  calc/sensitivity/followups）走 `web_api/structurer.py` 一次结构化 LLM + `richtext.py`
  tokenizer 切 RichText span。
- **诚实红线**：不伪造页码（src 标 L3 结构库来源）、能力空则留空、阵营中文名用 curated
  映射（`web_api/codex.py:_FACTION_ZH`，勿回退众数——含盟友阵营会污染）。
- **React 坑**：Next16 ESLint 拦 set-state-in-effect——状态重置放事件处理器，effect 只异步取数。

## 本地运行（续做时先起两个服务）

```bash
# 后端（需 DEEPSEEK_API_KEY 在 env + 代理 127.0.0.1:7897）
cd D:/Project/py/RAG
export HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897
.venv/Scripts/python.exe -m uvicorn web_api.main:app --host 127.0.0.1 --port 8000
# 前端（另开）
cd web && npm run dev   # 或 npm start（跑 npm run build 之后）
```
访问 http://localhost:3000（聊天）/ http://localhost:3000/codex（图鉴）。
后端端点：`/chat` SSE、`/chat/sync`、`/codex/factions|.../units|/units/{id}`、`/wiki/{path}`、`/healthz`。

## ⏭️ 下一步（Stage 4 剩两页签）

1. **模拟器页签**（依赖已解锁——P4/P5 引擎就位，后端 `agent/tools.py:simulate_combat` 已有）：
   - 后端加 `POST /simulate`（或复用 agent）返回 SimReport（期望伤害/击杀/团灭率/分布 p10-90/
     阶段漏斗/每 100 点性价比 + 诚实未建模清单）。报告结构见 `agent/tools.py:_report_to_dict`。
   - 前端 `/simulator` 页：攻/守单位选择（可复用 codex 单位列表）+ 姿态开关（掩体/半程/冲锋/
     防守 opt-in）+ 结果可视化（漏斗/分布条图，用原生 SVG 或已有组件，勿引重库）。
   - 设计稿的 B 方向「阶段漏斗」在这复活；SiteHeader 把「模拟器」从置灰改真路由。
2. **军表实验室页签**：严格依赖 T3（P6 军表系统 engines/roster/），未开工——先做 T3 再回来。

## 其余待办（非本线）

- Stage 5 部署：key 只 env、限流+CORS、鹰徽自绘更抽象版、不提供原文/库整体下载。
- 数据坑记录：fixture 用的「炮击战斗服」在 resolver 是 ambiguous，需「炮击战斗服小队」全名。
- 全项目其它未完成：见 `docs/superpowers/plans/2026-07-12-remaining-tasks.md`（T3 军表/T4 DSL 等）。
