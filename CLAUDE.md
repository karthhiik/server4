# CLAUDE.md — Barise Server4 Project

## gstack Skills (Adapted for OpenCode)

Use skills from `.claude/skills/gstack/`:

### Development
- `/review` — Staff Engineer code review, find bugs, auto-fix
- `/qa` — QA Lead, test app, find bugs, fix with atomic commits  
- `/browse` — Browser automation (Playwright), navigate, screenshot
- `/plan-eng-review` — Engineering Manager, architecture, data flow
- `/investigate` — Debugger, root-cause analysis

### Design & UI
- `/design-review` — Design audit, visual quality check
- `/ui-ux-pro-max` — 67 UI styles, 161 color palettes, design system generator

### Workflow
- `/superpowers` — Agentic software development with multi-agent orchestration
- `/office-hours` — YC-style product brainstorming
- `/ship` — Release engineer, sync tests, push, open PR

## Awesome Claude Code Reference
See `.claude/skills/gstack/awesome-claude-code.md` for curated plugins list.

## Project Structure

| Service | Framework | Port | Purpose |
|---|---|---|---|
| `Server1_FastApi/` | FastAPI | 8080 | Main API |
| `FASTAPI_COMMUNITY/` | FastAPI | 8080 | Community hub |
| `server2/` | Flask | — | Legacy (migrating) |
| `server3/` | FastAPI | 8001 | Chat/email |
| `server4/` | FastAPI | — | Presentation/Pitch |
| `shared_security/` | — | — | Crypto/upload security |

## Key Commands

```bash
# Server4
cd server4 && python run.py              # Dev mode
python test_phase_f.py                    # Run tests
```

## Tech Stack
- FastAPI, Flask, MongoDB, Redis, Celery
- AI: OpenAI, DeepSeek, Mistral, Groq, Cloudflare Workers
- Image: Lucid, Phoenix, Flux