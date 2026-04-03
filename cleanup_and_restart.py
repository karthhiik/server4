#!/usr/bin/env python
"""
Cleanup script: Kill server, clear Python cache, and test endpoint
"""
import subprocess
import os
import time
import shutil
import sys

def kill_python_processes():
    """Kill all python.exe processes"""
    print("Killing all Python processes...")
    if sys.platform == "win32":
        os.system("taskkill /IM python.exe /F 2>nul")
        time.sleep(1)
        os.system("taskkill /IM python.exe /F 2>nul")  # Try twice to be sure
    else:
        os.system("pkill -9 python 2>/dev/null")
    print("✓ Processes killed")

def clear_pycache(root_dir):
    """Remove all __pycache__ directories"""
    print(f"\nClearing Python cache from {root_dir}...")
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "__pycache__" in dirnames:
            cache_path = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                count += 1
                print(f"  Removed {cache_path}")
            except Exception as e:
                print(f"  Failed to remove {cache_path}: {e}")
    print(f"✓ Cleared {count} __pycache__ directories")

def start_server():
    """Start the FastAPI server"""
    print("\nStarting FastAPI server...")
    os.chdir("/d/Desktop/New_Flask/FLASK/Server1_FastApi")

    # Start server in a new process that persists
    if sys.platform == "win32":
        # Windows: use START command to open new window
        os.system("start python run.py")
    else:
        subprocess.Popen(["python", "run.py"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)

    print("✓ Server started in background")
    print(f"✓ Server should be available at http://127.0.0.1:8080")
    print(f"\nWait 8-10 seconds for server to be fully ready, then test with:")
    print(f'curl -X POST http://127.0.0.1:8080/api/generate-business-plan-async \\')
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -H "Authorization: Bearer test_token" \\')
    print(f'  -d \'{{"prompt": "Create a business plan for an AI SaaS startup", "research_mode": "deep"}}\'')

if __name__ == "__main__":
    os.chdir("/d/Desktop/New_Flask/FLASK")

    print("=" * 70)
    print("PHASE 2: Cleanup and Fresh Server Start")
    print("=" * 70)

    # Kill processes
    kill_python_processes()
    time.sleep(2)

    # Clear cache
    clear_pycache("/d/Desktop/New_Flask/FLASK/Server1_FastApi")

    # Start server
    start_server()

    print("\n" + "=" * 70)
    print("Setup complete! Server is starting...")
    print("=" * 70)
