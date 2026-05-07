#!/usr/bin/env python
"""Fix content_pipeline.py - remove the syntax error at line 372."""
import re

filepath = 'app/services/v4/content_pipeline.py'

with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# The issue: There's an extra ) at line 372 (byte position around 14325)
# Let me find the problematic section and fix it

# Find the second occurrence of "skeleton = self.planner.plan("
# The first one is around byte 7885, second around 14325

idx1 = data.find(b'skeleton = self.planner.plan(')
idx2 = data.find(b'skeleton = self.planner.plan(', idx1 + 1)

print(f"First plan() call at: {idx1}")
print(f"Second plan() call at: {idx2}")

if idx2 > 0:
    # Find the try: block that contains this second call
    # Look backwards for "try:"
    try_pos = data.rfind(b'try:', 0, idx2)
    print(f"Found try: at position: {try_pos}")
    
    if try_pos >= 0:
        # Find the matching "except Exception as e:" after this try block
        remaining = data[try_pos:]
        except_match = re.search(rb'except Exception as e:', remaining)
        if except_match:
            end_of_duplicate = try_pos + except_match.start()
            print(f"End of duplicate section at: {end_of_duplicate}")
            
            # Remove the duplicate section
            data = data[:try_pos] + data[end_of_duplicate:]
            
            with open(filepath, 'wb') as f:
                f.write(data)
            print(f"Fixed! File now has {len(data)} bytes")
        else:
            print("Could not find 'except Exception as e:' after try block")
    else:
        print("Could not find 'try:' before second plan() call")
else:
    print("Only one plan() call found - checking for extra )...")
    # Check for unmatched parentheses
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
        with open(filepath, 'wb') as f:
            f.write(data)
        print(f"Fixed! File now has {len(data)} bytes")
