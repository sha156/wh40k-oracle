import sqlite3, json, pathlib
c = sqlite3.connect('db/wh40k.sqlite')
cur = c.cursor()

claimed = {}
for f in pathlib.Path('dsl_payloads').glob('*.json'):
    p = json.loads(f.read_text(encoding='utf-8'))
    if p.get('faction') != 'SM':
        continue
    for e in p['entries']:
        det = e.get('detachment')
        if det:
            claimed.setdefault(det, f.name)

print("=== SM stratagem containers: name | strat# | enh# | claim ===")
conts = [r[0] for r in cur.execute("SELECT DISTINCT detachment FROM stratagems WHERE faction='SM' ORDER BY detachment")]
for cont in conts:
    ns = cur.execute("SELECT COUNT(*) FROM stratagems WHERE faction='SM' AND detachment=?", (cont,)).fetchone()[0]
    ne = cur.execute("SELECT COUNT(*) FROM enhancements WHERE detachment_name=?", (cont,)).fetchone()[0]
    claim = claimed.get(cont)
    mark = f'CLAIMED({claim})' if claim else '*** FREE ***'
    print(f"  {cont:36.36} | s{ns} e{ne} | {mark}")

print("\n=== Enh-only containers (in enhancements not in stratagems) ===")
econts = [r[0] for r in cur.execute("SELECT DISTINCT detachment_name FROM enhancements WHERE faction_id='SM' ORDER BY detachment_name")]
for cont in econts:
    if cont not in conts:
        claim = claimed.get(cont)
        print(f"  {cont} | {'CLAIMED('+claim+')' if claim else 'FREE'}")
