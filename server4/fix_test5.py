#!/usr/bin/env python
"""Fix test_phase5.py - rewrite header with proper _Results class"""

with open('test_phase5.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where the original file content starts (after the _Results class)
# The original file had test functions starting after line 98
# Let me find line 101 which should be "results = _Results()"
start_content = 0
for i, line in enumerate(lines):
    if 'results = _Results()' in line or 'results = TestResult()' in line:
        start_content = i
        break

print(f"Found results assignment at line {start_content}")

# Write the fixed file
fixed_lines = []
fixed_lines.append('"""\n')
fixed_lines.append('Phase 5 Verification Test -- Design Intelligence & Brand DNA\n')
fixed_lines.append('\n')
fixed_lines.append('Tests:\n')
# ... (keep the test list from original)
fixed_lines.append('Run: python test_phase5.py\n')
fixed_lines.append('"""\n')
fixed_lines.append('\n')
fixed_lines.append('import sys\n')
fixed_lines.append('import re\n')
fixed_lines.append('import traceback\n')
fixed_lines.append('\n')

# Add proper _Results class
fixed_lines.append('class _Results:\n')
fixed_lines.append('    def __init__(self):\n')
fixed_lines.append('        self.passed = 0\n')
fixed_lines.append('        self.failed = 0\n')
fixed_lines.append('        self.results = []\n')
fixed_lines.append('\n')
fixed_lines.append('    def ok(self, msg):\n')
fixed_lines.append('        self.passed += 1\n')
fixed_lines.append("        self.results.append(('PASS', msg))\n")
fixed_lines.append('\n')
fixed_lines.append('    def fail(self, msg, detail=""):\n')
fixed_lines.append('        self.failed += 1\n')
fixed_lines.append("        self.results.append(('FAIL', msg, detail))\n")
fixed_lines.append('\n')
fixed_lines.append('    def summary(self):\n')
fixed_lines.append('        return self.failed == 0\n')
fixed_lines.append('\n')
fixed_lines.append('\n')
fixed_lines.append('# ------ Test result tracking ------------------------------\n')
fixed_lines.append('\n')
fixed_lines.append('results = _Results()\n')
fixed_lines.append('\n')

# Now add the rest of the file (the test functions)
# Skip the old header (lines before "results = _Results()")
rest_start = start_content + 1 if start_content > 0 else 101
fixed_lines.extend(lines[rest_start:])

with open('test_phase5.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed test_phase5.py")
print(f"Total lines: {len(fixed_lines)}")
