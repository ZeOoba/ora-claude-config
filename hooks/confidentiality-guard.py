#!/usr/bin/env python3
"""ORA confidentiality EGRESS guard (PreToolUse). FAIL-CLOSED.

Blocks confidential deal identifiers (every active deal defined in
confidential-terms.json) from crossing any EXTERNAL egress boundary:

  * public website repo writes        (oxford-site / oxfordra.net / website-canonical)
  * mirror / build output             (.../dist/, paths containing 'mirror')
  * /outputs/ artifacts               (.pptx .docx .pdf .html .htm .csv)
  * Notion create/update tool calls   (mcp__*notion-(create|update|append|duplicate|move|comment)*)
  * Outlook send/draft/forward calls  (mcp__*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)*)
  * egress shell commands             (git push / curl / wget / scp / rsync-remote / Invoke-WebRequest)

The deal legitimately exists INSIDE the brain, so INTERNAL reads/writes/commands are
allowed -- only egress is blocked. This is the whole point: confidentiality is an
egress property, not a content property.

FAIL-CLOSED (inverts the prior fail-open guard, for egress only): if the tool call is an
egress surface (or an egress-capable tool we cannot parse), and we cannot prove it is
clean, we BLOCK. Terms-file unreadable -> BLOCK. Payload unparseable -> BLOCK.

Coverage note (I5 -- no silent half-coverage): a `git push` payload does not contain the
repo contents, so this hook scans only the command text. Deep confidential-content
checking of what a push would publish is enforced by the build-time grep gate on the
mirror/site `dist/` (Phase 2/6), not here.

Exit 0 = allow. Exit 2 = block (PreToolUse convention).
"""
import sys, os, json, re

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")

SITE_MARKERS = ("oxford-site", "oxfordra.net", "oxfordra_net", "website-canonical")
ARTIFACT_EXT = (".pptx", ".docx", ".pdf", ".html", ".htm", ".csv")
BUILD_MARKERS = ("/dist/", "\\dist\\", "/outputs/", "\\outputs\\", "mirror")

NOTION_WRITE = re.compile(r"notion[-_]?(create|update|append|duplicate|move|comment)", re.I)
OUTLOOK_SEND = re.compile(r"outlook_(send|create_draft|send_draft|forward|reply)", re.I)
EGRESS_BASH = re.compile(
    r"\bgit\s+push\b|\bcurl\b|\bwget\b|\bscp\b|\brsync\b\s+\S+::|"
    r"invoke-webrequest|invoke-restmethod|\bnetlify\b.*\bdeploy\b|\bwrangler\b.*\b(deploy|publish)\b|"
    r"send-via-outlook\.ps1",  # the SOLE live COM send path IS egress (review finding 2026-06-11)
    re.I,
)


def block(reason):
    sys.stderr.write("BLOCKED (confidentiality, fail-closed): %s\n" % reason)
    sys.exit(2)


def load_terms():
    with open(TERMS_FILE, encoding="utf-8") as f:
        return json.load(f)


def find_hit(text, terms):
    """Return (deal_label, term) on first confidential hit in `text`, else None."""
    if not text:
        return None
    low = text.lower()
    for key, deal in terms.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        for t in deal.get("always", []):
            if t and t.lower() in low:
                return (deal.get("label", key), t)
        reqs = [r.lower() for r in deal.get("context_requires_any", [])]
        if reqs and any(r in low for r in reqs):
            for t in deal.get("context", []):
                if t and t.lower() in low:
                    return (deal.get("label", key), t)
    return None


def collect_text(obj):
    """Flatten any nested tool_input into one scannable string."""
    parts = []
    if isinstance(obj, str):
        parts.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            parts.append(collect_text(v))
    elif isinstance(obj, list):
        for v in obj:
            parts.append(collect_text(v))
    elif obj is not None:
        parts.append(str(obj))
    return " ".join(p for p in parts if p)


def path_egress_surface(path):
    pl = (path or "").lower()
    if any(m in pl for m in SITE_MARKERS):
        return "public website repo"
    if pl.endswith(ARTIFACT_EXT):
        return "output artifact (%s)" % os.path.splitext(pl)[1]
    if any(m in pl for m in BUILD_MARKERS):
        return "mirror/build output"
    return None


def main():
    # 1) If we cannot load the term list, we cannot evaluate confidentiality -> fail closed.
    try:
        terms = load_terms()
    except Exception as e:
        block("confidential-terms.json unreadable (%s); cannot verify egress safety." % e)

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        block("tool-call payload could not be parsed; cannot verify egress safety.")

    tool = (data.get("tool_name") or data.get("tool") or "")
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {"_": ti}

    # --- Determine egress surface + scan text -----------------------------------------
    surface = None
    scan_text = None

    # File-writing tools: only egress when the target path is an external surface.
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        surface = path_egress_surface(path)
        if surface:
            # scan the content being written/inserted (not old_string)
            pieces = [ti.get("content", ""), ti.get("new_string", ""), ti.get("new_source", "")]
            for ed in ti.get("edits", []) or []:
                if isinstance(ed, dict):
                    pieces.append(ed.get("new_string", ""))
            scan_text = " ".join(str(p) for p in pieces if p)
            if not scan_text:
                # egress write we cannot read -> fail closed
                block("write to %s but content could not be extracted." % surface)

    # Notion writes: the whole payload is bound for Notion.
    elif NOTION_WRITE.search(tool):
        surface = "Notion write (%s)" % tool
        scan_text = collect_text(ti)

    # Outlook send/draft/forward/reply: the whole payload is bound for email.
    elif OUTLOOK_SEND.search(tool):
        surface = "Outlook send/draft (%s)" % tool
        scan_text = collect_text(ti)

    # Shell: only egress commands are scanned (internal commands may reference the deal).
    elif tool == "Bash":
        cmd = ti.get("command", "") or ""
        if EGRESS_BASH.search(cmd):
            surface = "egress shell command"
            scan_text = cmd

    # Not an egress surface -> allow.
    if surface is None:
        sys.exit(0)

    # --- Enforce -----------------------------------------------------------------------
    hit = find_hit(scan_text, terms)
    if hit:
        label, term = hit
        block("'%s' identifier ('%s') would cross egress surface [%s]. "
              "This deal must not reach any external surface until closing. "
              "Keep it on internal/local paths only." % (label, term, surface))

    sys.exit(0)


if __name__ == "__main__":
    main()
