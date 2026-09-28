"""Changelog/description-only skip gate for the scheduled eval-harness poll.

acquisition-underwriting/SKILL.md opens with frontmatter, an H1 intro and the inline changelog,
and states in that intro that "the body sections below are authoritative". Everything from the
FIRST `## ` heading onward (BODY TRIGGERS, ROUTING, STAGE -1 ... RCT) is treated as operative
doctrine. A doctrine-file change may skip the 18-agent replay ONLY when that operative region is
byte-identical (after line-ending normalization) between the last-checked snapshot and the
current file. Any doubt resolves to RUN.

Named residual risk: an operative rule pasted into the changelog prose above the first heading
would be skipped. That is accepted in exchange for not replaying on version-bump edits.

CLI: python doctrine_skip_gate.py --prior <snapshot> --current <SKILL.md>
     prints JSON {decision, reason}; exit 0 = SKIP, 10 = RUN (including every error path).
"""

import argparse
import json
import re
import sys
from collections import namedtuple

SKIP = "SKIP"
RUN = "RUN"

Verdict = namedtuple("Verdict", ["decision", "reason"])

_FIRST_SECTION = re.compile(r"^## ", re.MULTILINE)


def _normalize(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _operative_region(text):
    """Text from the first `## ` heading to end of file, or None if there is no such heading."""
    match = _FIRST_SECTION.search(text)
    return None if match is None else text[match.start():]


def classify(prior_text, current_text):
    prior = _normalize(prior_text or "")
    current = _normalize(current_text or "")
    if not prior.strip():
        return Verdict(RUN, "no prior snapshot to diff against")
    if prior == current:
        return Verdict(SKIP, "no content change after line-ending normalization")
    prior_ops = _operative_region(prior)
    current_ops = _operative_region(current)
    if prior_ops is None or current_ops is None:
        return Verdict(RUN, "no '## ' section heading found in one version -- cannot bound the preamble")
    if prior_ops != current_ops:
        return Verdict(RUN, "operative region (first '## ' heading onward) changed")
    return Verdict(SKIP, "all changes confined to frontmatter/intro/changelog above the first '## ' heading")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prior", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args(argv)
    try:
        try:
            with open(args.prior, encoding="utf-8") as f:
                prior = f.read()
        except FileNotFoundError:
            prior = ""
        with open(args.current, encoding="utf-8") as f:
            current = f.read()
        verdict = classify(prior, current)
    except Exception as e:  # any failure must fall to a full run, never a skip
        verdict = Verdict(RUN, f"gate error: {type(e).__name__}: {e}")
    print(json.dumps(verdict._asdict()))
    return 0 if verdict.decision == SKIP else 10


if __name__ == "__main__":
    sys.exit(main())
