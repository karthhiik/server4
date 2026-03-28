import ast
import sys

files = [
    'FASTAPI_COMMUNITY/app/api/utils/db_helpers.py',
    'FASTAPI_COMMUNITY/app/api/utils/community.py',
    'FASTAPI_COMMUNITY/app/api/routes/follow_routes.py'
]

print('Checking Python syntax for 3 files...\n')
errors_found = False

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f'✓ {file_path}: Syntax OK')
    except SyntaxError as e:
        errors_found = True
        print(f'✗ {file_path}: SYNTAX ERROR')
        print(f'  Line {e.lineno}: {e.msg}')
        if e.text:
            print(f'  {e.text.rstrip()}')
            if e.offset:
                print(f'  {" " * (e.offset - 1)}^')
    except FileNotFoundError:
        errors_found = True
        print(f'✗ {file_path}: FILE NOT FOUND')
    except Exception as e:
        errors_found = True
        print(f'✗ {file_path}: ERROR - {str(e)}')

print()
if not errors_found:
    print('All files have valid Python syntax!')
    sys.exit(0)
else:
    print('Syntax errors found in one or more files.')
    sys.exit(1)
