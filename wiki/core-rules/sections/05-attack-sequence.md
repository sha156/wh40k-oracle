---
id: core-rules-05
name_zh: 核心规则第 5 章《攻击流程》
name_en: 'Core Rules 05: ATTACK SEQUENCE'
aliases:
- 核心规则 05
type: core-rule
tags:
- core-rule
version:
  rules: 11版 Core Rules（BASIC RULES）
sources:
- book: Core Rules - New 40K Core Rules
  pages:
  - page_018.md
  - page_019.md
- book: 核心规则（GW 官方简体中文，11 版）
  pages:
  - page_018
  - page_019
updated: '2026-07-26'
---

11 版核心规则第 05 章《攻击流程》（ATTACK SEQUENCE）全文，共 4 节，官方节号 05.01–05.04。

> 正文为 **GW 官方简体中文版**；每节可展开对照官方英文原文。中文由官方 PDF 文本层直提，表格与版式会有失真——**判定规则以英文原文为准**。

## 1.命中掷骰 05.01

*HIT ROLLS*

为每一枚攻击骰进行一次攻击掷骰，掷一枚 D6。确认每一次掷骰结果是否命中或者失败，具体以第一个满足的下方条件为准：未修正的失败未修正的暴击命中大于等于那次攻击的 BS/WS 属性成功命中任何其他结果失败

<details>
<summary>官方英文原文</summary>

Make one hit roll for each attack dice by rolling one D6. For each result, check if it fails or is a hit by matching the first condition below that applies:

- Unmodified **FAILS**
- Unmodified **CRITICAL HIT**
- Equal to or greater than that attack’s BS/WS characteristic **HIT**
- Any other result **FAILS**

</details>

## 2.致伤掷骰 05.02

*WOUND ROLLS*

为每一次命中进行一次致伤掷骰，掷一枚 D6。确认每一次掷骰结果是否成功致伤或者失败，具体以第一个满足的下方条件为准：未修正的失败未修正的暴击致伤掷骰结果大于等于下方的条件要求：造成致伤攻击的力量 VS 目标的韧性需要结果力量是韧性的两倍（或大于两倍）+力量大于韧性+力量等于韧性+力量小于韧性+力量是韧性的一半（或低于一半）+任何其他结果失败

<details>
<summary>官方英文原文</summary>

Make one wound roll for each hit by rolling one D6. For each result, check if it fails or is a wound by matching the first condition below that applies:

- Unmodified **FAILS**
- Unmodified **CRITICAL WOUND**
- Equal to or greater than the required result below: **WOUND**

| ATTACK’S STRENGTH VS TARGET’S TOUGHNESS | REQUIRED RESULT |
|---|---|
| Strength is TWICE (or more than twice) the Toughness | + |
| Strength is GREATER than the Toughness | + |
| Strength is EQUAL to the Toughness | + |
| Strength is LESS than the Toughness | + |
| Strength is HALF (or less than half) the Toughness | + |

- Any other result **FAILS**

Each time the active player is instructed to resolve the attack sequence, they follow the steps below. In each step, if there is more than one dice to roll, make all of those rolls simultaneously.

1. HIT ROLLS
2. WOUND ROLLS
3. SAVE ROLLS
4. INFLICT DAMAGE

**WHEN DOES THIS SEQUENCE END?**  
If an attack fails or inflicts damage, this sequence ends for that attack. When all attacks have either failed or inflicted damage, this sequence ends and those attacks have been resolved.

**CRITICAL HITS AND CRITICAL WOUNDS**  
Critical hits are still hits, and critical wounds are still wounds. In addition, other rules can be triggered by a critical hit or a critical wound, such as [LETHAL HITS] and [DEVASTATING WOUNDS] (24).

**CURRENT ALLOCATION GROUP**  
The first group in the allocation order begins as the current group. Once all models in an allocation group are destroyed, the next group in the allocation order becomes the current one.

**SEE ALSO**  
- Destroyed  
- Modified Characteristics  
- Modifying Damage  
- Modifying Dice Rolls  
- Random Characteristics

</details>

## 3.豁免掷骰 05.03

*SAVE ROLLS*

对立玩家将结算以下流程：

1. 建立群组：将目标单位中的所有模型分为以下群组，按需进行对应次数的分类：

- 为每一个角色模型单独分组

- 为所有拥有相同 W、Sv 和 InSv 属性的其他模型进行分组。

2. 分配顺序：宣布对这些群组的攻击分配顺序，适用以下所有规则：

- 如果一个非角色群组中包含了一个失去了一点或更多耐伤的模型，那么那个群组将位于分配顺序的最上方。

- 在分配顺序中，没有任何角色群组能够优先于非角色群组。

- 包含了一个失去了一点或更多耐伤的模型的角色群组在分配顺序中必须优先于没有包含失去耐伤的模型的角色群组。

3. 进行豁免掷骰：对立玩家将为每一次对目标造成致伤的攻击进行一次豁免掷骰，掷一枚 D6。

<details>
<summary>官方英文原文</summary>

The opposing player resolves the following sequence:

1. **Create Groups**: Divide all models in the target unit into the following groups, as many times as required:
    - One group for each CHARACTER model.
    - One group for all other models with the same W, Sv and InSv characteristics.
2. **Allocation Order**: Declare the order in which those groups will have attacks allocated to them, applying all of the following:
    - If a non-CHARACTER group contains a model that has lost one or more wounds, that group must be first in the allocation order.
    - No CHARACTER group can be earlier in the allocation order than a non-CHARACTER group.
    - CHARACTER groups containing a model that has lost one or more wounds must be earlier in the allocation order than CHARACTER groups containing no wounded models.
3. **Make Save Rolls**: The opposing player makes one save roll for each attack that wounded the target by rolling one D6.

</details>

## 4.造成伤害 05.04

*INFLICT DAMAGE*

对立玩家将按照下方流程结算每一次豁免掷骰，从最低的掷骰结果到最高的掷骰结果进行结算，直到所有都被结算完成，或者目标单位中的所有模型都被摧毁为止（如果是后者，那么任何多出的攻击将丢失)。

1. 选择模型：为当前的分配群组（见右侧）选择一个模型；如果可能，被选择的必须是一个失去了一点或更多耐伤的模型。

2. 确认豁免掷骰：查看每一次掷骰结果，确认攻击是否造成伤害或者失败，具体以第一个满足的下方条件为准：未修正的造成伤害无敌豁免：如果当前分配群组中的模型拥有 InSv 属性，并且掷骰结果大于等于那个属性的数值。

豁免与 AP：在为掷骰结果进行了攻击武器AP 属性的修正之后，如果被修正的结果大于等于当前分配群组中模型的 Sv 属性。

任何其他结果造成伤害

3. 结算伤害：如果攻击造成了伤害，那么被选择的模型失去相当于那次攻击 D 属性数量的耐伤。如果这次伤害导致那个模型的剩余耐伤被降低至 0 或更低，那么那个模型被摧毁。

另请参见

- 被摧毁

- 被修正的属性

- 修正伤害

- 修正掷骰结果

- 随机属性当前分配群组位于分配顺序最上方的群组是当前群组。

在一个分配群组中的模型全部被摧毁之后，在分配顺序中的下一个群组将成为当前群组。

示例：一个 AP 属性为 -1 的攻击将把一次结果为 3 的豁免掷骰修正成结果为 2。如果模型的 Sv 属性优于或等于 2+，那么那次攻击失败。

攻击流程示例3，与其他攻击不是同类攻击。

05 20进行攻击手爆X5爆

1. 选择武器红色红色单位正在进行攻击。以下武器被选择进行射击：

- 2 把爆矢枪（爆）

- 2 把爆矢手枪（手）

- 1 把重型爆矢枪（重）

2. 选择目标蓝色蓝色单位被选择成为目标。这个单位中的所有模型都对攻击单位可见。目标位于所有武器的范围内，一把爆矢手枪除外，因此那件武器不能进行任何攻击。

3. 结算攻击只有一个敌方单位被选择成为目标，控制玩家拾取攻击骰：

- 玩家为爆矢枪和爆矢手枪拾取了总共五枚攻击骰，这些武器的 A 属性分别为 2 和 1，并且都进行同类攻击。

- 玩家为重型爆矢枪拾取三枚攻击骰，它的 A 属性为结算攻击骰结算其他攻击手爆X51.爆2.2.3.3.

1. 命中掷骰控制玩家先为爆矢枪和爆矢手枪进行五次命中掷骰。武器的 BS 属性为 3+。一共有四次攻击命中目标。

2. 致伤掷骰控制玩家进行四次致伤掷骰。这些武器的 S 属性为 4，目标单位的 T 属性为 3，需要 3+ 的掷骰结果来致伤目标。一共有三次攻击对目标造成致伤。

3. 豁免掷骰目标单位的控制玩家进行三次豁免掷骰。

4. 造成伤害

- 最低的一次掷骰结果小于目标的 InSv 和 Sv 属性，因此那次攻击造成伤害。被分配了这次攻击的模型在受到伤害后耐伤属性变为 0，因此被摧毁。

- 第二低的掷骰结果小于目标的 InSv 属性，但是大于目标 3+ 的 Sv 属性；那次攻击失败。

- 其中一次掷骰结果大于目标 5+ 的 InSv 属性；那次攻击失败。

1.

1. 命中掷骰控制玩家随后为重型爆矢枪进行 3 次命中掷骰。这件武器的 BS 属性为 4+。其中两次攻击命中目标。

2. 致伤掷骰控制玩家进行两次致伤掷骰。武器的 S 属性为 5，因此掷骰结果为 3+ 时就会致伤目标。两次攻击都造成致伤。

3. 豁免掷骰目标单位的控制玩家进行两次豁免掷骰。

4. 造成伤害

- 最低的一次掷骰结果在受到了武器 AP 属性的 -1 修正后，小于目标 3+ 的 Sv 属性，因此造成伤害。被分配了这次攻击的模型在受到伤害后耐伤属性变为 0，因此被摧毁。

- 另一次掷骰结果等于目标 5+ 的 InSv 属性；那次攻击失败。

攻击联合单位X1爆爆爆离爆爆重爆重爆X14 X6

1. 选择武器

3. 结算攻击红色红色单位正在进行攻击。以下武器被选择进行射击：只有一个敌方单位被选择成为目标，因此控制玩家将拾取攻击骰。玩家决定先结算重型爆矢枪的攻击，每一把武器的 A 属性为 3，因此拾取六枚攻击骰。

- 7 把爆矢枪（爆）

- 1 把等离子手枪（离）剩余武器的攻击骰将在重型爆矢枪的攻击被结算完成后进行结算，具体如下：

- 2 把重型爆矢枪（重）

2. 选择目标

- 每把爆矢枪的 A 属性为 2，因此总共拾取蓝色蓝色单位被选择成为目标。目标是一个由炽天使单位和圣塞莱斯汀（以及双生圣女）组成的联合单位（19)。这个单位中的所有模型都对攻击单位可见，并且位于所有被选择武器的范围内。

14 枚攻击骰。

- 等离子手枪的 A 属性为 1，因此拾取 1 枚攻击骰。

分配群组

1. 建立群组并宣布顺序目标单位的控制玩家将单位分成不同的群组：一个群组中包含了圣塞莱斯汀，一个群组中包含了双生圣女，还有一个群组中包含了炽天使。随后，玩家宣布分配顺序，选择将双生圣女放在顺序最上方（1)，希望她们更好的 Sv 和 InSv 属性能够抵御敌人的攻击。随后，炽天使必须被选择成为序列中的第二位（2)，因为圣塞莱斯汀属于一个角色模型，必须位于顺序最后（3)。

2. 结算攻击骰重型爆矢枪的攻击对目标造成五次致伤，因此目标单位的控制玩家进行五次豁免掷骰。

重重豁免掷骰2 2 2 2 2 3 1 1每次攻击将被逐次结算，从最低的豁免掷骰结果至最高的结果：

- 两次结果为 1 的豁免掷骰将被优先分配至当前的分配群组（双生圣女)。两次攻击造成伤害，两位双生圣女都被摧毁。

- 现在结果为 3 的豁免掷骰将被分配至炽天使，她们变成当前分配群组。在进行了武器 AP 属性 -1 的修正后，这次攻击也将造成伤害，将一个炽天使模型摧毁。

- 剩余的攻击失败，因此不会造成任何伤害。

3. 选择下一组攻击骰并重复流程本章节中将包含一些在进行攻击时最常见的额外规则概念。

<details>
<summary>官方英文原文</summary>

The opposing player resolves the following sequence for each save roll, working from lowest result(s) to highest result(s), until all attacks are resolved or all models in the target unit are destroyed – in the latter case, any excess attacks are lost.

1. **Select Model**: Select one model in the current allocation group (see right); this must be a model that has lost one or more wounds if possible.
2. **Check Save Roll**: For each result, check if that attack inflicts damage or fails by matching the first condition below that applies:

| Condition | Result |
|---|---|
| Unmodified | INFLICTS DAMAGE |
| Invulnerable Save: The models in the current allocation group have an InSv characteristic, and the result is equal to or greater than that characteristic. | FAILS |
| Save and AP: After modifying the result by the attacking weapon’s AP characteristic, it is equal to or greater than the Sv characteristic of models in the current allocation group. | FAILS |
| Any other result | INFLICTS DAMAGE |

Example: An AP characteristic of -1 would modify a save roll of 3 to a 2. For models with a Sv characteristic of 2+ or better, that attack would fail.

3. **Resolve Damage**: If that attack inflicts damage, the selected model loses a number of wounds equal to that attack’s D characteristic. If this reduces that model’s remaining wounds to 0 or fewer, it is destroyed.
## 05 ATTACK SEQUENCE EXAMPLES

### 1. SELECT WEAPONS
The RED unit is attacking. The following weapons are selected to make attacks with: 

- 2 boltguns (B)
- 2 bolt pistols (BP)
- 1 heavy bolter (HB)

### 2. SELECT TARGETS
The BLUE unit is selected as the target. The unit is visible to all models in the attacking unit. All of the selected weapons are in range, with the exception of one bolt pistol. As a result, that weapon will not make any attacks.

### 3. RESOLVE ATTACKS
There is only one enemy unit being targeted, so the controlling player now gathers attack dice:

- Five attack dice are gathered for the boltguns and bolt pistol, which have A characteristics of 2 and 1 respectively and all make identical attacks.
- Three attack dice are gathered for the heavy bolter, which has an A characteristic of 3 but does not make identical attacks.

BP
BP
B
B

X5

X3

**1. HIT ROLLS**  
The controlling player chooses to make the five hit rolls for the boltguns and bolt pistol first. The BS characteristic of the weapons is 3+. Four of the attacks hit the target.

**2. WOUND ROLLS**  
The controlling player makes four wound rolls. The weapons have an S characteristic of 4 and the target unit has a T characteristic of 3, so rolls of 3+ are required to wound. Three of the attacks wound the target.

**3. SAVE ROLLS**  
The target unit’s controlling player makes three save rolls.

**4. INFLICT DAMAGE**  
- The lowest result is less than both the InSv and Sv characteristics of the target, so that attack inflicts damage. This reduces the model to which that attack was allocated to 0 wounds, which destroys it.
- The next lowest result is less than the target’s InSv characteristic, but greater than its Sv characteristic of 3+; that attack fails.
- The other result is greater than the target’s InSv characteristic of 5+; that attack also fails.

**1. HIT ROLLS**  
The controlling player then makes three hit rolls for the heavy bolter. The BS characteristic of the weapon is 4+. Two of the attacks hit the target.

**2. WOUND ROLLS**  
The controlling player makes two wound rolls. The weapon has an S characteristic of 5, so rolls of 3+ are required to wound. Both attacks wound the target.

**3. SAVE ROLLS**  
The target unit’s controlling player makes two save rolls.

**4. INFLICT DAMAGE**  
- The lowest result, when modified by the attacking weapon’s AP characteristic of -1, is less than the target’s Sv characteristic of 3+, so that attack inflicts damage. This reduces the model to which that attack was allocated to 0 wounds, which destroys it.
- The other result is equal to the target’s InSv characteristic of 5+; that attack fails.
## ATTACK SEQUENCE EXAMPLES 05
1. **SELECT WEAPONS**
The **RED** unit is attacking. The following weapons are selected to make attacks with: 
▪ 7 boltguns (B)
▪ 1 plasma pistol (PP)
▪ 2 heavy bolters (HB)

2. **SELECT TARGETS**
The **BLUE** unit is selected as the target. It is an attached unit (19) formed from a Seraphim unit and Saint Celestine (with her two Geminae Superia). The unit is visible to all models in the attacking unit, and all of the selected weapons are in range.

3. **RESOLVE ATTACKS**
There is only one enemy unit being targeted, so the controlling player now gathers attack dice. They decide to resolve the heavy bolter attacks first, which each have an A characteristic of 3, so six attack dice are gathered.
The attack dice for the remaining weapons will be gathered once the heavy bolter attacks are resolved (see opposite), as follows:
▪ 14 attack dice for the boltguns, which each have an A characteristic of 2.
▪ One attack dice for the plasma pistol, which has an A characteristic of 1.

X14
X6
X1
PP
B
B
B
B
B
B
B
HB
HB

ATTACKING ATTACHED UNITS
1. CREATE GROUPS AND DECLARE ORDER  
The target unit’s controlling player divides it into groups: one containing Saint Celestine, one containing the Geminae Superia, and one containing the Seraphim. They then declare the allocation order, choosing the Geminae Superia first (1), hoping their better Sv and InSv characteristics will weather the attacks. The Seraphim must be chosen second (2), as Saint Celestine is a CHARACTER model so must be last in the order (3).

2. RESOLVE ATTACK DICE  
The heavy bolters’ attacks wound the target five times, so the target unit’s controlling player makes five save rolls.  
The attacks are resolved one at a time, from lowest save rolls to highest:  

* The two results of 1 are allocated first, to the current allocation group (the Geminae Superia). They both inflict damage, and both Geminae Superia are destroyed.  
* The result of 3 is now allocated to the Seraphim, who have become the current allocation group. When modified by the attacking weapon’s AP characteristic of -1, this also inflicts damage, destroying one Seraphim model.  
* The remaining attacks fail, so no further damage is inflicted.

3. SELECT NEXT GROUP OF ATTACK DICE AND REPEAT

ALLOCATION GROUPS  
Save Rolls  
1  
1  
2  
2  
3  
2  
2  
2  
HB  
HB
## 06
This section contains some additional rules concepts that are most frequently used while making attacks.

</details>
