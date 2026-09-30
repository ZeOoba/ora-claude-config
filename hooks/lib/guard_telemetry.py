"""Per-guard execution telemetry for the hook dispatchers (2026-09-30).

WHAT: one JSON line per guard/hook execution, appended to
hooks/_state/guard-telemetry.jsonl:

    {"ts": ..., "chain": ..., "guard": ..., "tool_name": ..., "session_id": ...,
     "exit_code": ..., "ms": ..., "path_taken": ...}

path_taken is one of PATH_TAKEN below: "inprocess" / "subprocess" (which
execution path produced the guard's decision), "failopen" (the guard could
not be run on either path and was skipped), "failclosed" (the guard script
was MISSING, so the pretooluse dispatcher refused the call -- see that file's
configuration-emergency branch), or "skipped" (a post-chain hook whose
prefilter declined the payload; recorded so a summary can show how often the
prefilter saved a process).

WHAT IS NEVER LOGGED -- THE CONFIDENTIALITY CONTRACT. Hook payloads carry
command text, file paths, file contents and MCP arguments, any of which can
contain confidential deal terms (invariant 3). This module therefore accepts
NO free-text field at all. The only payload-derived values it writes are
`tool_name` and `session_id`, and both pass an allowlist shape check first
(IDENT_RE / SID_RE): a value that does not look like a tool identifier or a
session id is written as "<invalid>" rather than truncated or escaped, so a
crafted payload cannot smuggle text into the log through either field.
`guard` and `chain` come from the dispatchers' own constants, never the
payload. There is deliberately no "message", "stderr" or "reason" field.

FAIL-OPEN, AND DECISION-NEUTRAL BY CONSTRUCTION. record()/flush() swallow
every exception. Callers must additionally wrap their own calls (they do) so
that even a broken import of this module cannot change a guard decision or an
exit code: telemetry is observability, never enforcement.

BOUNDED GROWTH. Before each append, a file at or above MAX_BYTES (~5 MB) is
rotated to `<path>.1` (os.replace -- the previous .1 is overwritten, so at
most one rotated generation is kept). Rotation runs under an exclusive lock
file with the size re-checked inside it, so two sessions crossing the
threshold together rotate once, not twice (see _rotate_if_needed). A failed
os.replace (Windows sharing violation) is swallowed and the append proceeds
on the current file.

KILL SWITCH: ORA_GUARD_TELEMETRY=0 disables all writes.

TEST SEAMS -- TEST ONLY, never set these in settings.json or a scheduled task:
ORA_GUARD_TELEMETRY_PATH (redirects the log file) and
ORA_GUARD_TELEMETRY_MAX_BYTES (rotation threshold).

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import time

_HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(_HOOKS_DIR, "_state", "guard-telemetry.jsonl")
MAX_BYTES = 5 * 1024 * 1024

ENV_KILL = "ORA_GUARD_TELEMETRY"
ENV_PATH = "ORA_GUARD_TELEMETRY_PATH"          # TEST ONLY
ENV_MAX_BYTES = "ORA_GUARD_TELEMETRY_MAX_BYTES"  # TEST ONLY

PATH_TAKEN = ("inprocess", "subprocess", "failopen", "failclosed", "skipped")

# Real tool names: Edit, Bash, mcp__<uuid>__notion-create-pages,
# mcp__plugin_desktop-commander_desktop-commander__write_file. No spaces, no
# slashes, no quotes -- so no path or sentence can pass.
IDENT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
# Session ids are UUID-shaped, sometimes "local_<uuid>".
SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
INVALID = "<invalid>"


def enabled():
    return os.environ.get(ENV_KILL, "1").strip() != "0"


def log_path():
    return os.environ.get(ENV_PATH) or DEFAULT_PATH


def max_bytes():
    raw = os.environ.get(ENV_MAX_BYTES)
    if raw:
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return MAX_BYTES


def _clean(value, pattern):
    if isinstance(value, str) and pattern.match(value):
        return value
    return INVALID if value not in (None, "") else ""


# Payloads above this size are NOT fully re-parsed just to read two ids
# (adversarial review 2026-09-30, nit 7: a large Write payload would pay the
# JSON parse twice -- once here, once in each guard). The harness emits
# session_id and tool_name before tool_input, so they sit in the first few KB;
# a bounded regex over that head finds them. Either path ends in the same
# allowlist check, so the large-payload path cannot widen what gets logged.
PARSE_CAP_BYTES = 256 * 1024
HEAD_BYTES = 16 * 1024
_HEAD_FIELD_RE = {
    "tool_name": re.compile(rb'"tool_name"\s*:\s*"([^"\\]{1,160})"'),
    "session_id": re.compile(rb'"session_id"\s*:\s*"([^"\\]{1,80})"'),
}


def ids_from_obj(obj):
    """(tool_name, session_id) from an ALREADY-PARSED payload, allowlisted."""
    if not isinstance(obj, dict):
        return "", ""
    return (_clean(obj.get("tool_name"), IDENT_RE),
            _clean(obj.get("session_id"), SID_RE))


def payload_ids(raw):
    """(tool_name, session_id) from the raw payload BYTES, both allowlisted.
    Never raises; unparseable -> ("", "")."""
    try:
        if len(raw) > PARSE_CAP_BYTES:
            head = raw[:HEAD_BYTES]
            out = []
            for field, pattern in (("tool_name", IDENT_RE), ("session_id", SID_RE)):
                m = _HEAD_FIELD_RE[field].search(head)
                out.append(_clean(m.group(1).decode("ascii", "replace"), pattern)
                           if m else "")
            return out[0], out[1]
        obj = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return "", ""
    return ids_from_obj(obj)


def make_record(chain, guard, tool_name, session_id, exit_code, ms, path_taken):
    """One record dict. Every field is typed and shape-checked here so a
    caller cannot accidentally widen what gets written."""
    try:
        rc = int(exit_code)
    except Exception:
        rc = -1
    try:
        dur = round(float(ms), 1)
    except Exception:
        dur = -1.0
    return {
        "ts": round(time.time(), 3),
        "chain": _clean(chain, IDENT_RE),
        "guard": _clean(guard, IDENT_RE),
        "tool_name": _clean(tool_name, IDENT_RE),
        "session_id": _clean(session_id, SID_RE),
        "exit_code": rc,
        "ms": dur,
        "path_taken": path_taken if path_taken in PATH_TAKEN else INVALID,
    }


ROTATE_LOCK_STALE_S = 30.0
_size = os.path.getsize  # indirection is a test seam for the race below


def _rotate_if_needed(path):
    """Rotate `path` to `path.1` once it reaches max_bytes().

    RACE (adversarial review 2026-09-30, finding 4): two sessions that both
    saw an over-threshold size could each os.replace() -- the second moving
    the FIRST one's fresh, near-empty log onto .1 and destroying the 5 MB
    generation just rotated. So rotation happens only under an exclusive
    O_CREAT|O_EXCL lock file, and the size is RE-CHECKED under the lock: the
    loser of the race sees the small fresh file and does nothing. Failing to
    get the lock just skips rotation this call (the next append retries). A
    lock older than ROTATE_LOCK_STALE_S (a crashed holder) is removed so
    rotation can never wedge permanently. On Windows an os.replace() of a file
    another process has open fails with a sharing violation; that is swallowed
    and appends continue on the current file, so no line is lost to rotation.
    """
    try:
        if _size(path) < max_bytes():
            return  # fast path: the overwhelmingly common case, no lock
    except Exception:
        return  # missing file -- nothing to rotate
    lock = path + ".rotate.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(lock) > ROTATE_LOCK_STALE_S:
                os.remove(lock)
        except Exception:
            pass
        return
    except Exception:
        return
    try:
        try:
            if _size(path) >= max_bytes():
                os.replace(path, path + ".1")
        except Exception:
            pass
    finally:
        try:
            os.close(fd)
        except Exception:
            pass
        try:
            os.remove(lock)
        except Exception:
            pass


def flush(records):
    """Append `records` (list of make_record() dicts) as JSON lines. Never
    raises. One open() per call, so a dispatcher pays one file append per tool
    call regardless of chain length."""
    try:
        if not records or not enabled():
            return
        path = log_path()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _rotate_if_needed(path)
        data = "".join(json.dumps(r, sort_keys=True, ensure_ascii=True) + "\n"
                       for r in records)
        with open(path, "a", encoding="ascii", newline="\n") as fh:
            fh.write(data)
    except Exception:
        pass
