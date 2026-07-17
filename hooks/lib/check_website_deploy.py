#!/usr/bin/env python3
"""Outbound-action check for Hard Invariant 2 (Gate 2a: oxfordra.net prod deploy),
invoked by website-canonical's netlify CLI wrapper (scripts/netlify-guard.js) right
before it would exec the real netlify-cli -- NOT by the PreToolUse shell-text gate.

WHY THIS EXISTS (OI-007, 2026-07-17): ora-autonomy-gate.py's Gate 2a detects a
`netlify ... deploy ... --prod` invocation by parsing the Bash command's literal TEXT.
Adversarial review proved that is structurally blind to value indirection -- splitting
the invocation across two Bash calls (build an executable reference in one, invoke it
in a second), or renaming/wrapping the binary, reaches exit 0 unblocked, no override
needed. This script closes that gap at the point where a shell has actually launched
the wrapper process: by then, argv is the final, resolved argument list. Whatever
indirection built the command is already collapsed -- there is no more text left to
obfuscate.

USAGE (called by scripts/netlify-guard.js, not by a human):
    python check_website_deploy.py --session <id>

Session id arrives as a CLI argument (not stdin, unlike check_external_send.py): it is
an internal env-var value (a UUID this process itself controls), never attacker-
influenced arbitrary text like an email address, so the argument-marshaling risk that
motivated moving RECIPIENTS to stdin does not apply here.

Exit 0  = authorized (a valid, session-matched, single-use token; CONSUMED as a side
          effect of this check -- see override_tokens.py's token_grants).
Exit 1  = NOT authorized (no token, wrong session, wrong scope, or expired). The caller
          (netlify-guard.js) must refuse to deploy.
Exit 3  = usage error (bad args).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from override_tokens import token_grants  # noqa: E402
from website_deploy_tier import WEBSITE_DEPLOY  # noqa: E402


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--session", required=True)
    try:
        args = parser.parse_args()
    except SystemExit:
        return 3

    fields = token_grants(args.session, WEBSITE_DEPLOY)
    if fields is None:
        sys.stderr.write(
            "check_website_deploy: DENY - no valid allow-website-deploy token for "
            "session %s\n" % args.session
        )
        return 1

    sys.stderr.write(
        "check_website_deploy: ALLOW - session %s authorized to deploy (reason: %s)\n"
        % (args.session, fields.get("reason", "<none given>"))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
