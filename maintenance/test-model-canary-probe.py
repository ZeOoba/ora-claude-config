#!/usr/bin/env python3
"""Tests for model-canary-probe.py.

Covers the pure functions: bare_model(), parse_model_tag(), is_human_turn(),
cut_scheduled_portion(), observe_models(), classify(), read_description().
Nothing here touches the live registry, session store, or transcript tree --
every input is an in-memory fixture, so the suite is safe to run anywhere and
does not rot when transcripts are pruned (only ~half of scheduled-task sessions
still had one on 2026-08-03).

The fixtures encode REAL shapes observed during the 2026-08-09 sweep, not
invented ones:
  - the injection row sits at idx 5 behind 5 hook/system rows (naive-cut trap)
  - ora-lease-snapshot-refresh continued interactively at row 102 of 1513
  - ora-am-brief's newest session had a scheduled portion holding exactly one
    <synthetic> row and nothing else
  - ora-511-industrial-fallout-check ships a real id with NO date
  - the [1m] suffix nests a bracket inside the tag

Run: python test-model-canary-probe.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mcp_probe", os.path.join(HERE, "model-canary-probe.py"))
mcp_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_probe)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label, detail))


def user(text):
    return {"type": "user", "message": {"content": text}}


def hook(text):
    return {"type": "user", "message": {"content": "<system-reminder>" + text}}


def toolres():
    return {"type": "user",
            "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def asst(model):
    return {"type": "assistant", "message": {"model": model, "content": []}}


def scheduled_prefix():
    """5 hook/system rows then the injection at idx 5 -- the real shape."""
    return [hook("session start"), hook("claudeMd"), hook("memory"),
            hook("env"), hook("skills"),
            user('<scheduled-task name="ora-thing" file="x">do the thing')]


# ---------------------------------------------------------------- bare_model
expect("bare_model strips [1m] suffix",
       mcp_probe.bare_model("claude-opus-5[1m]") == "claude-opus-5")
expect("bare_model leaves plain id",
       mcp_probe.bare_model("claude-opus-5") == "claude-opus-5")
expect("bare_model tolerates None", mcp_probe.bare_model(None) is None)

# ------------------------------------------------------------ parse_model_tag
raw, mid, date = mcp_probe.parse_model_tag(
    "Does a thing. [MODEL: claude-opus-5 observed | checked 2026-08-09 via canary]")
expect("parses observed tag id", mid == "claude-opus-5", mid)
expect("parses observed tag date", date == "2026-08-09", date)

raw, mid, date = mcp_probe.parse_model_tag(
    "Blah [MODEL: UNVERIFIABLE | checked 2026-07-08]")
expect("parses UNVERIFIABLE", mid == "UNVERIFIABLE" and date == "2026-07-08")

raw, mid, date = mcp_probe.parse_model_tag("Tickler. [MODEL: claude-sonnet-5]")
expect("undated tag -> date None", mid == "claude-sonnet-5" and date is None)

raw, mid, date = mcp_probe.parse_model_tag("no tag here at all")
expect("absent tag -> all None", mid is None and date is None and raw is None)

# LAST match wins -- a changelog sentence quoting an example tag must not win.
raw, mid, date = mcp_probe.parse_model_tag(
    "v1.8 note: never write [MODEL: claude-sonnet-5 | set 2026-01-01] as an "
    "example. [MODEL: claude-opus-5 | checked 2026-08-09]")
expect("LAST bracketed tag wins, not the quoted example",
       mid == "claude-opus-5" and date == "2026-08-09", "%s/%s" % (mid, date))

# The [1m] hazard: nested bracket must not sever the date half.
raw, mid, date = mcp_probe.parse_model_tag(
    "x [MODEL: claude-opus-5[1m] | checked 2026-08-09]")
expect("nested [1m] does not sever the date",
       mid == "claude-opus-5" and date == "2026-08-09", "%s/%s" % (mid, date))

raw, mid, date = mcp_probe.parse_model_tag("y [MODEL: claude-opus-5 | set 2026-07-24]")
expect("'set' verb parses same as 'checked'", date == "2026-07-24")

# -------------------------------------------------------------- is_human_turn
expect("tool_result is not a human turn", not mcp_probe.is_human_turn(toolres()))
expect("system-reminder is not a human turn", not mcp_probe.is_human_turn(hook("x")))
expect("assistant row is not a human turn", not mcp_probe.is_human_turn(asst("m")))
expect("empty user row is not a human turn", not mcp_probe.is_human_turn(user("   ")))
expect("slash-command echo is not a human turn",
       not mcp_probe.is_human_turn(user("<command-name>/model</command-name>")))
expect("real prose IS a human turn", mcp_probe.is_human_turn(user("now do X")))

# ------------------------------------------------------- cut_scheduled_portion
rows = scheduled_prefix() + [asst("claude-opus-5"), toolres(), asst("claude-opus-5")]
inj, cut = mcp_probe.cut_scheduled_portion(rows)
expect("injection found at idx 5 (naive-cut trap)", inj == 5, str(inj))
expect("no human turn -> cut at end", cut == len(rows), str(cut))

rows = (scheduled_prefix() + [asst("claude-opus-5"), asst("claude-opus-5")]
        + [user("thanks, now switch models"), asst("claude-sonnet-5")])
inj, cut = mcp_probe.cut_scheduled_portion(rows)
expect("interactive continuation cuts at the human turn", cut == 8, str(cut))

inj, cut = mcp_probe.cut_scheduled_portion([hook("a"), user("hi"), asst("m")])
expect("no injection row -> (None, None)", inj is None and cut is None)

# ------------------------------------------------------------- observe_models
rows = scheduled_prefix() + [asst("claude-opus-5[1m]"), asst("claude-opus-5")]
counts, inj, cut = mcp_probe.observe_models(rows)
expect("suffix and bare id collapse to one bucket",
       counts == {"claude-opus-5": 2}, str(counts))

# The ora-lease-snapshot-refresh case: the interactive tail must be EXCLUDED.
rows = (scheduled_prefix() + [asst("claude-opus-5")] * 34
        + [user("/model")] + [asst("claude-sonnet-5")] * 60)
counts, inj, cut = mcp_probe.observe_models(rows)
expect("interactive tail excluded from the observation",
       counts == {"claude-opus-5": 34}, str(counts))

# The ora-am-brief case: a portion of only <synthetic> is NO observation.
rows = scheduled_prefix() + [asst("<synthetic>")]
counts, inj, cut = mcp_probe.observe_models(rows)
expect("<synthetic>-only portion yields no observation", counts == {}, str(counts))

# ------------------------------------------------------------------- classify
sev, code, _ = mcp_probe.classify("t", None, None, "claude-opus-5", "2026-07-26")
expect("untagged + observation -> ACTION UNTAGGED",
       sev == "action" and code == "UNTAGGED")

sev, code, _ = mcp_probe.classify("t", "UNVERIFIABLE", "2026-07-08",
                                  "claude-opus-5", "2026-07-26")
expect("UNVERIFIABLE tag + observation -> INFO UPGRADABLE by default "
       "(UNVERIFIABLE is a ratified bucket, not a gap)",
       sev == "info" and code == "UPGRADABLE", "%s/%s" % (sev, code))

sev, code, _ = mcp_probe.classify("t", "UNVERIFIABLE", "2026-07-08",
                                  "claude-opus-5", "2026-07-26",
                                  upgradable_is_action=True)
expect("--include-upgradable promotes UPGRADABLE to action",
       sev == "action" and code == "UPGRADABLE", "%s/%s" % (sev, code))

sev, code, _ = mcp_probe.classify("t", "claude-sonnet-5", None,
                                  "claude-opus-5", "2026-07-26")
expect("undated tag -> ACTION UNDATED", sev == "action" and code == "UNDATED")

sev, code, _ = mcp_probe.classify("t", "claude-sonnet-5", "2026-08-09",
                                  "claude-opus-5", "2026-07-26")
expect("tag contradicted by observation -> ACTION CONTRADICTED",
       sev == "action" and code == "CONTRADICTED")

sev, code, _ = mcp_probe.classify("t", "claude-opus-5", "2026-07-16",
                                  "claude-opus-5", "2026-07-26")
expect("matching id but pre-anchor date -> ACTION OBSERVATION_STALE",
       sev == "action" and code == "OBSERVATION_STALE")

sev, code, _ = mcp_probe.classify("t", "claude-opus-5", "2026-08-09",
                                  "claude-opus-5", "2026-07-26")
expect("fresh matching tag -> ok OBSERVED", sev == "ok" and code == "OBSERVED")

# Absence must never itself be an ACTION -- it belongs in the unverifiable bucket.
sev, code, _ = mcp_probe.classify("t", "claude-opus-5", "2026-07-01", None,
                                  "2026-07-26")
expect("no observation -> info NO_OBSERVATION, never action",
       sev == "info" and code == "NO_OBSERVATION")

# A missing anchor must not silently manufacture OBSERVATION_STALE.
sev, code, _ = mcp_probe.classify("t", "claude-opus-5", "2026-07-16",
                                  "claude-opus-5", None)
expect("unreadable anchor -> no stale verdict", sev == "ok" and code == "OBSERVED")

# ------------------------------------------------------------ read_description
with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "SKILL.md")
    open(p, "w", encoding="utf-8").write(
        "---\nname: thing\ndescription: Does a thing. [MODEL: claude-opus-5 | "
        "checked 2026-08-09]\noutput_contract:\n  version: 1\n---\nbody text\n")
    d = mcp_probe.read_description(p)
    expect("description read from frontmatter",
           d and d.startswith("Does a thing."), str(d))
    expect("description stops at the next top-level key",
           d and "version" not in d, str(d))
    _, mid, date = mcp_probe.parse_model_tag(d)
    expect("end-to-end frontmatter -> tag parse",
           mid == "claude-opus-5" and date == "2026-08-09")

    p2 = os.path.join(td, "NOFM.md")
    open(p2, "w", encoding="utf-8").write("no frontmatter here\n")
    expect("missing frontmatter -> None", mcp_probe.read_description(p2) is None)
    expect("missing file -> None",
           mcp_probe.read_description(os.path.join(td, "nope.md")) is None)

# ------------------------------------------------------------------- report
failed = [r for r in results if not r[0]]
for ok, label, detail in results:
    if not ok:
        print("FAIL: %s %s" % (label, ("-- got " + detail) if detail else ""))
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
