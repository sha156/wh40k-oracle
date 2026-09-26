import json
import sqlite3

import pytest

from db_compile.zh_weapons import HISTORY_FIELDS, _historical_names


@pytest.mark.parametrize("changed_field", [None, "unit_id", "name_en", "s", "keywords_json"])
def test_history_only_matches_identical_canonical_weapon(tmp_path, changed_field):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE weapons (" + ",".join(f + " TEXT" for f in HISTORY_FIELDS) + ")")
    guard = ["w1", "u1", "Gun", "24", "2", "3", "4", "-1", "1", "[]"]
    row = list(guard)
    if changed_field:
        row[HISTORY_FIELDS.index(changed_field)] = "changed"
    conn.execute("INSERT INTO weapons VALUES (" + ",".join("?" for _ in row) + ")", row)
    path = tmp_path / "history.json"
    path.write_text(json.dumps({"records": [{"guard": guard, "name_zh": "源武器名"}]}), encoding="utf-8")
    result = _historical_names(conn, path)
    assert result == ([] if changed_field else [(1, "源武器名")])
    assert list(conn.execute("SELECT * FROM weapons").fetchone()) == row
