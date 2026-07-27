# MFM `_KEEP_SECTIONS` 覆盖缺口修复（2026-07-27）

**结论先行**：上一轮 §6 点名的 `_KEEP_SECTIONS` 误伤已修完。对 30 个阵营页的**全部**
h3 小节逐个做了数据判定（不靠小节名猜），把 **60 个**「阵营自己的单位列在子标题下」
的表头纳入比对池，把 **442 个**「同一单位的第二套价」继续排除。

`mfm --check` 从 **1243 可比 / 1243 一致 / 过期 0**
变成 **1319 可比 / 1273 一致 (96.5%) / 过期 46**。

**一致率从 100% 掉到 96.5% 是本轮最有价值的产出**：那 46 条不是新出现的错误，而是
**一直存在、但因为整段小节被切掉而从来没人比对过**的过期点数——包括基里曼
（库 340 / 官网 355）。旧的 1243 条**一条都没退化**（新增 76 条比对 = 30 一致 + 46 过期）。

**未 apply**，理由见 §5：46 条点数差本身可信且逐条可溯源，但 apply 会连带给
**67 个**单位新写 `points_json["mfm"]`，而该键在四处被当「现役」判据用——
翻转现役口径需要连同 wiki 重生成一起做，正是上一轮明确记下的「要合并做否则重生成两次」的遗留。

---

## 1. 备份路径（出事可回滚）

抓取前备份，均在系统临时目录（不落仓库）：

| 文件 | 备份路径 | 字节 | SHA-256 |
|---|---|---:|---|
| MFM 缓存 | `%TEMP%\mfm-sections-2026-07-27\backup\mfm_points.json` | 158,816 | `F476BE1B3D7455B2931A02ECCED43A21729E252A9A177E5F38B3D6CAA6B0AB58` |
| 主库 | `%TEMP%\mfm-sections-2026-07-27\backup\wh40k.sqlite` | 14,581,760 | `2DC2108E5E9F58DCEB39F56041250D624951CDEB249AE39225DEB853D555B4DD` |

主库本轮**全程未写**（SHA-256 与上一轮报告 §1 记录的一致，可交叉核对）。
临时脚本、30 页 HTML 快照、库副本、各步输出都在
`%TEMP%\mfm-sections-2026-07-27\`；仓库内只改 `db_compile/mfm.py` +
`tests/test_db_compile_mfm.py`，新增本报告。

## 2. 判定方法：用数据，不用小节名

对 30 页逐个 h3 小节切开，统计「单位表头数 / 分数行数 / 单位名清单」，
然后对**每个被排除小节**问两个纯数据问题：

1. **同一页的主小节（UNITS/FORTIFICATIONS）里，这个单位是否已经定过价？**
   定过 ⇒ 这里是同一单位的第二套价（条件价 / 战团差异价）⇒ 继续排除。
2. **全站还有没有别的页给这个单位定价？库里这个阵营有没有对应行？**
   用来判「它的主阵营是不是在别处」。

判定脚本三个，产物均在临时目录：`survey.py`（切小节）、`judge.py`（本阵营重叠）、
`cross.py`（跨页重叠）、`dbcheck.py`（库侧核对）。

## 3. 逐小节判定结论

被排除小节合计 **502 个单位表头 / 833 个分数行**，四类：

### 3.1 ❌ 误伤 → 本轮纳入（12 个小节 / 60 个表头）

判据：这些单位在**本阵营主小节里一个都没有**（重叠 0/N）。

| slug | 小节 | 表头 | 本阵营主小节已有 | 仅此处 | 判定 |
|---|---|---:|---:|---:|---|
| space-marines | ULTRAMARINES | 8 | 0 | 8 | 纳入（基里曼在此） |
| space-marines | IMPERIAL FISTS | 3 | 0 | 3 | 纳入 |
| space-marines | IRON HANDS | 2 | 0 | 2 | 纳入 |
| space-marines | SALAMANDERS | 2 | 0 | 2 | 纳入 |
| space-marines | RAVEN GUARD | 2 | 0 | 2 | 纳入 |
| space-marines | WHITE SCARS | 2 | 0 | 2 | 纳入 |
| aeldari | HARLEQUINS | 8 | 0 | 8 | 纳入 |
| aeldari | YNNARI | 11 | 0 | 11 | 纳入 |
| death-guard | PLAGUE LEGIONS | 6 | 0 | 6 | 纳入（见 3.2） |
| thousand-sons | SCINTILLATING LEGIONS | 6 | 0 | 6 | 纳入（见 3.2） |
| world-eaters | BLOOD LEGIONS | 5 | 0 | 5 | 纳入（见 3.2） |
| emperors-children | LEGIONS OF EXCESS | 5 | 0 | 5 | 纳入（见 3.2） |

其中 **38 个全站唯一**（跨页也只在这一处有价）：Harlequins 8 + Ynnari 11 +
SM 战团英雄 19。这批毫无争议——`ROBOUTE GUILLIMAN` 在全站只有
`space-marines / ULTRAMARINES` 一处定价，整段丢掉他就永远不在比对池里。

### 3.2 四个 `LEGIONS` 小节：上一轮说「还没核实」的，本轮实际核过了

`PLAGUE LEGIONS` / `SCINTILLATING LEGIONS` / `BLOOD LEGIONS` / `LEGIONS OF EXCESS`
里的 **22 个单位全部也出现在 `chaos-daemons` 页**（大不洁者、血怒魔、色孽魔女…）。
单看这一条像「盟友借调价」，应当排除。**但库侧数据推翻了这个读法**：

- `dbcheck.py` 实测：这 22 个单位在库里**同时有 CD 行和 DG/TS/WE/EC 行**
  （如 `great unclean one` → `faction_id ∈ {CD, DG}`）。库把它们建模成
  **按阵营各自独立的行**，不是一行被两个阵营共享。
- 既然库里 DG 那一行独立存在，它的权威价就是官网 death-guard 页给的价，
  而不是 chaos-daemons 页的价。比对它是**正确且有意义**的。
- 比对结果反过来证实了这一点：**CD 那些行全部一致**（本来就在旧比对池 1243 里），
  **DG/TS/WE/EC 那些行有 20 条过期**。同一张兵牌两个阵营两行、一行新一行旧——
  正是「有人管的那行是对的，没人管的那行烂掉了」。
- 官网也确实给出不同价：`BEASTS OF NURGLE` chaos-daemons 75 / death-guard 70；
  `PINK HORRORS` chaos-daemons 150 / thousand-sons 115；
  `BLOODLETTERS` chaos-daemons 110 / world-eaters 90。其余 18 个两边同价。

**结论：纳入。** 与 `imperial-agents` 那种「同一页同一单位两个价」有本质区别——
那里主小节已经定过价，这里 death-guard 主小节根本没有这些单位。

### 3.3 ✅ 正确排除 → 保持排除（442 个表头）

| 类别 | 小节 | 表头 | 与主小节重叠 | 价格冲突 | 判据 |
|---|---|---:|---:|---:|---|
| 战团页整段重印通用 SM 名录 | `SPACE MARINES`（BT 72 / BA 84 / DA 84 / DW 79 / SW 80） | 399 | **399/399 全部已在 `space-marines` 主小节** | 24 | 100% 重叠 ⇒ 第二套价 |
| 条件价 | `EVERY MODEL HAS THE IMPERIUM KEYWORD`（imperial-agents） | 29 | **29/29 全部已在同页主小节** | 16 | 100% 重叠 ⇒ 第二套价 |
| 分队名误命中 | `DETACHMENTS`（10 页） | 14 | — | — | **0 个分数行**，本来就不产生数据 |

价格冲突实例（收进来就会把一个单位拆成两个矛盾价，正是当初加白名单要挡的）：

- `INQUISITOR` imperial-agents 主小节 **55** / 条件小节 **65**
- `ASSAULT INTERCESSOR SQUAD` space-marines 主小节 **75** / blood-angels 重印段 **80**
- `REPULSOR EXECUTIONER` 通用页 **255** / DA·DW·SW 重印段各 **230**

> 注：`DETACHMENTS` 本轮实测 **14** 个表头（上一轮报告写 13，差 1，本报告以实测为准）。
> 无论 13 还是 14，它们的分数行都是 **0**，对结果零影响。

## 4. 改法：从「切小节」改成「主小节的自军价优先」

删掉 `_KEEP_SECTIONS` 整段切除，换成 `_PRIMARY_SECTIONS` + 一条**可自解释的逐单位规则**
（`db_compile/mfm.py`，`parse_mfm_html`）：

> 主小节的行全收；其余小节的行**只在该单位没被主小节定过价时**才收。

- 主小节里已有 ⇒ 第二套价 ⇒ 丢（`INQUISITOR` 的 65）
- 主小节里没有 ⇒ 该阵营列在子标题下的自己的单位 ⇒ 收（`ROBOUTE GUILLIMAN` 的 355）

没有魔法字符串名单——规则本身说明了「为什么这个小节算真单位」。
跨页那一层（战团页重印）由既有的 `_rows_by_faction`「通用页优先」再收敛一次，
行为与既有测试 `test_generic_sm_page_wins_over_chapter_page` 一致。

**顺带修掉一个共享前提**：`count_unit_headers()` 原先也走 `_slice_kept_sections()`，
所以对「整段小节被误伤」**完全无感知**（上一轮教训「校验器与被校验对象共享前提就一起瞎」
的正是这处）。现在它数**全部**表头，与小节筛选彻底正交。

副作用（已量化）：战团页那 709 行重印价现在**进了 json 缓存**（1716 → 2514 行），
但在比对时被通用页优先规则丢弃。这让模块里那句既有注释
「战团差异价完整保留在 mfm json」**从不成立变成成立**。

## 5. `mfm --check` 结果与过期条目逐条明细

```
MFM 比对（抓取时间 2026-07-27 15:14，只比基准梯度）：
  可比条目 1319  |  一致 1273 (96.5%)  |  过期 46  |  MFM 有库里无 5  |  梯度计价单位 326
```

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 可比条目 | 1243 | **1319**（+76） |
| 一致 | 1243 (100%) | **1273 (96.5%)** |
| **过期** | **0** | **46** |
| MFM 有库里无（mfm_only） | 5 | **5**（无新增） |
| db_unparsed | 0 | **0** |

**无退化证明**（`regress.py`）：旧 1243 条**全部仍然一致**；
新增 76 条 = 新一致 30 + 新过期 46；46 条过期**全部**属于本轮纳入的小节名单
（「不属于名单的过期条目」实测 **0** 条）。

### 5.1 过期条目逐条明细（46 条，库 → 官方 MFM）

**Space Marines（SM，17 条）** —— 全部来自 space-marines 页的战团小节

| 单位 | 档位 | 库 | MFM |
|---|---|---:|---:|
| Roboute Guilliman | 1 model | 340 | **355** |
| Marneus Calgar in Armour of Antilochus | 1 model | 140 | **155** |
| Captain Titus | 1 model | 90 | **100** |
| Cato Sicarius | 1 model | 95 | **105** |
| Uriel Ventris | 1 model | 95 | **105** |
| Chief Librarian Tigurius | 1 model | 75 | **85** |
| Victrix Honour Guard | 6 models | 220 | **230** |
| Wardens of Ultramar | 6 models | 105 | **120** |
| Pedro Kantor | 1 model | 90 | **80** |
| Tor Garadon | 1 model | 90 | **80** |
| Caanok Var | 1 model | 100 | **90** |
| Iron Father Feirros | 1 model | 95 | **85** |
| Adrax Agatone | 1 model | 85 | **80** |
| Vulkan He’stan | 1 model | 100 | **85** |
| Aethon Shaan | 1 model | 110 | **100** |
| Kor’sarro Khan | 1 model | 60 | **55** |
| Suboden Khan | 1 model | 115 | **90** |

**Aeldari（AE，9 条）** —— HARLEQUINS / YNNARI 小节

| 单位 | 档位 | 库 | MFM |
|---|---|---:|---:|
| Death Jester | 1 model | 90 | **70** |
| Shadowseer | 1 model | 60 | **50** |
| Starweaver | 1 model | 80 | **70** |
| Voidweaver | 1 model | 125 | **115** |
| The Yncarne | 1 model | 260 | **245** |
| Ynnari Incubi | 5 models | 85 | **80** |
| Ynnari Incubi | 10 models | 170 | **160** |
| Ynnari Raider | 1 model | 80 | **70** |
| Ynnari Venom | 1 model | 70 | **65** |

**Death Guard（DG，9 条）· Thousand Sons（TS，2 条）· Emperor's Children（EC，5 条）· World Eaters（WE，4 条）** —— 四个 `LEGIONS` 小节

| 阵营 | 单位 | 档位 | 库 | MFM |
|---|---|---|---:|---:|
| DG | Beasts of Nurgle | 1 model | 65 | **70** |
| DG | Beasts of Nurgle | 2 models | 130 | **140** |
| DG | Great Unclean One | 1 model | 250 | **265** |
| DG | Nurglings | 3 models | 40 | **45** |
| DG | Nurglings | 6 models | 70 | **90** |
| DG | Plaguebearers | 10 models | 110 | **115** |
| DG | Plague Drones | 3 models | 115 | **110** |
| DG | Plague Drones | 6 models | 230 | **220** |
| DG | Rotigus | 1 model | 265 | **280** |
| TS | Kairos Fateweaver | 1 model | 295 | **305** |
| TS | Lord of Change | 1 model | 285 | **320** |
| EC | Keeper of Secrets | 1 model | 240 | **255** |
| EC | Shalaxi Helbane | 1 model | 340 | **315** |
| EC | Fiends | 3 models | 95 | **90** |
| EC | Fiends | 6 models | 190 | **180** |
| EC | Seekers | 10 models | 160 | **155** |
| WE | Bloodthirster | 1 model | 305 | **320** |
| WE | Skarbrand | 1 model | 305 | **315** |
| WE | Bloodcrushers | 3 models | 110 | **95** |
| WE | Bloodcrushers | 6 models | 220 | **190** |

### 5.2 抽查：官网原文核对

从原始 HTML 抠出分数段落人工目检，全部与解析值一致；且多数带 **▲/▼ 变动标记**
——说明这些是**本版官网刚改的价**，库（Wahapedia 镜像）还没跟上：

```
ROBOUTE GUILLIMAN | ▲ | YOUR UNIT COSTS | 1 model | ▲ (+15) 355 pts
SUBODEN KHAN      | ▼ | YOUR UNIT COSTS | 1 model | ▼ (-10) 90 pts
DEATH JESTER      | ▼ | YOUR UNIT COSTS | 1 model | ▼ (-10) 70 pts
LORD OF CHANGE    | ▲ | YOUR 1ST TO 2ND UNITS COST | 1 model | ▲ (+20) 320 pts
PEDRO KANTOR      |   | YOUR UNIT COSTS | 1 model | 80 pts
```

## 6. apply 与否：**不 apply**

按红线要求，先在**库副本**上试跑并逐字段 diff（真库全程未写，`dryrun_apply.py`）：

```
apply 报告: 匹配 1019 单位 / 更新 46 个
**档位点数发生变化的条目: 46**       ← 与 --check 的 46 条过期逐条吻合
**顶层 points 变化: 46**
**新获得 points_json['mfm'] 溯源: 67**
**仅刷新 fetched_at 时间戳的单位: 962**
apply 后收敛校验（副本上）：可比 1319 / 一致 1319 / 过期 0
```

不 apply 的理由：

1. **`points_json["mfm"]` 会新写给 67 个单位，翻转「现役」口径。**
   该键在四处被当现役判据用：`wiki_engine/keyword_index.py:169`、
   `db_compile/zh_weapons.py:478,514`、`web_api/codex.py:46`、`db_compile/dup_units.py:145`。
   这 67 个 = 本轮新纳入的 60 个 + 上一轮遗留的 7 个 ≥1000 分单位。
   把它们翻成现役**事实上是对的**，但必须连带 wiki 重生成 + 现役计数重新对账，
   而上一轮报告已明确记下这件事「应与 apply 遗留合并做，否则 wiki 重生成两次」。
2. **顶层 `points` 会改 46 个，其中多条是大幅语义修正**——
   `AE/Troupe 580→85`、`SM/Victrix Honour Guard 330→110`、`WE/Bloodcrushers 330→95`：
   库里存的是 Wahapedia 各档累加和，`apply_points` 按设计改成基准档最小值。
   这个修正本身是对的，但**从未在这批单位上跑过**，值得单独一轮验证，不该顺手带过。
3. 本轮职责是「修覆盖缺口」。缺口已修、46 条差异已完整披露且可溯源——
   这正是本轮要交付的东西。写库是下一轮的独立动作。

**遗留（建议下一轮合并做，一次做完）**：
`mfm --apply` → wiki 重生成 → 现役计数对账 → 顶层 `points` 语义修正复核。
副本上已验证 apply 后收敛到 **1319 / 1319 / 过期 0**，路径是通的。

## 7. 验证

| 项 | 结果 |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | **2359 passed**（基线 2353 + 本轮新增 6） |
| 新判定逻辑有测试 | `TestSubFactionSectionCoverage` 6 条 |
| 护栏「真会红」 | 对旧实现跑新用例：**6 条里 4 条红**（另 2 条是有意的负向成对，旧实现本就正确） |
| `python -m wiki_engine lint` | **0 error** / 1 warning / 4 info（与基线持平） |
| `cd web && npm run lint` | **0 error** |
| `git status` | 只改 `db_compile/mfm.py` + `tests/test_db_compile_mfm.py` + 本报告；缓存与库 gitignored |
| 行尾 | 两文件全 CRLF 且 `git diff --ignore-cr-at-eol` 与普通 diff 逐字节同 stat（无假 diff） |

新增 6 条测试：

- `test_sub_faction_section_units_are_kept` —— 基里曼型：主小节没有 ⇒ 收
- `test_second_price_for_already_priced_unit_is_dropped` —— 负向成对：条件价 ⇒ 丢
- `test_both_semantics_resolved_on_one_page` —— 同页两种语义各判各的（靠小节名猜会翻车处）
- `test_headerless_page_still_parsed_whole` —— 无 h3 异常版式仍整篇当主小节
- `test_header_count_does_not_share_section_filtering` —— 校验器不与被校验对象共享前提
- `test_chapter_page_bulk_reprint_does_not_beat_generic_page` —— 战团差异价不得夺权

## 8. 教训

1. **「同一单位在别处也有价」不足以判它是借调价。** 四个 `LEGIONS` 小节里的 22 个单位
   全都在 `chaos-daemons` 页有价，单看这条会判「排除」——但库把它们建模成按阵营
   各自独立的行，DG 那行的权威价就在 death-guard 页。**判据要落到「库里被比对的那一行
   是谁」，而不是「这个名字在别处出现过没有」。** 比对结果反过来印证：CD 行全对、
   DG/TS/WE/EC 行 20 条过期——有人管的行是对的，没人管的行烂掉了。
2. **一致率 100% 可能是「比得少」而不是「数据好」。** 修复前 1243/1243 看着完美，
   其实 60 个单位压根没进池子，其中 38 个的点数是错的。
   **覆盖面指标必须和一致率指标一起看**，只报后者等于自欺。
3. **整段白名单是覆盖缺口的高发形态。** `_KEEP_SECTIONS` 和千分位正则是同一个失效模式的
   两个实例：不报错、指标好看、覆盖面无声塌掉。这次换成**逐单位、可自解释的规则**
   （主小节优先），而不是再列一张更长的小节名单——名单会继续过期，规则不会。
4. **校验器必须与被校验对象走不同代码路径。** `count_unit_headers()` 原先跟着
   `_slice_kept_sections()` 走，所以对整段误伤全无感知。这次把它改成不走小节筛选，
   代价是它会多数一些重复表头（只用于「>0 表头却 0 行」的断裂判定，不做等值对账）。
5. **`--check` 的差异条数不等于 apply 的影响面。** 46 条点数差，apply 却会动
   67 个单位的现役口径 + 46 个顶层 points + 962 个时间戳。副本逐字段 diff 是唯一
   看得清的办法，第二轮照做，第二轮同样靠它拦下了一次范围外的写库。
