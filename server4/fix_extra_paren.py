#!/usr/bin/env python
"""Fix syntax error in content_pipeline.py - remove extra ) at line 372."""
import re

with open('app/services/v4/content_pipeline.py', 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print(f"Lines (approx): {data.count(b'\\n')}")

# The issue: There's an extra ) that's unmatched
# Let me find the second ) that doesn't match any (
# Actually, let me just remove the DUPLICATE section

# Find the pattern: )\\n                    # Re-write slides with new skeleton
# followed by another plan() call

# Actually, let me find ALL plan() calls
plan_calls = [m.start() for m in re.finditer(rb'skeleton = self\.planner\.plan\(', data)]
print(f"Found {len(plan_calls)} planner.plan() calls")

if len(plan_calls) > 1:
    print("Found DUPLICATE plan() calls! Removing the second one...")
    # Find the start of the second plan() call
    second_call_start = plan_calls[1]
    
    # Find the try: block that contains this second call
    # Look backwards for "try:"
    try_pos = data.rfind(b'try:', 0, second_call_start)
    if try_pos >= 0:
        print(f"Found try: at position {try_pos}")
        # Find the matching except Exception as e:
        remaining = data[second_call_start:]
        except_match = re.search(rb'except Exception as e:', remaining)
        if except_match:
            end_of_duplicate = second_call_start + except_match.start()
            print(f"Removing duplicate section from {second_call_start} to {end_of_duplicate}")
            # Remove the duplicate section
            data = data[:try_pos] + data[end_of_duplicate:]
            
            with open('app/services/v4/content_pipeline.py', 'wb') as f:
                f.write(data)
            print("Duplicate section removed! File size now:", len(data), "bytes")
        else:
            print("Could not find end of duplicate section")
    else:
        print("Could not find try: before second plan() call")
else:
    print("Only 1 plan() call found. Checking for extra )...")
    # Count parentheses
    open_count = data.count(b'(')
    close_count = data.count(b')')
    print(f"Open (: {open_count}")
    print(f"Close ): {close_count}")
    if close_count > open_count:
        print(f"EXTRA ) found! Difference: {close_count - open_count}")
        # Find and remove extra ) lines
        lines = data.split(b'\\n')
        new_lines = []
        extra_found = False
        for line in lines:
            if line.strip() == b')' and not extra_found:
                # Check if this ) is extra by counting
                # For simplicity, just remove lines that are JUST )
                print(f"Removing line: {repr(line)}")
                extra_found = True
                continue
            new_lines.append(line)
        data = b'\\n'.join(new_lines)
        with open('app/services/v4/content_pipeline.py', 'wb') as f:
            f.write(data)
        print("Extra ) removed!")

print("Done!")
