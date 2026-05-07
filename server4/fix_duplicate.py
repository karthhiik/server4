#!/usr/bin/env python
"""Restore content_pipeline.py to original state and fix syntax errors."""
import re

# Read the current file
with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Current file has {len(content.split(chr(10))} lines, {len(content)} chars")

# The issue: The file has DUPLICATE sections and syntax errors
# Let me find and remove the duplicate plan() call section

# Find all skeleton = self.planner.plan( occurrences
plan_calls = [m.start() for m in re.finditer(r'skeleton = self\.planner\.plan\(', content)]
print(f"Found {len(plan_calls)} planner.plan() calls")

if len(plan_calls) > 1:
    print("Too many plan() calls! Need to remove duplicates.")
    # Find the second plan() call and remove it
    # The second call starts at plan_calls[1]
    second_call_start = plan_calls[1]
    
    # Find the end of the second call (next ] that matches)
    # Actually, let me find the surrounding try: block
    # Look for "try:" before the second call
    try_match = re.search(r'try:\s*\n.*?' + re.escape(content[second_call_start:second_call_start+50]), content[:second_call_start], re.S)
    if try_match:
        # Remove from the start of try: to the end of the try block
        # Find the matching except:
        remaining = content[second_call_start:]
        except_match = re.search(r'\n\s*except Exception as e:', remaining)
        if except_match:
            end_of_try_block = second_call_start + except_match.start()
            print(f"Removing duplicate section from {second_call_start} to {end_of_try_block}")
            content = content[:second_call_start] + content[end_of_try_block:]
            
            with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Removed duplicate section!")
        else:
            print("Could not find end of try block")
    else:
        print("Could not find try: before second plan() call")
else:
    print("Only 1 plan() call found. Checking for syntax errors...")
    
    # Check for balanced parentheses in the plan() call
    # Find the plan() call
    if plan_calls:
        start = plan_calls[0]
        # Find the matching )
        open_count = 1
        pos = start + len('skeleton = self.planner.plan(')
        while pos < len(content) and open_count > 0:
            if content[pos] == '(':
                open_count += 1
            elif content[pos] == ')':
                open_count -= 1
            pos += 1
        
        if open_count == 0:
            print(f"plan() call is balanced. Ends at position {pos}")
        else:
            print(f"Unbalanced parentheses! Open count: {open_count}")

print("Done!")
