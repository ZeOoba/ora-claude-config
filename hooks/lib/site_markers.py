"""Shared site-path marker constants for oxfordra.net-related hooks.

Single source of truth for the CANONICAL REPO DIRECTORY names -- ora-autonomy-gate.py
(Gate 2, human-confirmation boundary) and confidentiality-guard.py (egress leak-scan)
both need to agree on these, or a path recognized by one but not the other creates a
gap where a write could slip past one gate but not the other.

IMPORTANT -- these two hooks do NOT match markers the same way, so this module
intentionally exports two separate tuples rather than one unified list (2026-07-12
code review finding, corrected same day):

- ora-autonomy-gate.py substring-matches against the WHOLE Bash command text and
  against file paths, as an immediate hard-block (exit 2) trigger. It must use ONLY
  SITE_PATH_MARKERS (the canonical local checkout directory names) -- these never
  appear incidentally in unrelated content. Domain-form aliases must NOT be given to
  this hook: "oxfordra.net" appears in every internal @oxfordra.net email address,
  every fetch of the live site, and any filename that merely mentions the domain,
  and unioning it in caused empirically-confirmed false-positive hard blocks on
  routine operations (including the pre-authorized internal fleet send).

- confidentiality-guard.py uses markers only inside path_egress_surface(), which
  classifies a single FILE PATH argument (never a whole Bash command) into an egress
  surface -- and even then only blocks if a confidential TERM also hits. That is
  narrow and low-risk enough to also carry SITE_DOMAIN_MARKERS (a literal domain
  alias as a path segment is a deliberate/rare signal there, not incidental content).

Stdlib only. ASCII-only.
"""

# Canonical local checkout directory names. Safe for whole-command / whole-path
# bare substring matching (ora-autonomy-gate.py).
SITE_PATH_MARKERS = ("website-canonical", "oxford-site")

# Domain-form aliases. Safe ONLY for a file-path-specific egress classifier that
# additionally requires a confidential-term hit before blocking (confidentiality-guard.py).
# Do NOT hand these to a whole-command substring matcher -- see module docstring.
SITE_DOMAIN_MARKERS = ("oxfordra.net", "oxfordra_net")
