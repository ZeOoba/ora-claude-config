"""Shared helpers for the update_scheduled_task frontmatter-integrity guard pair
(scheduled-task-update-preguard.py / scheduled-task-update-postguard.py).

WHY THIS PAIR EXISTS (2026-08-13, built from two documented incidents):
  * reference_update_scheduled_task_drops_frontmatter_keys.md (OI-109): a
    `description`-only update_scheduled_task call silently deleted the
    `output_contract` frontmatter block, because the tool only knows about its
    own schema fields (name/description/cronExpression/fireAt/enabled/
    notifyOnCompletion/prompt) and rewrites SKILL.md's frontmatter from that --
    any custom key it doesn't know about does not survive the round-trip.
  * reference_skill_description_registry_file_desync.md: editing SKILL.md by
    hand (outside the tool) desyncs it from what update_scheduled_task believes
    is current, so the NEXT tool-mediated update can silently revert the
    hand-edit.
  Both are the same root cause -- two independent writers (the MCP tool and a
  human/agent Edit) sharing one file with no integrity check between them --
  so one shared module backs both guard halves rather than inventing two.

CONTRACT: this module never adds its own top-level try/except (see
registry-write-guard.py's convention: guards wrap their OWN main(), not their
imports). A caller crash here degrades that ONE guard call to fail-open via
its own outer wrapper, never blocks a tool call.

Frontmatter parsing is DELIBERATELY line-wise, not YAML, matching
reference_skill_frontmatter_lenient_parse.md: the harness itself parses
SKILL.md frontmatter line-wise, so ~97/147 fleet SKILL.md files fail strict
YAML by design. A top-level key is any UN-INDENTED line inside the `---`
fences matching `key:` -- nested/indented lines (e.g. output_contract's
sub-fields) are deliberately not walked; only the presence of the parent key
matters for the "was this key dropped" question this guard answers.

Stdlib only. ASCII-only.
"""

import hashlib
import json
import os
import re
import sys
import time

TASK_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")


def claude_dir():
    # hooks/lib/<this file> -> hooks -> ~/.claude
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def skill_md_path(task_id, base_dir=None):
    if not isinstance(task_id, str) or not task_id:
        return None
    root = base_dir if base_dir is not None else claude_dir()
    return os.path.join(root, "scheduled-tasks", task_id, "SKILL.md")


def state_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state",
                      "scheduled-task-update-guard")
    return os.path.normpath(d)


def ledger_path():
    return os.path.join(state_dir(), "last-tool-sha.json")


def pre_snapshot_path(session_id, task_id):
    key = hashlib.sha256(
        ("%s|%s" % (session_id, task_id)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(state_dir(), "pre-" + key + ".json")


def read_text(path):
    # utf-8-sig: strips a leading BOM if present, transparent no-op otherwise.
    # Without this, a BOM'd SKILL.md makes frontmatter_keys() see "U+FEFF---"
    # on line 1 -- not "---" -- so it returns None (malformed) and both guards
    # silently stop covering that task permanently, with no warning that they
    # stopped (adversarial review finding N3, 2026-08-13).
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return fh.read()
    except Exception:
        return None


def sha256_of(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def frontmatter_keys(text):
    """Set of top-level (un-indented) `key:` names inside the leading `---`
    fence pair, or None if `text` has no closing fence (malformed/truncated --
    the key set cannot be trusted)."""
    if not isinstance(text, str):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    keys = set()
    for ln in lines[1:]:
        if ln.strip() == "---":
            return keys
        if ln[:1].isspace():
            continue  # nested/indented line -- belongs to the previous top-level key
        m = TASK_KEY_RE.match(ln)
        if m:
            keys.add(m.group(1))
    return None  # closing fence never found


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json_atomic(path, data):
    """Best-effort atomic write (temp file + os.replace). Never raises past this
    function -- callers treat a failed write as a lost-but-non-fatal side effect,
    matching every other state-file writer in this hooks/ tree."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp-%d" % int(time.time() * 1000)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        pass


def remove_file(path):
    try:
        os.remove(path)
    except Exception:
        pass


def read_ledger():
    return load_json(ledger_path())


def update_ledger(task_id, sha):
    ledger = read_ledger()
    ledger[task_id] = {"sha": sha, "ts": time.time()}
    write_json_atomic(ledger_path(), ledger)


def emit(msg, hook_event_name):
    """Dual-delivery per shared-checkout-guard.py's DELIVERY note: systemMessage
    reaches the user's transcript, hookSpecificOutput.additionalContext is the
    only Pre/PostToolUse field that is both model-visible and non-blocking.

    `permissionDecision: "allow"` is included ONLY for PreToolUse -- it is a
    PreToolUse-specific field (memory-nag-correction.py's PostToolUse emit()
    omits it entirely; the tool call has already completed by PostToolUse, so
    there is no permission left to decide). Both guards are warn-only by
    contract regardless: a hand-edit or a dropped key is a HEURISTIC signal
    (sha-based, no certainty an actual regression occurred), so blocking on it
    would risk halting a legitimate, intentional update -- and PostToolUse
    cannot block anyway."""
    hso = {"hookEventName": hook_event_name, "additionalContext": msg}
    if hook_event_name == "PreToolUse":
        hso["permissionDecision"] = "allow"
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": hso,
    }))
    sys.stderr.write(msg + "\n")
