# engineering-router.py — UserPromptSubmit hook. Non-blocking lane suggester. Always exits 0.
import sys, json

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt = (data.get("prompt") or "").lower()
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
    others = "".join(f" {l[1]}" for l in lanes[1:])
    tail = f" Other possible:{others}." if others else ""
    print(f"[Engineering OS] Looks like lane {lane} -> run {cmd} ({why}).{tail} "
          f"Triage first: clarify if vague, split if compound, state the lane, then proceed. Not a match? Ignore.")

if __name__ == "__main__":
    main()
    sys.exit(0)
