# Faction Pack 兵牌级勘误清单（11 版官方 Rules Updates → 结构库落账工作单）

> 2026-07-11 提取。来源：29 个 Faction Pack（first iteration，2026-06-20 生效）的
> "Rules Updates" 章节，`data_refined/Faction Pack */` 精炼文本 + 原 PDF 回读。
> 结论先行：**兵牌级勘误共涉及 26 个阵营、约 395 个（阵营×单位）条目，全部 395 个都在
> 我们的结构库里**——即今天问到这些单位的被改条目，会按十版值/十版文本作答。这是 S4
> 的落账清单。逐条原文以各包 Rules Updates 为准（本文标注包内页码）。

## 0. 覆盖与缺口

- 29 包中 **26 包有兵牌级勘误**；Chaos Daemons 只有 FAQ；Adeptus Titanicus（新阵营）与
  Deathwatch（并入 SM 包管理）无 Rules Updates 章节。
- 对账：395/395 条目在 `db/wh40k.sqlite` datasheets 表中（"Ûthar the Destined" 带变音符、
  "Wartrakks" 库内为复数，属拼写变体非缺失）。
- 精炼缓存有 5 处截断，落库时必须回读原 PDF：
  Orks Battlewagon 运输段/Gretchin 条目（Orks 包 p23-24）、Tau Stealth Battlesuits
  Forward Observers/SM Inceptor Meteoric Descent（各自更新页尾）、AdMech Conqueror
  Imperative 尾部（AdMech 包 p17）。
- 中文名桥：**黑图书馆是中文名权威源**（aliases 表 blackforum 921 条已入库），落账时按
  canonical_id 自动带出中文名；黑图书馆的**数值面是十版，不可作 11 版数值源**。

## 1. 横向模板化变更（占条目大头，逐类落一次规则即可批量清账）

1. **FRAME 关键词批量新增**（11 版新测距关键词，24 版核心 17.02）：载具/无底盘模型
   全线补 FRAME。涉及：AM 29 车、SM 24 车、GK 8、Tau 9、Necrons 10、Orks 8、
   CSM/DG/TS/WE/EC 各自的 Chaos 载具、Sororitas 4、DA 3、Drukhari 5、
   Custodes 4、GSC 2、IA 4、LoV 2、BT 7、BA 1（Baal Predator）。
2. **飞机（AIRCRAFT）机制重做潮**，三种形态：
   - 保留飞机身份：Profile 的 M 与 OC 改 "-"（Stormtalon/Stormhawk、Doom Scythe、
     Ork 四种轰炸机、Razorwing/Voidraven、Nephilim/Dark Talon、Crimson Hunter/
     Hemlock、Harpy/Hive Crone 等），并普遍 **Core Abilities 删 'Hover'**（悬浮已改核心
     技能 24.17，飞机不再自带）。
   - **降格为普通飞行载具（删 AIRCRAFT 关键词）**：Heldrake（五个混沌阵营同步，
     M 改 12"、OC '-'，EC 版另加 Sv 3+）、Stormraven（M 改 14"）、Night Scythe
     （M 14" + 加 Hover + 加 Deep Strike）、Corvus Blackstar（M 14"）。
   - 这类改动直接影响模拟器/army 合法性（飞机必须进战略预备队 23.01）。
3. **传送/入场距离 9"→8" 批量订正**：Terminator/Deathwing Teleport Homer、
   Acolyte Iconward/Reductus Saboteur/Weirdboy Da Jump/Ophydian/Transcendent
   C'tan/Sporocyst/Callidus 等（与 11 版核心 8" 口径对齐）。
4. **Leader→Support 批量改造**（对应 11 版新核心技能 SUPPORT 24.34）：
   Sororitas 四辅助人物、Warlock、Cybernetica Datasmith、Master of Executions、
   GSC 四辅助人物、Necrons 六 Cryptek、Ministorum Priest、Sanguinary Priest、
   BT Castellan/Crusade Ancient、SM 九个（Ancient/Apothecary/Lieutenant 系）。
   例外反向：GK Brotherhood Chaplain **加** Leader。
5. **反应移动统一模板**："对手移动阶段敌单位在 8" 内结束移动→本单位可标准移动
   D6"/6""（Dominion Squad、Serberys Raiders、Rangers、Hellions、Death Riders、
   Fenrisian Wolves、Termagants、Goremongers、Kelermorph、Sanctus 等十余条）。
6. **surge move 模板**（11 版新移动类型 21.02）："对手射击阶段挨打后涌动 D6/D6+2""
   （Crusader Squad、Death Company Dreadnought、Accursed Cultists、Hybrid
   Metamorphs、Khorne Berzerkers、Carnifexes、Wulfen Dreadnought、Buri 等）。
7. **计谋交互模板**：英雄干预"额外可用且 -1CP"（Daemonifuge、Beastboss on
   Squigosaur、Maulerfiend、Von Ryan's Leapers、Brotherhood Techmarine 等）；
   "对手对 12" 内己方单位用计谋则 +1CP"（Cypher、Lady Malys、Swarmlord、Logan
   Grimnar、Uriel Ventris、Callidus）；"己方计谋 -1CP"（Nexos、Will of the Hive
   Mind、Supreme Strategist、Memnyr、Sekhetar）。

## 2. ⚠️ 数值向勘误（属性/武器表改值——问答最易答错旧值的一批）

| 阵营 | 单位 | 改动 |
|---|---|---|
| Custodes | Shield-Captain on Dawneagle Jetbike | T7 W8；salvo launcher 加[TWIN-LINKED] S10 AP-3 D D6+1；hurricane bolter AP-1 D2 |
| Custodes | Vertus Praetors | T7 W5；武器同上 |
| AdMech | Onager Dunecrawler | 四种主炮 A/S/D 全改 + 新增 Scuttling Walker 技能 |
| AdMech | Ironstrider Ballistarii | twin cognis autocannon A4；lascannon A2 |
| AdMech | Sicarian Infiltrators/Ruststalkers | 近战武器 A/S/AP 多处改 |
| AdMech | Skorpius Disintegrator | ferrumite cannon D 改 D6+1 |
| AM | Kasrkin/Catachan/Krieg 指挥班 | 武器表增删（等离子手枪/爆弹枪 profile 新增等） |
| AM | Tempestus Scions/Aquilons | 手枪类 BS 改 3+ |
| BA | Sanguinary Guard | encarmine blade WS2+；spear A4 WS2+；装备选项重写 |
| CSM | Lord Discordant on Helstalker | M14"、InSv 4+、chainglaive 全 profile 改、两技能重写 |
| CSM | Vashtorr the Arkifane | 锤子双 profile 改 + 三技能重写 |
| CSM | Chaos Predator Destructor | armoured tracks WS4+ |
| DG | Chaos Predator Destructor | predator autocannon S9 |
| DA | Deathwing Knights | mace of absolution/power weapon 全 profile 改 |
| DA | Inner Circle Companions | Calibanite greatsword 双 profile 改 |
| DA | Land Speeder Vengeance | plasma storm battery 双 profile 改 |
| DA | Lion El'Jonson | Fealty 双 profile 改 + 四技能重写 |
| DA | Ravenwing Black Knights/Command Squad | 近战武器加[DEVASTATING WOUNDS] |
| EC | Flawless Blades | blissblade A4 |
| EC | Infractors/Tormentors | power sword S5 |
| GSC | Acolyte Hybrids(手火焰)/Rockgrinder/Truck/Reductus | 爆破装药射程改 8" |
| IK | 全骑士底盘 | **OC 改 10**；Damaged 段统一重写（1-9/1-10 血 OC-5 且命中-1） |
| Necrons | Plasmancer | Living Lightning 重做（4D6 每 4+ 1 致命伤） |
| Orks | Warboss/Mega Armour/Zodgrod | Waaagh! 加成数值改（+4A/D3/+6"M） |
| SM | Captain in Gravis/Heavy Intercessor | heavy bolt rifle/bolter 全 profile 改（30" A2 [ASSAULT,HEAVY]…） |
| SM | Infernus Squad | pyreblaster 12" S5 AP-1 |
| SM | Lieutenant in Reiver/Combat Knife 系 | AP 改 -1（Scout/Reiver/Incursor 的刀类同步） |
| SM | Repulsor / Repulsor Executioner | 运力改 14 / 7 + 占位规则重写 |
| Tau | Riptide Battlesuit | ion accelerator 双 profile 改（72" A6 …）+ Nova Charge 重做 |
| TS | Kairos Fateweaver / Lord of Change | Infernal Gateway/Bolt of Change/rod 全 profile 改 |
| TS | Chaos Vindicator M9"；Flamers/Screamers Ld7+ | profile 改 |
| Tyranids | Exocrine | bio-plasmic cannon S9 |
| Tyranids | Tyrannofex | rupture cannon D 改 **D6+6** |
| Tyranids | Psychophage | M12"、talons and betentacled maw A6 AP-2、加 SMOKE |
| WE | Slaughterbound | lacerator/daemonic claw S10 |
| LoV | Hekaton/Sagitaur | 运力与限制重写 |
| 运输类 | Falcon/Wave Serpent/Venom/Chaos Rhino/Chaos Land Raider/Battlewagon/Stompa/Impulsor/Imperial Rhino/Hekaton | 运力数字与可载关键词全部重写 |

（技能文本重写类条目未列入本表——数量更大但多为措辞/机制重组，见各包原文；
落账时与本表同批处理。）

## 3. 包内新数据表（不在库，S4 增量源）

对 29 包全部 463 张重印数据表扫描，与 db 对账后**不在库的仅 6 项**：
Orks 的 Bannernob / Big Mek Dakkarig / Bigboss / Wartrakk（11 版新单位，与
"7 个 MFM-only 单位"名单对应）、SM 的 Eradicator Squad with Heavy Bolters（变体）、
另 1 项为解析误报（"Warhammer Legends" 标题）。其余重印表（GK Dreadnought、
Raven Strike Fighter、Orca Dropship、Canis Wolfborn、Dimachaeron、Repressor、
Secutarii、X-101、Giant Chaos Spawn 等 FW/回归单位）**库里已有同名行（十版值）**，
落账时以包内 11 版重印表整行覆盖——注意 base/variant 撞名陷阱（用 canonical id 直取，
见 PR #12 机制）。

## 4. 落账方案（S4 增量，建议顺序）

1. **db_compile 增加 fp_errata 层**：以本清单为工作单，逐包把 Rules Updates 的
   Datasheets 段解析成 patch 记录（unit canonical_id + 字段 + 新值 + 出处页码），
   落 `wh40k.sqlite` 时按 层级 wahapedia(十版基底) < fp_errata(11版补丁) 覆盖；
   中文名经 aliases（blackforum 优先）自动带出。
2. **重印表整行覆盖**：包内 463 张数据表可解析成完整行，凡与库内同 id 的直接以
   11 版重印为准（比逐字段 patch 更稳），6 个新单位插入新行。
3. **wiki 兵牌页**（现仅钛帝国 63 + 吞世者 7）：Tau 的 9 车 FRAME、Crisis Sunforge/
   Ethereal/Firesight/Pathfinder/Riptide/Stealth/Kroot Trail Shaper 条目直接改页；
   吞世者对照 WE 段（Heldrake/Chaos Rhino/Berzerkers/Eightbound/Jakhals 等 14 条）。
4. 完成后重跑基准 v3（重点回归 #76 类 FP 变体题）+ wiki lint。
5. 官方 first iteration 之后的更新会在包内**标红**——建立"重抓 Faction Pack → diff
   标红段"的巡检位（与 MFM --check 同节奏）。

## 5. 黑图书馆定位（本次裁决）

- **角色 = 中文名权威桥**：1167 个 40K 单位中英对照，已入 aliases（blackforum 源
  921 条）；勘误落账、wiki 建页、新单位命名一律经它取中文名。
- **不做数值源**：其 datasheet 面是十版（gameId=2），11 版数值以 Faction Pack
  重印表/勘误为唯一真源；两者冲突时以 FP 为准。
- 新增 4 个 Orks 新单位黑图书馆可能还没有中文名——届时中文名标"（暂无社区译名）"
  并进 review_needed，勿自造译名。
