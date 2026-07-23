# 模块 6 审查报告：wiki 双管线（wiki_compile / wiki_engine）

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：`wiki_compile/`（旧管线·双语术语表）、`wiki_engine/`（新管线·f09dacfb 昨日
  一次性生成 25 阵营 1715 单位页）。
- 方法：全量代码通读 + 只读 sqlite 对账 + 产物实页抽检 + scratchpad 隔离复现 +
  定向 pytest（-k wiki 177 passed 基线）。未修改仓库文件（审查阶段）。
- 结论先行：**2 个 HIGH（CONFIRMED，已修复）**、5 个 MEDIUM、4 个 LOW。对账与三个
  已修坑本体守住（db 1715 = wiki 1715 页零差额、0 嵌套 wikilink、0 未转义表格竖线、
  lint 0 断链假阳性）。

---

## F1（HIGH，CONFIRMED，已修复）：from_db 绕过 H16 人工编辑保护 + LLM 可反向覆盖官方页

- **位置**：`wiki_engine/from_db.py:266-271`（无条件覆盖，不读不写 gen_hashes）；
  对照 `synthesize.py:549,577-597`、`crosslinks.py:389-421`（两者精心维护 gen_hashes）
- **失效场景**：① **正向失守**——手工编辑的单位页在 from_db 重跑时被静默覆盖（脚本
  复现：加批注 → 重跑 → 批注消失，且仓库根本没有 `.gen_hashes.json`）；② **反向失守
  （权威倒挂）**——synthesize 的守卫是「无登记值 = 旧文件保持覆盖」，from_db 落盘路径
  与 synthesize `entity_page_path` 同构，故一次 `wiki_engine pipeline` 就能用 LLM 合成
  内容覆盖官方结构库渲染的页面，与「sqlite 是数值唯一真源」的裁决正面冲突。
- **修法（已实施）**：① from_db 接入 gen_hashes——`generate_faction` 加
  `gen_hashes` 参数，目标页有登记值且当前内容 ≠ 登记值即判人工编辑，跳过覆盖计入
  conflicts；`generate_all` 加载/保存登记表，main 打印冲突清单。② synthesize 加硬规则：
  目标页 frontmatter `source: official-db` 时**无条件**拒绝被 LLM 覆盖（不依赖
  gen_hashes 是否存在，`_is_official_db_page` 只查 frontmatter 区），单列
  `official_protected` 统计。
- **测试**：`test_wiki_from_db.py::TestGenHashesProtection`（人工编辑不被覆盖 + 冲突
  上报 / 删除页后正常再生成，成对）、`test_wiki_synthesize.py::TestOfficialDbPageGuard`
  （官方页识别 / 正文误提及与 LLM 页不受保护，成对）。

## F2（HIGH，CONFIRMED，已修复）：crosslinks 注入无词界、无阵营语境——125 处词中注入 + 跨阵营错链

- **位置**：`wiki_engine/crosslinks.py:331-346`（`re.escape(name)` 无边界）、
  `crosslinks.py:270-273`（全局单命名空间 first-wins）
- **失效场景**：全库扫描单位页 125 处 `[[…|X]]汉` 词中注入。三实证：帝皇卫队页
  「堡主战斧」被切成 `[[…星际战士…Castellan|堡主]]战斧`；兽人页「先知」链到灵族
  Farseer；帝国特勤页「毒刃」链到基因窃取者 Baneblade。1715 页 × 数千注册名的笛卡尔
  扫描把短单位名（堡主/先知/毒刃）变成地雷。
- **修法（已实施）**：① **阵营门**——目标是异阵营的 `factions/X/units/*` 页时不注入
  （同阵营/core-rules 术语页不受限，仅在有 self_path 语境时生效）；② **短 CJK 门**——
  纯 CJK 名 <3 字不注入；③ **ASCII 词边界**——`_name_pattern` 加负回溯/负前瞻，防
  "Vyper" 命中 "Vypers"、"Ork" 命中 "Orkish"。重跑 from_db→crosslinks→build→lint 后
  三个实证案例全清零，剩余「链接后接汉字」40 处经核均为同阵营合法链接（中文无词界
  的固有形态，非错链）。
- **测试**：`test_wiki_crosslinks.py::TestInjectionGuards`（跨阵营不注入/同阵营注入/
  core-rules 不受门限/短 CJK 不注入/ASCII 词界，五向成对）。
- **注**：本次只固化代码修复与测试，**全库 wiki 产物刷新留待 F3-F6 数据问题一起修完
  再一次性重跑并 diff 对账**（避免混入未审数据重渲染；改动只进 wiki 文件不进 FAISS
  索引，检索侧无影响）。

## F3（MEDIUM，CONFIRMED，已修复）：武器中文名按 (A,S,AP,D) 侧内配对，碰撞时张冠李戴——89 单位

- **位置**：`from_db.py:44-55`（`_zh_weapons_indices` 同键 last-write-wins）
- **说明**：同侧两把不同武器侧写完全相同时，中文索引只剩最后一条，官方两行套同一中文
  名。全库 89 单位存在此必错组合（如 Custodian Wardens 射击表两行都渲成「堡主战斧」）。
  数值仍官方，但武器名是翻译层核心交付物。
- **建议修法**：配对键加入武器名归一比对；同键多值时放弃中文名回退英文并记 drift。

## F4（MEDIUM，CONFIRMED，已修复）：slug 去重 "-2" 页与 entity_page_path 脱节，索引链错页、去重页全孤儿

- **位置**：`from_db.py:268-270`（`used_slugs` 加 -2）vs `models.py:289-293`
  （entity_page_path 无去重概念）
- **说明**：db 中同阵营同 slug 10 组（Repulsor 系列等）。from_db 给第二个写
  `repulsor-2.md`，build_outputs 用 entity_page_path 从 frontmatter 反推推不出 -2。
  `wiki/index.md` 链到 `repulsor.md`，`repulsor-2.md` 全库无入链（孤儿）。
- **建议修法**：把实际落盘相对路径写进 frontmatter，或以 id 作确定性去重后缀；
  build/lint 以真实文件路径为链接目标，废弃「从 fm 反推路径」的双源真值。

## F5（MEDIUM，CONFIRMED，已修复）：`_zh_model_desc` 丢弃档位语境，15 个 AoI 单位渲出同名不同价构成行

- **位置**：`from_db.py:92-95`（`re.match(r"(\d+)\s*models?")` 前缀命中即整体替换）
- **说明**：`1 model (Assigned Agent)` 等三种 desc 全塌缩成「1个模型」，读者无法知道
  哪个价对应哪种编制；frontmatter points 键原样泄漏 `<ky>` 标签。
- **建议修法**：保留括号语境并翻译；frontmatter 键先剥 `<ky>…</ky>`。

## F6（MEDIUM，CONFIRMED，已修复）：多特殊保护只渲第一个，Ghazghkull 页丢失马卡力 2+ 无敌豁免

- **位置**：`from_db.py:172-174`（`invulns[0]`）
- **说明**：全库唯一多 invuln 单位 Ghazghkull（4 和 2）只渲 `- 4+`，传奇旗手 2+ 特殊
  保护凭空消失——与官方数据卡不一致的数值内容错误（仅 1 单位，属正确性问题）。
- **建议修法**：按模型逐行渲染 invuln，或并入属性表。

## F7（MEDIUM，CONFIRMED，已修复）：build_outputs 是第四处没跟上转义约定的解析器，index.md 表格实际断列

- **位置**：`build_outputs.py:46-60,97`（`_extract_summary` 把含 `[[path|显示]]` 的
  正文首段塞进 index.md 表格单元格不转义）
- **说明**：`wiki/index.md` 实测 1 行被未转义 `|` 切成多余列。摘要截断还可能把
  wikilink 拦腰截断。
- **建议修法**：`_extract_summary` 把 `[[path|显示]]` 剥成纯显示文本。

## LOW（4 条，仅记录）

1. lint 对表格转义断链声称「可自动修复」但 --fix 静默 no-op（`lint.py:352-367`）——
   剥反斜杠后的 old_link 匹配不上带 `\|` 的实文。
2. canonicalize 不剥尾随反斜杠（`crosslinks.py:189-213`）——与 lint 剥法不一致的同族
   分歧；F8+F9 叠加会成死结（建议抽公共 `parse_wikilink()` 单点实现）。
3. canonical.py 下载非原子、零错误处理（`wiki_compile/canonical.py:33-41`）——半截 CSV
   静默产出配对缺员。建议 `.tmp + os.replace`。
4. check_drift 武器形参从未使用 + zstats 按位置对齐脆弱（`from_db.py:107-121,159-161`）。

---

## 已核无误（核法附后）

| 核查项 | 核法 | 结论 |
|---|---|---|
| 坑① 转义时机与范围 | 读 escape_table_pipes + 全库正则扫描 | 只对表格行转义，正文 wikilink 不误转；幂等 |
| 坑② lint 剥反斜杠 | 读 lint 正则 + 查 lint-report | 转义链接 0 假阳性；同族漏网即 F7/F8 |
| 坑③ inject 区间守卫 | 全库扫描嵌套 `[[…[[` = 0 | 守卫本体有效；防不了词中注入（另立 F2） |
| 页数对账 | 只读 sqlite：units 1715 全 faction_id 非空 = wiki 1715 | 零差额 |
| 中文路径编码 | 1715 中文目录写入/rglob 读回全通 | 无编码问题 |
| frontmatter YAML 特殊字符 | sqlite 查名含 `---`/`"`/`:` 均 0；safe_dump 往返验证 | 当前数据无炸点 |
| 数值权威（中文层不覆盖数值） | 读 cell()：官方值优先 | 守住（唯一缺口 F6 invuln 截断，非中文覆盖） |

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 2 | 均已修复 + 成对测试 |
| MEDIUM | 5 | **全部已修复 + 成对测试**（F3-F7，全库重跑 diff 对账，实证清零） |
| LOW | 4 | F9 已随 F7 修复（共用 strip_wikilinks 剥反斜杠）；F8/L3/L4 记录在案 |

## 修复补记（2026-07-23，分支 fix/wiki-data-correctness）

F3-F7 五个 MEDIUM 一并修复，实证全部清零：
- **F3**：`_zh_weapons_indices` 检测同侧写异名，歧义键删除→回退官方英文名，碰撞记入
  drift。实证 Custodian Wardens 射击两行渲为 Guardian spear / Castellan axe（不再都套
  「堡主战斧」）。
- **F4**：dedup 加 `ORDER BY name_en, id` 确定次序；`WikiPage.source_rel` 记真实扫描
  路径，build 链接用它而非从 name 反推。实证 repulsor-2.md 有入链、不再孤儿。
- **F5**：`_zh_model_desc` 保留档位尾串 + `_clean_desc` 剥 `<ky>`；frontmatter points
  键同步清洗。实证 Vindicare 三档 110/125/110 各带语境不塌缩。
- **F6**：特殊保护逐模型渲染。实证 Ghazghkull 碎骨者萨拉卡 4+ / 传奇旗手马卡力 2+
  都在。
- **F7**：`_extract_summary` 用共用 `strip_wikilinks` 剥链接为纯文本。实证 index.md
  零断列行。
- **F9**（LOW）：`_WIKILINK_RE` 加 `\\?` 吸收转义反斜杠 + `strip_wikilinks` rstrip
  兜底，与 F7 同一处修复。
- 全库重跑 from_db→crosslinks→build→lint：lint 0 errors，603 页真实内容变更（数据修复
  + F2 阵营门在产物生效），改动只进 wiki 文件不进 FAISS 索引。

## 遗留建议

1. F8（lint --fix 对转义断链 no-op）、L3（canonical.py 非原子下载）、L4（check_drift
   武器形参已在本次改为只传 models/zstats）后续按需处理。
2. lint 的 `alias-conflicts` 277 条 warning 大半来自 db 内跨阵营同名单位，建议按「同
   阵营才告警」降噪。
