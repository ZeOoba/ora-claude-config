#!/usr/bin/env python3
r"""
apply-block-c-deal-scoring.py  (QUEUED change, authored 2026-06-06)

Adds a "C.5.5 - NEW-DEAL BOX SCREEN" subsection to ora-am-brief Block C
(Inbox Pre-Brief) so broker-submitted listings get an ORA buy-box screen
(SCREEN/WATCH/PASS) folded into the existing pre-brief email.

WHY: mirrors the validated deal-flow-triage rubric onto the inbox deals that
the weekly ora-deal-sourcing-scan (public-web) never sees (direct-broker /
pocket / pre-marketing listings). See:
  ~/.claude/queued-changes/2026-06-06_block-c-deal-box-scoring.md
  memory/event_log.md 2026-06-06

MECHANISM: the scheduler references the prompt by filePath, so this is a plain
DURABLE edit to that SKILL.md - NOT an app-closed registry edit. Idempotent:
re-running is a no-op if the marker is already present. Backs up first.
Fail-safe: aborts (no write) if the C.6 anchor is missing (structure changed).

USAGE:
  python apply-block-c-deal-scoring.py --dry-run     # preview only
  python apply-block-c-deal-scoring.py               # apply (writes a .bak first)

PRECONDITION FOR VALUE (not for applying): the M365 read connector must be
healthy so Block C actually pulls the inbox; validate on the next live AM run.
"""
import argparse
import datetime
import shutil
import sys
from pathlib import Path

# Windows consoles default to cp1252; the inserted block carries Unicode
# (em-dash, middot, box-drawing chars). Make all prints Unicode-safe so
# --dry-run and the success messages don't crash on encode.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL = Path(
    r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)"
    r"\Documents\Claude\Scheduled\ora-am-brief\SKILL.md"
)
MARKER = "## C.5.5"            # idempotency check (dash-agnostic)
ANCHOR = "## C.6"             # insert the block immediately before this header

BLOCK = r"""## C.5.5 — NEW-DEAL BOX SCREEN  (added 2026-06-06; box-scores broker-submitted listings)

For every message Block C classified as **Broker** that is submitting/forwarding a NEW acquisition listing or OM (the urgency-4 "broker submitting a new deal" hits in C.3, plus any message with a listing/OM attachment flagged in C.5), run a coarse ORA buy-box screen. This does NOT re-sweep the inbox — it operates ONLY on the messages already swept in C.1 and classified in C.2. Goal: catch and score the direct-broker-email / pocket / pre-marketing listings that the weekly `ora-deal-sourcing-scan` (public-web scan) never sees.

Rubric (mirror of the `deal-flow-triage` agent — keep in sync with `~/.claude/agents/deal-flow-triage.md`):
- ORA box: Class B/C shallow-bay **industrial/flex** · **$1-10M** · **sub-50,000 SF/building** · **OH/MD/IN/WI/MO/KS/TN**. Replacement-cost reference ~$85-$120/SF.
- For each broker-submitted listing, extract from the body: address & market, asset type, building SF, asking price, $/SF, any stated NOI/cap/occupancy. If economics are only in an attached PDF OM, mark "[PDF OM - open to screen]" and screen on the body.
- Verdicts: **SCREEN** (fits type+price+size+geo) · **WATCH** (borderline / a key figure missing — conservative, never a silent PASS) · **PASS** (cite the ONE controlling box dimension that fails). Mark unverifiable broker figures [UNVERIFIED]. Label $/SF on fixed thresholds: within ~$85-120 = "within replacement band"; up to ~10% over = "marginally above band, SCREEN ok, confirm vintage/class"; ~1.5x+ over = "ABNORMAL: ~Nx band, flag for class verification" and lean WATCH. Never silently drop a listing.
- Do NOT underwrite (no DSCR/LTV/IRR). Coarse box-fit only — real numbers are deal-recon -> acquisition-underwriting.
- De-dupe: cross-check each listing's address against the Notion Deal Sourcing Log (data source 9a6ae219-85a3-4621-899c-c757fd062f8b). If already logged by `ora-deal-sourcing-scan`, mark "[already in Sourcing Log]" and do not re-surface as new.

Render the result as a dedicated section in the C.6 output, placed immediately under RED FLAGS:
═══ NEW DEALS — BOX SCREEN ═══
[one line per broker-submitted listing: Broker | Address & Market | Type | SF | Ask | $/SF | VERDICT | one-line why | flags]
Recommended next: [top 1-3 SCREEN listings -> run deal-recon]   (omit the line if none)

If no broker-submitted listings in the window: omit this section entirely (do not print an empty block).

"""


def main():
    ap = argparse.ArgumentParser(description="Apply the queued Block C deal box-scoring patch.")
    ap.add_argument("--dry-run", action="store_true", help="preview without writing")
    args = ap.parse_args()

    if not SKILL.exists():
        sys.exit(f"ABORT: SKILL.md not found at {SKILL}")

    text = SKILL.read_text(encoding="utf-8")

    if MARKER in text:
        print("Already applied (C.5.5 marker present) — no-op.")
        return
    if ANCHOR not in text:
        sys.exit(
            f"ABORT: anchor '{ANCHOR}' not found in {SKILL.name}. "
            "Block C structure changed — review and apply manually."
        )

    new_text = text.replace(ANCHOR, BLOCK + ANCHOR, 1)

    if args.dry_run:
        print("[DRY RUN] Would insert this block immediately before the C.6 header:\n")
        print(BLOCK)
        print("[DRY RUN] No file written.")
        return

    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = SKILL.with_name(SKILL.name + f".bak-{ts}")
    shutil.copy2(SKILL, bak)
    SKILL.write_text(new_text, encoding="utf-8")

    print(f"APPLIED. Backup written to: {bak}")
    print("VERIFY: open the SKILL.md and confirm C.5.5 sits between C.5 and C.6.")
    print("SYNC:   keep the rubric aligned with ~/.claude/agents/deal-flow-triage.md.")
    print("VALIDATE: on the next live AM run once the M365 read connector is healthy.")


if __name__ == "__main__":
    main()
