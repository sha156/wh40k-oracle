import sqlite3, json
c = sqlite3.connect('db/wh40k.sqlite')
c.row_factory = sqlite3.Row
cur = c.cursor()

# 13 existing FP detachment containers
CONT = ["Librarius Conclave","Armoured Speartip","Headhunter Task Force","Ceramite Sentinels",
        "Blade of Ultramar","Hammer of Avernii","Spearpoint Task Force","Forgefather’s Seekers",
        "Emperor’s Shield","Shadowmark Talon","Bastion Task Force","Orbital Assault Force",
        "Reclamation Force"]

out = {}
# detachment rule rows for faction SM (all), to match by rule name later
out['detachment_rows'] = [dict(r) for r in cur.execute(
    "SELECT id, name_en, name_zh, rule_text FROM detachments WHERE faction='SM'")]

out['by_container'] = {}
for cont in CONT:
    strat = [dict(id=r['id'], name_en=r['name_en'], name_zh=r['name_zh'], cp=r['cp_cost'],
                  phase=r['phase'], text=r['text_zh'])
             for r in cur.execute("SELECT * FROM stratagems WHERE faction='SM' AND detachment=? ORDER BY id", (cont,))]
    enh = [dict(id=r['id'], name=r['name'], cost=r['cost'], legend=r['legend'], desc=r['description'])
           for r in cur.execute("SELECT * FROM enhancements WHERE detachment_name=? ORDER BY id", (cont,))]
    out['by_container'][cont] = {'stratagems': strat, 'enhancements': enh}

import io
with io.open('_sm_dbdump.json','w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("detachment_rows:", len(out['detachment_rows']))
for cont in CONT:
    d = out['by_container'][cont]
    print(f"  {cont:28.28} s{len(d['stratagems'])} e{len(d['enhancements'])}")
