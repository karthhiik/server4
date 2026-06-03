import json
import sys
import time
import urllib.error
import urllib.request
import os

BASE_URL = "http://localhost:8003"
TIMEOUT_SECONDS = 300
POLL_INTERVAL_S = 4

def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _get(path: str, return_json: bool = True):
    req = urllib.request.Request(BASE_URL + path, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        if return_json:
            return json.loads(resp.read().decode("utf-8"))
        return resp.read()

def _poll_until_done(project_id: str, timeout_s: int) -> dict:
    start = time.time()
    terminal = {"completed", "failed", "error", "ready", "ready_for_editing"}
    while time.time() - start < timeout_s:
        try:
            status = _get(f"/api/v4/generation/{project_id}")
            state = status.get("status") or status.get("state")
            if state in terminal:
                status["_state"] = state
                return status
        except Exception as e:
            pass
        time.sleep(POLL_INTERVAL_S)
    return {"_state": "TIMEOUT"}

def test_full_user_flow():
    print("1. Generating Presentation...")
    payload = {
        "mode": "standard",
        "input_method": "prompt",
        "standard_input": {
            "prompt": "Test presentation for automated E2E system check.",
            "slide_count": 4,
            "generate_images": True,
            "generate_notes": True,
        },
    }
    
    try:
        started = _post("/api/v4/generate", payload)
        project_id = started["project_id"]
        print(f" -> Generation started. Project ID: {project_id}")
    except Exception as e:
        print(f" -> FAILED to start generation: {e}")
        return False
        
    print("\n2. Polling for Completion...")
    final = _poll_until_done(project_id, TIMEOUT_SECONDS)
    state = final.get("_state")
    if state not in {"completed", "ready", "ready_for_editing"}:
        print(f" -> FAILED generation. State: {state}")
        return False
    print(" -> Generation completed successfully.")
    
    print("\n3. Retrieving Slides...")
    try:
        slides_resp = _get(f"/api/v4/projects/{project_id}/slides")
        slides = slides_resp.get("slides", [])
        print(f" -> Retrieved {len(slides)} slides.")
        images_generated = sum(1 for s in slides if s.get("image_url"))
        print(f" -> Found {images_generated} slides with generated images.")
    except Exception as e:
        print(f" -> FAILED to retrieve slides: {e}")
        return False
        
    print("\n4. Testing PDF Export...")
    try:
        pdf_bytes = _get(f"/api/v4/projects/{project_id}/export/pdf", return_json=False)
        print(f" -> Successfully downloaded PDF export ({len(pdf_bytes)} bytes)")
    except Exception as e:
        print(f" -> FAILED PDF export: {e}")
        return False
        
    print("\n5. Testing PPTX Export...")
    try:
        pptx_bytes = _get(f"/api/v4/projects/{project_id}/export/pptx", return_json=False)
        print(f" -> Successfully downloaded PPTX export ({len(pptx_bytes)} bytes)")
    except Exception as e:
        print(f" -> FAILED PPTX export: {e}")
        return False

    print("\n✅ All End-to-End steps completed successfully!")
    return True

if __name__ == "__main__":
    success = test_full_user_flow()
    sys.exit(0 if success else 1)
