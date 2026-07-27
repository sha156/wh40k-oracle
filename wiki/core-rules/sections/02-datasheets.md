---
id: core-rules-02
name_zh: 核心规则第 2 章《数据表》
name_en: 'Core Rules 02: DATASHEETS'
aliases:
- 核心规则 02
type: core-rule
tags:
- core-rule
version:
  rules: 11版 Core Rules（BASIC RULES）
sources:
- book: Core Rules - New 40K Core Rules
  pages:
  - page_010.md
  - page_011
- book: 核心规则（GW 官方简体中文，11 版）
  pages:
  - page_010
  - page_011
updated: '2026-07-26'
---

11 版核心规则第 02 章《数据表》（DATASHEETS）全文，共 7 节，官方节号 02.01–02.07。

> 正文为 **GW 官方简体中文版**；每节可展开对照官方英文原文。中文由官方 PDF 文本层直提，表格与版式会有失真——**判定规则以英文原文为准**。

## 1.数据表名称 02.01

*DATASHEET NAME*

此处显示了单位的名称。

<details>
<summary>官方英文原文</summary>

Here you will find the name of the unit.

</details>

## 2.属性数据 02.02

*PROFILES*

这些数据描述了单位中模型的强度，具体如下：移动（M）：模型可以在战场上穿梭的速度。如果一个模型的 M 属性为 “-”，那么它可以被部署在战场上，但是不能被移动。

韧性（T）：模型抵御危害的能力。

豁免（Sv）：以掷骰结果的形式进行表示（例如 4+），这个属性代表了模型的护甲所提供的保护。

无敌豁免（InSv）：以掷骰结果的形式进行表示（例如 4+）。除了实际的护甲以外，一些模型拥有其他类型的额外保护，例如力场护盾或者超凡的反应力。并不是所有模型都拥有 InSv 属性，但拥有它们的模型会将这个属性列在此处。

耐伤（W）：耐伤代表了模型在被摧毁前可以承受的伤害数量。如果一个模型的耐伤属性被降至 0 或更低，那么那个模型被摧毁。

领导力（Ld）：以掷骰结果的形式进行表示（例如 7+），这代表了一个模型的勇气、决心或者自控能力。

目标控制（OC）：一个模型在控制战场目标方面的能力。如果一个模型的 OC 属性为“-”，那么它无法控制目标。

<details>
<summary>官方英文原文</summary>

These contain the following characteristics that tell you how mighty the models in the unit are:
- **Move (M)**: The speed at which a model traverses the battlefield. If a model has an M characteristic of ‘-’, it can be set up on the battlefield but otherwise cannot be moved.
- **Toughness (T)**: The model’s resilience against harm.
- **Save (Sv)**: Presented as a dice result (e.g. 4+), this indicates the protection a model’s armour gives it.
- **Invulnerable Save (InSv)**: Presented as a dice result (e.g. 4+). Some models are protected by esoteric means in addition to physical armour, such as force fields or preternatural reflexes. Not all models have an InSv characteristic, but if they do, it will be listed here.
- **Wounds (W)**: Wounds represent how much damage a model can sustain before it is destroyed. If a model’s wounds are reduced to 0 or fewer, that model is destroyed.
- **Leadership (Ld)**: Presented as a dice result (e.g. 7+), this reveals how courageous, determined or self‑controlled a model is.
- **Objective Control (OC)**: How effectively a model can control an objective on the battlefield. If a model has an OC characteristic of ‘-’ it is unable to control objectives at all.

</details>

## 3.技能 02.03

*ABILITIES*

许多单位都拥有在游戏期间会生效的技能。它们会被列在此处。

<details>
<summary>官方英文原文</summary>

Many units have abilities that may apply during the game. These will be described here.

</details>

## 4.武器 02.04

*WEAPONS*

武器拥有以下属性：范围（R）：武器的射程。R 属性为“近战”的武器属于近战武器。

攻击（A）：在每次使用武器时掷出的攻击骰数量。

射击技巧（BS）：以掷骰结果的形式进行表示（例如 4+），这个属性代表了武器使用者在使用对应的武器进行射击时的精准度。

械斗技巧（WS）：以掷骰结果的形式进行表示（例如 4+），这个属性代表了持有者在使用对应近战武器时的熟练程度。力量（S）：武器的 S 属性越高，就越容易击伤敌人。

护甲穿透（AP）：以掷骰结果的修正形式进行表示（例如 -1）。修正数值越高，武器就越容易击穿敌人的防御。

伤害（D）：一次攻击造成的伤害数量。

<details>
<summary>官方英文原文</summary>

Weapons have the following characteristics:
- **Range (R)**: How far ranged weapons can shoot. Weapons with an R characteristic of ‘Melee’ are melee weapons.
- **Attacks (A)**: How many attack dice are used each time that weapon is used.
- **Ballistic Skill (BS)**: Presented as a dice result (e.g. 4+), this shows how accurate the bearer is when shooting with the relevant ranged weapon.
- **Weapon Skill (WS)**: Presented as a dice result (e.g. 4+), this reflects the bearer’s skill in wielding the relevant melee weapon.
- **Strength (S)**: The higher a weapon’s S characteristic, the more likely it is to wound a foe.
- **Armour Penetration (AP)**: Presented as a modifier to a dice roll (e.g. -1). The larger the modifier, the better the weapon is at cutting through the target’s defences.
- **Damage (D)**: The amount of damage inflicted by an attack.

</details>

## 5.关键词 02.05

*KEYWORDS*

数据表上会列有一系列关键词，并且被分为阵营关键词与其他关键词。前者被用于决定可以被纳入军队中的模型，但除此之外两者功能相同。关键词会以关键词粗体一些规则会与一个或多个关键词产生关联。例如，一个规则会对步兵单位生效。这意味着这个规则只会对拥有步兵关键词的单位有效。同一个关键词的单数和复数表示拥有相同的功能。

<details>
<summary>官方英文原文</summary>

Datasheets have a list of keywords, separated into faction keywords and other keywords. The former are used when deciding which models to include in your army, but otherwise both are functionally the same. Keywords appear in full capitals, in KEYWORD BOLD.
## Boyz
### Characteristics
| | M | T | SV | W | LD | OC |
|---|---|---|---|---|---|---|
| BOYZ | 6" | 5 | 5+ | 1 | 7+ | 2 |
| BOSS NOB | 6" | 5 | 5+ | 2 | 7+ | 2 |

### Abilities
**Faction:** Waaagh!  
**Get da Good Bitz:** At the end of your Command phase, if this unit controls an objective, that objective is secured by your army.

### Unit Composition
▪ 1 Boss Nob  
▪ 9 Boyz

The Boss Nob is equipped with: 1 slugga; 1 kustom shoota; 1 big choppa  
Every Boy is equipped with: 1 slugga; 1 shoota; 1 choppa

Boyz charge forward in large, anarchic mobs led by hulking Boss Nobz. Laying down hails of inaccurate but enthusiastic dakka they dash toward the enemy before hurling themselves into close‑quarters combat, where their sheer muscle, ferocity and vicious choppas help them make short work of the foe.

### Ranged Weapons
| Weapon | Range | A | BS | S | AP | D |
|---|---|---|---|---|---|---|
| Kustom shoota [RAPID FIRE 2] | 18" | 4 | 5+ | 4 | 0 | 1 |
| Kombi‑rokkit | 24" | 1 | 5+ | 10 | -2 | 3 |
| Kombi‑shoota | 24" | 2 | 5+ | 4 | 0 | 1 |
| Shoota [RAPID FIRE 1] | 18" | 2 | 5+ | 4 | 0 | 1 |
| Slugga [CLOSE‑QUARTERS] | 12" | 1 | 5+ | 4 | 0 | 1 |

### Melee Weapons
| Weapon | Range | A | WS | S | AP | D |
|---|---|---|---|---|---|---|
| Big choppa | Melee | 3 | 3+ | 7 | -1 | 2 |
| Choppa | Melee | 3 | 3+ | 4 | -1 | 1 |

### Wargear Options
▪ The Boss Nob can have its 1 kustom shoota replaced with 1 kombi‑shoota and 1 kombi‑rokkit.

**Faction Keywords:** ORKS  
**Keywords:** INFANTRY; BATTLELINE; MOB; EXPLOSIVES; BOYZ
During a battle, you will move your models by picking them up and changing their position on the battlefield. The principles of movement are explained here.

## MOVING

</details>

## 6.单位构成 和其他规则 02.06

*6. UNIT COMPOSITION AND OTHER RULES*

这个部分会详细解释单位中模型的类型和数量。每一个模型都拥有一套默认的装备配置，并且也会列在此处。这个部分还可能列有其他规则，例如一个领袖单位可以加入的单位或者运输工具可以搭载的模型类型。

<details>
<summary>官方英文原文（英文由 PDF 直提）</summary>

This section details the number and 
types of models in the unit. Each of 
those models will have one set of default 
wargear, which will be listed here. It may 
also list other rules, such as which units 
a leader unit can join or which units can 
embark within a TRANSPORT.

</details>

## 7.武器装备选项 02.07

*7. WARGEAR OPTIONS*

一些数据表中会列有武器装备选项。在将这样的单位纳入您的军队时，您可以使用这些选项来调整单位中模型装备的武器和其他装备。

1蛮人小子M T SV W LD OC 6" 5 5+ 1 7+ 2 2 6" 5 5+ 2 7+ 2远程武器范围A BS S AP D特制射枪 [速射 2] 18" 4 5+ 4 0 1 4复合火箭发射器24" 1 5+ 10 -2 3复合射枪24" 2 5+ 4 0 1射枪 [速射 1] 18" 2 5+ 4 0 1短铳 [近距离] 12" 1 5+ 4 0 1近战武器范围A WS S AP D大砍刀近战3 3+ 7 -1 2砍刀近战3 3+ 4 -1 1武器装备选项7■强蛮人头目可以将其装备的特制射枪替换成 1 把复合射枪或者 1 把复合火箭发射器。阵营关键词：欧克蛮人关键词：步兵；战线；暴群；炸药；蛮人小子另请参见属性数据和武器

- 属性修正

- 被摧毁

- 随机属性技能

- 光环技能 22.01

- 阵营技能 22.02

- 灵能技能 22.03

- 武器装备技能 22.04关键词

- 单位中的混合关键词蛮人小子会组成庞大的混乱团体，在强蛮人头目的率领下出击。他们一边热情地使用手中的射枪胡乱射击，一边向前冲锋，最终与敌人展开肉搏，依靠自身的健壮身躯、凶残本性和锐利砍刀来轻松解决敌人。

技能阵营：Waaagh！

抢走好东西：在己方指挥阶段结束时，如果该单位控制了一个目标，那么那个目标被己方军队占领。

单位构成■1 个强蛮人头目

■9 个蛮人小子强蛮人头目装备有：1 把短铳；1 把特制射枪；1 把大砍刀每一个蛮人小子装备有：1 把短铳；1 把射枪；1 把砍刀移动额外规则后，那次移动结束。

03

12在一场战斗中，您会需要物理性的移动模型来调整它们在战场上的位置。关于移动的原则将在本章节中进行解释。

<details>
<summary>官方英文原文（英文由 PDF 直提）</summary>

Some datasheets have a list of wargear 
options. When you include such a unit in 
your army, you can use these options to 
alter the weapons and other wargear its 
models have.
1
BOYZ
M
T
SV
W
LD
OC
6"
5
5+
1
7+
2
2
6"
5
5+
2
7+
2
RANGED WEAPONS
RANGE
A
BS
S
AP
D
Kustom shoota [RAPID FIRE 2]
18"
4
5+
4
0
1
4
Kombi‑rokkit
24"
1
5+
10
‑2
3
Kombi‑shoota
24"
2
5+
4
0
1
Shoota [RAPID FIRE 1]
18"
2
5+
4
0
1
Slugga [CLOSE‑QUARTERS]
12"
1
5+
4
0
1
MELEE WEAPONS
RANGE
A
WS
S
AP
D
Big choppa
Melee
3
3+
7
‑1
2
Choppa
Melee
3
3+
4
‑1
1
WARGEAR OPTIONS
7
▪The Boss Nob can have its 1 kustom shoota replaced with 1 kombi‑shoota and 1 kombi‑rokkit.
FACTION KEYWORDS: 
ORKS
KEYWORDS: INFANTRY; BATTLELINE; MOB; EXPLOSIVES; BOYZ
SEE ALSO
PROFILES AND WEAPONS
►Characteristic Modifiers
►Destroyed
►Random Characteristics
ABILITIES
▪Aura Abilities 22.01
▪Faction Abilities 22.02
▪Psychic Abilities 22.03
▪Wargear Abilities 22.04
KEYWORDS
►Mixed Keywords in Units
Boyz charge forward in large, anarchic mobs led by hulking 
Boss Nobz. Laying down hails of inaccurate but enthusiastic 
dakka they dash toward the enemy before hurling 
themselves into close‑quarters combat, where their sheer 
muscle, ferocity and vicious choppas help them make short 
work of the foe.
ABILITIES
FACTION: Waaagh!
Get da Good Bitz: At the end of your Command phase, if 
this unit controls an objective, that objective is secured by 
your army.
UNIT COMPOSITION
▪1 Boss Nob
 
▪9 Boyz
The Boss Nob is equipped with: 1 slugga; 1 kustom shoota; 
1 big choppa
Every Boy is equipped with: 1 slugga; 1 shoota; 1 choppa
MOVING
If one or more of the above conditions are not met, that unit 
cannot make that move and its models are returned to their 
positions at the start of that move. Otherwise, after resolving 
any additional rules stated in the ‘After Moving’ section of that 
move type, that move ends.
03
++ WE WILL NOT SIMPLY ENDURE – WE WILL PREVAIL ++
12
During a battle, you will move your models by picking them up and changing 
their position on the battlefield. The principles of movement are explained here.

</details>