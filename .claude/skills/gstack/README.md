# gstack — Skills for OpenCode

Adapted from [Garry Tan's gstack](https://github.com/garrytan/gstack) for OpenCode CLI.

## Available Skills

| Skill | Description |
|-------|-------------|
| `/review` | Staff Engineer code review — find bugs, auto-fix obvious issues |
| `/qa` | QA Lead — test app, find bugs, fix with atomic commits |
| `/browse` | Browser automation — navigate, click, screenshot, extract |
| `/plan-eng-review` | Engineering Manager — architecture, data flow, edge cases |
| `/design-review` | Designer audit — visual quality, fix issues |
| `/investigate` | Debugger — root-cause analysis, trace data flow |

## Usage in OpenCode

Type the skill name to use it. Each skill reads its definition from `.claude/skills/gstack/<skill>.md`.

## Prerequisites

Some skills require dependencies:

- **/browse**: Requires `playwright` (`pip install playwright && playwright install chromium`)
- **/qa**: Requires /browse skill

## Quick Start

1. Copy skills to your project:
   ```bash
   cp -R ~/.claude/skills/gstack .claude/skills/  # if gstack already cloned
   ```
   
   Or use the skills in this directory:
   - `.claude/skills/gstack/review.md`
   - `.claude/skills/gstack/qa.md`
   - etc.

2. Add to your CLAUDE.md:
   ```
   ## gstack
   Use /review, /qa, /browse, /plan-eng-review, /design-review, /investigate from .claude/skills/gstack/
   ```

## Skill Details

### /review
Run git diff, analyze for:
- Syntax/type errors
- Missing error handling
- Hardcoded secrets
- Security vulnerabilities
- Missing tests

### /qa
Accept a staging URL, navigate through key flows, find bugs, fix them.

### /browse
Browser automation with Playwright. Actions: goto, click, type, screenshot, html, text, evaluate.

### /plan-eng-review
Read design doc, create architecture diagrams, test matrix, edge case analysis.

### /design-review
Audit visual hierarchy, color, typography, spacing, accessibility, responsiveness. Fix with atomic commits.

### /investigate
Gather evidence → Form hypothesis → Trace data flow → Test → Fix → Verify. Stop after 3 failed attempts.

---

**Note:** These are OpenCode-native implementations of gstack concepts. The original gstack is designed for Claude Code with 23 skills. This is a subset adapted for OpenCode tools.