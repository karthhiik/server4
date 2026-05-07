# Server4 — Barise Presentation Service

FastAPI backend for AI-powered presentation generation.

## Boot

The FastAPI `app` instance lives at top-level `main.py` (**not** `app/main.py`).
The folder named `app/` contains routers/services, not the ASGI entry point.

### Canonical command

```powershell
cd D:\Desktop\New_Flask\FLASK\server4
python run.py
```

That wraps `uvicorn.run("main:app", host=0.0.0.0, port=8003, reload=True)`
and `chdir`s to `server4/` so module resolution works regardless of cwd.

### Direct uvicorn

```powershell
cd D:\Desktop\New_Flask\FLASK\server4
python -m uvicorn main:app --host 127.0.0.1 --port 8003 --reload
```

### Production

```powershell
python run.py --prod --host 0.0.0.0 --port 8003
```

## Common mistake

```
python -m uvicorn app.main:app ...   # ❌ WRONG — server4/app/main.py does not exist
```

The folder name `app/` is misleading. There is no `app.main` module. Always
use `main:app` from the `server4/` directory.

If you see:

```
ERROR: Error loading ASGI app. Could not import module "app.main".
```

…you ran the wrong command. Use `python run.py` instead.

## Health check

```powershell
curl http://127.0.0.1:8003/health
# {"status":"ok","service":"presentation-service","version":"0.2.0"}
```

## Layout

```
server4/
├── main.py              ← FastAPI app instance lives here (line 94)
├── run.py               ← Canonical dev/prod runner
├── app/
│   ├── routers/         ← HTTP routes
│   ├── services/        ← V4 pipeline, LLM router, image generator, storage
│   ├── api/             ← V2/V3 routes + websocket handlers
│   ├── models/          ← Pydantic schemas
│   ├── database.py
│   ├── config.py
│   └── middleware/
└── tests/
```

## Related docs

- [docs/founder-plans/01-asgi-import-fix.md](../docs/founder-plans/01-asgi-import-fix.md) — root-cause analysis.
- [docs/founder-plans/00-INDEX.md](../docs/founder-plans/00-INDEX.md) — full plan index.
