#!/usr/bin/env python
"""Fix skeleton_planner.py - proper docstring close"""

filepath = 'app/services/v4/skeleton_planner.py'

# Read as binary
with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# Find the problematic area
idx = data.find(b'Fallback skeleton.')
if idx >= 0:
    print(f"Found 'Fallback skeleton.' at {idx}")
    # Show context
    print("Context:", repr(data[idx:idx+100]))
    
    # The issue: """Fallback skeleton.""""}\n
    # Should be: """Fallback skeleton."}\n
    # The """ after the period is starting a NEW string that never ends
    
    # Fix: Find the pattern """Fallback skeleton.""""}\r\n
    old = b'"""Fallback skeleton.""""}\r\n'
    new = b'"""Fallback skeleton."}\r\n'
    
    if old in data:
        data = data.replace(old, new)
        print("Fixed: removed extra \"\" before }")
    else:
        # Try without \r
        old2 = b'"""Fallback skeleton.""""}\n'
        new2 = b'"""Fallback skeleton."}\n'
        if old2 in data:
            data = data.replace(old2, new2)
            print("Fixed (no \\r)")
        else:
            print("Pattern not found, trying manual fix...")
            # Find the docstring end
            doc_end = data.find(b'.""""', idx)
            if doc_end >= 0:
                print(f"Found docstring end at {doc_end}")
                # Insert } after the docstring
                data = data[:doc_end+4] + b'}\r\n' + data[doc_end+4:]
                # Remove } from inside
                # Actually the issue is different...
                print("Manual fix attempted")

# Write back
with open(filepath, 'wb') as f:
    f.write(data)

print(f"Wrote {len(data)} bytes")

# Verify
try:
    compile(data, '<string>')
    print("\n✓ Compilation successful!")
except SyntaxError as e:
    print(f"\n✗ Syntax error: {e}")
