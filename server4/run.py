"""
Server 4 — Presentation Service (Development Runner)

Usage:
    python run.py              # Dev mode (port 8003, auto-reload)
    python run.py --port 8004  # Custom port
    python run.py --prod       # Production mode (no auto-reload)
"""

import argparse
import os
import sys
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Server4 Presentation Service")
    parser.add_argument(
        "--port", type=int, default=8003, help="Port to run on (default: 8003)"
    )
    parser.add_argument(
        "--prod", action="store_true", help="Production mode (no auto-reload)"
    )
    parser.add_argument(
        "--no-reload", action="store_true", help="Development mode without auto-reload"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    # Always run from server4 directory so "main:app" resolves correctly
    import pathlib
    server4_root = pathlib.Path(__file__).resolve().parent
    os.chdir(server4_root)

    print(f"\n{'=' * 60}")
    print(f"  Barise Presentation Service (Server4)")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    print(f"  Health: http://{args.host}:{args.port}/health")
    reload_enabled = not args.prod and not args.no_reload
    mode = "production" if args.prod else ("development (auto-reload)" if reload_enabled else "development")
    print(f"  Mode: {mode}")
    print(f"{'=' * 60}\n")

    # Watch source only. Watching the server4 root also watches tests,
    # generated files, uploads, and export artifacts, which creates noisy
    # reload cascades and KeyboardInterrupt tracebacks during active editing.
    reload_dirs = [str(server4_root / "app")]

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=reload_enabled,
        reload_dirs=reload_dirs,
        reload_includes=["*.py"],
        reload_excludes=[
            "tests/*",
            "uploads/*",
            "docs/*",
            ".pytest_cache/*",
            "__pycache__/*",
            "*.pyc",
        ],
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
