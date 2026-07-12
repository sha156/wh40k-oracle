# Stage 3 · 结构化回答契约 + FastAPI 后端（设计 spec）

> 2026-07-12 立项。BUILD-PLAN Stage 3（★关键决策）：回答不是 markdown 长文，而是按 E1-E9
> 槽位结构化返回，前端零解析直接映射组件。前端契约已在 `web/src/lib/answer.ts` 定稿并有
> fixture；本 spec 定后端如何产出同一契约。

## 1. 关键决策：槽位怎么填

实地核对（本会话裸调）确认后端现状：
- `agent/loop.py` 的 `AgentResult` 出的是**自由文本 `answer`** + `tool_calls`（仅工具名）+
  `degraded` + `sources`；真实 `OpenAICompatLLMClient.next_step` 的 final 产出是**带
  `[《书名》第X页]` 标记的中文散文**，不吐结构化槽位。
- 但 `get_datasheet` 返回的 dict **已是完全结构化**（models/weapons/points_options），
  可直接映射 E6 兵牌卡。

据此把 9 个槽位分成两类，各走不同产出路径：

| 类别 | 槽位 | 产出方式 |
|---|---|---|
| **A 确定性推导**（零 LLM） | E3 trace / E6 entityCard / E7 cites / degraded | 从工具调用序列 + 工具结果 dict 机械映射 |
| **B 生成式**（需 LLM 推理） | E4 verdict / E5 calc / E8 sensitivity / summary / followups | 在 loop 之上加**一次结构化 LLM 调用**（response_formatter），产出轻标记纯文本，再由**确定性 tokenizer** 转 RichText |

**决策要点**：不改造 `agent/loop.py`，也不要求主循环 LLM 直接吐槽位 JSON
（会污染既有 709 测试绿的 gold 链路、且散文→槽位耦合进主循环脆弱）。改为在其外面加一层：

```
用户问题
  → AgentLoop.run（工具用 RecordingTools 包一层，录 trace；不动 loop.py）
      → AgentResult(answer 散文, tool_calls, sources, degraded)
  → response_formatter:
      ① A 类槽位：RecordingTools 录到的调用 + get_datasheet dict → trace / entityCard / cites
      ② B 类槽位：结构化 LLM 调用（输入=问题+散文答案+工具证据摘要+可用引用清单，
                  输出=verdict/calc/sensitivity/followups 的轻标记纯文本）
      ③ tokenizer：轻标记纯文本 → RichText inline 数组
  → Answer（契约）
```

## 2. RichText tokenizer（确定性，不靠 LLM 精确吐 span）

结构化 LLM 只写自然中文，用三种轻标记；tokenizer 用正则确定性切 span：

| 标记 | 例 | → Inline |
|---|---|---|
| `【关键词】`或`[非数字…]` | `【重型】`/`[毁灭伤害]` | `{t:"kw"}` |
| `[n]`（方括号纯数字） | `[2]` | `{t:"cite", n:2}` |
| `**结论**` | `**值得带**` | `{t:"strong"}` |
| 数值 token（自动） | `2.3` `67%` `3+` `D6+1` `S12` `AP-4` `5++` | `{t:"num"}` |
| 其余 | | `{t:"text"}` |

歧义消解：`[` 后**纯数字**→cite；`[` 后含非数字→kw（`[2]` 是引用、`[重型]` 是关键词）。
数值 token 只在未被标记包裹的 text 段内自动识别，避免误切关键词内部数字。

## 3. 诚实红线（承接项目 §1 验证纪律）

- **不伪造页码**：`get_datasheet` 不返回 book/page，故 E6 `src` 如实标 `L3 结构库 · <阵营>`，
  E7 页码引用只来自真有出处的工具结果（rag_search passages 的 book/page、
  get_keyword_definition 的术语页），**绝不为凑 fixture 的 "p.44" 编页码**。
- **abilities 为空就留空**：黑图中文层 `能力` 常为 `[]`，英文 datasheet 无技能文本——
  留空数组，不编能力描述。
- **degraded 透传**：`AgentResult.degraded` / `simulate_combat` 的 `modeled:false` 如实进
  E8 CTA 的 `ready:false` + E3 trace 的 `status:"degraded"`。
- **结构化 LLM 调用失败**：fail-closed——回退到「只出 A 类槽位 + verdict.lede=散文整段纯文本」，
  绝不因结构化失败而丢答案或编造槽位。

## 4. FastAPI（`web_api/main.py`）

- `POST /chat`：SSE。事件顺序 = 先 `trace`（逐工具）→ 再逐槽位（verdict/calc/entityCard/
  cites/sensitivity/cta/followups）→ `done`。v1 先跑完 loop 再按序推（trace 已录全），
  真·工具进行中流式留待后续迭代（需侵入 loop，本期不做）。
- `GET /wiki/{path}`：只读返回 wiki 页（复用 wiki_engine），前端图鉴页 Stage 4 用。
- **安全**（BUILD-PLAN Stage 5 既定，本期即落）：key 只读 env（`DEEPSEEK_API_KEY`）、
  CORS 白名单（默认 `localhost:3000`）、会话内存 session（不引数据库）。

## 5. 验收

- `web_api/` 单测：tokenizer（含 fixture 里所有 span 类型）+ entityCard 映射（真 DB 的
  Broadside）+ formatter（Fake LLM，断言 A 类槽位确定性正确）。
- 全库 pytest 不回归（709 绿基线）。
- 真链路冒烟：DeepSeek 跑 fixture 问题，SSE 出完整 Answer，人工核对槽位合理、无编造页码。
- 不追求与 fixture **逐字一致**（散文由真 LLM 生成，措辞必异）；追求**槽位结构一致 +
  前端零解析可渲染 + 诚实**。

## 6. 边界（本期不做）

- 工具进行中的真流式（需改 loop.py）；军表/模拟器页签数据（Stage 4，依赖 T3/已解锁 P4）；
  entityCard 武器名中文本地化（黑图 `武器` 层数据稀疏，属数据完整度问题非契约问题）；
  多轮会话记忆的持久化（内存 session 起步）。
