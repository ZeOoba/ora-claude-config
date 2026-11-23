"""Tests for purge_scan.py (stdlib unittest; gated by tools/run_skill_suites.sh)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "purge_scan.py")
SECRET_FIG = "123,457"
SECRET_LIT = "Project Blue Heron"
SECRET_PHONE = "614-555-0199"
TIP_FIG = "987,651"


def git(repo, *args, env=None):
    e = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
             GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    if env:
        e.update(env)
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True, env=e).stdout


def write(repo, path, text):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def run(*args):
    return subprocess.run([sys.executable, "-I", SCRIPT] + list(args), capture_output=True, text=True)


class PurgeScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.repo = os.path.join(t, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        # Old history: secrets in a kept file, a removed folder, and a commit message.
        write(self.repo, "docs/deal.md", "Price was %s; call %s about %s.\n" % (SECRET_FIG, SECRET_PHONE, SECRET_LIT))
        write(self.repo, "notes/private.md", "%s everywhere\n" % SECRET_LIT)
        write(self.repo, "docs/hash.md", "sha 0a123,4570 and 9123,457 are not figures\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "add deal notes for %s" % SECRET_LIT)
        # Tip: secrets scrubbed, removed folder gone, one value still legitimately at the tip.
        write(self.repo, "docs/deal.md", "Price was [figure: private]; tip figure %s.\n" % TIP_FIG)
        git(self.repo, "rm", "-q", "-r", "notes")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "scrub")
        self.cfg = os.path.join(t, "private", "purge-config.json")
        os.makedirs(os.path.dirname(self.cfg))
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump({"remove_path_regex": r"(^|/)notes/",
                       "values": [123457, 987651, 50000],
                       "literals": [SECRET_LIT],
                       "phones": True,
                       "public_phones": []}, fh)
        self.rules = os.path.join(t, "private", "rules.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_writes_rules_and_never_prints_values(self):
        r = run("scan", self.repo, self.cfg, self.rules)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout + r.stderr
        for secret in (SECRET_FIG, SECRET_LIT, SECRET_PHONE, TIP_FIG, "123457"):
            self.assertNotIn(secret, out)
        rules = read_bytes(self.rules)
        self.assertIn(SECRET_LIT.encode(), rules)
        self.assertIn(b"614", rules)
        self.assertIn(b"123", rules)

    def test_rule_present_at_tip_is_dropped_and_counted(self):
        r = run("scan", self.repo, self.cfg, self.rules)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(b"987", read_bytes(self.rules))
        self.assertIn("dropped (present at main tip): 1", r.stdout)

    def test_round_figure_and_absent_value_get_no_rule(self):
        run("scan", self.repo, self.cfg, self.rules)
        self.assertNotIn(b"50,000", read_bytes(self.rules))

    def test_hex_and_longer_numbers_untouched_by_rules(self):
        run("scan", self.repo, self.cfg, self.rules)
        subprocess.run(["git", "filter-repo", "--version"], capture_output=True, check=True)
        git(self.repo, "filter-repo", "--force", "--invert-paths", "--path-regex", r"(^|/)notes/",
            "--replace-text", self.rules, "--replace-message", self.rules)
        self.assertIn("0a123,4570 and 9123,457", git(self.repo, "show", "main:docs/hash.md"))

    def test_verify_fails_before_and_passes_after_filter_repo(self):
        run("scan", self.repo, self.cfg, self.rules)
        self.assertEqual(run("verify", self.repo, self.cfg, self.rules).returncode, 1)
        tree_before = git(self.repo, "rev-parse", "main^{tree}")
        git(self.repo, "filter-repo", "--force", "--invert-paths", "--path-regex", r"(^|/)notes/",
            "--replace-text", self.rules, "--replace-message", self.rules)
        v = run("verify", self.repo, self.cfg, self.rules)
        self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
        self.assertEqual(tree_before, git(self.repo, "rev-parse", "main^{tree}"))


if __name__ == "__main__":
    unittest.main()
