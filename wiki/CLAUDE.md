# 战锤40K Wiki 宪法

> 本文件是 `wiki/` 的最高规则。**任何人（或 AI）在 wiki 里新增、修改、删除内容前，先读完本文件。**
> 规则要变，先改本文件，再改代码和内容——顺序不能反。
> 注意：本文件自身也会被 broken-links lint 扫描，因此文中所有双方括号链接示例
> 必须指向真实存在的页面；**反例与占位写法一律用全角括号 ［［…］］ 书写**，避免污染 lint 报告。

## 0. 这个 wiki 是什么、给谁读

这是战锤40K 垂类 AI 的 **L2 知识层**（v2 蓝图：L0 PDF → L1 data_refined → L2 wiki → L3 sqlite → L4 引擎 → L5 agent）。同一份 Markdown 有三类读者，所有规则都为同时伺候好这三者而设：

| 读者 | 入口 | 依赖什么 |
|------|------|----------|
| 人 | Obsidian vault（`wiki/` 直接作为库打开） | tags / aliases / 双链图谱 / 可读正文 |
| Agent | `python -m wiki_engine query`、agent/tools.py | frontmatter 字段、index.md、terms.json |
| 下游编译器 | db_compile → wh40k.sqlite → 模拟器 | frontmatter 的 id/points/keywords 等结构化字段 |

**最高纪律：frontmatter 是机器真源，正文是人读展示。两处出现同一数据（如分数）时必须一致；冲突以 frontmatter 为准并立即修复正文。**

## 1. 目录地图

```
wiki/
├── CLAUDE.md            本规则（唯一完全手写的根文件）
├── index.md             全局索引 —— 生成物，禁止手改
├── log.md               操作日志 —— 只追加，禁止改历史行
├── lint-report.md       体检报告 —— 生成物，禁止手改
├── review_needed.md     待人工校对清单 —— 生成物
├── terms.md / terms.json 双语术语表 —— wiki_compile 生成物
├── .obsidian/           本地 Obsidian 配置，不提交 git
├── core-rules/          全部"规则类"页面（含阵营机制，见 §2）
│   └── <english-slug>.md
└── factions/<中文阵营名>/
    ├── index.md         阵营索引 —— 生成物
    ├── units/           兵牌页（1 张 Wahapedia datasheet = 1 页）
    ├── stratagems/      计谋（目录未建，命名已预留）
    ├── detachments/     分队（预留）
    └── enhancements/    强化（预留）

未来扩展（见 §10 扩展协议，未走完协议前不得建目录）：
    missions/            任务/部署图
    maps/                地形/战场
```

- **阵营目录名 = 中文阵营名**，且必须取自 `wiki_engine/models.py` 的 `FACTION_NAMES` 映射（钛帝国、吞世者、星际战士……21 个）。新阵营先在 `FACTION_NAMES` 登记，再建目录。
- 生成物清单（禁止手工编辑，改了也会被下次 build 覆盖）：`index.md`、`factions/*/index.md`、`lint-report.md`、`terms.md`、`terms.json`、`review_needed.md`。**想改索引里的内容 = 去改实体页，然后重跑 build。**

## 2. 内容放哪里：分层判定

1. **所有"规则/技能/关键词/阶段"类页面 → `core-rules/`**，包括阵营专属机制（如"为了上上善道"、破敌重誓、黑暗契约）。不按阵营拆规则目录——这是有意的历史决定：链接目标全局唯一，跨阵营引用永不断链。阵营归属用 frontmatter 的 `faction` 字段表达，不用目录表达。
2. **单位、计谋、分队、强化 → `factions/<阵营>/<type>s/`**。这些是"某个阵营拥有的东西"，目录即归属。
3. **一个概念一页**，宁多勿混。判定标准：这个名字会不会被别的页面用双链 ［［…］］ 引用？会，就值得单开一页。
4. 不确定放哪 → 先进 `review_needed` 思路：开在 core-rules 并在 frontmatter 标 `faction`，之后随 lint 审查再定。

## 3. Frontmatter Schema（机器真源）

字段定义与 `wiki_engine/models.py::WikiPageFrontmatter` 严格同步，改 schema 必须两边同时改：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 全局唯一、**创建后永不修改**（是链接与 sqlite 的锚点）。unit = Wahapedia datasheet ID（9 位数字，YAML 里必须加引号如 `'000000412'`）；core-rule = 英文 kebab slug（如 `rapid-fire`）；Wahapedia 查无此单位（Legends/自制）时用 `<阵营拼音>-<name-slug>` 并在 sources 说明 |
| `name_zh` | ✅ | 权威中文名（选名规则见 §6） |
| `name_en` | ✅* | 英文 canonical 名；确实无英文源时可缺 |
| `aliases` | 建议 | 其他译名/简称/缩写，供检索与 Obsidian；每收录一个译名就少一次检索 miss |
| `faction` | unit 类必填 | 中文阵营名，须在 `FACTION_NAMES` 值域内 |
| `type` | ✅ | 枚举：`unit` / `core-rule` / `stratagem` / `detachment` / `enhancement`。**新增枚举值必须走 §10 扩展协议** |
| `points` | unit 必填* | 机器真源，dict 格式 `{模型数: 分数}`，如 `{5: 50, 10: 100}`；正文"**分数**"只是展示。现存页大量缺失（lint info: missing-points），补齐是常态任务，权威源见 §7 |
| `keywords` | unit 建议 | 普通关键词英文/规范中文列表（步兵、战线…），是 tags 自动生成和 sqlite 过滤的输入 |
| `tags` | 自动 | 由 `generate_tags()` 生成（type/faction、faction、type、每个 keyword 一条），**不手写** |
| `version` | 建议 | 数据版次，如 `{points: "MFM v1.4", rules: "Codex 10E 2025"}`，多版次共存时救命 |
| `sources` | ✅ | 出处列表 `[{book, pages}]`，无源不落笔（§7） |
| `raw` | ✅（流水线页） | `data_refined/` 回链，人工手写页可缺但要在 sources 里写全 |
| `updated` | ✅ | ISO 日期字符串（加引号防 YAML 解析成 date 对象） |
| `verify_warn` | 仅 True 时写 | LLM 合成数字校验未通过的标记，人工核对流程见 §7 |

## 4. 页面正文模板

### 4.1 所有页面通用

- frontmatter 之后、第一个 `##` 之前，写**一行 ≤60 字的中文导语**（这是什么、干什么用）。index.md 的摘要列和 RAG 检索都吃这一行——没有导语，索引里就会出现"**装备选项**："这种碎句（现存页的通病，逐步补齐）。
- 每个 `##` 小节要**自包含**：RAG 按 `##` 分块，小节内不许写"见上文/如前所述"。
- 数值一律半角；距离统一写 `6"`（半角双引号，禁用 `〞`）；骰子写 `D6` / `2D6` / `D3`；正负修正写 `+1` / `-1`。

### 4.2 unit 页（六节，顺序固定，节名一字不差）

```markdown
## 属性表
| 模型 | M | T | SV | W | LD | OC |
## 远程武器
| 武器 | 射程 | A | BS | S | AP | D | 技能 |
## 近战武器
| 武器 | 射程 | A | WS | S | AP | D | 技能 |
## 技能
## 单位构成
## 关键词
```

- 列名与列序固定，禁止增删列（下游按表头解析）。
- 某节确实无内容时**保留节标题**，正文写"无"（如无近战武器的炮台）；禁止直接删节，否则解析器无法区分"没有"和"漏了"。
- 武器技能列里的技能一律链接到 core-rules，如 [[core-rules/assault.md|突击]]。
- 装备选项、领袖合并、运输等归入"单位构成"节；`**分数**：` 行放在单位构成末尾，数值必须与 frontmatter `points` 一致。
- Legends 单位：导语行标注 `*LEGENDS*`，并加 alias。

### 4.3 core-rule 页

```markdown
## 中文名 ENGLISH NAME

规则正文（教科书式陈述，不写战术评价）。
```

- 汉化版本译名差异用引用块固定句式，放在正文最前：
  `> 部分汉化版本译作"××"，与"△△"为同一概念 Xxx Yyy 的不同译名。`
  同时把这些译名全部收进 frontmatter `aliases`。
- 参数化技能（速射1、热熔2、斥候7"）要给出带例子的解释，见 [[core-rules/rapid-fire.md|速射]] 的写法。

## 5. 链接规范（断链是本 wiki 的头号腐化源）

1. **唯一合法格式：根相对路径 + `.md` + 管道中文显示名**：
   `[[core-rules/twin-linked.md|双联]]`、`[[factions/钛帝国/units/breacher-team.md|破袭小队]]`。
2. **禁止裸名链接**：［［近战武器］］、［［克鲁特］］这种写法是历史上全部断链的来源——它赌"存在一个恰好叫这个名字的文件"，赌输就是 error。想链接却不知道路径？先 `python -m wiki_engine query 近战武器` 查，查不到就不加链接、用纯文本。
3. 链接目标不存在的页面（"以后会写"）：**不要预埋链接**，用纯文本写名字。本 wiki 与个人笔记库不同，红链不是 TODO 标记，是 lint error。
4. 同一页内，同一目标**只链首次出现**，之后用纯文本，避免正文变成链接海。
5. 交叉链接的批量注入交给 `python -m wiki_engine crosslinks`（基于 terms.json 别名匹配）；手写少量链接时遵守以上格式即可。

## 6. 命名与译名纪律

- **name_zh 选名优先级**：GW 官方中文 > 最新版 codex 汉化组译名 > 社区最通行译名。选定后全 wiki 统一用它，其余译名全部进 `aliases` + core-rule 页的译名引用块。正文用词必须与 `terms.md` 术语表一致——发现术语表错了，改 wiki_compile 的源头再重新生成，不要在正文里另起炉灶。
- **文件名 slug**：优先由 `name_en` 生成（小写、空格→连字符、去撇号，如 `breacher-team.md`），与 `wiki_engine/models.py::slugify` 行为一致。文件一旦建立不要改名（等于改所有入链）；确需改名走 §9 工作流并全库替换入链。
- **同名冲突**（alias-conflicts lint）：两个实体撞名时，给次要方加限定词（如"寻觅者导弹（装备）"vs 计谋同名页），并保证 aliases 不再重叠。

## 7. 数据真实性（最高优先级，没有之一）

1. **数值权威源排序：Wahapedia CSV / BSData > PDF 汉化书**。PDF 只做中文术语与规则文本源；属性、分数、武器数值与 Wahapedia 冲突时以 Wahapedia 为准，并在 `version` 里记录版次。
2. **无源不落笔**：每一页必须有 `sources`（书名+页码）；查不到的信息写"（源文本未提供）"，禁止按记忆或"合理推测"补数值——一个编造的 S 值会顺着 sqlite 流进模拟器，污染整条链路。
3. **verify_warn 处理流程**：该标记表示 LLM 合成时出现了原文没有的数字。人工逐数字对照 `raw` 回链的 data_refined 原文 → 修正错误 → 删除 frontmatter 的 `verify_warn` 行 → 跑 lint 确认该 warning 消失。**禁止未核对就删标记。**
4. 批量生成/修改必须对账：目标页数 vs 实际改动页数，差额要报告（防静默漏页）。
5. LLM 批量重写实体页前，先出 2–3 页样张人工确认格式，再铺全量。

## 8. 版本与归档

- 同一单位新旧 codex 共存时：**只保留最新版为正页**；旧版内容走 Archive 操作（`wiki_engine/operations/archive_op.py`）归档，不许两个版本同时以正页存在（会触发 alias-conflicts，也会让 RAG 检回过期数值）。
- 数据换版（新 MFM 分数、FAQ 勘误）：改 frontmatter `points`/正文 → 更新 `version` 和 `updated` → build 重建索引 → log.md 自动留痕。

## 9. 变更工作流（每次动 wiki 的标准动作）

所有命令用项目虚拟环境（系统 python 是 3.9，跑不动）：

```powershell
.\.venv\Scripts\python.exe -m wiki_engine query <名字>    # 改前先查：实体是否已存在（防重复建页）
# …编辑实体页…
.\.venv\Scripts\python.exe -m wiki_engine build           # 重建 index.md + 阵营索引
.\.venv\Scripts\python.exe -m wiki_engine lint            # 体检 + 自动修复；exit 1 = 有 error
```

- 大批量进料用 `pipeline`（合成→交叉链接→build→lint 一条龙）；新 PDF 源料走 `ingest`。
- **完成的定义：lint error = 0**。error（断链等）必须当场清零；warning（verify-warn、alias 冲突）要么当场处理、要么明确留档为已知问题；info（missing-points）允许存量，但新建页不得新增。
- **commit 前检查清单**：① lint 0 error；② 跑过 build（索引与内容同步）；③ log.md 有本次操作记录；④ 没有手改任何生成物；⑤ 批量任务已对账。
- 已知边界：lint 会扫描 `lint-report.md` 自身与本文件里的方括号示例，因此报告中可能出现自引用回声——判断真实断链数时以实体页行为准。（长期修法：给 check_broken_links 加 skip 名单。）

## 10. 扩展协议（加任务、地图或任何新内容类型时）

现有范围 = 规则专家 + 对局辅助（v2 蓝图定案：不做 lore、不做 meta 分析）。要加新类型（如 mission、map），**五步走完才许建目录**：

1. **先改本文件**：在 §1 目录地图和 §3 type 枚举里登记新类型，写出它的 frontmatter 附加字段和正文模板（比如 mission 页：`pack`（任务包）、部署图、主要目标、回合结构各一节）。
2. `wiki_engine/models.py`：type 枚举 + `entity_page_path` 路径规则。
3. 建目录 + 至少 1 页样张，确认 Obsidian / query / build 三方都读得对。
4. `wiki_engine/lint.py`：为新类型加最小 lint（必填字段、专属断链模式）。
5. 全量 `build` + `lint` 通过，log.md 记录"新类型上线"。

跳过任何一步的后果都已经发生过：没有 schema 的内容会在下次批量重建时被当成孤儿页扫进"未分类"。

## 11. AI 编辑守则（给未来的 Claude 会话）

- 编辑任何实体页后，**必须**跑 build + lint 才能宣布完成——"改了但没验证"要如实说。
- 禁止对 `wiki/**` 做全库正则批量替换，除非先 Grep 列出全部命中并逐类确认（表格里的数值极易误伤）。
- 禁止为了让 lint 变绿而删除 `verify_warn`、删除断链文本或删除空节——lint 是体检不是考试，作弊等于埋雷。
- 新建页面用现有同类型页当模板（unit 抄 [[factions/钛帝国/units/breacher-team.md|破袭小队]]，core-rule 抄 [[core-rules/rapid-fire.md|速射]]），不要凭空发明格式。
- 本文件不加 frontmatter（避免被扫描进实体索引）；文中新增双方括号链接示例前先确认目标存在。
