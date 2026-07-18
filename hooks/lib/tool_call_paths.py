"""Shared tool-call -> write-target normalization for the ORA write-guard hooks.

WHY THIS MODULE EXISTS (2026-07-18, write-guard architecture hardening). Two guards
-- memory-index-guard.py and registry-write-guard.py -- EACH independently
rediscovered the same blind spot on 2026-07-14: a guard written for the native
Write/Edit/MultiEdit tool-call shapes is silently bypassed by Desktop Commander's
write_file/edit_block (different tool names AND a different path field: "path", not
"file_path"), and one real regression reached disk that way (MEMORY.md line 85,
170 chars). That was a guard-ARCHITECTURE gap, not a one-off bug: every guard
re-parsed tool calls from scratch, so every guard shipped with whatever shapes its
author remembered that day. This module is the ONE place that knowledge lives. A new
write-guard imports from here; it does not re-enumerate tool shapes.

WHAT IT COVERS (the write-capable tool-call shapes known in this stack):
  file  : Write / Edit / MultiEdit           (file_path)
          NotebookEdit                        (notebook_path)
          DC write_file                       ("path" -- live schema -- OR "file_path",
                                               both arg spellings seen historically)
          DC edit_block                       (file_path, with "path" fallback)
  move  : DC move_file                        (source AND destination -- moving a file
                                               away deletes it; moving onto a path
                                               overwrites it; both are writes)
  shell : Bash, DC start_process,             (command / input text -- BEST-EFFORT:
          DC interact_with_process             a shell command cannot be statically
                                               resolved to file targets; shell_analysis
                                               flags may_write and NEVER claims a safe
                                               resolution -- resolved is always False,
                                               so a consumer must treat a may_write
                                               shell command as unresolved rather than
                                               silently passing it through as safe)

"DC" means BOTH live tool-name prefixes (mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ -- both exist in this stack, and
prefix-coverage was half of the 2026-07-14 gap).

BEHAVIOR-PRESERVATION CONTRACT for the legacy guards: both guards historically
applied `tool_input.get("file_path") or tool_input.get("path")` for ANY tool name.
primary_write_path() keeps that generic fallback for unknown tool names, so
refactoring a guard onto this module changes HOW it parses, never WHAT it blocks.

SAFETY POSTURE: this module never raises on malformed input -- every function
returns None / [] / False for shapes it cannot read. Fail-open vs fail-closed is
the CALLING GUARD's decision, not this module's.

Stdlib only. ASCII-only. Windows (`python`).
"""
import os
import re
import unicodedata
from collections import namedtuple

# --------------------------------------------------------------------- tool names
DC_PREFIXES = (
    "mcp__Desktop_Commander__",
    "mcp__plugin_desktop-commander_desktop-commander__",
)


def _dc_names(suffix):
    return frozenset(prefix + suffix for prefix in DC_PREFIXES)


DC_WRITE_FILE_NAMES = _dc_names("write_file")
DC_EDIT_BLOCK_NAMES = _dc_names("edit_block")
DC_MOVE_FILE_NAMES = _dc_names("move_file")
DC_WRITE_PDF_NAMES = _dc_names("write_pdf")
DC_START_PROCESS_NAMES = _dc_names("start_process")
DC_INTERACT_PROCESS_NAMES = _dc_names("interact_with_process")

NATIVE_FILE_TOOLS = frozenset(("Write", "Edit", "MultiEdit"))
NOTEBOOK_TOOLS = frozenset(("NotebookEdit",))


# MCP tool-family recognition is SUFFIX-based, not an exact-name allowlist: the
# 2026-07-14 gap was partly a PREFIX-coverage gap (mcp__Desktop_Commander__ vs
# mcp__plugin_desktop-commander_desktop-commander__ -- both live), and a THIRD
# prefix (a renamed/re-registered connector) would silently re-open an exact-name
# matcher. Suffix matching closes the whole family at once; a false hit on some
# unrelated future "..._write_file" tool merely subjects it to write-guard
# scrutiny, which is the correct default for a tool named like a writer
# (deny-by-default, same direction as ora-autonomy-gate check_mcp's Round 3 fix).
def _mcp_family(tool_name, suffix):
    return isinstance(tool_name, str) and tool_name.startswith("mcp__") \
        and tool_name.endswith(suffix)


def is_dc_write_file(tool_name):
    return _mcp_family(tool_name, "write_file")


def is_dc_edit_block(tool_name):
    return _mcp_family(tool_name, "edit_block")


def is_dc_move_file(tool_name):
    return _mcp_family(tool_name, "move_file")


def is_dc_write_pdf(tool_name):
    return _mcp_family(tool_name, "write_pdf")


def is_shell_tool(tool_name):
    return tool_name == "Bash" or _mcp_family(tool_name, "start_process") \
        or _mcp_family(tool_name, "interact_with_process")


def is_file_tool(tool_name):
    return tool_name in NATIVE_FILE_TOOLS or tool_name in NOTEBOOK_TOOLS \
        or is_dc_write_file(tool_name) or is_dc_edit_block(tool_name) \
        or is_dc_write_pdf(tool_name)


# Exact-name sets kept for consumers that need enumeration (legacy guards' content
# simulation, the SHAPES registry, settings matchers) -- recognition FUNCTIONS above
# are what the normalization paths use.
SHELL_TOOLS = frozenset(("Bash",)) | DC_START_PROCESS_NAMES | DC_INTERACT_PROCESS_NAMES
FILE_TOOLS = (NATIVE_FILE_TOOLS | NOTEBOOK_TOOLS | DC_WRITE_FILE_NAMES
              | DC_EDIT_BLOCK_NAMES | DC_WRITE_PDF_NAMES)
WRITE_CAPABLE_TOOLS = FILE_TOOLS | DC_MOVE_FILE_NAMES | SHELL_TOOLS


def is_write_capable(tool_name):
    return tool_name in WRITE_CAPABLE_TOOLS or is_file_tool(tool_name) \
        or is_dc_move_file(tool_name) or is_shell_tool(tool_name)


# --------------------------------------------------------------------- normalization
# Unicode categories stripped ON TOP OF NFKC, mirroring ora-autonomy-gate.py's
# _normalize_for_matching (Round 3 adversarial finding, 2026-07-17): Cf (zero-width
# space, RTL override, soft hyphen, ...) and Mn (combining marks) inserted MID-WORD
# break substring/word-boundary matching invisibly. Legitimate command/path text has
# no legitimate reason to contain either category.
_STRIP_CATEGORIES = ("Cf", "Mn")


def normalize_text(text):
    """NFKC-fold compatibility Unicode forms, then strip invisible format/combining
    characters, so marker matching sees what a human reads. Returns "" on non-str."""
    if not isinstance(text, str):
        return ""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded
                   if unicodedata.category(ch) not in _STRIP_CATEGORIES)


def resolve_path(path):
    """Case-normalized, junction/symlink-resolved absolute form of `path`.

    realpath() follows Windows junctions/symlinks to their real target even when the
    final component does not exist yet (the ordinary Write-a-new-file case) -- the
    same junction-evasion fix ora-autonomy-gate.py's check_file_write adopted
    2026-07-17. Falls back to plain abspath on OS errors. Known residual gaps, same
    as the autonomy gate's: a relative path evaluated against a different effective
    cwd, and a HARDLINK (two equally-real names for one inode -- no target to
    resolve)."""
    try:
        return os.path.normcase(os.path.realpath(path))
    except (OSError, ValueError):
        try:
            return os.path.normcase(os.path.abspath(path))
        except (OSError, ValueError):
            return os.path.normcase(path)


def _clean_str(value):
    return value if isinstance(value, str) and value else None


# --------------------------------------------------------------------- file targets
WriteTarget = namedtuple("WriteTarget", "tool_name raw_path path operation")
# operation is one of: "write", "edit", "notebook-edit", "move-source", "move-dest"


def primary_write_path(tool_name, tool_input):
    """The single file path a direct file-write tool call targets, or None.

    This is the drop-in replacement for the legacy guards' hand-rolled
    `tool_input.get("file_path") or tool_input.get("path")` -- including that exact
    generic fallback for tool names not otherwise listed, so adopting this function
    is behavior-preserving for them."""
    if not isinstance(tool_input, dict):
        return None
    if tool_name in NOTEBOOK_TOOLS:
        return _clean_str(tool_input.get("notebook_path")) \
            or _clean_str(tool_input.get("file_path"))
    if is_dc_write_pdf(tool_name):
        return _clean_str(tool_input.get("file_path")) \
            or _clean_str(tool_input.get("path")) \
            or _clean_str(tool_input.get("output_path"))
    # DC write_file: the live DC schema uses "path"; older payloads used "file_path"
    # -- accept both. Field ORDER is file_path-first for every branch below, because
    # that is the legacy guards' exact historical behavior (`file_path or path`) and
    # this function's contract is behavior preservation. A payload carrying BOTH
    # fields with different values is ambiguous under any single-path answer -- a
    # guard that must be decoy-proof against that shape should use write_targets(),
    # which returns a target per distinct candidate path.
    return _clean_str(tool_input.get("file_path")) \
        or _clean_str(tool_input.get("path"))


def _file_operation(tool_name):
    if tool_name in ("Edit", "MultiEdit") or is_dc_edit_block(tool_name):
        return "edit"
    if tool_name in NOTEBOOK_TOOLS:
        return "notebook-edit"
    return "write"  # Write, DC write_file, DC write_pdf, anything else file-shaped


def write_targets(tool_name, tool_input):
    """Every file path this tool call writes, as WriteTarget tuples with `path`
    resolved (absolute, case-normalized, junction-followed). Shell tools return []
    -- use shell_analysis() for those; they cannot be statically resolved."""
    if not isinstance(tool_input, dict):
        return []
    if is_dc_move_file(tool_name):
        targets = []
        src = _clean_str(tool_input.get("source"))
        dst = _clean_str(tool_input.get("destination"))
        if src:
            targets.append(WriteTarget(tool_name, src, resolve_path(src),
                                       "move-source"))
        if dst:
            targets.append(WriteTarget(tool_name, dst, resolve_path(dst),
                                       "move-dest"))
        return targets
    if is_shell_tool(tool_name):
        return []
    if is_file_tool(tool_name):
        op = _file_operation(tool_name)
        # DECOY DEFENSE: a payload may carry more than one plausible path field
        # (e.g. DC write_file with both "path" -- the live schema field the tool
        # actually honors -- and "file_path"). A gate checking only one of them can
        # be steered onto the innocent value while the tool writes the other. So a
        # path-gating consumer gets a target for EVERY distinct candidate, not just
        # primary_write_path()'s single legacy-ordered answer.
        candidates = []
        for field in ("file_path", "path", "notebook_path", "output_path"):
            raw = _clean_str(tool_input.get(field))
            if raw is not None and raw not in candidates:
                candidates.append(raw)
        return [WriteTarget(tool_name, raw, resolve_path(raw), op)
                for raw in candidates]
    return []


# --------------------------------------------------------------------- shell analysis
ShellAnalysis = namedtuple("ShellAnalysis", "tool_name command may_write resolved")

# Mutating shell/REPL verbs. Superset of ora-autonomy-gate.py's SITE_WRITE_INDICATORS
# plus REPL-flavored writers (interact_with_process feeds a live python/node shell).
# Breadth over precision, per the autonomy-gate doctrine: a false positive costs a
# retry; a false negative silently bypasses a guard.
SHELL_WRITE_INDICATORS = (
    ">", "cp ", "copy ", "mv ", "move ", "rm ", "del ", "remove-item",
    "set-content", "add-content", "out-file", "tee ", "new-item", "mkdir ",
    "touch ", "ren ", "rename ", "sed -i", "dd ",
    # PowerShell item cmdlets (REFUTE 2026-07-18: "move " never matches
    # "move-item" -- a Move-Item onto settings.json reached exit 0 before this)
    "move-item", "copy-item", "rename-item",
    # REPL / scripting writers
    "open(", "write_text", "write_bytes", "writefile", "shutil.", "os.remove",
    "os.rename", "os.replace", "unlink(", "rmtree",
)
# fd-duplication (2>&1, >&2, &>) and null-device (2>/dev/null, >nul) redirects write
# nothing -- must not trip the bare ">" indicator (autonomy-gate 2026-07-09/10 fixes).
_FD_DUP_RE = re.compile(r"\d*>&\d*|&>{1,2}")
_NULL_REDIRECT_RE = re.compile(r"\d*>\s*(?:/dev/null|nul)\b", re.IGNORECASE)
# git verbs that REWRITE working-tree files (REFUTE 2026-07-18: `git -C ~/.claude
# checkout main -- hooks/` rewrites the live governance layer with no classic write
# verb in its text -- and the verb is NOT adjacent to "git", so a literal
# "git checkout" substring also missed it; live-proven). Matches "git", then any
# same-segment args (no |;&), then a mutating verb as a whole word. Read-only git
# (log/diff/status/show/ls-files) is deliberately absent.
GIT_MUTATE_RE = re.compile(
    r"\bgit\b[^|;&\n]*?\b(checkout|restore|reset|apply|stash|merge|rebase|"
    r"cherry-pick|clean|revert|pull|switch)\b", re.IGNORECASE)


def _shell_text(tool_name, tool_input):
    if not isinstance(tool_input, dict):
        return None
    if _mcp_family(tool_name, "interact_with_process"):
        return tool_input.get("input")
    return tool_input.get("command")


def shell_may_write(command):
    """True if the command text carries a write-shaped verb/redirect. Static text
    analysis only -- value indirection (variables, concatenation, files read at run
    time) is a documented structural ceiling of this approach (see
    ora-autonomy-gate.py's HONEST LIMIT section); callers must not treat False as
    proof of read-only-ness for adversarial input."""
    if not isinstance(command, str):
        return False
    lowered = normalize_text(command).lower()
    lowered = _FD_DUP_RE.sub(" ", lowered)
    lowered = _NULL_REDIRECT_RE.sub(" ", lowered)
    if GIT_MUTATE_RE.search(lowered):
        return True
    return any(ind in lowered for ind in SHELL_WRITE_INDICATORS)


def shell_analysis(tool_name, tool_input):
    """ShellAnalysis for a shell-carrying tool call, else None.

    resolved is ALWAYS False: this module cannot statically resolve a shell command
    to its file targets. A consumer guard must therefore do its own marker matching
    on the (normalized) command text and must NOT interpret may_write=True with no
    marker hit as "safe" -- it is merely "unresolvable", the honest limit."""
    if not is_shell_tool(tool_name):
        return None
    text = _shell_text(tool_name, tool_input)
    if not isinstance(text, str):
        text = ""
    return ShellAnalysis(tool_name, text, shell_may_write(text), False)


# --------------------------------------------------------------------- shape registry
class Shape(object):
    """One write-capable tool-call shape, with a payload factory for tests.

    build(path, content=..., old=..., new=...) returns a tool_input dict that
    performs (or, for shell shapes, textually implies) a write to `path`. The
    coverage meta-test iterates SHAPES x guards so no future guard can ship covering
    only the shapes its author remembered."""

    def __init__(self, name, tool_name, kind, build):
        self.name = name
        self.tool_name = tool_name
        self.kind = kind  # "file" | "move" | "shell"
        self._build = build

    def build(self, path, content="x", old="OLD", new="NEW"):
        return self._build(path, content, old, new)

    def __repr__(self):
        return "Shape(%s)" % self.name


def _build_shapes():
    shapes = [
        Shape("native-write", "Write", "file",
              lambda p, c, o, n: {"file_path": p, "content": c}),
        Shape("native-edit", "Edit", "file",
              lambda p, c, o, n: {"file_path": p, "old_string": o, "new_string": n}),
        Shape("native-multiedit", "MultiEdit", "file",
              lambda p, c, o, n: {"file_path": p,
                                  "edits": [{"old_string": o, "new_string": n}]}),
        Shape("native-notebookedit", "NotebookEdit", "file",
              lambda p, c, o, n: {"notebook_path": p, "new_source": c}),
        Shape("bash", "Bash", "shell",
              lambda p, c, o, n: {"command": 'echo %s > "%s"' % (c, p)}),
    ]
    for i, prefix in enumerate(DC_PREFIXES):
        tag = "" if i == 0 else "-plugin"
        shapes.extend([
            Shape("dc-write-file%s" % tag, prefix + "write_file", "file",
                  lambda p, c, o, n: {"path": p, "content": c}),
            Shape("dc-write-file-filepath-arg%s" % tag, prefix + "write_file", "file",
                  lambda p, c, o, n: {"file_path": p, "content": c}),
            Shape("dc-edit-block%s" % tag, prefix + "edit_block", "file",
                  lambda p, c, o, n: {"file_path": p, "old_string": o,
                                      "new_string": n}),
            Shape("dc-move-file-dest%s" % tag, prefix + "move_file", "move",
                  lambda p, c, o, n: {"source": "C:/Users/Owner/other/src.tmp",
                                      "destination": p}),
            Shape("dc-move-file-source%s" % tag, prefix + "move_file", "move",
                  lambda p, c, o, n: {"source": p,
                                      "destination": "C:/Users/Owner/other/dst.tmp"}),
            Shape("dc-write-pdf%s" % tag, prefix + "write_pdf", "file",
                  lambda p, c, o, n: {"path": p, "content": c}),
            Shape("dc-start-process%s" % tag, prefix + "start_process", "shell",
                  lambda p, c, o, n: {"command": 'cmd /c echo %s > "%s"' % (c, p)}),
            Shape("dc-interact-with-process%s" % tag,
                  prefix + "interact_with_process", "shell",
                  lambda p, c, o, n: {"pid": 1,
                                      "input": "open(r'%s','w').write('%s')" % (p, c)}),
        ])
    return tuple(shapes)


SHAPES = _build_shapes()
