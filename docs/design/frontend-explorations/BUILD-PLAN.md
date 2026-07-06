# 战锤风前端制作计划（v2-warhammer.html → 正式站）

> 2026-07-06 定稿的设计稿：`docs/design/frontend-explorations/v2-warhammer.html`
> 设计语言来源：Wahapedia 10ed 实际 CSS（复刻 GW 官方 datasheet）——
> 钛帝国 `#175966/#2e5a6a`、暗底 `#0b171b`、GW 红 `#990000/#a31317`、
> 骨白 `#e7e9e1` + 官方切角/盾形 clip-path 坐标、ConduitITC → Bahnschrift 平替。
> 对应 v2 蓝图 P8（FastAPI + Next.js + Tailwind）；L4/L5 纯 Python 库已就位（P3 完成 agent/）。

## Stage 0 · 设计定稿（现在，0.5 轮）
- 看 v2-warhammer.html（桌面直接开文件；手机版式看 `_mobile-test.html` 三联屏）
- 按 E1–E9 角标反馈微调 1–2 轮 → 冻结设计 tokens
- 验收：用户点头

## Stage 1 · 设计系统抽取（~0.5 天）
- `tailwind.config`：上述色板进 theme.colors；切角/盾形/属性格三个 clip-path polygon 做成工具类常量
- **字体决策（上线前必须换）**：mockup 用的 Bahnschrift 是 Windows 系统字体，访客没有
  → 自托管开源窄体（Barlow Condensed / Oswald）+ Noto Sans SC 中文回退；不可用 GW 字体资产
- 基础组件：`PlateButton`（切角按钮）/ `ClipPanel` / `StatBox`（属性格）/ `WaxSeal`（封蜡）/
  `VerdictShield`（判定盾）/ `KwBar`（关键词条）
- 验收：Storybook 或一页 kitchen-sink 全组件过目

## Stage 2 · 聊天页静态版（1–2 天）
- Next.js App Router，组件化 E1–E9：Header/Nav、AskCard、ToolTrace、VerdictCard、
  CalcList、Datasheet、CiteSeals、SensitivityCTA、Composer
- 数据源 = 本设计稿同款 mock JSON（炮击战斗服问答做成 fixture，作为永久回归样例）
- 移动端沿用 680px 断点策略：表格容器横滑、chips 横滑、盾章降尺寸、输入框 ≥16px 防 iOS 聚焦缩放
- 验收：390 / 768 / 1280 三档不破版；Lighthouse 移动端 ≥ 90

## Stage 3 · 结构化回答契约 + 接后端（1–2 天）★关键决策
回答**不是 markdown 长文**，而是按槽位结构化返回（前端零解析，直接映射组件）：

```jsonc
{
  "verdict":   { "text": "...", "label": "值得带" },      // E4
  "calc":      [{ "n": 1, "text": "...", "cites": [2] }], // E5
  "entity_card": { /* datasheet 结构，同 wiki frontmatter+表 */ }, // E6
  "cites":     [{ "book": "...", "page": 44, "wiki": "factions/..." }], // E7
  "sensitivity": "...", "cta": { "kind": "simulator", "ready": false }, // E8
  "trace":     [{ "fn": "entity_resolver", "status": "ok|degraded", "note": "" }], // E3
  "followups": ["..."], "degraded": true                  // E9 / 全局
}
```

- FastAPI：`POST /chat`（SSE：先流 trace 事件，再逐槽位推送）、`GET /wiki/...`（图鉴数据）
- 在 `agent/loop.py` 之上加一层 response_formatter（P3 的 tools 本来就返回 dict，工作量小）
- 验收：同一 fixture 走真链路，渲染与静态版逐像素一致；QA 基准问题集回归

## Stage 4 · 其余三页签（各 1–3 天，按依赖排序）
1. **图鉴**：不依赖 P4/P6，可立刻做——wiki/*.md → 复用 Datasheet 组件 + 阵营索引页
2. **模拟器**：等 P4 蒙特卡洛引擎；届时把 B 方向稿的「阶段漏斗」可视化在这复活
3. **军表实验室**：等 P6 三件套（验表/点评/实时重算）

## Stage 5 · 部署与边界
- API key 只存服务端环境变量；接口限流 + CORS 白名单（蓝图既定）
- 版权红线：不提供规则书原文/数据库整体下载；**不用 GW 官方美术/字体资产**，
  全部 CSS/SVG 自绘（本稿已如此）；上线前把鹰徽再自绘得更抽象一版，避免商标风险
- 会话上下文：服务端内存 session 起步（蓝图既定，不引数据库）

## 依赖关系
- Stage 1–2 **立即可跑**，不等 P4–P7 后端进度
- Stage 3 只依赖 P3 已有的 agent/（补 formatter 小活）
- 模拟器页签严格依赖 P4；军表页签严格依赖 P6

## 每阶段通用验收
固定 fixture 回归对照 + 390/768/1280 三档截屏过目 + pytest 全绿（后端侧）
