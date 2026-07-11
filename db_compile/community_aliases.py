"""community_aliases：社区俗名层——玩家口语叫法 → canonical 单位。

区别于 data_refined/blackforum（从数据源抽的规范译名），本层是**人工策划**的社区俗名：
同一单位民间有多种叫法（激素虫=刀虫=Hormagaunts、阿巴顿=大掠夺者阿巴顿）。QA 审计
暴露的「真单位因俗名没解析而答错」由此修复。

纪律：**只收人工核验过、指向唯一真单位的俗名**。宁缺毋滥——错误俗名会导致 confident 错答
（参见 ROADMAP「中文查表拒绝 fuzzy 匹配」教训）。英文=权威真值，俗名经 name_en 精确匹配落地。
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict

SOURCE = "community"

_CANONICAL_ID_RE = re.compile(r"^\d{9}$")

# 俗名 → 权威英文名（units.name_en 精确匹配，大小写不敏感）。逐条经 QA 审计核验。
# 特例：值为 9 位数字时按 canonical id 直取——用于库内 name_en 撞名的单位
# （name_en 桥会非确定性选行），此时必须点名唯一真单位。
NICKNAMES: Dict[str, str] = {
    "激素虫": "Hormagaunts",              # 刀虫的旧译/直译（hormone→激素）
    "阿巴顿": "Abaddon The Despoiler",     # 全名「大掠夺者阿巴顿」
    "马格努斯": "Magnus The Red",          # 全名「红魔马格努斯」
    "福格瑞姆": "Fulgrim",                 # 帝皇之子恶魔原体
    "卡巴利特战士": "Kabalite Warriors",   # 音译，规范译名「阴谋团战士」
    "战争老大": "Warboss",                 # 兽人俗名，库内规范名「战争头目」(#38)
    "惩罚者机甲": "Penitent Engines",      # 战斗修女，库内规范名「忏悔者机甲」；
                                           # 勿与「惩罚者坦克」Castigator 混淆 (#100)
    "兽人小子": "Boyz",                    # 兽人步兵俗名（兽人=Ork），库内规范名「小子」(#41)；
                                           # resolver 对「兽人小子」原会 ambiguous(兽霸小子/小子)
    # 武器 → 唯一携带单位桥：题目只给武器名、系统无按武器名查询能力时，把武器名指到
    # 携带它的唯一单位，get_datasheet 返回该单位属性块（含该武器）即可作答。
    # 「Ion blaster」全库仅 Hearthkyn Warriors(炉心战士) 携带；不加会被 fuzzy 错配到
    # 基因窃取者 Reductus Saboteur 的炸药包（confident 错答）(#83)。
    "离子爆破者": "Hearthkyn Warriors",
    # ── 2026-07-11 v3 基准审计补充（benchmarks/v3_edition11/README 四缺陷）──
    "混沌教徒": "000000946",               # Cultist Mob（CSM 本尊，gold #23 所指）。库内同名
                                           # 三行（000004050 混沌恶魔 / 000003849 混沌骑士
                                           # 「邪教徒」均为盟军副本）→ id 直取；原先无命中
                                           # 掉 RAG 错抓「诅咒教徒」Accursed Cultists (#23)
    "复仇者小队": "Dire Avengers",         # 灵族复仇者，库内规范名「狂暴复仇者」；resolver
                                           # 原只给警戒者/终结者/破坏者候选 (#48)
    "机械教游侠": "000000848",             # Skitarii Rangers（AdM 本尊，MFM 已同步行）。库内
                                           # 同名两行（000003842 系帝国骑士盟军副本），name_en
                                           # 桥会非确定性选行 → 直接点名 canonical id (#65)
    "死亡连无畏机兵": "Death Company Dreadnought",  # 「机兵」后缀口语形；原 ambiguous 降级
                                           # → RAG 被 FP 磁力勾爪变体抢答（T9≠基础型 T10）(#76)
}


def populate_community_aliases(db_path, mapping: Dict[str, str] = None) -> Dict[str, int]:
    """把社区俗名灌进 aliases 表（source='community'）。en 精确匹配 units.name_en。

    幂等：先删本源旧行再写。匹配不到诚实计数、不硬塞。返回 {total, matched, unmatched}。
    """
    mapping = mapping if mapping is not None else NICKNAMES
    conn = sqlite3.connect(str(db_path))
    try:
        en2id = {(n or "").strip().lower(): c
                 for c, n in conn.execute("SELECT id, name_en FROM units") if n}
        all_ids = {c for c, _n in conn.execute("SELECT id, name_en FROM units")}
        conn.execute("DELETE FROM aliases WHERE source = ?", (SOURCE,))
        matched = 0
        for nick, target in mapping.items():
            t = target.strip()
            if _CANONICAL_ID_RE.match(t):
                # canonical id 直取（撞名单位专用）；id 不存在按 unmatched 诚实计数
                cid = t if t in all_ids else None
            else:
                cid = en2id.get(t.lower())
            if not cid:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO aliases (alias, canonical_id, lang, source) "
                "VALUES (?, ?, 'zh', ?)", (nick, cid, SOURCE))
            matched += 1
        conn.commit()
        return {"total": len(mapping), "matched": matched,
                "unmatched": len(mapping) - matched}
    finally:
        conn.close()
