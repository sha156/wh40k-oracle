import json, sqlite3
from pathlib import Path
OLD, NEW = "000010677006", "fp11e-spacemarines-bastion-s6"
# 1) 改 fp_rules_patches.json 里的 insert id
p = Path("db_compile/fp_rules_patches.json")
data = json.loads(p.read_text(encoding="utf-8"))
n = 0
for ins in data["inserts"]:
    if ins["values"].get("id") == OLD:
        ins["values"]["id"] = NEW
        n += 1
p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("patched inserts:", n)
# 2) 删除 DB 里以旧 id 落的行（改用 fp11e- 合成 id 重插）
con = sqlite3.connect("db/wh40k.sqlite")
cur = con.execute("DELETE FROM stratagems WHERE id=?", (OLD,))
con.commit()
print("deleted stray DB rows:", cur.rowcount)
con.close()
