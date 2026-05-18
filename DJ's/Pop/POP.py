#!/usr/bin/env python3
"""Pop DJ - Hits y Energía Comercial"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pop AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (default: auto-fallback from 8767)")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("DJ_PORT", 8767))

    here = Path(__file__).resolve().parent
    repo = here.parent
    base_dir = repo / "djs" / "Pop"

    run_dj("Pop", base_dir, port)