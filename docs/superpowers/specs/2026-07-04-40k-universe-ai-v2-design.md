# 战锤40K 宇宙垂类 AI —— 完整蓝图（v2）

日期：2026-07-04
状态：设计稿（待用户确认）
说明：本文档取代同日的 `2026-07-04-40k-universe-ai-design.md`（Wiki+Agent 初版），
在其基础上重新讨论并大幅扩展。关联文档：[LLM PDF 重构设计](2026-07-02-llm-pdf-refine-design.md)

## 一、愿景与范围

### 目标

从"规则书 RAG 问答"升级为**战锤40K 桌游全能助手**，能力分四档：

| 档位 | 能力 | 示例问题 |
|------|------|----------|
| ① 查 | 规则/单位数据/分队规则/CP技能，带原书引用 | "致命爆退是什么效果？" |
| ② 判 | 跨规则组合推理、裁判型判定 | "我冲锋后对方能不能先手反击？" |
| ③ 算 | 蒙特卡洛对战模拟、点数计算 | "10个火战士齐射打5个终结者，期望击杀几个？" |
| ④ 谋 | 军表验证+点评、战术建议 | "这份2000分钛帝国军表帮我看看缺什么" |

### 明确不做（本期）

- **meta 分析**：不引入比赛数据/社区 tier 榜（架构预留 `knowledge/meta/` 目录，后期想做时喂文档即可）
- **全自动组表**：只做验表+点评+缺口指出，不从零生成军表
- **背景故事 lore**：只做桌游规则域
- **对局全程托管**：不做"替你打一整局"的完整状态机，战术建议以单场景为单位

### 已确认的关键决策

1. 模拟精度 = **全量蒙特卡洛**（掷骰级，技能效果结构化进算式）
2. 军表深度 = **验表 + 点评**（合法性/算分/强弱项分析）
3. 交互 = **聊天 + 结构化面板**（模拟器/军表实验室有独立页签）
4. 数值权威源 = **英文 Faction Pack**，中文版做术语对照和描述文本
5. LLM 只干需要判断力的活（实体解析、意图理解、解释结果），确定性计算全部代码化
6. 知识组织 = **Karpathy LLM Wiki 范式**（参照 [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki)）：
   raw 源料不可变，wiki 页由 LLM 编译并持续维护，Ingest/Query/Lint 三操作，
   知识随时间复利增长；向量 RAG 从主线降级为检索兜底

## 二、分层架构总览

```
L0  data/                     原始 PDF（79本，只读）
L1  data_refined/             页级结构化 md（llm_refine 产物，已完成 ✅）＝ LLM Wiki 的 raw/ 层
L2  wiki/                     LLM Wiki 知识库（实体页 + index.md + log.md，LLM 全权维护）
L3  db/wh40k.sqlite           结构化数据层（属性/武器/点数/技能效果DSL，由 L2 编译）
L4  engines/                  三大引擎：模拟器 / 军表验证器 / 混合检索器
L5  agent/                    编排层：实体解析 + 意图路由 + 工具调用循环
L6  app.py                    Streamlit 多页签 UI
```

数据流单向向下依赖：L2 由 L1 编译，L3 由 L2 编译，L4 只读 L3+L2，L5 只调 L4 工具。
每层可独立测试、独立重建；上层坏了不影响下层资产。

**复用现有资产**：`data_refined/` 79 本书直接作为 L1；现有 FAISS+BM25 混合检索链
（含 jieba 分词、RRF、别名扩展）整体降级为 L4 的检索器兜底；100 题 QA 集升级为分类基准。

## 三、L2 LLM Wiki 知识库（Karpathy 范式）

### 范式约定

沿用 karpathy-llm-wiki 的核心约定，适配到战锤域：

| LLM Wiki 概念 | 本项目对应 |
|---------------|-----------|
| `raw/`（不可变源料，只读） | `data_refined/`（页级 md）；平衡补丁/新书先落这里 |
| `wiki/`（LLM 全权维护的知识页） | 实体页（单位/CP技能/分队/核心规则/USR） |
| `wiki/index.md`（全局索引） | 按阵营/类型分组，一行一页：链接+摘要+Updated 日期 |
| `wiki/log.md`（追加式操作日志） | 每次 ingest/lint 记一条，级联更新列在条目下 |
| **Ingest** | 新书/补丁 → raw → 编译进受影响实体页 + 级联更新 + 更新索引和日志 |
| **Query** | 先读 index.md 定位 → 读实体页 → 带 wiki 页引用回答 |
| **Lint** | 确定性检查自动修（断链/索引不一致），判断类问题报告给人 |
| **Archive** | 用户说"存下来"时，把裁判判定/模拟结论归档成新 wiki 页（标 `[Archived]`） |
| 冲突标注 | 中英文版本冲突、新旧补丁冲突 → 页内标注分歧+来源，不静默覆盖 |

与原版 skill 的差异：原版 ingest 是逐篇文章手动喂，我们的初始 79 本书走**批量编译器**
（wiki_compile.py）一次建库；建库之后的日常维护（季度补丁、FAQ、勘误、新 codex）
回归标准 Ingest 操作——这正是该范式的甜点区：知识库随版本演进复利生长，而不是每次重建。

### 目录结构

```
wiki/
├── index.md                        全局索引（一行一页：链接+摘要+Updated）
├── log.md                          追加式操作日志
├── terms.md                        双语术语总表（自动生成）
├── core-rules/                     核心规则：一个概念一页
│   ├── 阶段-冲锋阶段-charge-phase.md
│   ├── 通用技能-致命爆退-deadly-demise.md    ← USR（通用特殊规则）单独建页
│   ├── 序列-战斗顺序判定-fight-order.md      ← "谁先打"这类跨节规则合成页
│   └── ...
├── factions/<阵营slug>/
│   ├── index.md                    军队规则、分队总览
│   ├── units/<单位slug>.md
│   ├── stratagems/<技能slug>.md
│   ├── detachments/<分队slug>.md
│   └── enhancements/<强化slug>.md
└── faq/
    └── 平衡补丁-YYYY-MM.md          按补丁期归档，带生效版本号
```

### 实体页 = frontmatter + 正文 + 交叉链接

```markdown
---
id: tau-empire/units/fire-warriors        ← 全局唯一 canonical ID
name_zh: 火战士队
name_en: Fire Warriors
aliases: [FW, 火武士, 火战士班]            ← 社区译名，可持续追加
faction: tau-empire
type: unit
points: {"5": 50, "10": 80}
keywords: [Infantry, Battleline, Fire Warriors]
version: {points: "MFM v1.4", rules: "Dataslate 2026-03"}   ← 版本戳
sources:
  - {book: 钛帝国十版CODEX-20251112, pages: [42, 43]}
  - {book: Faction Pack Tau Empire, pages: [12]}
raw:                                      ← LLM Wiki 约定：回链不可变源料，lint 校验
  - ../../data_refined/钛帝国十版CODEX-20251112/page_042.md
  - ../../data_refined/Faction Pack Tau Empire/page_012.md
updated: 2026-07-04                       ← 知识内容最后变更日，非文件时间戳
---
## 属性表
| 模型 | M | T | SV | W | LD | OC |
|...|
## 武器
|...|
## 技能
- 原地隐蔽（Duck and Cover）：→ [[core-rules/通用技能-掩护]]
```

### 编译器 wiki_compile.py（流水线六步）

```
① extract_entities   代码：扫 data_refined/**/*.md 的 ## 标题 → 实体候选表
② pair_entities      LLM：按阵营做中英配对 → pairing.json（低置信度→人工校对清单）
③ synthesize_page    LLM：收集实体全部来源片段 → 合成单页（内容哈希缓存，增量重跑）
④ inject_crosslinks  代码：用术语表扫正文关键词 → 自动插 [[链接]]
⑤ build_outputs      代码：index.md / terms.md / 喂给 L3 的 entities.jsonl
⑥ lint               代码：断链、索引与文件不一致、raw 回链失效、无点数单位、
                     别名冲突、未配对实体 → 确定性问题自动修，其余出报告
```

每步跑完追加 `wiki/log.md`。成本：deepseek 全量编译约 2000 实体页 × 2K tokens
≈ ¥10-15 一次性；此后按哈希增量。

### Ingest 操作（建库后的日常维护入口）

初始建库用上面的批量编译器；之后所有知识更新走标准 LLM Wiki Ingest：

```
新源料（季度平衡补丁 / MFM点数册 / FAQ / 新codex PDF / 你随手丢的规则解读文章）
  ① 落 raw：PDF 走 llm_refine 增量 → data_refined/<书名>/；散篇文章直接存 md
  ② 编译：定位受影响实体页 → 合并更新（点数变更/规则勘误），冲突处标注分歧+来源
  ③ 级联更新：点数变了 → 该单位所在阵营 index、terms、引用它的分队页同步刷新；
     核心规则勘误 → 扫引用该规则的所有实体页
  ④ 收尾：wiki/index.md 刷新 Updated 日期；wiki/log.md 追加操作记录；
     db_compile 重编译 L3；QA 回归通过才算完成
```

## 四、L3 结构化数据层（wh40k.sqlite）

模拟、算分、验表的地基。由 L2 frontmatter + 表格解析编译生成（`db_compile.py`），
**永不手写数据**——发现错误改上游（L2 页或解析规则），重编译。

### 核心表

```sql
units(id, faction, name_zh, name_en, points_json, keywords_json, version)
models(unit_id, name, M, T, SV, INVULN, W, LD, OC, count_options_json)
weapons(id, unit_id, name_zh, name_en, range, A, BS_WS, S, AP, D, keywords_json)
   -- keywords_json: ["RAPID FIRE 1","LETHAL HITS"] 武器词条直接机器可读
abilities(id, owner_id, scope, condition_json, name_zh, name_en, text_zh, effect_dsl_json, dsl_status)
   -- scope: weapon/unit/attached/army/detachment/stratagem ← 上下文组装器按此挂载
   -- condition_json: 生效条件（"仅对MONSTER"/"仅被引导时"），组装器转成开关
   -- dsl_status: encoded / partial / not_modeled   ← 模拟覆盖度的诚实标记
stratagems(id, faction, detachment, name_zh, name_en, cp_cost, phase, text_zh, effect_dsl_json, dsl_status)
detachments(id, faction, name_zh, name_en, rule_text, enhancements_json)
aliases(alias, canonical_id, lang, source)   -- 实体解析的查找表
```

### 技能效果 DSL（模拟引擎的输入语言）

声明式 JSON，描述"何时触发、什么条件、改什么"：

```json
// 痛苦无感 5+
{"effect": "feel_no_pain", "value": 5}

// 对载具锁伤4+（ANTI-VEHICLE 4+）
{"when": "wound_roll", "if": {"target_has_keyword": "VEHICLE"},
 "effect": "critical_wound_on", "value": 4}

// CP技能：本阶段该单位命中+1
{"scope": "phase", "effect": "modify_hit_roll", "value": 1}

// 首领加成：所附队伍射击命中重骰1
{"scope": "attached_unit", "when": "hit_roll", "effect": "reroll_ones"}
```

原语集合（第一版约 30 个）覆盖十版通用词条：
reroll(1s/all/fail)、modify(hit/wound/save/damage/AP)、critical_hit_on / critical_wound_on、
lethal_hits、sustained_hits(X)、devastating_wounds、feel_no_pain(X)、damage_reduction(X)、
invuln(X)、ignore_modifiers、mortal_wounds(X)、fights_first、set_strength/toughness、
twin_linked、blast、rapid_fire(X)、melta(X)、torrent、heavy、anti_x(K, N)、hazardous、
one_shot、psychic、precision、extra_attacks、lance、assault、pistol、indirect_fire。

**DSL 录入策略**（工作量最大的一块，滚动推进）：
1. 武器词条（RAPID FIRE 等）→ 直接从武器表 keywords 解析，**零人工**
2. 通用 USR（致命爆退/痛苦无感等）→ 一次性写好 ~30 个原语映射
3. 阵营专属技能 → LLM 初翻成 DSL + 人工校对，按试点阵营逐个推进
4. 翻不动的复杂技能 → `dsl_status: not_modeled`，模拟报告里明示"未计入"

## 五、L4-1 蒙特卡洛模拟引擎（engines/simulator/）

### 上下文组装器（context_builder.py）——模拟的前置难点

一次对战的生效规则来自五层，归属逻辑各不相同：

| 层 | 来源 | 挂载方式 |
|---|------|---------|
| ① 面板层 | 单位属性/武器词条/自带技能 | 实体解析后自动 |
| ② 军队规则层 | 阵营 army rule（如钛帝国引导） | `unit.faction` 外键自动 join |
| ③ 分队层 | 分队规则+强化（组军选择，单位推不出） | 用户指定才挂载，否则列为可选开关 |
| ④ CP技能层 | 玩家主动开销 | 永远是可选开关 |
| ⑤ 总规则层 | USR 语义/SvT查表/修正上限 | 引擎内置 |

```
build_context(attacker, defender, options) → SimContext
  ① 实体解析 → 双方单位+武器 DSL
  ② faction join → 军队规则效果（含条件，如"被引导时"）
  ③ options 里给了分队/强化/CP技能/首领 → 挂载；没给 → 汇入开关列表
  ④ 态势开关：冲锋/掩体/半血/距离档
  ⑤ 产出：双方效果包 + toggles（渲染成面板开关）+ not_modeled 清单
```

实现依赖：effects 表带 `scope`（weapon/unit/attached/army/detachment/stratagem）
和 `condition` 字段，②③步是纯 SQL join，零 LLM。

聊天端默认档 = 面板+军队规则，回答附敏感性提示（"若在X分队命中再+1"），
用户点名分队/CP技能则全量挂载；面板端 toggles 全部可视化调参。

### 攻击序列流水线（十版标准流程逐骰模拟）

```
build_context（见上，产出 SimContext）
  → attacks 数量（解析 D6+3 等随机骰）
  → hit_roll（修正上限±1、重骰、暴击词条 lethal/sustained）
  → wound_roll（S vs T 查表、anti-X、devastating wounds）
  → allocate（伤害分配规则、precision 点名）
  → saving_throw（AP、无效保护 invuln 取优、掩体）
  → damage（D 值、damage_reduction、伤害不溢出到下一模型）
  → feel_no_pain
  → 循环至攻击耗尽 → 记录本次迭代结果
× N=10000 次迭代
```

### 输出（SimReport）

- 期望伤害 / 期望击杀模型数 / 整队团灭概率
- 分布图数据（P10/P50/P90，直方图）
- 反向视角：对方反打的同一套数字（"值不值得冲"要看交换比）
- **诚实声明**：本次模拟计入的技能清单 + `not_modeled` 未计入清单
- 敏感性提示：如"若对方使用CP技能盔甲坚守，期望击杀降至X"

### 战斗顺序判定器（fight_order.py，"谁冲谁"的核心）

独立小模块，输入双方状态（是否冲锋、fights first 技能、interrupt CP技能），
输出先攻序列。规则来源固化为代码 + 单元测试（十版战斗顺序是有限状态，可枚举），
判定结果附 wiki 规则页引用。Agent 回答"谁先手"= 判定器结论 + 引用 + 模拟数字。

### 验证体系

- 黄金用例集：~50 个手算校验场景（基础射击/近战/各词条单独生效/组合生效）
- 与社区工具（UnitCrunch 等）抽样对照
- 每个 DSL 原语一组单元测试；组合场景集成测试
- 随机种子固定，结果可复现

## 六、L4-2 军表系统（engines/roster/）

```
roster_parser.py    输入：官方App导出文本 / BattleScribe / 自然语言列表
                    → 实体解析 → 标准 Roster 对象（单位+配置+强化+分队）
roster_validator.py 规则检查：点数上限、重复限制（Rule of 3）、
                    Epic Hero 唯一、分队与阵营兼容、首领依附合法性
                    → 违规清单（每条附规则引用）
roster_critic.py    点评：调模拟引擎跑该军表 vs 标准威胁矩阵
                    （重装甲/轻步兵横队/精英近战/飞行单位等原型靶标）
                    → 火力覆盖雷达图数据 + 缺口描述 + LLM 生成点评文本
```

单位角色标签（反装甲/反步兵/压字/屏障/机动）在 L2 实体页 frontmatter 加
`roles` 字段，由 LLM 按属性+技能初标、人工校对。

## 七、L5 Agent 编排层（agent/）

### 实体解析器（entity_resolver.py，全系统共用）

用户嘴里的"冷言""FW""铁皮大壮"→ canonical ID。三级解析：
① aliases 表精确命中 → ② 模糊匹配（编辑距离+拼音）→ ③ 向量检索兜底。
多候选时返回列表让 Agent 反问确认。**这是聊天体验的命门，单独建测试集**
（把 QA 基准里踩过坑的社区译名全部收进来）。

### 工具箱（agent/tools.py）

```python
search_wiki(query)                    LLM Wiki Query：先查 index.md 定位，再全文检索
get_entity(name_or_id)                读实体页（自动实体解析）
get_keyword_definition(keyword)       USR/核心概念定义
judge_fight_order(ctx)                战斗顺序判定器
simulate_combat(attacker, defender, options)   蒙特卡洛引擎
validate_roster(roster_text)          验表
critique_roster(roster_text)          验表+模拟点评
calc_points(unit_list)                精确算分
archive_answer(title, content)        LLM Wiki Archive：用户要求时把判定/结论存为 wiki 页
rag_search(query)                     现有混合检索（兜底）
```

### Agent 循环

```
用户输入
  → 意图分类（查/判/算/谋/闲聊，轻量 LLM 调用）
  → function calling 循环（max_steps=6，模拟类问题步数多）
  → 回答合成：结论 + 数字 + 引用（实体页→原书页码）+ 未建模提示
异常/空结果 → 静默降级 rag_search 走老链路回答
```

### 会话上下文

会话级记住用户军表/阵营（"我的钛帝国军表"指代先前粘贴的 roster），
存 Streamlit session_state，不落盘。

## 八、L6 UI（Streamlit 多页签）

```
💬 聊天        主入口，全部能力可达；模拟类回答附"在模拟器中打开"按钮（带参跳转）
⚔️ 模拟器      下拉选攻/守单位→武器配置→增益开关（CP技能/光环/掩体）→分布图
📋 军表实验室  粘贴军表→合法性报告+火力雷达图+点评；可增删单位实时重算
📖 图鉴        wiki 浏览器：阵营→单位/技能/分队，双语切换，交叉链接可点
```

聊天与面板共用同一套 L4 引擎和实体解析器，只是入参方式不同。

## 九、数据更新与版本治理

日常更新统一走第三节的 **Ingest 操作**（raw → 编译 → 级联 → 索引/日志 → db 重编 → QA 回归）。
本节只补充版本治理规则：

- 版本戳贯穿：实体页 frontmatter 记 `version`，回答中标注"点数依据 MFM v1.4"
- 新旧版本共存书籍以最新版入库，旧版移 `data/archive/`；wiki 页只留最新事实，
  重大变更在页内"版本历史"小节留一行记录（何时、从什么改成什么、依据哪个补丁）
- lint + QA 基准回归通过才算 Ingest 完成，失败则回滚该批实体页（git 版本控制天然支持）

## 十、质量体系

| 基准 | 内容 | 目标 |
|------|------|------|
| QA-规则 | 现有100题中的规则定义/判定类 | ≥90%（当前77%全集） |
| QA-数据 | 属性/点数/武器数值类（答案唯一可对错） | ≥98%（走 SQLite 后应接近满分） |
| SIM-黄金 | 50个手算校验场景 | 100%（误差<1%） |
| ROSTER | 20份合法/非法军表判定 | 100% |
| 实体解析 | 社区译名→canonical ID 测试集 | ≥95% |

反幻觉铁律：数值类回答必须来自 SQLite（禁止 LLM 从上下文抄数字）；
判定类回答必须带规则页引用；凑不齐依据时明说"无法确认"并给查询方向。

## 十一、风险与边界

| 风险 | 应对 |
|------|------|
| DSL 录入量大（30阵营×几十技能） | 滚动推进：先2个试点阵营全覆盖，其余阵营先享受"查/判/基础模拟"，DSL 逐月补 |
| 十版→十一版规则更换 | L0-L2 按书隔离，换版=新书重跑流水线；模拟引擎攻击序列抽象成可配置 pipeline |
| 2本书部分页无文字层 | glm-4v-flash 视觉兜底（已有规划，二期） |
| LLM 编译成本失控 | 全流程内容哈希缓存；编译类调用一律 deepseek 而非贵模型 |
| 版权 | 个人使用，wiki/ 与 db/ 不公开发布，.gitignore 处理 |

## 十二、实施路线图（每期结束都有独立可用的产出）

```
P0  wiki_compile ①②：实体清单 + 中英配对 → terms.md
    └ 立即收益：术语表喂给现有 UNIT_ALIASES，老链路 QA 直接提升
P1  wiki_compile ③-⑥ 全流水线，试点编译 钛帝国+吞世者 两阵营 + 核心规则
    └ 收益：图鉴页签可用，实体页质量肉眼可验
P2  db_compile + SQLite + calc_points + 实体解析器
    └ 收益：数据类问题从"检索碰运气"变精确查询
P3  Agent 编排（工具箱+循环+降级）替换 app.py 单链，QA 全量回归对比
    └ 收益：查/判 两档能力上线，聊天体验换代
P4  模拟引擎：攻击序列 pipeline + 武器词条自动解析 + 通用 USR 原语 + 黄金用例
    └ 收益：基础"谁打谁"模拟上线（暂不含阵营专属技能）
P5  DSL 录入试点阵营专属技能 + 战斗顺序判定器 + 模拟器面板
    └ 收益：③算 ④谋（判定部分）完整体
P6  军表系统三件套 + 军表实验室面板 + 会话上下文
    └ 收益：④谋 完整体
P7+ 剩余28阵营 DSL 滚动录入；全量 wiki 编译；基准持续扩充；
    Ingest 维护流程实战演练（拿下一次 GW 平衡补丁走一遍全流程）
```

依赖关系：P0→P1→P2→{P3, P4} 并行 → P5 → P6。P3 之后每一期都是独立增量，
可按兴趣挑着做（ADHD 友好：每期 2-5 天粒度，有即时正反馈）。

## 自审清单

- [x] 无 TBD/占位符
- [x] 各层职责边界清晰，依赖单向
- [x] 与已确认决策一致（蒙特卡洛/验表点评/聊天+面板/不做meta）
- [x] 每期有独立可用产出与回退空间
- [x] 错误处理与降级策略已定义（Agent降级RAG、DSL not_modeled 诚实标记）
