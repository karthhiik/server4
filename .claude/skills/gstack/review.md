---
name: /review
description: Staff Engineer code review — find bugs, auto-fix obvious issues, flag completeness gaps
---

## When to use
When user wants code review on changes. Run after code is written but before shipping.

## How it works
1. Get git diff of changes
2. Analyze for common bugs, security issues, performance problems
3. Identify completeness gaps (missing tests, error handling, etc.)
4. Auto-fix obvious issues
5. Flag items needing user decision

## Usage
```
/review
```

## Implementation
Use bash to run `git diff` and analyze with grep/glob. Check for:
- Syntax errors, type errors
- Missing error handling
- Hardcoded secrets/credentials
- Missing tests
- Security vulnerabilities (SQL injection, XSS)
- Performance anti-patterns

For auto-fixes, use edit tool with clear explanations.