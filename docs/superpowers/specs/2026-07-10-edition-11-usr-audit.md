# 11 版 USR 审计：核心技能 vs 模拟器建模词条（S3）

> 2026-07-10 由子代理通读 11 版核心规则 24 章（page_078-085）+ 射击类型（10.05-10.07）+
> 战斗阶段（12.04-12.06）+ 涌动（21.01-21.02），对比 engines/simulator/ 实现逐条核实。
> 18 个高价值词条全部在 11 版原文中找到出处。结论三类：A 一致可用 / B 有变要改 / C 未建模。

## A 类：语义一致（14+ 词条，直接可用）

rapid fire（24.30 半射程+X）、melta（24.25 半射程 D+X）、sustained hits（24.36 暴击+X命中）、
torrent（24.37 自动命中）、twin-linked（24.38 重掷致伤）、anti-X（24.03 未修正 Y+ 暴击致伤）、
ignores cover（24.18 目标不享掩体，含抵消 Stealth）、feel no pain（24.12 X+ 逐点免伤）、
lance（24.21 冲锋致伤+1）、devastating wounds（24.10 致命伤/每暴击最多杀1模型/溢出作废/FNP逐点——
与 _spike_allocation 逐条吻合）、fights first（24.13，fight_order 已 11 版化）、
precision/extra attacks/one shot/hazardous/deadly demise/assault（机制未变，sim 一贯标注不建模，无冲突）。

⚠ A 类唯一保留（待人工复核）：sim 对致命伤池也施加 damage_reduction（受伤-1）；11 版 dev
伤害是 mortal wounds，多数"受伤-1"按规不减免致命伤。低频交互（守方开减伤 + 攻方带 dev）。

## B 类：语义有变（需改代码，按优先级）

### B1 STEALTH（24.33）——机制彻底改变【高优先】
- sim（十版）：攻方远程命中 -1（`abilities.py` → `Effect("hit","modify",(-1,),("phase_shooting",))`）
- 11 版原文："each time a ranged attack targets that unit, **that unit has the benefit of
  cover** against that attack (13.08)"
- 改法：Stealth 改走掩体/保存通道（复用 cover 路径），且可被 [IGNORES COVER] 抵消

### B2 INDIRECT FIRE（24.19 + 10.07）——命中机制重做【高优先】
- sim（十版）：命中 -1 + 目标获掩体
- 11 版原文：目标获掩体 + **禁止重掷命中** + "unmodified hit roll of 1-5 fails"（只 6+ 命中）；
  仅当"本回合驻停 + 有友军可见目标"时改善为 "1-3 fails"（4+ 命中）——与 BS 无关
- 改法：indirect 时命中判定覆盖为固定阈值（6+，或新增"驻停+观察者"开关时 4+），掩体保留

### B3 HEAVY（24.16）——触发条件放宽【中】
- sim（十版）：stationary（完全不动）才 +1 命中
- 11 版原文：未交战 + 本回合未上场 + 全员移动 ≤3" 即 +1
- 改法：条件语义从 stationary 改为"移动≤3"且未交战"（UI/CLI 开关随之改名或加开关）

### B4 LETHAL HITS（24.23）——强制改可选【中】
- sim（十版）：暴击命中强制自动致伤（跳致伤骰，不可能再出暴击致伤）
- 11 版原文："you **can choose** for that attack to automatically wound" + 设计师注明可放弃
  以保留触发 [DEVASTATING WOUNDS]/anti 暴击致伤的机会
- 改法：武器同时带 dev/anti 暴击致伤来源时，暴击命中走"择优"分支（期望值比较）

### B5 BLAST X（24.05）——新增带参形态【中】
- sim（十版）：硬编码 +1/每5模型（只支持 [BLAST]）
- 11 版原文："[BLAST X] … add X additional attack dice for every five models"
- 改法：blast 带参解析，`atk += X * (models//5)`

### B6 PSYCHIC（24.29）——新增"可无视命中修正"【待复核】
11 版赋予"可无视 BS/WS 与命中骰的任意修正"（可抵消 Stealth/间接/-1 类）；sim 目前纯标注。
中等置信（需复核十版原文确认属新增）。

### B7 PISTOL → CLOSE-QUARTERS（24.27/24.07 + 10.06）【低，信息性】
[PISTOL] 与 [CLOSE-QUARTERS] 等同且将被取代；近身射击对 MONSTER/VEHICLE 非近战武器 -1 命中。
sim 未建模数值暂无错误；词库应补 close_quarters 识别、注解文案更新。

## C 类：未建模的 11 版机制

- **CLEAVE X（24.06）**【建议优先补】：近战版 blast（全部攻击只打一个目标时每5模型+X攻击骰）。
  parse.py 已识别（KNOWN_PARAM）但 keyword_to_effects 无分支——打大编制单位的近战低估攻击数
- CLOSE-QUARTERS 射击类型（10.06）：交战中可开火；M/V 非近战武器 -1 命中
- OVERRUN FIGHT（12.06）：Fight step 中途接敌的单位可额外 pile-in 参战（影响"谁能打"，
  不改单次攻击数学；fight_order 未建模 overrun 资格）
- SURGE MOVE（21.01-21.02）：反应式移动，只改站位不进攻击序列数学
- 附：sim 建模的 conversion（长射程暴击4+）不是 11 版核心 USR（24 章无此条），系阵营专属
  武器关键词，需对阵营规则复核出处

## S4 结构化源调研结论（同日）

| 源 | 11 版状态 | 结论 |
|---|---|---|
| wahapedia | `wh40k11ed` URL 只是 alias 回 10ed 内容；Last_update=2026-06-13（11版生效前） | **未迁移**，等 |
| 黑图书馆 | gameId=2 仍十版40K（1167单位/38阵营）；gameId=5 是 Kill Team 非 11 版 | **无 11 版数据** |
| BSData | **BSData/wh40k-11e 仓库已建**（2026-05-12 创建，07-10 当天仍在推送），但根目录尚无 .cat 数据文件 | **在建观察项**，成熟后走既有 crosscheck .cat 解析接入 |
| MFM 官方实时站 | 已是 11 版梯度点数 | ✅ 已同步（1224/1224） |

⇒ DB 全量 11 版迁移暂无可用结构化源；过渡态 = 十版骨架 + 11版 MFM 点数 + Faction Pack 文本层补丁（S2 已实现版本仲裁披露）。
