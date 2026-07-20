import json
d = json.load(open('_sm_dbdump.json', encoding='utf-8'))
for cont, v in d['by_container'].items():
    print(f"\n### {cont}")
    print("  STRATS:")
    for s in v['stratagems']:
        print(f"    {s['id']} | {s['cp']} | {s['name_en']}")
    print("  ENHANCEMENTS:")
    for e in v['enhancements']:
        print(f"    {e['id']} | {e['name']}")
# Also: does any detachment_row rule name match FP detachment rule names?
print("\n\n### detachment rule rows (name_en) for candidate FP detachments:")
wanted = ['Psychic Disciplines','Mastered Doctrines','Calculated Annihilation','Recalculating',
          'Storm-swift Onslaught','Wrath of the First Khan','Vulkan','Wrath of Dorn','Masters of Shadow',
          'Unparalleled Tactician','Interlocking Tactics','Rapid-drop Deployment','Oath of Reclamation',
          'Target Sighted','Adaptive Defence','Rapid Deployment']
for r in d['detachment_rows']:
    for w in wanted:
        if w.lower() in (r['name_en'] or '').lower():
            print(f"  {r['id']} | {r['name_en']}")
            break
