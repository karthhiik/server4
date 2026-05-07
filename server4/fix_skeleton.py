#!/usr/bin/env python
"""Fix skeleton_planner.py - remove problematic docstrings and non-ASCII chars"""

# Read file as binary
with open('app/services/v4/skeleton_planner.py', 'rb') as f:
    data = f.read()

print(f"Original file: {len(data)} bytes")

# Find and fix the problematic function docstring
# The issue is at line 437-438: """Fallback skeleton."""}
# We need to replace the docstring with something simple

old_pattern = b'    ) -> DeckSkeleton:\r\n        """Fallback skeleton.""""}\r\n'
new_pattern = b'    ) -> DeckSkeleton:\r\n        """Fallback skeleton."""}\r\n'

if old_pattern in data:
    data = data.replace(old_pattern, new_pattern)
    print("Fixed docstring pattern")
else:
    print("Pattern not found, searching...")
    # Find the function
    idx = data.find(b'def _fallback_skeleton(')
    if idx >= 0:
        # Find the docstring
        docstart = data.find(b'"""', idx)
        if docstart >= 0:
            docend = data.find(b'"""', docstart + 3)
            if docend >= 0:
                # Replace docstring with simple one
                new_doc = b'        """Fallback skeleton."""}\r\n'
                data = data[:docstart] + new_doc + data[docend + 3:]
                print(f"Replaced docstring at position {docstart}")

# Remove any remaining non-ASCII characters
clean = bytearray()
for b in data:
    if b <= 127:
        clean.append(b)
    else:
        clean.append(32)  # space

print(f"Cleaned file: {len(clean)} bytes")

# Write back
with open('app/services/v4/skeleton_planner.py', 'wb') as f:
    f.write(bytes(clean))

print("Done! File fixed.")
