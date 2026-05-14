#!/usr/bin/env python3
"""Run a local static server for the WP-04.1 outcome visualization prototype."""

from __future__ import annotations

import argparse
import http.server
import socketserver
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local server for outcome visualization prototype UI.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local HTTP server.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print("Outcome UI server started")
        print(f"Repository root: {repo_root}")
        print(f"Open: http://127.0.0.1:{args.port}/ui/outcome_visualization/index.html")
        try:
            import os

            os.chdir(repo_root)
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
