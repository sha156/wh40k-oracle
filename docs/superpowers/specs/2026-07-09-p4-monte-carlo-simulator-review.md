# P4 蒙特卡洛模拟引擎 spec —— 独立评审报告

日期：2026-07-09
评审对象：[2026-07-09-p4-monte-carlo-simulator-design.md](2026-07-09-p4-monte-carlo-simulator-design.md)（spec v1）
方法：三个独立视角代理并行（架构评审 / 对库事实核查 / 十版规则域审计），结论交叉合并去重
状态：**已据本评审就地更新 spec → v2**（用户定：直接改 v1）。本报告转为 v2 的修改依据/变更理由存档。
用户已拍板的裁决：**C1 采「加装配层 + 缩 headline」方案**（见下 C1 节 → 决议）

> 规则域审计代理跑到一半因 Fable 5 额度中断，该块由主 Opus 手动对 `data_refined` 核心规则原文核完（见 H-B / MEDIUM 5·6 的页码引用）。

---

## 总判断

**spec 方向正确，但不能直接开工。** 一个击穿性数据缺口（C1）+ 三条高危设计/规则问题（H-A/B/C/D）+ 一批事实订正（MEDIUM 1-12）。
其中 C1 与 H-A（效果契约）会决定"造出来跑得动但答不对 / 半年后 P5 推倒重来"，是产 spec v2 前必须吸收的。

已核对**无误**的部分（不必改）：weapons 9307 / models 1817 / abilities 3677 行数、a/d 列骰子分布、keywords_json 拼接格式、abilities 全 `not_modeled`、S vs T 五档查表、集成点行号 `tools.py:241 simulate_combat` / `237 judge_fight_order`、entity_resolver 返回结构可直接 join、ANTI/BLAST 词条语义与 Core Rules 原文一致、numpy 1.26.4 / Python 3.9.1。

---

## 🔴 CRITICAL

### C1 单位「模型数量 + 武器装配 loadout」根本不在库里
**来源**：架构评审 C1 + 事实核查 ⚠5/⚠7 + M1（三方独立指认同一缺口）。

证据（源 CSV / 库，非应然）：
- `weapons` 表是**武器选项池**：Warboss(`000000001`) 列 5 把武器，一个模型不可能同时挥 big choppa + power klaw；**无数量列、无模型归属列**。
- 单位「有几个模型」只以自由文本存在 `units.points_json.items[].desc` 的 `"10 models"` 里；`models.count_options_json` 列**全库 0/1817 非空**（`build.py:104-113 _insert_models` 从未写入该列）。
- `calc_points`（`calc_points.py:20-31`）取 `min(items.cost)` 最小档价 → 模拟 10 模型却拿 5 模型点数算性价比，efficiency 错约一倍。

后果：`profile.load_from_db` 造不出正确 SimContext；旗舰黄金用例"10 火战士齐射"里的"10"和"每模型 1 把脉冲枪"都无法从库自动装配；对多武器单位"全武器打一遍"会严重超算。**spec 第三节"数据够跑基础模拟"的结论是错的。**

**→ 决议（用户已定）：加装配层 + 缩 headline**
- P4-a 硬子目标新增**装配层**：(a) 从 `points desc` 正则解析每档模型数；(b) 定义默认 loadout 来源（Wahapedia wargear 不提供默认装配 → 先接受 `options` 手动指定 loadout，BSData 默认选择留作后续增强）。
- 契约引入 `AttackerProfile{models:int, loadout:list[(WeaponProfile, count:int)]}`；`WeaponProfile` 加 `carriers`/`count`。
- **headline 范围收敛**：✅ 单模型单位（角色/载具，无装配歧义）+ ✅ 手动传 loadout 的多模型单位；⚠️ 自动装配多武器单位 → 明确留后续，不列入 P4 验收。
- 同步修 spec 第三节结论 + M1 的 efficiency 按模拟模型数选对应 cost 档（与装配层同一块地基）。

---

## 🟠 HIGH

### H-A 效果表示会逼 P5 重写 `sequence.py`
**来源**：架构评审 H1 + H2。
- `SimContext.toggles_available: list[str]` 是**显示字符串**不是可执行效果；防守侧烧成 `TargetProfile` 标量（fnp/减伤/掩体）。P5 的军队规则/CP/光环是**开放集** modifier（命中+1、save+1、reroll 1s、暴击阈值改…），无法继续枚举成标量。pipeline 没有通用施加接缝 → sequence.py 重写。
- P4 新造的 `WeaponProfile.primitives` 与蓝图既有 `abilities.effect_dsl_json`（约 30 原语）是**两套并行效果表示**，P5 合流困难。

**→ spec v2 改法**：现在就给 `SimContext` 加通用 `effects: list[Effect]` 通道（按 phase 分桶 attacks/hit/wound/save/damage/fnp）；`sequence.py` 每阶段写一次"取本阶段所有 modifier，按规则叠加/夹上限"的循环。武器词条与防守开关都表示成 `Effect`，**与蓝图 DSL 原语同构**。P5 只新增 effect 生产者（faction join / CP / 光环）喂进同一 list，引擎每阶段施加循环一次写好、永不重写。`toggles_available` 降为纯 UI 提示。

### H-B Devastating Wounds 需补精确 + 版本锁定；data_refined 英文核心是发售版不可信
**来源**：规则域审计（代理完整跑完，Web 勘误查证 + 本地中文速查表交叉印证）。

**先纠正主 Opus 中途的一处误判**：先前我在对话里说"spec 的转致命伤是过时错误"——**不准确**。这词条在十版内多次横跳（发售版=D 致命伤 → 中途某 dataslate=不可做任何保护但普通伤害 → **现行版又转回 D 致命伤**）。以本项目自己的现行勘误源 `data_refined/10版40K通用技能速查表1.08/page_004.md`【毁灭伤害】为准，**现行 = 暴击造伤 → 造成等同 D 的致命伤**。所以 spec v1"转致命伤"**方向是对的**，真正要补的是精确度，不是推翻。

现行精确语义（写代码者按此，缺一条即错）：
1. 暴击 wound → 攻击序列对该次结束 → 造成 **= D 的致命伤**；
2. **忽视一切保护，含无效保护 invuln**（spec 只写"跳保护"→ 实现者可能只跳护甲仍放行 invuln，直接错）；
3. **每次暴击造伤最多影响 1 个模型，溢出的致命伤作废**（no spillover）；
4. **痛苦无感 FNP 仍可逐点免除**这些致命伤（别误当致命伤跳过 FNP）；
5. 在本单位其它攻击的正常伤害全部结算后，才成池分配（非真正"wound→save 短路"）；
6. lethal hits 自动造伤会跳过造伤掷骰 → 不产生暴击造伤 → **不触发 dev wounds**（`规则注解中文/page_002.md` 明示）；spec 用 lethal"直接过 wound"短路恰好正确，建议在测试固化该组合。

**教训（写进 spec v2 纪律）**：本地 `data_refined` **英文核心规则是发售版**——其 DEVASTATING WOUNDS 24.10（转致命伤旧版正好又撞回现行）与 BENEFIT OF COVER 13.08（被转录成"worsen BS by 1"，是转录/版本错误）**均不可直接据以实现**；本项目做规则真源时**以中文速查表 1.08 + 现行 dataslate 优先，英文发售版核心仅作结构参考**。这与 [数据架构裁决](../../data-architecture-2026-07-09.md)"中文 PDF 数值不可信"是同类陷阱的规则版。**且十一版已于 2026 年发布**——本项目锁定十版，spec v2 应把规则版本号（哪个 dataslate）显式钉在文档里，dev wounds 这类横跳词条尤甚。

**→ spec v2 改法**：按上述 6 条精确建模 DEVASTATING WOUNDS；补 USR 语义权威源纪律 + 规则版本戳。

### H-C 近战「双向满编反打」系统性高估守方
**来源**：架构评审 H3 + 规则域审计（双方指认）。
冲锋的全部价值就是先手减员削弱对方反打；spec 第八节让守方按**满编模型数**反打，系统性高估 counter-punch，把主打要回答的"值不值得冲"算偏，且 spec 未标注这是**系统性偏差方向**。对射击无此问题（单向 A→B 即完整答案）。

**→ spec v2 改法**（廉价去偏，不需 fight_order）：把两次模拟**串行**——A 打完，守方按**幸存模型数**反打（把 A→B 击杀数喂进 reverse 的 `models`）。并**显式标注偏差方向**（"守方满编反打系统性高估反伤/低估冲锋价值"）。扩充 not_modeled 免责清单：**冲锋成功率未建模**（默认冲锋必中，未算 2D6 冲锋距离检定失败概率——回答"值不值得冲"却假设必冲到，会高估"冲"的价值）、Fights First / 交替 / interrupt（P5）、士气/Battle-shock（半血触发、OC 归 0）、接战范围/视线/射程可达性、守方最优分配（模拟用固定分配，真人会优化）、多耐伤单位被打残未死的部分点损失不计入交换比。

### H-D 模拟意图路由档位写错，接线后验收会放水
**来源**：事实核查 ❌4。
`llm_client.py:45-53` 意图定义：**算 = 算点数/军表分值；谋 = 战术推演/模拟对战/谁能打赢**。"谁冲谁能赢"实际归**"谋"**档，不是 spec 第十节写的"算"档。而 `loop.py:26 _MUST_VERIFY_INTENTS=("查","判","算")` **不含"谋"**（loop.py:25 注释理由"谋的诚实未建模回答无需检索"在 P4 接线后失效）。**接线后 LLM 可凭九版记忆直接答"谁能赢"、永不调 simulate_combat 且无拦截。**

**→ spec v2 改法**：接线时把"谋"加入 `_MUST_VERIFY_INTENTS`（或改意图分类把模拟类归入受控档）；P4-e 验收判据加"'谋'意图零工具 final 被拦截"。

---

## 🟡 MEDIUM（事实/精度订正，产 v2 时一批打包）

| # | spec v1 原文 | 实测 / 现行规则 | 来源 |
|---|---|---|---|
| 1 | bs_ws 形态 `4+` / `-` | 两半都错：主流是**裸数字**（带 `+` 全库仅 2 行）；无 BS 标记是 `N/A`(600，100% 是 torrent)，无 `-` 值 | 事实核查 ❌1 |
| 2 | 骰子 N∈1..3 | 漏 `4D6`×3；K∈0..8 压线（`D6+8`×2）；21 种非整数值均匹配通用 `NdM+K`，无 `D6+D3` 怪值——放宽 N 上限即可 | 事实核查 ❌2 |
| 3 | 20 词条表 | **漏 `indirect fire`(139 次核心词条**，介入 hit+save，应显式决策)；频次系统性低估（torrent 24→**601** 差 25 倍，twin-linked 285→833…只影响优先级不影响正确性）；**词条参数可为骰子式**（`sustained hits d3` / `rapid fire d3` 等 42 行），整数解析会静默丢；anti-X 目标词库比列举的多（anti-character/titanic/daemon…）须通用解析非白名单 | 事实核查 ❌3/⚠1/⚠2 |
| 4 | ② Hit "冲锋惩罚" | 十版**无近战冲锋命中惩罚**（属旧版），删；冲锋相关加成是 LANCE +1 wound（spec 已有） | 规则审计 |
| 5 | 掩体"不超装甲原值上限" | 措辞错。现行（Core Rules 13.08 page_050）：掩体使**该次攻击 BS 恶化，等效 +1 甲保**，但 **Sv 3+ 或更优对 AP0 不享受**；掩体从不影响无效保护。注：data_refined page_050 自身文本亦有疑（"worsen BS by 1"），以现行规则为准 | 规则审计（核 page_050） |
| 6 | ③ Wound 阶段 | 漏"自然 1 必失 / 自然 6 必中、暴击默认 6"（hit 阶段有、wound 阶段应对称补） | 规则审计 |
| 7 | TargetProfile 单组 t/sv/w | **94 个混编单位**（Kill Team 四种模型混编 T4/T5、兽群 4 种）单组属性装不下；须定义取哪行 / 怎么合并 | 事实核查 ⚠5 |
| 8 | WeaponProfile 无 range 字段 | **76 组同名双 profile 武器**（远近双模式 `30" / Melee`）；phase 过滤靠 `weapons.range`（Melee=2968 行），须定同名双行去重/选择策略；WeaponProfile 加 `range` | 事实核查 ⚠8 |
| 9 | 数据类放 `profile.py` | 会传递性 import sqlite3 破坏"引擎脱库"；纯契约拆到**零依赖 `contracts.py`**，`profile.py` 只负责装载 | 架构 M2 |
| 10 | `DiceExpr`="采样器" | 与向量化矛盾，且 frozen 里塞 callable 不可哈希；改**声明式** `(n,faces,k)`，由引擎向量化采样器解释 | 架构 M3 |
| 11 | `tests/simulator/` + `golden_cases.yaml` | 现仓 26 测试**全扁平** `test_*.py`、无 YAML 依赖（一律 JSON）；改 `test_simulator_parse/_sequence/_golden.py` + `golden_cases.json`；若坚持子目录须补 `__init__.py` | 事实核查 ⚠10 / 架构 M4 |
| 12 | CLI 示例 `"终结者"` | 实测 `entity_resolver("终结者")` 返回 **ambiguous**（候选终结者领主/连长/牧师）；接线层须处理 ambiguous / none / fuzzy 错配三路径 | 事实核查 ⚠9 / M5 |

**其他 LOW（v2 顺带）**：`AttackerProfile` 第五节提到但第六节契约缺（C1 已补）；`strength/ap:int` 硬类型 vs 3 个骰子值/2 个 `-`（兜底分支）；AP 符号约定（存 `-1/-2`，"Sv+AP" 方向别搞反）写死进 spec；逐点 FNP 需 `(N,maxA,maxD)` 三维数组（≈2.4M cell，可接受，spec 未提内存）；models 脏值 invuln 有 2/3 档、t=`5*`、M=`20+"`(95)/`-`(50) → P4-a"1817 模型零异常"判据会踩到；datasheets 表 `damaged_w` 358 条现成受损阈值数据 spec 未盘（P4 不用可，但"实测盘点"应提及）。

---

## 里程碑 / 验收判据的连带修正

- **P4-a 判据错测对象**（架构 M5）：v1 判据"9307 武器/1817 模型解析零异常"只测单把武器 stat 解析（易），不测**装配层**（难，即 C1）→ 会给假绿灯。v2 把"给单位名+档位 → 产出 N 模型×武器数量表"写进 P4-a 判据。
- **最高技术风险埋错位置**（架构 M5）：numpy 伤害分配核（不溢出 + 变长 D + 逐点 FNP 的满桶换模型扫描）是全篇主风险，v1 把它混在 P4-b。v2 在 P4-b 前先做一次性 spike 验证分配核，别和裸序列混一个 chunk。

---

## 产 spec v2 时的落地清单（用户说"改吧"后照此执行）

1. 第三节结论改回实然（承认装配缺口）+ 新增装配层描述 + M1 efficiency 按档匹配。
2. 契约层：拆 `contracts.py`（零依赖）；加 `AttackerProfile{models, loadout}`；`WeaponProfile` 加 `range/count`；`DiceExpr` 改声明式；**新增 `Effect`（按 phase 分桶）通用通道**，武器词条 + 防守开关表示成 Effect。
3. 第四节词条表：补 `indirect fire`（建模或显式 not_modeled 决策）；频次数字订正；词条参数支持骰子式；anti-X 通用解析。
4. 第七节序列：删"冲锋惩罚"；wound 阶段补自然 1/6；掩体规则精确措辞；DEVASTATING WOUNDS 改现行版；补 USR 语义"以 dataslate 为准不以 data_refined 为准"纪律。
5. 第八节近战：改**串行幸存反打**去偏。
6. 第十节接线：意图档"算"→"谋"+ 门控补"谋"；CLI 三失败路径。
7. 里程碑：装配层写进 P4-a 判据；P4-b 前加分配核 spike。
8. bs_ws / 骰子 N 上限 / models 脏值 / 同名双 profile / 测试扁平命名 无 YAML 等 MEDIUM 逐条落。

---

## 附：证据文件路径（复核用）

- 装配缺口：`db_sources/wahapedia/Datasheets_wargear.csv`（选项池无数量）、`Datasheets_models.csv`（模型档案非数量）、`Datasheets_models_cost.csv`（模型数仅存 description）
- 装配/点数逻辑：`db_compile/build.py:104-113`（未写 count_options_json）、`schema.py:54-67`、`calc_points.py:20-31`
- 集成点：`agent/tools.py:237,241`、`agent/loop.py:19,26`、`agent/llm_client.py:45-53`、`db_compile/entity_resolver.py`
- 规则原文：`data_refined/Core Rules - New 40K Core Rules/page_050.md`（掩体）、`page_079.md`（ANTI/BLAST）、`page_080.md`（DEVASTATING WOUNDS 发售版）
