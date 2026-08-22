# engineering-router.py — UserPromptSubmit hook. Non-blocking lane suggester. Always exits 0.
import sys, json, os, re

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)

# --- in-turn-approval budget reset for eos-plan-gate (2026-08-05) -------------
# WHY: measured plan-gate override rate was 32.5% (209/644) against a <15%
# target, and the DOMINANT override-reason class is verbatim "the user already
# approved this in-turn" -- e.g. "Gabriel replied 'Implement 1-3 now', that
# in-turn approval is the plan". A gate overridden 1-in-3 trains the reflex it
# exists to prevent.
#
# The plan gate itself CANNOT see prompts -- its PreToolUse payload carries only
# session_id and tool_input. This hook is the only one that sees the user's
# turn, so detection has to live here.
#
# DESIGN CHOICE, deliberate: a qualifying directive RESETS the edit budget
# (code-edits.count -> 0) rather than writing a permanent override marker.
#   * A permanent bypass would silently disable the gate for the whole session
#     after one qualifying prompt -- genuine unplanned sprawl LATER in that
#     session would go uncaught.
#   * A reset gives a fresh budget of LIMIT edits per scoped instruction, so
#     sprawl WITHIN a directive is still caught, and each new scoped directive
#     legitimately earns a new budget.
#
# Detection is deliberately CONSERVATIVE -- a false positive quietly weakens a
# safety gate, while a false negative merely costs one manual override (today's
# status quo). Requires an imperative directive AND a concrete scope signal.
_IMPERATIVE = (
    "fix", "implement", "do ", "proceed", "execute", "apply", "build",
    "run ", "add ", "make ", "update", "finish", "complete", "handle",
)
# Concrete scope signals: a numeric item reference ("items 1-3", "1 and 2"),
# an explicit plan/list reference, or a self-enumerated list in the prompt.
_NUM_REF = re.compile(
    r"\b(?:item|items|point|points|step|steps|number|numbers|#)?\s*"
    r"\d+\s*(?:-|–|to|and|,|through)\s*\d+\b")
_PLAN_REF = (
    "the plan", "pre-written plan", "top-5 plan", "top 5 plan", "the list",
    "the backlog", "these items", "those items", "the items", "all five",
    "all four", "all three", "enumerated", "as listed", "listed above",
)
_ENUM_LINE = re.compile(r"(?m)^\s*(?:\d+[.)]\s|[-*•]\s)")
# Comma/conjunction-separated item lists ("item 1, item 2 and item 3") that
# _NUM_REF's adjacent-digits form does not reach. Requires the explicit
# item/step/point noun, so bare quantities ("3 monitors and 2 keyboards")
# cannot qualify.
_ITEM_REF = re.compile(r"\b(?:item|step|point|number|#)\s*\d+\b")


def _scoped_directive_evidence(prompt_raw, prompt_lower):
    """Non-empty evidence string if this turn is an explicitly-scoped directive,
    else None. Both an imperative AND a scope signal are required."""
    if not any(w in prompt_lower for w in _IMPERATIVE):
        return None
    m = _NUM_REF.search(prompt_lower)
    if m:
        return "numeric item reference: %r" % m.group(0).strip()
    items = _ITEM_REF.findall(prompt_lower)
    if len(items) >= 2:
        return "enumerated item references (%d)" % len(items)
    for phrase in _PLAN_REF:
        if phrase in prompt_lower:
            return "explicit plan/list reference: %r" % phrase
    enum = _ENUM_LINE.findall(prompt_raw)
    if len(enum) >= 3:
        return "self-enumerated list of %d items" % len(enum)
    return None


# --- structured-prompt-as-plan recognition (2026-08-21) -----------------------
# WHY: _scoped_directive_evidence/_reset_plan_gate_budget above only RESETS an
# ALREADY-CONSUMED counter, and only on a turn AFTER the one that used up the
# budget (it is a UserPromptSubmit hook, so it needs a follow-up prompt to fire
# on). A prompt that is ITSELF a fully-staged multi-phase plan (e.g. "Phase 0:
# ... Phase 1: ... Phase 2: ... Phase 3: ...") and then gets executed straight
# through in the SAME turn never gets that follow-up turn -- the gate still
# denies on the 4th code edit, forcing a manual override for work that was
# already planned as thoroughly as /plan would have produced, just not THROUGH
# /plan. Observed live 2026-08-21 (this hook's own session).
#
# DELIBERATELY NARROWER than _scoped_directive_evidence: this writes the SAME
# PERMANENT plan-approved marker eos-plan-marker.py writes for a real /plan run
# or a docs/superpowers/plans/ file -- so the bar has to be high enough that a
# false positive is not materially different from a spurious /plan invocation.
# A bare numbered list ("do items 1-3") does NOT qualify here (that stays on
# the weaker, budget-reset-only path above) -- only an explicit multi-PHASE (or
# multi-STAGE) structure, the concrete shape "Phase 0-3" names, counts: >=2
# distinct "Phase N" / "Stage N" headers is a plan-shaped prompt almost nothing
# else produces by accident.
# Header-anchored: a bare "Phase 1"/"Stage 2" mention in ordinary prose (a due-
# diligence ESA reference -- "the Phase 1 flagged a REC, need a Phase 2 before
# closing" -- or "compare phase 1 and phase 2 of the rollout") must NOT match.
# Only a real structural header -- the number immediately followed by a colon
# or em-dash, the way a staged plan actually writes "Phase 1: ..." -- counts.
# Independent-review finding 2026-08-21 (eos-review-gate): the prior unanchored
# `\b(?:phase|stage)\s+\d+\b` matched that ESA-style prose and would have
# permanently disabled eos-plan-gate.py's edit-limit discipline for the rest of
# the session on ordinary commercial-RE language. Deliberately excludes "." and
# "-" as delimiters despite reading naturally in a header, too: a period reads
# as a sentence boundary after a bare mention ("we're now in phase 2.") and a
# hyphen reads as a range ("Phase 1-3 will take a week") -- both plausible
# false positives this gate cannot afford, since the marker it writes is
# permanent for the session. Colon and em-dash are the only unambiguous
# structural-header signals.
_PHASE_HEADER_RE = re.compile(r"\b(?:phase|stage)\s+\d+\s*[:—]", re.I)


def _written_plan_evidence(prompt_raw):
    """Evidence string if `prompt_raw` itself reads as a written, staged plan
    (>=2 DISTINCT-NUMBERED Phase/Stage headers), else None. Distinctness is
    judged by the header's number, not its raw text -- "Phase 1: ... Stage 1:
    ..." is the SAME step named twice, not two steps, and must not count as 2
    (independent-review finding 2026-08-21, non-blocking nit folded into the
    same fix)."""
    headers = set(m.group(0).lower() for m in _PHASE_HEADER_RE.finditer(prompt_raw))
    numbers = set(re.search(r"\d+", h).group(0) for h in headers)
    if len(numbers) >= 2:
        return "multi-phase prompt structure (%s)" % ", ".join(sorted(headers))
    return None


def _approve_plan_from_prompt(data, prompt_raw):
    """Write the same permanent plan-approved marker eos-plan-marker.py writes
    for a real /plan run, when THIS turn's prompt already reads as one (see
    _written_plan_evidence). Best-effort, fully silent on failure -- must never
    affect prompt handling. Auditable via the marker's own content, same as
    eos-plan-marker.py's 'lane:<skill>' convention."""
    try:
        sid = data.get("session_id")
        if not isinstance(sid, str) or not sid:
            return
        evidence = _written_plan_evidence(prompt_raw)
        if not evidence:
            return
        base = os.environ.get("EOS_SESSIONS_DIR") or \
            "C:/Users/Owner/.claude/hooks/sessions"
        sess = os.path.join(base, sid)
        os.makedirs(sess, exist_ok=True)
        with open(os.path.join(sess, "plan-approved"), "w", encoding="utf-8") as fh:
            fh.write("prompt:phase-plan (%s)" % evidence)
    except Exception:
        pass  # never let this affect the prompt path


def _reset_plan_gate_budget(data, prompt_raw, prompt_lower):
    """Reset eos-plan-gate's per-session code-edit counter when the user's turn
    already enumerates the work. Best-effort and fully silent on failure -- this
    must never affect prompt handling."""
    try:
        sid = data.get("session_id")
        if not isinstance(sid, str) or not sid:
            return
        evidence = _scoped_directive_evidence(prompt_raw, prompt_lower)
        if not evidence:
            return
        base = os.environ.get("EOS_SESSIONS_DIR") or \
            "C:/Users/Owner/.claude/hooks/sessions"
        sess = os.path.join(base, sid)
        count_file = os.path.join(sess, "code-edits.count")
        # Only act if a budget has actually been consumed -- no point creating
        # session state for a turn that has not edited anything yet.
        if not os.path.isfile(count_file):
            return
        os.makedirs(sess, exist_ok=True)
        with open(count_file, "w", encoding="ascii") as fh:
            fh.write("0")
        # Auditable, not silent: telemetry can distinguish an auto-reset from a
        # human override, so the measured override rate stays honest.
        with open(os.path.join(sess, "plan-gate-resets.log"), "a",
                  encoding="utf-8") as fh:
            fh.write("in-turn scoped directive -> budget reset (%s)\n" % evidence)
    except Exception:
        pass  # never let this affect the prompt path


# --- concurrent-session advisory (2026-08-05) ---------------------------------
# WHY: reference_concurrent_session_duplicate_hardening_work.md's 2026-08-05 entry
# logs three same-day near-collisions -- duplicate investigation/audit work by two
# sessions on the same target, discovered only by chance after the work was already
# done. None involved a contended file until too late, so claim_work.py's four
# named slugs (scoped to hooks/override-auth, open-items-tracker,
# oxford-command-center-data, repo-housekeeping) structurally could not have caught
# them. CLAUDE.md's Engineering OS already mandates checking "already-done" before
# starting any L2-L7 task, but nothing enforced it -- it depended entirely on the
# session remembering to run list_sessions/event_log.md before investing effort.
# This hook already fires on every prompt, so it is the correct trigger point (task
# START, not tool-call time -- by Write/Edit both recorded incidents were already
# finished). ADVISORY ONLY, never blocks: same fail-open posture as
# session_liveness.py's other contract ("enrichment, never a hard gate").
def _concurrent_session_note(session_id, sessions_dir=None):
    """One ASCII line naming how many OTHER live sessions are open, or "" if
    none/unknown. Never raises -- a broken or missing liveness reader must
    degrade to silence, not affect prompt routing (this runs on every turn).

    A non-string/empty session_id (e.g. a payload with no "session_id" field)
    must short-circuit to "" rather than reach other_active_sessions(): that
    reader excludes only an EXACT own-sid match, so an invalid sid never
    matches this session's own file and would otherwise count the caller as
    one of the "other" sessions -- a false, self-inclusive advisory. Mirrors
    _reset_plan_gate_budget's identical isinstance(sid, str) guard above."""
    if not isinstance(session_id, str) or not session_id.strip():
        return ""
    try:
        from session_liveness import other_active_sessions  # noqa: E402
        others = other_active_sessions(session_id, sessions_dir=sessions_dir)
    except Exception:
        return ""
    if not others:
        return ""
    return ("%d other session(s) active -- check list_sessions/event_log.md "
            "before duplicating investigation or analysis work." % len(others))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt_raw = data.get("prompt") or ""
    prompt = prompt_raw.lower()
    if not prompt.strip():
        return

    # Fix #2: only route/doctrine-check GENUINE user-prompt text. Background task-notification,
    # system-reminder, and tool-result turns arrive in this same `prompt` field; scanning them
    # produced a false DOCTRINE BLOCK (and L7 misroutes) when the notification text quoted
    # '/code-review ultra <confidential-repo>'. Treat any such non-user text as out of scope.
    system_markers = (
        "[system notification", "not user input", "<task-notification", "</task-notification",
        "task-notification>", "<system-reminder", "</system-reminder", "[background task",
        "task-result", "<tool_result", "tool result:",
    )
    if any(m in prompt for m in system_markers):
        return

    # Genuine user turn confirmed (system/notification text already returned
    # above), so a scope signal here really is Gabriel's own instruction.
    _approve_plan_from_prompt(data, prompt_raw)
    _reset_plan_gate_budget(data, prompt_raw, prompt)

    # Fix #1b: '/code-review ultra' is CLOUD review; doctrine forbids it on confidential repos.
    # The slash command itself can't be hooked, but catch the natural-language ask here.
    if any(t in prompt for t in ("code-review ultra", "ultrareview", "ultra review", "cloud review")):
        repos = ("oxford-command-center", "website-canonical", "oxford-site", "ora-pm")
        try:
            import os
            p = os.path.join(os.path.dirname(__file__), "..", "confidential-repos.json")
            with open(p, encoding="utf-8") as f:
                repos = tuple(json.load(f).get("confidential_repos", repos))
        except Exception:
            pass
        named = [r for r in repos if r in prompt]
        if named:
            print("[Engineering OS] DOCTRINE BLOCK: '/code-review ultra' is CLOUD review and is forbidden on "
                  "confidential repo(s): " + ", ".join(named) +
                  ". Use superpowers:requesting-code-review (LOCAL) instead.")
            return

    def has(*words):
        return any(w in prompt for w in words)

    # Negative-context guard: analytical/meta/scheduling prompts should not fire a lane,
    # unless the prompt opens with an explicit imperative coding command.
    analytical = (
        "explain why", "assume ", "suggest improvement", "suggest improvements",
        "what are the", "how would", "why would", "pros and cons",
        "compare the tradeoffs", "review the plan", "summarize",
        "calendar", "meeting", "remind me", "schedule a", "send an email", "lunch",
    )
    imperative_starts = ("build ", "fix ", "debug ", "refactor ", "ship ", "add a")
    stripped = prompt.lstrip()
    explicit_command = stripped.startswith(imperative_starts)
    if has(*analytical) and not explicit_command:
        return

    lanes = []
    if has("deploy", "ship", "release", "publish", "go live", "to production", "to prod"):
        lanes.append(("L7", "/ship", "release/deploy - target-aware, confirm before deploy"))
    if has("bug", "broken", "error", "failing", "fails", "doesn't work",
           "not working", "crash", "stack trace", "regression", "fix the"):
        lanes.append(("L2", "/debug", "root-cause via systematic-debugging + a failing test first"))
    if has("refactor", "clean up", "restructure", "simplify", "tidy", "extract", "rename"):
        lanes.append(("L4", "/refactor", "characterization tests first; behavior preserved"))
    if has("research", "compare", "investigate", "find out", "which library",
           "options for", "look into", "evaluate", "best way to"):
        lanes.append(("L5", "/research", "internal-first; scrub confidential terms from web queries"))
    if has("build", "add", "create", "implement", "feature", "make a",
           "write a", "scaffold", "new "):
        lanes.append(("L3", "/build", "brainstorm -> /plan -> worktree -> TDD -> local review -> land"))

    # Fix #1a: research/plan-dominant or explicit "don't code yet" prompts are NOT ship requests.
    # A prompt whose dominant intent is investigate/plan/review must not route L7 (release/deploy),
    # even when it name-drops deploy/ship/publish tokens (e.g. "...deployment patterns... before we
    # ship anything"). Drop L7 so L5 (/research) or L3 (/plan-then-build) intent wins instead.
    no_code = has("do not start coding", "don't start coding", "do not code", "don't code",
                  "dont code", "do not write code", "no coding yet", "without writing code",
                  "before you code", "before coding", "don't code yet")
    research_plan = has("research", "plan", "review", "evaluate", "audit", "investigate", "assess")
    if no_code or research_plan:
        lanes = [l for l in lanes if l[0] != "L7"]

    if not lanes:
        return

    order = {"L7": 0, "L2": 1, "L4": 2, "L5": 3, "L3": 4}  # most-specific intent wins
    lanes.sort(key=lambda x: order[x[0]])
    lane, cmd, why = lanes[0]
    other_lanes = "".join(f" {l[1]}" for l in lanes[1:])
    tail = f" Other possible:{other_lanes}." if other_lanes else ""
    note = _concurrent_session_note(data.get("session_id"))
    note_tail = f" {note}" if note else ""
    print(f"[Engineering OS] Looks like lane {lane} -> run {cmd} ({why}).{tail} "
          f"Triage first: clarify if vague, split if compound, state the lane, then proceed. Not a match? Ignore."
          f"{note_tail}")

if __name__ == "__main__":
    main()
    sys.exit(0)
