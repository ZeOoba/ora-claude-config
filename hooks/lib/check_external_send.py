#!/usr/bin/env python3
"""Outbound-action check for Hard Invariant 1, invoked by send-via-outlook.ps1 itself
right before it touches Outlook COM -- NOT by the PreToolUse shell-text gate.

WHY THIS EXISTS (OI-007, 2026-07-17): ora-autonomy-gate.py's Gate 1 detects an external
recipient by parsing the Bash command's literal TEXT. Adversarial review proved that
detection is structurally blind to value indirection -- a recipient built from a
PowerShell variable, string concatenation, or a file read never appears as a literal
email-shaped substring in the command text, so Gate 1 never fires and the send proceeds
completely unblocked, no override needed.

This script closes that gap by moving the check to the point where PowerShell has
ALREADY resolved $To/$Cc to their final, concrete string values -- indirection is
irrelevant here, because by this point there is no more indirection left to resolve.
Defense in depth, not a replacement: Gate 1 still runs first and catches the common
literal case cheaply; this is the backstop that cannot be evaded by construction tricks.

USAGE (called by send-via-outlook.ps1, not by a human):
    python check_external_send.py --session <id> --recipients addr1,addr2,...

Recipients here are the ALREADY-RESOLVED external addresses PowerShell is about to send
to -- the caller has already excluded internal (@oxfordra.net) addresses.

Exit 0  = authorized (a valid, session-matched, single-use token named every recipient;
          it has been CONSUMED as a side effect of this check -- see override_tokens.py's
          token_grants, "consume before granting").
Exit 1  = NOT authorized (no token, wrong session, wrong scope, expired, or a recipient
          this token doesn't name). The caller (send-via-outlook.ps1) must refuse to send.
Exit 3  = usage error (bad args) -- distinct from "not authorized" so a caller bug reads
          differently in the log than a genuine, working refusal.

Nothing here ever exits non-zero for an INTERNAL-only send: this script is only ever
invoked when the caller has already determined at least one recipient is external.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from override_tokens import token_grants  # noqa: E402
from email_send_tier import EXTERNAL_SEND, recipients_authorized  # noqa: E402


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--session", required=True)
    parser.add_argument("--recipients", required=True,
                        help="comma-separated list of EXTERNAL recipients about to be sent to")
    try:
        args = parser.parse_args()
    except SystemExit:
        return 3

    external = [r.strip() for r in args.recipients.split(",") if r.strip()]
    if not external:
        # Caller invoked this with an empty recipient list -- that's a caller bug (this
        # script is only meant to run when there IS at least one external recipient), not
        # something this check can authorize. Refuse rather than guess.
        sys.stderr.write("check_external_send: --recipients was empty; nothing to authorize\n")
        return 3

    fields = token_grants(
        args.session, EXTERNAL_SEND,
        extra_check=lambda f: recipients_authorized(f, external),
    )
    if fields is None:
        sys.stderr.write(
            "check_external_send: DENY - no valid allow-external-send token for session %s "
            "naming recipient(s): %s\n" % (args.session, ", ".join(external))
        )
        return 1

    sys.stderr.write(
        "check_external_send: ALLOW - session %s authorized to send to: %s (reason: %s)\n"
        % (args.session, ", ".join(external), fields.get("reason", "<none given>"))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
