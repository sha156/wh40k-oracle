# MFM 全站重抓与官方点数校验（2026-07-27）

**结论先行**：全站重抓成功，逐阵营行数对账**零差额**（30 个阵营全部 +0，合计 1716→1716），
`mfm --check` **可比 1243 / 一致 1243 (100.0%) / 过期 0**。上一轮点名的那 7 个
「从未被官方点数校验过」的 ≥1000 分单位**全部进入比对池且逐个一致**。

**未 apply**，理由见 §5——差异为 0，`apply_points` 自报 `units_updated=0`，
apply 唯一的实际效果是给 7 个单位补 `points_json["mfm"]` 溯源标记，
而那个标记在下游被当「现役」判据用，会牵动 wiki 重生成，超出本轮范围。

顺带查出**同一类静默丢行的第二处实例**（`_KEEP_SECTIONS` 排除掉了基里曼所在的
战团小节，全站约 60 个真实单位从未进过比对池），见 §6，**本轮未改**。

---

## 1. 备份路径（出事可回滚）

抓取与比对前先备份，两份都在系统临时目录（不落仓库）：

| 文件 | 备份路径 | 字节 | SHA-256 |
|---|---|---:|---|
| MFM 缓存 | `C:\Users\Administrator\AppData\Local\Temp\mfm-backup-2026-07-27-iter1\mfm_points.json` | 158,794 | `9C8339F6D1AC67AF3BB65CD3FF02EF82EBC23C7B11957F5DF77CB83F1B708FA7` |
| 主库 | `C:\Users\Administrator\AppData\Local\Temp\mfm-backup-2026-07-27-iter1\wh40k.sqlite` | 14,581,760 | `2DC2108E5E9F58DCEB39F56041250D624951CDEB249AE39225DEB853D555B4DD` |

本轮全部临时脚本与中间产物在 `C:\Users\Administrator\AppData\Local\Temp\mfm-new-2026-07-27\`
（对账脚本、30 个阵营页 HTML 快照、各步输出）。
仓库内**只新增本报告一个文件**；`db_sources/` 与 `db/` 均被 `.gitignore` 覆盖，
重抓后 `git status` 仍是 clean。

## 2. 重抓

先按纪律测连通（`Test-NetConnection 127.0.0.1:7897` → True；
venv python 直连 MFM 首页 → `status 200 / 74143 bytes / 4.2s`），再抓：

```powershell
$env:HTTP_PROXY='http://127.0.0.1:7897'; $env:HTTPS_PROXY='http://127.0.0.1:7897'
.\.venv\Scripts\python.exe -m db_compile mfm --fetch --json <临时路径>\mfm_points.json
```

抓进**临时路径的旧缓存副本**上，这样 `_guard_cache_regression()` 仍有对账基准
（直接抓新路径会因「旧文件不存在」而跳过护栏）。结果：
`failed=[]`、`parse_broken=[]`、30 阵营 1716 行，护栏放行。
核对无误后才覆盖回 `db_sources/mfm/mfm_points.json`。

## 3. 逐阵营行数对账

### 3.1 新旧缓存对账（旧 = 2026-07-26 05:03，新 = 2026-07-27 14:37）

**30 个阵营行数差全部为 0，合计 1716 → 1716（+0）**；逐条 `(单位, 档位, 模型数)`
键比对，**新增 0 / 消失 0 / 变价 0**。

| slug | 旧 | 新 | 差 | | slug | 旧 | 新 | 差 |
|---|---:|---:|---:|---|---|---:|---:|---:|
| adepta-sororitas | 54 | 54 | +0 | | imperial-agents | 35 | 35 | +0 |
| adeptus-custodes | 67 | 67 | +0 | | imperial-knights | 41 | 41 | +0 |
| adeptus-mechanicus | 67 | 67 | +0 | | leagues-of-votann | 42 | 42 | +0 |
| aeldari | 83 | 83 | +0 | | necrons | 98 | 98 | +0 |
| astra-militarum | 124 | 124 | +0 | | orks | 104 | 104 | +0 |
| black-templars | 36 | 36 | +0 | | space-marines | 151 | 151 | +0 |
| blood-angels | 30 | 30 | +0 | | space-wolves | 47 | 47 | +0 |
| chaos-daemons | 71 | 71 | +0 | | tau-empire | 75 | 75 | +0 |
| chaos-knights | 35 | 35 | +0 | | thousand-sons | 52 | 52 | +0 |
| chaos-space-marines | 91 | 91 | +0 | | **titan-legions** | **4** | **4** | **+0** |
| **chaos-titan-legions** | **4** | **4** | **+0** | | tyranids | 94 | 94 | +0 |
| dark-angels | 24 | 24 | +0 | | world-eaters | 44 | 44 | +0 |
| death-guard | 47 | 47 | +0 | | | | | |
| deathwatch | 17 | 17 | +0 | | | | | |
| drukhari | 45 | 45 | +0 | | | | | |
| emperors-children | 29 | 29 | +0 | | | | | |
| genestealer-cults | 48 | 48 | +0 | | | | | |
| grey-knights | 57 | 57 | +0 | | **合计** | **1716** | **1716** | **+0** |

判据对照：既没有「几乎每个阵营系统性掉 ~20% 行」（那是解析器被版式打断的指纹），
也没有真·点数更新（本版官网自 07-26 起未动）。**放行**。

### 3.2 「0 行 → 4 行」发生在哪一代缓存

预期的 `titan-legions` / `chaos-titan-legions` **0→4** 在本次对账里看不见，
因为它**已经发生在上一轮**：上一轮修完正则后用 `mfm --slug <阵营>` 定点补抓，
而 `--slug` 分支只合并该阵营并保留原 `fetched_at`——所以「旧」缓存虽标
`2026-07-26 05:03`，文件 mtime 却是 `2026-07-27 14:06`，里面已有 4+4 行。

真正的修复前基线是仓库里那份 `mfm_points.json.bak-0719`：

| 缓存代 | fetched_at | 合计行 | titan-legions | chaos-titan-legions |
|---|---|---:|---:|---:|
| `bak-0719`（修正则**之前**） | 2026-07-19 04:03 | 1670 | **0** | **0** |
| 旧备份（上一轮 `--slug` 补抓后） | 2026-07-26 05:03 | 1716 | 4 | 4 |
| **本轮全站重抓** | **2026-07-27 14:37** | **1716** | **4** | **4** |

本轮的价值在于：**用一次全站重抓独立复现了那 8 行**，证明它不是定点补抓的偶然产物，
而且顺带证明全站其余 1708 行一行没丢。四条泰坦行的原始值：

```
titan-legions:        WARHOUND TITAN 1100 / REAVER TITAN 2200 /
                      WARBRINGER NEMESIS TITAN 2600 / WARLORD TITAN 3500
chaos-titan-legions:  同名加 CHAOS 前缀，四个价格逐一相同
```

### 3.3 `count_unit_headers()` 独立交叉验证

用与分数行正则**正交**的表头计数器，对 30 个阵营页逐页比「表头数 vs 解析出的去重单位数」：

**30/30 页完全相等**（合计 968 表头 = 968 单位，1716 行）。摘录：

| slug | 表头数 | 去重单位数 | 行数 | 一致 |
|---|---:|---:|---:|:--:|
| space-marines | 84 | 84 | 151 | ✅ |
| astra-militarum | 72 | 72 | 124 | ✅ |
| orks | 57 | 57 | 104 | ✅ |
| necrons | 52 | 52 | 98 | ✅ |
| **titan-legions** | **4** | **4** | **4** | ✅ |
| **chaos-titan-legions** | **4** | **4** | **4** | ✅ |
| …（其余 24 页同样 ✅） | | | | |

没有任何一页出现「表头 N 个却只解析出 M<N 个单位」——即分数行正则对现行版式零断裂。

### 3.4 明星单位证伪法抽查

抽查绝无可能被官方移除的单位，全部命中：

| 阵营 | 单位 | 结果 |
|---|---|:--:|
| world-eaters | ANGRON | ✅ |
| adepta-sororitas | MORVENN VAHL | ✅ |
| orks | GHAZGHKULL THRAKA | ✅ |
| necrons | IMOTEKH THE STORMLORD / THE SILENT KING | ✅ |
| aeldari | AVATAR OF KHAINE / WRAITHKNIGHT / PHANTOM TITAN | ✅ |
| tau-empire | MANTA | ✅ |
| space-marines | INTERCESSOR SQUAD | ✅ |
| titan-legions | 四台泰坦全部 | ✅ |

两条初判「缺失」都回查了原始 HTML，不是数据缺口：

- `SZARETH THE SILENT KING` —— 官网条目名就叫 `THE SILENT KING`，是抽查清单写错名字。
- `ROBOUTE GUILLIMAN` —— 原始 HTML 里**确实存在**（`raw 'GUILLIMAN' 出现次数: 2`，
  带 `bg-red-500` 涨价色块），但他在 `ULTRAMARINES` 小节里，
  被 `_KEEP_SECTIONS` 过滤掉了。这是**真问题**，见 §6。

## 4. `mfm --check` 全量结果

```
MFM 比对（抓取时间 2026-07-27 14:37，只比基准梯度）：
  可比条目 1243  |  一致 1243 (100.0%)  |  过期 0  |  MFM 有库里无 5  |  梯度计价单位 321
```

- **过期（diffs）条数：0**，明细为空列表。
- **`db_unparsed`：0** —— 没有单位因 `points_json` NULL/损坏而被排除出对账口径。
- **`mfm_only`：5**，逐条都有已知解释，均非数据缺口：
  | 单位 | 解释 |
  |---|---|
  | CHAOS WARHOUND / REAVER / WARBRINGER NEMESIS / WARLORD TITAN | 混沌泰坦复用忠诚派同一张兵牌换关键词、共用同一份点数（`Faction Pack Adeptus Titanicus.pdf` p2 `TITANICUS TRAITORIS` 明示），库内**不该**有独立行；四个价格与忠诚派逐一相同（1100/2200/2600/3500） |
  | ERADICATOR SQUAD WITH HEAVY BOLTERS | 官网单列的变体装配名，库未单列该装配（`_MFM_NAME_ALIASES` 注释里已记录的既有情形） |

对比上一轮记录的 1236 可比 → 本轮 **1243**，+7 正是下面这 7 个单位。

## 5. 那 7 个 ≥1000 分单位的逐个比对

按「库内任一档位 ≥1000 分」的口径查库，全库**恰好 7 个**，与上一轮点名的名单完全吻合：

| # | 库内单位 | 阵营 | 档位 | 库内点数 | MFM 点数 | 判定 |
|---:|---|---|---|---:|---:|:--:|
| 1 | Phantom Titan（幻影泰坦） | AE | 1 model | 2100 | 2100 | ✅ 一致 |
| 2 | Revenant Titan（幽魂泰坦） | AE | 1 model | 1100 | 1100 | ✅ 一致 |
| 3 | Manta（蝠鲼） | TAU | 1 model | 2100 | 2100 | ✅ 一致 |
| 4 | Reaver Titan（掠夺者） | TL | 1 model | 2200 | 2200 | ✅ 一致 |
| 5 | Warbringer Nemesis Titan（天罚战争使者） | TL | 1 model | 2600 | 2600 | ✅ 一致 |
| 6 | Warhound Titan（战犬） | TL | 1 model | 1100 | 1100 | ✅ 一致 |
| 7 | Warlord Titan（战将泰坦） | TL | 1 model | 3500 | 3500 | ✅ 一致 |

**7/7 与官网一致**。这 7 个单位此前从未进过比对池，现在进了，而且库内数值本来就是对的
——静默丢行的代价不是「数值错了」，而是「数值对不对无人知晓」，这一格现在填上了。

### apply 与否：**不 apply**

先在**库副本**上试跑 apply 量化影响（真库全程未动）：

```
apply 报告: 匹配 959 单位 / 更新 0 个
**档位点数发生变化的条目: 0**
**顶层 points 变化: 0**
**新获得 mfm 溯源的单位: 7** -> [Manta, Phantom Titan, Reaver Titan, Revenant Titan,
                                  Warbringer Nemesis Titan, Warhound Titan, Warlord Titan]
**仅刷新 fetched_at 时间戳的单位: 962**
apply 后收敛校验（副本上）：可比 1243 / 一致 1243 / 过期 0
```

不 apply 的理由：

1. **差异为 0，apply 改不动任何点数。** `units_updated=0`、档位点数变化 0 条、
   顶层 points 变化 0 条。任务书给的 apply 触发条件是「差异只涉及那 7 个单位
   （及少量正常变价）」——这里连一条差异都没有，触发条件不成立。
   apply 前后 `--check` 都是 `1243/1243/0`，收敛校验一模一样，apply 买不到任何点数准确性。
2. **apply 唯一的实际效果有下游语义副作用。** 它会给那 7 个单位补上
   `points_json["mfm"]` 溯源块。而这个键在四处被当作「**现役**」判据使用：
   `wiki_engine/keyword_index.py:169`（现役武器反查索引）、`db_compile/zh_weapons.py:478,514`、
   `web_api/codex.py:46`、`db_compile/dup_units.py:145`。
   补上它 = 把这 7 个单位从「非现役」翻成「现役」——事实上**是对的**（它们确实在现行 MFM 里），
   但会连带改动 wiki 现役反查计数与图鉴接口输出，需要重生成 wiki 页并重新对账。
   这超出「本轮只做一件事」的范围，且未经验证，不该顺手做。
3. 红线写明「判据不满足就不许跑，宁可只交一份 `--check` 报告」。照办。

**遗留项（建议独立一轮做）**：那 7 个单位缺 `points_json["mfm"]` 溯源，
因而在 wiki/图鉴的「现役」口径里被算作非现役。修法就是一次 `mfm --apply`
加 wiki 重生成与计数对账，但要连同 §6 一起做，否则要重生成两次。

## 6. 顺带查出：同一类静默丢行的第二处实例（本轮未改）

基里曼的「消失」引出 `_KEEP_SECTIONS = {"UNITS", "FORTIFICATIONS"}` 的覆盖缺口。
对 30 个阵营页做了 h3 小节普查，被排除的小节里共有 **502 个单位表头**，分三类：

| 类别 | 小节 | 表头数 | 排除是否正确 |
|---|---|---:|---|
| 战团页重复渲染的通用 SM 名录 | `SPACE MARINES`（BT 72 / BA 84 / DA 84 / DW 79 / SW 80） | 399 | ✅ 正确，已由 `space-marines` 页覆盖（`_rows_by_faction` 通用页优先） |
| 借调价 | `EVERY MODEL HAS THE IMPERIUM KEYWORD`（imperial-agents） | 29 | ✅ 正确，正是当初加 `_KEEP_SECTIONS` 要挡的东西 |
| 分队名误命中 | `DETACHMENTS` | 13 | ✅ 正确，不是单位 |
| **子阵营专属真单位** | 见下 | **≈61** | ❌ **误伤** |

误伤的明细：

| slug | 小节 | 单位表头数 |
|---|---|---:|
| space-marines | ULTRAMARINES | 8（含 ROBOUTE GUILLIMAN） |
| space-marines | IMPERIAL FISTS | 3 |
| space-marines | IRON HANDS / SALAMANDERS / RAVEN GUARD / WHITE SCARS | 2 + 2 + 2 + 2 |
| aeldari | HARLEQUINS | 8 |
| aeldari | YNNARI | 11 |
| death-guard | PLAGUE LEGIONS | 6 |
| thousand-sons | SCINTILLATING LEGIONS | 6 |
| world-eaters | BLOOD LEGIONS | 5 |
| emperors-children | LEGIONS OF EXCESS | 5 |

这些是有独立官方点数的真实单位，和泰坦那 7 个属于**完全相同的失效模式**：
不是数值错，而是**从未进过比对池，对不对无人知晓**，且同样不报错。

**本轮不动它**：改 `_KEEP_SECTIONS` 会把约 61 个单位灌进比对池，需要逐个判定
「这是自军现行价还是又一种借调价」（`PLAGUE LEGIONS` 之类的小节语义还没核实），
属于独立一轮的活。本轮职责是把泰坦那 7 个补上校验，那件事已经做完。

## 7. 验证

| 项 | 结果 |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | 见 §7 实测输出 |
| `python -m wiki_engine lint` | 0 error |
| `cd web && npm run lint` | 0 error |
| `git status` | clean（缓存与库均 gitignored，仓库只多本报告） |

## 8. 教训

1. **「上一轮修了正则」不等于「缓存里就有数据」**——`--slug` 定点补抓会保留原
   `fetched_at`，缓存看起来还是旧的，实际内容已被局部改写。判断缓存代际要同时看
   `fetched_at` **和文件 mtime**，两者对不上就说明有过定点写入。
2. **明星单位证伪法要先核实名字再报警。** 两个「缺失」里一个是清单写错名
   （`THE SILENT KING` 不叫 `SZARETH ...`），另一个才是真问题。
   不回原始 HTML 就报「官网删了基里曼」是纯造谣。
3. **同一个 bug 类会在同一个文件里有第二处实例。** 泰坦那处是「正则对千分位零容忍」，
   这处是「小节白名单太窄」，表现完全一样：静默丢行、不报错、指标看着健康。
   修完一处应当顺着**同一个失效模式**扫一遍，而不是结案。
   `count_unit_headers()` 这次没抓到它——因为它也走 `_slice_kept_sections()`，
   **校验器和被校验对象共享了同一个前提就一起瞎**（与核心规则那轮同一条教训）。
   真正抓到它的是完全在体系外的「明星单位证伪法」。
4. **apply 之前先在库副本上试跑并逐字段 diff。** 这次靠它拿到「点数变化 0 条、
   只有 7 条溯源新增 + 962 条时间戳刷新」的精确画像，才敢下「不 apply」的结论——
   而不是凭 `--check` 是 0 差异就想当然。
