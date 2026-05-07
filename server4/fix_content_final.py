#!/usr/bin/env python
"""Recreate content_pipeline.py with correct content."""
import os

# The correct plan() call should be:
# skeleton = self.planner.plan(
#     project_id=project_id,
#     user_query=user_query,
#     research=research,
#     slide_count=target_slide_count,
#     narrative_arc="investor_pitch" if purpose == "pitch_deck" else "custom",
# )

# Let me read what we have and fix it
filepath = 'app/services/v4/content_pipeline.py'

with open(filepath, 'rb') as f:
    data = f.read()

print(f"Current file: {len(data)} bytes")

# The issue: There's an extra ) somewhere
# Let me find and remove the duplicate plan() call section

import re

# Find all "skeleton = self.planner.plan(" occurrences
plan_calls = [m.start() for m in re.finditer(rb'skeleton = self\.planner\.plan\(', data)]
print(f"Found {len(plan_calls)} planner.plan() calls")

if len(plan_calls) > 1:
    print("Found duplicate! Removing second call...")
    # Find the try: block that contains the second call
    second_call = plan_calls[1]
    
    # Find "try:" before the second call
    try_pos = data.rfind(rb'try:', 0, second_call)
    if try_pos >= 0:
        print(f"Found 'try:' at position {try_pos}")
        
        # Find the matching "except Exception as e:"
        remaining = data[try_pos:]
        except_match = re.search(rb'except Exception as e:', remaining)
        if except_match:
            end_of_try = try_pos + except_match.start()
            print(f"End of try block at {end_of_try}")
            
            # Remove from try_pos to end_of_try
            data = data[:try_pos] + data[end_of_try:]
            
            with open(filepath, 'wb') as f:
                f.write(data)
            print(f"Fixed! File now: {len(data)} bytes")
        else:
            print("Could not find 'except Exception as e:'")
    else:
        print("Could not find 'try:' before second plan() call")
else:
    print("Only one plan() call found. Checking for extra )...")
    # Count parentheses
    open_count = data.count(b'(')
    close_count = data.count(b')')
    print(f"Open (: {open_count}")
    print(f"Close ): {close_count}")
    
    if close_count > open_count:
        print(f"Extra ) found! Difference: {close_count - open_count}")
        # Find lines that are just )
        lines = data.split(b'\n')
        new_lines = []
        for i, line in enumerate(lines):
            if line.strip() == b')' and (i == 0 or lines[i-1].strip() != b''):
                # Check if this ) is extra by counting
                # For simplicity, just remove lines that are just )
                print(f"Removing line {i+1}: {line}")
                continue
            new_lines.append(line)
        data = b'\n'.join(new_lines)
        
        with open(filepath, 'wb') as f:
            f.write(data)
        print(f"Fixed! File now: {len(data)} bytes")

# Verify syntax
try:
    compile(data, filepath)
    print("Syntax check: PASSED")
except SyntaxError as e:
    print(f"Syntax check: FAILED - {e}")
    print(f"At line: {e.lineno}")
