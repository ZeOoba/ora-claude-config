#!/usr/bin/env python3
"""ORA confidentiality EGRESS guard (PreToolUse). FAIL-CLOSED.

Blocks confidential deal identifiers (every active deal defined in
confidential-terms.json) from crossing any EXTERNAL egress boundary:

  * public website repo writes        (oxford-site / oxfordra.net / website-canonical)
  * mirror / build output             (.../dist/, paths containing 'mirror')
  * /outputs/ artifacts               (.pptx .docx .pdf .html .htm .csv)
  * Notion create/update tool calls   (mcp__*notion-(create|update|append|duplicate|move|comment)*)
  * Outlook send/draft/forward calls  (mcp__*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)*)
  * live M365 / HubSpot send surfaces (outlook mail + calendar, Teams, SharePoint uploads,
                                       HubSpot content writes -- MCP_SEND_SURFACES, 2026-09-30)
  * egress shell commands             (git push / curl / wget / scp / rsync-remote / Invoke-WebRequest /
                                       gh pr|issue|gist|release|api|repo edit, incl. the files gh
                                       reads a body from -- see GH_EGRESS, 2026-11-08)

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

Roster-freshness tripwire (2026-07-08 audit finding): FAIL-CLOSED covers the roster being
ABSENT/unreadable, but NOT the roster being STALE-BUT-PRESENT -- the file parses fine, yet nobody
has re-confirmed the active-deal list lately (a closed deal never retired, or a NEW confidential
deal not yet added). The second case is INVISIBLE to fail-closed: there are no terms to match, so
the deal leaks. A stale `_meta.roster_last_verified` (> STALENESS_THRESHOLD_DAYS old) therefore
makes the guard surface a loud, one-time-per-session ADVISORY (plus a durable state breadcrumb)
instead of trusting the snapshot silently -- per Invariant 3 ("verify before naming any deal
externally -- if unverifiable, ask"). Staleness WARNS, it does NOT hard-block: the roster is
present, only possibly-incomplete, and freezing all egress forever would be disproportionate. Only
the no-hit clean-egress path (the exact path a missing deal would slip through) carries the advisory.

Exit 0 = allow. Exit 2 = block (PreToolUse convention). The stale-roster advisory rides on the
allow path (exit 0 + stderr) -- it never flips an allow into a block or vice-versa.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree add` never
checks it out into a fresh linked worktree. load_terms() falls back to the MAIN worktree's
copy (resolved via `git rev-parse --git-common-dir`, shared by every worktree of the same
repo) when this checkout's own copy is missing or unreadable and no explicit
CONFIDENTIAL_TERMS_FILE_OVERRIDE is set. Still fail-closed if the file is unreadable in BOTH
places (2026-07-12, mirrors the same fix in git-prepush-confidential-scan.py).
"""
import sys, os, json, re, datetime, subprocess, base64, html, io, zipfile, unicodedata, functools, time, glob

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(HOOK_DIR, "lib")
sys.path.insert(0, LIB_DIR)
try:
    from site_markers import SITE_PATH_MARKERS, SITE_DOMAIN_MARKERS  # noqa: E402
    SITE_MARKERS = SITE_PATH_MARKERS + SITE_DOMAIN_MARKERS
except Exception:
    # This hook is FAIL-CLOSED (see module docstring) -- an import failure must
    # never silently degrade it to fail-open. Fallback matches site_markers.py's
    # current combined value, so a missing/broken shared module keeps this guard
    # functioning at its last-known-good marker set instead of crashing past the
    # module-level import (which would exit 1 = non-blocking = a leak).
    SITE_MARKERS = ("oxford-site", "oxfordra.net", "oxfordra_net", "website-canonical")
# Test-only override (2026-07-09), same pattern as shared-checkout-guard.py's
# SHARED_CHECKOUT_REPOS env var: unset in every real session, so production behavior is
# byte-identical. Lets test-confidentiality-guard.py point this subprocess at a synthetic
# terms file when the live roster has zero active deals, without touching the real one.
TERMS_FILE_OVERRIDE = os.environ.get("CONFIDENTIAL_TERMS_FILE_OVERRIDE")
TERMS_FILE = TERMS_FILE_OVERRIDE or os.path.join(HOOK_DIR, "confidential-terms.json")

ARTIFACT_EXT = (".pptx", ".docx", ".pdf", ".html", ".htm", ".csv")
BUILD_MARKERS = ("/dist/", "\\dist\\", "/outputs/", "\\outputs\\", "mirror")

NOTION_WRITE = re.compile(r"notion[-_]?(create|update|append|duplicate|move|comment)", re.I)
# Composio-era pattern, kept verbatim so every name it ever matched still classifies.
OUTLOOK_SEND = re.compile(r"outlook_(send|create_draft|send_draft|forward|reply)", re.I)

# --- Live M365 / HubSpot send surfaces (2026-09-30) ----------------------------------------------
# Composio is gone; the live connector's tools are lowercase (mcp__<uuid>__outlook_send_mail ...),
# and OUTLOOK_SEND above missed the reply drafts, update_draft and every calendar/Teams/SharePoint/
# HubSpot write. Rule for inclusion: the tool carries free text that leaves the machine for a
# recipient or a service outside the brain. Per tool:
#   INCLUDED
#   outlook_send_mail / send_draft / forward_mail ........ outbound mail (send_draft and forward_mail
#       carry an id plus an optional note; the body they send is NOT in the payload -- see RESIDUAL)
#   outlook_create_draft / create_reply_draft / create_reply_all_draft / update_draft
#       ........ draft content that one send_draft call puts on the wire
#   outlook_set_vacation ....... the auto-reply text goes to every external sender (externalAudience)
#   outlook_create_event / update_event ........ an invite with attendees IS a send (subject, body,
#       location reach every attendee)
#   outlook_respond_to_event ... the optional comment is mailed to the organizer
#   outlook_delete_event ....... the optional comment (max 1024, plain text) is INCLUDED IN THE
#       CANCELLATION EMAIL to attendees when the user is the organizer (live schema, 2026-10-01)
#   teams_send_chat_message / send_channel_message / reply_channel_message ........ outbound messages
#   teams_create_chat .......... the group topic is shown to every member
#   sharepoint_upload_file / update_file ........ file content written to a shareable library
#   HubSpot manage_crm_objects . CRM records in a third-party SaaS
#   HubSpot manage_blog_post / manage_landing_page / manage_website_page ........ PUBLIC web content
#   HubSpot manage_campaign_objects / manage_segment ........ free-text names, notes, audiences,
#       filter expressions stored in the SaaS
#   HubSpot manage_aeo_prompts . CREATE sends promptTexts to external AI assistants
#   HubSpot manage_social_posts ........ content/title published to the firm's PUBLIC social channels
#       (audit finding 2026-11-08; every call is scanned, previews included)
#   Notion notion-send-message-to-session / notion-spawn-session ........ message / initial_message
#       text goes to a Notion Custom Agent (NOTION_WRITE predates these and misses them)
#   EXCLUDED
#   Notion notion-upload-skill ........ payload is ids + a checksum; the archive bytes go by an
#       out-of-band PUT (a Bash curl, which EGRESS_BASH scans as command text only)
#   outlook_email_search / calendar_search / find_available_time, teams_list_*, chat_message_search,
#       sharepoint_search / folder_search, read_resource, search_people, get_me, HubSpot get_* /
#       search_* / query_crm_data ........ reads: a term there is a query, not egress
#   HubSpot manage_saved_reports (LIST/FETCH only), manage_aeo_recommendations (LIST/DETAIL;
#       START_ACTION is a documented no-op), manage_onboarding (enum goal) ........ no free text out
#   outlook_create_filter / create_label / update_label / modify_* / trash / delete_* EXCEPT
#       delete_event (INCLUDED above) ........ mailbox housekeeping; the live filter tool cannot
#       forward or redirect
#   sharepoint_rename_item / create_folder / copy_item / move_item / delete_item ........ names and
#       ids inside the tenant, no content (see RESIDUAL: a name is still text)
#   import-claude-design-from-url (HubSpot, Netlify) ........ content by reference only (a URL)
# RESIDUAL (not closable from a payload scan): outlook_send_draft / forward_mail and reply drafts put
# text on the wire that is not in the payload (the stored draft, the forwarded/quoted original);
# SharePoint names via rename/create_folder; binary uploads that are neither text nor zip (PDF
# streams are compressed) are scanned only as raw bytes.
#
# MATCHER CONTRACT: the settings.json PreToolUse matcher for this hook must contain, verbatim, the
# alternative "mcp__.*<pattern>.*" for EVERY pattern below (test-confidentiality-guard.py asserts
# it, and generates tool names from each pattern's alternatives to check routing). The patterns
# added 2026-09-30 are case-SENSITIVE, like the matcher, so the two agree exactly; NOTION_WRITE and
# OUTLOOK_SEND keep their historical re.I (the matcher routes their lowercase forms and the
# Composio-era uppercase OUTLOOK_* forms; other case mixes are classified here but not routed).
OUTLOOK_MAIL = re.compile(
    r"outlook_(send_mail|send_draft|forward_mail|create_draft|create_reply_draft|"
    r"create_reply_all_draft|update_draft|set_vacation)")
OUTLOOK_CALENDAR = re.compile(r"outlook_(create_event|update_event|respond_to_event|delete_event)")
TEAMS_SEND = re.compile(
    r"teams_(send_chat_message|send_channel_message|reply_channel_message|create_chat)")
SHAREPOINT_WRITE = re.compile(r"sharepoint_(upload_file|update_file)")
HUBSPOT_WRITE = re.compile(
    r"__manage_(crm_objects|blog_post|landing_page|website_page|campaign_objects|segment|"
    r"aeo_prompts|social_posts)")
NOTION_AGENT = re.compile(r"notion-(send-message-to-session|spawn-session)")

# Order is the old if/elif order (Notion, then Outlook) followed by the new surfaces; the first match
# names the surface in the block message. Every one scans the WHOLE tool_input.
MCP_SEND_SURFACES = (
    (NOTION_WRITE, "Notion write"),
    (OUTLOOK_SEND, "Outlook send/draft"),
    (OUTLOOK_MAIL, "Outlook send/draft"),
    (OUTLOOK_CALENDAR, "Outlook calendar invite/response"),
    (TEAMS_SEND, "Teams message"),
    (SHAREPOINT_WRITE, "SharePoint content write"),
    (HUBSPOT_WRITE, "HubSpot write"),
    (NOTION_AGENT, "Notion agent message"),
)
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def classify_tool(tool):
    """Surface label for a tool whose WHOLE payload is bound for an external service, else None.
    File tools and Bash are classified by their target / command in main(), never here."""
    if not isinstance(tool, str) or tool in FILE_TOOLS or tool == "Bash":
        return None
    for rx, label in MCP_SEND_SURFACES:
        if rx.search(tool):
            return "%s (%s)" % (label, tool)
    return None


# ------------------------------------------------------------------------------------------------
# EGRESS TOOLS BEYOND Bash / Edit / Write (cc-audit-army 2026-11-09, HIGH 1 + HIGH 2)
#
# Before this block the guard classified only Bash, the native file tools and MCP_SEND_SURFACES;
# everything else hit "Not an egress surface -> allow". Live, that let these reach an external
# surface unscanned: a Desktop Commander / terminal-panel / PowerShell `curl -d`, a Desktop
# Commander write into the site repo or /outputs/, an Artifact publish (claude.ai page plus every
# local file it uploads), Artifact database rows and comment replies, Claude Docs writes, browser
# form input / typing / scripted fetches / navigation URLs, and Excel writes into an egress path.
#
# Kept SEPARATE from MCP_SEND_SURFACES on purpose: that table is pinned verbatim into the
# pre.confidentiality-guard settings matcher and its prefix(alt|alt) shape is generator-tested.
# These surfaces need ACTION-aware classification (an Artifact read or a browser screenshot is
# not egress) and some carry their content by local file reference, which must be read.
# They are routed by their own wiring row, pre.confidentiality-guard-egress-tools.
#
# Self-contained (no tool_call_paths import) so a broken shared lib can never turn this
# fail-closed guard into an import-time exit 1 (= non-blocking = fail-open).
# ------------------------------------------------------------------------------------------------
_SHELL_SUFFIXES = ("start_process", "interact_with_process", "run_in_terminal")
_DC_WRITE_SUFFIXES = ("write_file", "edit_block", "write_pdf")
_DC_PATH_FIELDS = ("file_path", "path", "output_path", "outputPath")
DOCS_WRITE = re.compile(r"^mcp__[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}__(batch|update|create)$")
BROWSER_TOOL = re.compile(r"^mcp__.*(claude-in-chrome|Claude_Browser)__"
                          r"(form_input|computer|javascript_tool|navigate|browser_batch|"
                          r"upload_image|file_upload)$")
ARTIFACT_READ_ACTIONS = frozenset(("read", "list", "open", "pin", "unpin", "quickstart", "delete"))
ARTIFACT_DATA_READ_ACTIONS = frozenset(("get", "list", "query", "profiles", "delete"))
ARTIFACT_COMMENT_READ_ACTIONS = frozenset(("read", "watch", "resolve"))
# Tools whose payload may name local files that leave the machine; any string value that is an
# existing local file is read and scanned (schemas vary: path, paths, file_path, imagePath...).
FILE_CARRYING = re.compile(r"(upload_image|file_upload)$")
EXCEL_READ = re.compile(r"^mcp__excel__(read_|get_|validate_)")
# Local files an egress call uploads are read with this cap per call (shares the decode budget).
FILE_READ_MAX_FILES = 200


def _mcp_suffix(tool, suffixes):
    return isinstance(tool, str) and tool.startswith("mcp__") and tool.endswith(suffixes)


def is_shell_tool(tool):
    return tool in ("Bash", "PowerShell") or _mcp_suffix(tool, _SHELL_SUFFIXES)


def shell_command(tool, ti):
    return ti.get("input") if _mcp_suffix(tool, ("interact_with_process",)) else ti.get("command")


def classify_extra(tool, ti, cwd=None):
    """Surface label for an action-aware send surface outside MCP_SEND_SURFACES, else None."""
    if not isinstance(tool, str):
        return None
    action = ti.get("action")
    if action is not None and not isinstance(action, str):
        raise ValueError("action is not a string")
    act = (action or "").strip().lower()
    # DENY-LIST of known READ / housekeeping actions; every other action -- including one a
    # future tool version adds -- is treated as egress (REFUTE 2026-11-09: an allow-list of
    # write actions failed open on any unknown action).
    if tool == "Artifact":
        return None if act in ARTIFACT_READ_ACTIONS else "Artifact publish/upload"
    if tool == "ArtifactData":
        return None if act in ARTIFACT_DATA_READ_ACTIONS else "Artifact database write"
    if tool == "ArtifactComments":
        return None if act in ARTIFACT_COMMENT_READ_ACTIONS else "Artifact comment"
    if DOCS_WRITE.match(tool):
        return "Claude Docs write (%s)" % tool
    m = BROWSER_TOOL.match(tool)
    if m:
        if m.group(2) == "computer" and act not in ("type", "key"):
            return None  # clicks, scrolls, screenshots carry no text to a page
        return "browser input (%s)" % tool
    if tool.startswith("mcp__excel__") and not EXCEL_READ.match(tool):
        path = ti.get("filepath")
        if path is not None and not isinstance(path, str):
            raise ValueError("Excel filepath is not a string")
        path = resolve_against(path, cwd)
        return ("Excel write into %s" % path_egress_surface(path)) if path_egress_surface(path) else None
    return None


def _resolve_local(path, base):
    if not isinstance(path, str) or not path.strip():
        raise ValueError("file reference is not a non-empty string")
    return path if os.path.isabs(path) else os.path.join(base or os.getcwd(), path)


def local_file_texts(paths, base, budget):
    """Readable text of every local file (or directory tree) an egress call uploads.
    RAISES on anything unreadable, missing, or over budget -- main() blocks on that."""
    texts, count = [], 0

    def _walk(full):
        # LAZY: the cap and deadline apply while listing, not after a full os.walk (review
        # 2026-11-09: a publish of a huge directory ran past any hook timeout before the cap).
        if not os.path.isdir(full):
            yield full
            return
        for d, _, fs in os.walk(full):
            _check_deadline()
            for f in fs:
                yield os.path.join(d, f)

    for p in paths:
        for f in _walk(_resolve_local(p, base)):
            count += 1
            if count > FILE_READ_MAX_FILES:
                raise ValueError("too many files to scan")
            _check_deadline()
            with open(f, "rb") as fh:
                blob = fh.read(max(budget[0], 0) + 1)
            texts.extend(_blob_texts(blob, budget))
    return texts


def artifact_upload_refs(ti, cwd):
    """(local file paths, base dir) an Artifact publish sends. Server-side copies
    ({artifact, path}) and removals (null) carry no local content."""
    base = ti.get("root")
    base = _resolve_local(base, cwd) if base else cwd
    refs = []
    if ti.get("file_path") is not None:
        refs.append(ti.get("file_path"))
    if isinstance(ti.get("file_paths"), list):
        refs.extend(ti["file_paths"])
    files = ti.get("files")
    if isinstance(files, dict):
        for v in files.values():
            if v is None:
                continue
            if isinstance(v, dict):
                # Read `from` WHENEVER present, even beside `artifact` (REFUTE 2026-11-09 decoy).
                if v.get("from") is not None:
                    refs.append(v.get("from"))
                elif "artifact" not in v:
                    raise ValueError("files entry has neither from nor artifact")
                continue
            refs.append(v)
    elif isinstance(files, list):
        refs.extend(e.get("path") if isinstance(e, dict) else e for e in files)
    elif files is not None:
        raise ValueError("unrecognised files shape")
    return refs, base


def extra_scan_text(tool, ti, cwd):
    """Everything a classify_extra surface sends, as one string. RAISES when part of it cannot be
    read; main() blocks on that (fail closed)."""
    views = [mcp_scan_text(ti)]
    budget = [SCAN_MAX_DECODED_BYTES]
    if tool == "Artifact":
        refs, base = artifact_upload_refs(ti, cwd)
        views.extend(local_file_texts(refs, base, budget))
    elif tool == "ArtifactData":
        refs = [ti.get("file_path")] if ti.get("file_path") is not None else []
        for w in ti.get("writes") or []:
            if isinstance(w, dict) and w.get("file_path") is not None:
                refs.append(w["file_path"])
        views.extend(local_file_texts(refs, cwd, budget))
    elif FILE_CARRYING.search(tool):
        refs = [s for s in _strings(ti) if _looks_local_file(s, cwd)]
        views.extend(local_file_texts(refs, cwd, budget))
    return "\n".join(v for v in views if v)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _looks_local_file(s, cwd):
    try:
        return len(s) < 1024 and os.path.isfile(_resolve_local(s, cwd))
    except Exception:
        return False


def resolve_against(path, cwd):
    """A relative tool path resolved against the payload's cwd, so a relative write inside the
    site repo is classified by where it lands (REFUTE 2026-11-09 residual 2)."""
    if isinstance(path, str) and path and not os.path.isabs(path) and isinstance(cwd, str) and cwd:
        return os.path.join(cwd, path)
    return path


def dc_write_as_native(tool, ti, terms, cwd=None):
    """Map a Desktop Commander write_file / edit_block / write_pdf call onto the native
    Write / Edit shape main() already classifies, so the same egress-path test, content scan
    and edit-seam simulation apply. DECOY DEFENSE: every candidate path field is checked and an
    egress one wins, because the tool may honor a different field than the one a check reads.
    RAISES on a non-string path; main() blocks on that."""
    cands = []
    for field in _DC_PATH_FIELDS:
        v = ti.get(field)
        if v is None:
            continue
        if not isinstance(v, str):
            raise ValueError("path field %r is not a string" % field)
        cands.append(resolve_against(v, cwd))
    egress = [p for p in cands if path_egress_surface(p)]
    path = egress[0] if egress else (cands[0] if cands else "")
    if tool.endswith("edit_block"):
        return "Edit", {"file_path": path, "old_string": ti.get("old_string", ""),
                        "new_string": ti.get("new_string", "")}
    content = ti.get("content", "")
    if not isinstance(content, str):
        content = collect_text(content)  # write_pdf structured content
    if tool.endswith("write_file") and ti.get("mode") == "append" and path_egress_surface(path) \
            and _exists(path):
        # Appended text joins the file's tail: a term can be formed across that seam.
        width = _seam_width(terms) or 256
        with open(path, encoding="utf-8", errors="replace") as fh:
            tail = fh.read()[-width:]
        content = tail + content
    return "Write", {"file_path": path, "content": content}


# What the recipient sees is not always the raw payload string: an HTML body is rendered (an empty
# tag can split a name, an entity can spell one of its letters), an upload arrives base64-encoded,
# and an Office file is a zip of XML whose runs split words at arbitrary points. Each view is added
# to the scan, never substituted for the raw text, so this can only add hits.
_TAG = re.compile(r"<[^<>]*>")
_BETWEEN_TAGS = re.compile(r">\s+<")
_WS = re.compile(r"\s+")  # str patterns: also matches U+00A0, which &nbsp; decodes to
# Exact field names (lowercased) that carry base64 file bytes on the live connectors: SharePoint
# upload/update `contentBase64`, Graph attachment `contentBytes`. Exact, not a substring: a flag
# such as isBase64 / useBase64 is not content and must not be decoded (review finding 2026-09-30).
_B64_FIELDS = ("contentbase64", "contentbytes")
_DATA_URI = re.compile(r"^data:[^,]*;base64,", re.I)
ZIP_MAX_MEMBERS = 5000
# Total bytes decoded across ALL blobs and zip members of one call. Past it the call BLOCKS: the
# harness's hook timeout does not block, so an unbounded decode would be a fail-open by timeout.
SCAN_MAX_DECODED_BYTES = 32 * 1024 * 1024


def _rendered_views(text):
    """How a renderer shows `text`: tags dropped, entities decoded, whitespace runs collapsed -- once
    as is, and once with whitespace BETWEEN tags removed (pretty-printed XML runs that split a
    word)."""
    loose = _WS.sub(" ", html.unescape(_TAG.sub("", text)))
    tight = _WS.sub(" ", html.unescape(_TAG.sub("", _BETWEEN_TAGS.sub("><", text))))
    return (loose, tight) if tight != loose else (loose,)


def _b64decode(value):
    """Decode base64 the way a lenient sender might have produced it: data: URI prefix, line
    wrapping, URL-safe alphabet, missing padding. RAISES if it still is not base64."""
    s = _WS.sub("", _DATA_URI.sub("", value.strip()))
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s, validate=True)


def _blobs(obj, out):
    """Decode every base64 content field (see _B64_FIELDS) into `out`.
    RAISES on a value that is not base64 -- the caller fails closed on that."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and isinstance(k, str) and k.lower() in _B64_FIELDS:
                out.append(_b64decode(v))
            else:
                _blobs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _blobs(v, out)
    return out


def _blob_texts(blob, budget):
    """Readable text of a decoded blob: the bytes as UTF-8 (and UTF-16 by BOM), plus every member of
    a zip container (docx/xlsx/pptx). `budget` is a one-item list of bytes still allowed to decode.
    RAISES past the budget or member cap, or on a member that cannot be read (e.g. encrypted) --
    the caller fails closed on that."""
    budget[0] -= len(blob)
    if budget[0] < 0:
        raise ValueError("payload too large to scan")
    texts = [blob.decode("utf-8", "ignore")]
    if blob[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texts.append(blob.decode("utf-16", "ignore"))
    buf = io.BytesIO(blob)
    if zipfile.is_zipfile(buf):
        with zipfile.ZipFile(buf) as z:
            infos = z.infolist()
            if len(infos) > ZIP_MAX_MEMBERS or sum(i.file_size for i in infos) > budget[0]:
                raise ValueError("zip container too large to scan")
            for info in infos:
                _check_deadline()
                # Bounded read: a header's declared size can lie, the decompressed stream cannot.
                with z.open(info) as fh:
                    data = fh.read(budget[0] + 1)
                budget[0] -= len(data)
                if budget[0] < 0:
                    raise ValueError("zip container too large to scan")
                texts.append(data.decode("utf-8", "ignore"))
    return texts


def mcp_scan_text(ti):
    """Everything an MCP send surface's payload can put in front of a recipient, as one string.
    RAISES when part of it cannot be read; main() blocks on that (fail closed)."""
    base = collect_text(ti)
    views = [base]
    views.extend(_rendered_views(base))
    budget = [SCAN_MAX_DECODED_BYTES]
    for blob in _blobs(ti, []):
        _check_deadline()
        for t in _blob_texts(blob, budget):
            _check_deadline()
            views.append(t)
            views.extend(_rendered_views(t))
    return "\n".join(v for v in views if v)
_GH_SUBS = (r"(?:pr|issue|gist|release|api|label|secret|variable|project|discussion|agent-task|"
            r"repo\s+(?:edit|create|new)|workflow\s+run|codespace\s+cp)")
# `gh`, `gh.exe`, a quoted full path ending in gh.exe, and a line continuation before the subcommand.
_GH_HEAD = r"\bgh(?:\.exe)?[\"']?\s+(?:\\\r?\n\s*)?[\"']?"
EGRESS_BASH = re.compile(
    r"\bgit\s+push\b|\bcurl\b|\bwget\b|\bscp\b|\brsync\b\s+\S+::|"
    r"invoke-webrequest|invoke-restmethod|\bnetlify\b.*\bdeploy\b|\bwrangler\b.*\b(deploy|publish)\b|"
    # PowerShell-native network/mail verbs (REFUTE 2026-11-09: the PowerShell tool and the
    # terminal panel are now egress-gated, and these idioms reached exit 0 before).
    r"\b(?:iwr|irm|curl\.exe|wget\.exe)\b|send-mailmessage|start-bitstransfer|"
    r"\bnet\.webclient\b|\bwebclient\b|\bhttpclient\b|upload(?:string|file|data|values)\b|"
    r"\bssh\b|\bsftp\b|\bftp\b|"
    r"send-via-outlook\.ps1|"  # the SOLE live COM send path IS egress (review finding 2026-06-11)
    + _GH_HEAD + _GH_SUBS + r"\b",  # GitHub CLI (audit finding 2026-11-08)
    re.I,
)

# --- gh CLI egress (audit finding conf-guard-gh-cli-egress-unscanned, 2026-11-08) ----------------
# PR / issue / gist / release / discussion bodies, `gh api` fields, repo and label descriptions,
# secrets and variables leave the machine for GitHub. Inline text is in the command and is scanned
# as command text like every other EGRESS_BASH match. Text gh READS FROM A FILE is not in the
# command, so it is read and scanned too:
#   --body-file / -F (pr, issue, discussion)   --notes-file / -F (release)   --input (api)
#   -F/--field key=@file (api)   -f/--env-file (secret, variable)   -a/--add (gist edit)
#   -F/--from-file (agent-task)   positional files of `gist create|new|edit`, `release create|new|upload`
#   `< file` redirected into gh (before or after it)
# Every one is REQUIRED: while a roster is active, a reference that cannot be read (missing, a glob
# matching nothing, a $VARIABLE), a gh command that cannot be tokenized, a command or process
# substitution / backtick anywhere in a gh command (bar the canonical quoted-heredoc
# `--body "$(cat <<'EOF' ... EOF)"`), or gh run through another shell / eval / xargs BLOCKS (fail
# closed) -- constructs are refused structurally rather than modelled one by one. One exception: a
# file this same command writes first FROM COMMAND TEXT (`cat > f <<'EOF'`, `echo ... > f`,
# `printf ... > f`), that nothing else in the command touches, and that does not exist yet -- its
# content is in the command text, which is scanned.
# RESIDUAL: `-` (stdin) fed by a pipe (`cat f | gh ... --body-file -`, `xargs gh ...`) is scanned as
# command text only (a heredoc body IS command text and is covered); a heredoc executed as a script
# (`bash <<EOF ... gh ... EOF`); a quoted or commented `<<X` whose X appears on a later line;
# non-zip compressed assets (raw bytes only); `-T/--template` names a template already in the repo
# (covered by the pre-push scan when committed); a gh alias (`gh alias set`), a `$G pr ...`
# indirection or a split name (`g''h`) is not recognized as gh. `$VAR` paths, ANSI-C `$'...'`
# quoting and backticks inside a single-quoted gh argument fail closed while a roster is active
# (the safe direction), as does any expanding `$(...)` in a command that also runs a read-only gh
# call (`B=$(git branch --show-current); gh pr list --head "$B"`). Also RESIDUAL: file content read
# into a variable without a substitution (`read -r B < f`, `mapfile`) and then sent; gh run through
# an interpreter other than a shell (`python -c`, `node -e`, `find -exec`).
GH_EGRESS = re.compile(_GH_HEAD + _GH_SUBS + r"\b", re.I)
_GH_FILE_FLAGS = {
    "pr": ("--body-file", "-F"),
    "issue": ("--body-file", "-F"),
    "discussion": ("--body-file", "-F"),
    "release": ("--notes-file", "-F"),
    "api": ("--input",),
    "secret": ("-f", "--env-file"),
    "variable": ("-f", "--env-file"),
    "gist": ("-a", "--add"),
    "agent-task": ("-F", "--from-file"),
}
# Short boolean flags that may be bundled IN FRONT of a file flag (`-dF body.md`).
_GH_BUNDLE_BOOLS = "dfwepi"
_GH_VERB_ALIASES = {"new": "create"}
_GH_POSITIONAL_VALUE_FLAGS = {
    ("gist", "create"): {"-d", "--desc", "-f", "--filename"},
    ("gist", "edit"): {"-a", "--add", "-d", "--desc", "-f", "--filename", "-r", "--remove"},
    ("release", "create"): {"-n", "--notes", "-F", "--notes-file", "-t", "--title", "--target",
                            "--discussion-category", "--notes-start-tag", "-R", "--repo"},
    ("release", "upload"): {"-R", "--repo"},
}
# How many leading positionals are NOT files: the release tag, the gist id being edited.
_GH_POSITIONAL_SKIP = {("release", "create"): 1, ("release", "upload"): 1, ("gist", "edit"): 1}
_SHELL_PUNCT = re.compile(r"^[();<>|&\n]+$")
_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# Shell constructs whose output gh would send but no payload scan can see. While a roster is active
# a gh command containing any of them BLOCKS, except the canonical quoted-heredoc body
# `--body "$(cat <<'EOF' ... EOF)"` (a quoted delimiter means the body is literal command text).
_SAFE_SUBST = re.compile(r"\$\(\s*cat\s+<<-?\s*(['\"])[A-Za-z_][A-Za-z0-9_]*\1")
_SHELL_RUNNERS = ("bash", "sh", "zsh", "dash", "ksh", "eval", "pwsh", "powershell", "cmd", "xargs",
                  "bash.exe", "sh.exe", "pwsh.exe", "powershell.exe", "cmd.exe")
_GLOB_CHARS = re.compile(r"[*?\[]")


def _strip_heredoc_bodies(cmd, quoted_only=False):
    """The command with every heredoc BODY removed (the operator line is kept). A body is free
    text -- an apostrophe in it would break shell tokenizing -- and it is already scanned as
    command text, so dropping it here loses nothing. A heredoc whose end delimiter never appears
    (an `<<` that was not really an operator, e.g. inside quotes) drops nothing."""
    lines = cmd.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in _HEREDOC.finditer(line):
            if quoted_only and not m.group(1):
                continue  # unquoted delimiter: the shell expands $(...) / backticks in the body
            delim = m.group(2)
            j = i
            while j < len(lines) and lines[j].strip() != delim:
                j += 1
            if j < len(lines):
                i = j + 1  # skip the body and the delimiter line
    return chr(10).join(out)


def _strip_comments(text):
    """`text` without shell comments: a `#` that starts a word outside quotes, to end of line
    (`a#b` stays one word). An apostrophe in a comment would otherwise break tokenizing, and a
    gh command written in a comment is not run."""
    out, quote, prev = [], None, "\n"
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(text):
                out.append(text[i:i + 2])
                i += 2
                prev = "x"
                continue
            if c == quote:
                quote = None
        elif c in ("'", '"'):
            quote = c
        elif c == "\\" and i + 1 < len(text):
            out.append(text[i:i + 2])
            i += 2
            prev = "x"
            continue
        elif c == "#" and prev in " \t\n;|&()":
            j = text.find("\n", i)
            i = len(text) if j < 0 else j
            continue
        out.append(c)
        prev = c
        i += 1
    return "".join(out)


def _prepared(cmd):
    """The command as the tokenizer sees it: heredoc bodies, comments and line continuations
    removed."""
    return re.sub(r"\\\r?\n", " ", _strip_comments(_strip_heredoc_bodies(cmd)))


def _shell_tokens(cmd):
    """Shell-ish tokens: words, and runs of operator characters (newline counts as one, so two
    commands on two lines are two segments). RAISES when the command cannot be tokenized."""
    import shlex
    lex = shlex.shlex(_prepared(cmd), posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""  # comments are already stripped; `a#b` is one word to the shell
    return list(lex)


def _is_gh(tok):
    return os.path.basename(tok.replace("\\", "/")).lower() in ("gh", "gh.exe")


def _segments(tokens):
    """[(words, stdin_files, stdout_files, operators)] per simple command. `<` targets go to
    stdin_files and `>`/`>>`/`>|` targets to stdout_files, wherever they sit in the command."""
    segs, words, ins, outs, ops = [], [], [], [], []
    pending = None
    for tok in tokens:
        if _SHELL_PUNCT.match(tok):
            t = tok.strip(" \t\r")
            if t in ("<", ">", ">>", ">|", "&>", "&>>"):
                pending = "in" if t == "<" else "out"
                continue
            if t in (">&", "<&", "2>&", ">>&"):
                pending = "skip"  # fd duplication: the next word is an fd, not a file
                continue
            if t in ("<<", "<<-", "<<<"):
                ops.append(t)
                pending = "skip"  # the heredoc delimiter / here-string word
                continue
            segs.append((words, ins, outs, ops))
            words, ins, outs, ops, pending = [], [], [], [], None
            continue
        if pending == "in":
            ins.append(tok)
        elif pending == "out":
            outs.append(tok)
        elif pending != "skip":
            words.append(tok)
        pending = None
    segs.append((words, ins, outs, ops))
    return [s for s in segs if s[0] or s[1] or s[2]]


def _gh_invocations(tokens):
    """(args after `gh`, redirect-in files) for every gh invocation in a token stream."""
    out = []
    for words, ins, _outs, _ops in _segments(tokens):
        starts = [i for i, w in enumerate(words) if _is_gh(w)]
        for n, s in enumerate(starts):
            end = starts[n + 1] if n + 1 < len(starts) else len(words)
            out.append((words[s + 1:end], ins if n == 0 else []))
    return out


def _written_paths(tokens):
    """Paths the command writes FROM ITS OWN TEXT, so their content is already scanned: the `>`
    target of `echo` / `printf`, or of `cat` fed only by a heredoc / here-string -- and ONLY when
    no other non-gh command in the same Bash call mentions that path (`>> f`, `cp x f`, `tee f`,
    `dd of=f` would change what the file holds)."""
    segs = _segments(tokens)
    candidates = {}
    for n, (words, ins, outs, ops) in enumerate(segs):
        if not outs or not words:
            continue
        cmd0 = os.path.basename(words[0]).lower()
        if cmd0 in ("echo", "printf") or (
                cmd0 == "cat" and ops and not ins and all(w.startswith("-") for w in words[1:])):
            for o in outs:
                candidates.setdefault(o, []).append(n)
    written = set()
    for path, writers in candidates.items():
        if len(writers) != 1:
            continue
        mentioned = False
        for n, (words, ins, outs, _ops) in enumerate(segs):
            if n == writers[0] or any(_is_gh(w) for w in words):
                continue
            if any(path in w for w in words + ins + outs):
                mentioned = True
                break
        if not mentioned:
            written.add(path)
    return written


def _flag_values(args, names):
    """Values of the named flags: `--f v`, `--f=v`, `-Fv`, `-F=v` (pflag strips the `=`), and a
    short flag bundled behind booleans (`-dF v`, `-dFv`)."""
    vals = []
    for i, a in enumerate(args):
        for n in names:
            if n.startswith("--"):
                if a == n and i + 1 < len(args):
                    vals.append(args[i + 1])
                elif a.startswith(n + "="):
                    vals.append(a[len(n) + 1:])
                continue
            m = re.match(r"^-([%s]*)%s(.*)$" % (_GH_BUNDLE_BOOLS, re.escape(n[1:])), a)
            if not m or a.startswith("--"):
                continue
            rest = m.group(2)
            if rest == "":
                if i + 1 < len(args):
                    vals.append(args[i + 1])
            else:
                vals.append(rest[1:] if rest.startswith("=") else rest)
    return vals


def _gh_sub_verb(args):
    """(subcommand, verb, index of the first argument after the verb), skipping a `-R/--repo <v>`
    placed between them (`gh release -R o/r create ...`)."""
    sub = args[0].lower() if args else ""
    i = 1
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-R", "--repo") else 1
    verb = args[i].lower() if i < len(args) else ""
    return sub, _GH_VERB_ALIASES.get(verb, verb), i + 1


def _check_structure(cmd, tokens):
    """RAISE when the command hides what gh sends behind a construct no payload scan can read:
    command / process substitution or backticks outside a quoted heredoc body (the canonical
    `$(cat <<'EOF' ... EOF)` body is allowed), or gh run through another shell or eval
    (`bash -c '...gh...'`, `eval`, `xargs gh`)."""
    # Shell text (every heredoc body stripped) is checked quote-aware; each UNQUOTED-delimiter
    # heredoc body is checked separately and quote-blind, because a body has no shell quoting --
    # an apostrophe in it must not open a fake quote that hides a later `$(`.
    text = _SAFE_SUBST.sub("", _strip_comments(_strip_heredoc_bodies(cmd)))
    if _expanding_construct(text):
        raise ValueError("command substitution, backticks or <(...) in a gh command")
    for body in _unquoted_heredoc_bodies(cmd):
        if re.search(r"(?<!\\)(?:\\\\)*(\$\(|`)", body):  # an even run of backslashes is no escape
            raise ValueError("command substitution or backticks in an unquoted heredoc body")
    for words, _ins, _outs, _ops in _segments(tokens):
        # Every word before the first gh, not just the first word: `timeout 60 bash -c`,
        # `env sh -c`, `nohup ...` (a runner name AFTER gh is just an argument).
        first_gh = next((n for n, w in enumerate(words) if _is_gh(w)), len(words))
        for n, w in enumerate(words[:first_gh]):
            if os.path.basename(w.replace("\\", "/")).lower() in _SHELL_RUNNERS \
                    and any(GH_EGRESS.search(x) or _is_gh(x) for x in words[n + 1:]):
                raise ValueError("gh run through %s" % w)


def _unquoted_heredoc_bodies(cmd):
    """Bodies of heredocs whose delimiter is unquoted (the shell expands `$(...)` in them)."""
    lines = cmd.splitlines()
    bodies, i = [], 0
    while i < len(lines):
        line = lines[i]
        i += 1
        for m in _HEREDOC.finditer(line):
            delim = m.group(2)
            j = i
            while j < len(lines) and lines[j].strip() != delim:
                j += 1
            if j < len(lines):
                if not m.group(1):
                    bodies.append(chr(10).join(lines[i:j]))
                i = j + 1
    return bodies


def _expanding_construct(text):
    """True when `text` holds a `$(`, backtick or `<(` the shell would EXPAND: outside single
    quotes and not backslash-escaped (`<(` only outside any quotes). A literal backtick in a
    single-quoted body or an escaped one in a double-quoted body is plain text, already scanned."""
    quote, i = None, 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
        elif c == "\\":
            i += 2
            continue
        elif c == "'" and quote is None:
            quote = "'"
        elif c == '"':
            quote = None if quote == '"' else '"'
        elif c == "`" or text.startswith("$(", i):
            return True
        elif quote is None and text.startswith("<(", i):
            return True
        i += 1
    return False


def gh_file_refs(cmd):
    """(path, written_by_command) for every file a gh invocation in `cmd` sends the content of.
    RAISES when the command cannot be tokenized or fails _check_structure."""
    tokens = _shell_tokens(cmd)
    _check_structure(cmd, tokens)
    written = _written_paths(tokens)
    invocations = _gh_invocations(tokens)
    refs = []
    for args, redir in invocations:
        refs.extend(redir)
        if not args:
            continue
        sub, verb, after = _gh_sub_verb(args)
        refs.extend(_flag_values(args, _GH_FILE_FLAGS.get(sub, ())))
        if sub == "api":
            for v in _flag_values(args, ("-F", "--field")):
                _k, sep, val = v.partition("=")
                if sep and val.startswith("@"):
                    refs.append(val[1:])
        value_flags = _GH_POSITIONAL_VALUE_FLAGS.get((sub, verb))
        if value_flags is not None:
            pos, skip = [], False
            for a in args[after:]:
                if skip:
                    skip = False
                    continue
                if a.startswith("-") and a != "-":
                    skip = a in value_flags
                    continue
                pos.append(a)
            pos = pos[_GH_POSITIONAL_SKIP.get((sub, verb), 0):]
            refs.extend(p.split("#", 1)[0] for p in pos)
    return [(p, p in written) for p in refs if p and p != "-"]


def _resolve_ref(path, cwd):
    p = os.path.expanduser(path)
    if os.name == "nt":
        if p == "/tmp" or p.startswith("/tmp/"):  # Git Bash /tmp is %TEMP%, not C:\tmp
            import tempfile
            p = os.path.join(tempfile.gettempdir(), p[5:])
        m = re.match(r"^/([a-zA-Z])/(.*)$", p)
        if m:  # Git Bash /c/Users/... form
            p = "%s:/%s" % (m.group(1), m.group(2))
    if not os.path.isabs(p):
        p = os.path.join(cwd if isinstance(cwd, str) and cwd else os.getcwd(), p)
    return p


def gh_referenced_texts(cmd, cwd, roster_active):
    """Readable text of every file a gh command sends. RAISES (caller blocks) while a roster is
    active on a tokenize failure, a nested gh, or a reference that cannot be read; with no active
    roster there is nothing to match, so nothing is read and nothing blocks."""
    texts = []
    if not roster_active:
        return texts
    try:
        refs = gh_file_refs(cmd)
    except Exception as e:
        raise ValueError("the command's file references could not be determined (%s)" % e)
    budget = [SCAN_MAX_DECODED_BYTES]
    for path, written in refs:
        _check_deadline()
        if "$" in path or "`" in path:
            raise ValueError("file reference %s is a shell expansion" % path)
        full = _resolve_ref(path, cwd)
        paths = sorted(glob.glob(full)) if _GLOB_CHARS.search(path) else [full]
        if not paths:
            raise ValueError("glob %s matches no file" % path)
        for f in paths:
            _check_deadline()
            if written and not os.path.exists(f):
                continue  # written by this same command from its own text, which is scanned
            try:
                with open(f, "rb") as fh:
                    blob = fh.read(budget[0] + 1)
            except Exception as e:
                raise ValueError("cannot read %s (%s)" % (path, type(e).__name__))
            texts.extend(_blob_texts(blob, budget))
    return texts


def roster_active(terms):
    """True when at least one active deal carries a term (an empty roster cannot leak)."""
    for key, deal in (terms.items() if isinstance(terms, dict) else ()):
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        if _str_terms(deal, "always") or _str_terms(deal, "context"):
            return True
    return False


# --- Roster-freshness tripwire ------------------------------------------------------------------
# WHY (2026-07-08 audit finding): Invariant 3's self-heal ("if confidential-deal state is
# unavailable ... verify ... if unverifiable, ask") fires ONLY on the roster being ABSENT/unreadable
# -- the load_terms() except-branch in main(). It is BLIND to the roster being STALE-BUT-PRESENT:
# the file parses fine, but nobody has re-confirmed the deal LIST lately. Two drift shapes:
#   * a deal quietly closed and was never retired  -> the guard over-blocks (annoying, but SAFE); OR
#   * a NEW confidential deal should have been added and wasn't -> the guard UNDER-blocks: the deal
#     leaks because there are no terms to match it. This second shape is the dangerous one, and it
#     is EXACTLY what fail-closed cannot catch (fail-closed needs terms present; here there are none).
# So we anchor freshness on `_meta.roster_last_verified` (ISO date) and trip when it ages out.
#
# ROSTER-LEVEL (in `_meta`), NOT per-deal, BY DESIGN: a per-deal "verified" date can only attest to
# deals ALREADY in the file -- it structurally cannot flag a deal that SHOULD exist but is missing
# (the dangerous under-block case). Only a whole-roster "the list was confirmed current on <date>"
# field catches that, so the anchor is roster-wide -- matching how the list is actually reviewed
# (see `_meta.review_cadence`).
#
# THRESHOLD 30 days: the file's own `_meta.review_cadence` ("quarterly", ~90d) is the FORMAL deep
# review; this is a lighter "is the list still current?" tripwire that catches quiet drift ~2 months
# before the quarterly review would. Deliberately tighter than the formal cadence: a leaked
# confidential deal is unrecoverable, a re-verify prompt is cheap -- asymmetric cost, so err early.
STALENESS_THRESHOLD_DAYS = 30
STATE_DIR = os.path.join(HOOK_DIR, "state")            # gitignored transient runtime state (.gitignore §3)
STALE_STATE_FILE = os.path.join(STATE_DIR, "roster-staleness.json")


def block(reason):
    sys.stderr.write("BLOCKED (confidentiality, fail-closed): %s\n" % reason)
    sys.exit(2)


def _read_stdin_text():
    """Decode stdin explicitly as UTF-8, off the raw buffer -- never trust
    sys.stdin's own text-mode encoding. A hook spawned directly by the
    harness (as opposed to a POSIX-locale shell) can get sys.stdin.encoding
    resolved to the Windows ANSI codepage instead of UTF-8 -- confirmed live
    in eos-claude-md-guard.py (2026-07-17) and reproduced here via a direct
    decode unit test (a subprocess spawned from a dev shell does not reliably
    reproduce this OS/codepage quirk -- see hooks/tests/test-confidentiality-
    guard.py's _load_guard_module()). Not exploitable against
    the current roster (every active term is pure ASCII, which survives
    cp1252 corruption of other bytes in scan_text), but it silently defeats
    this fail-closed leak scanner for ANY future confidential term containing
    a non-ASCII character (an accented name, a curly quote, an em-dash) --
    exactly the dangerous under-block case this hook's own docstring already
    flags as invisible to fail-closed. Reading the raw bytes and decoding
    them ourselves makes this independent of whatever codepage the parent
    process happened to inherit."""
    return sys.stdin.buffer.read().decode("utf-8")


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (same for every worktree of
    the same repo), or None on any failure -- not a git repo, git missing, etc."""
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if it can't be
    resolved or doesn't exist there. hooks/confidential-terms.json is gitignored
    (see .gitignore), so `git worktree add` never checks it out into a linked
    worktree -- this lets a linked worktree fall back to the main checkout's
    copy instead of failing closed on every egress call from a fresh worktree
    (2026-07-12, mirrors the same fix in git-prepush-confidential-scan.py)."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


def load_terms():
    """Parsed terms dict. Tries this checkout's copy first; when no explicit
    CONFIDENTIAL_TERMS_FILE_OVERRIDE is set and that copy is missing/unreadable,
    falls back to the MAIN worktree's copy (git-common-dir is shared across every
    worktree of the repo) before giving up. The override is a test-only escape
    hatch and is used EXACTLY as given, with no fallback, so a test pointed at a
    synthetic fixture never silently falls through to the real roster. Still
    raises (the caller's except in main() fails closed) if unreadable everywhere.
    """
    try:
        with open(TERMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if TERMS_FILE_OVERRIDE:
            raise
        fallback = _main_worktree_terms_file()
        if fallback is None:
            raise
        with open(fallback, encoding="utf-8") as f:
            return json.load(f)


def roster_staleness(terms):
    """(is_stale, detail) for the roster freshness anchor `_meta.roster_last_verified`.

    FAIL-CAUTIOUS (mirrors this hook's fail-closed bias -- detection over silence): a MISSING or
    UNPARSEABLE anchor is treated as STALE, not fresh. An absent freshness date is itself an
    unverifiable state, and Invariant 3 says treat unverifiable as ask-first -- silently assuming
    "fresh" would reintroduce exactly the blind spot this tripwire exists to close. A parseable
    FUTURE date (clock skew / forward-dated verification) is accepted as not-stale but noted, so it
    never nags. `detail` is a short human string reused verbatim in the advisory and the breadcrumb.
    """
    meta = terms.get("_meta") if isinstance(terms, dict) else None
    raw = (meta or {}).get("roster_last_verified")
    if not raw:
        return True, "_meta.roster_last_verified is MISSING -- roster freshness cannot be proven"
    try:
        verified = datetime.date.fromisoformat(str(raw).strip())
    except Exception:
        return True, "_meta.roster_last_verified (%r) is not an ISO date -- freshness cannot be proven" % raw
    days = (datetime.date.today() - verified).days
    if days > STALENESS_THRESHOLD_DAYS:
        return True, ("_meta.roster_last_verified=%s is %d days old (> %d-day tripwire); the "
                      "active-deal list may be out of date" % (verified.isoformat(), days,
                                                               STALENESS_THRESHOLD_DAYS))
    return False, "_meta.roster_last_verified=%s (%d days old)" % (verified.isoformat(), days)


def surface_staleness(detail, session_id):
    """Surface a STALE roster WITHOUT hard-blocking (Invariant 3: warn, don't freeze legitimate work).

    Two coordinated signals, BOTH best-effort -- a state read/write failure must NEVER affect the
    egress decision (this is telemetry, not the safety gate):
      * a one-time-per-session loud stderr ADVISORY, so the operator sees it in real time at the
        moment an egress decision is being made against a possibly-incomplete roster; and
      * a durable JSON breadcrumb (hooks/state/roster-staleness.json) a periodic check (the weekly
        eos-health-report / a doctrine probe) or a human can pick up. It also stores
        `last_warned_session`, which is how the advisory is throttled to once per session.

    If the breadcrumb can't be read (so we can't prove we already warned this session), we FAIL
    CAUTIOUS and warn anyway -- a repeated advisory is a cheaper failure than a silent stale roster.
    The caller still ALLOWS the (clean) egress: present-but-stale is a WARN, not the absent-roster
    hard-block. NOTE the breadcrumb carries only dates / a session id / this module's own detail
    string -- never any deal term -- so it is safe to write and to grep.
    """
    prior = {}
    try:
        with open(STALE_STATE_FILE, encoding="utf-8") as f:
            prior = json.load(f)
    except Exception:
        prior = {}  # unreadable/absent -> cannot prove a prior warning this session -> warn (cautious)
    already_warned = bool(session_id) and prior.get("last_warned_session") == session_id

    if not already_warned:
        sys.stderr.write(
            "WARNING (confidentiality, STALE ROSTER): %s. Re-verify the active-deal list against the "
            "source of record, then set _meta.roster_last_verified in confidential-terms.json to "
            "today. Until then, do NOT name any deal on an external surface without independent "
            "confirmation -- a newly-confidential deal may not yet be on the list.\n" % detail)

    # Best-effort durable breadcrumb. Wrapped so a write failure (perms, race) can never touch the
    # egress decision: staleness telemetry is advisory, egress safety is not negotiable.
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STALE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "stale": True,
                "detail": detail,
                "detected_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "threshold_days": STALENESS_THRESHOLD_DAYS,
                # Record the current session as warned so the advisory stays 1x/session. A blank
                # session_id can't be deduped (e.g. a direct test invocation) -> keep any prior
                # marker rather than clobber it, and such calls simply warn every time (cautious).
                "last_warned_session": session_id or prior.get("last_warned_session"),
            }, f, indent=2)
    except Exception:
        pass  # telemetry only -- egress safety must never depend on this write succeeding


def _str_terms(deal, field):
    """The string entries of a roster list. A malformed entry (a number, a nested list) is skipped
    rather than allowed to raise: an uncaught exception here exits 1, which is NON-BLOCKING."""
    value = deal.get(field) or []
    return [t for t in value if isinstance(t, str) and t] if isinstance(value, list) else []


# --- Matching normalization (2026-10-13; mirror of server/briefing/confidential.ts `normalizeForScan`) ---
# A bare lowercase substring match is evaded by anything that changes the CHARACTERS without
# changing what a reader sees: a zero-width space / soft hyphen inside a term, NBSP or thin space for
# a space, curly quotes and dashes, fullwidth letters, accents, numbers pasted with digit-group
# separators. Haystack and every roster term go through the same fold, so the comparison happens in
# one canonical space. KEEP THIS AND THE TYPESCRIPT TWIN ALIGNED -- both are pinned by the same
# synthetic vectors and the same table hash (tests/test-confidentiality-guard.py,
# tests/unit/confidential.test.ts).
#   1. drop superscript/subscript digits, fold typographic punctuation, NFKD, lowercase
#   2. delete combining marks (Mn) and the invisible set (format chars, default-ignorables,
#      non-whitespace control chars, fillers); fold non-ASCII decimal digits to ASCII (no NFC step)
#   3. fold typographic punctuation again, collapse every whitespace run to one space
# Variants: "tight" (invisible chars deleted -- `Zeph<ZWSP>yrine`), "spaced" (invisible chars become
# a space -- `Zephyrine<ZWSP>Holdings` for the term `zephyrine holdings`), and, when the text carries
# bidi override controls, tight REVERSED (what an RLO run renders as). Each also gets a "digits" form
# with group separators removed from properly grouped numbers (4,250,000 -> 4250000).
# The Unicode sets are a FIXED table (generated from Unicode 17), not unicodedata properties, so the
# hook and the TypeScript twin cannot drift when either runtime's Unicode data moves. NFKD and
# lower() still follow this interpreter's Unicode data (residual: a character assigned after it may
# fold differently on the two sides). Everything below runs as C-speed regex/str calls: this hook has
# no timeout of its own, and a timed-out hook does not block.
_TABLE_MN = "300-36f,483-487,591-5bd,5bf,5c1-5c2,5c4-5c5,5c7,610-61a,64b-65f,670,6d6-6dc,6df-6e4,6e7-6e8,6ea-6ed,711,730-74a,7a6-7b0,7eb-7f3,7fd,816-819,81b-823,825-827,829-82d,859-85b,897-89f,8ca-8e1,8e3-902,93a,93c,941-948,94d,951-957,962-963,981,9bc,9c1-9c4,9cd,9e2-9e3,9fe,a01-a02,a3c,a41-a42,a47-a48,a4b-a4d,a51,a70-a71,a75,a81-a82,abc,ac1-ac5,ac7-ac8,acd,ae2-ae3,afa-aff,b01,b3c,b3f,b41-b44,b4d,b55-b56,b62-b63,b82,bc0,bcd,c00,c04,c3c,c3e-c40,c46-c48,c4a-c4d,c55-c56,c62-c63,c81,cbc,cbf,cc6,ccc-ccd,ce2-ce3,d00-d01,d3b-d3c,d41-d44,d4d,d62-d63,d81,dca,dd2-dd4,dd6,e31,e34-e3a,e47-e4e,eb1,eb4-ebc,ec8-ece,f18-f19,f35,f37,f39,f71-f7e,f80-f84,f86-f87,f8d-f97,f99-fbc,fc6,102d-1030,1032-1037,1039-103a,103d-103e,1058-1059,105e-1060,1071-1074,1082,1085-1086,108d,109d,135d-135f,1712-1714,1732-1733,1752-1753,1772-1773,17b4-17b5,17b7-17bd,17c6,17c9-17d3,17dd,180b-180d,180f,1885-1886,18a9,1920-1922,1927-1928,1932,1939-193b,1a17-1a18,1a1b,1a56,1a58-1a5e,1a60,1a62,1a65-1a6c,1a73-1a7c,1a7f,1ab0-1abd,1abf-1add,1ae0-1aeb,1b00-1b03,1b34,1b36-1b3a,1b3c,1b42,1b6b-1b73,1b80-1b81,1ba2-1ba5,1ba8-1ba9,1bab-1bad,1be6,1be8-1be9,1bed,1bef-1bf1,1c2c-1c33,1c36-1c37,1cd0-1cd2,1cd4-1ce0,1ce2-1ce8,1ced,1cf4,1cf8-1cf9,1dc0-1dff,20d0-20dc,20e1,20e5-20f0,2cef-2cf1,2d7f,2de0-2dff,302a-302d,3099-309a,a66f,a674-a67d,a69e-a69f,a6f0-a6f1,a802,a806,a80b,a825-a826,a82c,a8c4-a8c5,a8e0-a8f1,a8ff,a926-a92d,a947-a951,a980-a982,a9b3,a9b6-a9b9,a9bc-a9bd,a9e5,aa29-aa2e,aa31-aa32,aa35-aa36,aa43,aa4c,aa7c,aab0,aab2-aab4,aab7-aab8,aabe-aabf,aac1,aaec-aaed,aaf6,abe5,abe8,abed,fb1e,fe00-fe0f,fe20-fe2f,101fd,102e0,10376-1037a,10a01-10a03,10a05-10a06,10a0c-10a0f,10a38-10a3a,10a3f,10ae5-10ae6,10d24-10d27,10d69-10d6d,10eab-10eac,10efa-10eff,10f46-10f50,10f82-10f85,11001,11038-11046,11070,11073-11074,1107f-11081,110b3-110b6,110b9-110ba,110c2,11100-11102,11127-1112b,1112d-11134,11173,11180-11181,111b6-111be,111c9-111cc,111cf,1122f-11231,11234,11236-11237,1123e,11241,112df,112e3-112ea,11300-11301,1133b-1133c,11340,11366-1136c,11370-11374,113bb-113c0,113ce,113d0,113d2,113e1-113e2,11438-1143f,11442-11444,11446,1145e,114b3-114b8,114ba,114bf-114c0,114c2-114c3,115b2-115b5,115bc-115bd,115bf-115c0,115dc-115dd,11633-1163a,1163d,1163f-11640,116ab,116ad,116b0-116b5,116b7,1171d,1171f,11722-11725,11727-1172b,1182f-11837,11839-1183a,1193b-1193c,1193e,11943,119d4-119d7,119da-119db,119e0,11a01-11a0a,11a33-11a38,11a3b-11a3e,11a47,11a51-11a56,11a59-11a5b,11a8a-11a96,11a98-11a99,11b60,11b62-11b64,11b66,11c30-11c36,11c38-11c3d,11c3f,11c92-11ca7,11caa-11cb0,11cb2-11cb3,11cb5-11cb6,11d31-11d36,11d3a,11d3c-11d3d,11d3f-11d45,11d47,11d90-11d91,11d95,11d97,11ef3-11ef4,11f00-11f01,11f36-11f3a,11f40,11f42,11f5a,13440,13447-13455,1611e-16129,1612d-1612f,16af0-16af4,16b30-16b36,16f4f,16f8f-16f92,16fe4,1bc9d-1bc9e,1cf00-1cf2d,1cf30-1cf46,1d167-1d169,1d17b-1d182,1d185-1d18b,1d1aa-1d1ad,1d242-1d244,1da00-1da36,1da3b-1da6c,1da75,1da84,1da9b-1da9f,1daa1-1daaf,1e000-1e006,1e008-1e018,1e01b-1e021,1e023-1e024,1e026-1e02a,1e08f,1e130-1e136,1e2ae,1e2ec-1e2ef,1e4ec-1e4ef,1e5ee-1e5ef,1e6e3,1e6e6,1e6ee-1e6ef,1e6f5,1e8d0-1e8d6,1e944-1e94a,e0100-e01ef"
_TABLE_FMT = "0-8,e-1b,7f-84,86-9f,ad,600-605,61c,6dd,70f,890-891,8e2,115f-1160,180e,200b-200f,202a-202e,2060-206f,2800,3164,feff,ffa0,fff0-fffb,110bd,110cd,13430-1343f,1bca0-1bca3,1d173-1d17a,e0000-e00ff,e01f0-e0fff"
_TABLE_PD = "2d,58a,5be,1400,1806,2010-2015,2212,2e17,2e1a,2e3a-2e3b,2e40,2e5d,301c,3030,30a0,fe31-fe32,fe58,fe63,ff0d,10d6e,10ead"
_TABLE_ND0 = "30,660,6f0,7c0,966,9e6,a66,ae6,b66,be6,c66,ce6,d66,de6,e50,ed0,f20,1040,1090,17e0,1810,1946,19d0,1a80,1a90,1b50,1bb0,1c40,1c50,a620,a8d0,a900,a9d0,a9f0,aa50,abf0,ff10,104a0,10d30,10d40,11066,110f0,11136,111d0,112f0,11450,114d0,11650,116c0,116d0,116da,11730,118e0,11950,11bf0,11c50,11d50,11da0,11de0,11f50,16130,16a60,16ac0,16b50,16d70,1ccf0,1d7ce,1d7d8,1d7e2,1d7ec,1d7f6,1e140,1e2f0,1e4f0,1e5f1,1e950,1fbf0"


def normalization_tables_sha256():
    """SHA-256 of the four tables; pinned by tests on both sides of the mirror."""
    import hashlib
    return hashlib.sha256("|".join((_TABLE_MN, _TABLE_FMT, _TABLE_PD, _TABLE_ND0)).encode("utf-8")).hexdigest()


def _parse_ranges(spec):
    out = []
    for r in spec.split(","):
        a, _, b = r.partition("-")
        lo = int(a, 16)
        out.append((lo, int(b, 16) if b else lo))
    return out


def _map_of(ranges, value):
    return {c: value for a, b in ranges for c in range(a, b + 1)}


# str.translate tables: one C-speed dict lookup per character. (A regex character class over these
# sets is NOT usable: sre scans non-BMP ranges linearly, ~1000 comparisons per character.)
_MN = _map_of(_parse_ranges(_TABLE_MN), None)
_FMT = _parse_ranges(_TABLE_FMT)
_ND_ZEROS = [lo for lo, _ in _parse_ranges(_TABLE_ND0)]
_PUNCT = {}
_PUNCT.update(_map_of(_parse_ranges(_TABLE_PD) + [(0x2212, 0x2212)], "-"))
_PUNCT.update(_map_of([(0x60, 0x60), (0xB4, 0xB4), (0x2B9, 0x2B9), (0x2BB, 0x2BC), (0x2018, 0x201B),
                       (0x2032, 0x2032), (0x2035, 0x2035), (0xA78C, 0xA78C)], "'"))
_PUNCT.update(_map_of([(0xAB, 0xAB), (0xBB, 0xBB), (0x201C, 0x201F), (0x2033, 0x2033), (0x2036, 0x2036)], '"'))
_T_PRE = dict(_PUNCT)
_T_PRE.update(_map_of([(0xB2, 0xB3), (0xB9, 0xB9), (0x2070, 0x2070), (0x2074, 0x2079), (0x2080, 0x2089)], None))
_T_POST = dict(_PUNCT)
for _z in _ND_ZEROS:
    if _z != 0x30:
        for _i in range(10):
            _T_POST[_z + _i] = str(_i)
_T_TIGHT = dict(_MN)
_T_TIGHT.update(_map_of(_FMT, None))
_T_SPACED = dict(_MN)
_T_SPACED.update(_map_of(_FMT, " "))
# Pure-ASCII inputs (the common case, and the big base64 payloads) take one fast translate pass.
# Mixed inputs are processed per NON-ASCII RUN: NFKD / NFC / the strip tables only ever act on
# non-ASCII characters (every ASCII character is a starter), so ASCII stretches are never walked by
# the slow code, while lower() still runs over the whole string (contextual final sigma).
_T_PRE_A = {c: v for c, v in _T_PRE.items() if c < 128}
_T_TIGHT_A = {c: v for c, v in _T_TIGHT.items() if c < 128}
_T_SPACED_A = {c: v for c, v in _T_SPACED.items() if c < 128}
_T_PRE_N = {c: v for c, v in _T_PRE.items() if c >= 128}
_T_TIGHT_N = {c: v for c, v in _T_TIGHT.items() if c >= 128}
_T_SPACED_N = {c: v for c, v in _T_SPACED.items() if c >= 128}
_T_POST_N = {c: v for c, v in _T_POST.items() if c >= 128}
_RE_NONASCII = re.compile("[^\u0000-\u007f]+")
_RE_ASCII_WS_ODD = re.compile("[\u0009-\u000d\u001c-\u001f]|  ")
_RE_ASCII_FMT = re.compile("[" + "".join(re.escape(chr(c)) for c in sorted(_T_TIGHT_A)) + "]")
_RE_BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
# 1-3 digits then 1+ (separator + exactly 3 digits); not touching other digits, so 12.50 stays.
# Digit-group separators: , . _ ' space NBSP thin-space narrow-NBSP and the Arabic thousands separator.
_SEP_CLASS = "[,._' \u00a0\u2009\u202f\u066c]"
# ONE separator character used throughout (a backreference), so "4,250,000 100%" is the number
# 4,250,000 followed by 100, not 4250000100.
_RE_GROUPED_NUM = re.compile(r"(?<![0-9])[0-9]{1,3}(" + _SEP_CLASS + r")[0-9]{3}(?:\1[0-9]{3})*(?![0-9])")
# Shortest compact term the whitespace-insensitive match applies to (short terms would over-match).
_COMPACT_MIN = 8

# Canonical digit-run form: ANY separator between two digits is dropped. Over-merges ("3 250,000" ->
# 3250000, "4.25" -> 425) on purpose, and is used SYMMETRICALLY (term and haystack) only for terms that
# mix words and a number, so the match never depends on how a neighbouring number happens to be written;
# the over-merge can only add matches (fail closed).
_RE_DIGIT_SEP = re.compile("(?<=[0-9])" + _SEP_CLASS + "(?=[0-9])")
_RE_ANY_DIGIT = re.compile("[0-9]")
_RE_ALL_DIGITS = re.compile("[0-9]+")
_SEAM_WALK_CAP = 400000
# NFKD is ~0.7 s per MB of non-ASCII text and this hook has no timeout of its own (a timed-out hook
# does not block), so past this many non-ASCII bytes beyond one-per-character the scan REFUSES and
# the caller blocks -- fail closed instead of timing out open.
_NONASCII_BUDGET = 2000000


class ScanTooLarge(Exception):
    pass


# Total NFKD OUTPUT characters one normalization may produce. Expanding characters (U+FDFA -> 18) make
# the output, not the input, the cost driver; past this the scan REFUSES and the caller blocks.
_NFKD_OUT_BUDGET = 4000000


def _nfkd_chunked(run, produced):
    """NFKD of a non-ASCII run in ~512-character pieces cut only before a combining-class-0
    character. NFKD is context-free between such starters, and one huge call is superlinear
    (canonical reordering of the mark runs it expands into). NFC is deliberately NOT applied
    anywhere: haystack and terms are both left decomposed, so the comparison is unaffected."""
    out, i, n = [], 0, len(run)
    while i < n:
        j = min(n, i + 512)
        # Extend to the next starter, but never past 2048 characters: U+0344 is a combining mark that
        # EXPANDS under NFKD, so one long mark run is itself superlinear. Marks are deleted afterwards
        # anyway; a forced cut can only reorder the (non-deleted) marks of a >2048-character run.
        stop = min(n, i + 2048)
        while j < stop and unicodedata.combining(run[j]):
            j += 1
        piece = unicodedata.normalize("NFKD", run[i:j])
        produced[0] += len(piece)
        if produced[0] > _NFKD_OUT_BUDGET:
            raise ScanTooLarge("normalized output too large to scan within the hook's time budget")
        out.append(piece)
        i = j
    return "".join(out)


def _variant(s, table_a, table_n, ascii_fmt_to):
    if s.isascii():
        c = s.translate(_T_PRE_A).lower().translate(table_a)
        # split()/join builds a list of every word (millions, on a big payload). Only needed when the
        # text carries whitespace other than single spaces; a trim is enough otherwise.
        if _RE_ASCII_WS_ODD.search(c) is None:
            return c.strip(" ")
        return " ".join(c.split())
    if len(s.encode("utf-8", "surrogatepass")) - len(s) > _NONASCII_BUDGET:
        raise ScanTooLarge("non-ASCII input too large to normalize within the hook's time budget")
    produced = [0]
    c = s.replace(chr(96), "'")
    c = _RE_NONASCII.sub(lambda m: _nfkd_chunked(m.group(0).translate(_T_PRE_N), produced), c)
    # NFKD can itself emit an ASCII backtick (U+FF40, U+1FEF); fold it like the original ones.
    c = c.replace(chr(96), "'").lower()
    c = _RE_NONASCII.sub(lambda m: m.group(0).translate(table_n), c)
    c = _RE_ASCII_FMT.sub(ascii_fmt_to, c)
    c = _RE_NONASCII.sub(lambda m: m.group(0).translate(_T_POST_N), c)
    # str.split() splits on exactly the whitespace set the TypeScript twin collapses (9-13, 1c-1f,
    # 20, 85, a0, 1680, 2000-200a, 2028/2029, 202f, 205f, 3000), runs included, ends trimmed.
    return " ".join(c.split())


def _tight_form(s):
    return _variant(s, _T_TIGHT_A, _T_TIGHT_N, "")


def _spaced_form(s):
    return _variant(s, _T_SPACED_A, _T_SPACED_N, " ")


def _digits_form(s):
    if not _RE_ANY_DIGIT.search(s):
        return s
    return _RE_GROUPED_NUM.sub(lambda m: m.group(0).replace(m.group(1), ""), s)


def _digits_form_canon(s):
    if not _RE_ANY_DIGIT.search(s):
        return s
    return _RE_DIGIT_SEP.sub("", s)


@functools.lru_cache(maxsize=4)
def _norm_variants(s):
    """(text_forms, digit_forms, compact_forms) for a haystack. Cached: seam windows re-use one post-edit file."""
    tight = _tight_form(s)
    # An ASCII text with no invisible characters has nothing for the "spaced" variant to change.
    spaced = tight if (s.isascii() and _RE_ASCII_FMT.search(s) is None) else _spaced_form(s)
    texts = [tight] if tight == spaced else [tight, spaced]
    # compact: the tight form with every space removed -- matches a long multi-word term whatever mix
    # of invisible characters and spaces separates its words.
    compacts = [tight.replace(" ", "")]
    if _RE_BIDI.search(s):
        # What a bidi-override run renders as: the text reversed (both variants, and the compact form).
        texts.append(tight[::-1])
        if spaced != tight:
            texts.append(spaced[::-1])
        compacts.append(tight[::-1].replace(" ", ""))
    texts = tuple(texts)
    digits = tuple(dict.fromkeys(f(t) for t in texts for f in (_digits_form, _digits_form_canon)))
    return texts, digits, tuple(compacts)


_OPT_SEP = _SEP_CLASS + "?"
_UNAMBIGUOUS_SEP = "[,._']"


def _numeric_term_re(bare):
    """Regex for a purely numeric roster term written against the haystack as TEXT: the term's digits in
    groups of three from the right, each pair of groups allowed an optional separator. Anchored so it is
    a whole number: not touching another digit, not the tail of a larger grouped number (1,250,000 does
    not carry 250000), not the head of one (4,250,000,000 does not carry 4250000). A SPACE before it is
    deliberately allowed: "Suite 7 250,000" is ambiguous and fails toward matching."""
    groups, end = [], len(bare)
    while end > 0:
        groups.insert(0, bare[max(0, end - 3):end])
        end -= 3
    return re.compile("(?<![0-9])(?<![0-9]" + _UNAMBIGUOUS_SEP + ")" + _OPT_SEP.join(groups)
                      + "(?![0-9])(?!" + _UNAMBIGUOUS_SEP + "[0-9]{3}(?![0-9]))")


def _forms_contain(forms, raw_term):
    texts, digits, compact = forms
    tight = _tight_form(raw_term)
    if not tight:
        return False
    if any(tight in h for h in texts):
        return True
    compact_term = tight.replace(" ", "")
    if compact_term != tight and len(compact_term) >= _COMPACT_MIN and any(compact_term in c for c in compact):
        return True
    # The TERM gets both digit forms too (as the haystack does), so a term mixing words and a number
    # does not depend on how its neighbours happen to be written.
    d_terms = tuple(dict.fromkeys((_digits_form(tight), _digits_form_canon(tight))))
    bare = re.sub(r"^\$\s*", "", d_terms[0])
    if _RE_ALL_DIGITS.fullmatch(bare):
        pat = _numeric_term_re(bare)
        # Also the digit forms: the canonical digit-run form folds odd groupings (Indian lakh 42,50,000,
        # 25 00 00) back to the plain digits. Only adds matches.
        return any(pat.search(h) for h in texts) or any(pat.search(h) for h in digits)
    return any(d in h for h in digits for d in d_terms)


# In-hook wall-clock budget. This hook has no timeout of its own and a timed-out hook does NOT block,
# so past this many seconds the scan raises ScanTooLarge and every caller turns that into a block.
_SCAN_SECONDS = 25
_DEADLINE = [None]


def _check_deadline():
    d = _DEADLINE[0]
    if d is not None and time.monotonic() > d:
        raise ScanTooLarge("scan exceeded its time budget")


@functools.lru_cache(maxsize=64)
def _raw_anchor(ctx, reqs):
    """Is any (lowercased) trigger in the raw context text? Memoized: seam windows all share ONE
    post-edit file, and re-searching it per window made a many-seam replace_all O(seams x file)."""
    low = _lower(ctx)
    return any(r in low for r in reqs)


@functools.lru_cache(maxsize=64)
def _norm_anchor(ctx, reqs):
    try:
        forms = _norm_variants(ctx)
    except ScanTooLarge:
        # A context file too large to normalize: treat the anchor as PRESENT (the stricter direction),
        # so its context terms are still looked for in the small window instead of the whole edit
        # being refused. Context terms are then matched on the window alone.
        return True
    return any(_forms_contain(forms, r) for r in reqs)


@functools.lru_cache(maxsize=4)
def _lower(s):
    return s.lower()


def find_hit(text, terms, context_text=None):
    """Return (deal_label, term) on first confidential hit in `text`, else None. A context term
    counts when its trigger (context_requires_any) appears in `context_text`, which defaults to
    `text`; seam windows pass the whole post-edit file so a trigger elsewhere on the page counts.
    Matching is over normalized forms (see the block above), never the raw text."""
    if not text:
        return None
    # Pre-pass: the ORIGINAL matcher (raw lowercase substring), linear time. A plain, unobfuscated
    # term is therefore blocked before any normalization runs, so padding a payload with
    # characters that make normalization slow can never hide a plain term.
    low = _lower(text)
    ctx_src = text if context_text is None else context_text
    for key, deal in terms.items():
        _check_deadline()
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        for t in _str_terms(deal, "always"):
            if t.lower() in low:
                return (deal.get("label", key), t)
        reqs = tuple(r.lower() for r in _str_terms(deal, "context_requires_any"))
        if reqs and _raw_anchor(ctx_src, reqs):
            for t in _str_terms(deal, "context"):
                if t.lower() in low:
                    return (deal.get("label", key), t)
    forms = _norm_variants(text)
    if not any(forms[0]):
        return None
    for key, deal in terms.items():
        _check_deadline()
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        for t in _str_terms(deal, "always"):
            if _forms_contain(forms, t):
                return (deal.get("label", key), t)
        reqs = tuple(_str_terms(deal, "context_requires_any"))
        # An anchor that normalizes to nothing (empty, whitespace or invisible-only) matches everywhere;
        # fail closed and treat the group as unanchored. Computed from the RAW list, since _str_terms
        # drops empty strings (the TypeScript twin keeps them).
        raw_anchors = deal.get("context_requires_any")
        raw_anchors = [r for r in raw_anchors if isinstance(r, str)] if isinstance(raw_anchors, list) else []
        # ANY blank anchor leaves the group unanchored (a blank anchor matches everywhere, as '' always
        # did); it must not be skipped just because a real anchor sits next to it.
        unanchored = any(not _tight_form(r) for r in raw_anchors)
        if unanchored or (reqs and _norm_anchor(ctx_src, reqs)):
            for t in _str_terms(deal, "context"):
                if _forms_contain(forms, t):
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


# --- Edit seams (2026-09-24) ---------------------------------------------------------------------
# An Edit's new_string is not the whole story: the text it lands between is already on disk, so a
# term can be CREATED at the seam -- "Zephyr C|QQ|orp Portfolio" with QQ -> "" (or with QQ -> "o",
# which alone contains no term) becomes a confidential name that new_string never carried. Before
# this, that shape passed unscanned; and a delete-only Edit (new_string "") had nothing to scan at
# all, so it fail-closed on every public-site edit that only removed text. Both close the same way:
# apply the edit(s) to the file's current text in memory and scan a window around every seam, at
# least as wide as the longest term on each side. Context triggers are looked up in the WHOLE
# post-edit file, since a trigger elsewhere on the page makes a context term at the seam a hit.
#
# Fail closed when the edit cannot be simulated against a file that EXISTS: the real Edit tool
# matches more leniently than `old in text` (curly/straight quote folding, \uXXXX decoding,
# UTF-16 files by BOM, files far past our size cap), so "old_string not found here" does not mean
# "the tool will refuse". Only a target that does not exist yet keeps the pre-2026-09-24 behavior
# (scan new_string; nothing to scan -> block).
#
# Known limit: the decision is taken on a snapshot. A writer that changes the file between this hook
# and the Edit's apply (seconds, measured) is not seen; nothing re-scans after the write. The
# pre-2026-09-24 guard had the same gap for any non-empty edit (a seam it never looked at).
#
# Why the windows cover every new occurrence (MultiEdit applies edits in order): take a term present
# after the last edit that was not there before. Let k be the last edit whose replaced span or
# insertion point falls inside the term. No later edit changes the term's characters, so the term is
# already present, intact, in the text right after edit k -- and it contains or straddles k's seam.
# The window taken from that intermediate text, [seam - W, seam + len(new) + W] with W >= the term's
# length, contains it.
SEAM_MAX_FILE_BYTES = 20 * 1024 * 1024


def _seam_width(terms):
    """Window margin on each side of a seam, in NORMALIZED characters (see _seam_window): three times
    the longest active term, measured both raw and normalized (NFKD can expand a character), plus
    slack. 0 when no deal is active -- nothing to find. None on a roster shape it cannot read, which
    disables seam simulation (the caller then fails closed on an empty scan, as before)."""
    try:
        longest = 0
        for key, deal in terms.items():
            if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
                continue
            for field in ("always", "context", "context_requires_any"):
                for t in deal.get(field, []) or []:
                    if isinstance(t, str):
                        longest = max(longest, len(t), len(_tight_form(t)))
        return 3 * longest + 8 if longest else 0
    except Exception:
        return None


def _seam_window(text, lo, hi, width):
    """text[lo:hi] widened until at least `width` NORMALIZED characters lie on each side (or the file
    ends). Measured with the real normalizer, so any character that normalizes away -- zero-width,
    combining, fillers, whitespace runs -- cannot push a padded term out of the window. The margin
    doubles, so cost is linear in the padding. None past _SEAM_WALK_CAP (the caller fails closed)."""
    n = len(text)
    x = max(2 * width, 64)
    while True:
        _check_deadline()
        a, b = max(0, lo - x), min(n, hi + x)
        if ((a == 0 or len(_tight_form(text[a:lo])) >= width)
                and (b == n or len(_tight_form(text[hi:b])) >= width)):
            return text[a:b]
        if x > _SEAM_WALK_CAP:
            return None
        x *= 2


def _edit_seams(path, edits, width):
    """(windows, post_edit_text) for the edit(s), or None when they cannot be simulated (unreadable,
    non-UTF-8 or oversized file, a non-dict edit, missing or empty old_string, old_string not in the
    text). Never raises: an uncaught exception exits 1, which is NON-BLOCKING, i.e. fail-open.

    Mirrors the Edit tool where it matters: universal newlines (it matches LF old_strings against
    CRLF files), and a delete (new_string "") of text followed by a newline also removes that
    newline. Windows only feed the term scan, so none of this changes what is written."""
    try:
        if not path or os.path.getsize(path) > SEAM_MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="strict", newline=None) as f:
            text = f.read()
        windows = []
        for ed in edits:
            _check_deadline()
            if not isinstance(ed, dict):
                return None
            old, new = ed.get("old_string"), ed.get("new_string")
            if not isinstance(old, str) or not isinstance(new, str) or not old:
                return None
            old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
            if old not in text:
                return None
            if new == "" and not old.endswith("\n") and old + "\n" in text:
                old += "\n"
            if ed.get("replace_all"):
                parts = text.split(old)
                text = new.join(parts)
                at = 0
                for part in parts[:-1]:
                    _check_deadline()
                    at += len(part)
                    w = _seam_window(text, at, at + len(new), width)
                    if w is None:
                        return None
                    windows.append(w)
                    at += len(new)
            else:
                at = text.index(old)
                text = text[:at] + new + text[at + len(old):]
                w = _seam_window(text, at, at + len(new), width)
                if w is None:
                    return None
                windows.append(w)
        return windows, text
    except Exception:
        return None


def _exists(path):
    """True when something is at `path` (file, directory, anything). Never raises."""
    try:
        return bool(path) and isinstance(path, str) and os.path.lexists(path)
    except Exception:
        return False


def path_egress_surface(path):
    # Slash-normalized (review 2026-11-09): a joined relative path is mixed-slash on Windows
    # (C:\ws/outputs/x), which neither "/outputs/" nor "\\outputs\\" matched.
    pl = (path or "").replace("\\", "/").lower()
    if any(m in pl for m in SITE_MARKERS):
        return "public website repo"
    if pl.endswith(ARTIFACT_EXT):
        return "output artifact (%s)" % os.path.splitext(pl)[1]
    if any(m in pl for m in BUILD_MARKERS):
        return "mirror/build output"
    return None


def main():
    _DEADLINE[0] = time.monotonic() + _SCAN_SECONDS
    # 1) If we cannot load the term list, we cannot evaluate confidentiality -> fail closed.
    try:
        terms = load_terms()
    except Exception as e:
        block("confidential-terms.json unreadable (%s); cannot verify egress safety." % e)

    # _read_stdin_text() must be INSIDE the try: unlike the old sys.stdin.read()
    # (which -- decoding via whatever the platform resolves, e.g. cp1252 --
    # effectively never raises), an explicit .decode("utf-8") CAN raise
    # UnicodeDecodeError on genuinely malformed input. This hook is
    # FAIL-CLOSED: a read/decode failure must BLOCK via the same path as an
    # unparseable payload, not propagate as an uncaught exception (which
    # would exit 1 -- non-blocking, i.e. a silent fail-OPEN on this
    # fail-closed gate).
    try:
        raw = _read_stdin_text()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        block("tool-call payload could not be parsed; cannot verify egress safety.")

    if not isinstance(data, dict):
        # A non-object payload used to raise on data.get -> exit 1 = fail-OPEN (REFUTE 2026-11-09).
        block("tool-call payload is not a JSON object; cannot verify egress safety.")
    tool = (data.get("tool_name") or data.get("tool") or "")
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        # The tools gated since 2026-11-09 are read field-by-field; a non-dict input cannot be
        # classified, so fail closed for them (legacy tools keep the whole-payload wrap below).
        if (_mcp_suffix(tool, _DC_WRITE_SUFFIXES + ("move_file",)) or is_shell_tool(tool)
                and tool != "Bash") or tool in ("Artifact", "ArtifactData", "ArtifactComments") \
                or (isinstance(tool, str) and (DOCS_WRITE.match(tool) or BROWSER_TOOL.match(tool)
                                               or tool.startswith("mcp__excel__"))):
            block("%s tool_input is not an object; cannot verify egress safety." % tool)
        ti = {"_": ti}

    # --- Determine egress surface + scan text -----------------------------------------
    surface = None
    scan_text = None

    # Desktop Commander writes reuse the native file-tool path below (HIGH 1, 2026-11-09).
    if _mcp_suffix(tool, _DC_WRITE_SUFFIXES):
        try:
            tool, ti = dc_write_as_native(tool, ti, terms, data.get("cwd"))
        except Exception as e:
            block("Desktop Commander write could not be classified (%s); cannot verify egress "
                  "safety." % e)

    # File-writing tools: only egress when the target path is an external surface.
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        if not isinstance(path, str):
            block("file path is not a string; cannot classify the write target.")
        surface = path_egress_surface(path)
        if surface:
            # scan the content being written/inserted (not old_string)
            pieces = [ti.get("content", ""), ti.get("new_string", ""), ti.get("new_source", "")]
            raw_edits = ti.get("edits")
            for ed in raw_edits if isinstance(raw_edits, list) else ([raw_edits] if raw_edits else []):
                pieces.append(ed.get("new_string", "") if isinstance(ed, dict) else ed)
            scan_text = " ".join(str(p) for p in pieces if p)
            # An explicit empty Write writes nothing that could leak.
            extracted = tool == "Write" and isinstance(ti.get("content"), str)
            if tool in ("Edit", "MultiEdit"):
                edits = [ti] if tool == "Edit" else ti.get("edits")
                width = _seam_width(terms)
                seams = None
                if isinstance(edits, list) and edits and width is not None:
                    seams = _edit_seams(path, edits, width)
                if seams is None:
                    if _exists(path):
                        block("edit to %s could not be simulated against the file on disk, so the "
                              "text at its seams cannot be checked." % surface)
                else:
                    windows, post_edit = seams
                    for w in windows:
                        try:
                            hit = find_hit(w, terms, context_text=post_edit)
                        except Exception as e:
                            block("edit seam scan failed (%s); cannot verify egress safety." % type(e).__name__)
                        if hit:
                            block("'%s' identifier ('%s') would be formed where this edit joins the "
                                  "existing text of %s. This deal must not reach any external surface "
                                  "until closing." % (hit[0], hit[1], surface))
                    extracted = True
            if not scan_text and not extracted:
                # egress write we cannot read -> fail closed
                block("write to %s but content could not be extracted." % surface)

    # Desktop Commander move_file: egress when the DESTINATION is an external surface; what lands
    # there is the source file's bytes, so read and scan them (HIGH 1, 2026-11-09).
    elif _mcp_suffix(tool, ("move_file",)):
        src, dst = ti.get("source"), ti.get("destination")
        if not isinstance(dst, str) or (src is not None and not isinstance(src, str)):
            block("move_file source/destination is not a string; cannot classify the move.")
        surface = path_egress_surface(resolve_against(dst, data.get("cwd")))
        if surface:
            try:
                scan_text = "\n".join(local_file_texts([src], data.get("cwd"),
                                                       [SCAN_MAX_DECODED_BYTES]))
            except Exception as e:
                block("move into %s, but the source could not be read for scanning (%s)."
                      % (surface, e))

    # Shell: only egress commands are scanned (internal commands may reference the deal).
    # Every shell-capable tool, not just Bash (HIGH 1, 2026-11-09): Desktop Commander
    # start_process / interact_with_process, the terminal panel's run_in_terminal, PowerShell.
    elif is_shell_tool(tool):
        cmd = shell_command(tool, ti)
        cmd = "" if cmd is None else cmd
        if not isinstance(cmd, str):
            # A non-string command used to raise TypeError in EGRESS_BASH.search -> exit 1, which
            # is NON-blocking (review of the 2026-11-08 gh fix).
            block("%s command is not a string; cannot classify it." % tool)
        if EGRESS_BASH.search(cmd):
            surface = "egress shell command"
            scan_text = cmd
            if GH_EGRESS.search(cmd):
                try:
                    extra = gh_referenced_texts(cmd, data.get("cwd"), roster_active(terms))
                except Exception as e:
                    block("gh command sends file content that could not be read for scanning "
                          "(%s)." % e)
                if extra:
                    scan_text = "\n".join([cmd] + extra)

    # Notion / Outlook / Teams / SharePoint / HubSpot writes: the whole payload is bound for an
    # external service (see MCP_SEND_SURFACES for what is in and out, and why).
    else:
        surface = classify_tool(tool)
        if surface:
            try:
                scan_text = mcp_scan_text(ti)
            except Exception as e:
                block("payload for %s could not be fully decoded for scanning (%s)." % (surface, e))
        else:
            # Artifact / Docs / browser / Excel (HIGH 2, 2026-11-09) -- see classify_extra.
            try:
                surface = classify_extra(tool, ti, data.get("cwd"))
            except Exception as e:
                block("%s could not be classified (%s); cannot verify egress safety." % (tool, e))
            if surface:
                try:
                    scan_text = extra_scan_text(tool, ti, data.get("cwd"))
                except Exception as e:
                    block("content for %s could not be fully read for scanning (%s)."
                          % (surface, e))

    # Not an egress surface -> allow.
    if surface is None:
        sys.exit(0)

    # --- Enforce -----------------------------------------------------------------------
    try:
        hit = find_hit(scan_text, terms)
    except Exception as e:
        block("egress scan failed (%s); cannot verify egress safety." % type(e).__name__)
    if hit:
        label, term = hit
        block("'%s' identifier ('%s') would cross egress surface [%s]. "
              "This deal must not reach any external surface until closing. "
              "Keep it on internal/local paths only." % (label, term, surface))

    # Clean egress. Before allowing, check roster FRESHNESS -- this no-hit path is the exact failure
    # mode a stale roster hides: a NEW confidential deal that should be on the list but isn't produces
    # ZERO hits and would sail through silently. A present-but-stale roster is a WARN (surface the
    # advisory + allow), NOT the absent-roster hard-block; staleness makes the hook speak up, it does
    # not freeze all legitimate egress forever. Evaluated only here (egress surface, no hit) so the
    # cost/noise lands only where a missing-deal leak could actually occur.
    stale, detail = roster_staleness(terms)
    if stale:
        surface_staleness(detail, data.get("session_id") or "")

    sys.exit(0)


if __name__ == "__main__":
    main()
