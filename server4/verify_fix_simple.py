#!/usr/bin/env python
"""Quick test to verify the SkeletonPlanner.plan() fix works."""
import sys
sys.path.insert(0, '.')

print("Testing V4ContentPipeline imports and basic functionality...")

try:
    from app.services.v4.content_pipeline import V4ContentPipeline
    print("[OK] V4ContentPipeline imported successfully")
    
    # Create instance
    pipeline = V4ContentPipeline()
    print("[OK] V4ContentPipeline instance created")
    
    # Check if planner has the correct method signature
    import inspect
    sig = inspect.signature(pipeline.planner.plan)
    params = list(sig.parameters.keys())
    print(f"[OK] planner.plan() parameters: {params}")
    
    # Verify no 'analysis' or 'mode' parameters (these were the bug)
    if 'analysis' in params or 'mode' in params:
        print("[FAIL] ERROR: Still has old parameters!")
    else:
        print("[OK] Parameters are correct (no 'analysis' or 'mode')")
        
except Exception as e:
    print(f"[FAIL] FAILED: {e}")
    import traceback
    traceback.print_exc()
