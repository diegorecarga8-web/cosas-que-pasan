#!/usr/bin/env python3
"""Punto de entrada de Cosas que pasan 2. Ejecuta: python cqp.py --help"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cqp2.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
