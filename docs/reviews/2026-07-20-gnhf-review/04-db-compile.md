# 模块 4 审查报告：db_compile/ 数据编译管线

- 日期：2026-07-23（GNHF 全库深度审查续作，模块 3-8 批次）
- 范围：`db_compile/` 全部 17 文件（fp_errata / mfm / dsl_apply / fp_rules / build /
  update / schema / datasheet / aliases / blacklibrary / community_aliases / crosscheck /
  downloads / enhancements / entity_resolver / calc_points / __main__）。
- 方法：全文精读 + 调用方/测试交叉核对 + 机械复现。写操作只在 scratchpad 的 DB 副本
  上执行（copy1/copy2.sqlite），真库只读（`file:...?mode=ro`）；验证脚本 4 个
  （幂等性/restore 层序/静默绿灯/fp_rules+dsl 幂等）。未跑联网 fetch。
- 结论先行：**2 个 HIGH（均 DB 副本机械复现 CONFIRMED，已修复）**、2 个 MEDIUM、
  5 个 LOW。三个补丁层（fp_errata / fp_rules / dsl_apply）的幂等性、from/指纹守卫、
  白名单防注入、restore 挂载全部机械验证通过。真问题集中在 MFM 点数链的「绿灯谎言」。

---

## H1（HIGH，CONFIRMED，已修复）：restore/update 层序缺口——fp_errata 新插单位每次重建后点数归 NULL，且三道校验全部静默放行

- **位置**：`db_compile/update.py:397-404`（`_PIPELINE` 中 mfm_apply 先于 fp_errata）、
  `update.py:417-426`（`_RESTORE_STAGES` 同序）、`db_compile/fp_errata.py:200-204`
  （插入时写死 `points_json=NULL`）
- **失效场景**：`db_compile build`（默认自动 restore）后：① build 从 CSV 重建，3 个
  11 版新兽人单位（Bigboss / Bannernob / Big Mek Dakkarig）不存在；② mfm_apply 先跑，
  匹配不到它们（MFM 缓存里明明有 55/50/115 分）；③ fp_errata 再插回来，points_json=NULL。
  此后 calc_points 对这三个单位报「无点数记录」，军表验表/点评失效。
- **DB 副本复现**：模拟 fresh-build 态按 restore 顺序跑——`fp_errata units_inserted:
  [ORK:Bigboss, ORK:Bannernob, ORK:Big Mek Dakkarig]`，三行 points_json 全 NULL。
- **为什么至今没发现**：当前真库里这三个单位有分数——是最近一次手动 `mfm --apply`
  碰巧打在已含 fpe 行的库上补上的，下一次 rebuild 就会再次归 NULL。而收尾的
  `stage_mfm_check` 抓不到：`check_points` 对 NULL 行 `json.loads(None)` 抛 TypeError
  被裸 `continue` 吞（`mfm.py:328-329`），既不进 diffs 也不进 mfm_only，1233 条可比
  全绿。三道防线（apply 匹配、check 比对、stage 告警）同时静默。
- **修法（已实施）**：① `_PIPELINE` 与 `_RESTORE_STAGES` 把 fp_errata 挪到 mfm_apply
  之前（两层互不读写对方字段，交换无副作用；MFM "BIGBOSS" 与库 "Bigboss" 小写精确
  命中，apply 能落上）；② `check_points` 新增 `db_unparsed` 桶——NULL/损坏行单列并
  在 stage/CLI 上浮告警，不再裸 continue 蒸发。
- **测试**：`tests/test_db_compile_update_stages.py`（层序双断言 + unparsed 上浮）、
  `tests/test_db_compile_mfm.py::TestCheckPointsUnparsed`（NULL 行进桶/健康行不受
  影响，成对）。

## H2（HIGH，CONFIRMED，已修复）：MFM fetch 无新旧缓存对账护栏，且 check 在「零可比」时报「已完全对齐官方」——2026-07-22 事故的结构性复发口

- **位置**：`db_compile/mfm.py:163-192`（`fetch_all` 无条件覆盖，唯一护栏是首页 slug
  为空才 raise）、`db_compile/update.py:352-367`（`stage_mfm_check`）
- **失效场景**：官网第三次改版式 → 解析器匹配不到 → 每阵营 0 或极少行 → fetch_all
  **不与旧缓存对账、直接覆盖好缓存** → apply 无事可做 → check「可比 0」→
  `ok = len(diffs)==0` 成立 → 全绿收官文案「（已完全对齐官方）」，而库内全部点数已
  静默回退 Wahapedia 旧值。机械复现（构造全空 rows 缓存）：`stage ok: True |
  warning: None | 可比 0，一致 0 (0%)，过期 0（已完全对齐官方）`。7-22 事故复盘承诺
  的「fetch 后新旧缓存逐阵营行数对账」护栏此前没有落进任何代码。
- **修法（已实施）**：① `fetch_all` 写盘前 `_guard_cache_regression`——任一阵营行数
  掉幅超 30% 或总行数掉幅超 10% 时 raise 拒绝覆盖（消息给出掉行清单与人工核实指引），
  CLI 加 `--force` 逃生门（仅限人工核实官网真删减后）；② `stage_mfm_check` 对
  compared 设绝对下限 1000——跌破即 warning「不能据此判定对齐」，「已完全对齐官方」
  文案只在 可比充足 ∧ 零 diffs ∧ 零 unparsed 时出现。
- **测试**：`TestFetchRegressionGuard`（系统性掉行 raise 且旧缓存保住 / --force 放行 /
  小幅波动不误伤，三向成对）、`test_zero_compared_is_not_reported_aligned` /
  `test_healthy_check_reports_aligned`（成对）。

## M1（MEDIUM，CONFIRMED，仅记录）：fetch_all 单阵营抓取失败时用空列表覆盖该阵营的缓存好数据

- **位置**：`db_compile/mfm.py:176-182`（`except RuntimeError: rows = []`）
- **说明**：失败阵营写 []，随后整文件覆盖旧缓存；`stage_mfm_fetch` 不读不报 failed。
  H2 的对账守卫已使这类覆盖 fail-closed（0 行触发掉幅 raise），但正解是失败 slug
  保留旧 rows（标 stale_from 溯源）+ failed 非空上浮 warning。
- **建议修法**：合并写回旧 rows；`stage_mfm_fetch` 上浮 failed。

## M2（MEDIUM，CONFIRMED，已随 H1 修复）：check_points 静默吞掉 points_json 解析失败的库行

- 即 H1 的机制本体，`db_unparsed` 桶已落，CLI `--check` 同步展示。

## L1（LOW，CONFIRMED，仅记录）：build.py 报告行数虚计——stratagems/detachments 返回 len(rows) 而非实际插入数

- `_insert_stratagems`/`_insert_detachments` 插入时按 `r.get("id")` 过滤，返回值不过滤；
  `_insert_models` 对 datasheet_id 缺失行照插 unit_id=NULL 孤儿行不计不报。当前 CSV
  干净（缺 id 行数 0），纯报告口径问题。建议统一 `(valid, skipped)` 口径。

## L2（LOW，CONFIRMED，仅记录）：update 管线各补丁 stage 的 skipped/invalid 不上浮

- 上游改 unit_id 导致补丁 `stat_skipped` 时，update/restore 的 summary 与 warning 都
  不体现（CLI 直跑有完整打印，但日常入口是 build/update）。建议 warn 聚合加入各
  `*_skipped`/`*_invalid` 非零项。

## L3（LOW，PLAUSIBLE，仅记录）：fp_errata._insert_new_units 的 models 用裸 INSERT——补丁改名边缘场景下重复插行

- 存在性守卫按 (faction_id, name_en) 查，units/weapons 是 INSERT OR REPLACE，唯独
  models 裸 INSERT。将来补丁把 new_unit 的 name 改掉而 unit_id 不变时，models 表追加
  重复属性行。建议插入前先 `DELETE FROM models WHERE unit_id = ?`。

## L4（LOW，CONFIRMED，仅记录）：dsl_apply 全量对账测试的注释合计（2782）与断言（2889）漂移

- 注释漏记 GSC PR25 = 107（与模块 8 F4 同一发现）。断言本身是机器对账，有效。

## L5（LOW，CONFIRMED，仅记录）：update 全管线对黑图书馆 API 重复全量抓取两次

- `stage_aliases_blackforum` 与 `stage_zh_details` 各自 `load_or_fetch_units(
  offline=False)`（~24 页×2）。功能无损纯浪费。建议首抓后传递结果。

---

## 高危点已核无误清单（核法附后）

1. **补丁层幂等性**：DB 副本各连跑两遍，全表内容哈希前后一致，报告计数稳定
   （stat 52 / weapon 3 / kw 10 全 already；text 198 / name 291 / deact 74 / ins 395
   全 already；DSL 2889 全 already）。无叠加、无重复插行。
2. **from 守卫三态**：库值==to 幂等跳过、==from 才改、皆非让路告警——代码与
   mismatch_does_not_clobber 系列测试双确认；`_guard_norm` 保留 `+`/`-` 使
   `20+"` ≠ `20"` 可区分。
3. **restore_authority_layers 挂载**：8 层齐全；build CLI 默认自动补跑；
   test_stage_wired_into_restore 锁死 DSL 层不脱钩。层序问题即 H1（已修）。
4. **expect_duplicate_name 豁免**：默认拦同名异 id、显式旗标才放行，成对覆盖。
5. **SQL 注入面**：表/列名全部过白名单（_STAT_FIELDS/_WEAPON_FIELDS/_TEXT_TARGETS/
   _INSERT_COLUMNS/_PROJECTION_TABLES/_MATERIALIZE_SOURCES），数据值一律参数化；
   PDF/网页文本无进 SQL 语句体的路径。
6. **DSL 指纹守卫**：带 effects 必须有 provenance.text_sha256（录入期强制）；指纹
   漂移同步清空旧投影；跨文件重复 (table,id) 直接 raise。
7. **计数守卫 2889=216/582/2091**：对真实 payload 目录重算并集断言，副本实跑一致。
8. **build 原子替换**：tmp 库全成功才 os.replace，异常删 tmp 保旧库。
9. **mfm 新版式解析与归一兜底**：色块头/▲▼前缀/借调价小节排除/单复数归一唯一命中
   护栏均有回归测试；真库实抓缓存 1233 条可比全一致。TL 双 slug 折叠实测两页无同名
   单位，当前无冲突（见遗留 3）。

## 严重级分布（本模块）

| 严重级 | 数量 | 处置 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 2 | 均已修复 + 成对测试 |
| MEDIUM | 2 | 1 随 H1 修复，1 记录在案 |
| LOW | 5 | 记录在案 |

## 遗留建议

1. H1 修复后建议下次真实 rebuild 时人工核一次「fpe_* 单位 points_json 非 NULL」收尾
   （静态层序测试已钉，行为级对账靠 stage_mfm_check 的 unparsed 告警承接）。
2. `__main__.py` 的 `mfm --slug` 在缓存不存在时裸 traceback，可比照 `--apply` 给
   SystemExit 清晰提示。
3. TL 双 slug 先到先得——GW 若给两边同名单位定不同价会静默取 chaos 价，可在
   `_rows_by_faction` 对同 (fid, unit) 不同价二次写入加告警。
