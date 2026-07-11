# qa_gold v3：11 版口径迁移审计（S5，2026-07-11）

> 方法：96 题逐 gold_type 审计。rule 类逐题对 11 版核心规则原文（data_refined 缓存页）；
> ability/stat/weapon 类先全量扫描 29 个 Faction Pack 的勘误块（"Change to/Add/Delete"
> 格式，共 51 页）与完整数据表页，再对命中项逐块核对是否触及 gold 所问的值。
> 十版原版与 97.9 最终成绩冻结于 `benchmarks/v1_10th/`。

## 结论总览

| gold_type | 题数 | 11 版漂移 | 处置 |
|---|---|---|---|
| stat | 68 | 0 | 不动（十版 codex 数据表在 11 版继续合法，勘误未触及所问数值） |
| weapon | 10 | 0 | 不动（同上） |
| rule | 10 | **7** | 按 11 版核心规则重写 gold（#85/#86/#88/#89/#90/#92/#94），#87/#91/#93 语义未变（#93 补 Stealth 注） |
| ability | 8 | **1** | #41 Boyz 保镖节按 Orks Faction Pack 勘误更新；其余 7 题未被勘误触及 |

## rule 类逐题裁决

| 题 | 词条 | 11 版出处 | 裁决 |
|---|---|---|---|
| #85 | DEADLY DEMISE | 24.08 | **改**：运输载具在载员完成紧急脱离**之后**投骰（旧 gold 写"脱离前"；11 版原文+示例明确时序） |
| #86 | DEEP STRIKE | 24.09 | **改**：9 寸→**8 寸**；改经 ingress move（20.04）措辞 |
| #87 | SUSTAINED HITS | 24.36 | 一致，不动 |
| #88 | SCOUTS | 24.31-24.32 | **改**：机制重做——战前能力结算步三选一（预备队改部署/斥候移动/专属运输载具代移），斥候移动结束须距敌 8 寸以上且发起时须完全在己方部署区 |
| #89 | INFILTRATORS | 24.20 | **改**：9 寸→**8 寸** |
| #90 | LONE OPERATIVE | 24.24 | **改**：语义从"不能被选为目标"强化为"12 寸外**不可见**"；新增间接火力 12 寸条款与 Lone Operative X" 带参形态 |
| #91 | MELTA | 24.25 | 一致，不动 |
| #92 | PISTOL | 24.27+24.07+10.06 | **改**：[PISTOL]≡[CLOSE-QUARTERS]；近身射击的巨兽/载具 -1 命中、目标限制、二选一开火规则 |
| #93 | IGNORES COVER | 24.18 | 语义未变；补"含规则授予的掩体（如 Stealth）"注 |
| #94 | LEADER | 24.22+19.01-19.04 | **改**：新增 SUPPORT 概念（每保镖限 1 领袖+1 支援）；联合单位全程为单一单位（十版"保镖灭后领袖分裂"措辞删除）；死亡触发以最后模型为准；19.04 领袖技能存续规则 |

## Faction Pack 勘误扫描（stat/weapon/ability 排雷）

勘误命中 gold 单位的全部 7 处，逐块核对结果：

| 勘误位置 | 单位（gold 题号） | 改了什么 | 是否触及 gold |
|---|---|---|---|
| Aeldari p23 | Warp Spiders(#46)/Dire Avengers(#48)/Asurmen(#45) | 戏面阵 token 能力、Hand of Asuryan | 否（gold 问 Flickerjump/武器面板/属性） |
| CSM p38 | Abaddon(#21)/Chaos Rhino(#26) | Dark Destiny 能力、装备/运输节 | 否（gold 问 W/SV、T/SV） |
| Orks p24 | **Boyz(#41)** | **Bodyguard 节改写**（满编20双领袖，其一须 WARBOSS） | **是 → gold 已更新** |
| SM p61 | Land Raider Crusader/Redeemer(#17 同名变体) | 关键词节 | 否（基础型号未动） |
| Thousand Sons p10 | Chaos Rhino(#26) | 核心能力节 | 否 |
| World Eaters p8 | Helbrute(#25)/Land Raider/Rhino | Frenzy 能力、关键词节 | 否 |
| Tyranids p20 | Hive Tyrant(#69) | Onslaught 能力 | 否（gold 问 W/SV） |

另：Faction Pack 含**完整 11 版数据表**的单位（如钛帝国 R'varna p49：M8/T10/SV2+/W15/5++）
与 gold #4 一致——包内数据表多为 Forge World/命名变体（Captain Tycho、Land Raider Helios 等），
不覆盖基础 codex 单位，与"补充而非替代"的 11 版设计一致。**这也意味着 Faction Pack 可作为
这批单位的 11 版结构化数据源（S4 增量项）。**

## 版本与影响

- qa_gold.json meta：version=v3、edition=11、source 追加审计说明
- 判分含义变化：v3 下 agent 答"深打 9 寸/渗透 9 寸/十版斥候流程"将被判 ❌——这正是
  版本迁移验证的目的（检验索引里的 11 版规则真的被检索并引用）
- v1（97.9）与 v3 成绩**不可直接比较**：7 题 gold 语义变了

## 实测（2026-07-11，两轮）

- **run1 = 91.7**（88✅/4⚠️/4❌）：#86 深打、#88 斥候答了十版 9 寸/旧流程，引用
  《10版40K通用技能速查表》——十版规则书已不在索引，坐实来源是 **wiki/core-rules
  术语页十版残留**（get_keyword_definition 读到旧版，S6 已知项）。
- **修复**：core-rules 11 个术语页升级 11 版口径（deep-strike/scouts/infiltrators/
  lone-operative/pistol/deadly-demise/leader/melta/sustained-hits/ignores-cover/
  stealth），build+lint 通过（存量 4 断链 error 不变；顺修 lint 对 wiki 宪法文件的
  误报）。
- **run2 = 93.8**（90✅/2⚠️/4❌）：#86/#88 转绿✅。剩余 4 ❌ 两轮一致，全是实体解析
  缺陷（#23 诅咒教徒混淆 / #48 复仇者小队缺别名 / #65 跨阵营游侠 / #76 FP 变体 vs
  基础型），非版本问题——已立项下轮修复。**v3 基线 = 93.8**，产物归档
  `benchmarks/v3_edition11/`。
