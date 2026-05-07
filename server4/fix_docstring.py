#!/usr/bin/env python
"""Fix malformed docstring in skeleton_planner.py"""
import os

filepath = 'app/services/v4/skeleton_planner.py'

# Read as binary
with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# The issue: line 437-438 has: ) -> DeckSkeleton:\r\n        """Fallback skeleton.""""}\r\n
# The """}" is wrong - should be just """
# Let's find and fix it

# Find the problematic pattern
idx = data.find(b'Fallback skeleton.')
if idx >= 0:
    print(f"Found 'Fallback skeleton.' at offset {idx}")
    # Show context
    print("Context:", repr(data[idx-50:idx+100]))
    
    # Replace the malformed closing
    old = b') -> DeckSkeleton:\r\n        """Fallback skeleton.""""}\r\n'
    new = b') -> DeckSkeleton:\r\n        """Fallback skeleton."""\r\n'
    
    if old in data:
        data = data.replace(old, new)
        with open(filepath, 'wb') as f:
            f.write(data)
        print("Fix applied: replaced malformed docstring close")
    else:
        # Try simpler fix - just find the """}" pattern
        # Find the last """ before the function ends
        search_start = idx
        # Find the bad pattern """}
        bad_idx = data.find(b'"""}\r\n', search_start)
        if bad_idx >= 0:
            print(f"Found bad pattern at {bad_idx}: {repr(data[bad_idx:bad_idx+20])}")
            # Replace """}\r\n with """\r\n
            data = data[:bad_idx] + b'"""\r\n' + data[bad_idx+4:]
            with open(filepath, 'wb') as f:
                f.write(data)
            print("Fix applied: removed extra } from docstring")
        else:
            print("Could not find the exact bad pattern")
            # Show what's around line 438
            lines = data.split(b'\r\n')
            for i, line in enumerate(lines[435:442], 436):
                print(f"  Line {i}: {repr(line)}")
else:
    print("Could not find 'Fallback skeleton.'")

# Verify by trying to compile
try:
    with open(filepath, 'r', encoding='utf-8') as f:
        compile(f.read(), '<string>')
    print("\n✓ File compiles successfully!")
except SyntaxError as e:
    print(f"\n✗ Syntax error: {e}")
