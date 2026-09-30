#!/usr/bin/env python3
"""Run the PostToolUse Bash-side hooks in ONE process instead of three
(hooks-audit 2026-09-30, Task 5).

WHAT IT REPLACES (live settings.json PostToolUse at 1370b41):

  matcher Bash                        catch_up_main.py --hook   (timeout 360)
  matcher Bash                        inline bash deploy-grep + curl  [DELETED]
  matcher mcp__a66aaa4a-...__.*       inline bash Netlify updater curl  [DELETED]
  matcher Bash                        eos-gate-sentinel.py

with ONE entry, matcher `Bash`, timeout 360. Every hook keeps its OWN original
matcher (POST_HOOKS below) and
is run only when that matcher matches the tool -- so no tool gains or loses a
hook; hooks/tests/test-posttooluse-dispatcher.py proves per-tool equivalence
against a frozen copy of the pre-change PostToolUse block. The inline
deploy-grep hook is deleted, not folded (Task 2a): it grepped the WHOLE payload
for the word "deploy" (false-firing on any output mentioning it), reported on
stderr under exit 0 (invisible), and /ship already verifies real deploys.
The inline Netlify-updater curl hook is deleted too (Gabriel, 2026-09-30): all
three netlify *-updater tools are in settings.json permissions.deny, so it
could never fire; no Netlify tool gains any PostToolUse hook from this file.

WHY A SEPARATE FILE, NOT `pretooluse-dispatcher.py --chain post`. The two
dispatchers have OPPOSITE failure semantics, and sharing a code path would let
one leak into the other:
  * PreToolUse: exit 2 BLOCKS; first 2 short-circuits the chain; a missing
    guard script FAILS CLOSED (the security layer is incomplete).
  * PostToolUse: the tool already ran, nothing here can or should block; EVERY
    hook runs regardless of what an earlier one returned; a missing hook is
    skipped (fail open); this process ALWAYS exits 0.
A `--chain post` flag would put a fail-closed missing-file branch and a
short-circuit-on-2 loop one argv typo away from the post chain. A separate
file also keeps LANDING ORDER simple: a settings.json that names this file
before it exists makes the interpreter exit 2 on PostToolUse, which surfaces a
visible error but blocks nothing -- no silent miscoverage in either direction.

EXECUTION PATHS, per hook:
  * eos-gate-sentinel -- IN-PROCESS (its main() is import-safe), with the same
    per-hook subprocess fallback the pre dispatcher uses if it cannot be loaded
    or raises. Its stdin is re-readable (same _StdinShim contract). BEHAVIOR
    NOTE: in-process, its sys.stdin.read() now sees the payload decoded as
    UTF-8 (errors="replace"); as a subprocess it saw the Windows locale code
    page (cp1252), where a non-cp1252 byte could raise and silently drop the
    gate-green marker. So a payload that used to drop no marker can now drop
    one -- a fail-open improvement (the marker is evidence a test RAN, and the
    command matched the test regex either way). Cost: a payload whose JSON is
    malformed makes the sentinel raise in-process and pays one fallback
    subprocess (the old per-call cost), still ending in exit 0.
  * catch-up-main -- stays a SUBPROCESS (it does a real fetch+merge into the
    shared ora-skills checkout; isolating it costs nothing because it now runs
    only when needed). It is spawned only when a cheap prefilter sees
    `gh pr merge` in tool_input.command (see gh_pr_merge_prefilter's docstring
    for why that is a strict SUPERSET of catch_up_main.is_ora_skills_merge()),
    so the ~65-100 ms interpreter start it used to cost on EVERY Bash call is
    now paid only on the rare merge. Its exit-0 semantics are unchanged (it is
    its own `--hook` mode, which always exits 0). TIMEOUT: the harness used to
    kill it at 360 s. The entry keeps timeout 360, and the child gets
    CATCH_UP_TIMEOUT_S = 350 so THIS process terminates catch_up_main.py
    itself before the harness kills this one (on Windows killing a parent does
    not kill its child, so without the margin the catch_up_main.py process
    would be orphaned too). SCOPED CLAIM (adversarial review 2026-09-30):
    subprocess.run(timeout=) terminates ONLY the direct child; any `git`
    grandchild catch_up_main.py has spawned keeps running, so a mid-merge git
    can still be orphaned. That is NOT a regression -- the old harness kill
    orphaned it identically -- and catch_up_main.py's own TOTAL_BUDGET_S (280)
    plus per-call git timeouts are what actually bound it, well inside both.

OUTPUT: every hook's stdout is collected and merged into ONE JSON object
(additionalContext joined with blank lines, hookEventName "PostToolUse") --
naively concatenating two JSON objects parses as nothing. A single emitter's
stdout passes through byte-for-byte.

fleet-session-hook.py is NOT folded here: Task 2c's narrowing was withheld (its
per-tool-call updates are a load-bearing liveness heartbeat -- see the audit
report), so it still fires on Bash|Task|TaskCreate|TaskUpdate|Edit|Write|
MultiEdit, and it is registered async. Folding its Bash slice in would turn an
async hook synchronous on every Bash call. eos-plan-marker,
commit-provenance-recorder, memory-nag-correction and
scheduled-task-update-postguard stay separate too: none of them fires on Bash,
so folding them would widen this entry's matcher for no process saved on the
Bash path.

Telemetry: one record per hook run, chain "post", via hooks/lib/guard_telemetry.py
(same confidentiality contract as the pre dispatcher; path_taken "skipped" when
the catch-up prefilter declines).

Stdlib only. ASCII-only. Windows (`python`).
"""
import io
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

try:
    import guard_telemetry as _telemetry  # noqa: E402
except Exception:  # noqa: BLE001
    _telemetry = None

CATCH_UP_SCRIPT = "C:/Users/Owner/ora-skills/tools/catch_up_main.py"
CATCH_UP_TIMEOUT_S = 350
SUBPROCESS_TIMEOUT_S = 60


class PostHook(object):
    def __init__(self, name, matcher, kind, prefilter=None):
        self.name = name
        self.matcher = matcher  # the hook's ORIGINAL settings.json matcher
        self.kind = kind        # "module" | "catchup"
        self.prefilter = prefilter


# ------------------------------------------------------------ catch-up prefilter
_STRIP = str.maketrans("", "", "\"'\\")
_GH_PR_MERGE = re.compile(r"(?i:gh)(?i:\.exe)?\s+pr\s+merge")


def gh_pr_merge_prefilter(payload):
    """True when catch_up_main.py could possibly act on this payload.

    SUPERSET ARGUMENT (never a false negative vs is_ora_skills_merge()):
    that function requires tool_name == "Bash", the literal substring "merge"
    in the raw command, and a shell segment whose first three UNQUOTED words
    are (basename in gh/gh.exe, case-insensitive), "pr", "merge". Its word
    scanner builds words from raw characters minus quote characters and
    backslash escapes, and separates words only by whitespace (every other
    separator also ends the segment). So in the raw text, with every `"`, `'`
    and `\\` deleted (and backslash-newline continuations joined first), such a
    segment necessarily contains "gh" or "gh.exe" (any case), whitespace,
    "pr", whitespace, "merge" contiguously -- which is exactly what the regex
    below searches for, anywhere, with no anchoring. It is a strict superset:
    it also passes `echo gh pr merge`, heredocs, comments, --help and other
    repos, all of which catch_up_main.py then rejects itself. Fuzzed against
    catch_up_main's own positive corpus in test-posttooluse-dispatcher.py."""
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return False
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return False
    command = tool_input.get("command")
    if not isinstance(command, str) or "merge" not in command:
        return False
    norm = command.replace("\\\n", "").translate(_STRIP)
    return _GH_PR_MERGE.search(norm) is not None


# ORDER: cheap first, the potentially-minutes-long catch-up last, so a
# catch-up timeout can never cost the other hooks their run.
POST_HOOKS = (
    PostHook("eos-gate-sentinel", "Bash", "module"),
    PostHook("catch-up-main", "Bash", "catchup", prefilter=gh_pr_merge_prefilter),
)

# The settings.json matcher for this dispatcher's single entry: the union of
# every POST_HOOKS matcher. Every remaining hook is `Bash`, and a matcher made
# only of name characters is an EXACT-name match in the harness
# (code.claude.com/docs/en/hooks), so the plain spelling needs no anchoring;
# test-posttooluse-dispatcher.py asserts the live entry spells this.
DISPATCHER_MATCHER = "Bash"

# Documented harness semantics (same page): a matcher made ONLY of letters,
# digits, `_`, `-`, spaces, `,` and `|` is an exact name or a list of exact
# names separated by `|` or `,`; "" and "*" match everything; anything else is
# an unanchored regex search. Case-sensitive (JavaScript regex default).
_PLAIN_MATCHER = re.compile(r"^[A-Za-z0-9_\-, |]*$")


def matcher_matches(matcher, tool_name):
    """Would the harness fire an entry with `matcher` for `tool_name`? Used to
    give every folded hook EXACTLY the trigger its own settings.json entry had."""
    if not isinstance(tool_name, str):
        return False
    if matcher in ("", "*"):
        return True
    if _PLAIN_MATCHER.match(matcher):
        names = [p.strip() for p in re.split(r"[|,]", matcher)]
        return tool_name in [n for n in names if n]
    try:
        return re.search(matcher, tool_name) is not None
    except re.error:
        return False


# ------------------------------------------------------------------ plumbing
class _StdinShim:
    """Same contract as pretooluse-dispatcher.py's: text AND .buffer reads,
    independently re-readable per hook."""

    def __init__(self, raw):
        self.buffer = io.BytesIO(raw)
        self._text = io.StringIO(raw.decode("utf-8", errors="replace"))

    def read(self, *a):
        return self._text.read(*a)

    def readline(self, *a):
        return self._text.readline(*a)

    def __iter__(self):
        return iter(self._text)

    def isatty(self):
        return False


def _load(name):
    path = os.path.join(HOOKS_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location(
        "_posthook_" + name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError("no spec for " + path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_inprocess(name, raw):
    mod = _load(name)
    main = getattr(mod, "main", None)
    if not callable(main):
        return None
    real_in, real_out, real_err = sys.stdin, sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    rc = 0
    try:
        sys.stdin, sys.stdout, sys.stderr = _StdinShim(raw), out, err
        try:
            main()
        except SystemExit as e:
            code = e.code
            rc = 0 if code is None else (code if isinstance(code, int) else 1)
    finally:
        sys.stdin, sys.stdout, sys.stderr = real_in, real_out, real_err
    return rc, out.getvalue(), err.getvalue()


def _run_subprocess(argv, raw, timeout):
    r = subprocess.run(argv, input=raw, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8", "replace"), \
        r.stderr.decode("utf-8", "replace")


def _run_module_hook(name, raw):
    """(rc, out, err, path_taken). Never raises."""
    path = os.path.join(HOOKS_DIR, name + ".py")
    if not os.path.isfile(path):
        return 0, "", ("posttooluse-dispatcher: %s missing from %s -- skipped "
                       "(PostToolUse fails open)\n" % (name, HOOKS_DIR)), "failopen"
    try:
        result = _run_inprocess(name, raw)
        if result is not None:
            return result + ("inprocess",)
    except Exception as e:  # noqa: BLE001 -- degrade to the hook's own process
        sys.stderr.write("posttooluse-dispatcher: %s in-process failed (%s); "
                         "using subprocess\n" % (name, type(e).__name__))
    try:
        return _run_subprocess([sys.executable, path], raw,
                               SUBPROCESS_TIMEOUT_S) + ("subprocess",)
    except Exception as e:  # noqa: BLE001
        return 0, "", ("posttooluse-dispatcher: %s FAILED BOTH PATHS (%s) -- "
                       "skipped\n" % (name, type(e).__name__)), "failopen"


def _run_catch_up(raw):
    if not os.path.isfile(CATCH_UP_SCRIPT):
        return 0, "", ("posttooluse-dispatcher: %s missing -- catch-up skipped\n"
                       % CATCH_UP_SCRIPT), "failopen"
    try:
        return _run_subprocess([sys.executable, CATCH_UP_SCRIPT, "--hook"], raw,
                               CATCH_UP_TIMEOUT_S) + ("subprocess",)
    except subprocess.TimeoutExpired:
        return 0, "", ("posttooluse-dispatcher: catch_up_main.py exceeded %ds "
                       "and was terminated\n" % CATCH_UP_TIMEOUT_S), "failopen"
    except Exception as e:  # noqa: BLE001
        return 0, "", ("posttooluse-dispatcher: catch_up_main.py failed to run "
                       "(%s)\n" % type(e).__name__), "failopen"


def run_hook(hook, raw, payload):
    """(rc, out, err, path_taken) for one hook. Never raises."""
    try:
        if hook.prefilter is not None and not hook.prefilter(payload):
            return 0, "", "", "skipped"
        if hook.kind == "module":
            return _run_module_hook(hook.name, raw)
        if hook.kind == "catchup":
            return _run_catch_up(raw)
        return 0, "", "", "failopen"
    except Exception as e:  # noqa: BLE001
        return 0, "", ("posttooluse-dispatcher: %s raised %s -- skipped\n"
                       % (hook.name, type(e).__name__)), "failopen"


def merge_outputs(chunks):
    """ONE valid JSON object for the harness, or "". A single chunk passes
    through verbatim; several are merged (additionalContext and systemMessage
    joined, other keys first-wins), with hookEventName forced to PostToolUse.
    Non-JSON chatter is dropped -- it is not a delivery channel."""
    chunks = [c for c in chunks if c and c.strip()]
    if not chunks:
        return ""
    if len(chunks) == 1:
        return chunks[0]
    msgs, ctxs, merged = [], [], {}
    for c in chunks:
        try:
            obj = json.loads(c)
        except (ValueError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if k == "systemMessage":
                if v:
                    msgs.append(str(v))
            elif k == "hookSpecificOutput" and isinstance(v, dict):
                hso = merged.setdefault("hookSpecificOutput", {})
                for hk, hv in v.items():
                    if hk == "additionalContext":
                        if hv:
                            ctxs.append(str(hv))
                    else:
                        hso.setdefault(hk, hv)
            else:
                merged.setdefault(k, v)
    if msgs:
        merged["systemMessage"] = "\n\n".join(msgs)
    if ctxs:
        merged.setdefault("hookSpecificOutput", {})["additionalContext"] = \
            "\n\n".join(ctxs)
    if "hookSpecificOutput" in merged:
        merged["hookSpecificOutput"]["hookEventName"] = "PostToolUse"
    return json.dumps(merged) if merged else ""


def main():
    """Always returns 0. PostToolUse hooks here never block."""
    try:
        raw = sys.stdin.buffer.read()
    except Exception:  # noqa: BLE001
        return 0
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        payload = None
    tool_name = payload.get("tool_name") if isinstance(payload, dict) else None

    ids = ("", "")
    records = []
    if _telemetry is not None:
        try:
            ids = _telemetry.ids_from_obj(payload)  # already parsed above
        except Exception:  # noqa: BLE001
            ids = ("", "")

    stdouts = []
    try:
        for hook in POST_HOOKS:
            if not matcher_matches(hook.matcher, tool_name):
                continue
            t0 = time.perf_counter()
            rc, out, err, path_taken = run_hook(hook, raw, payload)
            if _telemetry is not None:
                try:
                    records.append(_telemetry.make_record(
                        "post", hook.name, ids[0], ids[1], rc,
                        (time.perf_counter() - t0) * 1000.0, path_taken))
                except Exception:  # noqa: BLE001
                    pass
            if out and out.strip():
                stdouts.append(out)
            if err:
                try:
                    sys.stderr.write(err)
                except Exception:  # noqa: BLE001
                    pass
        merged = merge_outputs(stdouts)
        if merged:
            sys.stdout.write(merged)
    except Exception:  # noqa: BLE001 -- never let a post hook disrupt the session
        pass
    finally:
        if _telemetry is not None and records:
            try:
                _telemetry.flush(records)
            except Exception:  # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # noqa: BLE001
        pass
    sys.exit(0)
