"""Thin shim so validator rules can reuse the orchestrator's own schema contracts.

Keeping one implementation of the card/patch contract is the point: if the validator had its own
copy, a schema change could pass validation while the orchestrator rejected the same record.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ORCH = Path(__file__).resolve().parents[1] / "orchestrator"
if str(_ORCH) not in sys.path:
    sys.path.insert(0, str(_ORCH))

import patch  # noqa: E402,F401
import schemas  # noqa: E402,F401
