---
name: /superpowers
description: Superpowers — Agentic software development workflow with multi-agent orchestration
---

## When to use
When user wants to build software with multiple specialized agents working together.

## How it works
1. **Speculate** - Analyze requirements, generate specification
2. **Build** - Implement with subagents (frontend, backend, tests)
3. **Review** - Code review with quality gates
4. **Verify** - Run tests, validate functionality

## Usage
```
/superpowers Build a task management app
/superpowers Add user authentication to my project
/superpowers Fix the login bug
```

## Subcommands

### /speculate
- Analyze requirements
- Generate detailed specification
- Create implementation plan

### /build  
- Frontend agent: React/Next.js/Vue
- Backend agent: Python/Node/Go
- Test agent: Unit + integration tests

### /review
- Code quality review
- Security check
- Performance analysis

### /verify
- Run test suite
- Verify against spec
- Check for regressions

## Best Practices
- Always speculate before building
- Review before merging
- Test-driven development
- Clean architecture principles