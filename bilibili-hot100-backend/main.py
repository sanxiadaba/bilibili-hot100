"""ASGI entry point kept for ``uvicorn main:app`` compatibility.

The implementation lives in the :mod:`hot100` package; this module only exposes
``app`` and a ``python main.py`` runner.
"""

from __future__ import annotations

import uvicorn

from hot100 import config
from hot100.api import app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)
