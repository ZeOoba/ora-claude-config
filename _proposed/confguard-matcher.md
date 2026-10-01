# confidentiality-guard PreToolUse matcher -- proposed change (2026-09-30)

Branch: feat/confguard-coverage-0930. Status: PROPOSED, not applied. settings.json is a
blast-radius file; apply only with Gabriel's in-turn approval, by editing the ONE PreToolUse entry
whose command runs `hooks/confidentiality-guard.py` (the entry right after the inline
`Edit|Write` sensitive-file blocker). Change only its `matcher` value. Land the guard change
(this branch) in the live hooks dir first or together -- the new matcher routes tools that only
the new guard classifies; with the old guard they are spawned and allowed (no harm, no coverage).

## Old matcher (live and in the branch's tracked settings.json, verbatim)

```text
NotebookEdit|mcp__.*notion-(create|update|append|duplicate|move|comment)|mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)
```

The live string has NO `Bash` alternative. Bash reaches the guard through
`pretooluse-dispatcher.py --chain bash` (BASH_GUARD_CHAIN), and Edit/Write/MultiEdit through the
dispatcher's default chain. Do NOT add Bash, Edit, Write or MultiEdit here -- the guard would run
twice on those tools (see the dispatcher's module docstring).

## New matcher

<!-- new-matcher -->
```text
NotebookEdit|mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY).*|mcp__.*notion[-_]?(create|update|append|duplicate|move|comment).*|mcp__.*outlook_(send|create_draft|send_draft|forward|reply).*|mcp__.*outlook_(send_mail|send_draft|forward_mail|create_draft|create_reply_draft|create_reply_all_draft|update_draft|set_vacation).*|mcp__.*outlook_(create_event|update_event|respond_to_event|delete_event).*|mcp__.*teams_(send_chat_message|send_channel_message|reply_channel_message|create_chat).*|mcp__.*sharepoint_(upload_file|update_file).*|mcp__.*__manage_(crm_objects|blog_post|landing_page|website_page|campaign_objects|segment|aeo_prompts).*|mcp__.*notion-(send-message-to-session|spawn-session).*
```

The same string is `PROPOSED_MATCHER` in `hooks/tests/test-confidentiality-guard.py`; the suite
asserts this block equals it whenever this file exists.

## Rationale

1. **Live tools are lowercase.** The Composio-era `OUTLOOK_(...)` alternative cannot match
   `mcp__c0ea3c01-...__outlook_send_mail` under case-sensitive matching, anchored or not, so
   today the guard never runs on any live Outlook, Teams, SharePoint, HubSpot or Notion-agent
   write -- even though its internal `OUTLOOK_SEND` regex (re.I) would have scanned
   `outlook_send_mail`.
2. **Built mechanically from the guard.** Apart from `NotebookEdit` and the kept uppercase
   Composio alternative, every alternative is `mcp__.*<pattern>.*` for one pattern in
   `MCP_SEND_SURFACES` (the guard's MATCHER CONTRACT). The suite asserts each pattern appears
   verbatim and generates tool names from every pattern's alternatives (with server prefix and
   suffix drift) that must be routed. A new guard branch without a matcher change fails the suite.
3. **Semantics.** code.claude.com/docs/en/hooks.md (checked 2026-09-30): a matcher with regex
   characters is a "JavaScript regular expression, unanchored" (`RegExp.test`); case sensitivity
   is not stated (JS default: sensitive). The trailing `.*` is a no-op under the documented
   reading and keeps the entry correct if matching were anchored. The suite checks the anchored,
   case-sensitive reading, which implies the documented one.
4. **Read tools are not routed** (`outlook_email_search`, `teams_list_chats`, `sharepoint_search`,
   HubSpot `get_*`/`query_*`/`manage_saved_reports`, ...); the suite asserts none of them match.
5. **Residual:** the guard's historical `re.I` on NOTION_WRITE / OUTLOOK_SEND classifies
   mixed-case names that this case-sensitive matcher does not route. Live names are lowercase.
6. Per-tool inclusion/exclusion is justified in `hooks/confidentiality-guard.py` above
   `MCP_SEND_SURFACES`.

## Apply / rollback

Apply: replace the old string with the new one in that single entry; run
`hooks/tests/test-confidentiality-guard.py` (the ADVISORY line disappears; any other value that
still misses a classified tool is a hard FAIL). Rollback: restore the old string.
