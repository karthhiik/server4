#!/usr/bin/env python
"""Fix encoding issues in skeleton_planner.py and test_phase5.py"""

import os

# Fix skeleton_planner.py
file1 = 'app/services/v4/skeleton_planner.py'
with open(file1, 'rb') as f:
    data = f.read()

print(f"skeleton_planner.py: {len(data)} bytes")
# Find non-ASCII
non_ascii = [b for b in data if b > 127]
print(f"Non-ASCII bytes: {len(non_ascii)}")

# Replace known problematic bytes
replacements = {
    b'\xe2\x80\x94': b'-',      # em dash
    b'\xe2\x80\x98': b"'",      # left single quote
    b'\xe2\x80\x99': b"'",      # right single quote
    b'\xe2\x80\x9c': b'"',       # left double quote
    b'\xe2\x80\x9d': b'"',       # right double quote
    b'\xe2\x80\xa6': b'...',     # horizontal ellipsis
    b'\xc2\xab': b'<<',        # left double angle quote
    b'\xc2\xbb': b'>>',        # right double angle quote
}

for old, new in replacements.items():
    data = data.replace(old, new)

# Remove any remaining non-ASCII
clean = bytearray()
for b in data:
    if b <= 127:
        clean.append(b)
    else:
        clean.append(32)  # space

with open(file1, 'wb') as f:
    f.write(bytes(clean))
print(f"Fixed {file1}")

# Fix test_phase5.py
file2 = 'test_phase5.py'
with open(file2, 'rb') as f:
    data = f.read()

print(f"test_phase5.py: {len(data)} bytes")
# Replace box-drawing characters with ASCII
box_replacements = {
    b'\xe2\x94\x80': b'-',  # various box drawing
    b'\xe2\x94\x84': b'-',
    b'\xe2\x94\x88': b'-',
    b'\xe2\x94\x8c': b'-',
    b'\xe2\x94\x90': b'-',
    b'\xe2\x94\x94': b'-',
    b'\xe2\x94\xb4': b'-',
    b'\xe2\x94\xb8': b'-',
    b'\xe2\x94\xbc': b'-',
}

for old, new in box_replacements.items():
    data = data.replace(old, new)

# Remove any remaining non-ASCII (like Unicode box drawing)
clean = bytearray()
for b in data:
    if b <= 127:
        clean.append(b)
    else:
        clean.append(32)  # space

with open(file2, 'wb') as f:
    f.write(bytes(clean))
print(f"Fixed {file2}")

print("\nDone! All files cleaned.")
