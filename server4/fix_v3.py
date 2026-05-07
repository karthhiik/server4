#!/usr/bin/env python
"""Fix the malformed docstring in skeleton_planner.py"""
import os

filepath = 'app/services/v4/skeleton_planner.py'

# Read as binary
with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# The issue: line 437-438 has:
#     ) -> DeckSkeleton:
#         """Fallback skeleton.""""}
# The } is INSIDE the docstring, should be OUTSIDE

# Find the bad pattern: """Fallback skeleton.""""}  (with } inside)
bad_pattern = b') -> DeckSkeleton:\r\n        """Fallback skeleton.""""}\r\n'

if bad_pattern in data:
    # Replace with correct version: } outside docstring
    good_pattern = b') -> DeckSkeleton:\r\n        """Fallback skeleton."\r\n        cap = (\r\n'
    data = data.replace(bad_pattern, good_pattern)
    print("Fixed: moved } outside docstring")
else:
    # Try alternate pattern without \r
    bad2 = b') -> DeckSkeleton:\n        """Fallback skeleton.""""}\n'
    if bad2 in data:
        good2 = b') -> DeckSkeleton:\n        """Fallback skeleton."\n        cap = (\n'
        data = data.replace(bad2, good2)
        print("Fixed (no \\r)")
    else:
        print("Pattern not found, searching...")
        # Find the area
        idx = data.find(b'Fallback skeleton')
        if idx >= 0:
            print(f"Found at {idx}: {repr(data[idx:idx+100])}")

# Write back
with open(filepath, 'wb') as f:
    f.write(data)

print(f"Wrote {len(data)} bytes")

# Verify
try:
    compile(data, '<string>')
    print("Compile: OK")
except SyntaxError as e:
    print(f"Compile error: {e}")
