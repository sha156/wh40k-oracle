import json, re
d = json.load(open('_sm_dbdump.json', encoding='utf-8'))
def strip(t): return re.sub('<[^>]+>',' ',t or '').replace('  ',' ')
v = d['by_container']['Librarius Conclave']
for s in v['stratagems']:
    print(f"\n--STRAT {s['id']} {s['name_en']} (cp{s['cp']})--")
    print(strip(s['text'])[:600])
for e in v['enhancements']:
    print(f"\n--ENH {e['id']} {e['name']}--")
    print(strip(e['desc'])[:400])
