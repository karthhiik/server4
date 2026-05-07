#!/usr/bin/env python3
"""Apply all performance fixes to content_pipeline.py - clean approach."""
with open('app/services/v4/content_pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the company preflight section and add standard mode skip
output = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find the company preflight section start
    if '# Stage 1.5: company preflight' in line or '# Stage1.5' in line:
        # Write the comment lines (unchanged)
        while i < len(lines) and (lines[i].strip().startswith('# Stage') or 
               lines[i].strip().startswith('# Premium') or
               lines[i].strip().startswith('# OR') or
               lines[i].strip().startswith('# LinkedIn') or
               lines[i].strip().startswith('# slow') or
               lines[i].strip() == '' or
               lines[i].startswith('            #')):
            output.append(lines[i])
            i += 1
            if i >= len(lines):
                break
        
        # Add skip comment
        output.append('            # Skip for standard mode (save ~4s, target <10s generation).\n')
        
        # Write company_ctx initialization
        if i < len(lines) and 'company_ctx: CompanyContext' in lines[i]:
            output.append(lines[i])
            i += 1
        
        # Add if check for standard mode
        output.append('            if mode != "standard":\n')
        
        # Indent the next lines (company preflight code) by 4 extra spaces
        while i < len(lines):
            current = lines[i]
            # Check if we've reached the end of the company preflight section
            if current.strip().startswith('# Stage 2:') or 
               current.strip().startswith('# Stage2'):
                break
            # Add extra indentation
            if current.strip():  # Non-empty line
                output.append('    ' + current)
            else:
                output.append(current)
            i += 1
        
        # Add else clause for standard mode
        output.append('            else:\n')
        output.append('                logger.info("v4_company_preflight_skipped", mode=mode, reason="standard_mode_speed")\n')
        continue
    
    output.append(line)
    i += 1

with open('app/services/v4/content_pipeline.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print('Fix applied successfully!')
