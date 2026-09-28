#!/usr/bin/env python3
"""Tests for pr-land-watch.py -- the queue behind the ora-pr-land-watch scheduled task.

WHY THIS EXISTS. "Do Y once PR X lands" kept being solved with a one-time task fired at a
guessed time (ora-branch-catchup-refute-trailer-366, 2026-09-23). If the PR had not merged
by then, the task could only report and exit, and an unattended run cannot re-schedule
itself (update_/create_scheduled_task are never auto-approved unattended). The watcher
replaces the guess with a poll: a queue of (repo, PR, payload) watches that a recurring
task drains as each PR merges.

These tests pin the classification contract the task's SKILL.md relies on:
  * MERGED -> due (attempt-counted, in flight, retired after MAX_ATTEMPTS)
  * CLOSED / not-found / open past expiry -> terminal
  * a transient gh failure -> reported but still pending, until it expires
  * payload provenance: pinned at add, re-verified at poll
They also pin the four Important findings from the 2026-09-23 adversarial review: a
lost add/mark under a broken lock, gh errors that never expire, a payload escaping via
junction/hardlink or being rewritten after add, and double execution across overlapping
runs.

Run: python _tests/test_pr_land_watch.py   (exit 0 = pass)
"""
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(os.path.dirname(HERE), "pr-land-watch.py")
spec = importlib.util.spec_from_file_location("pr_land_watch", MOD)
plw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plw)

TODAY = datetime.date(2026, 9, 23)
NOW = datetime.datetime(2026, 9, 23, 14, 0, tzinfo=datetime.timezone.utc)
REPO = "ZeOoba/oxford-command-center"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="plw-test-")
        self.state = plw.State(self.dir)
        os.makedirs(self.state.payload_dir, exist_ok=True)
        self.pr_states = {}
        self.calls = []
        self.on_fetch = None

        def fake_fetch(repo, pr):
            self.calls.append((repo, pr))
            if self.on_fetch:
                self.on_fetch()
            v = self.pr_states.get((repo, pr), {"state": "OPEN"})
            if isinstance(v, Exception):
                raise v
            return v

        self.fetch = fake_fetch

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def payload(self, wid, text="do the thing"):
        with open(self.state.payload_path(wid), "w", encoding="utf-8") as f:
            f.write(text)

    def add(self, wid="w1", repo=REPO, pr=366, expires=None):
        self.payload(wid)
        return plw.add_watch(self.state, wid, repo, pr, expires=expires, note="n",
                             today=TODAY, fetch=self.fetch)

    def set_pr(self, state, pr=366, sha="abc123"):
        v = {"state": state}
        if state == "MERGED":
            v.update(mergedAt="2026-09-24T01:00:00Z", mergeCommit={"oid": sha} if sha else None)
        self.pr_states[(REPO, pr)] = v

    def poll(self, today=TODAY, now=NOW):
        return plw.poll(self.state, fetch=self.fetch, today=today, now=now)

    def watch(self, wid):
        return [w for w in plw.load(self.state)["watches"] if w["id"] == wid][-1]


class TestAdd(Base):
    def test_add_defaults_and_pins_payload(self):
        w = self.add()
        self.assertEqual(w["status"], "pending")
        self.assertEqual(w["expires"], "2026-10-23")
        self.assertEqual(w["attempts"], 0)
        self.assertEqual(len(w["payloadSha256"]), 64)
        self.assertTrue(w["key"])

    def test_add_requires_payload(self):
        with self.assertRaises(plw.WatchError):
            plw.add_watch(self.state, "nopayload", "ZeOoba/x", 1, today=TODAY, fetch=self.fetch)

    def test_rejects_bad_id_repo_pr(self):
        for wid, repo, pr in [("../evil", "a/b", 1), ("C:\\x", "a/b", 1), ("abc\n", "a/b", 1),
                              ("ok", "not-a-repo", 1), ("ok", "a/b;rm -rf", 1), ("ok", "a/b", 0),
                              ("ok", "a/b\n", 1)]:
            with self.subTest(wid=wid, repo=repo, pr=pr):
                with self.assertRaises(plw.WatchError):
                    plw.add_watch(self.state, wid, repo, pr, today=TODAY, fetch=self.fetch)

    def test_rejects_duplicate_pending_id(self):
        self.add()
        with self.assertRaises(plw.WatchError):
            self.add()

    def test_expiry_bounds(self):
        with self.assertRaises(plw.WatchError):
            self.add(expires="2026-09-22")
        with self.assertRaises(plw.WatchError):
            self.add(wid="w2", expires="2027-06-01")

    def test_add_verifies_pr_exists_and_is_live(self):
        self.pr_states[(REPO, 9999)] = RuntimeError("GraphQL: Could not resolve to a PullRequest")
        with self.assertRaises(plw.WatchError):
            self.add(pr=9999)
        self.set_pr("CLOSED", pr=5)
        with self.assertRaises(plw.WatchError):
            self.add(wid="w5", pr=5)
        self.set_pr("MERGED", pr=6)
        self.add(wid="w6", pr=6)  # already merged is fine -- due on the next poll


class TestPoll(Base):
    def test_open_stays_pending_and_nothing_reported(self):
        self.add()
        r = self.poll()
        self.assertEqual(r["due"], [])
        self.assertEqual(r["pending"], 1)
        self.assertFalse(plw.needs_attention(r))

    def test_merged_is_due_with_verified_payload_text(self):
        self.add()
        self.set_pr("MERGED")
        r = self.poll()
        d = r["due"][0]
        self.assertEqual((d["mergeSha"], d["attempt"], d["payloadText"]), ("abc123", 1, "do the thing"))
        self.assertTrue(plw.needs_attention(r))
        self.assertEqual(self.watch("w1")["status"], "pending")  # until marked

    def test_in_flight_blocks_double_execution(self):
        self.add()
        self.set_pr("MERGED")
        self.assertEqual(len(self.poll()["due"]), 1)
        r = self.poll(now=NOW + datetime.timedelta(minutes=30))  # overlapping run
        self.assertEqual(r["due"], [])
        self.assertEqual(r["inFlight"], 1)
        self.assertFalse(plw.needs_attention(r))
        r = self.poll(now=NOW + datetime.timedelta(minutes=plw.IN_FLIGHT_MINUTES + 1))
        self.assertEqual(r["due"][0]["attempt"], 2)  # crashed run re-fires after the window

    def test_due_retires_after_max_attempts(self):
        self.add()
        self.set_pr("MERGED")
        step = datetime.timedelta(minutes=plw.IN_FLIGHT_MINUTES + 1)
        for i in range(plw.MAX_ATTEMPTS):
            self.assertEqual(len(self.poll(now=NOW + i * step)["due"]), 1, i)
        r = self.poll(now=NOW + plw.MAX_ATTEMPTS * step)
        self.assertEqual(r["due"], [])
        self.assertEqual([x["id"] for x in r["exhausted"]], ["w1"])
        self.assertEqual(self.watch("w1")["status"], "failed")

    def test_closed_unmerged_is_terminal(self):
        self.add()
        self.set_pr("CLOSED")
        self.assertEqual([x["id"] for x in self.poll()["closed"]], ["w1"])
        self.calls.clear()
        self.poll()
        self.assertEqual(self.calls, [])

    def test_expired_when_still_open_past_expiry(self):
        self.add(expires="2026-09-30")
        self.assertEqual(self.poll(today=datetime.date(2026, 9, 30))["expired"], [])
        r = self.poll(today=datetime.date(2026, 10, 1))
        self.assertEqual([x["id"] for x in r["expired"]], ["w1"])

    def test_merged_beats_expired(self):
        self.add(expires="2026-09-30")
        self.set_pr("MERGED", sha=None)
        r = self.poll(today=datetime.date(2026, 10, 5))
        self.assertIsNone(r["due"][0]["mergeSha"])

    def test_transient_gh_error_stays_pending(self):
        self.add()
        self.pr_states[(REPO, 366)] = RuntimeError("gh: auth required")
        r = self.poll()
        self.assertIn("auth required", r["errors"][0]["error"])
        self.assertEqual(self.watch("w1")["status"], "pending")

    def test_gh_error_past_expiry_expires(self):  # review finding 2
        self.add(expires="2026-09-30")
        self.pr_states[(REPO, 366)] = RuntimeError("error connecting to api.github.com")
        r = self.poll(today=datetime.date(2027, 6, 1))
        self.assertEqual([x["id"] for x in r["expired"]], ["w1"])
        self.assertEqual(self.watch("w1")["status"], "expired")

    def test_not_found_is_terminal_but_command_not_found_is_not(self):  # review finding 2
        self.add()
        self.pr_states[(REPO, 366)] = RuntimeError("bash: gh: command not found")
        self.poll()
        self.assertEqual(self.watch("w1")["status"], "pending")
        self.pr_states[(REPO, 366)] = RuntimeError("GraphQL: Could not resolve to a PullRequest with the number of 366.")
        self.poll()
        self.assertEqual(self.watch("w1")["status"], "not-found")

    def test_non_dict_gh_output_is_an_error_not_a_crash(self):
        self.add()
        self.pr_states[(REPO, 366)] = ["unexpected"]
        r = self.poll()
        self.assertEqual(r["errors"][0]["id"], "w1")

    def test_missing_payload_fails_the_watch(self):
        self.add()
        os.remove(self.state.payload_path("w1"))
        self.set_pr("MERGED")
        r = self.poll()
        self.assertEqual(r["due"], [])
        self.assertEqual(self.watch("w1")["status"], "failed")

    def test_payload_rewritten_after_add_is_refused(self):  # review finding 3
        self.add()
        self.payload("w1", "rm -rf everything")
        self.set_pr("MERGED")
        r = self.poll()
        self.assertEqual(r["due"], [])
        self.assertIn("payload changed", r["errors"][0]["error"])
        self.assertEqual(self.watch("w1")["status"], "failed")

    def test_hardlinked_payload_refused(self):  # review finding 3
        outside = os.path.join(self.dir, "outside.md")
        with open(outside, "w") as f:
            f.write("x")
        os.link(outside, self.state.payload_path("h1"))
        with self.assertRaises(plw.WatchError):
            plw.add_watch(self.state, "h1", REPO, 366, today=TODAY, fetch=self.fetch)

    @unittest.skipUnless(os.name == "nt", "junctions are Windows-only")
    def test_junctioned_payload_dir_refused(self):  # review finding 3
        elsewhere = os.path.join(self.dir, "elsewhere")
        os.makedirs(elsewhere)
        with open(os.path.join(elsewhere, "j1.md"), "w") as f:
            f.write("x")
        self.add()  # pin w1 under the real dir first
        shutil.rmtree(self.state.payload_dir)
        subprocess.run(["cmd", "/c", "mklink", "/J", self.state.payload_dir, elsewhere],
                       check=True, capture_output=True)
        with self.assertRaises(plw.WatchError):
            plw.add_watch(self.state, "j1", REPO, 366, today=TODAY, fetch=self.fetch)
        os.rmdir(self.state.payload_dir)  # remove the junction itself, never its target

    def test_repo_not_resolvable_stays_retryable(self):  # review 2, Minor D: also means "no access"
        self.add()
        self.pr_states[(REPO, 366)] = RuntimeError("GraphQL: Could not resolve to a Repository with the name 'x'.")
        self.poll()
        self.assertEqual(self.watch("w1")["status"], "pending")

    def test_payload_rewritten_during_gh_call_hands_out_checked_text(self):  # review 2, A
        self.add()
        self.set_pr("MERGED")
        self.on_fetch = lambda: self.payload("w1", "TAMPERED")
        d = self.poll()["due"][0]
        self.assertEqual(d["payloadText"], "do the thing")

    def test_non_utf8_payload_refused_at_add(self):  # review 2, B
        with open(self.state.payload_path("u16"), "w", encoding="utf-16") as f:
            f.write("instructions")
        with self.assertRaises(plw.WatchError):
            plw.add_watch(self.state, "u16", REPO, 366, today=TODAY, fetch=self.fetch)

    def test_one_bad_watch_does_not_stall_the_queue(self):  # review 2, B
        self.add("bad", pr=1)
        self.add("good", pr=2)
        self.pr_states[(REPO, 1)] = {"state": "MERGED", "mergeCommit": "not-a-dict"}
        self.set_pr("MERGED", pr=2)
        orig = plw._classify

        def boom(state, w, *a):
            if w["id"] == "bad":
                raise KeyError("surprise")
            return orig(state, w, *a)

        plw._classify = boom
        try:
            r = self.poll()
        finally:
            plw._classify = orig
        self.assertEqual([d["id"] for d in r["due"]], ["good"])
        self.assertEqual([e["id"] for e in r["errors"]], ["bad"])
        self.assertEqual(self.watch("bad")["status"], "pending")
        plw._classify = boom
        try:
            r = self.poll(today=datetime.date(2026, 11, 1))  # past the default 30d expiry
        finally:
            plw._classify = orig
        self.assertEqual([e["id"] for e in r["expired"]], ["bad"])
        self.assertEqual(self.watch("bad")["status"], "expired")

    def test_non_dict_merge_commit_tolerated(self):
        self.add()
        self.pr_states[(REPO, 366)] = {"state": "MERGED", "mergeCommit": "weird"}
        self.assertIsNone(self.poll()["due"][0]["mergeSha"])

    def test_empty_queue_needs_no_attention(self):
        r = self.poll()
        self.assertFalse(plw.needs_attention(r))
        self.assertEqual(r["pending"], 0)


class TestConcurrency(Base):
    def test_add_during_poll_fetch_is_not_lost(self):  # review finding 1
        self.add()
        self.payload("w2")

        def concurrent_add():
            self.on_fetch = None
            plw.add_watch(self.state, "w2", REPO, 367, today=TODAY, fetch=self.fetch)

        self.on_fetch = concurrent_add
        self.poll()
        self.assertEqual(sorted(w["id"] for w in plw.load(self.state)["watches"]), ["w1", "w2"])

    def test_mark_during_poll_fetch_wins(self):  # review finding 1
        self.add()
        self.set_pr("MERGED")

        def concurrent_mark():
            self.on_fetch = None
            plw.mark(self.state, "w1", "done", note="finished elsewhere")

        self.on_fetch = concurrent_mark
        r = self.poll()
        self.assertEqual(r["due"], [])
        self.assertEqual(self.watch("w1")["status"], "done")

    def test_truly_overlapping_polls_hand_out_once(self):  # review 2 test gap
        self.add()
        self.set_pr("MERGED")
        inner = {}

        def nested_poll():
            self.on_fetch = None
            inner["r"] = self.poll()

        self.on_fetch = nested_poll
        outer = self.poll()
        self.assertEqual(len(inner["r"]["due"]) + len(outer["due"]), 1)
        self.assertEqual(self.watch("w1")["attempts"], 1)

    def test_lock_released_only_by_owner(self):  # review finding 1
        lock = plw._Lock(self.state)
        lock.__enter__()
        with open(self.state.lock_path, "w") as f:
            f.write("someone-elses-token")
        lock.__exit__(None, None, None)
        self.assertTrue(os.path.exists(self.state.lock_path))
        os.remove(self.state.lock_path)

    def test_stale_lock_is_broken(self):
        self.add()
        with open(self.state.lock_path, "w") as f:
            f.write("stale")
        old = datetime.datetime.now().timestamp() - plw.STALE_LOCK_SECONDS - 5
        os.utime(self.state.lock_path, (old, old))
        plw.mark(self.state, "w1", "done")
        self.assertFalse(os.path.exists(self.state.lock_path))


class TestMarkAndState(Base):
    def test_mark_done_is_terminal(self):
        self.add()
        plw.mark(self.state, "w1", "done", note="PR #1 opened")
        w = self.watch("w1")
        self.assertEqual((w["status"], w["note"]), ("done", "PR #1 opened"))
        self.set_pr("MERGED")
        self.assertEqual(self.poll()["due"], [])

    def test_mark_rejects_unknown_status_and_id(self):
        self.add()
        with self.assertRaises(plw.WatchError):
            plw.mark(self.state, "w1", "pending")
        with self.assertRaises(plw.WatchError):
            plw.mark(self.state, "nope", "done")

    def test_re_add_after_terminal_re_pins_payload(self):
        self.add()
        plw.mark(self.state, "w1", "cancelled")
        self.payload("w1", "new instructions")
        w = plw.add_watch(self.state, "w1", REPO, 366, today=TODAY, fetch=self.fetch)
        self.set_pr("MERGED")
        self.assertEqual(self.poll()["due"][0]["payloadText"], "new instructions")
        self.assertEqual(sum(1 for x in plw.load(self.state)["watches"] if x["id"] == "w1"), 2)
        self.assertEqual(w["status"], "pending")

    def test_corrupt_queue_raises_not_silently_empties(self):
        with open(self.state.queue_path, "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(plw.WatchError):
            plw.load(self.state)

    def test_cli_poll_json(self):
        self.add()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = plw.main(["--state-dir", self.dir, "poll"], fetch=self.fetch, today=TODAY, now=NOW)
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(buf.getvalue())["needsAttention"])


if __name__ == "__main__":
    unittest.main()
