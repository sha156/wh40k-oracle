# P4 蒙特卡洛对战模拟引擎 —— 立项设计（spec v2）

日期：2026-07-09
状态：已据独立评审就地修订（v1→v2，2026-07-09）
前置依赖：P0-P2 已落地（[数据架构定论](../../data-architecture-2026-07-09.md)：数值走 sqlite、别名走 aliases 表、L3 已重建）
关联文档：[v2 蓝图第五节 L4-1](2026-07-04-40k-universe-ai-v2-design.md)（本 spec 是其 P4 展开）、[本 spec 的独立评审报告](2026-07-09-p4-monte-carlo-simulator-review.md)（三方评审：架构/事实核查/规则域，v2 的每处改动都可回溯到该报告）
规则版本锁定：**十版（10th edition），现行 Balance Dataslate**。横跳过的词条（尤其 DEVASTATING WOUNDS）以本项目现行勘误源 `data_refined/10版40K通用技能速查表1.08` + 现行 dataslate 为准；`data_refined` 的**英文核心规则是发售版，已过时，不作规则真源**（详见第七节纪律）。

## v1→v2 主要修订（评审吸收）

- 🔴 **C1**：承认"模型数量 + 武器装配 loadout"不在库（`weapons` 是无数量选项池、`models.count_options_json` 全库空），新增**装配层**，headline 收敛到"单模型单位 + 手动 loadout 多模型单位"。
- 🟠 **效果契约**：新增零依赖 `contracts.py` + 通用 `Effect`（按 phase 分桶）通道，武器词条与防守开关都表示成 Effect，避免 P5 重写 `sequence.py`。
- 🟠 **规则订正**：DEVASTATING WOUNDS 精确化（跳含 invuln、致命伤 max 1 模型不溢出、FNP 仍生效）、删除杜撰的"冲锋命中惩罚"、掩体补"Sv≤3+ 对 AP0 不享受"、conversion 改为暴击命中阈值下调、wound 阶段补自然骰、allocate 补"已损伤模型优先"。
- 🟠 **意图路由**：模拟归"谋"档（非"算"），并把"谋"补进零工具门控。
- 🟡 一批事实订正：bs_ws 是裸数字+`N/A`、骰子含 `4D6`、补 `indirect fire`、词条参数支持骰子式、94 个混编单位/76 组同名双 profile 处理、`DiceExpr` 声明式、测试扁平命名无 YAML 等。

---

## 一、这一版要解决的问题

蓝图路线图 P4 一行话：**"攻击序列 pipeline + 武器词条自动解析 + 通用 USR 原语 + 黄金用例 → 基础'谁打谁'模拟上线（暂不含阵营专属技能）"**。

用户口径叫 **"谁冲谁能赢"**：给定攻方单位、守方单位、一组态势开关（冲锋/掩体/半血/距离），
逐骰模拟十版标准攻击序列 N 次，输出期望伤害、期望击杀、团灭概率、阶段漏斗、交换比，
并**诚实标注**哪些技能/机制未计入。

本 spec 只覆盖 **P4**。它是一个纯 Python 库（`engines/simulator/`），不 import 任何 UI，
把现有 `agent/tools.py:simulate_combat`（第 241 行）的 `_not_modeled` 桩替换成真实实现。

---

## 二、范围边界（P4 做 / 不做，硬划线）

### headline 能力范围（C1 决议后收敛）

| 场景 | P4 状态 |
|------|--------|
| **单模型单位**（角色/载具/怪兽，无装配歧义） | ✅ 保证 |
| **多模型单位 + 手动指定 loadout**（`options` 传 `{models:N, loadout:[(武器,数量)]}`） | ✅ 保证 |
| **多武器单位的自动默认装配**（从库推断"这 10 个模型各拿什么武器"） | ⚠️ **不保证**，留后续（Wahapedia wargear 是无数量选项池，推不出默认装配；BSData 默认选择是增强项） |

### 能力归属

| 能力 | 归属 | 状态 |
|------|------|------|
| 十版逐骰攻击序列（射击 + 近战通用流程） | **P4** | ✅ |
| 装配层：解析每档模型数（`points_json.items[].desc` 的 "N models"）+ 手动 loadout 组装 | **P4** | ✅（C1 新增，P4-a 硬子目标） |
| 武器词条自动解析成 Effect（rapid fire / sustained / lethal / dev wounds / anti-X / twin-linked / blast / melta / torrent / heavy / lance / precision / pistol / assault / hazardous / extra attacks / ignores cover / one shot / conversion；见第四节） | **P4** | ✅（从 `weapons.keywords_json` 零人工提取） |
| `indirect fire`（139 次核心词条） | **P4** | ✅ 建模（命中 -1 等效 + 目标获掩体；见第四节） |
| 通用 USR 原语**防守侧手动开关**：FNP(X)、invuln（models 表自动读）、伤害削减、掩体 | **P4** | ✅（作为 `options` → Effect；自动从 abilities 表提取留 P5） |
| numpy 向量化万次迭代 + 分布/漏斗/交换比输出 | **P4** | ✅ |
| 黄金用例校验集 + 与 UnitCrunch 抽样对照 | **P4** | ✅ |
| `simulate_combat` 工具接线 + 最小 CLI 入口 | **P4** | ✅ |
| **阵营专属技能 / 军队规则 / 分队规则自动挂载**（effect DSL 编码） | **P5** | ❌（abilities 表 3677 条**全部** `dsl_status=not_modeled`，DSL 层 0%，是 P5 主体） |
| **战斗顺序判定器** `fight_order.py`（先手/interrupt/fights first） | **P5** | ❌（本期"谁冲谁"用串行幸存反打近似，见第八节） |
| **CP 技能 / 首领光环 / 分队强化的自动上下文组装** | **P5** | ❌（`context_builder` 的 faction/detachment join 是 P5） |
| **自动默认 loadout 推断 / BSData 组军约束** | **P5/P6** | ❌ |
| Streamlit 模拟器面板 | **P5** | ❌（P4 只出库 + CLI） |
| 军表验证 / 点评 / 威胁矩阵 | **P6** | ❌ |

**一句话边界**：P4 = "两个单位的裸数据 + 武器词条 + 手动 loadout + 少数手动防守开关，跑十版掷骰序列"。
凡需要"知道单位属于哪个分队、开了哪个 CP、光环覆盖没覆盖、默认拿什么武器"的，全部是 P5+。

---

## 三、数据就绪度盘点（实测 2026-07-09，`db/wh40k.sqlite`）

> v1 曾下"数据够跑基础模拟"的结论——**评审证伪，已订正**。数值骨架（单把武器 stat）够干净，但**"可开火单位的装配"（N 模型 × 各自武器 × 数量）缺失**，需装配层补。

### 够用的（单把武器/单模型属性）

| 输入 | 表/字段 | 实测形态 | 解析层要做的事 |
|------|---------|---------|------------------|
| 武器攻击数 A | `weapons.a`（9307 行） | 7729 整数 + **1578 骰子式**：`D6`(801) `D3`(254) `D6+3`(184) `2D6`(126) …含 `4D6`(3) | 骰子解析器 `NdM+K`（**N≤4**、M∈3/6、K≤8） |
| 武器伤害 D | `weapons.d` | 7747 整数 + **1560 骰子式** | 同上骰子解析器 |
| 武器强度 S / 穿甲 AP | `weapons.s` / `weapons.ap` | S：9304 整数 + 3 骰子(`2D6`×2/`D6+6`×1)；AP：9305 整数 + 2 个 `-` + 1 个 `-0` | 近似纯整数，骰子/`-`/`-0` 走兜底分支 |
| 命中 BS/WS | `weapons.bs_ws` | **裸数字**为主（`3`/`4`/`2`/`5`/`6`；带 `+` 全库仅 2 行）；无 BS 标记是 **`N/A`**(600，**100% 是 torrent**) | 直接取整；`N/A` → 自动命中（torrent 类），无 `-` 值 |
| 武器词条 | `weapons.keywords_json`（6568/9307 非空） | **单元素数组里逗号拼一坨** `["anti-infantry 4+, devastating wounds, rapid fire 1"]`；大小写混乱（`rapid`/`RAPID`/`pISTOl` 等 48 种变体，全库 0 个多元素数组） | 拆逗号 + lowercase 归一 + 带参解析（参数可为骰子式，见第四节） |
| 模型属性 M/T/SV/W/OC | `models`（1817 行） | M=`6"`（带引号）/`20+"`(95)/`-`(50)；SV=`4+`；W/OC 整数；T 有 `5*`(1) | 属性归一层：M 去 `"`、`20+"`/`-` 特判；SV 去 `+`；`*` 注脚剥离 |
| 无效保护 invuln | `models.invuln` | `-`(961，无) + 4/5/6 + 边缘 `2`(3)/`3`(1)/`4*`(2) | `-`→None；有值存优；`*` 剥注脚 |

### 缺的（装配 —— C1，装配层补）

| 输入 | 实况 | 装配层对策 |
|------|------|-----------|
| **每档模型数**（blast/团灭必需） | `models.count_options_json` **全库 0/1817 非空**；模型数只以自由文本存 `units.points_json.items[].desc` 的 `"10 models"`/`"5 models"` | 正则从 desc 抽每档模型数 |
| **武器 loadout**（哪些模型拿哪把、几把） | `weapons` 是**选项池**（Warboss 列 5 把互斥），无数量、无模型归属 | P4：**手动 `options.loadout`**；单模型单位可自动（选项池即其全部武器） |
| **多模型混编单位** | **94/1715** 个 unit 有 2-4 行异质 model（如 Kill Team T4/T5 混编） | 契约支持多 model 行（见第六节 `TargetProfile.model_rows`）；未指定时按主模型行 + 警示 |
| **同名多 profile 武器** | **76 组** `(unit_id,name_en)` 重复（远近双模式 `30"`/`Melee`） | `WeaponProfile.range` 字段 + 按 phase 过滤（`range=='Melee'` vs 数字射程）+ 去重策略 |

### 明确不碰

| 输入 | 实况 |
|------|------|
| 阵营技能 effect DSL | `abilities` 3677 条**全 NULL、全 `not_modeled`** → P4 全列入报告 `not_modeled` 清单，不建模 |
| 受损档效果 | `datasheets.damaged_w` 358 条有阈值（`1-4` 等，可机读），但效果在 `damaged_description` 自由文本 → P4 不建模，半血只作 models 数手动开关 |

**结论**：解析层 = 骰子解析器 + 属性归一器 + 武器词条归一器（三者有界可穷举）；**装配层** = 模型数解析 + 手动 loadout 组装。缺的是"技能语义"（P5）与"默认装配推断"（P5+），不是数值骨架。

---

## 四、P4 覆盖的武器词条原语（从 keywords_json 直取 → Effect）

一次性写好解析映射即全库生效。**每个词条产出一个 `Effect`**（第六节），而非硬编码进序列分支。
（频次为实测量级，仅供优先级参考；正确性靠规则语义。）

| 词条 | 语义（现行十版） | Effect.phase / 介入 |
|------|------|-----------|
| `rapid fire X`（967） | 半射程内 A+X | attacks（距离开关） |
| `sustained hits X`（676；X 可为 `d3`） | 暴击命中额外 +X 命中 | hit（crit 分支） |
| `lethal hits`（263） | 暴击命中**自动造伤**（跳造伤掷骰 → 不产生暴击造伤 → **不触发 dev wounds**） | hit→wound 短路 |
| `devastating wounds`（686） | 暴击造伤 → 见第七节精确语义（跳含 invuln、致命伤 max 1 模型、FNP 仍生效） | wound crit → 致命伤池 |
| `anti-X N+`（infantry 330 / vehicle 179 / fly 117 / monster / psyker / character / titanic / daemon…） | 对含 X 关键词目标，未修正造伤 N+ 即暴击造伤 | wound（crit 阈值下调，依目标 keyword）**通用解析非白名单** |
| `twin-linked`（833） | 造伤掷骰重骰失败 | wound（reroll） |
| `blast`（860） | 每满 5 个目标模型 +1 攻击（结算时模型数、向下取整；不可对接战目标用） | attacks（依守方模型数） |
| `melta X`（372） | 半射程内 D+X | damage（距离开关） |
| `torrent`（601） | 自动命中（`bs_ws=N/A`） | hit（跳过） |
| `heavy`（455） | 本方静止时命中 +1 | hit（态势开关） |
| `lance`（57） | 冲锋回合造伤 +1 | wound（态势开关） |
| `precision`（203） | 可点名附着角色 | allocate（**本期仅标注，不做角色分配，留 P5**；`not_modeled` 声明会低估斩首） |
| `pistol`（1066） | 交战中可射击 | 态势标注 |
| `assault`（403） | 前进后可射击 | 态势标注 |
| `hazardous`（405） | 用后每把掷 D6，出 1 一个模型受 3 致命伤 | 反向自伤分支（可选计入） |
| `ignores cover`（633） | 无视掩体（连 Stealth 类给的掩体一并禁用） | save（禁掩体加值） |
| `extra attacks`（162） | 额外武器攻击，不排他（其攻击数默认不可被改） | attacks（叠加） |
| `one shot`（200） | 每局一次 | attacks（数量夹取，标注） |
| `conversion`（16） | **目标完全位于 12"/24" 外时，未修正命中 4+ 即暴击命中**（下调暴击命中阈值，非 +1 命中、不占 ±1 预算） | hit（crit 阈值，依距离档） |
| `psychic`（343） | psychic 标签透传（供 anti-psyker 交互） | 标签透传 |
| **`indirect fire`（139）** | 无视线可射，但**命中 -1 且目标视为处于掩体** | hit（-1）+ save（掩体） |

**防守侧原语（P4 作为 `options` 手动开关 → Effect）**：`feel_no_pain(X)`、`invuln(X)`（models 表自动读）、`damage_reduction(X)`、`cover`。

未列入上表的一切阵营技能/军队规则 → **一律进 `not_modeled` 清单**，报告显式声明。低频专属词条（`bubblechukka`/`c'tan power` 等 ≤3 次）走 `unparsed_keywords` 兜底并记日志，不静默丢。

---

## 五、模块结构 `engines/simulator/`

```
engines/
├── __init__.py
└── simulator/
    ├── __init__.py
    ├── contracts.py      # 【零依赖】纯数据类：DiceExpr / Effect / WeaponProfile / AttackerProfile / TargetProfile / SimContext / SimReport
    ├── parse.py          # 脏数据 → 干净数值：骰子解析器 / 属性归一器 / 词条归一器
    ├── keywords.py       # 词条 → Effect 映射表（第四节那张表的代码化）
    ├── assembly.py       # 装配层：points desc 解析每档模型数 + 手动 loadout 组装 → AttackerProfile（C1）
    ├── profile.py        # 从 sqlite 装载：load_attacker / load_target（import sqlite3 + contracts）
    ├── context.py        # build_context(attacker, defender, options) → SimContext（P4：面板层+词条Effect+手动防守Effect；faction/detachment join 是 P5 占位）
    ├── sequence.py       # 十版攻击序列 pipeline（numpy 向量化，核心）——只 import contracts
    ├── report.py         # SimReport 组装：分布/漏斗/交换比/性价比/not_modeled
    ├── engine.py         # 顶层 simulate(attacker, defender, options, n=10000, seed=...) 编排
    └── cli.py            # 最小命令行入口（开发期自测用，非 UI）
tests/                    # 【扁平，遵现仓惯例，无子目录/无 YAML】
    ├── test_simulator_parse.py       # 骰子/属性/词条解析边界（含 4D6、N/A、20+"、-0 等脏值）
    ├── test_simulator_assembly.py    # 模型数解析 + loadout 组装
    ├── test_simulator_sequence.py    # 每个 Effect 一组单测
    └── test_simulator_golden.py      # 黄金手算用例（读 golden_cases.json）
tests/golden_cases.json               # 手算场景 + 期望值 + 容差（JSON，非 YAML）
```

**依赖方向硬约束**：`sequence.py`/`report.py` **只 import `contracts.py`**，绝不 import sqlite3/app/streamlit；装载在 `profile.py`、组装在 `assembly.py` 完成。这保证引擎脱库单测、P8 FastAPI 可直接复用。（v1 把数据类放 `profile.py` 会传递性 import sqlite3，已拆到零依赖 `contracts.py` 修正。）

**Python 3.9 注意**：venv 是 3.9.1，禁用 `int | None` 语法，一律 `Optional[int]` + `from __future__ import annotations`。

---

## 六、数据契约（`contracts.py`，零依赖纯数据）

```python
@dataclass(frozen=True)
class DiceExpr:                # 声明式，非采样器：由引擎向量化采样器解释，可哈希、可作缓存 key
    n: int = 0; faces: int = 0; k: int = 0   # NdM+K；常量记 n=0,faces=0,k=常量

@dataclass(frozen=True)
class Effect:                  # 武器词条与防守开关的统一表示；P5 的技能/CP/光环也产出同型 Effect
    phase: str                # attacks|hit|wound|save|damage|fnp
    op: str                   # modify|reroll|crit_threshold|extra_hits|auto_wound|skip_save|mortal_pool|fnp|damage_reduction|...
    params: tuple             # 声明式参数（可含 DiceExpr）
    condition: tuple = ()     # 生效条件（target_has_keyword=X / half_range / stationary / charging / ap0 …），组装器/引擎转开关

@dataclass(frozen=True)
class WeaponProfile:
    name_zh: str; name_en: str
    range: str                # 'Melee' 或 数字射程（同名双 profile 按此 + phase 过滤）
    attacks: DiceExpr
    bs_ws: Optional[int]      # None = 自动命中（torrent）
    strength: int; ap: int; damage: DiceExpr
    effects: tuple            # 第四节归一后的 Effect 列表
    count: int = 1            # 该 loadout 中持此武器的模型/武器数（装配层填）

@dataclass(frozen=True)
class AttackerProfile:        # C1 新增：可开火单位 = 模型数 + loadout
    name_zh: str; name_en: str; canonical_id: str
    models: int
    loadout: tuple            # tuple[WeaponProfile]（每个带 count）
    keywords: frozenset       # 供 lance/conversion 等态势判定与自身关键词

@dataclass(frozen=True)
class TargetProfile:
    name_zh: str; name_en: str; canonical_id: str
    models: int               # 满编模型数（态势可调半血档）——装配层从 points desc 解析
    t: int; sv: int; invuln: Optional[int]; w: int; oc: int
    keywords: frozenset       # 供 anti-X / blast 判定
    model_rows: tuple = ()    # 94 个混编单位：多 model 行；单一时空，引擎用主行 + 报告警示
    effects: tuple = ()       # options 手动防守开关（FNP/减伤/掩体）→ Effect

@dataclass(frozen=True)
class SimContext:
    attacker: AttackerProfile
    target: TargetProfile
    stance: "Stance"                    # 冲锋/静止/半射程/掩体/距离档
    effects: tuple                      # 【通用通道】按 phase 分桶的全部生效 Effect（词条+防守+态势）；P5 只往这里加生产者
    toggles_available: tuple            # 【纯 UI 提示】未挂载的可选增益（"若在X分队+1"），不承担效果挂载
    not_modeled: tuple                  # 已知但未建模的技能/机制名清单
    phase: str                          # 'shooting' | 'melee'

@dataclass
class SimReport:
    expected_damage: float; expected_kills: float; wipe_probability: float
    distribution: dict                  # {p10,p50,p90, histogram}
    funnel: dict                        # attacks→hits→wounds→unsaved→final 各阶段期望留存
    efficiency: dict                    # 每100点期望伤害/击杀（点数按【模拟的模型数选对应 cost 档】，非 min 档）
    reverse: Optional["SimReport"]      # 反向视角（守方按【幸存模型数】反打，见第八节）
    modeled_effects: list               # 本次计入的 Effect（诚实声明）
    not_modeled: list                   # 未计入清单
    bias_notes: list                    # 系统性偏差方向声明（见第八节）
    sensitivity_hint: list
    seed: int; iterations: int
```

---

## 七、十版攻击序列 pipeline（`sequence.py` 核心，规则已按现行 dataslate 订正）

逐阶段（每阶段规则固化为代码 + 单测；`np.random.default_rng(seed)` 可复现）：

```
① Attacks   解析 A（骰子采样）；rapid fire/blast/extra attacks/melta 按态势与目标模型数调整
② Hit       BS/WS 判定；命中修正上限 ±1；未修正 1 必失、未修正 6 必中；暴击命中默认未修正 6；
            sustained → 暴击额外命中；lethal → 记"自动造伤"标记（跳造伤掷骰）；
            conversion → 目标超 12"/24" 时暴击命中阈值降到 4+（占 crit 阈值，不占 ±1 预算）；
            torrent → 自动命中；heavy → 静止 +1；indirect fire → -1；
            【无近战冲锋命中惩罚——十版无此规则，v1 已删】
③ Wound     S vs T 查表（下方）；未修正 1 必失、未修正 6 必为暴击造伤（恒成功且触发 dev wounds）；
            anti-X → 按目标 keyword 下调暴击造伤阈值；twin-linked → 重骰失败；
            dev wounds 暴击 → 进致命伤池（见下）；lethal 自动造伤 → 跳本阶段（故不触发 dev）
④ Allocate  伤害分配：【已损伤模型必须优先继续承受分配至其死亡】，再换下一模型；
            一次攻击伤害不溢出到下一模型（十版规则）；precision 本期只标注（留 P5）
⑤ Save      取 min(Sv 经 AP 修正后, invuln) 之更优（数值越小越优）；
            掩体 → 护甲保护 +1，但【Sv 3+ 或更优的模型对 AP0 攻击不享受掩体】；
            ignores cover 禁掩体；invuln 不受 AP、不受掩体
⑥ Damage    每次未过保 D 值（骰子采样）；damage_reduction 后夹 ≥1；不溢出
⑦ FNP       每点伤害掷 FNP(X)，成功免伤（【含 dev wounds 致命伤——不可当致命伤跳过 FNP】）
   ── 致命伤池（dev wounds）：本单位其它攻击的正常伤害全部结算后，成池分配；
      每点造成 = D 致命伤，【忽视一切保护含无效保护 invuln】，【每次暴击造伤最多影响 1 个模型，溢出作废】，【FNP 仍逐点生效】
   → 记录本次迭代：造成伤害、死亡模型数、是否团灭
× N=10000 次迭代（numpy 向量化）
```

**S vs T 命中伤害查表（写死 + 单测，自上而下 if-elif）**：
```
S ≥ 2T → 2+ ；  S > T → 3+ ；  S = T → 4+ ；  2S > T 且 S < T → 5+ ；  2S ≤ T → 6+
```

**规则真源纪律（写死进本节）**：DEVASTATING WOUNDS / BENEFIT OF COVER 等被 dataslate 改过的词条，
**以 `data_refined/10版40K通用技能速查表1.08` + 现行 dataslate 为准**；`data_refined/Core Rules - New 40K Core Rules`
是**发售版英文核心**，其 DEV WOUNDS 24.10（旧版）与 COVER 13.08（被转录成"worsen BS by 1"的错误）**不作实现依据**。
十一版已发布，本项目锁定十版——规则版本号钉在文档，横跳词条改动时同步更新。

**numpy 向量化设计（去风险）**：
- 攻击维度有界（单武器单次 ≤ 数十），迭代维度大（N=1e4）。策略：对每个"攻击槽"在 **N 维上向量化**，
  在攻击槽维度上小循环（≤ 数十次）。命中/伤/保是 `(N, max_attacks)` 布尔/整型数组，掩码处理变长攻击数。
- 伤害分配（模型 W 桶、"已损伤优先"、不溢出）用沿攻击槽维度扫描 + 跨 N 并行累加当前模型剩余 W、
  归零即计一杀并重置的向量化累积实现。致命伤池单独一路结算。
- 逐点 FNP 需 `(N, maxA, maxD)` 三维（N=1e4、maxA~40、maxD~6 ≈ 2.4M cell，可接受）。
- **此分配核是全篇最高技术风险，P4-b 前先做一次性 spike 单独验证**（见第十一节）。万次迭代亚秒级，纯 numpy。

---

## 八、"谁冲谁能赢" 的编排（P4 近似，已去偏）

真正的"谁先打"是**有限状态的战斗顺序判定**（冲锋方先打 → fights first → 交替 → interrupt），属 P5 `fight_order.py`。
P4 用**串行幸存反打 + 交换比**近似回答"值不值得冲"：

```
simulate(A→B, phase=melee, stance=charging)   → A 打 B 的期望击杀与团灭率
simulate(B→A, phase=melee, stance=default,
         target.models = B 的【幸存模型数】)    → B 反打 A（reverse 字段）——把 A→B 击杀数扣掉再打
→ 交换比 = (A 造成的 B 点数损失) / (A 自身预期损失)
→ 结论："A 冲 B：期望干掉 B 的 x 个模型（团灭率 y%），代价是 A 被幸存者反打损失 z 点"
```

（v1 让守方**满编**反打，系统性高估守方反伤/低估冲锋价值——已改串行幸存反打去偏。）

**必须写进 `bias_notes` 的系统性偏差声明**（诚实优先）：
- 守方反打用"期望幸存数"而非逐迭代联动，仍略高估（近似而非精确顺序结算）；
- **冲锋成功率未建模**：默认冲锋必接触，未算 2D6 冲锋距离检定失败概率 → 高估"冲"的价值；
- Fights First / 交替 / interrupt 缺失（P5）；
- 士气/Battle-shock（半血触发、OC 归 0）、接战范围/视线/射程可达性、守方最优分配（模拟用固定分配）均未建模；
- 交换比按"击杀模型→点数"折算，多耐伤单位被打残未死的部分点损失不计入。

---

## 九、验证体系（防假实现的核心）

1. **黄金手算用例集**（`tests/golden_cases.json`，~30-50 例，容差 <1%）：
   - 基础射击：10 火战士脉冲步枪（S5 vs T5=4+）齐射 5 终结者（2+ 甲）
   - 基础近战：兽人 Power klaw（S10 AP-2 D2）打 T5
   - 每词条**单独**生效一例：rapid fire 半射程、sustained(含 `d3` 参数)、lethal、anti-vehicle、twin-linked、blast(对满编)、melta 半射程、conversion 远距离暴击、indirect fire
   - **规则订正专项用例**（评审新增）：① dev wounds 暴击**跳 invuln**（4++ 目标照样吃满 D 致命伤）；② dev wounds 致命伤**不溢出**（D3 暴击对 1W 模型只死 1 个）；③ **lethal + dev 同武器**（lethal 自动造伤 → **不触发 dev**）；④ 掩体 **Sv3+ 对 AP0 不享受**、对 AP1 享受；⑤ **多耐伤×低D 分配**（D1 打满编 3W 模型，验"已损伤优先"）；⑥ 未修正 6 造伤恒暴击触发 dev
   - 防守开关：FNP 5+（对含 dev 致命伤也生效）、invuln 4++ 对高 AP、掩体 +1
   - S vs T 查表五档边界各一例
2. **与社区工具抽样对照**：5-8 个常见对位与 UnitCrunch 比期望伤害，偏差 >2% 立案。
3. **每个 Effect 一组单测**；组合场景集成测试；随机种子固定复现。
4. **反假实现纪律**（遵 opus-boost 验证纪律）：解析器上线前先裸调——打印 10 个真实武器 keywords 解析结果 + 10 个单位装配结果人工目检，确认无"静默丢词条/漏装配/大小写漏匹配"；`not_modeled`/`unparsed_keywords`/`bias_notes` 必须真实反映跳过项，禁止空列表糊弄。

---

## 十、集成点

- `agent/tools.py:simulate_combat`（第 241 行 `_not_modeled` 桩）→ 替换为调 `engines.simulator.engine.simulate`；
  入参 `(attacker, defender, options)` 经 `entity_resolver` → canonical id → `profile.load_*`。
  `judge_fight_order`（第 237 行）**保持 P5 桩不动**。
- **意图路由订正**（评审 ❌4）：模拟类问题（"谁冲谁能赢"）实际归 **"谋"** 档（`llm_client.py:45-53`：谋=战术推演/模拟对战/谁能打赢），**不是"算"档**。且 `loop.py:26 _MUST_VERIFY_INTENTS=("查","判","算")` **不含"谋"** → 接线后 LLM 可凭记忆直接答"谁能赢"、永不调 simulate_combat 且无拦截。**接线时必须把"谋"加入门控**（或改意图分类把模拟归入受控档）。
- **CLI 三失败路径**：`entity_resolver` 可能返回 ambiguous（如 `"终结者"` → 多候选无 canonical_id）/ none / fuzzy 错配，接线层与 CLI 须分别处理并提示（不静默取第一个）。
  示例：`python -m engines.simulator.cli "兽人 Warboss" "终结者小队" --phase melee --charge`（用可精确解析的单位名）。
- 点数从 `calc_points` 带入性价比，但 **efficiency 按模拟的模型数选对应 cost 档**（非 `min(items.cost)`）。

---

## 十一、里程碑（P4 内部拆 chunk，每步有可验证产出，ADHD 友好）

| # | 内容 | 完成判据 |
|---|------|---------|
| **P4-a 解析+装配层** | `parse.py` 三解析器 + `assembly.py`（模型数 + loadout）+ `profile.load_*` | ① 全库 9307 武器 / 1817 模型解析零异常（含 4D6/N/A/20+"/-0 脏值），抽样目检；② **给单位名+档位 → 产出 N 模型×武器数量表**（单模型单位自动、代表性多模型单位手动 loadout）；`test_simulator_parse/_assembly` 绿 |
| **[spike] 分配核** | 一次性验证 numpy 伤害分配核（不溢出 + 变长 D + 已损伤优先 + 逐点 FNP + 致命伤池） | 手算对拍 3-4 个分配场景，误差 0；确认三维数组内存与性能可接受 |
| **P4-b 裸序列** | `sequence.py` 无词条纯序列 + S/T 查表 + 掩体/allocate/dev 池正确 | 基础射击/近战 + 规则订正专项黄金用例 <1% 误差 |
| **P4-c 词条→Effect** | `keywords.py` + 第四节 20 词条 + indirect fire 介入序列 | 每词条单独 + 组合（lethal+dev、anti+dev）黄金用例通过；`not_modeled`/`unparsed` 真实 |
| **P4-d 报告层** | `report.py` 分布/漏斗/交换比/性价比 + 串行幸存反打 + efficiency 按档 | SimReport 字段齐全含 bias_notes，UnitCrunch 抽样对照 <2% |
| **P4-e 接线** | `tools.py:simulate_combat` 接线 + CLI + 意图"谋"门控 + 三失败路径 | CLI 端到端；"谋"意图零工具 final 被拦截；Agent 回答带诚实声明；全套单测绿 |

依赖：P4-a →（spike）→ P4-b → P4-c → P4-d → P4-e 线性；每 chunk 独立可用可回退。

---

## 十二、风险与应对

| 风险 | 应对 |
|------|------|
| **装配数据缺失（C1）** | headline 收敛到单模型 + 手动 loadout；装配层从 points desc 解析模型数；自动默认 loadout 明确留 P5 |
| keywords_json 脏（大小写/逗号/带参含骰子式） | 归一层 lowercase + 逗号拆 + 通用带参正则（参数支持 `d3`）；未识别记 `unparsed_keywords` 不静默丢；上线前目检 |
| 骰子长尾（`4D6`/`D6+8`/`-0`） | 通用 `NdM+K` 正则（N≤4、K≤8）+ 兜底分支；全库跑一遍收未匹配集补规则 |
| **规则记错（自洽地错）** | 全部固化进 S/T 查表 + 规则订正专项黄金用例 + UnitCrunch 对照；规则真源纪律写死（速查表/dataslate 优先，发售版英文核心不作依据）；规则版本号钉文档 |
| 效果表示逼 P5 重写 | `Effect` 通用通道 + 每阶段"收集并施加所有 Effect"接缝，P5 只加生产者 |
| scope 膨胀（误纳 P5 技能） | abilities 表一律 `not_modeled`；防守开关仅 4 个机制确定的通用原语，手动传入 |
| 分配核（主技术风险） | P4-b 前独立 spike 验证；黄金用例覆盖不溢出/已损伤优先/致命伤池 |
| 反假实现 | 裸调目检 + `not_modeled`/`bias_notes`/`unparsed` 真实 + 黄金用例容差断言，禁止"跑通即完成"自我宣称 |

---

## 自审清单

- [x] 数据就绪度是实测非应然，**已订正 v1 的"数据够跑"错误结论**（承认装配缺口）
- [x] P4/P5/P6 边界硬划线（abilities DSL、fight_order、面板、军表、默认装配全部明确划出）
- [x] 与 v2 蓝图 P4 定义一致（词条自动解析 + 通用 USR + 黄金用例，不含阵营技能）
- [x] 引擎（sequence/report）只 import 零依赖 contracts，可脱库单测、P8 可复用
- [x] 效果统一为 `Effect`，P5 平滑扩展不重写 sequence.py
- [x] 规则按现行 dataslate 订正（dev wounds/掩体/conversion/自然骰/allocate/无冲锋惩罚），规则真源纪律与版本戳写死
- [x] "谁冲谁"近似去偏（串行幸存反打）+ 系统性偏差方向诚实声明
- [x] 意图路由归"谋"并补门控，接线不放水
- [x] 每里程碑有可验证产出与回退空间；主技术风险单独 spike
- [x] 适配本机 Python 3.9（Optional 而非 `|`）；测试遵扁平惯例、无 YAML 依赖
