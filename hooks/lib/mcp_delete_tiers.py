"""Tier table for the MCP destructive-delete gate (R-06; audit findings M18, M65).

WHY. Hard-delete MCP tools (Notion delete-*, excel delete_*, delete_scheduled_task, ccd
delete_session / discard_kept_worktree, ...) reached NO PreToolUse guard, and under
defaultMode=bypassPermissions one call removes records for good. Hard Invariants 5 and 6:
deleting in a business store needs Gabriel's permission, and the rule is "never delete --
move to /archive/". hooks/mcp-delete-guard.py enforces; THIS module only answers "which
tier is this call?", so the table is testable on its own.

TIERS
  irreversible -> deny unless a single-use allow-mcp-delete token names this exact call
  recoverable  -> interactive: ask; scheduled/headless: deny unless allowlisted
  exempt       -> allow; not a data delete, or another gate owns it (reason recorded)
  unknown      -> delete-shaped name with no row: handled like recoverable
  unrouted     -> not delete-shaped; the guard should never see it, and allows it

Rows are keyed on the tool-name SUFFIX after the last "__", so a reinstalled connector
with a new GUID stays classified. `verified` is True only when the suffix is present in
hooks/tests/lib/mcp_tool_snapshot.json; test-mcp-delete-tiers.py asserts that
equivalence, so the flag cannot drift from the evidence.

SETTINGS_MATCHER is the exact settings.json matcher of the guard's entry;
test-matcher-coverage.py asserts byte equality. Hook matchers are JavaScript regular
expressions without inline flags, so case variants are spelled out.

Stdlib only. ASCII-only. Windows (`python`).
"""
import hashlib
import json
import re

IRREVERSIBLE = "irreversible"
RECOVERABLE = "recoverable"
EXEMPT = "exempt"
UNKNOWN = "unknown"
UNROUTED = "unrouted"
_BY_INPUT = "by-input"

SETTINGS_MATCHER = (
    "mcp__.*__.*([Dd]elete|DELETE|[Tt]rash|TRASH|[Rr]emove|REMOVE|[Pp]urge|PURGE"
    "|[Dd]iscard|DISCARD).*"
    "|mcp__.*__(clean_up_worktrees|notion-calendar-cancel-events|sharepoint_move_item"
    "|manage_segment|manage_campaign_objects)"
)
_MATCHER_RE = re.compile(SETTINGS_MATCHER)

KEYWORD_RE = re.compile(r"delete|trash|remove|purge|discard", re.IGNORECASE)
EXTRA_NAMES = frozenset((
    "clean_up_worktrees", "notion-calendar-cancel-events", "sharepoint_move_item",
    "manage_segment", "manage_campaign_objects",
))
READ_PREFIXES = (
    "list_", "list-", "get_", "get-", "search_", "search-", "read_", "read-",
    "query_", "query-", "fetch_", "fetch-", "restore", "undelete",
    "notion-get-", "notion-list-", "notion-query-", "notion-search", "notion-fetch",
    "notion-restore-",
)
# Keys that differ between two otherwise identical calls and must not change the digest
# a token binds: _consent is set by the app after its card is approved;
# instructions_version is Notion bookkeeping.
VOLATILE_KEYS = frozenset(("_consent", "instructions_version"))

_EXCEL = "excel MCP rewrites the workbook in place; no undo"
_ABSENT = "named by the ratified design; absent from the current M365 connector"

TIERS = {
    "delete_trigger": (IRREVERSIBLE, False,
                       "claude-code-remote scheduled-task delete: removes the task, its run "
                       "history and every session it started; no restore (pause with "
                       "update_trigger enabled:false)"),
    "delete_scheduled_task": (IRREVERSIBLE, True,
                              "removes the registry entry, cron and run history (pause with "
                              "update_scheduled_task enabled:false; retire via the "
                              "register-scheduled-task skill)"),
    "delete_range": (IRREVERSIBLE, True, _EXCEL),
    "delete_sheet_rows": (IRREVERSIBLE, True, _EXCEL),
    "delete_sheet_columns": (IRREVERSIBLE, True, _EXCEL),
    "delete_worksheet": (IRREVERSIBLE, True, _EXCEL),
    "notion-delete-comment": (IRREVERSIBLE, True,
                              "no restore tool for comments; the last one also removes its "
                              "discussion"),
    "delete_session": (IRREVERSIBLE, True,
                       "transcript, record and worktree are removed for good (the app also "
                       "shows a card)"),
    "discard_kept_worktree": (IRREVERSIBLE, True,
                              "uncommitted worktree changes are discarded for good (the app "
                              "also shows a card)"),
    "delete": (IRREVERSIBLE, True,
               "docs-connector object delete; recoverability is undocumented"),
    "notion-calendar-cancel-events": (IRREVERSIBLE, True,
                                      "cancels calendar events and may notify attendees"),
    "memory_delete": (IRREVERSIBLE, True, "Mnemoverse memory delete; no restore tool"),
    "memory_delete_domain": (IRREVERSIBLE, True, "Mnemoverse domain delete; no restore tool"),
    "outlook_batch_delete_messages": (IRREVERSIBLE, False, _ABSENT),
    "outlook_delete_draft": (IRREVERSIBLE, False, _ABSENT),
    "outlook_delete_label": (IRREVERSIBLE, False, _ABSENT),
    "outlook_delete_filter": (IRREVERSIBLE, False, _ABSENT),
    "outlook_delete_item": (IRREVERSIBLE, False,
                            "pinned in test-confidentiality-guard.py; absent from the current "
                            "M365 connector"),
    "sharepoint_delete_item": (IRREVERSIBLE, False,
                               "ratified as a hard delete; demote only after a live schema "
                               "shows recycle-bin semantics"),
    "notion-delete-pages": (RECOVERABLE, True, "Notion Trash; notion-restore-pages undoes it"),
    "notion-delete-databases": (RECOVERABLE, True,
                                "Notion Trash; notion-restore-pages undoes it"),
    "delete_group": (RECOVERABLE, True, "sidebar group only; its sessions are untouched"),
    "delete_section": (RECOVERABLE, True, "sidebar section only; its sessions are untouched"),
    "outlook_trash_thread": (RECOVERABLE, False,
                             "Deleted Items folder; pinned in test-confidentiality-guard.py"),
    "sharepoint_move_item": (RECOVERABLE, False,
                             "moves a business file out of place (Invariant 5); reversible "
                             "by moving it back"),
    "clean_up_worktrees": (_BY_INPUT, True, "decided by delete_sessions/include_uncommitted"),
    "manage_segment": (_BY_INPUT, True, "decided by operation.type"),
    "manage_campaign_objects": (_BY_INPUT, True, "decided by assetOperations[].action"),
    "outlook_delete_event": (EXEMPT, False,
                             "owned by ora-autonomy-gate Gate 1d (token event:<eventId>)"),
    "image_remove_background": (EXEMPT, True,
                                "Adobe image edit that returns a new image; deletes nothing"),
    "outlook_untrash_thread": (_BY_INPUT, False,
                               "decided by restoreMap[].destinationFolderId; explicit row, not "
                               "a read prefix, so untrash_then_delete stays gated"),
}


def _set(value):
    """True for anything but an explicit False/None: a truthy string must not pass."""
    return value is not None and value is not False


def _clean_up_worktrees(ti):
    if not isinstance(ti, dict):
        return IRREVERSIBLE, "tool_input is not an object -- fails closed"
    if _set(ti.get("delete_sessions")) or _set(ti.get("include_uncommitted")):
        return IRREVERSIBLE, "deletes sessions or uncommitted worktree changes for good"
    return RECOVERABLE, "removes inactive worktrees only; sessions and branches stay"


_SEGMENT_OPS = {
    "DeleteSegmentOperation": (RECOVERABLE, "RestoreSegmentOperation brings it back"),
    "RemoveMembersOperation": (RECOVERABLE, "the removed record ids are in the payload"),
    "RemoveAllMembersOperation": (IRREVERSIBLE, "empties a static segment; no restore"),
    "CreateStaticSegmentOperation": (EXEMPT, "not a delete"),
    "CreateDynamicSegmentOperation": (EXEMPT, "not a delete"),
    "UpdateSegmentOperation": (EXEMPT, "not a delete"),
    "AddMembersOperation": (EXEMPT, "not a delete"),
    "RestoreSegmentOperation": (EXEMPT, "undoes a delete"),
    "UpdateSegmentSuppressionOperation": (EXEMPT, "exclusion settings; no record removed"),
}


def _manage_segment(ti):
    op = ti.get("operation") if isinstance(ti, dict) else None
    if not isinstance(op, dict):
        return IRREVERSIBLE, "operation is not an object -- fails closed"
    op_type = op.get("type")
    row = _SEGMENT_OPS.get(op_type) if isinstance(op_type, str) else None
    if row is None:
        return IRREVERSIBLE, "unknown segment operation type -- fails closed"
    return row


_CAMPAIGN_OPS = frozenset(("CAMPAIGN_CREATE", "CAMPAIGN_UPDATE", "CAMPAIGN_ASSET",
                           "CAMPAIGN_ASSET_TYPES_LIST"))


def _manage_campaign_objects(ti):
    op_type = ti.get("operationType") if isinstance(ti, dict) else None
    if not isinstance(op_type, str) or op_type not in _CAMPAIGN_OPS:
        return IRREVERSIBLE, "unknown campaign operationType -- fails closed"
    if op_type != "CAMPAIGN_ASSET":
        return EXEMPT, "not an asset removal"
    req = ti.get("assetRequest")
    ops = req.get("assetOperations") if isinstance(req, dict) else None
    if not isinstance(ops, list) or not ops:
        return IRREVERSIBLE, "assetOperations missing or malformed -- fails closed"
    actions = set()
    for op in ops:
        action = op.get("action") if isinstance(op, dict) else None
        if not isinstance(action, str) or action not in ("ADD", "REMOVE"):
            return IRREVERSIBLE, "asset operation with an unknown action -- fails closed"
        actions.add(action)
    if "REMOVE" in actions:
        return RECOVERABLE, "dissociates campaign assets; re-adding restores them"
    return EXEMPT, "asset additions only"


# outlook_untrash_thread moves Deleted Items mail to a caller-named folder (schema, from the
# live tool definition). Without a restoreMap every in-trash message returns to Inbox; with
# one, ONLY mapped messages move and unmapped ones stay in Deleted Items. The schema only
# pattern-checks destinationFolderId. A map built from outlook_trash_thread's result is
# EXPECTED to carry opaque Graph folder ids; real ids have not been observed in this repo
# (the test ids are synthetic), so the 40-character floor is a heuristic, not a measured
# bound. A short well-known name (deleteditems, inbox, ...) is out of contract, and a
# recoverableitems* name is assumed (unverified) to push trashed mail toward purge.
# KNOWN LIMITS, accepted: the "opaque" test is effectively a length test (the pattern is the
# schema's own alphabet), and the opaque id of a Recoverable Items folder, if a caller could
# obtain one, would pass as EXEMPT. outlook_modify_labels.moveToFolderId is not delete-shaped
# and never reaches this gate.
_OPAQUE_FOLDER_ID = re.compile(r"[A-Za-z0-9+/=_-]{40,}")


def _outlook_untrash_thread(ti):
    if not isinstance(ti, dict):
        return IRREVERSIBLE, "tool_input is not an object -- fails closed"
    if "restoreMap" not in ti:
        return EXEMPT, "no restoreMap: every in-trash message returns to Inbox"
    rmap = ti["restoreMap"]
    if not isinstance(rmap, list) or not rmap:
        return IRREVERSIBLE, "restoreMap is not a non-empty list -- fails closed"
    tier, reason = EXEMPT, "restores to the folder ids outlook_trash_thread recorded"
    for entry in rmap:
        dest = entry.get("destinationFolderId") if isinstance(entry, dict) else None
        if not isinstance(dest, str) or not dest:
            return IRREVERSIBLE, "restoreMap entry without a destinationFolderId -- fails closed"
        if dest.casefold().startswith("recoverableitems"):
            return IRREVERSIBLE, ("destination is a Recoverable Items folder: moves trashed "
                                  "mail toward purge")
        if _OPAQUE_FOLDER_ID.fullmatch(dest) is None:
            tier, reason = RECOVERABLE, ("destination is not an opaque folder id "
                                         "(well-known name or short id)")
    return tier, reason


_INPUT_CLASSIFIERS = {
    "outlook_untrash_thread": _outlook_untrash_thread,
    "clean_up_worktrees": _clean_up_worktrees,
    "manage_segment": _manage_segment,
    "manage_campaign_objects": _manage_campaign_objects,
}


def short_name(tool_name):
    if not isinstance(tool_name, str):
        return ""
    return tool_name.rsplit("__", 1)[-1]


def is_routed(tool_name):
    """Would the settings.json matcher send this tool to the guard?"""
    return isinstance(tool_name, str) and _MATCHER_RE.search(tool_name) is not None


MAX_NAME_LEN = 512  # real MCP names are far shorter; bounds regex cost on hostile names


def middle_segments(tool_name):
    """'__'-separated segments between the server segment and the final one.

    mcp__<server>__<a>__<b>__<short> -> "<a>__<b>". The server may hold single
    underscores or hyphens, so only the first and last '__' parts are excluded.
    """
    parts = tool_name[len("mcp__"):].split("__")
    return "__".join(parts[1:-1]) if len(parts) > 2 else ""


def classify(tool_name, tool_input):
    """(tier, reason, short). The guard still wraps the call."""
    short = short_name(tool_name)
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__"):
        return UNROUTED, "not an MCP tool", short
    if len(tool_name) > MAX_NAME_LEN:
        return UNKNOWN, "oversized tool name", short[:64]
    tier, reason = _classify_mcp(short, tool_input)
    if tier in (EXEMPT, UNROUTED):
        middle = middle_segments(tool_name)
        if middle and (KEYWORD_RE.search(middle) or middle in EXTRA_NAMES):
            # A delete verb in an earlier segment (mcp__x__delete__list_all) must not be
            # laundered by a read prefix or lenient row in the last segment.
            return UNKNOWN, "delete verb in an earlier name segment", short
    if tier == UNROUTED and is_routed(tool_name):
        # The matcher sends it to the guard but the short name carries no delete verb
        # (e.g. mcp__x__delete__all): never let a routed name pass as unrouted.
        return UNKNOWN, "routed by the matcher but the short name is not classified", short
    return tier, reason, short


def _classify_mcp(short, tool_input):
    row = TIERS.get(short)
    if row is not None:
        tier, _verified, reason = row
        if tier == _BY_INPUT:
            try:
                tier, reason = _INPUT_CLASSIFIERS[short](tool_input)
            except Exception:  # classify must never raise: fail closed
                return IRREVERSIBLE, "by-input classifier raised -- fails closed"
        return tier, reason
    if short.lower().startswith(READ_PREFIXES):
        return EXEMPT, "read or restore verb"
    if KEYWORD_RE.search(short) or short in EXTRA_NAMES:
        return UNKNOWN, "delete-shaped name with no tier row"
    return UNROUTED, "name is not in the delete class"


def target_digest(tool_input):
    """sha256/16 of the canonical input, minus VOLATILE_KEYS."""
    if isinstance(tool_input, dict):
        tool_input = {k: v for k, v in tool_input.items() if k not in VOLATILE_KEYS}
    blob = json.dumps(tool_input, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=repr)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()[:16]


def target_label(short, tool_input):
    """What an allow-mcp-delete token's `targets:` line must name."""
    return "%s:%s" % (short, target_digest(tool_input))
