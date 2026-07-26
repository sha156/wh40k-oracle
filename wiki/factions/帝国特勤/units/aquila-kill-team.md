---
id: '000004174'
name_zh: 天鹰杀戮小队
name_en: Aquila Kill Team
faction: 帝国特勤
type: unit
points:
  5 models: 100
  10 models: 200
tags:
- unit
- unit/帝国特勤
- 帝国特勤
version:
  points: MFM 2026-07-23 14:17
  source: official-db
sources:
- book: 官方结构库 db/wh40k.sqlite（Wahapedia 11版镜像 + MFM 官方点数）
updated: '2026-07-23'
---

## 属性表
| 模型 | M | T | SV | W | LD | OC |
|---|---|---|---|---|---|---|
| 杀戮小队军士·死亡守望老兵 | 6" | 4 | 3+ | 2 | 6+ | 2 |
| 重装型装甲老兵 | 5" | 6 | 3+ | 3 | 6+ | 2 |

## 射击武器
| 武器 | 射程 | A | BS | S | AP | D | 技能 |
|---|---|---|---|---|---|---|---|
| 阿斯塔特榴弹发射器-破片弹 | 24" | D3 | 3+ | 4 | 0 | 1 | [[core-rules/blast.md\|爆炸]] |
| 阿斯塔特榴弹发射器（穿甲） | 24" | 1 | 3+ | 9 | -2 | D3 | — |
| 爆矢手枪 | 12" | 1 | 3+ | 4 | 0 | 1 | [[core-rules/pistol.md\|手枪]]，[[core-rules/lethal-hits.md\|致命一击]] |
| 死亡守望神射手爆矢卡宾枪 | 24" | 2 | 3+ | 5 | -1 | 1 | [[core-rules/heavy.md\|重型]]，[[core-rules/lethal-hits.md\|致命一击]] |
| 破片炮 | 18" | D3 | 3+ | 7 | -2 | 2 | [[core-rules/blast.md\|爆炸]]，[[core-rules/heavy.md\|重型]]，[[core-rules/lethal-hits.md\|致命一击]]，[[core-rules/rapid-fire.md\|速射D3]] |
| 地狱风暴爆弹步枪 | 30" | 2 | 3+ | 5 | -2 | 2 | [[core-rules/assault.md\|突击]]，[[core-rules/heavy.md\|重型]]，[[core-rules/lethal-hits.md\|致命一击]] |
| 地狱火重型爆弹枪-重型爆弹枪 | 36" | 3 | 3+ | 5 | -1 | 2 | [[core-rules/sustained-hits.md\|连击1]] |
| 地狱火重型爆弹枪-重型火焰喷射器 | 12" | D6 | N/A | 5 | -1 | 1 | [[core-rules/ignores-cover.md\|无视掩体]]，[[core-rules/torrent.md\|洪流]] |
| 等离子焚化枪（标准） | 24" | 2 | 3+ | 7 | -2 | 1 | [[core-rules/assault.md\|突击]]，[[core-rules/heavy.md\|重型]] |
| 等离子焚化枪（过载） | 24" | 2 | 3+ | 8 | -3 | 2 | [[core-rules/assault.md\|突击]]，[[core-rules/hazardous.md\|危险]]，[[core-rules/heavy.md\|重型]] |
| 等离子手枪-标准 | 12" | 1 | 3+ | 7 | -2 | 1 | [[core-rules/pistol.md\|手枪]] |
| 等离子手枪-过载 | 12" | 1 | 3+ | 8 | -3 | 2 | [[core-rules/hazardous.md\|危险]]，[[core-rules/pistol.md\|手枪]] |
| 特种爆矢手枪 | 18" | 1 | 3+ | 4 | -1 | 1 | [[core-rules/pistol.md\|手枪]]，[[core-rules/precision.md\|精准]]，[[core-rules/lethal-hits.md\|致命一击]] |
| 潜猎爆弹步枪 | 30" | 2 | 3+ | 5 | -2 | 2 | [[core-rules/heavy.md\|重型]]，[[core-rules/lethal-hits.md\|致命一击]]，[[core-rules/precision.md\|精准]] |

## 近战武器
| 武器 | 射程 | A | WS | S | AP | D | 技能 |
|---|---|---|---|---|---|---|---|
| 格斗武器 | 近战 | 3 | 3+ | 4 | 0 | 1 | — |
| 战斗刀 | 近战 | 4 | 3+ | 4 | -1 | 1 | [[core-rules/precision.md\|精准]] |
| 重型雷霆锤 | 近战 | 3 | 4+ | 10 | -2 | 3 | [[core-rules/devastating-wounds.md\|毁灭伤害]] |
| 动力武器 | 近战 | 4 | 3+ | 5 | -2 | 2 | [[core-rules/sustained-hits.md\|连击1]] |
| 异形相位刃 | 近战 | 4 | 3+ | 5 | -2 | 1 | [[core-rules/devastating-wounds.md\|毁灭伤害]] |

## 技能
- **【阵营技能】：派遣特工**
- **诛灭异形**：当该单位中的模型进行攻击时，您可以重掷结果为1的命中掷骰。如果攻击的目标没有帝国或混沌关健词,改为您可以重掷命中掷骰。
- **阿斯塔特护盾【装备技能】**：持有者拥有 4+ 无敌豁免
- **杀戮小队**：每当该单位成为攻击的目标时，如果其包含韧性属性不同的模型，则直到攻击单位完成攻击前，在决定致伤成功所需要的掷骰结果时，应使用本单位中多数模型具备的韧性属性值。如果出现两种或更多韧性属性值在数量上并列多数，则取其中的最高值。在决定该单位中的哪些模型可以搭乘某一运输工具时，重装型装甲老兵模型占用*2*个模型的运输容量，但可搭乘任何其所属单位允许搭乘的运输工具，即使其他单位中的类似模型因为拥有重装型装甲关键词而导致无法搭乘
- **武器装备选项**：该单位中每有5个模型，至多1个模型可以将装备的地狱火重型爆矢枪替换为以下一种选项:1 把破片炮1把地狱风暴爆矢步枪和1把阿斯塔特榴弹发射器。该单位中每有5个模型，至多1个模型可以将装备的追猎者爆矢步枪替换为 1把等离子焚化炮 。该单位中每有5个模型，至多1个模型可以将装备的死亡守望神射手爆矢卡宾枪替换为1 把战斗刀。该单位中每有5个模型，至多1个模型可以将装备的重型雷霆锤替换为1把动力武器和1 个阿斯塔特护盾。

## 单位构成
- **5个模型** — 100 分
- **10个模型** — 200 分

## 关键词
- **阵营关键词**：Agents of the Imperium
- **普通关键词**：[[core-rules/infantry.md|Infantry]]，[[core-rules/battleline.md|Battleline]]，Ordo Xenos，[[core-rules/grenades.md|Grenades]]，Imperium，Gravis，Tacticus，Aquila Kill Team，Deathwatch，Retinue