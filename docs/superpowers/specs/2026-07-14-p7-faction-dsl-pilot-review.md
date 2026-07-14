# P7 阵营技能 DSL 试点 spec 对抗性复审报告

> 2026-07-14，独立子代理白盒复审初稿 spec，任务是证伪。所有结论落到真实代码/数据证据
> （只读 SQL 跑在 `db/wh40k.sqlite`）。16 项 finding 已全部回写进 design spec 同日版本，
> 本文归档证据与处置。

## 事实核查（零节断言抽查 9 条）

**8 项全中**：id 000008439=FTGG(scope=NULL)；44 战略/10 detachments/28 增强计数；
DSL 列预留且 100% 空；name_zh 全 NULL；Auxiliary Cadre 漂移坐实（另加固：Photon
Grenades 战略 When 段也漂移）；FTGG 11 版原文"improve the Ballistic Skill characteristic"
逐字核对；unmodified-1 恒失手已实现（`sequence.py:395`，BS 下限是涌现行为非钳制）；
守方白名单四种+披露机制核对无误。

**1 项措辞不精确**：`sequence.py:209-211` 中 211 行夹的是 wound_mod，非 hit modifier
（→ F13，已修措辞）。**1 项口径漂移**：detachments TAU 实为 9 条规则行 + 1 行 'KEYWORDS'
噪声，非"8 分队=8 行"（→ F10）。

## Finding 清单与处置

| # | 级别 | 问题 | 处置（回写位置） |
|---|---|---|---|
| F1 | CRITICAL | DSL 只落 DB 会被 `--rebuild` 静默清零（`build.py:198-203` INSERT OR REPLACE 不含 effect_dsl_json；`_RESTORE_STAGES` 无 DSL 阶段） | 文件真源 `dsl_payloads/tau.json` + `stage_dsl_apply` + rebuild 幸存测试（§二.1/§七.4/D6） |
| F2 | CRITICAL | condition 合取样例与引擎冲突：`_cond_true` 只读 `condition[0]`，照样例录入 FTGG 无条件生效；未知 tag 静默 False | 单 tag 契约 + 复合 tag 注册制 + `_cond_true` 未知 tag raise（§二.3/D7） |
| F3 | HIGH | abilities 表无 faction/detachment 列，load_faction_dsl 无法按分队检索；三套分队身份体系互不链接 | 链接由载荷 JSON 自带字段承载，join 键统一 enhancements.detachment_name 拼写（§二.2/D5） |
| F4 | HIGH | 攻方侧 `w.effects` 消费零记账，笔误/漏接=静默零效果 | `unconsumed_attacker_effect_notes` 同款对账（§四.5） |
| F5 | HIGH | `modeled_effects` 从 raw_keywords 重推导不读 w.effects，DSL 生效也不进报告 | 注入点自带汇报追加项 + "出现⇄影响"成对断言（§四.4） |
| F6 | HIGH | web_api `sanitize_options` 未知键静默丢弃，全部新开关会被吞 | 白名单/收敛函数扩充 + 后端回显生效清单 + 对拍测试（§四.6） |
| F7 | HIGH | encoded 判据缺"施加侧有消费点"，防守向条目会假 encoded | 判据第④条 + 分侧白名单由消费点生成 + 期望值必须动（§二.4/D4） |
| F8 | MEDIUM | bs_improve 与掩体（同为 BS 特征值语义却折进 hit_neg）通道不对称；特征值上限条款语料缺页 | PR2 内裁决对称性 + 三方叠加测试 + 上限列观察项（§四.2/D2） |
| F9 | MEDIUM | from 守卫"不符则报错"会破坏 restore 幂等 | 采用 fp_errata 三态语义（§三） |
| F10 | MEDIUM | 9 规则行↔8 分队口径漂移，硬编 8 会静默漏条 | 对账枚举源=非噪声行全集（§零/§三.1） |
| F11 | MEDIUM | agent/tools.py 直调路径缺席，Agent 模式用不了 DSL 开关 | 模块清单补 tools.py，四路对拍（§四.6/§六） |
| F12 | MEDIUM | 同一规则文本双处存放无同步报警 | text_sha256 指纹对账（§二.2/§七.3） |
| F13 | LOW | 夹取行号表述不精确 | 措辞已修（§零） |
| F14 | LOW | "PR1 改文本影响 agent 读数"过虑（无消费者读正文列） | 归因改为例行护栏（§三/§七.7） |
| F15 | LOW | dsl_version 无版本策略 | 只接受 1，其他拒载（§二.2） |
| F16 | LOW | condition_json 死列可作链接载体 | 采 F3 载荷方案后保留不占用（D5） |

## 复审确认无害项

- **D5 不污染 P5 分类器**：全库对账过滤 `owner_id IS NOT NULL AND != ''`
  （`test_simulator_abilities.py:290-291`），新行 owner_id=NULL 天然排除；
  `load_abilities`/`web_api/codex.py` 均 `WHERE owner_id = ?` 不误捞
- **frozen dataclass 注入可行**：`engine.py:48,54-55`、`assembly.py:119` 已有
  `dataclasses.replace` 先例；注入放 profile/assembly 层，依赖纪律不破
- **PR1 改文本对现有链路无害**：全仓 grep 无消费者读 `stratagems.text_zh`/
  `detachments.rule_text` 正文（仅 `profile.py:127` 读名字列）

## 总评

事实底座扎实（9 项抽查 8 中）。两条实质损失缝（F1 rebuild 清零、F2 条件静默失效）
必须 PR0 收口——均已收口。F3-F7 接线完整性问题不改也能开工但会在 PR2/PR3 变返工点，
已全部前置进 spec。
