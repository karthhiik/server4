#!/usr/bin/env python
"""Fix TaskType.SKELETON_PLANNER in skeleton_planner.py"""
with open('app/services/v4/skeleton_planner.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Count occurrences
count = content.count('TaskType.SKELETON_PLANNER')
print(f"Found {count} occurrences of TaskType.SKELETON_PLANNER")

if count > 0:
    # Replace with TaskType.OUTLINE_PLANNING
    new_content = content.replace('TaskType.SKELETON_PLANNER', 'TaskType.OUTLINE_PLANNING')
    with open('app/services/v4/skeleton_planner.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Fixed {count} occurrences -> TaskType.OUTLINE_PLANNING")
else:
    print("No TaskType.SKELETON_PLANNER found")

# Verify
with open('app/services/v4/skeleton_planner.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Check if file compiles
import py_compile
try:
    py_compile.compile(content, '<string>')
    print("File compiles OK")
except py_compile.PyCompileError as e:
    print(f"Compile error: {e}")
