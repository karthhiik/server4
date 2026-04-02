---
name: /qa
description: QA Lead — test the app, find bugs, fix them with atomic commits, re-verify
---

## When to use
When user wants to test a deployed app (staging URL) and find bugs.

## How it works
1. Accept a staging URL from user
2. Use /browse to navigate through the app
3. Click through key user flows
4. Identify bugs (UI broken, functionality not working, errors in console)
5. Fix bugs with atomic commits
6. Re-verify fixes work

## Usage
```
/qa https://staging.myapp.com
```

## Implementation
- Requires /browse skill to be available
- Navigate: homepage → login → dashboard → key features
- Check: console errors, network failures, broken CSS, missing images
- Document bugs with steps to reproduce
- Create fixes as separate atomic commits

## Prerequisites
/browse skill must be loaded first.