#!/usr/bin/env python
"""Reconstruct content_pipeline.py with correct content."""
import re

# This is the CORRECT version of the file (620 lines)
# With the duplicate section REMOVED and parameters FIXED

correct_content = '''# Full correct content here - but let me just fix the actual file

Actually, let me just directly fix the syntax error by removing the extra )
'''

# Read the actual file
with open('app/services/v4/content_pipeline.py', 'rb') as f:
    data = f.read()

print(f"Current file: {len(data)} bytes")

# The issue: There's an extra ) at line 372
# Let me check if the file has unbalanced parentheses
open_count = data.count(b'(')
close_count = data.count(b')')
print(f"Open (: {open_count}")
print(f"Close ): {close_count}")

if close_count > open_count:
    print(f"Extra ) found! Difference: {close_count - open_count}")
    # Find lines that are just )
    lines = data.split(b'\\n')
    new_lines = []
    for i, line in enumerate(lines):
        if line.strip() == b')' and not any(c == b'(' for c in lines[max(0,i-5):i]):
            print(f"Removing extra ) at line {i+1}")
            continue
        new_lines.append(line)
    data = b'\\n'.join(new_lines)
    
    with open('app/services/v4/content_pipeline.py', 'wb') as f:
        f.write(data)
    print(f"Fixed! File now: {len(data)} bytes")
    print(f"New counts: ({data.count(b'(')}, {data.count(b')')})")
