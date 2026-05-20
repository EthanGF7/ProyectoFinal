#!/usr/bin/env python3
"""Nexus DJ - Electronic, House, Techno"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (0 or omit = OS picks one)")
    args = parser.parse_args()

    if args.port is not None:
        port = args.port
    else:
        try:
            port = int(os.environ.get("DJ_PORT", 0))
        except ValueError:
            port = 0

    base_dir = Path(__file__).resolve().parent

    run_dj("Nexus", base_dir, port)
