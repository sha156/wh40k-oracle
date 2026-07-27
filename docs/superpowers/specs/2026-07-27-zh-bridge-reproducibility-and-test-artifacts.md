# 中文名桥的可复现性 + 测试不再写仓库产物（2026-07-27）

本轮范围＝目标里的 **A**（固化中文名修复的可复现性）与 **C**（硬编码基线过时 / 测试写产物）。
**B**（#113 / #117 的数据来源路由）留下一轮，本轮**未跑基准、未改 agent 路径**。

---

## A · 那两个中文名是怎么进库的，重建会不会丢

### 问题

上一轮（配额中断、0 提交）把两个单位的中文层补进了 `db/wh40k.sqlite`：

| canonical_id | name_en | name_zh | source |
|---|---|---|---|
| `000003916` | Ynnari Kabalite Warriors | 死神军阴谋团武士 | blackforum |
| `000000121` | Uriel Ventris | 文崔斯连长 | blackforum |

而 `db/wh40k.sqlite` 是 gitignored、当时又没有任何代码改动被提交。
**「库里有、代码里没有」＝下次重建就静默消失**，所以要先查清它们是怎么进去的。

### 结论：不依赖任何未提交改动，已提交代码就能重跑出来

`db_compile/blacklibrary.py::populate_zh_details` 里的**中文名桥**（`_zh_to_ids`）
是 commit `bb5db826` 就已提交的代码。英文名对不上时（只差单复数或头衔前缀），
退到归一化中文名一对一接。这两个单位正是这条桥接上的：

```
YNNARI KABALITE WARRIOR   -> Ynnari Kabalite Warriors     （单复数）
Captain Uriel Ventris     -> Uriel Ventris                （头衔前缀）
```

那 `1129 → 1135` 的 +6 是什么变的？是**缓存**不是代码：
`db_sources/blacklibrary/details.json` 的 mtime 是 2026-07-27 02:12，
而它上一次被灌进库是更早的事。上一轮跑了重建/补层链，就把这份更新过的缓存吃进去了。

### 复现验证（真库零改动）

在库的**副本**上，用已提交代码 + 当前缓存重跑 `populate_zh_details`：

```
details in cache: 1072
report: {'records': 1072, 'matched': 939, 'matched_by_zh': 7,
         'unmatched': 131, 'no_detail': 2}
rows after: 1135
000003916 → 死神军阴谋团武士
000000121 → 文崔斯连长
```

**1135 行、两个中文名都在。**稳定可复现，桥没有缺口，
因此**没有改 `db_compile/blacklibrary.py` 的必要**（目标里"此时才改"的前提未触发）。

`build` 走的就是这条：
`db_compile build` → `update.restore_authority_layers` → `_RESTORE_STAGES` 里的
`stage_zh_details` → `populate_zh_details`。复现命令清单已写进 `CLAUDE.md`「运行方式」。

### 中文名桥当前接的全部 8 行

| canonical_id | 黑图英文名 | 库内英文名 | 中文名 | 技能条目 | HEAD 的 wiki 里有中文名？ |
|---|---|---|---|---|---|
| 000003836 | Death Company Marine With Boltguns | Death Company Marines with Boltguns | 【传奇】装备爆弹枪的死亡连战士 | 3 | ❌ 新 |
| 000000562 | Sentry Pylons | Sentry Pylon | 哨戒石碑塔 | 4 | ❌ 新 |
| 000000121 | Captain Uriel Ventris | Uriel Ventris | 文崔斯连长 | 3 | ❌ 新 |
| 000000847 | Servitor | Servitors | 奴工【传奇】 | 2 | ❌ 新 |
| 000000397 | Servitor | Servitors | 奴工【传奇】 | 2 | ❌ 新 |
| 000003916 | YNNARI KABALITE WARRIOR | Ynnari Kabalite Warriors | 死神军阴谋团武士 | 2 | ❌ 新 |
| 000004205 | Warsmith Kravek Morne | Kravek Morne | 克拉维克·莫恩 | 3 | ✅ 旧 |
| 000000662 | scourges with Heavy Weapon | Scourges with Heavy Weapons | 装备重型武器的天灾 | 2 | ✅ 旧 |

**两条独立证据对上了**（这是判"哪 6 个是新的"的依据，不是猜的）：

1. 算术：8 行共 21 条目；新 6 行 `3+4+3+2+2+2 = 16`，旧 2 行 `3+2 = 5`。
   与 host 实测的 `EXPECTED_ZH_ITEMS 3280 → 3296`（**+16**）、`unit_zh_detail 1129 → 1135`（**+6**）**逐个自洽**。
2. 交叉验证（走不同代码路径）：`wiki/factions/*/units/*.md` 在 HEAD 是 `568b7301`
   全量重生成的产物。grep 这 8 个中文名——克拉维克·莫恩 与 装备重型武器的天灾 **查得到**，
   其余 6 个**一个都查不到**。与算术划出的分界线完全重合。
   （`奴工` 的 4 处命中经逐条核对全是别的单位：圣物奴工 / 武装奴工突破者 / 武装奴工毁灭者 / 奴工战斗支队；
   两个 `servitors.md` 页里没有"奴工"。）

### 新增护栏

`tests/test_db_compile_zh_coverage.py::TestRealCorpus::test_zh_name_bridge_survives_a_db_rebuild`

在库的副本上重跑 `populate_zh_details`，断言这 6 个 canonical_id 重建后仍有 `name_zh`，
并顺带断言它们的库内 `name_en` 与黑图英文名**确实不同**——
这样桥一旦被拆掉（或被改成只认英文名），用例当场红，而不是等到某次重建后中文层悄悄少一块。
真库一个字节不动（`shutil.copyfile` 到 `tmp_path`）。

---

## C1 · `EXPECTED_ZH_ITEMS` 基线更新

`tests/test_web_api_ability_keywords.py` 的 `EXPECTED_ZH_ITEMS` `3280 → 3296`。
注释里写清了**这次为什么变**：+16 条目来自 +6 行中文名桥，逐个单位列名、与
「units 无中文层 586→580」「空 `abilities_json` 仍是 16（无新增空行）」三个数自洽，
是合法数据增长不是污染。

其余三个基线（`EXPECTED_ZH_KW_SPANS=188` / `EXPECTED_EN_ROWS=4009` /
`EXPECTED_EN_KW_SPANS=443`）**实测未变**，一个字没动。

> 没有改成"从数据推导"：这个常量的**全部价值**就是与数据脱钩地钉住一个人核实过的数，
> 从库里推导等于把探测器接到被测对象上，`3296` 会永远等于 `3296`。

---

## C2 · pytest 不再写 `wiki/indexes/` 产物

### 定位

`tests/test_wiki_keyword_index.py::test_generate_index_is_complete_and_linked` 直接
`generate(DB, WIKI, PDF)` —— 写的就是仓库里的 `wiki/indexes/keywords.md` 与 `.json`
（它已经声明了 `tmp_path` 参数，但根本没用）。跑一次 pytest 工作区就脏，
下一轮 gnhf 以 "Working tree is not clean" 秒退。

### 修法

`wiki_engine/keyword_index.py::generate` 加 `out_root: Optional[Path] = None`：
**`wiki_root` 只用于读**（`_rule_page` 判规则页是否真实存在——断链断言要的就是真页），
**`out_root` 决定写去哪**，默认等于 `wiki_root` ⇒ 正常生成路径逐字节不变
（唯一调用方 `wiki_engine/cli.py` 未改）。测试改传 `out_root=tmp_path`，
断链断言仍打在真 `WIKI` 上，覆盖面一点没减。

### 产物按新数据正规重生成

committed 的 `wiki/indexes/keywords.*` 与当前库确实对不齐了，用正规命令重生成：

```powershell
.\.venv\Scripts\python.exe -m wiki_engine keywords
```

差异全部是 +6 行中文层的直接后果——原先渲染成英文的单位名/武器名现在有了中文，
例如 `Sybarite weapon → 享乐者武器`、`毒晶手枪` 的持有者从 `Ynnari Kabalite Warriors`
变成 `死神军阴谋团武士`（连带条目按中文重排序）。词条总数 46、反查 2751 条现役对，未变。

### 验证

跑完**全量** `pytest -q` 后 `git status --porcelain` 只剩本轮的源码/产物改动，
`wiki/indexes/` 不再出现在里面。

---

## 验证结果

| 项 | 结果 |
|---|---|
| `pytest -q` | **2392 passed, 0 failed**（129s） |
| 全量 pytest 后 `git status` | 只有本轮改动，无测试写出的产物 ✅ |
| `python -m wiki_engine lint` | **0 errors**, 1 warning, 4 info（与基线持平） |
| `cd web && npm run lint` | **0 error** |
| 中文名桥副本复现 | 1135 行 / 6 个目标单位全在 ✅ |
| 数据库 | **未手工 UPDATE**，真库本轮零改动 |
| gold | **未改** |

未跑基准：本轮没有触碰 agent / 检索路径（`agent/` 下不引用 `keyword_index` 或
`keywords.json`），基准留给 B 轮一并两轮跑。

## 遗留（点名，不当作已完成）

- **B 未做**：#113（基里曼点数答 320，来源民间译本 PDF；库内官方 355）与 #117
  （Frame 关键词答 PDF 而非库）仍红，#117 两轮摆动。
- **6 个单位的 wiki 兵牌页尚未重生成**：库里有中文层，`wiki/factions/*/units/*.md`
  还是 `568b7301` 的英文版。词条索引已跟上（本轮重生成），但单位页要走
  `from_db → crosslinks → build → lint` 四步全量刷新，超出本轮范围。
  `wiki_engine lint` 0 error，没有断链，不阻塞。
