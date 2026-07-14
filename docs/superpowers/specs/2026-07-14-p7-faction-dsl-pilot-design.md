# P7 阵营技能 DSL 试点（钛帝国）设计 spec

> 2026-07-14 立项，同日经对抗性复审改订（16 项 finding 全部收口，见配套
> `2026-07-14-p7-faction-dsl-pilot-review.md`）。承接 P5「宁漏不错」裁决（阵营规则只 surface
> 名字）与 remaining-tasks T4-7：把阵营军队规则/分队规则/CP 战略**逐条人工译成 Effect DSL**，
> 带 encoded/partial/not_modeled 诚实标记，以钛帝国为试点把「录入→测试→标记」流程定型。
> 上游 spec：`2026-07-09-p5-abilities-fightorder-panel-design.md`、
> `2026-07-09-p4-monte-carlo-simulator-design.md`。

## 零、开工前数据就绪度实测（2026-07-14，经复审二次核验）

| 事实 | 证据 | 对设计的影响 |
|---|---|---|
| `abilities`(3677行)/`stratagems`(1482行) 均已预留 `effect_dsl_json` + `dsl_status DEFAULT 'not_modeled'` 列，**当前 100% 空/not_modeled** | `db_compile/schema.py:98-99,114-115`；全表实测 | P7 无需改表即可落 DSL |
| **🔴 rebuild 会清零 DSL**：`build.py:198-203` 对 abilities 用 `INSERT OR REPLACE` 且不含 effect_dsl_json；`update.py:355` build 会 unlink 重建整库 | 复审 F1 实测 | DSL 必须有文件级真源 + restore 阶段（见 §二.1），只活在 DB 里=假修复级灾难 |
| **🔴 漂移陷阱**：DB 的 `detachments.rule_text` / `stratagems.text_zh` 是 **Wahapedia 十版**文本，与 11 版 Faction Pack 已实质漂移（Auxiliary Cadre 分队规则整段改写；Photon Grenades 战略 When 段措辞已改） | `detachments` id `000009838` vs `data_refined/Faction Pack Tau Empire/page_003.md`；`page_019.md:33-34` | DSL 绝不能对着 DB 现存文本编码；试点前先 11 版化（PR1） |
| 11 版现行文本 = 十版基底 + FP overlay 的**合成**：新分队给完整文本，旧分队只给 change-list | `page_003.md` vs `page_019.md`（RULES UPDATES 体裁） | 每条录入记 provenance（基底 + 补丁），合成结果人工核对 |
| 钛帝国规模：1 条军队规则（For the Greater Good，`abilities` id `000008439`，scope=NULL，表中列名是 `name_en`）+ detachments 表 **9 条真规则行 + 1 行 'KEYWORDS' 噪声**（id 000008820）+ 44 战略（8 分队）+ 28 增强 | sqlite 实测（复审 F10 修正计数口径） | 对账枚举源=「detachments 表 TAU 非噪声行全集」，**不许硬编 8** |
| 分队身份三套体系互不链接：enhancements 用 detachment_id、stratagems 用名字、detachments 存规则名；`abilities` 表**无 faction/detachment 列** | 复审 F3 实测（enhancements↔detachments join 8/8 NULL） | 链接载体放进 DSL 载荷 JSON（§二.2），join 键统一用 enhancements.detachment_name 拼写（含弯撇号 ’） |
| `data_refined/Faction Pack Tau Empire/`（61 页）结构化良好；`detachments`/`stratagems` 的 name_zh 全 NULL | 亲验 + 实测 | 真源用 refine 缓存；中文名从十版中文 codex 缓存补 |
| **🔴 规则通道陷阱**：11 版军规是 "improve the **Ballistic Skill characteristic** by 1"——特征值改善≠命中骰修正；`sequence.py:210` 的 ±1 夹取只作用于 hit roll modifier（211 行夹的是 wound_mod） | `page_019.md:19-23` + `sequence.py` 亲验 | 需要新 op `bs_improve`，禁止映射成 `("hit","modify",(1,))` |
| BS 下限无需钳制：unmodified 1 恒失手已实现（`sequence.py:395` `hr != 1`），BS 改善到 1+ 数学等效 2+，是涌现行为 | 复审核验 | PR2 只加断言测试固定该涌现语义 |
| **🔴 条件语义**：`_cond_true`（`sequence.py:84-105`）只读 `condition[0]` 当 tag，其余元素是该 tag 的参数；**未知 tag 静默返回 False** | 复审 F2 实测 | DSL condition 契约=单 tag+参数（§二.3）；`_cond_true` 未知 tag 必须改为 raise（堵静默降级缝） |
| **攻方侧无消费对账**：`_gather_params` 遍历 `w.effects` 未知 op/条件直接跳过零记账；`unconsumed_*` 披露只覆盖守方 | 复审 F4（`sequence.py:129-176` vs `:311-321`） | PR2 补攻方对账（§四.5） |
| **modeled_effects 不读 w.effects**：`context.py:33-44` 从 raw_keywords 重新推导 | 复审 F5 | DSL 注入点须自带汇报通道（§四.4） |
| web_api `sanitize_options` 未知键**静默丢弃**（`simulate.py:15,57-80`），布尔白名单不含任何 DSL 开关；agent 直调路径（`agent/tools.py:388-460`）不过此白名单、自建 Stance | 复审 F6/F11 | PR2/PR3 必须同步扩 sanitize + tools.py，且后端回显已生效开关（§四.6） |
| frozen dataclass 运行时注入有成熟先例：`engine.py:48,54-55`、`assembly.py:119` 均用 `dataclasses.replace` | 复审核验 | 战略 effects 在 profile/assembly 层 replace 注入（sequence 不 import sqlite 的纪律不破） |
| 守方 Effect 白名单=fnp/damage_reduction/hit+modify/save+cover 四种，其余披露不静默丢 | `sequence.py:303-321` 复审核验 | 防守向 DSL 条目的 encoded 判据必须核对消费侧（§二.4 判据④） |
| P5 toggle_defensive 至今无消费者（`abilities.py:10-13`）；P5 分类器对账过滤 `owner_id IS NOT NULL AND != ''`，新增 owner_id=NULL 行不污染 | 复审核验（`test_simulator_abilities.py:290-291`） | 本期不动 toggle_defensive；分队规则新行走 owner_id=NULL 安全 |

## 一、范围边界

| 项 | 状态 | 说明 |
|---|---|---|
| DSL 真源文件 + restore 阶段 + 加载器/校验器 | ✅ 本期 | `dsl_payloads/tau.json` → `stage_dsl_apply` 挂 `_RESTORE_STAGES`（F1 收口） |
| 钛帝国规则文本 11 版化（fp_rules 刷新层） | ✅ 本期 PR1 | 仿 `fp_errata` 三态守卫（==from 应用 / ==to 幂等跳过 / 其他告警跳过，F9） |
| 军队规则 For the Greater Good 编码 + 引擎接线 | ✅ 本期 PR2 | 旗舰样例：新 op `bs_improve` + `guided` 开关 + 攻方对账 + 汇报通道 |
| Mont'ka + Kauyon 两分队规则 + 各 6 条战略 | ✅ 本期 PR3 | 效果多为 SUSTAINED/ASSAULT/LETHAL HITS/BS，通道基本现成 |
| 其余分队/战略/增强、其余 25 阵营 | 🔄 滚动（PR4+） | 流程定型后按模板铺开 |
| CP 经济 / 每阶段一次限制 / 对手互动战略 | ❌ 不建模 | 模拟假设"该战略本阶段生效"，标准注记披露 |
| 空间类效果（光环范围/移动/深打/接敌） | ❌ 不建模 | 逐条标 partial/not_modeled 并写明缺什么 |
| 战斗轮门控（Kauyon 3-5 轮 / Mont'ka 1-3 轮） | ⚠️ 半建模 | opt-in 开关"假设处于生效轮次"，报告披露该假设 |
| toggle_defensive 自动挂载 | ❌ 维持现状 | P5 裁决不变 |

## 二、DSL 载荷：真源、格式、判据

### 1. 真源与 rebuild 幸存（F1 收口）

- **文件级唯一真源**：`dsl_payloads/tau.json`（进 git），按 `(table, id)` 键存载荷；
  DB 的 `effect_dsl_json`/`dsl_status` 列只是**运行时投影**
- 新 restore 阶段 `stage_dsl_apply` 挂进 `db_compile/update.py` `_RESTORE_STAGES`
  （位置在 fp_rules 之后——DSL 指纹要对着 11 版化之后的文本核）；CLI `python -m db_compile dsl-apply`
- **对账测试**：restore 后 DB 中 encoded/partial/not_modeled 计数 == 真源文件计数；
  `--rebuild` 全流程跑一遍断言 DSL 不丢

### 2. 载荷格式（dsl_payloads/tau.json 单条目）

```json
{
  "table": "abilities", "id": "000008439",
  "faction": "TAU", "detachment": null,
  "dsl_version": 1,
  "status": "partial",
  "effects": [
    {"phase": "hit", "op": "bs_improve", "params": [1],
     "condition": ["guided_vs_spotted"], "source": "For the Greater Good"}
  ],
  "requires_toggles": ["guided"],
  "not_modeled_notes_zh": ["观察员自身不选择射击的机会成本未建模", "每敌军单位每阶段仅被标记一次未建模"],
  "provenance": {
    "current_text": "Faction Pack Tau Empire p19 (RULES UPDATES)",
    "base_text": "Wahapedia 10e For the Greater Good",
    "synthesis": "FP change-to 全文替换",
    "text_sha256": "<11版化后 DB 文本指纹>"
  },
  "encoded_by": "manual-2026-07-14"
}
```

- `faction`/`detachment` 字段承载链接（abilities 表无此列，F3 收口）：`load_faction_dsl`
  扫 `effect_dsl_json IS NOT NULL` 行（试点期几十行，扫得起）按载荷内字段过滤；
  detachment 拼写以 enhancements.detachment_name 为准（含弯撇号 `Mont’ka`）
- `text_sha256`：录入时对 DB 现行文本取指纹；对账测试断言指纹匹配——文本被后续
  刷新而 DSL 未重核时测试红（F12 收口）
- `dsl_version`：加载器**只接受 1**，其他值拒载报错（F15）

### 3. condition 契约（F2 收口）

- 引擎契约：`Effect.condition = (tag, *args)`——**单 tag**，`_cond_true` 只认 `condition[0]`，
  其余元素是该 tag 的参数。DSL 校验器强制此形状，**合取列表直接拒载**
- 需要复合条件时注册**复合 tag**（如 `guided_vs_spotted` 自含"射击阶段+guided 开关开启"
  语义，在 `_cond_true` 加分支实现），不做通用合取求值器（YAGNI）
- **PR2 必改**：`_cond_true` 未知 tag 从 `return False` 改为 `raise`（静默降级缝，
  CLAUDE.md 纪律）；现有全部 tag 加回归测试护住

### 4. dsl_status 三态判据（写死进 dsl.py docstring，F7 收口）

- `encoded`：①效果全部落入 effects ②数值语义与原文手算等价 ③op/condition 过白名单
  ④**该 (phase, op) 在施加侧（攻/守）有引擎消费点**——白名单按攻/守两侧分列，且由
  引擎实际消费点生成（不手抄第二份，漂移即测试红）
- `partial`：可建模子集已落 effects（同样满足①③④），其余**逐条**写进
  `not_modeled_notes_zh`（一条不许漏）
- `not_modeled`：effects 为空，notes 写明原因
- 铁律：**逐条人工录入**，LLM 只出初稿，落库前人工对照原文核数值（P5 陷阱 T1 的
  94% 条件式教训）；每条 encoded 必须有"差分测试期望值必须动"的断言（不动=假 encoded）

## 三、原文真源与十版漂移处理（PR1：fp_rules 刷新层）

- 新模块 `db_compile/fp_rules.py`（仿 `fp_errata.py`）+ `fp_rules_patches.json`，按
  `(表, id)` 定位；**守卫采用 fp_errata 三态语义**（F9）：DB==from → 应用；DB==to →
  幂等跳过；其他 → 跳过并显眼告警（Wahapedia 滚更 11 版时自报，届时评估退役）
- 补丁范围（本期只钛帝国）：
  1. `detachments.rule_text`：**TAU 非噪声行全集（实测 9 条）**按 FP 合成现行文本；
     'KEYWORDS' 噪声行顺手核实处置（删或标记）
  2. `stratagems.text_zh`：44 条中被 FP 勘误的逐条替换（未勘误的十版文本 11 版仍现行）
  3. `abilities` id `000008439`：替换为 FP p19 change-to 全文
  4. `name_zh` 补齐：来源 `data_refined/钛帝国十版CODEX-20251112/`；FP 新增无中文名的
     自译并标 `zh_source:"self-translated"`
- 挂 `restore_authority_layers`；CLI `python -m db_compile fp-rules`
- **对账**：应用后产 before/after 全量 diff 报告，人工过目，目标数 vs 实际数落 devlog
- 下游影响：全仓 grep 确认无 agent/web 消费者读 `stratagems.text_zh`/`detachments.rule_text`
  正文（仅 `profile.py:127` 读 detachments 名字列，PR1 不动名字列）——改文本对现有链路无害

## 四、引擎接线（PR2）

1. **op `bs_improve`**：改善命中阈值特征值，不进 `hit_pos/hit_neg` 夹取池；先特征值后
   修正（11 版 1.05 次序）；下限由 unmodified-1 涌现语义承担（加断言测试固定，不另钳制）
2. **掩体通道对称性裁决（F8，PR2 内定）**：11 版 13.08 掩体同样是"worsen BS"特征值
   语义，现实现折进 hit_neg 夹取池——与 bs_improve 不对称，guided×掩体×烟幕三方叠加时
   两种口径结果不同。PR2 评估把掩体折算迁入 bs 通道（净 BS 变化=改善−恶化，modifier
   夹取独立）；若影响面大则本期固定现口径 + 三方叠加测试 + 报告披露不对称。
   **特征值修正有无上限：当前语料缺页**（Modified Characteristics 正文缺，
   `wiki/core-rules/hit-roll.md:28` 已注记），按无上限实现，列入 T1-4 类外部源观察项
3. **condition `guided_vs_spotted`** + 攻方开关 `--guided`（说明"假设本单位受引导且目标
   已被标记"）；观察员带 Markerlight 再加 `--markerlight-observer` → 追加 `("save","ignores_cover")`
4. **DSL 汇报通道（F5）**：注入点同时产出 `modeled_effects` 追加项（含 source）；
   测试断言"开开关 → 报告出现该条 **且** 数值变化"成对出现（双向诚实语义）
5. **攻方消费对账（F4）**：加 `unconsumed_attacker_effect_notes` 同款机制——`w.effects`
   中未被 `_gather_params` 消费的 Effect 强制披露进 not_modeled
6. **接线面收全（F6/F11）**：`web_api/simulate.py` `sanitize_options` 白名单扩
   `guided`/`markerlight_observer`/战略 id 列表（需新收敛函数，现仅支持 bool/int/loadout）；
   **`agent/tools.py` simulate_combat_resolved 同步支持**（Agent 模式是基准主力路径）；
   后端回显"已生效开关清单"供前端对账，未接受的开关显式报出而非静默丢
7. **战略 = 一次性 opt-in 开关**：`load_faction_dsl` 返回已编码条目；注入在
   **profile/assembly 层**用 `dataclasses.replace(w, effects=w.effects + strat_effects)`
   重建 loadout（先例 `engine.py:48`、`assembly.py:119`；sequence 不 import sqlite 纪律不破）；
   CP 消耗只展示不结算

## 五、试点条目预判（PR2+PR3 逐条译表）

| 条目 | 类型 | 预判 | 关键映射 |
|---|---|---|---|
| For the Greater Good | 军规 | partial | `bs_improve+1`(guided_vs_spotted) + `ignores_cover`(markerlight)；观察员机会成本不建模 |
| Kauyon: Patient Hunter | 分队规则 | partial | 3-5 轮门控开关 + SUSTAINED HITS 1 + guided 时忽略 BS/命中修正（注意区分两类修正） |
| Mont'ka: Killing Blow | 分队规则 | partial | 1-3 轮门控开关 + ASSAULT + guided 追加效果逐句核 |
| 12 条战略（Kauyon 6 + Mont'ka 6） | 战略 | 逐条判 | When/Target/Effect 三段式；Effect 落白名单 op 且消费侧存在者 encoded |
| Through Unity, Devastation 等增强 | 增强 | 多为 partial | 依赖"leading a unit"→开关"假设依附中"+披露（增强整体后置 PR4） |

> 本表是预判不是结论；以录入时手算核验为准，预判与实录不符时以实录为真并回改本表。

## 六、模块结构与依赖方向

```
dsl_payloads/tau.json             # DSL 唯一真源（git 管理）
db_compile/fp_rules.py            # PR1 文本 11 版化补丁（三态守卫）
fp_rules_patches.json             # 文本补丁数据
db_compile/dsl_apply.py           # 真源 → DB 投影 + restore 阶段注册
engines/simulator/dsl.py          # 载荷解析/分侧白名单校验/Effect 反序列化（只 import contracts）
engines/simulator/profile.py      # + load_faction_dsl
engines/simulator/assembly.py     # + 战略 effects replace 注入（含汇报追加项）
engines/simulator/sequence.py     # + bs_improve 通道 + _cond_true 未知tag raise + 攻方对账
engines/simulator/cli.py          # + --guided/--markerlight-observer/--stratagem <id>
agent/tools.py                    # + options 解析同步（Agent 直调路径）
web_api/simulate.py               # + sanitize 白名单/收敛函数/生效开关回显
ui/simulator_panel.py             # + 分队选择 → DSL 开关组渲染
```

依赖方向不变：dsl.py 只依赖 contracts；sequence 不 import sqlite；面板只调引擎公开 API。

## 七、验证体系（防假实现）

1. **每条 encoded 双验**：解析级（JSON→Effect 逐字段断言）+ 引擎级（N=60000 蒙特卡洛
   差分对手算值，沿用 `test_simulator_abilities.py:225-280` 范式）；**期望值必须动**，
   不动即假 encoded（F7）
2. **bs_improve 专项**：①BS4+ 带 -1 修正场景，断言 guided 后=「BS3+ 再 -1」而非修正抵消
   ②PSYCHIC `ignore_hit_mods` 不无视 BS 改善 ③guided×掩体×烟幕三方叠加按 §四.2 裁决口径
   断言（F8）④unmodified-1 涌现下限断言
3. **全库对账**：钛帝国全部条目（军规 1 + detachments 表 TAU 非噪声行全集 + 战略 44）
   三态计数和==总数；partial/not_modeled 的 notes 逐条非空；encoded 条目 (phase,op)
   在施加侧消费白名单内；`text_sha256` 指纹匹配现行文本（F12）
4. **rebuild 幸存测试**：`--rebuild` → restore 全链 → DSL 计数==真源文件计数（F1）
5. **fp_rules 守卫测试**：伪造漂移文本断言跳过+告警；重复应用断言幂等
6. **接线对拍**：前端开关名 ↔ sanitize 白名单 ↔ tools.py 参数三方一致性测试（F6/F11）；
   攻方 unconsumed 披露测试（F4）；"报告出现⇄结果被影响"成对断言（F5）
7. **回归**：全库测试绿（739 基线）；基准 v3 重跑 ≥99.0（DSL 与检索无耦合，重跑属
   例行护栏而非风险响应，F14）；面板 AppTest 无头回归

## 八、里程碑（每步独立 commit + devlog）

| PR | 内容 | 规模 |
|---|---|---|
| PR0 | 本 spec + 对抗性复审收口 | 0.5 天 |
| PR1 | fp_rules 钛帝国文本 11 版化 + name_zh 补齐 + diff 对账报告 | 1 天 |
| PR2 | dsl.py + 真源/restore 机制 + bs_improve + _cond_true 加固 + 攻方对账 + FTGG 编码接线（CLI/面板/tools/web 四路开关） | 1.5 天 |
| PR3 | Mont'ka + Kauyon 分队规则 + 12 战略逐条 + web 契约与开关回显 | 1-1.5 天 |
| PR4+ | 增强 + 其余分队/战略 + 其余阵营滚动 | 长期 |

## 九、风险与应对

| 风险 | 应对 |
|---|---|
| rebuild/restore 链路 DSL 丢失 | 文件真源 + stage_dsl_apply + 幸存测试（F1，已入 §二.1/§七.4） |
| 合成现行文本合错 | provenance 留痕 + PR1 diff 报告逐条人工过目 |
| DSL 录入数值笔误 / 假 encoded | 分侧白名单 + 手算差分"期望值必须动" + 指纹对账 |
| condition/op 静默失效 | `_cond_true` 未知 tag raise + 攻方消费对账 + 汇报成对断言 |
| 开关在某条链路被静默吞 | 四路（CLI/面板/tools/web）对拍测试 + 后端回显生效清单 |
| 战轮门控开关被误解为永久生效 | 开关文案写明假设；报告标准注记 |
| Wahapedia 滚更 11 版与 fp_rules 冲突 | 三态守卫自报，届时评估退役 |
| 空间类占比高导致 encoded 率难看 | 诚实标记本来就是目标，不设 encoded 率 KPI |

## 决策记录

- **D1**：原文真源 = `data_refined/Faction Pack Tau Empire/`（11 版 overlay）合成十版基底；
  DB 现存 Wahapedia 十版文本不作为编码依据
- **D2**：`bs_improve` 独立于 hit modifier 通道，不吃 ±1 夹取；特征值修正上限条款在当前
  语料缺页，按无上限实现并列入外部源观察项（复审 F8 修订）
- **D3**：战略/军规 = opt-in 开关，CP 经济与次数限制不建模只披露
- **D4**：逐条人工录入，LLM 仅辅助初稿；三态判据含"施加侧有消费点"第四条件（F7 修订）
- **D5**：分队规则条目落 `abilities` 表新行（owner_id=NULL，id 新段）；faction/detachment
  链接**由 DSL 载荷 JSON 自带字段承载**，不改表、不动既有行 scope（F3 修订；
  `condition_json` 死列保留不占用）
- **D6**：DSL 唯一真源是 `dsl_payloads/*.json` 文件，DB 列是投影；restore 链新增
  stage_dsl_apply（F1 新增）
- **D7**：`_cond_true` 未知 tag 由静默 False 改为 raise——属引擎加固，随 PR2 落地（F2 新增）

## 自审清单

- [ ] PR1 diff 对账报告逐条 before/after 已人工过目；'KEYWORDS' 噪声行已处置
- [ ] 每条 encoded 有解析级+引擎级双测试，手算值写在测试注释里，期望值必须动
- [ ] bs_improve 专项四测试（叠加/PSYCHIC/三方/下限涌现）全绿
- [ ] rebuild 幸存测试在；三态计数对账 + 指纹对账在；notes 无空
- [ ] 四路开关对拍测试在；攻方 unconsumed 披露在；汇报成对断言在
- [ ] 基准 v3 重跑 ≥99.0，全库测试绿；面板/CLI 开关文案写明假设
