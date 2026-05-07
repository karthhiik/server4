"""Quick test: verify generate doesn't block the server."""
import requests
import time

BASE = "http://127.0.0.1:8003"

# 1. Health before
r = requests.get(f"{BASE}/health", timeout=5)
print(f"1. Health BEFORE: {r.status_code}")

# 2. Generate (should return instantly)
t0 = time.time()
r = requests.post(
    f"{BASE}/api/v3/generate",
    json={"topic": "AI Testing", "mode": "standard", "slide_count": 5},
    timeout=15,
)
t1 = time.time()
d = r.json()
deck_id = d.get("deck_id", "")
print(f"2. Generate: {r.status_code} in {t1-t0:.1f}s | deck={deck_id[:12]} | {d.get('message','')}")

# 3. Health AFTER (should be instant if server is not blocked)
r = requests.get(f"{BASE}/health", timeout=5)
print(f"3. Health AFTER: {r.status_code} (server NOT blocked)")

# 4. Poll status a few times
for i in range(5):
    time.sleep(3)
    try:
        r = requests.get(f"{BASE}/api/v3/deck/{deck_id}/status", timeout=5)
        data = r.json()
        print(f"4.{i+1} Status: {r.status_code} | {data.get('status','?')} | slides={data.get('total_slides',0)}")
        if data.get("status") in ("completed", "failed"):
            break
    except Exception as e:
        print(f"4.{i+1} Error: {e}")
