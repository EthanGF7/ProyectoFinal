#!/usr/bin/env python3
"""Urbano DJ - Reggaeton y Trap"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urbano AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (default: dynamic from environment)")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("DJ_PORT", 0))

    here = Path(__file__).resolve().parent
    repo = here.parent
    base_dir = repo / "djs" / "Urbano"

    run_dj("Urbano", base_dir, port)