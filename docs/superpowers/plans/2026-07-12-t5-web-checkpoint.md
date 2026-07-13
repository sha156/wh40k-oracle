# T5 网站化 进度 CHECKPOINT（2026-07-12）

> 让「继续」能无损续接。BUILD-PLAN：`docs/design/frontend-explorations/BUILD-PLAN.md`；
> Stage 3 设计：`docs/superpowers/specs/2026-07-12-stage3-response-contract-design.md`。

## ✅ 已完成（Stage 1-4 图鉴）

| 阶段 | 内容 | 提交 | PR |
|---|---|---|---|
| Stage 1-2 | 前端设计系统 + 聊天页静态版（Next.js 16/Tailwind 4，E1-E9 组件化） | 30d53537 | #18 已并 |
| Stage 3 后端 | `web_api/` FastAPI——response_formatter 散文→结构化槽位契约 | 56cc8ae1 | #20 已并 |
| Stage 3 前端 | 前端切真调 /chat SSE（渐进渲染闭环） | c5b39467 | #21 已并 |
| Stage 4 图鉴 | `/codex` 阵营→单位→兵牌浏览（复用 Datasheet） | 226f886d | #21 已并 |
| Stage 4 模拟器 | `POST /simulate` + `/simulator` 页（选单位→装配→漏斗/分布） | 本分支 | — |

**当前分支**：`feat/stage4-simulator-tab`。**全库 739 测试绿。**

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

## ✅ Stage 4 模拟器页签（2026-07-13 完成）

- 后端：`agent/tools.py` 抽出 `simulate_combat_resolved`（canonical id 直调，免名字解析），
  `web_api/simulate.py`（options 边界白名单，n 钳 [100,20000]）+ `POST /simulate`；契约
  真源 `web/src/lib/sim.ts`，`contract.py` 的 Sim* 镜像（camelCase）。零 LLM。
- 前端：`/simulator` 页（`components/sim/UnitPicker|SimResults`）——阵营+单位双面板 →
  姿态开关（射击：未移动/半程/掩体/间瞄/守方隐身；近战：冲锋；守方 FNP/减伤/模型数）→
  多武器单位走 loadout_required 装配面板（武器池+点数档位）→ KPI 行 + B 方向阶段漏斗
  （只画同量纲的 attacks→hits→wounds→unsaved，damage/kills 进 KPI 不混轴）+ 击杀直方图 +
  建模边界诚实披露（已计入/未建模/偏差/守方未施加开关/阵营分队）。
- 交互坑：**切 phase 必须清 loadout**——近战/射击武器池不同，跨阶段沿用会被引擎静默滤成
  空手 0 伤（引擎语义是滤不匹配武器，不报错）。
- 端到端已浏览器目检：射击/近战/装配流/切换清空全通过；移动端断点复用图鉴页已验收
  pattern（resize_window 不生效未实机截屏）。

## ⏭️ 下一步

1. **军表实验室页签**：严格依赖 T3（P6 军表系统 engines/roster/），未开工——先做 T3 再回来。
2. 模拟器页签可选增强：defender_loadout 反打 UI（后端已支持 reverse 报告）、掩体等开关
   在近战下的语义提示。

## 其余待办（非本线）

- Stage 5 部署：key 只 env、限流+CORS、鹰徽自绘更抽象版、不提供原文/库整体下载。
- 数据坑记录：fixture 用的「炮击战斗服」在 resolver 是 ambiguous，需「炮击战斗服小队」全名。
- 全项目其它未完成：见 `docs/superpowers/plans/2026-07-12-remaining-tasks.md`（T3 军表/T4 DSL 等）。
