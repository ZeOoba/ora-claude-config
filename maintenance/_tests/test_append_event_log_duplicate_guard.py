#!/usr/bin/env python3
"""Tests for append-event-log.py's duplicate-entry guard (TDD -- written before
the implementation).

THE DEFECT THIS GUARDS (2026-08-12): the same prepared entry was appended to
event_log.md TWICE, byte-identical (5,054 chars, md5 c00d2cbc0b68). Nothing
detected it; it was found by hand days-of-work later. With 30+ concurrent
sessions and a documented block-loss incident already on record, a silent
double-append is a real corruption vector.

WHY THE GUARD MUST KEY ON CONTENT, NOT THE HEADER: repeated headers are
LEGITIMATE and routine. The allow-hook-test-failure override protocol writes
5 entries in one day under a byte-identical '## ' header, each with a
different body (different timestamps/reasons) -- verified in the live log:
5 same-header entries, 5 distinct body md5s. A header-based guard would block
mandatory mechanical record-keeping. Only an EXACT content match is a duplicate.

WHY REFUSING IS SAFE HERE: this script's whole design is "the append must always
succeed" (it spools rather than fails). Skipping an exact duplicate does not
violate that -- the content is ALREADY in the log, so the caller's intent is
already satisfied and nothing can be lost. Exit stays 0 so `&&` caller chains
(both pre-push gates use them) do not break.

Run: python maintenance/_tests/test_append_event_log_duplicate_guard.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPEND = os.path.join(os.path.dirname(HERE), "append-event-log.py")

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


def load():
    spec = importlib.util.spec_from_file_location("append_event_log", APPEND)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HEADERLESS = "---\nname: event-log\n---\n\n"
E1 = "## 2026-08-12 - First entry\n\nBody of the first entry.\n"
E2 = "## 2026-08-12 - Second entry\n\nBody of the second entry.\n"
# Same header as E1, DIFFERENT body -- the override-protocol shape.
E1_SAME_HDR = "## 2026-08-12 - First entry\n\nA DIFFERENT body, same header.\n"


def make_log(tmp, entries=()):
    p = os.path.join(tmp, "event_log.md")
    content = HEADERLESS
    for e in entries:
        content += e.strip() + "\n\n"
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def run(m, log, entry, extra=None):
    """Invoke main() with a temp entry file. Returns (exit_code, log_text)."""
    fd, ef = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    # newline="" is REQUIRED: without it Windows translates "\n" -> "\r\n" on write,
    # so a deliberately-CRLF fixture becomes "\r\r\n" on disk and reads back with
    # DOUBLED blank lines. That is a test artifact, not real input, and it silently
    # made the CRLF case exercise the wrong thing (caught 2026-08-12).
    with open(ef, "w", encoding="utf-8", newline="") as f:
        f.write(entry)
    argv = ["--entry-file", ef, "--log", log] + list(extra or [])
    try:
        rc = m.main(argv)
    finally:
        os.remove(ef)
    with open(log, encoding="utf-8") as f:
        return rc, f.read()


def main():
    m = load()
    print("append-event-log.py duplicate-guard tests")

    # --- 1. the actual 2026-08-12 defect: exact duplicate must NOT land twice
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    rc, txt = run(m, log, E1)
    expect("exact duplicate is not appended a second time",
           txt.count("## 2026-08-12 - First entry") == 1,
           "count=%d" % txt.count("## 2026-08-12 - First entry"))
    expect("exact duplicate returns exit 0 (never breaks && chains)", rc == 0, "rc=%s" % rc)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 2. REGRESSION GUARD: same header + different body MUST still append.
    # This is the override-protocol case (5x/day under one header in the live log).
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    rc, txt = run(m, log, E1_SAME_HDR)
    expect("same header, DIFFERENT body still appends (override protocol)",
           txt.count("## 2026-08-12 - First entry") == 2,
           "count=%d" % txt.count("## 2026-08-12 - First entry"))
    expect("  ...and both bodies are present",
           "Body of the first entry." in txt and "A DIFFERENT body, same header." in txt)
    expect("same-header append returns exit 0", rc == 0, "rc=%s" % rc)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 3. a genuinely new entry still appends, newest-first
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    rc, txt = run(m, log, E2)
    expect("novel entry appends", "## 2026-08-12 - Second entry" in txt)
    expect("novel entry lands NEWEST-first (above the existing entry)",
           txt.index("Second entry") < txt.index("First entry"))
    expect("novel append returns exit 0", rc == 0, "rc=%s" % rc)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4. duplicate detection survives trailing-whitespace / EOL differences
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    rc, txt = run(m, log, E1.replace("\n", "\r\n") + "\n\n   ")
    expect("CRLF + trailing-whitespace variant is still caught as a duplicate",
           txt.count("## 2026-08-12 - First entry") == 1,
           "count=%d" % txt.count("## 2026-08-12 - First entry"))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4b. blank-line drift (same content, different vertical spacing) is a duplicate
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    spaced = E1.replace("\n\n", "\n\n\n")
    rc, txt = run(m, log, spaced)
    expect("blank-line-drift variant is caught as a duplicate",
           txt.count("## 2026-08-12 - First entry") == 1,
           "count=%d" % txt.count("## 2026-08-12 - First entry"))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 5. --allow-duplicate forces the append through
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])
    rc, txt = run(m, log, E1, extra=["--allow-duplicate"])
    expect("--allow-duplicate overrides the guard",
           txt.count("## 2026-08-12 - First entry") == 2,
           "count=%d" % txt.count("## 2026-08-12 - First entry"))
    expect("--allow-duplicate returns exit 0", rc == 0, "rc=%s" % rc)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 6. empty log (no existing entries) is not mistaken for a duplicate
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [])
    rc, txt = run(m, log, E1)
    expect("first-ever entry into an empty log appends",
           txt.count("## 2026-08-12 - First entry") == 1)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 7. the pure helper is directly testable and header-insensitive
    if hasattr(m, "is_duplicate_entry"):
        expect("is_duplicate_entry: exact match -> True",
               m.is_duplicate_entry(HEADERLESS + E1, E1) is True)
        expect("is_duplicate_entry: same header, different body -> False",
               m.is_duplicate_entry(HEADERLESS + E1, E1_SAME_HDR) is False)
        expect("is_duplicate_entry: absent -> False",
               m.is_duplicate_entry(HEADERLESS + E1, E2) is False)
    else:
        expect("is_duplicate_entry helper exists", False, "not defined")

    # --- 8. REGRESSION (found in code review): a '## ' markdown sub-heading
    # inside an entry BODY must not be mistaken for a new entry boundary. Real
    # entries in the live log use '## ' sub-headings in their text -- only a
    # DATED header ('## YYYY-MM-DD') starts a new entry.
    body_subheading_entry = (
        "## 2026-08-12 - Entry with a sub-heading\n\n"
        "Intro line.\n\n"
        "## Not a dated header\n\n"
        "More body text under the sub-heading."
    )
    if hasattr(m, "entry_blocks"):
        blocks = list(m.entry_blocks(HEADERLESS + body_subheading_entry + "\n"))
        expect("entry_blocks: a '## ' body sub-heading does not split the entry",
               len(blocks) == 1, "got %d blocks" % len(blocks))
    else:
        expect("entry_blocks helper exists", False, "not defined")

    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [body_subheading_entry])
    rc, txt = run(m, log, body_subheading_entry)
    expect("re-appending an entry with a '## ' sub-heading IS caught as a duplicate",
           txt.count("## 2026-08-12 - Entry with a sub-heading") == 1,
           "count=%d" % txt.count("## 2026-08-12 - Entry with a sub-heading"))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 9. REGRESSION: dated headers still split correctly (must not overcorrect
    # into treating the whole log as one block)
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1, E2])
    if hasattr(m, "entry_blocks"):
        with open(log, encoding="utf-8") as f:
            blocks = list(m.entry_blocks(f.read()))
        expect("entry_blocks: two real dated entries still yield two blocks",
               len(blocks) == 2, "got %d blocks" % len(blocks))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 10. TOCTOU RACE (found in code review): N SEPARATE OS PROCESSES racing
    # to append BYTE-IDENTICAL content to the same fresh log must land exactly
    # ONE copy. Threads share a process (and the GIL serializes their file I/O
    # in ways real sessions never experience); real sessions are separate
    # processes, so this races the CLI itself -- same style as
    # test_allocate_oi_id.py's test_separate_processes_are_unique.
    #
    # Why this reliably catches the bug rather than depending on rare timing:
    # the FIRST version of this guard checked for a duplicate ONCE, in a
    # separate read BEFORE the retry loop -- so every racing process sees
    # "not yet a duplicate" and enters the loop. The write loop's mtime-guard
    # then legitimately makes every process but the winner retry on
    # BlockingIOError -- but the old code's retry attempts were NOT
    # duplicate-aware, so a losing process's LATER attempt would blindly
    # re-insert after the winner had already landed the same entry. That is
    # not a narrow timing window: with N processes racing for a single fresh
    # slot, most of them lose the first attempt and retry, so most of them
    # would have re-appended on old code. The fix re-checks freshly on every
    # attempt (see _atomic_insert), so a loser's retry now recognizes the
    # winner's entry and skips instead of duplicating it.
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [])
    race_file = os.path.join(tmp, "race_entry.md")
    race_entry = ("## 2026-08-12 - Race entry\n\n"
                  "Byte-identical content from every racing process.\n")
    with open(race_file, "w", encoding="utf-8", newline="") as f:
        f.write(race_entry)

    N = 8
    procs = [subprocess.Popen(
        [sys.executable, APPEND, "--entry-file", race_file, "--log", log],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(N)]
    outs = [p.communicate(timeout=60) for p in procs]  # (stdout, stderr) each;
    rcs = [p.returncode for p in procs]                # must communicate() BEFORE
                                                         # reading returncode, or a
                                                         # full pipe can deadlock a
                                                         # racing process indefinitely

    with open(log, encoding="utf-8") as f:
        final = f.read()
    count = final.count("## 2026-08-12 - Race entry")
    expect("%d racing OS processes appending IDENTICAL content -> exactly 1 copy" % N,
           count == 1,
           "count=%d landed; returncodes=%s; stdouts=%s"
           % (count, rcs, [o[0].strip() for o in outs]))
    expect("every racing process exits 0 (winner AND all skippers -- never breaks && chains)",
           all(rc == 0 for rc in rcs), rcs)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 11. DRAIN-SPOOL DUPLICATE (found in code review, second finding): two
    # locked runs that both spooled the SAME entry content must not both land it
    # when the spool drains. drain_spool() has no duplicate check of its own --
    # it relies entirely on _atomic_insert/_inplace_insert doing it (see their
    # docstrings) -- so this proves that reliance actually holds, not just that
    # the shared helper exists.
    tmp = tempfile.mkdtemp()
    log = make_log(tmp, [E1])  # E1 already landed via some other path
    spool_dir = log + ".pending"
    os.makedirs(spool_dir, exist_ok=True)
    for name in ("1.md", "2.md"):  # two independently-spooled copies, same content
        with open(os.path.join(spool_dir, name), "w", encoding="utf-8", newline="") as f:
            f.write(E1)

    drained = m.drain_spool(log)

    with open(log, encoding="utf-8") as f:
        final = f.read()
    expect("drain_spool resolves both spooled entries (written OR recognized-duplicate)",
           drained == 2, "drained=%d" % drained)
    expect("a spooled entry that duplicates one already in the log is NOT reinserted",
           final.count("## 2026-08-12 - First entry") == 1,
           "count=%d" % final.count("## 2026-08-12 - First entry"))
    expect("both spool files are cleared -- a recognized duplicate doesn't wedge the queue",
           not os.listdir(spool_dir), os.listdir(spool_dir))
    shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for ok, _ in results if ok)
    print("\n%d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
