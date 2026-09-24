"""Shared fixture for the test_safe_push_*.py suites (temp repos + bare origin; see test_safe_push_core.py)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(os.path.dirname(HERE)), "safe-push.py")


def git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), r.stderr))
    return r.stdout.strip()


class Race:
    """bare origin + clone A (ours) + clone B (the other session)."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="safe-push-")
        self.bare = os.path.join(self.root, "origin.git")
        self.a = os.path.join(self.root, "a")
        self.b = os.path.join(self.root, "b")
        self.hooks = os.path.join(self.root, "hooks-a")
        self.nohooks = os.path.join(self.root, "nohooks")
        os.makedirs(self.hooks)
        os.makedirs(self.nohooks)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.bare], check=True)
        subprocess.run(["git", "clone", "-q", self.bare, self.a], check=True, capture_output=True)
        self._cfg(self.a, self.hooks)
        self.write(self.a, "f.txt", "base\n")
        self.write(self.a, "g.txt", "base\n")
        git(self.a, "add", "-A")
        git(self.a, "commit", "-q", "-m", "init")
        git(self.a, "push", "-q", "origin", "main")
        subprocess.run(["git", "clone", "-q", self.bare, self.b], check=True, capture_output=True)
        self._cfg(self.b, self.nohooks)

    @staticmethod
    def _cfg(repo, hooks):
        git(repo, "config", "user.email", "t@t")
        git(repo, "config", "user.name", "t")
        git(repo, "config", "core.hooksPath", hooks)

    @staticmethod
    def write(repo, name, text):
        with open(os.path.join(repo, name), "w", newline="\n") as f:
            f.write(text)

    def commit(self, repo, name, text, msg):
        self.write(repo, name, text)
        git(repo, "commit", "-q", "-am", msg)

    def other_session_pushes(self, name="g.txt", text=None, msg="other"):
        git(self.b, "pull", "-q", "--ff-only", "origin", "main", check=False)
        self.commit(self.b, name, text or ("other %s\n" % os.urandom(4).hex()), msg)
        git(self.b, "push", "-q", "origin", "main")

    def hook(self, body):
        """pre-push hook for A: counts runs, then runs body."""
        counter = os.path.join(self.root, "prepush-runs.txt").replace("\\", "/")
        path = os.path.join(self.hooks, "pre-push")
        with open(path, "w", newline="\n") as f:
            f.write("#!/bin/sh\necho run >> '%s'\n%s\n" % (counter, body))
        return counter

    def runs(self):
        p = os.path.join(self.root, "prepush-runs.txt")
        return len(open(p).read().split()) if os.path.exists(p) else 0

    def remote_tip(self):
        return git(self.a, "ls-remote", "origin", "refs/heads/main").split()[0]

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def run_tool(repo, *args):
    r = subprocess.run([sys.executable, TOOL, "--repo", repo, *args], capture_output=True, text=True)
    out = r.stdout + r.stderr
    line = [l for l in out.splitlines() if l.startswith("RESULT_JSON=")]
    res = json.loads(line[-1][len("RESULT_JSON="):]) if line else None
    return r.returncode, res, out
