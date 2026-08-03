---
name: feedback_agent_model_pin_not_held_end_to_end
description: "An explicit `model:` on an Agent dispatch is honored at spawn but can silently fall back mid-run — verify the transcript, don't assume the pin held"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0ab34204-58c9-4742-bed5-706c5d028422
  modified: 2026-08-01T01:46:16.178Z
---

An explicit `model:` passed to the Agent tool is honored **at spawn** but is **not guaranteed for the duration of the run**. The harness can emit a fallback partway through and finish the agent on a different model. Observed 2026-07-31 on `ora-appsec-sweep`'s two `security-auditor` dispatches, both pinned `model: 'fable'`:

- `agent-a7cb98f7a98d0daed` (ora-pm): meta recorded `{"model":"fable"}`; 62 assistant messages on `claude-fable-5`, then an explicit `{"type":"fallback","from":{"model":"claude-fable-5"},"to":{"model":"claude-opus-5"}}` content block, then **68 messages on `claude-opus-5`** — i.e. more than half the run.
- `agent-a43623bcd1c477c5d` (oxford-command-center): same pin, 107 messages on fable, fallback, then 3 on opus-5.

**Why:** CLAUDE.md's dispatch invariant ("confidential/financial/governor code never below Fable; ALWAYS pin an explicit `model` per dispatch") is enforced by passing the pin — but nothing enforces it *after* spawn. Where a doctrine floor is carried by the dispatch rather than by the surface (see the ratified Option C in `ora-appsec-sweep/SKILL.md`, 2026-07-24), a mid-run fallback moves the actual work off the pinned tier **with no visible signal** in the agent's returned report. Integrity gates that assert only "the call returned a result / the pin was passed / the output came from the subagent" cannot see this.

**How to apply:** when a model floor actually matters (financial, governor, confidential, or security-gate judgment), do not treat a passed pin as proof. Verify after the fact against the subagent transcript in
`~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.jsonl`:

```bash
grep -o '"model":"[^"]*"' agent-<id>.jsonl | sort | uniq -c
python -c "import json;[print(x) for l in open('agent-<id>.jsonl',encoding='utf-8') if l.strip() for x in (json.loads(l).get('message',{}) or {}).get('content',[]) if isinstance(x,dict) and x.get('type')=='fallback']"
```

Note the fallback direction before alarming: falling back **to** Opus-5 is a move to the session's own top-tier model, not the Sonnet/Haiku downgrade the doctrine warns against — so it is not automatically a floor breach. Report the observation and the direction; let Gabriel rule on whether it is compliant. Tracked as `open-items-tracker.md#OI-052`.

Related: [[reference_scheduled_task_model_standard]] (a scheduled task's own frontmatter `model:` is inert on CC/MCP — server-pinned at registration), [[feedback_verify_subagent_safe_claims]], [[feedback_verify_before_repeating_session_claims]].
