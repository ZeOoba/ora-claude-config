"""pipe-mask-guard -- PreToolUse hook for Bash. NEVER BLOCKS; may REWRITE.

WHAT. When an EVIDENCE command (git push/commit/merge/rebase/pull, gh pr merge,
a gate, a test run, verify-push, the pre-push gates -- the list lives in
hooks/lib/bash_pipelines.py) sits in a non-last stage of a pipeline, bash
reports the LAST stage's exit status and the evidence command's own status is
gone. This guard returns the same tool input with `set -o pipefail; ` prepended
to the command (PreToolUse `updatedInput`), so the status that comes back is the
real one.

WHY A REWRITE, NOT DOCTRINE OR A BLOCK. rules.md s26 and
feedback_piped_gate_exit_masking have said "don't pipe a gate" since 2026-07-16;
it recurred 2026-09-10 and again in the 2026-10-22 /insights window (a push
reported landed through `| tail`). Written rules are read past. A block would
fire on a legitimate quick look and teach override habits. A rewrite costs the
author nothing and removes the mechanism.

PERMISSION SAFETY -- the two properties that make a rewrite acceptable here:
  1. THIS GUARD never emits a permissionDecision. `allow` would skip the
     permission prompt for the rewritten command (code.claude.com/docs/en/hooks)
     -- a permission widening this guard has no business making. (Caveat: the
     dispatcher's emit_stdout can MERGE another guard's permissionDecision into
     the same output object as this guard's updatedInput, so "never combined
     with allow" is not a property of the pipeline as a whole. Deny rules still
     win over any hook decision, and rule 2 below keeps the rewrite from
     dodging them.)
  2. Permission rules are matched against the input the hook RETURNS. A prefix
     could make a whole-string deny rule (`Bash(git push --force*)`) stop
     matching. So if any Bash deny rule in the user settings matches the
     ORIGINAL command, any of its pipelines or stages, or any stage with its
     env assignments and transparent wrappers stripped (bp.command_words),
     nothing is rewritten; and if the deny list cannot be read at all, nothing
     is rewritten either.

SCOPE. Evidence commands only, and only a SINGLE-STATEMENT command: one
pipeline, optionally behind pure `cd <dir> &&` hops (pipefail does not change
cd's exit status, and `cd X && <gate> | tail` is the most common shape). The
prefix is command-wide, so with `;` / `||` / `&` / newline-separated statements
it would also turn a neighbouring `git log | head -1` into a SIGPIPE 141 or a
`grep | tail` into a no-match failure, even though the push landed -- such
commands are left untouched (status quo: the exit status stays masked, per
rules.md s26 read the output, not the status). Every non-last stage must itself be an evidence command or tee/cat; a
look-only stage (grep, head, ...) in the middle disqualifies the rewrite.
Look-only runs (`pytest --collect-only`, `--listTests`, `--help`, `--version`)
are not evidence. Already-guarded commands (`set ... pipefail` / `PIPESTATUS`)
are left alone. A LAST stage that can exit before EOF also changes the call
(bash_pipelines.early_exit_kind). A PREDICATE (`grep -q/-l/-L`) always
disqualifies the rewrite: pipefail would make it report the evidence command's
failure instead of grep's. A LIMITER (`| head -N`, `grep -m`, `sed 1q`, `read`,
`less`, `more`, awk `exit`) disqualifies it only for CHATTY evidence (test
runners, gates), which it would SIGPIPE to rc 120/141 on a passing run; after
short-output evidence (`git push/commit/merge`, `gh pr merge`) the rewrite
stays, because those finish before the limiter quits and a bare `| head` is
exactly how a rejected push gets reported as landed. Known residual
(still rewritten, can still show rc 141 on a passing run): interpreters that stop
reading (`python -c`, `perl -ne ... last`), `sh -c`/`bash -c` wrappers, wrappers
that take options (`env -u/-i`, `stdbuf`, `nice`), script files (`sed -f`,
`awk -f`), `awk nextfile`, `dd count=`, and `head -n -N` is skipped needlessly.

FAIL-OPEN. Any error -> no output, exit 0 -> the command runs as written
(status quo). There is no per-call confirmation that the harness applied the
rewrite; a PostToolUse landing check that would report it is a planned
follow-up, so until then the guard's effect is verified by its tests only.

Dispatcher: LAST in BASH_GUARD_CHAIN, so any blocking guard short-circuits
before a rewrite is emitted. Stdlib only. ASCII-only.
"""
import fnmatch
import json
import os
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

DEFAULT_SETTINGS = (
    os.path.join(os.path.expanduser("~"), ".claude", "settings.json"),
    os.path.join(os.path.expanduser("~"), ".claude", "settings.local.json"),
)


def _settings_files():
    env = os.environ.get("ORA_PIPEMASK_SETTINGS")
    if env:
        return [p for p in env.split(os.pathsep) if p], True
    return list(DEFAULT_SETTINGS), False


def bash_deny_patterns():
    """fnmatch patterns from every Bash(...) deny rule, or None when the
    PRIMARY settings file cannot be read (the caller then refuses to rewrite).
    An absent settings.local.json is normal and not an error."""
    files, explicit = _settings_files()
    pats = []
    for i, path in enumerate(files):
        required = explicit or i == 0
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            if required:
                return None
            continue
        except Exception:  # noqa: BLE001
            return None
        deny = ((data or {}).get("permissions") or {}).get("deny") or []
        for rule in deny:
            if isinstance(rule, str) and rule.startswith("Bash(") and rule.endswith(")"):
                body = rule[5:-1].replace(":*", "*")
                if body:
                    pats.append(body)
    return pats


def _statement_texts(command, bp):
    """Every string a Bash deny rule could be matched against: the raw command,
    each pipeline, each stage, and each stage with leading NAME=value
    assignments and transparent wrappers (time, env, timeout N) stripped."""
    texts = [command.strip()]
    for pipe in bp.pipelines(command) or []:
        texts.append(" | ".join(" ".join(stage) for stage in pipe))
        for stage in pipe:
            texts.append(" ".join(stage))
            texts.append(" ".join(bp.command_words(stage)))
    return texts


def decide(payload):
    """The updatedInput dict to emit, or None to leave the command untouched."""
    import bash_pipelines as bp
    if not isinstance(payload, dict):
        return None
    if payload.get("tool_name") not in (None, "Bash"):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    if bp.has_pipefail(command):
        return None
    if not bp.pipefail_targets(command):
        return None
    pats = bash_deny_patterns()
    if pats is None:
        return None
    for text in _statement_texts(command, bp):
        for pat in pats:
            if fnmatch.fnmatchcase(text, pat):
                return None
    updated = dict(tool_input)
    updated["command"] = bp.PIPEFAIL_PREFIX + command
    return updated


def main():
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8", "replace"))
        updated = decide(payload)
    except Exception:  # noqa: BLE001 -- fail open: command runs as written
        return
    if updated is None:
        return
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": updated,
    }}))


if __name__ == "__main__":
    main()
    sys.exit(0)
