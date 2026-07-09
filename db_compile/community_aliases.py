"""community_aliases：社区俗名层——玩家口语叫法 → canonical 单位。

区别于 data_refined/blackforum（从数据源抽的规范译名），本层是**人工策划**的社区俗名：
同一单位民间有多种叫法（激素虫=刀虫=Hormagaunts、阿巴顿=大掠夺者阿巴顿）。QA 审计
暴露的「真单位因俗名没解析而答错」由此修复。

纪律：**只收人工核验过、指向唯一真单位的俗名**。宁缺毋滥——错误俗名会导致 confident 错答
（参见 ROADMAP「中文查表拒绝 fuzzy 匹配」教训）。英文=权威真值，俗名经 name_en 精确匹配落地。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

SOURCE = "community"

# 俗名 → 权威英文名（units.name_en 精确匹配，大小写不敏感）。逐条经 QA 审计核验。
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
        conn.execute("DELETE FROM aliases WHERE source = ?", (SOURCE,))
        matched = 0
        for nick, en in mapping.items():
            cid = en2id.get(en.strip().lower())
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
