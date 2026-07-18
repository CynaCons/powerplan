#!/usr/bin/env python3
"""Path-style MCP entrypoint: python powerplan_server.py

Prefer: python -m powerplan  (after pip install -e . or PYTHONPATH=repo root)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from powerplan.server import main

if __name__ == "__main__":
    asyncio.run(main())
