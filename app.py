"""Vercel entrypoint: Vercel looks for a FastAPI `app` in a root app.py. The real app lives in src/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from offerlens.api import app  # noqa: E402

__all__ = ["app"]
