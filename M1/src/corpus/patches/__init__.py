"""Code-authored evidence patches.

A patch authored in code is reviewable in a diff, testable, and reproducible: the same inputs
produce the same evidence. Patches from humans or vendors arrive as JSON in `M1/work/patches/`
instead. Both pass the identical adversarial verification before touching canonical state.
"""

from . import (p0001_us_equity_sources, p0002_crypto_event_sources,  # noqa: F401
               p0003_cme_partial, p0004_citation_replacements,
               p0005_nasdaq_universe, p0006_m2_qimb_kill,
               p0007_queue_identifiability,
               p0008_m2_passive_kill)

CODE_PATCHES = (p0001_us_equity_sources, p0002_crypto_event_sources, p0003_cme_partial,
                p0004_citation_replacements, p0005_nasdaq_universe, p0006_m2_qimb_kill,
               p0007_queue_identifiability,
               p0008_m2_passive_kill)
