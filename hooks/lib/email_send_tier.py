"""Shared EXTERNAL_SEND tier + recipient-binding, used by BOTH enforcement points for
Hard Invariant 1 (no external email without Gabriel's approval):

  1. ora-autonomy-gate.py (PreToolUse) -- shell-text detection. Fast, catches literal
     cases before the tool call even runs, but structurally blind to value indirection
     (a variable/file-sourced recipient) -- see OI-007 / the gate's own docstring.
  2. check_external_send.py -- the OUTBOUND-ACTION check, invoked by
     send-via-outlook.ps1 itself right before it touches Outlook COM. By the time
     PowerShell has bound $To/$Cc, any indirection (variable, concatenation, file read)
     has ALREADY been resolved to a concrete string -- so this layer closes exactly the
     gap the shell-text layer cannot, and is immune to how the recipient value was
     constructed.

Defense in depth, not redundancy: layer 1 fails fast and cheaply for the common case;
layer 2 is the one that actually can't be evaded, and is the backstop if layer 1 is ever
bypassed (its own bugs, a matcher gap not yet found, or exactly the indirection ceiling
this module exists to close).

Both layers MUST use the identical Tier definition and recipient-binding rule, or they
silently diverge on what "authorized" means -- exactly the drift risk that motivated
hooks/lib/override_tokens.py in the first place. This module is that shared point for the
EXTERNAL_SEND tier specifically (override_tokens.py itself stays domain-agnostic; it
knows nothing about email).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from override_tokens import Tier  # noqa: E402

INTERNAL_DOMAIN = "@oxfordra.net"

# Same tier both layers must use: scope, TTL, single-use. requires_extra_check tells
# override_tokens.token_grants() to REFUSE (not silently skip) if a caller forgets to
# supply the recipient-binding predicate below.
EXTERNAL_SEND = Tier("allow-external-send", "external-send", 300, single_use=True,
                      requires_extra_check=True)


def is_external(address):
    """True if `address` is not an @oxfordra.net recipient. Case-insensitive."""
    return not address.lower().endswith(INTERNAL_DOMAIN)


def recipients_authorized(fields, external):
    """Every external recipient of the send must be named in the token's `recipients:`
    field. A token approving a send to one counterparty does not authorize a send to
    another -- this is the extra_check both enforcement points pass to token_grants."""
    raw = fields.get("recipients")
    if not raw:
        return False
    allowed = {r.strip().lower() for r in raw.split(",") if r.strip()}
    if not allowed:
        return False
    return all(r.lower() in allowed for r in external)
