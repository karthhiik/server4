"""
gstack /review skill — Staff Engineer code review.
Analyzes git diff for bugs, security issues, completeness gaps.
"""

import subprocess
import re
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path


def get_git_diff(staged: bool = False, branch: str = "") -> str:
    """Get git diff output."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    if branch:
        cmd.extend([f"{branch}...HEAD", "--stat"])
    else:
        cmd.append("--stat")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        full_diff = subprocess.run(
            ["git", "diff"] + (["--staged"] if staged else []),
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        return full_diff.stdout
    except Exception as e:
        return f"Error getting diff: {e}"


def get_changed_files() -> List[str]:
    """Get list of changed files."""
    result = subprocess.run(
        ["git", "diff", "--name-only"], capture_output=True, text=True, cwd=os.getcwd()
    )
    return [f.strip() for f in result.stdout.split("\n") if f.strip()]


def analyze_common_bugs(content: str, extension: str) -> List[str]:
    """Analyze for common bug patterns."""
    issues = []

    # Python-specific
    if extension == ".py":
        # Bare except
        if re.search(r"except\s*:", content):
            issues.append("Bare except clause — should catch specific exception")
        # TODO without issue number
        if re.search(r"#\s*TODO\s*(?!#[A-Z0-9-]+)", content):
            issues.append("TODO without issue reference")
        # Hardcoded paths
        if re.search(r'["\'][A-Za-z]:\\\\|/\w+/', content):
            issues.append("Hardcoded file path detected")
        # Print statements in production code
        if re.search(r"\bprint\s*\(", content) and "debug" not in content.lower():
            issues.append("print() statement — use logging instead")

    # JavaScript/TypeScript
    elif extension in [".js", ".ts", ".jsx", ".tsx"]:
        # Console.log
        if re.search(r"console\.(log|debug|info)", content):
            issues.append("console.* statement — use proper logger")
        # Any type
        if re.search(r":\s*any\b", content):
            issues.append("Using 'any' type — be more specific")
        # TODO
        if re.search(r"//\s*TODO", content):
            issues.append("TODO comment found")

    return issues


def analyze_security(content: str) -> List[str]:
    """Analyze for security issues."""
    issues = []

    # Hardcoded secrets patterns
    secret_patterns = [
        (r'api[_-]?key\s*=\s*["\'][^"\']{20,}', "Hardcoded API key"),
        (r'secret\s*=\s*["\'][^"\']{20,}', "Hardcoded secret"),
        (r'password\s*=\s*["\'][^"\']+', "Hardcoded password"),
        (r'token\s*=\s*["\'][^"\']{20,}', "Hardcoded token"),
        (r'private[_-]?key\s*=\s*["\']', "Hardcoded private key"),
    ]

    for pattern, desc in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Security: {desc}")

    # SQL injection
    if re.search(r"(SELECT|INSERT|UPDATE|DELETE).*\%s|%.*\+", content):
        issues.append("Potential SQL injection — use parameterized queries")

    # XSS
    if re.search(r"innerHTML\s*=|dangerouslySetInnerHTML", content):
        issues.append("Potential XSS — validate/-sanitize HTML content")

    return issues


def analyze_completeness(content: str, filepath: str) -> List[str]:
    """Analyze for completeness gaps."""
    issues = []
    extension = Path(filepath).suffix

    # Missing error handling
    if extension in [".py", ".js", ".ts"]:
        if "open(" in content and "try" not in content:
            issues.append("File operations without try/except")
        if "requests" in content or "fetch" in content:
            if "except" not in content:
                issues.append("Network calls without error handling")

    # Missing tests
    if extension == ".py" and "def " in content:
        if not Path(filepath).name.startswith("test_"):
            test_file = Path(filepath).parent / f"test_{Path(filepath).name}"
            if not test_file.exists():
                issues.append(
                    f"No corresponding test file (expected: {test_file.name})"
                )

    # Missing type hints
    if extension == ".py":
        if "def " in content and ":" in content:
            if "->" not in content and "def " in content:
                # Check if it's a complex function
                if "async" in content or "yield" in content:
                    pass  # Skip for now
                else:
                    issues.append("Function without return type hint")

    return issues


def run_review() -> Dict[str, any]:
    """Run full code review."""
    files = get_changed_files()
    results = {
        "files_reviewed": len(files),
        "files_with_issues": [],
        "total_issues": 0,
        "issues_by_type": {
            "bugs": [],
            "security": [],
            "completeness": [],
        },
        "auto_fixes": [],
    }

    for filepath in files:
        if any(
            filepath.startswith(p)
            for p in [".git/", "node_modules/", "venv/", "__pycache__/", ".venv/"]
        ):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            continue

        extension = Path(filepath).suffix

        # Analyze
        bug_issues = analyze_common_bugs(content, extension)
        sec_issues = analyze_security(content)
        comp_issues = analyze_completeness(content, filepath)

        if bug_issues or sec_issues or comp_issues:
            results["files_with_issues"].append(filepath)
            results["issues_by_type"]["bugs"].extend(
                [(filepath, i) for i in bug_issues]
            )
            results["issues_by_type"]["security"].extend(
                [(filepath, i) for i in sec_issues]
            )
            results["issues_by_type"]["completeness"].extend(
                [(filepath, i) for i in comp_issues]
            )
            results["total_issues"] += (
                len(bug_issues) + len(sec_issues) + len(comp_issues)
            )

    # Get summary stats
    diff_output = get_git_diff()
    results["diff_stats"] = diff_output[:500] if diff_output else "No changes"

    return results


def print_review_summary(results: Dict) -> str:
    """Format review results as text."""
    lines = [
        "=" * 60,
        "gstack /review — Code Review Results",
        "=" * 60,
        f"Files reviewed: {results['files_reviewed']}",
        f"Files with issues: {len(results['files_with_issues'])}",
        f"Total issues: {results['total_issues']}",
        "",
    ]

    if results["issues_by_type"]["security"]:
        lines.append("🚨 SECURITY ISSUES:")
        for fp, issue in results["issues_by_type"]["security"]:
            lines.append(f"  [{fp}] {issue}")
        lines.append("")

    if results["issues_by_type"]["bugs"]:
        lines.append("🐛 BUGS:")
        for fp, issue in results["issues_by_type"]["bugs"]:
            lines.append(f"  [{fp}] {issue}")
        lines.append("")

    if results["issues_by_type"]["completeness"]:
        lines.append("⚠️ COMPLETENESS:")
        for fp, issue in results["issues_by_type"]["completeness"]:
            lines.append(f"  [{fp}] {issue}")
        lines.append("")

    if not results["total_issues"]:
        lines.append("✅ No issues found!")

    return "\n".join(lines)


if __name__ == "__main__":
    results = run_review()
    print(print_review_summary(results))
