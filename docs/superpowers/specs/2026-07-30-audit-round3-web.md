# 全库三轮代码审查 · 第 3 轮：`web_api/` + 前端 `web/`

- 分支：`review/full-audit-2026-07-30`
- 范围：`web_api/`（19 个 py）、`web/src/`（46 个 ts/tsx）、`web/e2e/`（4 个）
- 产出形式（用户拍板）：**审出分级清单 + 只修 CRITICAL/HIGH**；MEDIUM/LOW 只记录
- 前置：已读第 1 轮 §5、第 2 轮 §4/§5，5 条移交线索逐条给了结论（见 §4）

---

## 0. 本轮结论速览

| 分级 | 条数 | 状态 |
|---|---|---|
| 🔴 CRITICAL | **0** | 本轮未发现 |
| 🔴 HIGH | **3** | H1 / H2 / H3，全部有实测复现输出，见 §2.1 |
| 🟡 MEDIUM | 7 | 只记录 |
| 🟢 LOW | 5 | 只记录 |
| ⚪ 疑似 | 1 | 未复现，单列 |
| ⛔ 判为不成立 | 6 | 附反证，见 §4 |

**一句话**：这一层的代码质量整体高于前两轮——`web_api/` 的只读浏览端点把
「fail-closed 不返回空列表」这条约定**逐个端点**做到位了，前端 `DetachmentBrowser`/
`CoreRulesBrowser`/`ChangelogBrowser` 也都就地报错而不是渲染成空态；契约字段名
**机械对账 37 组模型零漂移**。三条 HIGH 全部集中在**同一个母题**：
**边界把用户的输入或后端的失败细节丢掉了，而页面看不出来**——
① 点数徽章在全库 1715 个单位上恒为空（口径读错，功能整条死掉且无人察觉）；
② 模拟器数值入参超限后被静默丢弃，端出一份 `ok=True` 的**假成功**报告；
③ `SimResponse.errors` 这条通道在前端根本不存在，而后端的 note 明文写着「见 errors」。

**特别地**：第 1 轮 H3（loadout 件数 ≤0 不再假成功）的那句用户可见文案，
经本轮实测**用户可见性为零**——它走的正是 ③ 那条前端从不读的 `errors` 通道。

---

## 1. 逐文件审查覆盖表

方法说明：按 objective 要求「grep/rg 定位再定点读」，故下表区分
**通读**（整文件读完）与 **定向审**（按风险模式 grep + 命中处定点读）。
两者都算「已审」；未审的会写明原因。

### 1.1 `web_api/`（19 / 19 已审）

| # | 文件 | 方式 | 结论 |
|---|---|---|---|
| 1 | `__init__.py` | 通读 | 5 行包 docstring，无逻辑。无问题 |
| 2 | `changelog_browse.py` | 定向审（对账/异常/空返回） | `_reconcile` 三件事逐条对账（明细页可读、条目数与 🆕 数相符、磁盘无清单外的页），差额一律 503 + 日志点名。无问题 |
| 3 | `codex.py` | 通读 | **H1**（`_min_points` 口径读错）。宽口径 `_current_unit_ids` 与第 2 轮 M1 一致，按 objective 不动 |
| 4 | `contract.py` | 通读 | 与前端契约字段名机械对账零漂移（§2.4）。`WikiBlock` 判别式联合 + `model_rebuild()` 到位。无问题 |
| 5 | `core_rules_browse.py` | 通读（60-219）+ 定向审 | 缺 frontmatter / 0 节 / 目录空一律 503；slug 正则 + `is_relative_to` 双重防穿越；节号「全仓库唯一一处实现」成立。无问题 |
| 6 | `entity_card.py` | 定向审（空返回/points 口径） | `_points_str` 用的是 `ds["points_options"]`（真列表），**不是** H1 那个坑。无问题 |
| 7 | `formatter.py` | 通读 | **M1**（结构化失败静默退化，无 traceWarn） |
| 8 | `keyword_refs.py` | 定向审（异常吞/降级披露） | 三处降级都走 `_warn_once` 吼一声且退成**纯文本**（不编解释）。无问题 |
| 9 | `keywords.py` | 通读 | 载荷三种坏法分开报，空数组也判损坏。无问题 |
| 10 | `main.py` | 通读 | **M2**（`_SESSIONS` 无上限）。限流挂在 CORS 之前、`/wiki` 用 `is_relative_to` 防穿越、并发信号量 503 —— 三条安全约定**均仍成立** |
| 11 | `preflight.py` | 通读 | 五类资产核对，`WEB_API_RETRIEVAL=off` 时降 `required=False` 并写明「不是坏了是没开」。无问题 |
| 12 | `ratelimit.py` | 通读 | 两档配额、XFF 默认不信、键上限 4096 防内存撑爆、装载顺序注释与 `main.py` 一致。无问题 |
| 13 | `richtext.py` | 通读 | 标记切分确定性；`[数字]`→cite / `[非数字]`→kw 的歧义消解明确。无问题 |
| 14 | `roster.py` | 通读 | `_to_loadout` 非法即整体丢弃，但 `critique_roster` **按输入侧事实改写 note**（诚实归因）——与 H2 形成正反对照 |
| 15 | `simulate.py` | 通读 | **H2**（超上限静默丢弃）。`_as_bool` 收严、`n` 钳 [100,20000]、白名单来自 dsl 注册表——这三条仍成立 |
| 16 | `structurer.py` | 通读 | 解析失败抛异常交上层 fail-closed，系统提示明令「不新增未查证的数字」。无问题 |
| 17 | `trace.py` | 通读 | `_status` 把 `modeled:false` / `ok:false` 都标 degraded。无问题 |
| 18 | `wiki_blocks.py` | 定向审（空返回/异常） | 与 `Blocks.tsx` 的块型一一对上（§2.4）。无问题 |
| 19 | `wiki_browse.py` | 通读 | fail-closed 做得最彻底的一份：`WikiUnavailable` vs `NotFound` 分家、子页对账 `_reconcile`、TL/UN 真空阵营与「卷挂了一半」分开判。无问题 |

### 1.2 `web/src/`（46 / 46 已审）

**页面 / 布局（6）**

| 文件 | 方式 | 结论 |
|---|---|---|
| `app/page.tsx` | 通读 | 10 行，挂 fixture 给 `ChatApp`。无问题 |
| `app/layout.tsx` | 通读 | 字体/元信息。无问题 |
| `app/codex/page.tsx` | 通读（1-199）+ 定向审 | **M3**（任何错误都甩 `BACKEND_HINT`）、**M4**（子浏览器 503 时双错误横幅） |
| `app/simulator/page.tsx` | 通读 | **H3**（`errors` 从不渲染）、**L1**（race 下 loading 提前熄）、**L2**（`!rep.reverse` 时那句「反打未接入本页」在反打真失败时会说反话） |
| `app/roster/page.tsx` | 通读 | 竞态/中止/签名过期都处理了（`critiqueSig` 一变旧点评即视为过期）。无问题 |
| `app/design/page.tsx` | 定向审 | 纯静态设计稿展示页，无取数、无契约消费。无问题 |

**chat 组件（12）**

| 文件 | 方式 | 结论 |
|---|---|---|
| `chat/ChatApp.tsx` | 通读 | **M5**（流未发 `done` 就断 ⇒ 永远停在 streaming，输入框永久禁用） |
| `chat/Composer.tsx` | 通读 | `disabled` 绑 streaming——是 M5 的受害方 |
| `chat/ToolTrace.tsx` | 通读 | 逐步 degraded 标 ⚠ + `traceWarn` 徽章。无问题 |
| `chat/Datasheet.tsx` | 定向审（字段覆盖） | EntityCard **19/19 字段全部渲染**（含 legend/damaged/leads/factionKeywords）。无问题 |
| `chat/CalcList.tsx` | 通读 | **L3**（steps 为空仍画标题栏，出现空面板） |
| `chat/VerdictCard.tsx` / `AnswerHead.tsx` / `AskCard.tsx` / `CiteSeals.tsx` / `SensitivityCta.tsx` / `SiteHeader.tsx` / `Aquila.tsx` | 通读 | 纯展示，无取数无解析。无问题 |

**codex 组件（5）**

| 文件 | 方式 | 结论 |
|---|---|---|
| `codex/Blocks.tsx` | 通读 | 6 种块型（p/ul/ol/table/h/quote/details）**全覆盖**，`details` 递归渲染。无问题 |
| `codex/DetachmentBrowser.tsx` | 通读（250-360）+ 定向审 | 就地报错不渲染空列表、`reqSeq` 丢弃过期响应、`WikiApiError` 时**不**升顶部横幅——本层的正确范式 |
| `codex/CoreRulesBrowser.tsx` | 定向审 | 503/404 分开话术（做得好）；但无条件 `onError?.()` ⇒ **M4** |
| `codex/ChangelogBrowser.tsx` | 定向审 | 同上 ⇒ **M4** |
| `codex/KeywordIndex.tsx` | 定向审 | 列表失败就地报错（对）；详情失败无条件 `onError()` ⇒ **M4** |

**roster / sim 组件（6）**

| 文件 | 方式 | 结论 |
|---|---|---|
| `roster/ValidationPanel.tsx` | 通读 | `surfacedOnly` 显示成「未校验」，issues 全渲染。无问题 |
| `roster/CritiquePanel.tsx` | 通读 | `summary` / `notModeled` / 未评估单位的 `note` 全渲染；**不显示 `totalPoints`** ⇒ 第 1 轮 M3 在 UI 层不成立（§4 N2） |
| `roster/RosterUnitRow.tsx` | 定向审 | `models` 超 100 由 Pydantic `le=100` 挡成 422 ⇒ 前端弹错误横幅，**fail-closed**（与 H2 的对照组） |
| `sim/LoadoutPanel.tsx` | 通读 | **L4**（件数输入无 `max`，超 400 的值会被后端整体丢弃） |
| `sim/SimResults.tsx` | 通读 | modeledEffects / notModeled / biasNotes / defenderToggles / factionOptions / warning 全渲染——**唯独没有 `errors`**（H3） |
| `sim/UnitPicker.tsx` | 通读 | **L1** 的显形处（`!loadingUnits && filtered.length===0` → 「无匹配单位」） |

**ui 组件（9）**：`ClipPanel` / `KwBar` / `PlateButton` / `Rich` / `SlotBadge` / `StatBox` /
`VerdictShield` / `WaxSeal` —— 通读，纯展示无取数；`Rich.tsx` 对 6 种 Inline 判别式**全覆盖**。
`KeywordChip.tsx` —— 定向审（悬停/钉住 tooltip，有 state 无取数）：
`:110-115` 对查不到真源的词条**渲染成纯文本、连按钮都不给**，
`:115` 的兜底文案只说「为什么查不到」而不代写解释——诚实性做到位。均无问题。

**lib 契约与客户端（8）**

| 文件 | 方式 | 结论 |
|---|---|---|
| `lib/answer.ts` | 通读 | 契约真源，与 `contract.py` 零漂移 |
| `lib/sim.ts` | 通读 | 同上；`errors: string[]` 在此声明，全前端**仅此一处出现**（H3 的铁证） |
| `lib/roster.ts` | 通读 | 同上 |
| `lib/keywords.ts` | 定向审 | 同上 |
| `lib/wiki.ts` | 定向审 | `WikiApiError` 带 status——503/404 分开话术的基础设施 |
| `lib/codex.ts` | 通读 | **M3 的源头**：`throw new Error("后端返回 ${status}")`，不带 status 类型，调用方无从分辨 |
| `lib/api.ts` | 通读 | SSE 手写解析正确；**M5** 的源头（流正常结束但没 `done` 事件时静默 resolve） |
| `lib/fixtures/broadside-vs-knight.ts` | 定向审 | 首屏 fixture，`degraded:true` + `status:"degraded"` 都在，示例本身诚实。无问题 |

### 1.3 `web/e2e/`（4 / 4 已审）

| 文件 | 结论 |
|---|---|
| `helpers.ts` | `pickSimUnit` 先等下拉真有 option 再 `selectOption`——注释写明「否则报错会掩盖后端没连上这个真因」。有效 |
| `codex.spec.ts` | 中英切换断言「武器名换语言、单位英文名与数值不变」，是**真断言**不是存在性断言。有效 |
| `roster.spec.ts` | 第二条明确写「光有表头不算产出（P6 教训：装配成功≠有输出）」并断言行里有 `\d+\.\d`。有效 |
| `simulator.spec.ts` | 三条全是 2026-07-25 真实缺陷的回归钉；断言含否定式（`Crushing bulk 件数` 必须 `toHaveCount(0)`）。有效 |

**e2e 覆盖缺口（记入 §5 遗留，不算缺陷）**：4 条用例全走 happy path，
**没有一条**覆盖「后端 503 / 超上限入参 / 装配失败」这些错误路径——
本轮三条 HIGH 里的 H2、H3 正落在 e2e 的盲区。

---

## 2. 分级 finding 清单

### 2.1 🔴 HIGH

#### H1 · 图鉴/模拟器/军表的「N 分起」点数徽章在**全库 1715 个单位**上恒为空

- **文件:行**：`web_api/codex.py:88-96`（`_min_points`），消费方 `:119-123`
- **根因**：`points_json` 存的是 **dict**
  （`{"points":170,"items":[{...,"cost":170}],"mfm":{...}}`——同文件
  `_current_unit_ids:46` 就是按 dict 取 `.get("mfm")` 的），而 `_min_points`
  把它当 **list of dict** 迭代：

```python
opts = json.loads(points_json)          # 实际是 dict
costs = [o.get("cost") for o in opts if isinstance(o, dict) and ...]
#                          ^^^^ 迭代 dict 得到的是 key 字符串 → isinstance 恒 False
```

  于是 `costs` 恒为 `[]`，函数恒返回 `None`，`pts` 恒为 `null`。

- **复现输入 → 实际输出**（`%TEMP%\r3_probe2.py`、`r3_probe6.py`，库 `mode=ro`，零写入）：

```
$ .venv/Scripts/python.exe %TEMP%\r3_probe2.py
000000882 Custodian Guard {"points": 170, "items": [{"line": "1", "desc": "4 models", "cost": 170}, ...
---- list_units 实测 ----
TAU 单位数: 43
有 pts 的: 0
{'id': '000000455', 'nameEn': 'AX-1-0 Tiger Shark', 'nameZh': '虎鲨AX-1-0', 'pts': None, 'legacy': False}
{'id': '000000412', 'nameEn': 'Breacher Team',      'nameZh': '破袭小队',    'pts': None, 'legacy': False}

$ .venv/Scripts/python.exe %TEMP%\r3_probe6.py
units 总数 = 1715
现实现 _min_points 非 None 的单位数 = 0
按 items[].cost 取 min 后非 None 的单位数 = 1711
TAU: 43 个单位，pts 非 null 0 个
SM: 186 个单位，pts 非 null 0 个
NEC: 62 个单位，pts 非 null 0 个
```

- **影响**：三个页面的点数展示分支**永远走不到**——
  `web/src/app/codex/page.tsx:294`（图鉴单位列表）、
  `web/src/components/sim/UnitPicker.tsx:106`（模拟器攻/守选单位）、
  `web/src/app/roster/page.tsx:332`（军表搜索下拉）都是
  `{u.pts ? (<span…>{u.pts}</span>) : null}`，`pts` 恒 null ⇒ 徽章从来没出现过。
  **1711/1715 个单位本来有点数可显示**。这是一整条功能**静默死亡**：
  没有报错、没有空位、页面看着完全正常。
- **口径不许猜**：修法取 `items[].cost` 的最小值，与
  `engines/simulator/assembly.py:52-55 default_model_count`
  的注释「默认满编模型数 = 最小档模型数（**与 calc_points 取 min 档一致**）」同源，
  不引入第二套点数口径。
- **定级理由**：确定性可复现、覆盖全库、当前 100% 触发，属「significant quality issue」⇒ HIGH。
  不升 CRITICAL：不产出错误数值，只是不产出。
- **零测试覆盖**：`grep -rn "_min_points\|\"pts\"" tests/ web/e2e/` 无任何命中。

#### H2 · 模拟器数值入参超上限后**静默丢弃**，端出一份 `ok=True` 的假成功报告

- **文件:行**：`web_api/simulate.py:104-108`（`attacker_models` / `defender_models` /
  `damage_reduction` 走 `_as_pos_int(v, hi)`，超 `hi` 返回 `None` ⇒ 该键**不进** `out`），
  `:57-70`（`_as_loadout` 任一件数超 `WEAPON_COUNT_MAX=400` ⇒ **整份 loadout** 返回 `None`）
- **UI 可达性**：`web/src/app/simulator/page.tsx:304-311, 313-322` 两个模型数输入框
  `type="number" min={1}` 且**没有 `max`**；`buildOptions:164-167` 只判 `am > 0` 就发出去。
  `web/src/components/sim/LoadoutPanel.tsx:79-88` 件数框同样 `min={0}` 无 `max`。
- **复现输入 → 实际输出**（`%TEMP%\r3_probe5.py`，Tactical Drones 000000403，
  射击阶段唯一武器 ⇒ 自动装配，无需人工 loadout）：

```
样本单位: ('000000403', 'Tactical Drones', [{'models': 4, 'cost': 70}, {'models': 8, ...}])
填 attacker_models=None  → sanitize={'phase': 'shooting'}                        ok=True 攻击次数=8.0  期望伤害=1.174
填 attacker_models=5     → sanitize={'phase': 'shooting', 'attacker_models': 5}  ok=True 攻击次数=10.0 期望伤害=1.449
填 attacker_models=101   → sanitize={'phase': 'shooting'}                        ok=True 攻击次数=8.0  期望伤害=1.174
填 attacker_models=200   → sanitize={'phase': 'shooting'}                        ok=True 攻击次数=8.0  期望伤害=1.174
```

  用户在「攻方模型数」里填 **200**，页面上那个框仍显示 200，
  旁边端出的却是**按默认 4 个模型**算的报告（8 次攻击 / 1.174 伤害，
  与压根不填时**逐位相同**）。没有 warning、没有 note、没有任何披露。

- **同一开关的第二个后果**（件数超 400，`%TEMP%\r3_probe3.py`）：

```
--- ② 用面板里真实存在的武器名，件数填 500（>WEAPON_COUNT_MAX=400）---
sanitize_options 后 = {'phase': 'shooting'}          ← loadout 整份消失
ok= False reason= loadout_required
note= 武器表是选项池（含互斥选项），P4 不猜默认装配；请据 weapon_pool 指定 loadout=...
errors= []
```

  用户填完装配点「开始模拟」，拿回来的是**一模一样的装配面板**和
  「请指定 loadout」——他刚指定过。填的东西凭空消失，零解释。

- **影响**：这正是项目纪律里点名的「**假成功**」形状——每一层都是成功路径
  （边界过滤成功、装配成功、模拟成功、渲染成功），而结果回答的是**另一个问题**。
  与第 1 轮 H3（loadout 件数 ≤0 曾端出全 0 假成功报告）同型，只是换了个入参。
- **对照组证明这不是"设计如此"**：同一份上限常量在军表侧
  （`web_api/contract.py:290` `models: int = Field(ge=1, le=100)`）走的是
  **Pydantic 422 拒收** ⇒ 前端弹错误横幅，fail-closed；
  `web_api/roster.py:75-79 critique_roster` 甚至专门为「loadout 被整体丢弃」
  改写 note 说「已整体丢弃（不猜半份装配）→ 未评估，请修正装配后重试」。
  **同一个仓库、同一组常量，模拟器这一侧是唯一静默的那个。**
- **注释保护线的边界**：`simulate.py:24-29` 的注释论证的是**「不静默钳」**
  （钳了会悄悄改变模拟语义）——这条对，修法**不许改成钳制**。
  但它没有论证「丢弃可以不说」。正确修法是**丢弃照旧 + 显式披露**。
- **定级理由**：UI 可达、确定性复现、产出一份看不出问题的错误报告 ⇒ HIGH。

#### H3 · `SimResponse.errors` 在整个前端**从不被读取**，而后端 note 明文写着「见 errors」

- **文件:行**：契约声明 `web/src/lib/sim.ts:138`；后端产出
  `engines/simulator/assembly.py:169-192`、`agent/tools.py:788, 793, 806, 940, 946, 957`；
  后端 note `engines/simulator/assembly.py:192`
- **铁证**（全前端唯一一次出现就是类型声明本身）：

```
$ cd web && grep -rn "errors" src/ --include=*.ts --include=*.tsx
src/lib/sim.ts:138:  errors: string[];
```

  `web/src/app/simulator/page.tsx` 的三条失败分支
  （`needLoadout:336-347` / `needDefLoadout:350-361` / `failedOther:363-385`）
  一律只渲染 `resp?.note`，`resp.errors` 一次都没进 JSX。

- **复现输入 → 实际输出**（`%TEMP%\r3_probe3.py` ③，直连 `/simulate` 契约）：

```
--- ③ 武器名不在池里 ---
ok= False reason= loadout_required
note= loadout 不可用（武器名无法匹配或件数非法），见 errors
errors= ["武器名 'Nonexistent Gun' 不在该单位武器池"]
```

  页面此时渲染的是 `LoadoutPanel note={resp?.note}` ⇒ 用户看到的是
  **「loadout 不可用（武器名无法匹配或件数非法），见 errors」**，
  而那个 `errors` 在这个页面上**不存在**。一句指向虚空的指路。

- **最重要的后果 —— 第 1 轮 H3 的用户可见性为零**：
  第 1 轮修的「件数 ≤ 0 必须显式失败」，那句面向用户的文案
  （`assembly.py:183-186`「武器 X 的件数 0 ≤ 0，无法模拟（0 件 = 不开火，
  只会得到期望伤害恒为 0 的空报告）；要排除这把武器就别把它写进 loadout」）
  **只进 `errors`**。第 1 轮 §5 移交线索 ④ 问的正是这句话「到底显示了没有」——
  **答案是没有**。后端诚实了，用户一个字也看不到。
- **可达性如实交代**：今天从**浏览器 UI** 走不到这条 note——
  `LoadoutPanel` 的武器名全部来自后端返回的 `weaponPool`，必然匹配；
  而 `_match_weapon` 的「同名多 profile」歧义分支我实测**全库 0 组**
  （`%TEMP%\r3_probe1.py`：`同阶段同名多 profile 的 (单位,阶段,武器) 组合数: 0`）。
  可达的是 **`/simulate` 这个契约化公开端点的直连调用方**（上面 ③ 即是），
  以及 **agent 工具链**（LLM 从自然语言现编 loadout，第 1 轮 H3 的原始场景）。
- **定级理由**：note 与页面自相矛盾（指向一个用户拿不到的字段）、
  且使一条已完成的 HIGH 修复在 web 侧完全失效 ⇒ HIGH。
  未升 CRITICAL：不产出错误数值，且失败本身是被正确报出来的（`ok=false`）。

### 2.2 🟡 MEDIUM（本轮只记录，不修）

#### M1 · 结构化 LLM 失败后静默退化，`traceWarn`/`degraded` 都不标
`web_api/formatter.py:164-172`。`except Exception: structured = {}` ⇒ verdict 退成
「参谋回复 / Advisory」+ 散文 lede，`calc` 变空数组。答案本体是模型真写的散文，
**不构成伪造**，故不升 HIGH；但页面上「计算依据」面板会变成一个空壳
（见 L3），且 `_derive_trace_warn` 只看 trace step 的 status，
对「排版器挂了」这件事一无所知。建议：结构化失败时补一条 `traceWarn`。

#### M2 · `_SESSIONS` 会话内存无上限、无 TTL
`web_api/main.py:92, 152-155`。任意客户端自选 `session_id`，每次 `/chat` 追加两条历史，
字典从不清理。限流（heavy 20 次/分）压住了增速，但长跑进程内存只增不减。
且 `_SESSIONS` 写进去之后**当前没有任何读取方**（`_run_answer` 不把历史传给 loop），
即这份内存目前是纯负担。判 MEDIUM（可用性/资源，非正确性）。

#### M3 · `lib/codex.ts` 抛的错不带状态码，导致 503/404 被说成「后端没起来」
`web/src/lib/codex.ts:25-29` `throw new Error("后端返回 ${resp.status}")`；
消费方 `app/codex/page.tsx:86-88, 97-99`、`app/simulator/page.tsx:32-34, 117-119`
一律 `setError(BACKEND_HINT)` = 「无法连接后端。请确认 web_api 已启动」。
后端返回 503「结构库未构建」时它**明明活着**，最该修的（db 卷没挂）被这句话盖掉。
`lib/wiki.ts:95-102` 的 `WikiApiError` 已经把正确做法做出来了——codex 这条线没跟上。

#### M4 · 子浏览器 503 时同屏出现两条互相打架的错误信息
`web/src/components/codex/CoreRulesBrowser.tsx:85-90, 108-112`、
`ChangelogBrowser.tsx:118-123, 140-144`、`KeywordIndex.tsx:218-225`
在 catch 里**无条件** `onError?.()`，而 `app/codex/page.tsx:140`
把它接成了 `setError(BACKEND_HINT)`。于是 503 时页面同时显示：
顶部「无法连接后端，请确认 web_api 已启动」+ 就地「503：后端读不到核心规则产物，
容器化部署要确认 wiki/ 只读卷挂上了」。
**同仓库已有正解**：`DetachmentBrowser.tsx:326-331` 用
`if (!(e instanceof WikiApiError)) onError()` 守住，注释写得明明白白
——「后端答了 404/503 恰恰说明它活着……真正该修的反而被"后端没起"盖过去」。
这三处就是那条注释点名要防的情形，只是没跟着改。

#### M5 · SSE 流没发 `done` 就结束 ⇒ 永远停在 streaming，输入框永久禁用
`web/src/lib/api.ts:96-108`（`reader.read()` 返回 `done:true` 即正常 `return`，
不校验是否收到过 `done` 事件）+ `web/src/components/chat/ChatApp.tsx:73`
（`onDone` 是**唯一**把 `status` 从 `"streaming"` 拨回 `"idle"` 的地方）+
`Composer.tsx:65,75`（`disabled` 绑 streaming）。
连接在 headers 之后中断、或 `_stream_answer` 生成器中途抛异常时，
`streamChat` 会**正常 resolve**，`status` 永远停在 `"streaming"`：
输入框和发送键永久禁用，页面上只留一句「机魂运算中……」，刷新才能恢复。
**判 MEDIUM 而非 HIGH**：本轮没有构造出复现——需要一个会中途断流的伪后端
（Playwright `page.route` 可做，但 e2e 要起 dev server + 系统 Chrome，
不在本轮必跑的验证集里）。按红线「跑不出复现的不升 HIGH」。

#### M6 · 「现役口径」两套（第 2 轮 M1 的第 3 轮确认）
`web_api/codex.py:33-52` 用宽口径（MFM ∪ 黑图书馆）且 docstring 写明理由。
本轮按 objective 只做一件事：**确认前端没有在展示层再叠一层过滤**——
`app/codex/page.tsx:155-163`、`UnitPicker.tsx:33-41`、`app/roster/page.tsx:240-250`
三处 `filter` 全部只按搜索串过滤，**没有任何 legacy/现役二次过滤**。
`showLegacy` 只作为 query 参数透给后端。结论：**前端未叠加，后端口径未动**。
本条留在 MEDIUM 是承接第 2 轮 M1（窄口径那三处仍待统一），不是第 3 轮新增。

#### M7 · `/codex/factions` 与 `/codex/units` 缺 fail-closed 与只读浏览端点的一致性
`web_api/main.py:220-256`：`DB_PATH.exists()` 不成立时 503（对），
但 `codex.list_factions` 内部若 sqlite 表缺失会抛 `sqlite3.OperationalError`
一路冒成 500 而非 503——与 `wiki_browse`/`core_rules_browse`/`changelog_browse`
那套「缺件 503 + 挂载提示」的成熟约定不一致。当前库完整，**未复现**，
按形状记 MEDIUM。

### 2.3 🟢 LOW（只记录）

- **L1** `web/src/app/simulator/page.tsx:27-37`：`.finally(() => setLoading(false))`
  在**被中止的旧请求**上也会跑。切阵营时旧请求的 AbortError 落到 finally，
  把新请求刚点亮的 loading 熄掉 ⇒ `UnitPicker.tsx:115-119` 短暂显示「无匹配单位」。
  瞬时、不影响最终结果，故 LOW。
- **L2** `web/src/components/sim/SimResults.tsx:169-174`：`!rep.reverse` 时固定说
  「单向模拟（攻方 → 守方）：守方幸存反打未接入本页」。但本页**已经接入**反打
  （`page.tsx:301` 有开关、`buildOptions:170-175` 会发 `reverse`）。
  正常路径下反打失败都走 `ok=false` 显式分支，所以这句话今天不会说反话；
  措辞属历史残留。LOW。
- **L3** `web/src/components/chat/CalcList.tsx:31-53`：`steps` 为空仍渲染标题栏
  「计算依据 · Adeptus Calculus」+ 空 `<ol>`。M1 触发时会看到一个空面板。LOW。
- **L4** `web/src/components/sim/LoadoutPanel.tsx:79-88`：件数输入框只有 `min={0}`，
  没有 `max`，也没有任何提示说明单把上限 400 / 总行数上限 40。是 H2 第二个后果的
  前端一侧；H2 修在后端披露即可，这条只作提示性记录。LOW。
- **L5** `web/src/lib/api.ts:65`：`line.slice(5).trim()` 对 `data:` 行整体 trim。
  当前后端 `_sse` 用 `json.dumps` 单行输出，无影响；将来若下发多行 data
  或以空白开头的字符串会失真。LOW。

### 2.4 判为**不成立**的重点核查（正面结论，供后续别再查）

以下三项是 objective 点名的高风险模式，本轮**机械核查后确认无问题**，
结论放在这里而不是 §4，因为它们是「核查通过」而非「推翻别人的怀疑」。

**契约漂移（风险模式 #2）—— 37 组模型逐字段机械对账，字段名零漂移。**
方法：`%TEMP%\r3_contract2.py` 解析 `web/src/lib/*.ts` 的 interface
（含 `extends` 继承链展开、嵌套对象体折叠），与 `web_api/contract.py`
每个模型的 `model_json_schema(by_alias=True).properties`（自引用模型解 `$ref`）取差集。

```
$ .venv/Scripts/python.exe %TEMP%\r3_contract2.py
!! TS 未找到 interface Stat

对账 38 个模型；字段名有差异的: 1
```

  唯一那条是**解析器假阳性**：`Stat` 在 TS 里被内联成匿名对象类型
  （`answer.ts:105  stats: { lab: string; val: string }[];`），不是具名 interface。
  其余 **37 组全对**：`SimResponse`/`SimReport`/`Answer`/`EntityCard`/`KeywordDetail`/
  `DetachmentDetail`/`CoreRuleChapter`/`ChangelogIndex`/`RosterIn` … 一个字段不多不少。
  （首版脚本把「可选性」也对了一遍，报出 27 组差异——那是**口径错**：
  Pydantic 的 `is_required()` 说的是**入参**必填性，而响应模型有 default 不代表
  出参会缺键，`model_dump` 照样发。已改用 schema properties 口径，不留这个误报。）

**块型/内联型覆盖 —— 后端产出的每一种前端都渲染。**
`contract.py:451-455` 的 `WikiBlock` 判别式联合共 6 型（p / ul / ol / table / h / quote / details，
其中 ul、ol 共用 `WikiListBlock`）；`Blocks.tsx:63-128` 的 switch **六型全覆盖**，
`details` 递归调 `Blocks` 渲染嵌套块。
`answer.ts:9-16` 的 `Inline` 判别式联合 6 型（text/num/kw/strong/em/cite）；
`Rich.tsx:24-58` **六型全覆盖**。两处的 `default` 分支都是「少渲一块也不整页崩」，方向正确。

**安全边界（风险模式 #5）—— 五条约定逐条仍成立。**

| 约定 | 位置 | 本轮核查 |
|---|---|---|
| 限流挂在 CORS **之前** | `main.py:82-89` | ✔ `install_rate_limit(app)` 在 `add_middleware(CORSMiddleware)` 上一行 |
| 两档配额，heavy = /chat + /simulate + /roster/critique | `ratelimit.py:21` | ✔ 三个前缀齐全；`/roster/validate` 刻意不在内（注释写明理由） |
| XFF 默认不信 | `ratelimit.py:110-125` | ✔ 需显式 `WEB_API_TRUST_FORWARDED=1` |
| options 白名单 + `n` 钳 [100,20000] | `simulate.py:73-121` | ✔ 白名单以 `dsl.py` 注册表为唯一真源（不手抄第二份）；`n` 钳制在 `:112-114` |
| 并发信号量 503 | `main.py:314-336, 386-391` | ✔ `/simulate` 与 `/roster/critique` 共用同一把闸，`finally` 释放 |
| **新增端点是否绕过** | — | ✔ 逐个核对 `main.py` 的 **21 条**路由装饰器：`/codex/*`、`/roster/*`、`/wiki/*` 全部落在 default 档；无端点绕过中间件（限流是 `@app.middleware("http")`，全局生效） |

另：`/wiki/{path:path}` 的目录穿越守卫已从 `str.startswith` 改成
`is_relative_to`（`main.py:495-502`），`detachment_detail`
（`wiki_browse.py:309-314`）与 `chapter_detail`（`core_rules_browse.py:203-208`）
各自还有第二道 slug 形态检查。三处一致，无遗漏。

---

## 3. 已修项的「改前会红 / 改后转绿」验证输出

**迭代 1 零实现代码改动**（objective 规定：第 1 次迭代只做审查），本节暂空。
H1/H2/H3 的修复与两次实测输出将在后续迭代补进本节。

---

## 4. 前两轮移交线索的结论 + 判为**不成立**的条目（附反证）

### 4.1 第 1 轮 §5 移交的两条

**线索 ④「`loadout_required` 的 `errors` 里那句『件数 ≤ 0』有没有真显示给用户」
→ 结论：没有显示。已升格为本轮 H3。** 见 §2.1 H3。

**线索 ⑤「军表两个页签同时展示两个 `total_points`（第 1 轮 M3）」
→ N2：在 UI 层不成立。**
反证：`web/src/components/roster/CritiquePanel.tsx` 全文**没有一处**渲染
`report.totalPoints`——它只渲染 `summary`、每单位的 `points`、四档 `damagePer100`、
`notModeled`。唯一显示总点数的是 `ValidationPanel.tsx:56-60`（`validate` 那一份，
即第 1 轮认定为权威的那个数）。所以「同一张表两个总分」**在页面上不会同屏出现**，
第 1 轮 M3 的用户可见影响为 0；该条仍留在第 1 轮 M3（引擎层的数确实不一致），
但**不需要**在第 3 轮连带改前端。

### 4.2 第 2 轮 §5 移交的三条

**线索 ①「现役口径以 `web_api/codex.py` 为基准，前端别再叠一层」→ 已核，前端未叠加。**
见 §2.2 M6。后端口径一字未动。

**线索 ②「通用（核心）战略 28 条落在 `core-rules/` 而非任何阵营目录，
前端按阵营遍历会让它们『消失』」→ N3：作为「诚实性缺陷」不成立，作为功能缺口成立。**
反证两条：
- 后端**根本没有**暴露这 28 条的端点：
  `grep -rn "core-rules" web_api/ web/src/` 的全部命中都指向
  `wiki/core-rules/sections/`（核心规则章节全文），**没有任何路由读
  `wiki/core-rules/stratagems/`**（实测该目录 `ls | wc -l` = 28）。
  即这不是「前端遍历漏了后端给的东西」，而是这条数据从未接进 web。
- 「分队」页签**没有做过任何全量断言**：`DetachmentBrowser` 只显示每个分队自己的
  `stratagemCount`（来自该分队页的链接数），全页没有一处「共 N 条战略」的头条数字。
  对照 `ChangelogBrowser.tsx:160-165` 是**有**「共 {index.total} 条」头条断言的
  ——那一页因此配了后端逐条对账（`changelog_browse._reconcile`）。
  所以分队页不存在「数字对不上」这回事。
**结论**：记为功能缺口（§5 遗留 W1），不记缺陷。

**线索 ③「第 1 轮那两条仍有效」→ 已在 4.1 逐条给结论。**

### 4.3 本轮自查中排除的其它怀疑

**N4「`Answer.degraded` 存进 state 却从不渲染 ⇒ 降级答案看着像正常答案」——不成立。**
反证：`grep -rn "degraded" web/src/` 显示该布尔确实只在
`ChatApp.tsx:62` 写入、无处读取；**但降级本身是通过文字披露的**——
`web_api/formatter.py:84-88 _derive_summary` 在 `degraded` 为真时把
「已降级兜底」拼进 `summary`，而 `ChatApp.tsx:98` 把 summary 交给
`AnswerHead` 渲染在应答头右侧。降级答案的正文（如「本站为轻量部署，
规则问答未启用……」）也完整走 `verdict.lede`。用户看得到。
该布尔字段冗余属 LOW 级冗余，不记缺陷。

**N5「`_match_weapon` 的『命中 N 个同名 profile』会让用户从面板里选到歧义武器」——不成立。**
反证（`%TEMP%\r3_probe1.py`，遍历全库 1715 个单位 × 两个阶段）：

```
同阶段同名多 profile 的 (单位,阶段,武器) 组合数: 0
```

`_match_weapon:91-95` 先按 phase 收窄，收窄后同名多 profile 全库 0 组。
该分支从 UI 不可达（H3 里已如实交代）。

**N6「`web_api/entity_card.py:_points_str` 也踩了 H1 那个坑」——不成立。**
反证：`_points_str:87-94` 读的是 `ds["points_options"]`，
那是 `db_compile.datasheet.Datasheet` dataclass 的字段（**真列表**），
不是 `points_json` 那个 JSON 字符串。实测兵牌页点数正常显示（e2e `codex.spec.ts` 通过）。
只有 `codex._min_points` 一处读错。

---

## 5. 三轮合计的遗留清单

**读法**：本表汇总三轮全部 MEDIUM / LOW / 疑似（HIGH 已全部修完，不在表内）。
「当前影响」栏是**实测**结论，不是估计。用户可据此决定后续做什么。

### 5.1 MEDIUM（15 条）

| 编号 | 文件:行 | 一句话 | 当前影响 |
|---|---|---|---|
| R1-M1 | `agent/loop.py:78-80` + `agent/tools.py:322-323` | `calc_points` 参数类型错被判成「空结果」当场降级，模型失去改参重试机会 | 答案仍诚实，损失的是恢复能力 |
| R1-M2 | `engines/simulator/fight_order.py:142-151` | 镜像对局下 COUNTEROFFENSIVE 归属用名字判定，答反（「你本就先打」） | 只影响建议文案，不影响 order/first_side |
| R1-M3 | `engines/roster/critique.py:160` | `critique.total_points` 漏计强化点数，与 `validate` 差 20 分 | **UI 层不显示**（第 3 轮 N2 证），仅引擎层不一致 |
| R1-M4 | `agent/tools.py:489-504` | 裸 `except Exception: pass` 连 `stat_conflicts` 诚实披露一起吞 | 未构造出触发输入 |
| R1-M5 | `engines/simulator/effect_params.py:408-419 / 450-458` | 守方消费点白名单被手抄第二份，披露文案漏 4 个已接通消费点 | 两份当前等价，文案已失真 |
| R1-M6 | `engines/simulator/parse.py:93-103` | `parse_ap` 无法解析一律归 0，与 `norm_stat_int` 不对称 | 真库 **0 行**受影响 |
| R2-M1 | `db_compile/zh_weapons.py:476-481,512-517`、`dup_units.py:132-145` | 「现役单位」窄口径少 141 个在售单位（宽口径基准在 `web_api/codex.py:33-52`） | 两口径今天都 100%，无隐藏缺译 |
| R2-M2 | `wiki_engine/lint.py:54-64,144-175` | 生成物里 4809 条 wikilink 从不被 lint 检查 | 实测 **0 断链** |
| R2-M3 | `corpus_manifest.py:59-70` | 27 本未登记 PDF 静默回退 defaults，ingest 汇总不可区分 | 27 本**逐本核对全对**，0 例误分类 |
| R2-M4 | `db_compile/update.py:483-521` | `_RESTORE_STAGES` 是 `_PIPELINE` 的人工副本，缺「写库层必须都在」的通用断言 | 10/10 都在，顺序一致 |
| R2-M5 | `scripts/qa_bench.py:311-321` | `parse_verdict` 判词同时含 ✅❌ 时永远判 ✅ | 扫 56 个结果文件，双标记判词 **0 条** |
| R2-M6 | `db_compile/enhancements.py:82-87,102` | 无 id 行静默丢弃，`inserted` 报过滤后的数 | `--check` 能逮到，`--apply` 单跑没门 |
| R2-M7 | `wiki_engine/_io.py:46-59` | 登记表损坏即返回 `{}`，人工编辑保护整体静默失效 | 原子写，损坏概率低 |
| **R3-M6** | 见 R2-M1 | 第 3 轮确认：前端未在展示层叠加二次过滤 | — |
| **R3-M7** | `web_api/main.py:220-256` | `/codex/factions`、`/codex/units` 缺表级 fail-closed，表缺失会 500 而非 503 | 库完整，未复现 |

（第 3 轮新增的 M1–M5 见下表，与上表分开是因为它们是本轮**新发现**。）

| 编号 | 文件:行 | 一句话 | 当前影响 |
|---|---|---|---|
| R3-M1 | `web_api/formatter.py:164-172` | 结构化 LLM 失败静默退化，不标 `traceWarn`/`degraded` | 答案本体不伪造；「计算依据」变空面板 |
| R3-M2 | `web_api/main.py:92,152-155` | `_SESSIONS` 无上限无 TTL，且写进去后当前无人读 | 限流压住增速，长跑内存只增不减 |
| R3-M3 | `web/src/lib/codex.ts:25-29` | 抛的错不带状态码，503/404 全被说成「后端没起来」 | 误导排查方向 |
| R3-M4 | `CoreRulesBrowser.tsx:85-90,108-112`、`ChangelogBrowser.tsx:118-123,140-144`、`KeywordIndex.tsx:218-225` | 503 时同屏两条互相打架的错误信息（`DetachmentBrowser` 已有正解未跟进） | 同上 |
| R3-M5 | `web/src/lib/api.ts:96-108` + `ChatApp.tsx:73` | SSE 没发 `done` 就断流 ⇒ 永远停在 streaming，输入框永久禁用 | **未复现**（缺断流伪后端） |

### 5.2 LOW（13 条）

| 编号 | 文件:行 | 一句话 |
|---|---|---|
| R1-L1 | `agent/llm_client.py:180-182` | 工具返回超 4000 字被截断（有「…（已截断）」标记，非静默） |
| R1-L2 | `llm_refine.py:245-248` | 兜底页 meta 写 `verify_ok: True`——没被校验过却自称通过 |
| R1-L3 | `llm_refine.py:142-163` | `_refine_coverage` 分母含空白页，覆盖率数学上到不了 1.0 |
| R1-L4 | `ingest.py:320/378/429-431` | 增量去重按路径原样字符串匹配，相对/绝对路径混用会新旧 chunk 并存 |
| R2-L1 | `wiki_engine/keyword_index.py:196-199` | `keywords_json` 解析失败 `continue` 且不计数（无 `bad_json` 桶） |
| R2-L2 | `wiki_compile/extract.py:106-110` | 噪声标题先于主标题出现时静默丢页码（同文件另一处是有告警的） |
| R2-L3 | `db_compile/fp_errata.py:179-204` | 判据 `(faction_id,name_en)` 但写入固定 `unit_id`，同 id 换名会抹 `name_zh`/`points_json` |
| R2-L4 | `wiki_compile/terms.py:44` | 备份文件名带 `strftime` 时间戳（不进仓库产物，无假 diff） |
| **R3-L1** | `web/src/app/simulator/page.tsx:27-37` | 被中止的旧请求也跑 `finally`，把新请求的 loading 提前熄掉 ⇒ 闪现「无匹配单位」 |
| **R3-L2** | `web/src/components/sim/SimResults.tsx:169-174` | 「守方幸存反打未接入本页」是历史残留措辞，本页其实已接入 |
| **R3-L3** | `web/src/components/chat/CalcList.tsx:31-53` | `steps` 为空仍画标题栏，出现空面板 |
| **R3-L4** | `web/src/components/sim/LoadoutPanel.tsx:79-88` | 件数框无 `max`、无上限提示（H2 的前端一侧） |
| **R3-L5** | `web/src/lib/api.ts:65` | `data:` 行整体 `trim()`，将来多行 data / 前导空白会失真 |

### 5.3 疑似（3 条，均未复现出实际错误输出）

| 编号 | 文件:行 | 一句话 | 为什么没复现 |
|---|---|---|---|
| R1-M7 | `app.py:396-397` | `merged` 为空时直接 return，规则层保底结果被丢弃 | 构造不出「主检索空而 `layer=rules` 过滤非空」的现实输入（共用同一 vectorstore） |
| R2-M8 | `db_compile/mfm.py:228-234,120-135` | 断裂探测只覆盖「有表头且 0 行」，覆盖不到**部分**丢行 | 需联网抓真实 HTML 才能构造版式；缓存只存解析后的行，无法回放 |
| R2-M9 | 分队容器 325 vs 分队页 324 | 差 1 未定因 | 确认需跑 `wiki_engine entities` 取报告，会重写 wiki 产物（红线禁止） |

（R3-M5「SSE 断流卡死」按同一纪律未复现，但因为路径清晰、可用 Playwright
`page.route` 构造，故留在 MEDIUM 而非疑似；若后续也造不出来应降为疑似。）

### 5.4 功能缺口（不是缺陷，但用户可能想做）

- **W1** 通用（核心）战略 **28 条**（`wiki/core-rules/stratagems/`，实测 28 页）
  从未接进 web——没有后端路由、前端也没有对应页签。
  第 2 轮已证 1653（阵营）+ 28（核心）= 1681（库内战略总数），**一条不少**，
  只是这 28 条在网站上看不到。见 §4.2 N3。
- **W2** e2e 4 条用例全走 happy path，**没有一条**覆盖错误路径
  （503 / 超上限入参 / 装配失败 / 断流）。本轮 H2、H3 正落在这个盲区里。
- **W3** 前端没有任何单测框架（`package.json` 只有 `@playwright/test`），
  纯函数（`buildOptions` / `parseBlock` / `fmt`）无法低成本回归。

---

## 6. 本轮实际数字

### 迭代 1（只审查，零实现代码改动）

| 项 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `.venv\Scripts\python.exe -m pytest -q` | **2421 passed, 0 failed**（168.12s）— 与起跑基线一致 |
| 前端 lint | `cd web && npm run lint` | **0 error**（eslint 无输出） |
| 前端 build | 未跑 | 本迭代**零前端代码改动**，按 objective 免跑 |
| wiki lint | 未跑 | 未触碰 wiki 相关代码 |
| 基准 | 未跑 | 未碰 `agent/`、未改库、未改索引 |
| 工作区 | `git status --porcelain` | 仅本报告一个新文件 |

复现脚本全部写在系统临时目录、未入仓库：
`%TEMP%\r3_probe1.py`（同名 profile 全库扫描）、
`r3_probe2.py` / `r3_probe6.py`（H1 量化）、
`r3_probe3.py`（H2 件数超限 + H3 errors）、
`r3_probe4.py` / `r3_probe5.py`（H2 模型数超限假成功）、
`r3_contract.py` / `r3_contract2.py`（契约机械对账）。
全部以 `mode=ro` 或只读方式访问 `db/wh40k.sqlite`，**零写入**。

### 红线自查

- ✔ 未写 `db/wh40k.sqlite`（探针全部 `sqlite3.connect(..., uri=True, mode=ro)` 或只读查询）
- ✔ 未改 `benchmarks/**/qa_gold*.json`
- ✔ 未重新生成 `wiki/` 产物
- ✔ 未改本轮范围外的 `agent/` `engines/` `app.py` `db_compile/` `wiki_engine/` `scripts/`
- ✔ 临时脚本在 `%TEMP%`，`git status` 干净

### 未完成项（如实登记）

1. **H1 / H2 / H3 尚未修复** —— 按 objective 的迭代节奏，第 1 次迭代只做审查，
   修复留给后续迭代（每次 1-3 条 + 配测试 + 实测「stash 掉实现真会红」）。
2. **R3-M5（SSE 断流卡死）未复现** —— 需要一个会中途断流的伪后端。
   Playwright `page.route` 可以做到，但要起 dev server + 系统 Chrome，
   不在本轮必跑验证集内。已按红线降级处理（MEDIUM，不进 HIGH）。
3. **R2-M9（分队 325 vs 324）本轮同样未定因** —— 定因需跑
   `python -m wiki_engine entities`，会重写 wiki 产物，红线禁止。

---

## 7. 下一次迭代要做的事

1. 修 **H1**（`web_api/codex.py:_min_points` 改读 `items[].cost` 取 min），
   配 pytest 护栏：断言真库上 `list_units("TAU")` 的 `pts` 非 null 数 > 0
   且格式为「N 分起」；实测 stash 掉实现会红。
2. 修 **H2**（`web_api/simulate.py` 超上限入参不再静默丢弃——
   **保持不钳制**，改为在响应里显式披露被丢弃的入参），配 pytest 护栏。
3. 修 **H3**（`web/src/app/simulator/page.tsx` 渲染 `resp.errors`），
   改了前端就必须 `npm run build` 通过。
4. 每条改完立刻验证并把两次输出补进 §3。
