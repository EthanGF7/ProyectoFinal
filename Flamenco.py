#!/usr/bin/env python3
"""Flamenco DJ - Duende, Pasión y Algoritmo"""
import argparse
import os
import sys
from pathlib import Path

# Añadir DJ's/ al path para importar core/
ROOT = Path(__file__).resolve().parent.parent   # -> DJ's/
sys.path.insert(0, str(ROOT))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flamenco AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (default: auto-fallback from 8765)")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("DJ_PORT", 8765))
    base_dir = ROOT / "djs" / "Flamenco"           # DJ's/djs/Flamenco
    src_dir  = Path(__file__).resolve().parent / "src"  # DJ's/Flamenco/src

    run_dj("Flamenco", base_dir, port, src_dir)
