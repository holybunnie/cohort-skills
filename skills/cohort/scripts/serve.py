#!/usr/bin/env python3
"""Serve the COHORT HTML report on http://localhost:<port>/cohort-report.html."""

from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--dir", default=".", help="Directory containing cohort-report.html")
    p.add_argument("--once", action="store_true", help="Serve one request then exit (for tests)")
    args = p.parse_args(argv)

    serve_dir = Path(args.dir).resolve()
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(serve_dir), **kw)

    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://localhost:{args.port}/cohort-report.html"
        print(f"COHORT report served at {url}")
        print("Press Ctrl+C to stop.")
        if args.once:
            httpd.handle_request()
            return 0
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nshutting down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
