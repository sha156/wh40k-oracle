# 收官检查点：词条解释层 → 诚实性四缺陷 → 点数 apply（2026-07-28）

> 这条线**已全部并入 main**（PR #67 + #68，main HEAD `dc5248a6`），分支与 main 差额 0、
> 工作区干净、无开着的 PR。本文件是状态归档与冷启动交接。

## 1. 现在在哪

| 指标 | 值 |
|---|---|
| main HEAD | `dc5248a6` |
| pytest | **2398 passed**，0 failed |
| 基准 | **115 题 100.0 零硬错**（连跑两轮 99.1 / 100.0） |
| `mfm --check` | 1319 可比 / 1319 一致 / **过期 0** |
| wiki lint | 0 error / 1 warning（alias-conflicts 摘要）/ 4 info |
| 前端 lint | 0 error |
| wiki 规模 | 4950+ 页 |

**跑完 pytest 工作区仍干净**（测试不再写 `wiki/indexes/` 产物）。

## 2. 起因与产出

用户翻兵牌提了三件事，顺藤摸出一串数据层与诚实性缺陷。

### 用户点名的三件

| | 结果 |
|---|---|
| 武器词条鼠标悬停显示解释 | ✅ 全库 127 个词条零解析失败，解释**逐字取自官方中文核心规则**（可 grep 到行号） |
| 技能正文【致命一击】【精准】可交互 | ✅ 三种写法（中文【】/英文[]/`<span class=kwb>`）统一在 `keyword_refs.ability_spans` 一处切段 |
| 危机火刃技能仍是英文 | ✅ **查明补不到**——不是 1 个是 **16 个**，黑图源里 `能力` 字段就是空的（带对照组的 live 查询验证）。**一个字没编** |

### 顺带修掉的真 bug

- **MFM 解析器千分位静默丢行**：`(\d+) pts` 对 `2,200 pts` 零容忍且不报错 → 泰坦两页缓存
  常年 0 行、**7 个 ≥1000 分单位从未被点数校验过**。而待办里「Titan Legions 缺 7 个兵牌」
  是**伪缺口**（泰坦军团就 4 个单位、兵牌与 PDF 逐字一致），那个 7 是被丢掉的行数
- **`_KEEP_SECTIONS` 白名单误伤 60 个子阵营真单位**（含基里曼）→ 纳入后逮到 **46 条过期点数**
- **近战数值指纹主路径全盘失效**（库内 `Melee` vs 黑图「近战」不归一）→ 配对 4085 → **5341**
- **四种互斥的诚实性缺陷**（详见 §3）

### 数据变更（用户授权 apply）

46 条过期点数已 apply，八步流程走完：备份+SHA-256 → **副本试跑逐字段 diff** → apply →
收敛校验**过期 46→0** → 现役口径核对 → wiki 全量重生成 1242 页 → 基准验证 → 页面目检。
**基里曼 340 → 355。**

⚠️ `db/wh40k.sqlite` 是 **gitignored**，数据变更靠命令复现、不进 git：
```powershell
.\.venv\Scripts\python.exe -m db_compile mfm --apply   # 点数
.\.venv\Scripts\python.exe -m db_compile blacklibrary   # 中文层（含那 6 个补上的单位）
```
中文名桥的可复现性已验证：**已提交代码 + 本地缓存重跑即得**，无需改代码，并有测试钉死。

## 3. 四种互斥的诚实性错法（每种留一道锚点题）

| 病象 | 锚点题 | 修法 |
|---|---|---|
| 遇歧义**不查证就反问** → 既不降级也不作答 | #63 | note 改「先逐个候选查证再作答」 |
| **查不到就编否定断言**（「这阵营不存在」） | #109 | 补名字解析 + 措辞说穿「查不到≠不存在」+ 兜底判定 |
| 同名跨阵营**不消歧只报一个** | #118 | 工具边界追加式补报同名兄弟行与各阵营点数 |
| **编造的名字换回真实兵牌**（found=True 每层都成功） | #119 | 2590 样本证明 ratio 判据无解，改绝对编辑距离≤2 + 简称子串单向豁免 |

**这四种互斥**——修好「不许反问」很自然滑向「那就挑一个报」。
所以任何一轮的验收都必须要求「目标题转绿**且**其余锚点保持 ✅」，只看目标题不算数。

**#113/#117 的根因不是「路由偏好选错工具」**（那是 host 的误判），而是
**工具查空 → 触发降级 → 降级链是纯 PDF 经典链** → 从民间译本拿到旧值。
最小修法两处：分隔号 `·`/`.` 归一化**判 exact**（判 fuzzy 会被只信 exact 的
`find_datasheet` 拒绝——解析到了 ≠ 用得上）、`get_keyword_definition` 移出判空表。

## 4. 报告索引（都带可复现命令与证据）

`docs/superpowers/specs/` 下 8 份：
`2026-07-27-zh-abilities-coverage.md`（中文技能覆盖五类归因）、
`-duplicate-units-audit.md`（11 组疑似重复，零数据改动）、
`-titan-legions-datasheet-audit.md`（伪缺口 + 千分位）、
`-mfm-refetch-points-verification.md`（全站重抓，含不 apply 的理由）、
`-mfm-section-coverage-fix.md`（60 个真单位纳入 + 46 条过期明细）、
`-qa-gold-v33-points-coverage.md`（基准扩题）、
`-calc-points-negative-assertion-fix.md`、`-same-name-cross-faction-disambiguation.md`、
`-fuzzy-silent-mismatch-fix.md`、`-data-source-routing-fix.md`。

devlog（面向学习，每篇讲"值得学的点"）：`D:\Project\devlog\wh40k-oracle\commits\` 11 篇。

## 5. 剩余（都非阻塞）

- **`rag_search` 恒返 k 条、`found` 恒为 True**：不相关段落也以「检索到依据」的形状交给模型。
  属检索质量问题，已点名遗留
- **fp11e 64 分队 + 200 战略缺容器名/type**：Wahapedia 无源，需人工裁决，**禁止按 id 前缀反推**
- **战略/增强剩余中文名**：GW 免费包不含 codex 正文，只能人工译
- **11 组疑似重复单位**：报告已出、一行数据未改，留谁是用户的决定
- **新 wiki 页未进 FAISS**：L2 混进 L0/L1 索引是分层决策，需用户拍板
- **Docker 镜像未真实构建**（本机 WSL 装残）、**腾讯云安全组未放行 8100**（只有用户能点）
- 军表 PR1c 文本解析（缺真实样本）；外部源观察（BSData-11e / Wahapedia 11 版 / 黑图 11 版 gameId）

## 6. 冷启动怎么接

```powershell
cd D:\Project\py\RAG
git log --oneline -1                                    # 应为 dc5248a6 或其后继
.\.venv\Scripts\python.exe -m pytest -q                 # 应 2398 passed
.\.venv\Scripts\python.exe -m db_compile mfm --check    # 应 1319/1319/过期 0
.\.venv\Scripts\python.exe -m wiki_engine lint          # 应 0 error
```
判基准回归**只看逐题 verdict、不看总分**：
`python scripts/compare_bench_runs.py <base.json> <new.json>`
（#29/#41/#42 是已知固定波动题，会互换）。
