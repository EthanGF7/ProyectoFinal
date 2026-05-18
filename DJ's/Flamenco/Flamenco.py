#!/usr/bin/env python3
"""Flamenco DJ - Duende, Pasión y Algoritmo"""
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import core/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flamenco AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (default: auto-fallback from 8765)")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("DJ_PORT", 8765))

    here = Path(__file__).resolve().parent
    repo = here.parent
    base_dir = repo / "djs" / "Flamenco"

    run_dj("Flamenco", base_dir, port)