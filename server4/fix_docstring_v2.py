#!/usr/bin/env python
"""Fix the malformed docstring in skeleton_planner.py"""

filepath = 'app/services/v4/skeleton_planner.py'

# Read as binary
with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# The issue: line 437-438 has:
#     ) -> DeckSkeleton:
#         """Fallback skeleton.""""}
# The """}" is wrong - the } should be OUTSIDE the docstring
# Fix: Replace the malformed pattern

old_pattern = b') -> DeckSkeleton:\r\n        """Fallback skeleton.""""}\r\n'
new_pattern = b') -> DeckSkeleton:\r\n        """Fallback skeleton."""}\r\n'

if old_pattern in data:
    data = data.replace(old_pattern, new_pattern)
    with open(filepath, 'wb') as f:
        f.write(data)
    print("Fix applied: moved } outside docstring")
else:
    print("Pattern not found, trying alternate...")
    # Try without \\r
    old2 = b') -> DeckSkeleton:\n        """Fallback skeleton.""""}\n'
    new2 = b') -> DeckSkeleton:\n        """Fallback skeleton."""}\n'
    if old2 in data:
        data = data.replace(old2, new2)
        with open(filepath, 'wb') as f:
            f.write(data)
        print("Fix applied (no \\r)")
    else:
        print("Neither pattern found")
        # Show what's actually there
        idx = data.find(b'DeckSkeleton:')
        if idx >= 0:
            print("Found context:", repr(data[idx:idx+100]))

# Verify by trying to compile
try:
    compile(data, '<string>')
    print("\n✓ File compiles successfully!")
except SyntaxError as e:
    print(f"\n✗ Syntax error: {e}")
