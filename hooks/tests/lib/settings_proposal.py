"""The hooks-audit (2026-09-30) settings.json proposal, as CODE rather than a
snapshot, so tests are meaningful BEFORE and AFTER it is applied.

WHY (adversarial review 2026-09-30, finding 1): the first cut had three tests
silently prefer an untracked _proposed/settings.json over settings.json --
green only in the authoring worktree, red on every fresh clone and in the
pre-push gate. Instead, a test now calls effective(live_settings):

  * state "applied" -- live settings.json already carries the proposal
    (post-apply): it is tested as-is.
  * state "pending" -- live settings.json carries none of it (pre-apply): the
    proposal is applied IN MEMORY by apply() and the result is tested, and the
    tests separately keep asserting the live file's own untouched wiring.
  * state "partial" -- one half applied, the other not: that is a botched
    apply, and effective() raises so every test goes red.

_proposed/settings.json is only the rendered artifact of apply() for a human
to review; test-matcher-coverage.py asserts the two agree. The CLI renders or
checks, and NEVER writes in place:

    python hooks/tests/lib/settings_proposal.py --status <settings.json>
    python hooks/tests/lib/settings_proposal.py --render <settings.json> <out.json>

Stdlib only. ASCII-only. Windows (`python`).
"""
import copy
import hashlib
import json
import sys

PY = "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe"
HOOKS = "C:/Users/Owner/.claude/hooks/"
# Still needed to RECOGNIZE the folded (deleted) inline Netlify-updater entry;
# the dispatcher itself no longer runs any Netlify check (Gabriel, 2026-09-30).
NETLIFY_MATCHER = "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__.*"
POST_DISPATCHER_MATCHER = "Bash"
POST_DISPATCHER_CMD = PY + ' "' + HOOKS + 'posttooluse-dispatcher.py"'
ASCII_CMD = PY + ' "' + HOOKS + 'ascii-only-guard.py"'
# sha256 of settings.json at 1370b41 (the file the proposal was authored
# against), computed over LF-normalized bytes so a CRLF (autocrlf) checkout of
# the same content still matches -- see normalized_sha256().
BASE_SHA256 = "02729fffb3d43ef3ef7239e782e5373fc233cabe2185667db4eaa67448fa7a06"


class ProposalError(Exception):
    pass


def _cmds(entry):
    return " ".join(h.get("command", "") for h in entry.get("hooks", []))


def _entry_sha(entry):
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()


# EXACT identity of the four PostToolUse entries the post dispatcher replaces,
# as they stood at 1370b41: sha256 of json.dumps(entry, sort_keys=True), i.e.
# matcher, command, timeout and every other field. Re-review 2026-09-30
# finding C2: a SUBSTRING match let an edited entry (e.g. eos-gate-sentinel
# given a new flag and timeout 999) still read as "pending", and apply() then
# silently dropped that edit. Now any change to a folded entry makes the state
# "partial", which raises in effective() and fails every test loudly.
FOLDED_ENTRY_SHA256 = {
    "6fff6103d72c0068082658f80f90aac1bb416e592e362164f9a5c84a671f5de0": "catch-up-main",
    "90c20ebadfb0f04ab305d8fe62bb697dc01cc9c129a5986ef8e683107686e652": "deploy-grep-curl",
    "fc458656571ab4c9a9f325664fbf06113ab085ea177f53d3a1227e839ab5f000": "netlify-updater-check",
    "09c93e1f4b9ba8bb395c9c93289372640efbe436624df32f10b5223f7d5c1925": "eos-gate-sentinel",
}


def _is_folded_post_entry(entry):
    """EXACTLY one of the four 1370b41 PostToolUse entries being folded."""
    return _entry_sha(entry) in FOLDED_ENTRY_SHA256


def _looks_folded(entry):
    """A LOOSE resemblance to a folded entry -- used only to detect an entry
    that was folded-in-spirit but edited (which must read as partial)."""
    c, m = _cmds(entry), entry.get("matcher")
    return ((m == "Bash" and "catch_up_main.py" in c)
            or ('grep -o \\"deploy\\"' in c or 'grep -o "deploy"' in c)
            or (m == NETLIFY_MATCHER and "updater" in c and "curl" in c)
            or ("eos-gate-sentinel.py" in c))


def _dispatcher_entry():
    return {"matcher": POST_DISPATCHER_MATCHER,
            "hooks": [{"type": "command", "command": POST_DISPATCHER_CMD,
                       "timeout": 360}]}


def state(settings):
    """"pending", "applied" or "partial" -- see module docstring. pending is
    EXACT: all four folded entries byte-for-byte as at 1370b41 and no edited
    look-alike. applied is STRUCTURAL: no exact or look-alike folded entry
    remains, and exactly one dispatcher entry and one ascii entry exist,
    whatever their timeouts / paths / extra hooks."""
    hooks = settings.get("hooks", {})
    post = hooks.get("PostToolUse", [])
    pre = hooks.get("PreToolUse", [])
    exact = sorted(FOLDED_ENTRY_SHA256[_entry_sha(e)] for e in post
                   if _is_folded_post_entry(e))
    look = sum(1 for e in post if _looks_folded(e))
    disp_any = [e for e in post if "posttooluse-dispatcher.py" in _cmds(e)]
    ascii_any = [e for e in pre if "ascii-only-guard.py" in _cmds(e)]
    if (not disp_any and not ascii_any and look == 4
            and exact == sorted(FOLDED_ENTRY_SHA256.values())):
        return "pending"
    # APPLIED is STRUCTURAL, not content-exact (round-3 review, C8a): after the
    # apply, routine edits -- a longer dispatcher timeout, a timeout on the
    # ascii hook, a new interpreter path, a second hook on the ascii entry --
    # must not read as "partial" and turn the pre-push gate red. Content is
    # judged by the tests that own it (E3-E7, R1, A3, write-guard routing).
    if not exact and look == 0 and len(disp_any) == 1 and len(ascii_any) == 1:
        return "applied"
    return "partial"


def apply(settings):
    """A NEW dict: `settings` with the proposal applied. Raises ProposalError
    unless the input is exactly in the "pending" state."""
    if state(settings) != "pending":
        raise ProposalError("apply() needs a pending settings file, got %r"
                            % state(settings))
    new = copy.deepcopy(settings)
    hooks = new["hooks"]
    kept = [e for e in hooks["PostToolUse"] if not _is_folded_post_entry(e)]
    hooks["PostToolUse"] = [_dispatcher_entry()] + kept
    pre = hooks["PreToolUse"]
    idx = [i for i, e in enumerate(pre) if "registry-write-guard.py" in _cmds(e)]
    if len(idx) != 1:
        raise ProposalError("expected exactly one registry-write-guard entry, "
                            "found %d" % len(idx))
    pre.insert(idx[0] + 1, {
        "matcher": pre[idx[0]]["matcher"],
        "hooks": [{"type": "command", "command": ASCII_CMD}],
    })
    return new


def effective(settings):
    """The settings the branch's wiring should be judged on (see module doc)."""
    st = state(settings)
    if st == "applied":
        return settings
    if st == "pending":
        return apply(settings)
    raise ProposalError(
        "settings.json is PARTIALLY migrated (the posttooluse-dispatcher / "
        "ascii-only-guard proposal is half-applied) -- finish or revert it")


def normalized_sha256(raw):
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def render(settings):
    return json.dumps(settings, indent=2) + "\n"


def main(argv):
    if len(argv) >= 2 and argv[0] == "--status":
        raw = open(argv[1], "rb").read()
        s = json.loads(raw.decode("utf-8-sig"))
        sha = normalized_sha256(raw)
        print("state: %s" % state(s))
        print("sha256 (LF-normalized): %s (%s the 1370b41 base the proposal "
              "was authored on)"
              % (sha, "MATCHES" if sha == BASE_SHA256 else "DIFFERS FROM"))
        return 0
    if len(argv) >= 3 and argv[0] == "--render":
        if argv[1] == argv[2]:
            sys.stderr.write("refusing to render in place\n")
            return 2
        s = json.loads(open(argv[1], "rb").read().decode("utf-8-sig"))
        with open(argv[2], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(apply(s)))
        print("rendered %s -> %s" % (argv[1], argv[2]))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
