---
name: /investigate
description: Debugger — systematic root-cause debugging, trace data flow, test hypotheses
---

## When to use
When user encounters a bug and wants to find the root cause.

## How it works
1. Gather symptoms (error messages, logs, observed behavior)
2. Form hypothesis about root cause
3. Trace data flow to verify/disprove hypothesis
4. Test fixes with minimal changes
5. Stop after 3 failed fix attempts — escalate

## Iron Law
**No fixes without investigation.** Must trace the actual root cause, not symptoms.

## Usage
```
/investigate
```

## Investigation Process

### Step 1: Gather Evidence
- Error message + stack trace
- Logs (application, system)
- Expected vs actual behavior
- Reproducible steps

### Step 2: Form Hypothesis
- What's the most likely cause?
- What's the simplest explanation?
- What's the most recent change?

### Step 3: Trace Data Flow
- Input → Processing → Output
- Follow the data through the system
- Check each transformation point
- Identify where it diverges

### Step 4: Test Hypothesis
- Can you reproduce the bug?
- Does your hypothesis explain it?
- Is there a simpler explanation?

### Step 5: Fix
- Fix the root cause, not symptoms
- Minimal change preferred
- Add test to prevent regression

### Step 6: Verify
- Does the fix work?
- Are there any side effects?
- Does the test pass?

## Rules
- Stop after 3 failed fix attempts
- If stuck, escalate to user with findings
- Document what you tried