import json

with open('cyber_insurance_standard_output.json', encoding='utf-8') as f:
    data = json.load(f)

bad_patterns = ['consulting', 'energy crisis', 'Category:', 'News And Views', 'Conclave', '$X', 'Y%', ' TBD ', '[PDF]', 'constitution', 'polity']
found = []
for s in data['result']['slides']:
    raw = json.dumps(s.get('raw', {}))
    for bp in bad_patterns:
        if bp.lower() in raw.lower():
            found.append(f'Slide {s["index"]} ({s["intent"]}): contains "{bp}"')
            break

if found:
    print('REMAINING ISSUES:')
    for f in found:
        print(f'  {f}')
else:
    print('ALL CRITICAL PATTERNS CLEARED')

topic_words = ['satellite', 'space', 'cyber', 'insurance', 'orbital', 'threat', 'risk', 'underwriting']
all_text = ' '.join(json.dumps(s.get('raw', {})) for s in data['result']['slides']).lower()
print('\nTopic keyword frequency:')
for tw in topic_words:
    count = all_text.count(tw)
    print(f'  "{tw}" mentioned {count} times')
