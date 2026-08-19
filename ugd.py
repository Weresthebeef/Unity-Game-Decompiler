# Unity Game Decompiler (ugd)
# From-scratch implementation - NO stolen code
# MIT License - Copyright (c) 2026 Gc.idk

"""
Main entry point for the Unity Game Decompiler.

This is a thin wrapper around ugd.cli. Run with:
    python ugd.py [options] path
    python -m ugd.cli [options] path
"""
import sys

from ugd.cli import main

if __name__ == '__main__':
    sys.exit(main())