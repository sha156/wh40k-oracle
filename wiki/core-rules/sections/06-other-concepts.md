---
id: core-rules-06
name_zh: 核心规则第 6 章《其他概念》
name_en: 'Core Rules 06: OTHER CONCEPTS'
aliases:
- 核心规则 06
type: core-rule
tags:
- core-rule
version:
  rules: 11版 Core Rules（BASIC RULES）
sources:
- book: Core Rules - New 40K Core Rules
  pages:
  - page_024.md
- book: 核心规则（GW 官方简体中文，11 版）
  pages:
  - page_024
updated: '2026-07-26'
---

11 版核心规则第 06 章《其他概念》（OTHER CONCEPTS）全文，共 3 节，官方节号 06.01–06.03。

> 正文为 **GW 官方简体中文版**；每节可展开对照官方英文原文。中文由官方 PDF 文本层直提，表格与版式会有失真——**判定规则以英文原文为准**。

## 可见度 06.01

*VISIBILITY*

视野直线将被用于决定模型之间的可见度。在一个观察模型拥有视野直线时，那个模型必须能够从自身的任意部分画出一条 1mm 宽的虚拟直线，与被观察的模型的任意部分相连。这条直线就是所谓的视野直线。在这么做时，观察模型和被观察模型所属单位中的其他模型被忽略。

如右页图例所示，其他模型和单位可以对观察模型可见或者完全可见。请注意，地形可能会拥有对可见度产生影响的额外规则（13.07)。

<details>
<summary>官方英文原文</summary>

Line of sight is used to determine visibility between models. For an observing model to have line of sight, it must be possible to draw an imaginary straight line, 1 mm wide, from any part of that model to any part of the model being observed. This line is the line of sight. While doing so, other models in the observing model’s unit and in the observed model’s unit are ignored. Other models and units can be either visible or fully visible to the observing model, as shown opposite. Note that terrain applies additional rules to visibility (13.07).

</details>

## 致命伤 06.02

*MORTAL WOUNDS*

一些攻击或规则会对单位造成致命伤。每当一个单位受到一处或更多致命伤时，其控制玩家必须为每一处致命伤结算以下流程，直到所有致命伤都被分配完毕，或者单位被摧毁为止：

1. 选择模型：按照下方第一个满足的要求选择单位中的一个模型：如果那个单位中一个非角色模型失去了至少一点或更多耐伤，那么您必须选择那个模型。

若是其他情况，如果那个单位中包含一个或更多非角色模型，那么您必须选择其中一个模型。

若是其他情况，如果那个单位中的一个或更多角色模型失去了一点或更多耐伤，那么您必须选择其中一个模型。

若是其他情况，那么您必须选择那个单位中的一个角色模型。

2. 结算伤害：被选择的模型失去 1 点耐伤。如果这么做将导致模型的耐伤变为 0，那么那个模型被摧毁。

致命伤与普通伤害在结算攻击骰时，如果攻击同时造成了致命伤以及普通伤害，那么先结算所有普通伤害，随后再结算所有致命伤。

<details>
<summary>官方英文原文</summary>

Some attacks or rules inflict mortal wounds on units. Each time a unit suffers one or more mortal wounds, its controlling player must resolve the following sequence for each of those mortal wounds, until either all of them have been inflicted or that unit is destroyed:
1. Select Model: Select one model in that unit by following the first instruction below that applies:
   - If a non‑CHARACTER model in that unit has lost one or more wounds, you must select that model.
   - Otherwise, if that unit contains one or more non‑CHARACTER models, you must select one of those models.
   - Otherwise, if one or more CHARACTER models in that unit have lost one or more wounds, you must select one of those models.
   - Otherwise, you must select one CHARACTER model in that unit.
2. Resolve Damage: The selected model loses 1 wound. If this reduces that model’s remaining wounds to 0, it is destroyed.

**MORTAL WOUNDS AND NORMAL DAMAGE**
When resolving attack dice, if those attacks inflict a mixture of both mortal wounds and normal damage, resolve all of the normal damage first, then resolve all of the mortal wounds.

</details>

## 危险掷骰 06.03

*HAZARD ROLLS*

在为一个单位进行危险掷骰时，掷一枚 D6：若结果为 1-2，那次掷骰失败，并且那个单位受到 1 处致命伤（见上方），如果那个单位中的每一个模型都是一个凶兽/载具模型，则改为造成 3 处致命伤。

如果一个单位需要进行多次危险掷骰，那么同时进行所有掷骰。

模型可见模型完全可见单位可见如果一个单位中的一个或多个模型对观察模型可见，那么那个单位可见。

单位完全可见如果一个单位中的每一个模型都对观察模型完全可见，那么那个单位完全可见。在进行判断时，观察模型的视线可以穿过那个单位中的其他模型。

如果一个模型的任意部分对观察模型可见，那么那个模型可见。

如果一个模型面向观察模型的所有部分都对其可见（也就是说如果使那个模型任意部分不可见的因素只有那个模型本身)，那么那个模型完全可见。

26战斗轮次27每一局《战锤 40000》的游戏都将按照一系列战斗轮次进行。本章节将详细解释战斗轮次的结构，以及玩家轮流进行移动和攻击的顺序。

每个战斗轮次都会按照以下的步骤进行结算：

1. 战斗轮次开始

2. 玩家回合

3. 战斗轮次结束

<details>
<summary>官方英文原文</summary>

To make a hazard roll for a unit, roll one D6: on a 1-2, that roll fails and that unit suffers 1 mortal wound (see above), or 3 mortal wounds instead if each model in that unit is a MONSTER/VEHICLE model. If more than one hazard roll is required for a unit, make all of those rolls simultaneously.

### MODEL VISIBLE
If any part of another model is visible to the observing model, that model is visible.

### MODEL FULLY VISIBLE
If every part of another model that is facing the observing model is visible to the observing model (so the only thing blocking visibility to any part of that other model is that model itself), that model is fully visible.

### UNIT FULLY VISIBLE
If every model in a unit is fully visible to the observing model, that unit is fully visible. When determining this, the observing model can see through other models in that unit.

### UNIT VISIBLE
If one or more models in a unit are visible to the observing model, that unit is visible.
## THE BATTLE ROUND

</details>