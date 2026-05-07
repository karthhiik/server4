#!/usr/bin/env python
"""Fix skeleton_planner.py:
1. Update safe_complete() calls to use new signature
2. Fix intents bug in _fallback_skeleton()
"""
with open('app/services/v4/skeleton_planner.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace all safe_complete() calls
# Old: prompt=user, system=system, task_type=TaskType.OUTLINE_PLANNING
# New: router=self.model_router, primary_task=TaskType.OUTLINE_PLANNING, messages=[...]

import re

# Pattern to match safe_complete calls and replace them
def fix_safe_complete(match):
    """Fix a single safe_complete() call."""
    text = match.group(0)
    # Extract the arguments
    # Old format: prompt=user, system=system, task_type=..., timeout_s=...
    # New format: router=..., primary_task=..., messages=[...], timeout_s=...
    
    # Replace prompt= with messages=[...]
    text = re.sub(r'prompt=user,', 'messages=[{"role": "user", "content": user}, {"role": "system", "content": system}],', text)
    text = re.sub(r'prompt=user,\s+system=system,', 'messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],', text)
    
    # Replace task_type= with primary_task=
    text = re.sub(r'task_type=', 'primary_task=', text)
    
    # Add router=self.model_router,
    text = re.sub(r'safe_complete\(\s*', 'safe_complete(\n                router=self.model_router,\n    ', text)
    
    return text

# Actually, let me just do a simpler approach - replace the entire function bodies
# Let me find and replace _plan_premium and _plan_standard functions

print("Fixing _plan_premium function...")
# Find _plan_premium function
premium_match = re.search(r'async def _plan_premium\(.*?(?=async def _plan_standard|\Z)', content, re.S)
if premium_match:
    old_premium = premium_match.group(0)
    # Fix the safe_complete call inside
    new_premium = old_premium.replace(
        '                prompt=user,\n                system=system,\n                task_type=TaskType.OUTLINE_PLANNING,\n                timeout_s=STANDARD_SKELETON_TIMEOUT_S,\n                model_preference="kimil",  # Premier reasoning model\n            )',
        '                router=self.model_router,\n                primary_task=TaskType.OUTLINE_PLANNING,\n                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],\n                timeout_s=STANDARD_SKELETON_TIMEOUT_S,\n            )'
    )
    if new_premium != old_premium:
        content = content.replace(old_premium, new_premium)
        print("  Fixed _plan_premium")
    else:
        print("  No change in _plan_premium")

print("Fixing _plan_standard function...")
# Find _plan_standard function
standard_match = re.search(r'async def _plan_standard\(.*?(?=def _build_system_prompt|\Z)', content, re.S)
if standard_match:
    old_standard = standard_match.group(0)
    # Fix the primary safe_complete call
    new_standard = old_standard.replace(
        '                prompt=user,\n                system=system,\n                task_type=TaskType.OUTLINE_PLANNING,\n                timeout_s=STANDARD_SKELETON_PRIMARY_TIMEOUT_S,\n            )',
        '                router=self.model_router,\n                primary_task=TaskType.OUTLINE_PLANNING,\n                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],\n                timeout_s=STANDARD_SKELETON_PRIMARY_TIMEOUT_S,\n            )'
    )
    # Fix the fallback safe_complete call
    new_standard = new_standard.replace(
        '                    prompt=user,\n                    system=system,\n                    task_type=TaskType.OUTLINE_PLANNING,\n                    timeout_s=STANDARD_SKELETON_FALLBACK_TIMEOUT_S,\n                    model_preference="fast",  # Fast fallback\n                )',
        '                    router=self.model_router,\n                    primary_task=TaskType.OUTLINE_PLANNING,\n                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],\n                    timeout_s=STANDARD_SKELETON_FALLBACK_TIMEOUT_S,\n                )'
    )
    if new_standard != old_standard:
        content = content.replace(old_standard, new_standard)
        print("  Fixed _plan_standard")
    else:
        print("  No change in _plan_standard")

# Fix 2: Fix intents bug in _fallback_skeleton()
print("Fixing _fallback_skeleton() intents bug...")
# Find the intents = intents[:cap] line and fix it
# Should be: define intents based on narrative_arc, then slice
old_intents = '        intents = intents[:cap]'
new_intents = '''        # Define intents based on narrative_arc
        if narrative_arc == "investor_pitch":
            intents = [item["intent"] for item in CANONICAL_COMPANY_PITCH_STRUCTURE]
        else:
            intents = [item["intent"] for item in CANONICAL_CONCEPT_PITCH_STRUCTURE]
        intents = intents[:cap]'''

if old_intents in content:
    content = content.replace(old_intents, new_intents)
    print("  Fixed intents bug")
else:
    print("  intents line not found")

# Write back
with open('app/services/v4/skeleton_planner.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! File updated.")
