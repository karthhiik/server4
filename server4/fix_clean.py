#!/usr/bin/env python3
"""Apply all performance fixes to content_pipeline.py without syntax errors."""
import re

with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the company preflight section and skip for standard mode
output = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find the company preflight section
    if '# Stage 1.5: company preflight' in line or '# Stage1.5:' in line:
        # Write the comment lines (unchanged)
        output.append(line)  # '# Stage 1.5: company preflight...'
        i += 1
        if i >= len(lines):
            break
        output.append(lines[i])  # '# Premium runs the deep variant...'
        i += 1
        if i >= len(lines):
            break
        output.append(lines[i])  # '# OR 1 search)...'
        i += 1
        if i >= len(lines):
            break
        output.append(lines[i])  # '# slow homepage never delays research.'
        i += 1
        if i >= len(lines):
            break
        
        # Add skip comment
        output.append('            # Skip for standard mode (save ~4s, target <10s generation).\n')
        
        # Write company_ctx initialization
        output.append('            company_ctx: CompanyContext = CompanyContext()\n')
        i += 1  # Skip original company_ctx line
        
        # Add if mode != "standard": check
        output.append('            if mode != "standard":\n')
        
        # Indent the next lines (original preflight code) by 4 extra spaces
        indent_level = '    '  # 4 extra spaces for inside the if block
        while i < len(lines):
            current_line = lines[i]
            # Check if we've reached the end of the preflight section
            # (next stage starts with '# Stage 2:' or similar)
            if current_line.strip().startswith('# Stage 2:') or 
               current_line.strip().startswith('            # Stage2:'):
                break
            # Add extra indentation
            if current_line.strip():  # Non-empty line
                output.append('    ' + current_line)
            else:
                output.append(current_line)
            i += 1
        
        # Add else clause for standard mode
        output.append('            else:\n')
        output.append('                logger.info("v4_company_preflight_skipped", mode=mode, reason="standard_mode_speed")\n')
        continue
    
    output.append(line)
    i += 1

# Write back
with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print('Fix applied successfully!')
