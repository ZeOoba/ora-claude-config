"""Shared WEBSITE_DEPLOY tier, used by BOTH enforcement points for Hard Invariant 2
(no oxfordra.net prod deploy without Gabriel's approval):

  1. ora-autonomy-gate.py (PreToolUse) -- shell-text detection of `netlify ... deploy
     ... --prod`. Fast, catches literal cases before the tool call even runs, but
     structurally blind to value indirection (splitting the invocation across two Bash
     calls, or referencing the binary via a variable) -- see OI-007.
  2. check_website_deploy.py -- the OUTBOUND-ACTION check, invoked by the netlify CLI
     wrapper (website-canonical/scripts/netlify-guard.js) right before it would exec the
     real netlify-cli. By the time a shell has actually launched the wrapper process,
     argv is the final, resolved argument list -- indirection that built the command is
     already collapsed, so this layer closes exactly the gap the shell-text layer cannot.

Same pattern as hooks/lib/email_send_tier.py for Gate 1 -- see that module's docstring
for the full defense-in-depth rationale. This module is simpler: a website deploy has no
per-recipient binding to check, only session-scoped, single-use authorization.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from override_tokens import Tier  # noqa: E402

WEBSITE_DEPLOY = Tier("allow-website-deploy", "website-deploy", 300, single_use=True)
