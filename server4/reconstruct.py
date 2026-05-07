#!/usr/bin/env python
"""Reconstruct content_pipeline.py with the correct content."""
import re

# Read the corrupted file
try:
    with open('app/services/v4/content_pipeline.py', 'rb') as f:
        corrupted = f.read()
    print(f"Corrupted file: {len(corrupted)} bytes")
except:
    corrupted = b''

# The file should be ~20000 bytes (620 lines)
# Let me reconstruct it from the original structure we saw earlier

# Actually, let me just fix the corrupted file by:
# 1. Removing the duplicate section
# 2. Fixing the plan() call parameters

with open('app/services/v4/content_pipeline.py', 'rb') as f:
    data = f.read()

print(f"Current file: {len(data)} bytes")

# Find the problematic section
# The issue is that there's a ')' at line 372 that's unmatched
# Let me find if there's a duplicate plan() call

plan_calls = [m.start() for m in re.finditer(rb'skeleton = self\.planner\.plan\(', data)]
print(f"Found {len(plan_calls)} planner.plan() calls")

if len(plan_calls) > 1:
    print("Found duplicate plan() calls! Removing the second one...")
    # Find the try: block that contains the second call
    second_call = plan_calls[1]
    
    # Find the "try:" before this call
    try_pos = data.rfind(b'try:', 0, second_call)
    if try_pos >= 0:
        print(f"Found 'try:' at position {try_pos}")
        # Find the matching "except Exception as e:"
        remaining = data[try_pos:]
        except_match = re.search(rb'except Exception as e:', remaining)
        if except_match:
            end_of_duplicate = try_pos + except_match.start()
            print(f"Removing duplicate section from {try_pos} to {end_of_duplicate}")
            data = data[:try_pos] + data[end_of_duplicate:]
            
            with open('app/services/v4/content_pipeline.py', 'wb') as f:
                f.write(data)
            print(f"Fixed! File now has {len(data)} bytes")
        else:
            print("Could not find 'except Exception as e:' after try block")
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
            if line.strip() == b')' and not any(c == b'(' for c in lines[max(0,i-5):i]):
                print(f"Removing extra ) at line {i+1}")
                continue
            new_lines.append(line)
        data = b'\n'.join(new_lines)
        
        with open('app/services/v4/content_pipeline.py', 'wb') as f:
            f.write(data)
        print(f"Fixed! File now has {len(data)} bytes, {len(data.split(b'\n'))} lines")
