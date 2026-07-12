"""Shared site-path marker list for oxfordra.net-related hooks.

Single source of truth for what counts as "the website tree" -- ora-autonomy-gate.py
(Gate 2, human-confirmation boundary) and confidentiality-guard.py (egress leak-scan)
must agree on this list, or a path recognized by one but not the other creates a gap
where a write could slip past one gate but not the other. This IS a real, previously-
live gap: confidentiality-guard.py had already added the domain-form aliases
(oxfordra.net, oxfordra_net) that ora-autonomy-gate.py lacked -- a domain-named path
would be leak-scanned but not human-gated for a website write. Union of both hooks'
pre-existing lists as of 2026-07-12.

Stdlib only. ASCII-only.
"""

SITE_PATH_MARKERS = ("website-canonical", "oxford-site", "oxfordra.net", "oxfordra_net")
