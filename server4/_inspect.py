import json
d=json.load(open('test_v4_live_local_raw.json',encoding='utf-8'))
print('STATUS PER DECK:')
for r in d:
    print(f"  {r['id']:<6} {r['status']:<5} elapsed={r.get('elapsed_s')}s slides={r.get('slide_count',0)} layouts={r.get('layouts')}")
print()
print('IMAGE COVERAGE:')
for r in d:
    if r.get('status')=='PASS':
        n=sum(1 for s in r.get('slides',[]) if s.get('image_url'))
        print(f"  {r['id']}: {n}/{len(r.get('slides',[]))} slides have image_url")
