# P5 阵营技能 DSL 试点 + 战斗顺序判定器 + 模拟器面板 —— 立项设计（spec v1）

日期：2026-07-09
状态：立项（P4 已整体完工，全库 457 测试绿；本 spec 是蓝图 P5 的展开）
前置依赖：P4 已落地（`engines/simulator/` 十版逐骰序列 + 20 词条 Effect 通道 + 装配层 + `simulate_combat` 接线 + CLI + 「谋」门控）
关联文档：
- [v2 蓝图第五节 L4-1 / 路线图 P5](2026-07-04-40k-universe-ai-v2-design.md)（本 spec 是其 P5 展开）
- [P4 立项设计 spec v2](2026-07-09-p4-monte-carlo-simulator-design.md)（能力边界那一节列出的"留 P5"清单是本期入口）
- [数据架构定论](../../data-architecture-2026-07-09.md)（数值走 sqlite、别名走 aliases 表、abilities 折叠已修复到 3677 行覆盖 1709 单位）
规则版本锁定：**十版（10th edition），现行 Balance Dataslate**。战斗顺序与 USR 语义以现行 dataslate + `data_refined/10版40K通用技能速查表1.08` 为准；`data_refined` 英文核心是发售版，已过时，不作规则真源（承 P4 第七节纪律）。

蓝图 P5 一行话：**"DSL 录入试点阵营专属技能 + 战斗顺序判定器 + 模拟器面板 → 收益：③算 ④谋（判定部分）完整体"**。

---

## 零、开工前的数据就绪度实测（承 P4「数据就绪度是实测非应然」纪律）

P4 spec 曾按记忆写"abilities 全 NULL、全 not_modeled"。本期开工前**实测 `db/wh40k.sqlite`**，得到远比那句话丰富、但**也更危险**的真相——直接照 name 抓取会踩假实现坑：

| 实测项 | 数字 | 对 P5 的含义 |
|--------|------|-------------|
| `abilities` 行数 / 有 owner_id | 3677 / 3607（owner_id 命中 units.id） | 技能确实**按单位挂载**，不是纯词典 |
| `abilities.dsl_status` | **3677 条全 `not_modeled`**、`effect_dsl_json` 全空、`scope` 全空 | DSL 层确实 0%，是 P5 主体 |
| `abilities.name_zh` | 基本全 None | **无中文名**——分类只能靠 `name_en` + `text_zh`（英文 HTML） |
| `text_zh` 提及 `Feel No Pain` | 106 条 | 有料，但见下方陷阱 |
| `text_zh` 提及 `Stealth` | 13 条 | 干净、可建模（见下） |
| `stratagems` | 1482（name_en + cp_cost + phase + 英文 HTML text，dsl_status 全 not_modeled） | 可**列名做 toggle**，不可 fake-apply |
| `detachments` | 284（name_en + faction + rule_text 英文） | 同上 |
| `models.invuln` | 已结构化（P4 已用） | 无效保护是唯一干净的自动防守数值源 |

### 🔴 陷阱 T1：FNP 的值高度条件化 / 光环授予 —— 禁止正则直取

实测 106 条含 "Feel No Pain" 的技能文本，抽样：

```
Meganobz「Krumpin' Time」   : ...Feel No Pain 5+ ability...        ← 无条件、自带
Painboy「Dok's Toolz」       : ...Feel No Pain 5+ ability...        ← 光环，授予【附近其它单位】，自己未必吃
Librarian「Psychic Hood」    : ...Feel No Pain 4+ ability against… ← 条件：仅对【灵能攻击】
Librarian Dreadnought        : ...Feel No Pain 5+ ability against… ← 条件：仅对【致命伤/某类攻击】
Infiltrator Squad「Helix…」  : ...Feel No Pain 6+ ability...        ← 无条件、自带
```

**若用 `re.search(r'Feel No Pain (\d)\+')` 直取并全局施加，会三重出错**：
1. 把"against 灵能攻击"的条件 FNP 当成通用 FNP（多数命中是条件式）；
2. 把光环授予他人的 FNP 当成自带（Painboy 自己不吃 Dok's Toolz）；
3. 无法区分"每次攻击"vs"仅对致命伤"。

**这是与 P4 C1 同族的假实现坑**（照 schema 想当然）。裁决见第二节：**FNP 不做无脑自动施加，改"检测→标注条件→surface 成 toggle，仅无条件自带子集默认预勾"**。

### ✅ 唯一干净可自动的只有 invuln —— 二次实测把 auto 范围收得更紧

开工二次实测（`unit_zh_detail` + 各单位 `abilities` owner 行）进一步证伪了初版"Stealth/无条件 FNP 也能自动"的想法：

- **核心 USR（Stealth / Lone Operative / Deadly Demise / Deep Strike / Fights First…）只以词典行存在（owner=None，共 70 条）**，**不按单位挂载**；`units.keywords_json` 里的 "Stealth" 是 T'au「隐形战斗服」的**单位名关键词**（仅 2 例，全是假阳性）。→ **无法从库里可靠判定"某单位自带 CORE Stealth"**，Stealth 自动检测召回≈0。
- **"无条件 FNP" 是幻觉**：Meganobz 的原文是"**While the Waaagh! is active**, models in this unit have the Feel No Pain 5+ ability"——初版"无 against/aura/within 即无条件"的正则会漏掉"While…"从而**误判为无条件并错施加**。42 条"看似无条件"里混着大量 "While X" 条件式。→ **FNP 一律不自动施加**。

**据此把 auto 收敛到唯一真干净项**：
- **无效保护 invuln**：`models.invuln` 结构化字段，P4 已自动读入 `TargetProfile.invuln`。✅ 唯一 auto。

**结论（据二次实测收敛）**：P5 的价值不在"自动把技能都算进去"（数据不支持、会造假），而在四件事：
1. **战斗顺序真判定**（`fight_order.py`，纯规则、零数据依赖、高置信）——本期最硬的新增算力；
2. **把每个单位的技能精确分类披露**（取代 P4 笼统的"abilities 全未建模"一行）；
3. **把可建模的防守 USR（FNP X / Stealth / 减伤 / 掩体）解析出参数、surface 成 opt-in 开关**（引擎已支持这些 Effect，用户/面板一键启用即正确建模；**默认关，绝不自动施加**）；
4. **模拟器面板**。

即：**只有 invuln 自动；FNP/Stealth/减伤 检测+解析参数+开关化，默认关；其余精确分类为 not_modeled。宁漏不错。**

---

## 一、范围边界（P5 做 / 不做，硬划线）

| 能力 | 归属 | 状态 |
|------|------|------|
| **战斗顺序判定器 `fight_order.py`**（冲锋先打 / Fights First / Fights Last / Counter-offensive 打断） | **P5** | ✅ 纯规则有限状态机，代码+单测 |
| `judge_fight_order` 工具接线（替换 P5 桩）+「谋」门控覆盖 | **P5** | ✅ |
| `simulate_matchup` 用 fight_order **判定谁先打**（升级 P4 的"默认攻方先打"） | **P5** | ✅ |
| **abilities 分类器 `abilities.py`**：每单位技能 → (可建模防守 / 精确 not_modeled 分桶) | **P5** | ✅ 取代 P4 笼统清单 |
| **Stealth 开关建模**（启用后：守方全员 Stealth → 攻方射击命中 -1，仅射击） | **P5** | ✅ opt-in 开关（自动检测召回≈0，故 toggle 非 auto）；引擎有单测 |
| **FNP X 检测+参数解析+开关**（"Feel No Pain X+" 抽 X + 条件标注；默认**关**，绝不自动施加） | **P5** | ✅ 二次实测证伪"无条件子集"，一律 toggle |
| **减伤 / 掩体（Go to Ground）/ 其它防守技能** → 检测 + 解析参数 + surface 成 toggle（默认不施加） | **P5** | ✅ 诚实披露，用户 opt-in |
| **无效保护 invuln 自动建模** | **P5** | ✅ 唯一 auto（`models.invuln` 结构化，P4 已做，本期纳入披露区） |
| **context_builder**：自动挂 P5-a 防守 Effect + 把阵营军队规则/分队/CP 战略**列名**成 `toggles_available` | **P5** | ✅（列名，不 fake-apply 效果） |
| **少量通用效果的手工核验 DSL**（如 Go to Ground = 掩体+Stealth）behind 显式 toggle | **P5** | ✅ 每条单独手算核验，≤5 条 |
| **Streamlit 模拟器面板**（⚔️ 页签：选单位/装配/态势/防守开关 → 分布图+漏斗+性价比+诚实披露） | **P5** | ✅ 引擎薄壳 |
| **试点阵营全套专属技能 DSL 编码**（军队规则/分队/CP 战略逐条译成正确 Effect） | **P7 滚动** | ❌ 数据条件化、需逐条人工核对，自动编码高造假风险；本期只 surface 名字 |
| **首领依附 / 光环范围结算 / 载具搭载 Firing Deck** | **P6+** | ❌ 需空间/依附建模 |
| 军表验证 / 点评 / 威胁矩阵 | **P6** | ❌ |
| 网站化（FastAPI + Next.js） | **P8** | ❌ |

**一句话边界**：P5 = "真判谁先打 + 把每个单位的技能诚实分类披露 + 干净防守子集自动算 + 其余开关化 + 面板"。凡需要"逐条把阵营技能译成正确算式"的，明确留 P7 滚动、本期不假装完成。

---

## 二、abilities 分类器（`engines/simulator/abilities.py`，零依赖纯逻辑 + profile 侧装载）

### 分类桶（每个单位的每条技能落一个桶）

| 桶 | 判定（name_en / text 模式） | 产出 |
|----|------|------|
| `toggle_defensive` | **Feel No Pain X+**（抽 X + 条件标注 while/against/aura/within）、**Stealth**（-1 射击命中）、减伤（reduce…Damage…by 1）、掩体/+1 saves 类 | → surface：名字+解析参数+条件，默认**不**施加；面板/options 一键启用后引擎正确建模 |
| `nm_targeting` | Lone Operative / Stealth-作为选取限制 / 「can only be selected as target if…」 | → not_modeled（选取规则，单场景不涉及） |
| `nm_deployment` | Scouts / Infiltrators / Deep Strike | → not_modeled（部署/移动） |
| `nm_morale` | Synapse / Shadow in the Warp / Battle-shock 类 | → not_modeled（士气，P4 已声明不建模） |
| `nm_ondeath` | Deadly Demise X | → not_modeled（死亡爆炸，需多单位战场） |
| `nm_aura_leader` | Leader / Aura 授予他人 / 「while within N"」 | → not_modeled（依附/光环范围，P6+） |
| `nm_other` | 其余未匹配 | → not_modeled（原文名列出，不静默吞） |

### 关键实现约束（防假实现）

1. **无 auto_defensive 自动施加**：零节二次实测证伪"无条件 FNP 子集"（Meganobz "While the Waaagh!…" 会被误判），**FNP/Stealth/减伤一律进 `toggle_defensive`，默认关**。invuln 唯一 auto，走 P4 `load_target` 已有通道（分类器只把它列入披露区）。
2. **值+条件解析**：`Feel No Pain\s*(\d)\+` 抽 X；文本含 `while` / `against` / `aura` / `within` / `psychic` / `mortal` → 附条件标注（`是否无条件` 标 False）；抽不到值 → 记 `参数未解析`，不猜默认。Stealth 检测按文本含独立 "Stealth" 能力句。启用后引擎施加 `Effect("hit","modify",(-1,),("phase_shooting",))`（仅射击，近战不生效）。
4. **HTML 清洗**：`text_zh` 是 Wahapedia HTML，先 `re.sub('<[^>]+>','')` + `html.unescape`。
5. **披露真实**：分类器产出 `AbilityClassification`（auto_effects / toggle_effects / not_modeled_by_category），供 context 汇成报告；**禁止空列表糊弄**——3607 条挂载技能必须全部落桶。

### 引擎侧新增接缝（sequence.py 最小扩展）

P4 的 `_gather_params` 只读**攻方武器** Effect。Stealth 是**守方**授予的、改**攻方**命中的 Effect。新增：`run_sequence` 在 `_gather_params` 后，把 `target.effects` 里 `phase=="hit"` 且 `condition==("phase_shooting",)` 的 modify 值并入攻方 `hit_mod`（仍受 ±1 上限夹取）。这是唯一的引擎改动，其余防守 Effect（fnp/damage_reduction）沿用 P4 已有的 `_target_effect_value` 通道。

---

## 三、战斗顺序判定器（`engines/simulator/fight_order.py`，纯规则有限状态机）

十版战斗阶段（Fight phase）先攻顺序是**可枚举的确定规则**，零数据依赖，高置信度。规则（现行核心规则 Fight phase「Fights First」）：

```
Fight phase 分两步依次结算：
  Step 1「Fights First」：具备下列任一的单位先打——
       · 本回合冲锋成功的单位（charged this turn）
       · 拥有 Fights First 能力的单位
     若两边都有资格，从【当前玩家（active player）】的单位开始交替选取结算。
  Step 2「Everyone else」：其余单位，同样从 active player 开始交替选取结算。
  例外「Fights Last」：拥有 Fights Last 的单位放到最后（即使冲锋也不先打）。
  打断「Counter-offensive」战略（2CP）：非当前玩家可在【对方结算完一个单位后】
     立刻选自己一个合格单位插入结算（把它从队列提前）。
```

### 契约与 API

```python
@dataclass(frozen=True)
class FighterState:
    name: str
    is_active_player: bool     # 是否当前回合玩家（谁的回合）
    charged: bool = False      # 本回合是否冲锋成功
    fights_first: bool = False # 是否有 Fights First 能力
    fights_last: bool = False  # 是否有 Fights Last 能力

@dataclass(frozen=True)
class FightVerdict:
    order: Tuple[str, ...]     # 先攻→后攻的单位名序列
    first_striker: str         # 谁先打
    simultaneous_risk: bool    # 是否存在"对方能在你之前/交替打"的风险
    rationale: str             # 中文判定说明（引用规则步骤）
    rule_refs: Tuple[str, ...] # 规则页/USR 页引用锚点
    counter_offensive_note: str # Counter-offensive 可否改变结论的提示

def judge(a: FighterState, b: FighterState,
          counter_offensive_by: Optional[str] = None) -> FightVerdict: ...
```

判定分层：先按 (fights_last) 降级到最后，再按 (charged or fights_first) 分入 Step1/Step2，同层从 active player 起交替。`counter_offensive_by` 给定时，模拟该单位插队后的序列并在 note 里说明差异。**每条分支一组单测**（双方都冲锋、一方 fights_first 一方冲锋、fights_last 覆盖冲锋、counter-offensive 打断、非当前玩家单位不能主动先打等）。

### 与 simulate_matchup 的联动（升级 P4 近似）

P4 的 `simulate_matchup` 写死"A（攻方）先打，B 幸存者反打"。P5 让 `judge` 先定谁先打：
- 若判定 **A 先打** → 维持 A→B、B 幸存反打（现状）。
- 若判定 **B 先打**（如 B 有 Fights First 而 A 只是普通冲锋且…实际冲锋方总先打，故 B 先打只发生在 B 冲锋 / B fights_first 且 A 无）→ 交换：B→A、A 幸存反打。
- `bias_notes` 更新：把 P4 那条"Fights First/交替/interrupt 未建模"改为"已按 fight_order 判定先攻方；交替选取与 Counter-offensive 的逐单位插入仍以整单位近似"。

---

## 四、context_builder 组装（`context.py` 扩展，surface-don't-fake）

`build_context(attacker, target, stance, options)` 扩展为：

1. **自动挂载**：`invuln` 由 P4 `load_target` 已自动读入（唯一 auto 防守数值）；`abilities.classify(target)` 的 `auto_defensive` 桶**本期仅含 invuln 披露**，FNP/Stealth 不自动挂（见零节裁决）。
2. **surface toggles**：把 `toggle_defensive` + 该单位所属阵营的 army rule 名 + options 里未指定的分队/CP 战略名，汇入 `SimContext.toggles_available`（`(名字, 一句话, 是否已解析出参数)` 三元组）——**只列名与提示，不施加效果**。
3. **精确 not_modeled**：`abilities.classify` 的各 not_modeled 分桶 → `SimContext.not_modeled`，格式 `"未建模·<类别>：技能A、技能B…"`，取代 P4 的单行笼统声明。
4. **手工核验通用效果**（≤5 条，behind 显式 options 开关，每条 spec 附手算）：
   - `go_to_ground`：Infantry 单场景开关 → 掩体 Effect + Stealth(-1 射击命中) Effect。
   - `armour_of_contempt`（若建模）：暴击致伤/暴击命中降级——**评估后若语义复杂则不做，列 toggle**。
   - 其余一律 surface，不编码。

**scope 纪律**：任何需要"逐条判断阵营技能语义正误"的编码，本期不做（P7 滚动）。context 只做"自动挂干净子集 + 诚实列名 + 少数手算核验开关"。

---

## 五、Streamlit 模拟器面板（`ui/simulator_panel.py` + `app.py` 加 `st.tabs`）

**解耦纪律（承蓝图第八节）**：面板是**引擎薄壳**，只调 `agent.tools.simulate_combat`（已含实体解析+装配+三失败路径），不复制任何模拟逻辑，不 import engines.* 的内部。app.py 现为单页聊天（843 行，近 800 行软上限）——面板落**独立模块** `ui/simulator_panel.py`，app.py 用 `st.tabs(["💬 聊天","⚔️ 模拟器"])` 包裹，避免膨胀 app.py。

面板控件：
- 攻方单位名（文本框，实体解析）→ 解析出武器池 → 多选 loadout（武器:数量）；守方单位名。
- 态势开关：phase(shooting/melee)、冲锋、半射程、掩体、静止、远距离、间接火力。
- 防守开关：由 `abilities.classify` 预填（auto 默认勾选、toggle 默认不勾），FNP/减伤数值可调。
- 迭代次数 n（默认 8000）、seed。
- 「开始模拟」→ 调 simulate_combat → 渲染：
  - **分布直方图**（matplotlib，字体 **Microsoft YaHei**，承本机中文渲染纪律）：击杀数分布 + p10/p50/p90 竖线。
  - **阶段漏斗表**：attacks→hits→wounds→unsaved→damage→kills。
  - **性价比**：每 100 点伤害/击杀。
  - **诚实披露区**：`modeled_effects`（绿）/`not_modeled`（灰，分类）/`bias_notes`（黄）。
  - 反打（若填了守方 loadout）：并列第二组数字。
- **失败路径显式**：ambiguous → 列候选让用户点选；loadout_required → 列武器池；not_found → 提示换名。**不静默取第一个**。

UI 偏好（承 opus-boost 第四节）：不用 emoji 当功能图标（页签图标可保留）、企业级质感、红色强调节制。

---

## 六、模块结构与依赖方向

```
engines/simulator/
├── abilities.py     # 【新】纯逻辑分类器 + AbilityClassification 契约；profile 侧装载技能行
├── fight_order.py   # 【新】纯规则先攻判定；只 import 自身契约（零外部依赖）
├── context.py       # 【改】build_context 挂 auto 防守 + surface toggles + 精确 not_modeled
├── sequence.py      # 【最小改】run_sequence 并入 target 侧 hit 修正（Stealth）
├── engine.py        # 【改】simulate_matchup 用 fight_order 定先攻方
├── profile.py       # 【改】load_target 装载单位 abilities 行（新增 load_abilities）
└── （contracts/parse/keywords/assembly/cli 沿用 P4，cli 加 fight-order 展示）
ui/
└── simulator_panel.py   # 【新】Streamlit 面板（引擎薄壳）
app.py               # 【改】st.tabs 包裹聊天 + 模拟器面板（最小侵入）
agent/tools.py       # 【改】judge_fight_order 桩 → 接 fight_order.judge；TOOL_SPECS 描述更新
tests/
├── test_simulator_abilities.py   # 分类器分桶 + FNP 条件陷阱 + Stealth 施加
├── test_simulator_fight_order.py # 先攻判定全分支
└── （现有 test_simulator_* 保持绿）
```

**依赖硬约束**：`fight_order.py` / `abilities.py`（纯逻辑部分）**只依赖标准库 + 自身契约**，可脱库单测；装载 abilities 行在 `profile.py`（唯一碰 sqlite 处）。`ui/simulator_panel.py` 只 import `agent.tools` + matplotlib/streamlit，不碰引擎内部。Python 3.9：`Optional[...]` 不用 `|`，`from __future__ import annotations`。

---

## 七、验证体系（防假实现，承 P4 第九节）

1. **fight_order 全分支单测**：双冲锋/单侧 fights_first/fights_last 覆盖冲锋/counter-offensive 插队/非当前玩家不能主动先打/都不冲锋（active 先） —— 每条断言 order + first_striker。
2. **abilities 分类器黄金样本**：从真实 DB 抽 ~15 个代表单位（Meganobz 无条件 FNP、Painboy 光环 FNP、Librarian 条件 FNP、有 Stealth 的单位、Lone Operative、Deadly Demise、Synapse），断言每条技能落**正确桶**——尤其 **T1 陷阱专项**：条件 FNP 必须进 toggle 不进 auto。
3. **Stealth 端到端**：构造守方带 Stealth Effect，跑 `run_sequence` shooting，命中率较无 Stealth 下降一档（-1）；melee 不变。数值对拍手算命中期望。
4. **裸调目检**（承 opus-boost）：分类器上线前，对全库 3607 条挂载技能跑一遍分桶，打印各桶计数 + 抽样 20 条人工目检，确认**无静默丢技能**（各桶之和 == 3607）。
5. **面板**：本机 streamlit 跑起来，对一个已知对位（如 P4 CLI 验过的兽人打终结者）目检分布图/漏斗/披露区与 CLI 数字一致（面板只是壳，数字必须等同 CLI）。
6. **回归**：P4 全套 test_simulator_* 保持绿；`agent.tools` 现有测试保持绿；全库测试计数只增不减。
7. **诚实断言**：not_modeled / toggles_available / bias_notes 必须真实反映，禁止空列表；simulate_matchup 的先攻判定必须与 fight_order.judge 一致（同一函数，不重复实现）。

---

## 八、里程碑（P5 内部拆 chunk，每步独立 commit + devlog，ADHD 友好）

| # | 内容 | 完成判据 |
|---|------|---------|
| **P5-a 分类器+Stealth** | `abilities.py` 分桶 + `profile.load_abilities` + `sequence` 并入守方 hit 修正 + `context` 精确 not_modeled | 全库 3607 条零丢分桶（各桶和==3607）；FNP 条件陷阱专项单测绿；Stealth 端到端命中降档 |
| **P5-b fight_order** | `fight_order.py` 判定 + `engine.simulate_matchup` 用其定先攻 | 全分支单测绿；matchup 先攻方与 judge 一致；bias_notes 更新 |
| **P5-c context 组装** | `build_context` 挂 auto 防守 + surface toggles + ≤5 条手算核验开关 | auto/​toggle/not_modeled 三清单真实；go_to_ground 手算核验；scope 未越界（阵营技能只列名） |
| **P5-d 面板** | `ui/simulator_panel.py` + `app.py` st.tabs | streamlit 跑通；面板数字==CLI；失败路径显式；中文图渲染正常 |
| **P5-e 接线+验收** | `judge_fight_order` 接 fight_order + CLI + 门控确认 + 对抗性复审 | judge 工具端到端；「谋」门控覆盖；全库测试绿；对抗性复审无 HIGH 遗留 |

依赖：P5-a →（并行 P5-b）→ P5-c → P5-d → P5-e。

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| **FNP 条件化误施加（T1，最高造假风险）** | auto 桶仅收无条件自带；条件/光环一律 toggle；分类器黄金样本专项断言；宁漏不错 |
| **阵营技能 scope 膨胀成假编码** | 硬划线：本期只 surface 名字，逐条 DSL 编码留 P7；手算核验开关 ≤5 条且每条附手算 |
| **fight_order 规则记错** | 规则固化进单测 + 规则版本戳；引用现行核心规则 Fight phase；独立 rules-domain 复审 |
| **面板复制引擎逻辑（架构腐化）** | 面板只调 simulate_combat；"面板数字==CLI"作为验收断言，逼其做纯壳 |
| **app.py 膨胀 / set_page_config 二次触发** | 面板独立模块；st.tabs 不重复 set_page_config；tabs 内不再调页面级配置 |
| **静默丢技能** | 分桶各桶和==3607 断言；nm_other 兜底列原名 |

---

## 自审清单

- [x] 数据就绪度实测非应然，逮到 FNP 条件化陷阱 T1 并据此收敛 auto 范围（承 P4 C1 教训）
- [x] P5/P6/P7 边界硬划线（阵营技能逐条 DSL 编码明确留 P7，本期只 surface）
- [x] fight_order 是纯规则有限状态机，零数据依赖，全分支单测
- [x] auto 收敛到唯一干净项 invuln；FNP/Stealth/减伤 全 opt-in（二次实测证伪"无条件子集"），诚实披露
- [x] 面板是引擎薄壳，"数字==CLI"防架构腐化
- [x] 依赖方向硬约束（纯逻辑脱库单测、装载归 profile、面板不碰引擎内部）
- [x] 适配 Python 3.9（Optional 非 `|`）；测试遵扁平惯例、无 YAML
- [x] 每里程碑独立 commit+devlog、可回退；对抗性复审收尾
