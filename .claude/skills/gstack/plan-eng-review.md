---
name: /plan-eng-review
description: Engineering Manager — lock architecture, data flow, diagrams, edge cases, tests
---

## When to use
When user wants engineering review of a design doc or implementation plan.

## How it works
1. Read the design doc (DESIGN.md or provided document)
2. Analyze architecture, data flow, state machines
3. Identify edge cases, failure modes, security concerns
4. Create test matrix (happy path + failure scenarios)
5. Document assumptions and hidden requirements

## Usage
```
/plan-eng-review
```

## Implementation Checklist

### Architecture Analysis
- [ ] Component diagram (ASCII)
- [ ] Data flow between services
- [ ] Database schema changes
- [ ] API contracts
- [ ] Authentication/authorization flow

### Edge Cases
- [ ] Network failures
- [ ] Invalid input handling
- [ ] Race conditions
- [ ] Concurrency issues
- [ ] Timeout handling
- [ ] Partial failures in distributed systems

### Security
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication bypass
- [ ] Authorization gaps

### Test Matrix
| Scenario | Input | Expected | Test Type |
|----------|-------|----------|-----------|
| Happy path | Valid X | Y | Unit |
| Invalid input | Invalid X | Error | Unit |
| Network fail | Timeout | Graceful | Integration |

## Output
Write analysis to a review file or update the design doc with:
- Architecture diagrams (ASCII)
- Test matrix
- Edge case analysis
- Security concerns