#!/usr/bin/env python3
"""
Serve the generated SPA from output/ on the first free port in a range.

Defaults:
  start-port: 8080
  end-port:   8090

Examples:
  python3 serve_spa.py
  python3 serve_spa.py --output output --start-port 8080 --end-port 8090
"""

import argparse
import socket
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MAX_TCP_PORT = 65535


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(host: str, start_port: int, end_port: int) -> int | None:
    upper = min(end_port, MAX_TCP_PORT)
    for port in range(start_port, upper + 1):
        if is_port_free(host, port):
            return port
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve SPA output on the first available port.")
    parser.add_argument("--output", default="output", help="Directory to serve (default: output)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--start-port", type=int, default=8080,
                        help="First port to check (default: 8080)")
    parser.add_argument("--end-port", type=int, default=8090,
                        help="Last port to check (default: 8090, clamped to 65535)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    if not output_dir.is_dir():
        print(f"Error: output directory '{output_dir}' does not exist.", file=sys.stderr)
        return 1

    if args.start_port < 1:
        print("Error: --start-port must be >= 1", file=sys.stderr)
        return 1
    if args.end_port < args.start_port:
        print("Error: --end-port must be >= --start-port", file=sys.stderr)
        return 1

    if args.end_port > MAX_TCP_PORT:
        print(f"Note: --end-port {args.end_port} exceeds max TCP port {MAX_TCP_PORT}; using {MAX_TCP_PORT}.")

    port = find_free_port(args.host, args.start_port, args.end_port)
    if port is None:
        print(
            f"Error: no free port found in range {args.start_port}-{min(args.end_port, MAX_TCP_PORT)}.",
            file=sys.stderr,
        )
        return 1

    handler = partial(SimpleHTTPRequestHandler, directory=str(output_dir))
    server = ThreadingHTTPServer((args.host, port), handler)

    print(f"Serving '{output_dir}' on http://{args.host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
