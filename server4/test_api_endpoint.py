#!/usr/bin/env python
"""Test Server4 API endpoint to verify the SkeletonPlanner.plan() fix."""
import requests
import json

url = "http://localhost:8003/api/v4/generate"
payload = {
    "query": "Create a presentation about AI in healthcare (5 slides)",
    "mode": "standard",
    "purpose": "custom",
    "slide_count": 5
}

print(f"Sending POST request to {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        if "slides" in data:
            slides = data.get("slides", [])
            print(f"Slides: {len(slides)}")
            if slides:
                print(f"First slide title: {slides[0].get('title', 'N/A')}")
        else:
            print(f"Response keys: {list(data.keys())[:10]}")
    else:
        print(f"Error response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("Request timed out (expected - LLM may be slow)")
except Exception as e:
    print(f"Request failed: {type(e).__name__}: {e}")
