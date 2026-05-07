#!/usr/bin/env python
"""Fix content_pipeline.py - remove extra ) at line 372"""
with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Check lines 365-380
print("\nChecking lines 365-380:")
for i in range(364, min(381, len(lines))):
    print(f"{i+1}: {repr(lines[i])}")

# The issue: there's an extra ) somewhere
# Let me find ALL ) lines
print("\nFinding lines with ):")
paren_lines = []
for i, line in enumerate(lines):
    if ')' in line and '(' not in line:
        paren_lines.append(i+1)
        
if paren_lines:
    print(f"Lines with ) but no (: {paren_lines}")
    # Check if any of these are unmatched
    # Simple check: count ( and ) in the file
    content = ''.join(lines)
    open_count = content.count('(')
    close_count = content.count(')')
    print(f"Total (: {open_count}, ): {close_count}")
    if close_count > open_count:
        print(f"EXTRA ) found! Difference: {close_count - open_count}")
        # Find and remove the extra )
        # Look for lines that have ) but shouldn't
        for i in range(len(lines)):
            if lines[i].strip() == ')':
                print(f"Found line with just ): line {i+1}")
                # This is likely the extra one
                # But we need to be careful - it might be legitimate
                
# Let me check the context around line 372 (user's error)
if len(lines) >= 372:
    print(f"\nContext around line 372:")
    for i in range(369, min(375, len(lines))):
        print(f"{i+1}: {repr(lines[i])}")
" 2>&1