---
name: reference_notion_update_content_silent_partial_apply
description: notion-update-page update_content can return success while silently applying only SOME of its edits — a returned page_id is not proof the edit landed
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3a21fa0c-1eb5-4c06-b0c0-b5dce4253d70
  modified: 2026-08-04T00:31:17.634Z
---

`mcp__…__notion-update-page` with `command: "update_content"` takes an array of `{old_str, new_str}` pairs. **A returned `{"page_id": …}` is NOT proof the edits applied.** Two distinct failure modes, both observed 2026-08-03:

1. **Hard error** — one non-matching `old_str` rejects the whole call with `validation_error: No matches found for …`, echoing every `old_str` concatenated (which misleadingly suggests they were treated as one string).
2. **Silent partial apply** — the call returns a normal `page_id` while only some pairs took effect. Row deletions no-opped, prose replacements landed, and nothing in the response distinguished them.

**Two reliable causes of a non-matching anchor:**

- **Table rows are stored one `<td>` per line, not inline.** An `old_str` written as `<tr><td>A</td><td>B</td></tr>` never matches; it must be `<tr>\n<td>A</td>\n<td>B</td>\n</tr>`. This is the single most common cause.
- **Escaping differs between the fetch render and the stored text.** The `notion-fetch` view escapes `\[`, `\$`, `\~` and renders emails/URLs as markdown links (`[**a@b.com**](mailto:a@b.com)`). Anchors copied from the render fail; anchors using plain `$` and `[` generally succeed. Do not blind-copy from the fetch output.

**Why this matters:** on 2026-08-03 the accumulated no-ops left two canonical pages self-contradictory — the Portfolio Intelligence Dashboard carried both a withdrawn diagnosis and its retraction plus a stray `~~`, and the corrections register displayed a literal `PLACEHOLDER_A2_ROW` and a junk placeholder row. Both had to be rebuilt with `replace_content`. The damage was invisible at edit time because every call had reported success.

**How to apply:** fetch the page first and anchor on its *stored* form, not the rendered one. Prefer short, unique, plain-prose anchors over long ones containing tables or formatting. For table-heavy canonical pages, **`replace_content` with the whole body is more reliable than incremental patching** and is the right move the moment two edits in a row misbehave. Always verify after writing — re-fetch or search for the new text — and never treat the returned `page_id` as confirmation. Related: [[reference_notion_view_dsl_formula_filter_bug]], [[feedback_verify_negative_glob_results]].
