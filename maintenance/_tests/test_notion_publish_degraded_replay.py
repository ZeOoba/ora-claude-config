"""Regression replay for maintenance/_state/notion-publish-degraded.json.

Pins real send-log decisions (subject, bytes, ET send date) captured from
scheduled-tasks/_shared/send-log.txt on 2026-09-13, so a future edit to a
producer's fallback_email_subject_pattern / must_not_match / min_bytes cannot
silently start rejecting a genuine full report or accepting a bare notice.

Run: python maintenance/_tests/test_notion_publish_degraded_replay.py
"""
import json
import pathlib
import re
import sys
import unittest

STATE = pathlib.Path(__file__).resolve().parents[1] / "_state" / "notion-publish-degraded.json"


def norm(subject: str) -> str:
    for ch in "—–‒−":
        subject = subject.replace(ch, "-")
    subject = subject.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", subject).strip()


def decide(producer: dict, subject: str, nbytes: int, date: str) -> str:
    """Return ACCEPT / REJECT_MUST_NOT_MATCH / REJECT_BYTES / NO_MATCH per the shared rule item 3."""
    pat = producer["fallback_email_subject_pattern"]
    if pat is None:
        return "NO_MATCH"
    y, m, d = (int(x) for x in date.split("-"))
    import datetime as dt
    day = dt.date(y, m, d)
    rx = (pat.replace("{DATE}", date)
             .replace("{DATE_LONG}", f"{day:%B} {day.day}, {day.year}")
             .replace("{MONTH_YYYY}", f"{day:%B %Y}"))
    n = norm(subject)
    if not re.search(rx, n, re.I):
        return "NO_MATCH"
    if re.search(producer["must_not_match"], n, re.I):
        return "REJECT_MUST_NOT_MATCH"
    if nbytes < producer["min_bytes"]:
        return "REJECT_BYTES"
    return "ACCEPT"


# (task_id, block prefix or None, subject, bytes, ET send date, expected)
CASES = [
    # genuine full reports that must qualify as delivery proof
    ("ora-am-brief", "B", "ORA Daily Brief PUBLICATION FAILED - 2026-09-12", 26008, "2026-09-12", "ACCEPT"),
    ("ora-am-brief", "B", "❌ ora-am-brief DAILY-BRIEF PUBLICATION FAILED — 2026-09-13", 21681, "2026-09-13", "ACCEPT"),
    ("ora-pm-ledger", "C", "ORA EOD Action Ledger - 2026-09-12 - 7 need you (Notion post FAILED - block quota)", 7190, "2026-09-12", "ACCEPT"),
    ("automation-health-monitor", None, "[AUTO-SENT] Automation Health 2026-09-09 - Notion publication FAILED (block quota) + 4 quarterly refreshes stranded", 6624, "2026-09-09", "ACCEPT"),
    ("ora-lease-expiration-brief", None, "ORA Lease Expiration Brief - 2026-08-10", 1226, "2026-08-10", "ACCEPT"),
    ("ora-deal-aging-sla", None, "Deal Aging SLA - 2026-08-17: 0 breaches, 1 verified-ask contradiction (4484 Robertson)", 861, "2026-08-17", "ACCEPT"),
    ("ora-skill-text-audit", None, "ORA Skill Text Audit — 2026-08-15", 2236, "2026-08-15", "ACCEPT"),
    ("ora-weekly-hygiene", "C", "ORA SharePoint Freshness — 2026-08-23 — REDUCED SCOPE, see coverage gaps", 2827, "2026-08-23", "ACCEPT"),
    # bare / not-run notices that must be rejected
    ("ora-weekly-hygiene", "C", "ORA SharePoint Freshness — 2026-09-02 — COVERAGE GAP, not run", 903, "2026-09-02", "REJECT_MUST_NOT_MATCH"),
    ("automation-health-monitor", None, "ora-automation-health-monitor PUBLICATION FAILED - 2026-09-08", 2401, "2026-09-08", "REJECT_BYTES"),
    ("automation-health-monitor", None, "PUBLICATION FAILED ora-automation-health-monitor 2026-09-10", 2856, "2026-09-10", "REJECT_BYTES"),
    ("automation-health-monitor", None, "❌ ora-automation-health-monitor PUBLICATION FAILED — 2026-09-11", 2147, "2026-09-11", "REJECT_BYTES"),
    # undated pattern must not accept a reply/forward
    ("ora-health-guard-fail-aging-nudge", None, "RE: [ACTION] Health Guard FAIL Aging -- 1 stale", 2912, "2026-09-05", "NO_MATCH"),
    ("ora-health-guard-fail-aging-nudge", None, "[ACTION] Health Guard FAIL Aging -- 1 stale", 2912, "2026-09-05", "ACCEPT"),
]


class ReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = json.loads(STATE.read_text(encoding="utf-8-sig"))

    def producer(self, task_id, block):
        hits = [p for p in self.state["producers"]
                if p["task_id"] == task_id and (block is None or p.get("block", "").startswith(block))]
        self.assertEqual(len(hits), 1, f"{task_id}/{block}: expected exactly one roster entry")
        return hits[0]

    def test_pinned_decisions(self):
        for task_id, block, subject, nbytes, date, expected in CASES:
            with self.subTest(task=task_id, date=date, bytes=nbytes):
                self.assertEqual(decide(self.producer(task_id, block), subject, nbytes, date), expected)

    def test_schema(self):
        self.assertIn("review_by", self.state)
        for p in self.state["producers"]:
            if p["fallback_email_subject_pattern"] is None:
                self.assertIsNone(p["min_bytes"])
            else:
                self.assertIsInstance(p["min_bytes"], int)
                self.assertTrue(p["min_bytes_basis"])
                re.compile(p["must_not_match"])
                self.assertNotIn("\x08", p["must_not_match"], "word boundary serialized as a backspace")
                if "{DATE" not in p["fallback_email_subject_pattern"] and "{MONTH_YYYY}" not in p["fallback_email_subject_pattern"]:
                    self.assertTrue(p["fallback_email_subject_pattern"].startswith("^(?!\\s*(re|fw|fwd):)"),
                                    f"{p['task_id']}: undated pattern lacks the reply/forward guard")


if __name__ == "__main__":
    sys.exit(unittest.main())
