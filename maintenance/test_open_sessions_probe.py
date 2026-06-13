"""Tests for the open-sessions probe classifier (pure functions only)."""
import unittest

from open_sessions_probe import classify, is_scheduled_run, Status


def cc_user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def cc_tool_result(tool_use_id="tu_1"):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]}}


def cc_assistant_text(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": text}]}}


def cc_assistant_tool_use(name="Bash", tool_use_id="tu_1"):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tool_use_id, "name": name, "input": {}}]}}


class ClassifyTests(unittest.TestCase):
    def test_clean_close_is_no_action(self):
        entries = [cc_user("do the thing"),
                   cc_assistant_text("Done. Nothing else open from this session.")]
        result = classify(entries)
        self.assertEqual(result.status, Status.NO_ACTION)

    def test_trailing_question_needs_answer(self):
        entries = [cc_user("review this PSA"),
                   cc_assistant_text("Found two issues. Do you want the aggressive or conservative redline?")]
        result = classify(entries)
        self.assertEqual(result.status, Status.NEEDS_ANSWER)

    def test_offer_phrase_needs_answer(self):
        entries = [cc_user("audit the model"),
                   cc_assistant_text("Audit complete, one discrepancy.\nWant me to correct the DSCR cell before it goes to Eric?")]
        result = classify(entries)
        self.assertEqual(result.status, Status.NEEDS_ANSWER)

    def test_question_mid_message_but_clean_ending_is_no_action(self):
        entries = [cc_user("x"),
                   cc_assistant_text("What changed? The cap rate input. I fixed it and verified the output. All clean now.")]
        result = classify(entries)
        self.assertEqual(result.status, Status.NO_ACTION)

    def test_unanswered_tool_use_is_stalled(self):
        entries = [cc_user("run it"), cc_assistant_tool_use()]
        result = classify(entries)
        self.assertEqual(result.status, Status.STALLED)

    def test_answered_tool_use_then_text_is_no_action(self):
        entries = [cc_user("run it"), cc_assistant_tool_use(), cc_tool_result(),
                   cc_assistant_text("Ran clean, all tests green.")]
        result = classify(entries)
        self.assertEqual(result.status, Status.NO_ACTION)

    def test_human_message_without_reply_is_interrupted(self):
        entries = [cc_assistant_text("Done."), cc_user("also check the rent roll")]
        result = classify(entries)
        self.assertEqual(result.status, Status.INTERRUPTED)

    def test_trailing_tool_result_without_followup_is_stalled(self):
        entries = [cc_user("run it"), cc_assistant_tool_use(), cc_tool_result()]
        result = classify(entries)
        self.assertEqual(result.status, Status.STALLED)

    def test_ask_user_question_tool_is_needs_answer(self):
        entries = [cc_user("plan the build"),
                   {"type": "assistant", "message": {"role": "assistant", "content": [
                       {"type": "tool_use", "id": "tu_q", "name": "AskUserQuestion",
                        "input": {"questions": [{"question": "Which auth method?"}]}}]}}]
        result = classify(entries)
        self.assertEqual(result.status, Status.NEEDS_ANSWER)

    def test_empty_transcript_is_unknown(self):
        result = classify([])
        self.assertEqual(result.status, Status.UNKNOWN)

    def test_snippet_carries_last_text(self):
        entries = [cc_user("x"), cc_assistant_text("Pick a lender: A or B?")]
        result = classify(entries)
        self.assertIn("Pick a lender", result.snippet)

    def test_sidechain_entries_ignored(self):
        entries = [cc_user("x"),
                   cc_assistant_text("Done, all verified."),
                   {"type": "assistant", "isSidechain": True,
                    "message": {"role": "assistant", "content": [
                        {"type": "text", "text": "subagent asking: which file?"}]}}]
        result = classify(entries)
        self.assertEqual(result.status, Status.NO_ACTION)


class ScheduledRunTests(unittest.TestCase):
    def test_scheduled_task_tag_in_first_user_message(self):
        entries = [{"type": "user", "message": {"role": "user", "content":
                    '<scheduled-task name="loopnet-autoreply" file="...">This is an automated run.</scheduled-task>'}},
                   cc_assistant_text("Running the sweep.")]
        self.assertTrue(is_scheduled_run(entries))

    def test_tag_in_content_blocks(self):
        entries = [{"type": "user", "message": {"role": "user", "content": [
                    {"type": "text", "text": '<scheduled-task name="x">run</scheduled-task>'}]}}]
        self.assertTrue(is_scheduled_run(entries))

    def test_leading_system_entries_skipped(self):
        entries = [{"type": "system", "subtype": "status"},
                   {"type": "user", "message": {"role": "user", "content":
                    '<scheduled-task name="x">run</scheduled-task>'}}]
        self.assertTrue(is_scheduled_run(entries))

    def test_normal_human_message_is_not_scheduled(self):
        entries = [cc_user("review this PSA"), cc_assistant_text("On it.")]
        self.assertFalse(is_scheduled_run(entries))

    def test_tag_mentioned_later_does_not_count(self):
        entries = [cc_user("why did the <scheduled-task> run twice?"),
                   cc_assistant_text("Looking.")]
        self.assertFalse(is_scheduled_run(entries))

    def test_empty_is_not_scheduled(self):
        self.assertFalse(is_scheduled_run([]))


if __name__ == "__main__":
    unittest.main()
