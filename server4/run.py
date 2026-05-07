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
    print(f"  Mode: {'production' if args.prod else 'development (auto-reload)'}")
    print(f"{'=' * 60}\n")

    # Reload only server4 files, not the entire workspace
    reload_dirs = [str(server4_root / "app"), str(server4_root)]

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=not args.prod,
        reload_dirs=reload_dirs,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
