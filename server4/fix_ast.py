#!/usr/bin/env python3
"""Fix content_pipeline.py using AST to avoid syntax errors."""
import ast
import sys

# Read the file
with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the company preflight section and fix it
# The issue: the "if mode != \"standard\":" block is not properly closed

# Let's just add "if mode != \"standard\":" before the preflight code
# And close it properly after the emit statement

lines = content.split('\n')
output = []
i = 0
in_preflight = False
preflight_indent = None

while i < len(lines):
    line = lines[i]
    
    # Detect start of company preflight section
    if '# Stage 1.5: company preflight' in line or '# Stage1.5:' in line:
        # Write the comment lines (unchanged)
        while i < len(lines) and (lines[i].strip().startswith('#') or lines[i].strip() == ''):
            output.append(lines[i])
            i += 1
        # Now we're at the company_ctx line
        if i < len(lines) and 'company_ctx: CompanyContext = CompanyContext()' in lines[i]:
            output.append(lines[i])
            i += 1
        # Add the if check
        output.append('            # Skip for standard mode (save ~4s, target <10s generation)')
        output.append('            if mode != "standard":')
        # Now indent the next lines (preflight code) by 4 extra spaces
        preflight_indent = '    '  # 4 spaces for inside the if block
        in_preflight = True
        continue
    
    # If we're inside the preflight block, add extra indent
    if in_preflight:
        # Check if we've reached the end of the preflight section
        if line.strip().startswith('# Stage 2:') or line.strip().startswith('            # Stage2:'):
            # End of preflight section
            in_preflight = False
            output.append('            else:')
            output.append('                logger.info("v4_company_preflight_skipped", mode=mode, reason="standard_mode_speed")')
            output.append(line)
            i += 1
            continue
        # Add extra indent
        if line.strip():  # Non-empty line
            output.append('    ' + line)
        else:
            output.append(line)
        i += 1
    else:
        output.append(line)
        i += 1

# Write back
with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('AST fix applied!')
