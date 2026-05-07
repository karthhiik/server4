#!/usr/bin/env python
"""Fix content_pipeline.py - remove duplicate plan() section causing syntax error."""
import os

filepath = 'app/services/v4/content_pipeline.py'

with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# The issue: There's a DUPLICATE plan() call section
# Find the second occurrence of "skeleton = self.planner.plan("
idx1 = data.find(b'skeleton = self.planner.plan(')
if idx1 >= 0:
    idx2 = data.find(b'skeleton = self.planner.plan(', idx1 + 1)
    if idx2 >= 0:
        print(f"Found SECOND plan() call at byte {idx2}")
        
        # Find the try: block before this second call
        # Look backwards for "try:"
        try_pos = data.rfind(b'try:', 0, idx2)
        if try_pos >= 0:
            print(f"Found try: at byte {try_pos}")
            
            # Find the matching "except Exception as e:" after the try block
            remaining = data[try_pos:]
            except_match = re.search(rb'except Exception as e:', remaining)
            if except_match:
                end_of_duplicate = try_pos + except_match.start()
                print(f"End of duplicate section at byte {end_of_duplicate}")
                
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
        # Check if there's an extra ) line
        lines = data.split(b'\n')
        for i, line in enumerate(lines):
            if line.strip() == b')':
                print(f"Found line with just ): at line {i+1}")
                # This might be the extra one - but we need context
                print(f"Context: {lines[max(0,i-2):i+3]}")
                break
else:
    print("Only one plan() call found - no duplicate to remove")

# Verify syntax
try:
    compile(data, filepath)
    print("Syntax check: PASSED")
except SyntaxError as e:
    print(f"Syntax check: FAILED - {e}")
    print(f"At line: {e.lineno}")
