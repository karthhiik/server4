#!/usr/bin/env python
"""Syntax validation and import test script."""

import sys
import py_compile
import os

# Files to validate
files_to_check = [
    r"d:\Desktop\New_Flask\FLASK\Server1_FastApi\app\services\intelligence\repository.py",
    r"d:\Desktop\New_Flask\FLASK\Server1_FastApi\app\services\intelligence\checkpoint.py",
    r"d:\Desktop\New_Flask\FLASK\Server1_FastApi\app\celery_tasks\intelligence_tasks.py",
]

print("=" * 70)
print("PYTHON SYNTAX VALIDATION")
print("=" * 70)

syntax_errors = []
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✓ {filepath}")
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath}")
        print(f"  Error: {e}")
        syntax_errors.append((filepath, str(e)))

print("\n" + "=" * 70)
print("IMPORT TEST")
print("=" * 70)

# Add the Server1_FastApi directory to sys.path
server_path = r"d:\Desktop\New_Flask\FLASK\Server1_FastApi"
if server_path not in sys.path:
    sys.path.insert(0, server_path)

try:
    from app.services.intelligence.repository import repository
    print("✓ Successfully imported repository")
except Exception as e:
    print(f"✗ Failed to import repository: {e}")
    import traceback
    traceback.print_exc()
    syntax_errors.append(("import_repository", str(e)))

try:
    from app.services.intelligence.checkpoint import checkpoint_manager
    print("✓ Successfully imported checkpoint_manager")
except Exception as e:
    print(f"✗ Failed to import checkpoint_manager: {e}")
    import traceback
    traceback.print_exc()
    syntax_errors.append(("import_checkpoint", str(e)))

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if syntax_errors:
    print(f"\n❌ Found {len(syntax_errors)} error(s):\n")
    for item, error in syntax_errors:
        print(f"  - {item}")
        print(f"    {error}\n")
    sys.exit(1)
else:
    print("\n✓ All syntax checks passed!")
    print("✓ All imports successful!")
    print("\nImport successful")
    sys.exit(0)
