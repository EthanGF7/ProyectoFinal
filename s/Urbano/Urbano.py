#!/usr/bin/env python3
"""Urbano DJ - Reggaeton y Trap"""
import argparse
import os
import sys
from pathlib import Path

# Permite importar core.server desde DJ's/core/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.server import run_dj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urbano AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (0 or omit = OS picks one)")
    args = parser.parse_args()

    # Prioridad: --port  > env DJ_PORT > 0 (dinámico)
    if args.port is not None:
        port = args.port
    else:
        try:
            port = int(os.environ.get("DJ_PORT", 0))
        except ValueError:
            port = 0

    # base_dir = la propia carpeta del DJ (donde están canciones/, json/, etc.)
    base_dir = Path(__file__).resolve().parent

    run_dj("Urbano", base_dir, port)
