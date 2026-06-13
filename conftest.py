"""Pytest bootstrap for the fab repo.

`fab` lives under ``src/`` and the ``services`` sidecar lives at the repo root.
Neither is guaranteed to be installed in the environment that runs the tests
(for example ``uv pip install pytest`` followed by ``uv run pytest`` installs
no project code). pytest auto-loads this root ``conftest.py`` before collecting
any tests, so inserting both directories here makes ``import fab`` and
``import services`` resolve regardless of install state or runner.

The ``[tool.pytest.ini_options] pythonpath`` setting in ``pyproject.toml`` does
the same thing when honoured; this file is the belt-and-braces guarantee.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for candidate in (ROOT / "src", ROOT):
    path = str(candidate)
    if path not in sys.path:
        sys.path.insert(0, path)
