# tests/test_wiki_from_db.py
"""wiki_engine/from_db：从官方结构库渲染单位页（数值官方 / 中文黑图书馆 / USR 裸链）。"""
import json
import sqlite3

import pytest

from wiki_engine import from_db
from wiki_engine.crosslinks import escape_table_pipes


def _mkdb(tmp_path, *, with_zh=True, invuln="5", aircraft_m=False):
    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
        "points_json TEXT,keywords_json TEXT,version TEXT);"
        "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,"
        "invuln TEXT,w TEXT,ld TEXT,oc TEXT,base TEXT,count_options_json TEXT);"
        "CREATE TABLE weapons(id TEXT,unit_id TEXT,name_zh TEXT,name_en TEXT,"
        "range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);"
        "CREATE TABLE abilities(id TEXT,owner_id TEXT,scope TEXT,condition_json TEXT,"
        "name_zh TEXT,name_en TEXT,text_zh TEXT,effect_dsl_json TEXT,dsl_status TEXT);"
        "CREATE TABLE unit_zh_detail(canonical_id TEXT,name_zh TEXT,faction_zh TEXT,"
        "score TEXT,stats_json TEXT,abilities_json TEXT,weapons_json TEXT,"
        "intro_json TEXT,source TEXT);")
    conn.execute(
        "INSERT INTO units VALUES('1','ORK','Warboss',?,?,?,NULL)",
        ("战争头目" if with_zh else None,
         json.dumps({"points": 85, "items": [{"desc": "1 model", "cost": 85}],
                     "mfm": {"fetched_at": "2026-07-23"}}),
         json.dumps({"keywords": ["Infantry", "Character", "Warboss"],
                     "faction_keywords": ["Orks"]})))
    conn.execute(
        "INSERT INTO models VALUES('1','Warboss',?,'5','4+',?,'6','6+','1','40mm',NULL)",
        ("-" if aircraft_m else "6\"", invuln))
    # 两把武器：射击(A2 S4)与近战(A2 S4) 同侧写——必须靠射击/近战分组区分中文名
    conn.execute("INSERT INTO weapons VALUES('w1','1',NULL,'Twin slugga','12','2','5',"
                 "'4','0','1',?)", (json.dumps(["pistol, twin-linked"]),))
    conn.execute("INSERT INTO weapons VALUES('w2','1',NULL,'Attack squig','Melee','2',"
                 "'4','4','0','1',?)", (json.dumps(["extra attacks"]),))
    conn.execute("INSERT INTO abilities VALUES('a1','1','','', NULL,'Might is Right',"
                 "'Add 1 to the Hit roll.',NULL,NULL)")
    if with_zh:
        conn.execute(
            "INSERT INTO unit_zh_detail VALUES('1','战争头目','兽人','',?,?,?,?,'blackforum')",
            (json.dumps([{"unitName": "战争头目", "m": "20" if aircraft_m else "6",
                          "t": "5", "sv": "4", "w": "6", "ld": "6", "oc": "1"}]),
             json.dumps([{"name": "最大最强", "content": [{"type": "text", "content": [
                 {"text": "近战武器A+4", "style": ""}]}]}]),
             json.dumps({"射击武器": [{"name": "双联手铳", "skill": ["手枪", "双联"],
                                    "攻击次数": "2", "造伤": "4", "破甲": "0", "伤害": "1"}],
                         "近战武器": [{"name": "咬人跳跳", "skill": ["额外攻击"],
                                    "攻击次数": "2", "造伤": "4", "破甲": "0", "伤害": "1"}]}),
             json.dumps([{"content": [{"text": "阵营关键词"}]},
                         {"content": [{"text": "兽人"}]},
                         {"content": [{"text": "关键词"}]},
                         {"content": [{"text": "步兵"}, {"text": "人物"}]}])))
    conn.commit()
    conn.close()
    return db


class TestRenderUnit:
    def test_numbers_from_official_tables(self, tmp_path):
        db = _mkdb(tmp_path)
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        assert "| 战争头目 | 6\" | 5 | 4+ | 6 | 6+ | 1 |" in page.body
        assert "**1个模型** — 85 分" in page.body        # 官方 MFM 点数
        assert page.fm.id == "1" and page.fm.name_zh == "战争头目"

    def test_weapon_zh_name_by_profile_no_cross_group_collision(self, tmp_path):
        # 双联手铳(射击) 与 咬人跳跳(近战) 同 A2/S4/0/1，不得互相错标
        db = _mkdb(tmp_path)
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        shoot = [l for l in page.body.split("\n") if "12\"" in l][0]
        melee = [l for l in page.body.split("\n") if "近战 |" in l and "咬人跳跳" in l]
        assert "双联手铳" in shoot
        assert melee  # 近战行是咬人跳跳，没被射击的双联手铳污染

    def test_usr_wrapped_as_bare_wikilink(self, tmp_path):
        db = _mkdb(tmp_path)
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        assert "[[额外攻击]]" in page.body        # 近战武器技能裸链
        assert "[[步兵]]" in page.body and "[[人物]]" in page.body  # 关键词裸链

    def test_empty_invuln_hides_section(self, tmp_path):
        db = _mkdb(tmp_path, invuln="-")
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        assert "特殊保护" not in page.body

    def test_aircraft_empty_official_m_falls_back_to_zh(self, tmp_path):
        # 官方 M='-'（Wahapedia 抽取遗漏）→ 退回中文层 20
        db = _mkdb(tmp_path, aircraft_m=True)
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        stat_row = [l for l in page.body.split("\n")
                    if l.startswith("| 战争头目")][0]
        assert "20" in stat_row and " - " not in stat_row

    def test_english_fallback_when_no_zh_detail(self, tmp_path):
        db = _mkdb(tmp_path, with_zh=False)
        conn = sqlite3.connect(str(db))
        page, _ = from_db.render_unit(conn, "1", "欧克蛮人")
        conn.close()
        assert page.fm.name_zh is None
        assert "Might is Right" in page.body        # 官方英文技能兜底
        assert "Twin slugga" in page.body            # 官方英文武器名兜底


class TestEscapeTablePipes:
    def test_escapes_only_in_table_rows(self):
        body = ("| 武器 | 技能 |\n"
                "| 枪 | [[core-rules/rapid-fire.md|速射2]] |\n"
                "- **普通关键词**：[[core-rules/vehicle.md|载具]]")
        out = escape_table_pipes(body)
        assert "[[core-rules/rapid-fire.md\\|速射2]]" in out   # 表格行转义
        assert "[[core-rules/vehicle.md|载具]]" in out          # 列表行不转义

    def test_idempotent(self):
        body = "| x | [[a/b.md\\|c]] |"
        assert escape_table_pipes(body) == body


class TestGenHashesProtection:
    """gnhf 审查模块 6 F1：from_db 接入 H16 生成哈希登记表——人工编辑不被静默覆盖。"""

    def test_manual_edit_protected_fresh_page_overwritten(self, tmp_path):
        db = _mkdb(tmp_path)
        wiki = tmp_path / "wiki"
        from_db.generate_all(db, wiki)
        target = wiki / "factions" / "兽人" / "units" / "warboss.md"
        assert target.exists()
        gh = json.loads((wiki / ".gen_hashes.json").read_text(encoding="utf-8"))
        assert "factions/兽人/units/warboss.md" in gh  # 登记表已建

        # 人工编辑 → 重跑不覆盖 + conflicts 上报
        target.write_text(target.read_text(encoding="utf-8") + "\n人工批注\n",
                          encoding="utf-8")
        reps = from_db.generate_all(db, wiki)
        assert "人工批注" in target.read_text(encoding="utf-8")
        assert "factions/兽人/units/warboss.md" in reps[0]["conflicts"]

        # 负向成对：删除该页（等同还原）→ 重跑正常再生成，无冲突
        target.unlink()
        reps2 = from_db.generate_all(db, wiki)
        assert target.exists() and reps2[0]["conflicts"] == []
        assert "人工批注" not in target.read_text(encoding="utf-8")


class TestDataCorrectnessFixes:
    """gnhf 审查模块 6 F3-F6 数据正确性修复。"""

    def test_weapon_name_collision_falls_back_to_english(self, tmp_path):
        # F3：同侧两把不同武器侧写完全相同 → 中文名歧义 → 回退英文，不张冠李戴
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT);"
            "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,"
            "invuln TEXT,w TEXT,ld TEXT,oc TEXT,base TEXT,count_options_json TEXT);"
            "CREATE TABLE weapons(id TEXT,unit_id TEXT,name_zh TEXT,name_en TEXT,"
            "range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);"
            "CREATE TABLE abilities(id TEXT,owner_id TEXT,scope TEXT,condition_json TEXT,"
            "name_zh TEXT,name_en TEXT,text_zh TEXT,effect_dsl_json TEXT,dsl_status TEXT);"
            "CREATE TABLE unit_zh_detail(canonical_id TEXT,name_zh TEXT,faction_zh TEXT,"
            "score TEXT,stats_json TEXT,abilities_json TEXT,weapons_json TEXT,"
            "intro_json TEXT,source TEXT);")
        conn.execute("INSERT INTO units VALUES('1','AC','Custodian Wardens','守卫',"
                     "'{}',?,NULL)", (json.dumps({"keywords": []}),))
        conn.execute("INSERT INTO models VALUES('1','Warden','5\"','6','2+','4','3',"
                     "'6+','2','40mm',NULL)")
        # 两把射击武器同侧写 2/6/-1/2，官方英文名不同
        conn.execute("INSERT INTO weapons VALUES('w1','1',NULL,'Guardian spear','24',"
                     "'2','2','6','-1','2',NULL)")
        conn.execute("INSERT INTO weapons VALUES('w2','1',NULL,'Castellan axe','24',"
                     "'2','2','6','-1','2',NULL)")
        # 中文层两把同侧写但名字不同 → 歧义
        conn.execute("INSERT INTO unit_zh_detail VALUES('1','守卫','卡斯托迪斯','',"
                     "'[]','[]',?,'[]','blackforum')",
                     (json.dumps({"射击武器": [
                         {"name": "卫士之矛", "攻击次数": "2", "造伤": "6",
                          "破甲": "-1", "伤害": "2"},
                         {"name": "堡主战斧", "攻击次数": "2", "造伤": "6",
                          "破甲": "-1", "伤害": "2"}]}),))
        conn.commit()
        page, drift = from_db.render_unit(conn, "1", "卡斯托迪斯")
        conn.close()
        # 两把武器都回退官方英文名，绝不都套「堡主战斧」
        assert "Guardian spear" in page.body and "Castellan axe" in page.body
        assert "卫士之矛" not in page.body and "堡主战斧" not in page.body
        assert any(d.get("kind") == "weapon_name_collision" for d in drift)

    def test_model_desc_preserves_tier_context(self, tmp_path):
        from wiki_engine.from_db import _zh_model_desc
        assert _zh_model_desc("1 model") == "1个模型"
        assert _zh_model_desc("1 model (Assigned Agent)") == "1个模型 (Assigned Agent)"
        # F5：<ky> 标签剥除，档位语境保留
        assert _zh_model_desc("1 model (<ky>AGENTS OF THE IMPERIUM</ky> Detachment)") == \
            "1个模型 (AGENTS OF THE IMPERIUM Detachment)"

    def test_frontmatter_points_key_strips_ky_tags(self, tmp_path):
        db = _mkdb(tmp_path, with_zh=False)
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE units SET points_json=? WHERE id='1'",
                     (json.dumps({"points": 110, "items": [
                         {"desc": "1 model (<ky>Assigned</ky>)", "cost": 110}]}),))
        conn.commit()
        page, _ = from_db.render_unit(conn, "1", "兽人")
        conn.close()
        assert page.fm.points is not None
        assert all("<ky>" not in k for k in page.fm.points)

    def test_multiple_invuln_all_rendered(self, tmp_path):
        # F6：多模型不同豁免逐行渲染，不只渲第一个
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT);"
            "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,"
            "invuln TEXT,w TEXT,ld TEXT,oc TEXT,base TEXT,count_options_json TEXT);"
            "CREATE TABLE weapons(id TEXT,unit_id TEXT,name_zh TEXT,name_en TEXT,"
            "range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);"
            "CREATE TABLE abilities(id TEXT,owner_id TEXT,scope TEXT,condition_json TEXT,"
            "name_zh TEXT,name_en TEXT,text_zh TEXT,effect_dsl_json TEXT,dsl_status TEXT);"
            "CREATE TABLE unit_zh_detail(canonical_id TEXT,name_zh TEXT,faction_zh TEXT,"
            "score TEXT,stats_json TEXT,abilities_json TEXT,weapons_json TEXT,"
            "intro_json TEXT,source TEXT);")
        conn.execute("INSERT INTO units VALUES('1','ORK','Ghazghkull Thraka','加兹古尔',"
                     "'{}','{}',NULL)")
        conn.execute("INSERT INTO models VALUES('1','Ghazghkull Thraka','6\"','9','2+',"
                     "'4','12','6+','5','80mm',NULL)")
        conn.execute("INSERT INTO models VALUES('1','Makari','6\"','4','6+','2','4',"
                     "'6+','1','40mm',NULL)")
        conn.commit()
        page, _ = from_db.render_unit(conn, "1", "兽人")
        conn.close()
        # 两个不同豁免（4+ 和 2+）都出现，逐模型标注
        assert "4+" in page.body and "2+" in page.body
        assert "Ghazghkull Thraka：4+" in page.body and "Makari：2+" in page.body
