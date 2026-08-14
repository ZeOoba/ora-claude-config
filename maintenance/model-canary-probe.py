#!/usr/bin/env python3
"""OBSERVE which model each CC/MCP scheduled task actually fires on, and check
its [MODEL: ...] tag against that observation.

Companion to dangling-mutation-probe.py CHECK B, not a duplicate: that check
detects that an observation is NEEDED (a real-id tag older than the current
lineup anchor on a task that has since fired). This probe MAKES the
observation. Promoted to maintenance/ 2026-08-09 after a Gabriel-directed
sweep closed 4 tag gaps by hand -- the method is entirely mechanical, so
leaving it as manual transcript archaeology guaranteed the gaps would recur
(every sweep since 2026-07-13 has been cleaning up the same class).

METHOD -- the transcript cut (authoritative; reference_scheduled_task_model_standard.md).
  Locate the `<scheduled-task name=` injection row FIRST, then cut at the first
  genuine human turn AFTER it. Cutting at "first user-type row" is WRONG: rows
  0-4 are hooks/system and the injection itself sits around idx 5, so a naive
  cut yields an empty scheduled portion and reports the whole run as
  interactive. Only assistant rows between injection and cut are counted.

WHY NOT the one-call `get_session` model field: it reports the session's
CURRENT configured model, not what fired. For a session that continued
interactively (a human ran /model afterwards) it silently contradicts the
transcript. Confirmed twice -- ora-appsec-sweep 2026-07-22, and
ora-lease-snapshot-refresh 2026-08-09, where the field read claude-sonnet-5
while all 34 scheduled-portion messages were claude-opus-5. Reading the
transcript directly sidesteps the trap entirely; `went_interactive` is
reported so a consumer can see when the shortcut would have lied.

TWO NON-OBVIOUS DATA FACTS this probe depends on:
  1. Task descriptions are NOT in the registry. scheduled-tasks.json holds only
     {id, cronExpression, enabled, filePath, createdAt, lastRunAt, ...}; the
     description that list_scheduled_tasks returns is composed from each task's
     SKILL.md frontmatter. So tags are read from filePath, never the registry.
  2. Frontmatter here is parsed LINE-WISE, not with yaml.safe_load -- ORA
     SKILL.md frontmatter is deliberately not strict YAML and ~97/147 fleet
     files fail a strict parse BY DESIGN (reference_skill_frontmatter_lenient_parse).

SCOPE (reference_scheduled_task_model_standard.md "Tag scope & required fields"):
  only ENABLED RECURRING CC/MCP tasks. One-time (fireAt) and disabled tasks are
  EXEMPT -- they are MODEL-N/A, never a gap.

NEVER WRITES to any task. Report-only. A missing/pruned transcript is
UNVERIFIABLE, never folded into "clean" -- a zero that could mean "couldn't
look" is a failure, not a pass (feedback_verified_null_vs_inferred_null).

Run: python model-canary-probe.py [--max-sessions-per-task N] [--json]
Exit 0 = no findings, 1 = findings, 2 = probe could not run its own checks.
NOTE for the ora-task-integrity-guard caller: STEP 2.5 is informational by
doctrine, so NONE of these exit codes is a STEP-3 alarm condition. Exit 2 must
still be surfaced on the GUARD OK line so "couldn't look" never reads as clean.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: reported by main() as exit 2, never a silent pass

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

STATE_DIR = os.path.join(HERE, "_state")
LOG = os.path.join(STATE_DIR, "model-canary.log")
JSON_OUT = os.path.join(STATE_DIR, "model-canary.json")
MEMORY_DIR = os.path.join(
    os.path.expanduser("~"), ".claude", "projects",
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory")
LINEUP_FILE = os.path.join(MEMORY_DIR, "reference_model_release_checklist.md")
PROJECTS_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")

INJECTION_MARK = "<scheduled-task name="
# A model value the transport uses for placeholder/error rows. NOT an
# observation -- ora-am-brief's 2026-08-09 session carried exactly one of these
# in its scheduled portion and nothing else. Treating it as a model would have
# produced a tag asserting a model that does not exist.
NON_MODELS = {"<synthetic>", "synthetic", "", None}

# Full [MODEL: ...] tag, tolerating one level of nested brackets so a value like
# claude-opus-5[1m] is captured whole rather than severed at the inner bracket.
TAG_RE = re.compile(r"\[MODEL:(?:[^\[\]]|\[[^\]]*\])*\]")
DATE_RE = re.compile(r"(?:checked|set)\s+(\d{4}-\d{2}-\d{2})")
LINEUP_RE = re.compile(r"Current lineup as of (\d{4}-\d{2}-\d{2})")


# ---------------------------------------------------------------- pure helpers

def bare_model(mid):
    """Strip the context-window suffix: claude-opus-5[1m] -> claude-opus-5.

    Tags must always carry the BARE id. A nested [1m] closes the tag bracket
    early, severing the date half, which pins the task to the undated bucket
    permanently and immune to re-tagging in that form (hazard, 2026-08-03)."""
    if not mid:
        return mid
    return re.sub(r"\[[^\]]*\]$", "", mid.strip())


def parse_model_tag(description):
    """-> (raw_tag, model_id_or_None, date_or_None). LAST match wins.

    Last, not first: CC/MCP descriptions carry long inline changelogs and a
    changelog sentence can legitimately quote an example tag, so a first-match
    read grades the task on prose instead of its real trailing tag."""
    if not description:
        return (None, None, None)
    matches = TAG_RE.findall(description)
    if not matches:
        return (None, None, None)
    raw = matches[-1]
    inner = raw[len("[MODEL:"):-1].strip()
    date = None
    m = DATE_RE.search(inner)
    if m:
        date = m.group(1)
    value = inner.split("|")[0].strip()
    value = re.sub(r"\s+(observed|OBSERVED)\b.*$", "", value).strip()
    if value.upper().startswith("UNVERIFIABLE"):
        return (raw, "UNVERIFIABLE", date)
    tok = value.split()[0] if value.split() else ""
    return (raw, bare_model(tok) or None, date)


def row_text(row):
    msg = row.get("message") or {}
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def is_tool_result(row):
    c = (row.get("message") or {}).get("content")
    if isinstance(c, list):
        return any(isinstance(b, dict) and b.get("type") == "tool_result"
                   for b in c)
    return False


def is_human_turn(row):
    """A genuine human-authored turn -- not a tool_result, hook, system
    reminder, or slash-command echo. These are what END the scheduled portion."""
    if row.get("type") != "user" or is_tool_result(row):
        return False
    t = row_text(row)
    if not t.strip():
        return False
    s = t.lstrip()
    if s.startswith("<system-reminder") or "<command-name>" in s:
        return False
    return True


def cut_scheduled_portion(rows):
    """-> (injection_idx, cut_idx) or (None, None) if no injection row.

    injection_idx is where the scheduled prompt was injected; cut_idx is the
    first genuine human turn after it, else len(rows)."""
    inj = None
    for i, r in enumerate(rows):
        if INJECTION_MARK in row_text(r):
            inj = i
            break
    if inj is None:
        return (None, None)
    for i in range(inj + 1, len(rows)):
        if is_human_turn(rows[i]):
            return (inj, i)
    return (inj, len(rows))


def observe_models(rows):
    """-> dict {model_id: count} over assistant rows in the scheduled portion.

    Placeholder values are dropped, so a portion containing only <synthetic>
    yields {} -- i.e. NO observation, which the caller must treat as
    unverifiable rather than as evidence of anything."""
    inj, cut = cut_scheduled_portion(rows)
    if inj is None:
        return ({}, None, None)
    counts = {}
    for r in rows[inj:cut]:
        if r.get("type") != "assistant":
            continue
        m = (r.get("message") or {}).get("model")
        if m in NON_MODELS:
            continue
        counts[bare_model(m)] = counts.get(bare_model(m), 0) + 1
    return (counts, inj, cut)


def format_breakdown(counts):
    """-> 'claude-opus-4-8 x45 (58%), claude-fable-5 x32 (42%)', busiest first,
    ties broken alphabetically so output is deterministic across runs.

    The percentage carries a judgement the raw counts don't: a 1-message
    fallback (x1, 1%) should read very differently from a genuine near-even
    split (x32, 42%), and MIXED_RUN has no minimum-share threshold by design
    (thresholds rot) -- so the reader needs the share to make that call."""
    total = sum(counts.values())
    if not total:
        return ""
    return ", ".join(
        "%s x%d (%d%%)" % (k, v, round(100.0 * v / total))
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def classify(task_id, tag_model, tag_date, observed, anchor,
             upgradable_is_action=False, counts=None):
    """-> (severity, code, detail) where severity is 'action'|'info'|'ok'.

    observed is the winning bare model id, or None when nothing usable was seen.
    Never returns 'action' on absence alone -- absence is the caller's
    unverifiable bucket, which is reported separately and never as clean.

    counts is the optional {model_id: msg_count} the winner was drawn from.
    Omit it (or pass a single-entry / empty dict) for the legacy single-model
    path -- every pre-existing caller is unaffected. When it holds >1 entry the
    run is MIXED: a tag matching any model actually present reads as info
    MIXED_RUN rather than a defect (the plurality winner is a sampling
    artifact, not ground truth -- see the block below), while a tag matching
    NONE of them still reads as CONTRADICTED. Tag-shape gaps and staleness are
    both checked independently of mixedness, so neither can be silently
    swallowed by it.

    UPGRADABLE is INFO by default, deliberately. `UNVERIFIABLE` is one of the
    four RATIFIED buckets, not a gap -- it was the honest baseline before a
    cheap observation method existed. Flagging all ~17 of them as actions every
    run would leave the probe permanently non-zero, which trains readers to
    ignore it. The real gaps are UNTAGGED / UNDATED / CONTRADICTED /
    OBSERVATION_STALE / MIXED_RUN-with-no-matching-tag. Pass --include-upgradable
    when deliberately running an upgrade sweep."""
    if observed is None:
        return ("info", "NO_OBSERVATION",
                "no usable scheduled-portion model in the sampled session(s)")
    if tag_model is None:
        return ("action", "UNTAGGED",
                "in scope and untagged; observation available: %s" % observed)
    if tag_model == "UNVERIFIABLE":
        return ("action" if upgradable_is_action else "info", "UPGRADABLE",
                "tag says UNVERIFIABLE but the model IS observable: %s" % observed)
    if tag_date is None:
        return ("action", "UNDATED",
                "tag carries an id but no checked/set date; observed %s" % observed)
    # A scheduled portion is not guaranteed to be single-model. ora-appsec-sweep
    # 2026-08-12 started on claude-fable-5 (its `model: fable` frontmatter pin
    # honoured) and switched to claude-opus-4-8 mid-run, no human turn involved.
    # `observed` is only the PLURALITY winner, so on a mixed run it flips with
    # sample timing -- that task read claude-fable-5 mid-run and claude-opus-4-8
    # once complete, i.e. two contradictory "observations" of one fire in one
    # day. Never let that artifact masquerade as a tag defect: report the whole
    # breakdown instead, and reserve CONTRADICTED for a tag matching NOTHING
    # actually seen.
    #
    # Mixedness is deliberately a FLAG, not an early return -- the first cut of
    # this fix returned as soon as it detected a mixed run, which put it ahead
    # of the anchor check below and silently downgraded a pre-existing ACTION
    # (OBSERVATION_STALE) to an info on any mixed run with a stale tag date
    # (caught in review, 2026-08-12, before merge). Staleness is ORTHOGONAL to
    # mixing: "this tag predates the lineup anchor and needs re-observing" does
    # not stop being true just because the run also turned out to be mixed.
    mixed = bool(counts) and len(counts) > 1
    breakdown = format_breakdown(counts) if mixed else None

    if mixed and tag_model not in counts:
        return ("action", "CONTRADICTED",
                "run spans %d models (%s); NONE matches tag %s"
                % (len(counts), breakdown, tag_model))
    if not mixed and tag_model != observed:
        return ("action", "CONTRADICTED",
                "tag asserts %s but the task fires on %s" % (tag_model, observed))
    if anchor and tag_date < anchor:
        detail = ("tag %s predates lineup anchor %s; re-observed %s (unchanged)"
                  % (tag_date, anchor, observed))
        if mixed:
            detail += "; run spans %d models (%s)" % (len(counts), breakdown)
        return ("action", "OBSERVATION_STALE", detail)
    if mixed:
        # A max() tie means there is no real "winner" -- only name one when the
        # count data actually supports the claim, so the phrase never implies a
        # plurality that does not exist.
        top = sorted(counts.values(), reverse=True)
        winner_clause = (
            (" -- the plurality winner %s is a sampling artifact, not a defect"
             % observed) if top[0] != top[1] else
            " -- tied, no single plurality winner; both are genuine observations")
        return ("info", "MIXED_RUN",
                "run spans %d models (%s); tag %s matches one of them%s"
                % (len(counts), breakdown, tag_model, winner_clause))
    return ("ok", "OBSERVED", "tag matches observation (%s)" % observed)


def read_lineup_anchor(path=LINEUP_FILE):
    try:
        m = LINEUP_RE.search(open(path, encoding="utf-8").read())
        return m.group(1) if m else None
    except Exception:
        return None


def read_description(skill_md_path):
    """Description from SKILL.md frontmatter, parsed line-wise (see module doc)."""
    try:
        lines = open(skill_md_path, encoding="utf-8").read().split("\n")
    except Exception:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    out, capturing = [], False
    for ln in lines[1:end]:
        if ln.startswith("description:"):
            capturing = True
            out.append(ln[len("description:"):].strip())
        elif capturing:
            if re.match(r"^[A-Za-z_][\w-]*:", ln):
                break
            out.append(ln.strip())
    return " ".join(x for x in out if x).strip() or None


# --------------------------------------------------------------- live plumbing

def load_rows(jsonl_path):
    rows = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def sessions_for_tasks(store_json):
    """-> {task_id: [session_record, ...]} newest first, from the session store
    that sits alongside the registry."""
    store_dir = os.path.dirname(store_json)
    out = {}
    for p in glob.glob(os.path.join(store_dir, "*.json")):
        if os.path.basename(p) == "scheduled-tasks.json":
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        tid = d.get("scheduledTaskId")
        if not tid:
            continue
        d["_path"] = p
        out.setdefault(tid, []).append(d)
    for v in out.values():
        v.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    return out


def transcript_for(session):
    cli = session.get("cliSessionId")
    if not cli:
        return None
    hits = glob.glob(os.path.join(PROJECTS_ROOT, "*", cli + ".jsonl"))
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sessions-per-task", type=int, default=3,
                    help="how many recent fires to sample before giving up "
                         "on finding a usable observation (default 3)")
    ap.add_argument("--json", action="store_true",
                    help="dump the full result object to stdout")
    ap.add_argument("--include-upgradable", action="store_true",
                    help="promote UPGRADABLE (UNVERIFIABLE tag on a task whose "
                         "model IS observable) from info to action; use when "
                         "deliberately running an upgrade sweep")
    a = ap.parse_args()

    if _sd is None:
        print("model-canary-probe: FAILED -- _shared/store_discovery.py "
              "unavailable; cannot locate the registry. Reporting exit 2 "
              "rather than an empty (falsely clean) result.")
        return 2
    store_json = _sd.discover_store(_sd.store_name("cc"))
    if not store_json:
        print("model-canary-probe: FAILED -- no CC/MCP registry found. exit 2.")
        return 2

    try:
        reg = json.load(open(store_json, encoding="utf-8"))
    except Exception as exc:
        print("model-canary-probe: FAILED -- registry unreadable (%s). exit 2."
              % exc)
        return 2

    anchor = read_lineup_anchor()
    anchor_note = None
    if not anchor:
        anchor_note = ("lineup anchor unreadable (%s) -- OBSERVATION_STALE "
                       "cannot be evaluated this run" % os.path.basename(LINEUP_FILE))

    by_task = sessions_for_tasks(store_json)
    actions, infos, oks, unverifiable, exempt = [], [], [], [], []

    for t in reg.get("scheduledTasks", []) or []:
        tid = t.get("id")
        if not tid:
            continue
        # SCOPE FILTER -- applied before classification, never after.
        if not t.get("enabled", False):
            exempt.append((tid, "paused"))
            continue
        if not t.get("cronExpression"):
            exempt.append((tid, "one-time"))
            continue

        desc = read_description(t.get("filePath") or "")
        raw_tag, tag_model, tag_date = parse_model_tag(desc)

        observed, sampled, went_inter, won_counts = None, 0, None, None
        for sess in (by_task.get(tid) or [])[:a.max_sessions_per_task]:
            jp = transcript_for(sess)
            if not jp:
                continue
            try:
                rows = load_rows(jp)
            except Exception:
                continue
            sampled += 1
            counts, inj, cut = observe_models(rows)
            if not counts:
                continue
            observed = max(counts.items(), key=lambda kv: kv[1])[0]
            won_counts = counts
            went_inter = cut < len(rows)
            break

        if observed is None:
            unverifiable.append((tid, sampled))

        sev, code, detail = classify(tid, tag_model, tag_date, observed, anchor,
                                     a.include_upgradable, counts=won_counts)
        rec = {"task": tid, "code": code, "detail": detail,
               "tag_model": tag_model, "tag_date": tag_date,
               "observed": observed, "went_interactive": went_inter,
               "sessions_sampled": sampled,
               # Full breakdown, not just the plurality winner -- without this
               # a downstream consumer of model-canary.json can only learn a
               # run was mixed by string-parsing `detail`.
               "observed_counts": won_counts}
        (actions if sev == "action" else infos if sev == "info" else oks).append(rec)

    print("model-canary-probe  scope=cc-enabled-recurring  in_scope=%d exempt=%d "
          "anchor=%s" % (len(actions) + len(infos) + len(oks), len(exempt),
                         anchor or "UNREADABLE"))
    for r in actions:
        print("  [ACTION] %-38s %-18s %s" % (r["task"], r["code"], r["detail"]))
    for r in infos:
        print("  [info]   %-38s %-18s %s" % (r["task"], r["code"], r["detail"]))
    if unverifiable:
        print("  [unverifiable] %d task(s) had no usable scheduled-portion "
              "observation (transcript pruned, or only placeholder rows) -- "
              "NOT a clean result for those: %s"
              % (len(unverifiable), ", ".join(t for t, _ in unverifiable)))
    if anchor_note:
        print("  [unverifiable] %s" % anchor_note)

    # Observed-model DISTRIBUTION across the fleet. Reported every run because
    # the server-side assignment is per-session and non-deterministic, NOT a
    # fixed per-task pin (established 2026-07-26: the same task fired on
    # different models on different days). A minority id here is therefore the
    # expected shape of that coin-flip, not evidence of a per-task defect --
    # but it is also the reason a single-sample tag is a point-in-time
    # observation rather than a durable property, and the distribution is the
    # only place that stays visible.
    # NOTE (2026-08-12 review): this still counts one vote per TASK (the
    # plurality winner), same as before -- a minority model inside a mixed run
    # is not folded in here, because "minority: X on N task(s)" below reads as
    # a task count and switching this to a message count would silently break
    # that phrasing. The full per-task breakdown is not lost, though: it now
    # rides on each record's "observed_counts" (see rec{} above) for anyone who
    # needs the true message-level split.
    dist = {}
    for r in actions + infos + oks:
        if r["observed"]:
            dist[r["observed"]] = dist.get(r["observed"], 0) + 1
    if dist:
        print("  observed-model distribution: %s"
              % ", ".join("%s=%d" % kv for kv in sorted(dist.items(),
                                                        key=lambda kv: -kv[1])))
        if len(dist) > 1:
            minority = sorted(dist.items(), key=lambda kv: kv[1])[:-1]
            print("    note: >1 model observed across the fleet -- expected "
                  "under the per-session (not per-task) assignment; minority: %s"
                  % ", ".join("%s on %d task(s)" % kv for kv in minority))
    if not actions:
        print("OK -- no in-scope tag gaps.")

    result = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
              "anchor": anchor, "actions": actions, "infos": infos,
              "ok": oks, "unverifiable": [t for t, _ in unverifiable],
              "observed_distribution": dist,
              "exempt": [{"task": t, "why": w} for t, w in exempt]}
    if a.json:
        print(json.dumps(result, indent=2))

    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(JSON_OUT, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s in_scope=%d actions=%d info=%d ok=%d unverifiable=%d "
                     "exempt=%d anchor=%s\n"
                     % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        len(actions) + len(infos) + len(oks), len(actions),
                        len(infos), len(oks), len(unverifiable), len(exempt),
                        anchor or "UNREADABLE"))
    except Exception as exc:
        print("  [warn] could not write probe state: %s" % exc)

    return 1 if actions else 0


if __name__ == "__main__":
    sys.exit(main())
