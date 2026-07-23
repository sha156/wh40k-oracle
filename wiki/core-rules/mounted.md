---
id: mounted
name_zh: 骑乘
name_en: Mounted
type: core-rule
sources:
- book: Core Rules - New 40K Core Rules
  pages: []
updated: '2026-07-23'
---

骑乘是一个单位类型标记，用于标示骑乘坐骑或载具平台的近战步兵型单位，无独立通用规则。

## 骑乘 MOUNTED

【骑乘】是数据卡上的单位类型关键词，用于标示骑乘坐骑（如摩托、骑兽）的单位。**11 版核心规则本册中未出现【MOUNTED】关键词的任何独立通用规则条文**——它不像 [[core-rules/infantry.md|步兵]]/[[core-rules/monster.md|巨兽]]/[[core-rules/vehicle.md|载具]] 那样拥有专属的地形穿越或移动规则。

其实际作用是作为分类与限定标记：

- 供数据卡技能、计谋、增强、武器技能以关键词形式**点名生效对象**（如某能力"仅对【骑乘】单位生效"）。
- 作为 sqlite/引擎侧的关键词过滤字段。

具体行为一律由引用它的那条阵营规则或武器技能决定；核心规则不为【骑乘】设定通用行为。

> 关联：类型对照见 [[core-rules/infantry.md|步兵]] / [[core-rules/monster.md|巨兽]] / [[core-rules/vehicle.md|载具]]。
> 依据：11 版 Core Rules 本册未见【MOUNTED】独立通用规则；为单位类型标记（无 section 号可引）。