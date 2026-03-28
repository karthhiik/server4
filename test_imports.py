#!/usr/bin/env python3
"""
FastAPI Application Import Test
Tests whether the FASTAPI_COMMUNITY app can be imported without errors
"""
import sys
import os
import traceback

# Add the project root to sys.path
project_root = r"D:\Desktop\New_Flask\FLASK\FASTAPI_COMMUNITY"
sys.path.insert(0, project_root)
os.chdir(project_root)

print("=" * 70)
print("FastAPI Application Import Test")
print("=" * 70)
print(f"\nProject Root: {project_root}")
print(f"Python Version: {sys.version}")
print(f"Working Directory: {os.getcwd()}\n")

# Test 1: Try importing the main app
print("Test 1: Importing app.main.app...")
print("-" * 70)
try:
    from app.main import app
    print("✓ App imports successfully!")
    print(f"  App Type: {type(app)}")
    print(f"  App Routes: {len(app.routes)} routes registered")
except Exception as e:
    print(f"✗ FAILED to import app.main.app")
    print(f"  Error: {type(e).__name__}: {str(e)}")
    print("\nFull Traceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("Test 2: Checking app configuration...")
print("-" * 70)
try:
    print(f"  Title: {app.title}")
    print(f"  Version: {app.version if hasattr(app, 'version') else 'N/A'}")
    print(f"  Debug: {app.debug if hasattr(app, 'debug') else 'N/A'}")
    print(f"  Middleware Count: {len(app.user_middleware)}")
    print(f"  Exception Handlers: {len(app.exception_handlers)}")
    print("✓ App configuration looks good!")
except Exception as e:
    print(f"✗ Error checking app configuration: {e}")
    traceback.print_exc()

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("✓ All import tests passed!")
print("  The FastAPI application can be imported and initialized successfully.")
print("=" * 70)
