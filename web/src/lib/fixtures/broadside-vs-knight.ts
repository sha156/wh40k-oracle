import type { Exchange } from "../answer";

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
          kw: "[重型，毁灭伤害]",
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
          kw: "[双联]",
          range: '30"',
          a: "6",
          skill: "4+",
          s: "7",
          ap: "-1",
          d: "2",
        },
        {
          name: "寻觅者导弹",
          kw: "[一次性]",
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
