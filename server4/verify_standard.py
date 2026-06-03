import json

with open('cyber_insurance_standard_output.json', encoding='utf-8') as f:
    data = json.load(f)

print(f'Slides: {data["result"]["n_slides"]}')
print(f'Title: {data["result"]["deck_title"]}')
print(f'Duration: {data["result"]["duration_ms"]:.0f}ms')
print()

for s in data['result']['slides']:
    print(f'Slide {s["index"]} | {s["intent"]} | {s["headline"]}')
    if s.get('subheadline'):
        print(f'  Sub: {s["subheadline"]}')
    for b in (s.get('bullets') or [])[:3]:
        print(f'  • {b}')
    if s.get('stat_blocks'):
        for sb in s['stat_blocks']:
            print(f'  [{sb.get("value")}] {sb.get("label")}')
    print()
