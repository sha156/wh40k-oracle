# tests/test_db_compile_aliases.py
"""aliases：从 data_refined 双语标题提取 (中文→canonical_id)，灌进 aliases 表。"""
import sqlite3

from db_compile.aliases import (
    harvest_bilingual_pairs,
    load_alias_expansions,
    populate_aliases,
)


def _make_refined(tmp_path):
    d = tmp_path / "data_refined" / "泰伦虫族10版中文"
    d.mkdir(parents=True)
    (d / "page_1.md").write_text(
        "## 刀虫 HORMAGAUNTS\n正文...\n## 泰伦武士 TYRANID WARRIORS\n正文...\n"
        "## ENHANCEMENTS\n纯英文标题应跳过\n",
        encoding="utf-8")
    # 英文 Faction Pack（纯英文标题）不产出中文对
    d2 = tmp_path / "data_refined" / "Faction Pack Tyranids"
    d2.mkdir(parents=True)
    (d2 / "page_1.md").write_text("## Hormagaunts\n英文页\n", encoding="utf-8")
    return tmp_path / "data_refined"


def _make_db(tmp_path):
    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
        "points_json TEXT,keywords_json TEXT,version TEXT);"
        "CREATE TABLE aliases(alias TEXT NOT NULL,canonical_id TEXT NOT NULL,"
        "lang TEXT NOT NULL,source TEXT NOT NULL,PRIMARY KEY(alias,lang,source));"
    )
    conn.execute("INSERT INTO units VALUES('000000070','TYR','Hormagaunts',NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO units VALUES('000000071','TYR','Tyranid Warriors',NULL,NULL,NULL,NULL)")
    conn.commit()
    conn.close()
    return db


class TestHarvest:
    def test_extracts_only_chinese_bearing_headings(self, tmp_path):
        pairs = harvest_bilingual_pairs(_make_refined(tmp_path))
        assert ("刀虫", "HORMAGAUNTS") in pairs
        assert ("泰伦武士", "TYRANID WARRIORS") in pairs
        # 纯英文标题（ENHANCEMENTS / Hormagaunts）不产出
        assert all(any("一" <= ch <= "鿿" for ch in zh) for zh, _ in pairs)
        assert len(pairs) == 2


class TestPopulate:
    def test_maps_zh_to_canonical_id_via_english(self, tmp_path):
        db = _make_db(tmp_path)
        refined = _make_refined(tmp_path)
        report = populate_aliases(db, refined)

        assert report["matched"] == 2
        conn = sqlite3.connect(str(db))
        rows = dict(conn.execute(
            "SELECT alias, canonical_id FROM aliases WHERE source='data_refined'").fetchall())
        conn.close()
        assert rows["刀虫"] == "000000070"
        assert rows["泰伦武士"] == "000000071"

    def test_idempotent_rerun_does_not_duplicate(self, tmp_path):
        db = _make_db(tmp_path)
        refined = _make_refined(tmp_path)
        populate_aliases(db, refined)
        populate_aliases(db, refined)  # 二次
        conn = sqlite3.connect(str(db))
        n = conn.execute("SELECT COUNT(*) FROM aliases WHERE source='data_refined'").fetchone()[0]
        conn.close()
        assert n == 2

    def test_unmatched_english_reported_not_written(self, tmp_path):
        # data_refined 有对，但 en 在 units 里查无 → 不写、诚实计数
        db = _make_db(tmp_path)
        d = tmp_path / "data_refined" / "书"
        d.mkdir(parents=True)
        (d / "p.md").write_text("## 幽灵骑士 WRAITHKNIGHT\n", encoding="utf-8")
        report = populate_aliases(db, tmp_path / "data_refined")
        assert report["harvested"] >= 1
        assert report["matched"] == 0


class TestLoadAliasExpansions:
    """classic 查询扩展用的 {别名 → 库内规范名 英文名} 映射。"""

    def _db_with_aliases(self, tmp_path):
        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        # 给单位补中文名
        conn.execute("UPDATE units SET name_zh='刀虫' WHERE id='000000070'")
        conn.executemany(
            "INSERT INTO aliases(alias,canonical_id,lang,source) VALUES(?,?,?,?)",
            [
                ("激素虫", "000000070", "zh", "community"),   # 别名≠规范名，有用
                ("刀虫", "000000070", "zh", "blackforum"),     # 自指，应跳过
                ("小子", "000000071", "zh", "community"),      # 2 字，应按长度过滤
                ("HORMAGAUNTS", "000000070", "en", "x"),       # 英文别名不进 zh 扩展
            ],
        )
        conn.commit()
        conn.close()
        return db

    def test_maps_alias_to_canonical_names(self, tmp_path):
        exp = load_alias_expansions(self._db_with_aliases(tmp_path))
        assert exp["激素虫"] == "刀虫 Hormagaunts"

    def test_skips_self_referential_and_short_and_en(self, tmp_path):
        exp = load_alias_expansions(self._db_with_aliases(tmp_path))
        assert "刀虫" not in exp    # 自指（== name_zh）跳过
        assert "小子" not in exp    # 长度 < 3 跳过
        assert "HORMAGAUNTS" not in exp  # 非 zh

    def test_missing_db_returns_empty(self, tmp_path):
        assert load_alias_expansions(tmp_path / "nope.sqlite") == {}
