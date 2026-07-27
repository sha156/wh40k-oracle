import type { Exchange, KeywordRef } from "../answer";

/**
 * 首屏样例用到的四个武器词条。字段与 `brief` 正文**逐字取自后端 keyword_refs 的真实
 * 输出**（真源：wiki/indexes/keywords.json + wiki/core-rules/sections/24-core-abilities.md，
 * GW 官方简体中文），不是手写的解释——首屏是给人看规则的，编一句像样的话就是造数。
 *
 * 两处与线上不同、都是有意的：
 * · 原稿写「一次性」，官方 11 版中文是**单发**（ONE SHOT 24.26）。fixture 跟官方走。
 * · TWIN‑LINKED 只取 24.38 本节的两段。线上那一节的中文正文尾部粘进了后面「电子支持」
 *   附录的整段文字（官方中文 PDF 切节的已知缺陷，第 24 章最后一节没有下界），
 *   fixture 不复制那段污染——它不属于这一节。
 */
const KW: Record<string, KeywordRef> = {
  heavy: {
    text: "重型",
    slug: "heavy",
    base: "HEAVY",
    nameZh: "重型",
    section: "24.16",
    ruleSlug: "24-core-abilities",
    group: "universal",
    brief:
      "重型武器是战场上最为庞大的枪炮，但是需要进行稳定才能达到最高效率。\n" +
      "在己方射击阶段中，每次使用[重型]武器进行攻击时，如果攻击单位满足以下所有条件，那么命中掷骰的结果增加 1 点：\n" +
      "那个单位不处于交战状态。\n那个单位不是在本回合中被部署至战场的。\n" +
      '在本回合中，那个单位中没有模型移动超过 3"。',
  },
  devastatingWounds: {
    text: "毁灭伤害",
    slug: "devastating-wounds",
    base: "DEVASTATING WOUNDS",
    nameZh: "毁灭伤害",
    section: "24.10",
    ruleSlug: "24-core-abilities",
    group: "universal",
    brief:
      "最为强大的武器能够轻松击穿装甲并击杀多个敌人。\n" +
      "每次使用一件[毁灭伤害]武器进行攻击时，如果攻击造成了暴击致伤，那么那次攻击流程结束，" +
      "目标单位受到相当于那件武器 D 属性数量的致命伤。这些伤害将在武器攻击造成的普通伤害之后进行结算。\n" +
      "[毁灭伤害]武器每一次通过暴击致伤所造成的致命伤最多只能对一个模型造成伤害；那一次攻击造成的任何剩余的致命伤将被舍弃。",
  },
  twinLinked: {
    text: "双联",
    slug: "twin-linked",
    base: "TWIN-LINKED",
    nameZh: "双联",
    section: "24.38",
    ruleSlug: "24-core-abilities",
    group: "universal",
    brief:
      "两把相同的武器通常会被连接在同一个瞄准系统上来增加它们的致命性。\n" +
      "每次使用[双联]武器进行攻击时，您可以重掷致伤掷骰。",
  },
  oneShot: {
    text: "单发",
    slug: "one-shot",
    base: "ONE SHOT",
    nameZh: "单发",
    section: "24.26",
    ruleSlug: "24-core-abilities",
    group: "universal",
    brief:
      "一些武器十分稀少、复杂或装填缓慢，在战斗中只能使用一次。\n" +
      "每一件拥有本技能的武器在战斗中只能被选择进行攻击一次。\n" +
      "如果一个被摧毁的模型被返还至单位中，其拥有的所有在战斗中已经被选择进行过攻击的[单发]武器不能再次被选择用于攻击。",
  },
};

/**
 * 永久回归样例：炮击战斗服 vs 帝国骑士（含 simulate_combat 降级的诚实轨迹）。
 * 与设计定稿 v2-warhammer.html 内容逐字一致——改动此 fixture 前先对照原稿。
 */
export const broadsideVsKnight: Exchange = {
  question: "炮击战斗服的重型磁轨枪打帝国骑士能打掉多少血？值得带吗？",
  context: "当前语境：钛帝国 T'AU EMPIRE",
  answer: {
    summary: "检索 4 步 · 引用 3 条 · 期望值粗算",
    traceWarn: "⚠ simulate_combat 降级",
    trace: [
      {
        fn: "entity_resolver",
        args: '("炮击战斗服")',
        result: "broadside-battlesuits (000000433)",
        status: "ok",
      },
      {
        fn: "get_entity",
        args: '("broadside-battlesuits")',
        result: "属性/武器/技能",
        status: "ok",
      },
      {
        fn: "get_keyword_definition",
        args: '("毁灭伤害")',
        status: "ok",
      },
      {
        fn: "simulate_combat",
        args: "(...)",
        status: "degraded",
        note: "未建模（P4 建设中），降级为期望值粗算",
      },
    ],
    verdict: {
      label: "值得带",
      labelEn: "Sanctioned",
      lede: [
        { t: "text", s: "单台炮击战斗服（未移动、重型磁轨枪 2 发）对帝国骑士每轮期望约 " },
        { t: "num", s: "2.3" },
        { t: "text", s: " 伤，其中约 " },
        { t: "num", s: "1.0" },
        { t: "text", s: " 来自[毁灭伤害]致命伤；满编 3 台一轮约 " },
        { t: "num", s: "7" },
        { t: "text", s: " 伤，约 " },
        { t: "num", s: "3" },
        { t: "text", s: " 轮打掉一台满血骑士（22W）。" },
        { t: "strong", s: "值得带" },
        { t: "text", s: "：80 分/台的 S12 AP-4 D6+1，是钛帝国点数效率最高的反坦克平台之一。" },
      ],
    },
    calc: [
      {
        n: 1,
        text: [
          { t: "kw", s: "[重型]" },
          { t: "text", s: "：未移动 +1 命中 → " },
          { t: "num", s: "3+" },
          { t: "text", s: " 命中（" },
          { t: "num", s: "67%" },
          { t: "text", s: "）" },
          { t: "cite", n: 2 },
        ],
      },
      {
        n: 2,
        text: [
          { t: "text", s: "S12 对 T12 → " },
          { t: "num", s: "4+" },
          { t: "text", s: " 穿防（" },
          { t: "num", s: "50%" },
          { t: "text", s: "）" },
        ],
      },
      {
        n: 3,
        text: [
          { t: "text", s: "AP-4 击穿 3+ 甲，骑士只能用 " },
          { t: "num", s: "5++" },
          { t: "text", s: " 无效保护 → 失防 " },
          { t: "num", s: "67%" },
        ],
      },
      {
        n: 4,
        text: [
          { t: "text", s: "穿防骰 6 触发" },
          { t: "kw", s: "[毁灭伤害]" },
          { t: "text", s: " → 直接致命伤，无视任何保护" },
          { t: "cite", n: 3 },
        ],
      },
      {
        n: 5,
        text: [
          { t: "text", s: "D6+1 平均 " },
          { t: "num", s: "4.5" },
          { t: "text", s: " 伤/发；另有寻觅者导弹（一次性，S14 AP-3）可补一发" },
        ],
      },
    ],
    entityCard: {
      nameZh: "炮击战斗服小队",
      nameEn: "Broadside Battlesuits",
      pts: "80 / 170 / 270",
      stats: [
        { lab: "M", val: '5"' },
        { lab: "T", val: "6" },
        { lab: "SV", val: "2+" },
        { lab: "W", val: "8" },
        { lab: "LD", val: "7+" },
        { lab: "OC", val: "2" },
      ],
      ranged: [
        {
          name: "重型磁轨枪",
          kw: [KW.heavy, KW.devastatingWounds],
          range: '60"',
          a: "2",
          skill: "4+",
          s: "12",
          ap: "-4",
          d: "D6+1",
          hot: true,
        },
        {
          name: "集束导弹仓",
          kw: [KW.twinLinked],
          range: '30"',
          a: "6",
          skill: "4+",
          s: "7",
          ap: "-1",
          d: "2",
        },
        {
          name: "寻觅者导弹",
          kw: [KW.oneShot],
          range: '48"',
          a: "1",
          skill: "4+",
          s: "14",
          ap: "-3",
          d: "D6+1",
        },
      ],
      melee: [
        {
          name: "粉碎冲撞",
          range: "近战",
          a: "3",
          skill: "5+",
          s: "6",
          ap: "0",
          d: "1",
        },
      ],
      abilities: [
        { tag: "Faction:", name: "为了上上善道" },
        { name: "先进装甲", text: "对抗致命伤 4+ 不知疼痛。" },
      ],
      composition: [
        [
          { t: "num", s: "1" },
          { t: "text", s: " 个炮击夏司'瓦（" },
          { t: "num", s: "80/170/270" },
          { t: "text", s: " 分）" },
        ],
        [
          { t: "num", s: "0–2" },
          { t: "text", s: " 个炮击夏司'钨" },
        ],
      ],
      keywords: "载具，机甲，战斗服，炮击",
      faction: "阵营: 钛帝国",
      src: "src: 《钛帝国十版CODEX-20251112》 p.44",
      wiki: "wiki: factions/钛帝国/units/broadside-battlesuits",
    },
    cites: [
      {
        n: 1,
        book: "《钛帝国十版CODEX-20251112》",
        page: 44,
        wiki: "factions/钛帝国/units/broadside-battlesuits",
      },
      {
        n: 2,
        book: "《战锤40K总规则10版》",
        section: "武器技能",
        term: "重型",
        wiki: "core-rules/heavy",
      },
      {
        n: 3,
        book: "《战锤40K总规则10版》",
        section: "武器技能",
        term: "毁灭伤害",
        wiki: "core-rules/devastating-wounds",
      },
    ],
    sensitivity: {
      title: "◭ 敏感性 · 标记加成",
      text: [
        { t: "text", s: "若有观察员提供[标记]（为了上上善道），命中提升至 " },
        { t: "num", s: "2+" },
        { t: "text", s: "，期望伤害 " },
        { t: "num", s: "×1.25" },
        { t: "text", s: " → 满编约 " },
        { t: "num", s: "8.8" },
        { t: "text", s: " 伤/轮。" },
      ],
    },
    cta: {
      kind: "simulator",
      ready: false,
      label: "⚔ 在模拟器中打开此对局",
      mini: "P4 建设中 · 当前为期望值粗算",
    },
    followups: [
      "换集束导弹仓打步兵效率？",
      "对比铁手将军 vs 炮击",
      "满编三台的点数曲线",
    ],
    degraded: true,
  },
};
