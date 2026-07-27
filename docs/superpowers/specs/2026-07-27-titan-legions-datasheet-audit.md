# 泰坦军团缺兵牌排查报告（2026-07-27）

**结论先行：缺口是 0 个。泰坦军团一共就 4 个单位，4 个在库里都有完整兵牌，
每一格数值都与官方 Faction Pack PDF 逐字一致。「MFM 有 7 个、库里只有 4 个、
图鉴点进去是空壳」这个前提不成立——本次没有新建任何兵牌，因为没有可建的。**

那个「7」不是泰坦军团的单位数，是**被 MFM 解析器静默丢掉的单位数**：
库内 7 个点数 ≥1000 的单位（4 个泰坦 + 灵族幽魂/幻影泰坦 + 钛族 Manta）
在 MFM 缓存里全部查无此条，因为官网四位数分数写作 `2,200 pts`，
而解析器的 `(\d+)` 正则对千分位逗号零容忍且不报错。**本轮修的是这个。**

---

## 一、缺口核清（先报数，再动手）

### 1.1 MFM 官网到底有几个泰坦军团单位

2026-07-27 直连官网抓两页（`mfm.warhammer-community.com/en/titan-legions`、
`/en/chaos-titan-legions`），页面 HTML 各 75.7 KB，`<h3>` 小节只有一个 `UNITS`：

| MFM slug | 单位表头数 | 单位与分数 |
|---|---|---|
| `titan-legions` | **4** | WARHOUND 1,100 / REAVER 2,200 / WARBRINGER NEMESIS 2,600 / WARLORD 3,500 |
| `chaos-titan-legions` | **4** | 同上四个的 CHAOS 前缀版，分数逐个相同 |

**官网是 4 个，不是 7 个。** 两页的 4 个分数与库内 `points_json` 逐个相同（见 §三）。

### 1.2 官方 PDF 里有几张兵牌

`data/Faction Pack Adeptus Titanicus.pdf`，共 10 页，全部**可文字提取**
（无图片型页面，`page.get_text()` 每页 871–2068 字符）：

| PDF 页 | 内容 |
|---|---|
| p1 | 封面 + 目录（`Imperial Armour Datasheets.....2`） |
| p2 | ARMY RULES（TOWERING EXAMPLE / TITANIC SUPPORT / TITANICUS TRAITORIS） |
| p3–4 | **WARHOUND TITAN** 兵牌 + 装备选项/编制 |
| p5–6 | **REAVER TITAN** 兵牌 + 装备选项/编制 |
| p7–8 | **WARBRINGER NEMESIS TITAN** 兵牌 + 装备选项/编制 |
| p9–10 | **WARLORD TITAN** 兵牌 + 装备选项/编制 |

**PDF 里就是 4 张兵牌。** 没有第 5–7 张，不存在「PDF 有而库里没有」的单位。

### 1.3 库内这 4 个单位缺什么

一个都不缺。`db/wh40k.sqlite` 只读查询（`faction_id='TL'`）：

| id | 单位 | models 行 | 属性 M/T/SV/W/LD/OC | weapons 行 | abilities 行 | datasheets 行 |
|---|---|---|---|---|---|---|
| `000000867` | Warhound Titan | 1 | 全非空 | 6 | 2 | 有 |
| `000000868` | Reaver Titan | 1 | 全非空 | 8 | 2 | 有 |
| `000002077` | Warbringer Nemesis Titan | 1 | 全非空 | 9 | 2 | 有 |
| `000000869` | Warlord Titan | 1 | 全非空 | 13 | 2 | 有 |

图鉴页也不是空壳：`wiki/factions/泰坦军团/units/` 下 4 个页面，
六节（属性表/射击武器/近战武器/技能/单位构成/关键词）全部有内容。
浏览器目检见 §五。

### 1.4 建不了的：4 个混沌泰坦（但这是官方设计，不是缺口）

`chaos-titan-legions` 那 4 条（CHAOS WARHOUND/REAVER/WARBRINGER/WARLORD TITAN）
在库里没有对应行，`mfm --check` 把它们列进 `mfm_only`。**这 4 个建不了，
而且不该建**——依据是 PDF **p2 TITANICUS TRAITORIS** 段原文：

> You can use the Adeptus Titanicus datasheets in this document to represent
> Titanicus Traitoris models if you wish. To do so, on those datasheets and on this
> Army Rules card, replace all instances of the Imperium keyword with Chaos, and replace
> all instances of the Adeptus Titanicus Faction keyword with Titanicus Traitoris.
> For the purposes of points values, use those published for the equivalent Adeptus
> Titanicus models.

即混沌泰坦**没有独立兵牌**，是同一张兵牌换两个关键词、用同一份点数。
官方 PDF 里既然没有第二套数值，就不存在可抄的字段——照红线留空即等于不建。
本次没有为它们建行，也没有给它们配名字别名（配了会让 `apply_points`
在将来官方拆分点数时把帝国版的价覆盖掉）。

---

## 二、每个字段的 PDF 页码出处

下表是**逐格核对**的结果，不是抽样。左边是库内值，右边是 PDF 出处页；
`✓` = 库内值与该页原文逐字符相同。

### 2.1 属性与保护（PDF 各兵牌页右下角属性条）

| 单位 | M | T | SV | W | LD | OC | 无敌保 | PDF 页 |
|---|---|---|---|---|---|---|---|---|
| Warhound Titan | 14" ✓ | 13 ✓ | 2+ ✓ | 40 ✓ | 6+ ✓ | 16 ✓ | 5+（仅对远程）✓ | **p3** |
| Reaver Titan | 12" ✓ | 14 ✓ | 2+ ✓ | 60 ✓ | 6+ ✓ | 20 ✓ | 5+（仅对远程）✓ | **p5** |
| Warbringer Nemesis Titan | 12" ✓ | 14 ✓ | 2+ ✓ | 80 ✓ | 6+ ✓ | 20 ✓ | 5+（仅对远程）✓ | **p7** |
| Warlord Titan | 10" ✓ | 16 ✓ | 2+ ✓ | 100 ✓ | 6+ ✓ | 30 ✓ | 5+（仅对远程）✓ | **p9** |

### 2.2 武器（36 行全对）

| 单位 | PDF 页 | 远程 | 近战 | 库内 weapons 行 | 逐格一致 |
|---|---|---|---|---|---|
| Warhound Titan | **p3** | 5（含等离子爆裂枪 standard/supercharge 两档） | 1 | 6 | 6/6 ✓ |
| Reaver Titan | **p5** | 5 | 3（feet + power fist strike/sweep） | 8 | 8/8 ✓ |
| Warbringer Nemesis Titan | **p7** | 8 | 1 | 9 | 9/9 ✓ |
| Warlord Titan | **p9** | 10（含 Sunfury standard/supercharge 两档） | 3（feet + arioch claw strike/sweep） | 13 | 13/13 ✓ |

抽三条最容易抄错的贴原文比对（PDF 原文 → 库内值）：

- p9 `Belicosa volcano cannon [BLAST] 120" D3+3 3+ 32 -5 18`
  → `range=120, a=D3+3, bs_ws=3, s=32, ap=-5, d=18, kw=[blast]` ✓
- p7 `Nemesis quake cannon [BLAST, INDIRECT FIRE] 480" D6+6 3+ 16 -4 4`
  → `range=480, a=D6+6, bs_ws=3, s=16, ap=-4, d=4, kw=[blast, indirect fire]` ✓
- p3 `Warhound inferno gun [IGNORES COVER, TORRENT] 24" 3D6 N/A 7 -2 3`
  → `range=24, a=3D6, bs_ws=N/A, s=7, ap=-2, d=3, kw=[ignores cover, torrent]` ✓
  （`N/A` 而不是编一个 BS 值——洪流武器自动命中，库里照实存 `N/A`）

### 2.3 技能与受损

| 单位 | 独有技能（库内 abilities 表） | 受损阈值 | PDF 页 |
|---|---|---|---|
| Warhound Titan | Striding Colossus（**twice** CP）、Flank Speed | 1-13，OC-8、命中-1 | **p3** ✓ |
| Reaver Titan | Striding Colossus（**three times** CP）、God-machine | 1-20，OC-10、命中-1 | **p5** ✓ |
| Warbringer Nemesis Titan | Striding Colossus（**three times** CP）、Titanic Fire Support | 1-26，OC-10、命中-1 | **p7** ✓ |
| Warlord Titan | Striding Colossus（**four times** CP）、Wrath of the Omnissiah | 1-33，OC-15、命中-1 | **p9** ✓ |

Striding Colossus 的倍数 4 个单位各不相同（2/3/3/4 倍 CP），库里 4 条正文逐字对上——
这一条最能证明数据是抄来的而不是套的（套同类单位会 4 个一样）。
`CORE: Deadly Demise` 与 `FACTION: Super-heavy Walker` 不在 `abilities` 表里，
走全库通用的核心/阵营技能通道（`Super-heavy Walker` 全库 9 条），非泰坦军团独有缺失。

### 2.4 编制与装备选项

| 单位 | `datasheets.loadout` | PDF 页 |
|---|---|---|
| Warhound Titan | Warhound plasma blastgun; Warhound vulcan mega-bolter; Warhound feet | **p4** ✓ |
| Reaver Titan | Reaver apocalypse launcher; Reaver gatling blaster; Reaver laser blaster; Reaver feet | **p6** ✓ |
| Warbringer Nemesis Titan | 2 anvillus defence batteries; 3 ardex-defensor maulers; Nemesis quake cannon; Reaver gatling blaster; Reaver laser blaster; Nemesis feet | **p8** ✓ |
| Warlord Titan | 2 apocalypse launchers; 2 ardex-defensor lascannons; 2 ardex-defensor maulers; macro gatling blaster; arioch power claw; Warlord feet | **p10** ✓ |

### 2.5 点数

| 单位 | 库内 | MFM 官网（2026-07-27 实抓） | PDF |
|---|---|---|---|
| Warhound Titan | 1100 | 1,100 ✓ | PDF 不载点数（官方点数真源是 MFM） |
| Reaver Titan | 2200 | 2,200 ✓ | 同上 |
| Warbringer Nemesis Titan | 2600 | 2,600 ✓ | 同上 |
| Warlord Titan | 3500 | 3,500 ✓ | 同上 |

### 2.6 PDF 里读不出来 / 库里没有的字段（照红线列出，一个都没补）

| 字段 | 状况 | 处置 |
|---|---|---|
| `Frame` 关键词 | PDF p3/5/7/9 的 KEYWORDS 行都有 `Frame`，库内 4 个单位的 `keywords_json` 都没有 | **没动**——见 §四，这是全库 318 处的系统性缺口，不是泰坦军团问题，单改 4 个单位会造成库内口径不一致 |
| `units.version` | 4 个单位都是 `NULL` | 保持 NULL，PDF 未提供版次字段 |
| `models.count_options_json` | 4 个单位都是 `NULL` | 保持 NULL，单模型单位本就无编制档位 |
| `abilities.name_zh` / `text_zh` 中文 | 库内是英文原文 | 保持——wiki 宪法 §3「正文一律官方英文」是用户裁决 |
| 混沌泰坦 4 个单位全部字段 | 官方 PDF 无独立兵牌（p2 明示复用） | 不建行，见 §1.4 |

---

## 三、本轮真正修的东西：MFM 千分位逗号静默丢行

### 3.1 症状

`db_sources/mfm/mfm_points.json` 里 `titan-legions` 与 `chaos-titan-legions`
两个 key 长期是空 list（07-19 与 07-26 两版缓存都是空），
`mfm --check` 的可比条目里因此**从来没有过这 7 个单位**：

```
库内 points >= 1000 的单位：
  AE    Revenant Titan            1100  MFM缓存里【无】
  AE    Phantom Titan             2100  MFM缓存里【无】
  TAU   Manta                     2100  MFM缓存里【无】
  TL    Warhound Titan            1100  MFM缓存里【无】
  TL    Reaver Titan              2200  MFM缓存里【无】
  TL    Warlord Titan             3500  MFM缓存里【无】
  TL    Warbringer Nemesis Titan  2600  MFM缓存里【无】
合计 7
```

**这 7 就是「7 个单位」的来源。** 它们不是缺兵牌的新单位——
4 个泰坦兵牌齐全，灵族两个泰坦和钛族 Manta 也都在库里，
只是它们的**点数从未被官方源校验过**。

### 3.2 根因

`db_compile/mfm.py` 的分数行正则：

```python
r'<span[^>]*>(?:[▲▼]\s*\([+\-]?\d+\)\s*)?(\d+) pts</span></li>'
```

官网四位数分数渲染成 `<span>2,200 pts</span>`。`(\d+) pts` 要求数字紧接
`" pts"`，`2,200` 里逗号一横插就整条匹配不上——**不抛异常、不打日志，
那一档直接不进结果**。泰坦军团全部单位都是四位数，所以整页解析出 0 行。

两道既有护栏都拦不住它：

1. `_guard_cache_regression` 按「新缓存对旧缓存掉行 ≥30%」判解析器断裂——
   而 titan-legions 是 **0 → 0**，不算掉行。
2. `fetch_all` 把 `fetch_faction` 抛的异常记进 `failed`——而这里根本没抛异常，
   页面「成功」解析出 0 行，跟「这个阵营就是没有单位」在数据上完全一样。

**校验器与被校验对象共享了同一个假设（行数掉了才叫坏），所以一起瞎。**

### 3.3 修法

`db_compile/mfm.py`，两处：

1. **正则容忍千分位**：`((?:\d{1,3}(?:,\d{3})+|\d+)) pts`，逗号形式优先、
   匹配不到再退回裸数字；`int(pts.replace(",", ""))` 落值。
   `▲/▼ (±N)` 变动标记前缀同步放宽成 `[\d,]+`（涨降幅也可能过千）。
2. **加一个与行数正交的独立信号**：`count_unit_headers(html)`
   数「保留小节内的单位名表头个数」。`fetch_faction` 里
   「表头 > 0 而分数行 == 0」判 `MfmParseBroken`（新异常类，
   **不重试**——正则对不上重试一万次也是 0 行）；`fetch_all` 把它与网络失败
   分开收进 `parse_broken`，写盘前 raise 拒绝把断裂页写成「空阵营」，
   `--force` 放行时也必须在缓存里留痕。

### 3.4 机械验证

修前 / 修后，同一份 2026-07-27 实抓 HTML：

| slug | 表头数 | 修前解析行数 | 修后解析行数 |
|---|---|---|---|
| `titan-legions` | 4 | **0** | **4** |
| `chaos-titan-legions` | 4 | **0** | **4** |

用 `mfm --slug` 补抓 4 个受影响阵营页（`titan-legions` /
`chaos-titan-legions` / `aeldari` / `tau-empire`）后：

```
修前：可比条目 1236 | 一致 1236 (100.0%) | 过期 0 | MFM 有库里无 1
修后：可比条目 1243 | 一致 1243 (100.0%) | 过期 0 | MFM 有库里无 5
```

- **可比条目 +7**，正是 §3.1 那 7 个单位，**7/7 一致、过期 0**。
  这同时给 §2.5 的点数提供了走项目自己 CLI 的机器证据，不靠一次性脚本。
- `mfm_only` 1 → 5：新增的 4 个是混沌泰坦（§1.4 解释，官方设计如此，
  不是数据缺失）；原有的 1 个是 `ERADICATOR SQUAD WITH HEAVY BOLTERS`（既有项）。
- 7 个单位的点数**一格都没改**——库内本来就是对的，只是从未被校验过。

`db_sources/` 在 `.gitignore` 第 29 行，缓存本身不进 git；
复现命令是 `python -m db_compile mfm --slug titan-legions`。

### 3.5 护栏

`tests/test_db_compile_mfm.py` 新增两组（+9 条，全库 2344 → 2353）：

- `TestParseMfmHtmlThousandsSeparator`：四位数带逗号可解析、变价档带逗号可解析，
  **加一条负向成对**（三位数裸数字不得被逗号形态挤掉）。
- `TestSilentParseFailureDetection`：表头数与分数行数互相独立、
  真空页 0 表头不误判、`fetch_faction` 有表头无行时抛 `MfmParseBroken`、
  正常页不抛、`fetch_all` 拒绝写断裂缓存、`--force` 放行时 `parse_broken`
  留痕且不冒充 `failed`。

**已验证这些测试真会红**：把正则改回旧形态跑，
`test_four_digit_points_with_comma_parsed`、
`test_comma_form_also_works_on_colored_marked_tier`、
`test_fetch_faction_ok_when_rows_parse` 三条失败（改回后 `mfm.py` 字节一致）。

---

## 四、点名的遗留：`Frame` 关键词全库缺失（本轮没动）

PDF p3/5/7/9 四个泰坦的 KEYWORDS 行都写着 `Frame`，库内 4 个单位一个都没有。
扫全部 Faction Pack 后确认这是**系统性**的：

- 19 个 Faction Pack + Core Rules 里 `Frame` 共出现 **318 次**
  （Astra Militarum 90、Space Marines 88、Aeldari 26、Tau 24……）
- 库内带 `Frame` 关键词的单位：**0 个**

即 `Frame` 是 11 版的通用关键词，上游 Wahapedia 镜像没有把它作为 keyword 带进来。
**只给泰坦军团 4 个单位补上会让全库口径分裂**（查询「有 Frame 的单位」会只返回 4 个泰坦），
所以本轮不动，作为独立任务点名。真要补，应该是一次全库范围的
「从 Faction Pack PDF 的 KEYWORDS 行反灌关键词」对账，配反向核对。

---

## 五、验证记录

| 项 | 结果 |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | **2353 passed**（基线 2344 + 新增 9） |
| `python -m wiki_engine lint` | **0 error / 1 warning / 4 info**；`wiki/lint-report.md` 跑完仍不脏（上一轮的时间戳假 diff 修复继续生效） |
| `cd web && npm run lint` | **0 error** |
| `cd web && npm run build` | 通过（6 条路由全静态预渲染） |
| 图鉴页浏览器目检 | Playwright 驱动 `/codex` → 泰坦军团页签（显示 `ADEPTUS TITANICUS 4`）→ 4 个单位逐个点开，4/4 通过；截图逐张目检 Warlord（p9/p10）与 Warbringer（p7/p8），属性/武器/技能/受损/装备/关键词/点数全部有内容且与 PDF 一致，**不是空壳** |
| `mfm --check` | 1243 可比 / 1243 一致 (100.0%) / 过期 0 |
| 数据改动 | **units / models / weapons / abilities / datasheets 五张表零改动** |

改动文件只有三个：`db_compile/mfm.py`（+64 行）、`tests/test_db_compile_mfm.py`（+115 行）、
本报告。`db_sources/mfm/mfm_points.json` 是 gitignored 的本地缓存（内容已按 §3.4 补齐）。

本次没有新建兵牌，因此不存在「新建兵牌的 PDF 页码出处」——
§二给的是**既有 4 个兵牌的逐字段 PDF 页码出处**（核对结论：全对）。
