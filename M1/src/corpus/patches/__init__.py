"""Code-authored evidence patches.

A patch authored in code is reviewable in a diff, testable, and reproducible: the same inputs
produce the same evidence. Patches from humans or vendors arrive as JSON in `M1/work/patches/`
instead. Both pass the identical adversarial verification before touching canonical state.
"""

from . import p0001_us_equity_sources  # noqa: F401

CODE_PATCHES = (p0001_us_equity_sources,)
