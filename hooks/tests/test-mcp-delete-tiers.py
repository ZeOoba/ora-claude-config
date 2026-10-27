"""Tests for hooks/lib/mcp_delete_tiers.py and the committed tool snapshot (R-06).

Run: python test-mcp-delete-tiers.py
Proves: every delete-shaped name in the snapshot has an explicit tier; each row's
`verified` flag equals snapshot membership; the snapshot is fresh; false-positive
names are pinned; the by-input classifiers fail closed; both matcher models agree.

Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import glob
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
import mcp_delete_tiers as t  # noqa: E402

SNAPSHOT = os.path.join(HOOKS_DIR, "tests", "lib", "mcp_tool_snapshot.json")
WARN_DAYS = 30
FAIL_DAYS = 90
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def load_snapshot():
    with open(SNAPSHOT, "r", encoding="ascii") as fh:
        return json.load(fh)


def full_names(snap):
    """Harness-style names. Connector keys are '<server>:<tool>' (local servers add a
    display-name segment); the suffix is exact, the prefix approximate for local ones."""
    out = set(snap["internal_tools"])
    for key in snap["connector_tools"]:
        parts = key.split(":")
        server = re.sub(r"[^A-Za-z0-9_-]", "_", "_".join(parts[:-1]))
        out.add("mcp__%s__%s" % (server, parts[-1]))
    return out


def test_snapshot_shape_and_age():
    snap = load_snapshot()
    check("T0 snapshot lists are non-empty and sorted",
          snap["connector_tools"] and snap["internal_tools"]
          and snap["connector_tools"] == sorted(snap["connector_tools"])
          and snap["internal_tools"] == sorted(snap["internal_tools"]))
    captured = datetime.date.fromisoformat(snap["captured_at"])
    age = (datetime.date.today() - captured).days
    if age > WARN_DAYS:
        print("WARN T1 snapshot is %d days old; refresh with "
              "hooks/tests/lib/refresh_mcp_tool_snapshot.py" % age)
    check("T1 snapshot captured_at is at most %d days old" % FAIL_DAYS,
          0 <= age <= FAIL_DAYS, "age=%d" % age)


def test_every_routed_snapshot_tool_is_classified():
    snap = load_snapshot()
    for name in sorted(full_names(snap)):
        if not t.is_routed(name):
            continue
        tier, reason, short = t.classify(name, {})
        check("T2 routed snapshot tool %s has an explicit tier" % short,
              tier not in (t.UNKNOWN, t.UNROUTED), "tier=%s" % tier)


def test_verified_flags_match_snapshot():
    shorts = {n.rsplit("__", 1)[-1] for n in full_names(load_snapshot())}
    for key, (tier, verified, reason) in sorted(t.TIERS.items()):
        check("T3 TIERS[%s].verified == (suffix in snapshot)" % key,
              verified == (key in shorts), "verified=%s in_snapshot=%s" % (verified, key in shorts))


def test_every_row_is_reachable():
    for key in sorted(t.TIERS):
        name = "mcp__srv__" + key
        check("T4 row %s is routed by SETTINGS_MATCHER" % key, t.is_routed(name))


def test_false_positive_and_read_pins():
    pins = [
        ("mcp__7c55602a-d1ec-4c77-a92e-06ee3c786d3a__image_remove_background", t.EXEMPT),
        ("mcp__x__list_deleted_items", t.EXEMPT),
        ("mcp__x__get_trash", t.EXEMPT),
        ("mcp__x__restore_from_trash", t.EXEMPT),
        ("mcp__x__purge_everything", t.UNKNOWN),
        ("mcp__x__OUTLOOK_DELETE_MESSAGE", t.UNKNOWN),
        ("mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-restore-pages", t.EXEMPT),
        ("mcp__ccd_session_mgmt__archive_session", t.UNROUTED),
        # C4: routed by the matcher but the text after the last "__" has no keyword; a
        # routed name must never classify UNROUTED.
        ("mcp__x__delete__all", t.UNKNOWN),
        ("mcp__x__purge__everything", t.UNKNOWN),
        # single-segment middle: last segment is a read verb, but the name routes via the matcher
        ("mcp__x__clean_up_worktrees__list_all", t.UNKNOWN),
        # KNOWN LIMITATION (pinned, not endorsed): a read/restore prefix exempts the whole
        # name, so a compound verb that starts with one is EXEMPT even though it deletes.
        ("mcp__x__get_and_delete", t.EXEMPT),
        ("mcp__x__restore_then_purge", t.EXEMPT),
        # delete_trigger (claude-code-remote) is an explicit IRREVERSIBLE row, matched on the
        # exact short name only: its non-deleting siblings stay unrouted and a compound name
        # is not covered by the row.
        ("mcp__claude-code-remote__delete_trigger", t.IRREVERSIBLE),
        ("mcp__claude-code-remote__update_trigger", t.UNROUTED),
        ("mcp__claude-code-remote__fire_trigger", t.UNROUTED),
        ("mcp__claude-code-remote__archive_session", t.UNROUTED),
        ("mcp__x__delete_trigger_and_sessions", t.UNKNOWN),
        ("mcp__x__delete_triggers", t.UNKNOWN),
        # untrash is an explicit by-input TIERS row, NOT a read prefix: with no restoreMap
        # (the {} used here) the restore tool is EXEMPT, its delete sibling stays gated, and
        # a compound name starting with it is not laundered. Map-dependent tiers: see T6.
        ("mcp__ms365__outlook_untrash_thread", t.EXEMPT),
        ("mcp__ms365__outlook_trash_thread", t.RECOVERABLE),
        ("mcp__x__untrash_then_delete", t.UNKNOWN),
        ("mcp__x__untrash_everything", t.UNKNOWN),
        ("Bash", t.UNROUTED),
        (None, t.UNROUTED),
    ]
    for name, want in pins:
        got = t.classify(name, {})[0]
        check("T5 %s classifies as %s" % (name, want), got == want, "got=%s" % got)
    check("T5b notion-restore-pages is not routed",
          not t.is_routed("mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-restore-pages"))


def test_input_classifiers():
    cu = "mcp__ccd_host__clean_up_worktrees"
    ut = "mcp__ms365__outlook_untrash_thread"
    fid = "AAMkAGI2" + "A" * 92  # opaque Graph-style folder id (100 chars)
    rm = lambda *dests: {"conversationId": "c1", "restoreMap": [
        {"messageId": "m%d" % i, "destinationFolderId": d} for i, d in enumerate(dests)]}
    cases = [
        # outlook_untrash_thread: no map -> Inbox; opaque ids -> restore; anything else is
        # out of contract; Recoverable Items fails to IRREVERSIBLE; malformed fails closed
        (ut, {"conversationId": "c1"}, t.EXEMPT),
        (ut, rm(fid, fid + "B"), t.EXEMPT),
        (ut, rm("A" * 40), t.EXEMPT),
        (ut, rm("A" * 39), t.RECOVERABLE),
        (ut, rm("deleteditems"), t.RECOVERABLE),
        (ut, rm("inbox"), t.RECOVERABLE),
        (ut, rm(fid, "deleteditems"), t.RECOVERABLE),
        (ut, rm("recoverableitemsdeletions"), t.IRREVERSIBLE),
        (ut, rm("RecoverableItemsPurges"), t.IRREVERSIBLE),
        (ut, rm(fid, "recoverableitemsroot"), t.IRREVERSIBLE),
        (ut, rm("deleteditems", "recoverableitemsdeletions"), t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": None}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": []}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": "x"}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": [1]}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": [{}]}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": [{"destinationFolderId": 5}]}, t.IRREVERSIBLE),
        (ut, {"conversationId": "c1", "restoreMap": [{"destinationFolderId": ""}]}, t.IRREVERSIBLE),
        (ut, ["not", "a", "dict"], t.IRREVERSIBLE),
        (ut, None, t.IRREVERSIBLE),
        (cu, {"older_than_days": 30}, t.RECOVERABLE),
        (cu, {"older_than_days": 30, "delete_sessions": False}, t.RECOVERABLE),
        (cu, {"older_than_days": 30, "delete_sessions": True}, t.IRREVERSIBLE),
        (cu, {"older_than_days": 30, "include_uncommitted": "true"}, t.IRREVERSIBLE),
        (cu, ["not", "a", "dict"], t.IRREVERSIBLE),
        # C9: any set value other than None/False is a delete request (not bool(value))
        (cu, {"delete_sessions": 0}, t.IRREVERSIBLE),
        (cu, {"include_uncommitted": ""}, t.IRREVERSIBLE),
        (cu, {"delete_sessions": []}, t.IRREVERSIBLE),
        (cu, {"delete_sessions": None}, t.RECOVERABLE),
    ]
    seg = "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__manage_segment"
    cases += [
        (seg, {"operation": {"type": "DeleteSegmentOperation", "listId": 1}}, t.RECOVERABLE),
        (seg, {"operation": {"type": "RemoveMembersOperation", "listId": 1}}, t.RECOVERABLE),
        (seg, {"operation": {"type": "RemoveAllMembersOperation", "listId": 1}}, t.IRREVERSIBLE),
        (seg, {"operation": {"type": "AddMembersOperation", "listId": 1}}, t.EXEMPT),
        (seg, {"operation": {"type": "SomethingNew"}}, t.IRREVERSIBLE),
        (seg, {"operation": "DeleteSegmentOperation"}, t.IRREVERSIBLE),
        (seg, {}, t.IRREVERSIBLE),
        # C3: typed-wrong fields fail closed instead of raising
        (seg, {"operation": {"type": ["DeleteSegmentOperation"]}}, t.IRREVERSIBLE),
        (seg, {"operation": {"type": {"a": 1}}}, t.IRREVERSIBLE),
        (seg, {"operation": {"type": 5}}, t.IRREVERSIBLE),
        (seg, {"operation": {"type": None}}, t.IRREVERSIBLE),
        (seg, {"operation": ["DeleteSegmentOperation"]}, t.IRREVERSIBLE),
        (seg, {"operation": None}, t.IRREVERSIBLE),
        (seg, "DeleteSegmentOperation", t.IRREVERSIBLE),
        (seg, None, t.IRREVERSIBLE),
    ]
    camp = "mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__manage_campaign_objects"
    rm = {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"campaignCrmObjectId": 1,
          "assetOperations": [{"action": "REMOVE", "assetObjectType": "BLOG_POST"}]}}
    add = {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"campaignCrmObjectId": 1,
           "assetOperations": [{"action": "ADD", "assetObjectType": "BLOG_POST"}]}}
    cases += [
        (camp, rm, t.RECOVERABLE),
        (camp, add, t.EXEMPT),
        (camp, {"operationType": "CAMPAIGN_CREATE"}, t.EXEMPT),
        (camp, {"operationType": "CAMPAIGN_ASSET"}, t.IRREVERSIBLE),
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"assetOperations": [
            {"action": "DROP"}]}}, t.IRREVERSIBLE),
        (camp, {}, t.IRREVERSIBLE),
        (camp, {"operationType": ["CAMPAIGN_ASSET"]}, t.IRREVERSIBLE),
        (camp, {"operationType": {"a": 1}}, t.IRREVERSIBLE),
        (camp, {"operationType": 5}, t.IRREVERSIBLE),
        (camp, {"operationType": None}, t.IRREVERSIBLE),
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"assetOperations": [
            {"action": ["REMOVE"]}]}}, t.IRREVERSIBLE),
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"assetOperations": [
            {"action": {"x": 1}}, "junk"]}}, t.IRREVERSIBLE),
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"assetOperations": "REMOVE"}},
         t.IRREVERSIBLE),
        (camp, None, t.IRREVERSIBLE),
        # mixed ADD+REMOVE is still a removal; empty ops list fails closed
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"assetOperations": [
            {"action": "ADD", "assetObjectType": "BLOG_POST"},
            {"action": "REMOVE", "assetObjectType": "BLOG_POST"}]}}, t.RECOVERABLE),
        (camp, {"operationType": "CAMPAIGN_ASSET", "assetRequest": {"campaignCrmObjectId": 1,
                                                                    "assetOperations": []}},
         t.IRREVERSIBLE),
    ]
    for name, ti, want in cases:
        try:
            got = t.classify(name, ti)[0]
        except Exception as exc:  # classify must never raise
            got = "RAISED %s" % type(exc).__name__
        check("T6 %s %s -> %s" % (name.rsplit("__", 1)[-1], json.dumps(ti)[:60], want),
              got == want, "got=%s" % got)
    # C3: classify() never raises, for any tool_input shape, on every by-input tool
    weird = [None, 0, 1, "", "x", [], [1], {}, {"operation": object()}, 1.5, True,
             {"operation": {"type": {1, 2}}}, {"operationType": {1, 2}},
             {"delete_sessions": object()}, {"operation": {"type": b"x"}}]
    weird = weird + [{"restoreMap": object()}, {"restoreMap": [object()]},
                     {"restoreMap": [{"destinationFolderId": object()}]},
                     {"restoreMap": [{"destinationFolderId": b"x"}]}]
    for name in (cu, seg, camp, ut):
        raised = []
        for ti in weird:
            try:
                tier = t.classify(name, ti)[0]
                if tier not in (t.RECOVERABLE, t.IRREVERSIBLE, t.EXEMPT):
                    raised.append("%r->%s" % (ti, tier))
            except Exception as exc:
                raised.append("%r->%s" % (ti, type(exc).__name__))
        check("T6b classify never raises for %s" % name.rsplit("__", 1)[-1],
              not raised, "; ".join(raised[:3]))


def test_matcher_models_agree():
    names = full_names(load_snapshot()) | {"mcp__srv__" + k for k in t.TIERS} | {
        "mcp__x__purge_everything", "mcp__x__list_deleted_items", "Bash", "Edit"}
    for name in sorted(names):
        anchored = re.fullmatch(t.SETTINGS_MATCHER, name) is not None
        documented = re.search(t.SETTINGS_MATCHER, name) is not None
        check("T7 anchored == documented routing for %s" % name, anchored == documented,
              "anchored=%s documented=%s" % (anchored, documented))


def test_matcher_edge_names_classify_safely():
    """C5. SETTINGS_MATCHER is unchanged. Its extra-name alternation is end-anchored only in
    the fullmatch model: a suffix-extended name (manage_segment_v2, sharepoint_move_item2,
    clean_up_worktrees_preview) is NOT routed by a fullmatch ("anchored") engine but IS
    routed by an unanchored search ("documented") engine; a non-mcp prefix (xmcp__a__delete)
    is the reverse of that concern: search routes it, fullmatch does not. The models are
    allowed to disagree on these names. T7c checks ONLY what classify() returns; how an
    anchored-engine settings.json would actually behave for these names is UNVERIFIED here.
    What classify() must return, regardless of engine: never EXEMPT and never an IRREVERSIBLE tier row for a name that has
    no row, and UNKNOWN (handled like recoverable) whenever the documented engine routes
    it to the guard, UNROUTED only when neither engine routes it."""
    names = ["mcp__x__manage_segment_v2", "mcp__x__sharepoint_move_item2",
             "mcp__x__clean_up_worktrees_preview", "xmcp__a__delete"]
    for name in names:
        anchored = re.fullmatch(t.SETTINGS_MATCHER, name) is not None
        documented = re.search(t.SETTINGS_MATCHER, name) is not None
        tier = t.classify(name, {"delete_sessions": True})[0]
        check("T7b %s: tier %s is safe (anchored=%s documented=%s)" % (
              name, tier, anchored, documented),
              tier == (t.UNKNOWN if documented and name.startswith("mcp__") else t.UNROUTED),
              "tier=%s" % tier)
        if anchored != documented:
            check("T7c %s: classify() is non-EXEMPT/non-IRREVERSIBLE when engines disagree" % name,
                  tier not in (t.EXEMPT, t.IRREVERSIBLE), "tier=%s" % tier)


def test_keyword_names_are_routed_or_rowed():
    """C6. Every snapshot name KEYWORD_RE hits and that is not read-prefixed must be sent to
    the guard by SETTINGS_MATCHER, unless its TIERS row is EXEMPT (a row alone does not
    gate anything, so non-EXEMPT rows must be routed)."""
    for name in sorted(full_names(load_snapshot())):
        short = t.short_name(name)
        if not t.KEYWORD_RE.search(short) or short.lower().startswith(t.READ_PREFIXES):
            continue
        row = t.TIERS.get(short)
        if row is not None and row[0] == t.EXEMPT:
            continue  # explicit EXEMPT rows (outlook_delete_event, image_remove_background)
        check("T10 delete-shaped %s is routed by SETTINGS_MATCHER" % short, t.is_routed(name))


def test_routed_middle_segment_floor():
    """Reviewer finding: a delete verb in an earlier '__' segment must floor the tier at
    UNKNOWN even when the last segment is a read prefix or an EXEMPT/lenient row."""
    camp_create = {"operationType": "CAMPAIGN_CREATE"}
    cases = [
        ("mcp__x__delete__list_all", {}),
        ("mcp__x__DELETE__restore", {}),
        ("mcp__x__delete__image_remove_background", {}),
        ("mcp__x__delete__outlook_delete_event", {}),
        ("mcp__x__delete__outlook_untrash_thread", {}),
        ("mcp__x__purge_all__list_x", {}),
        ("mcp__x__delete_all__manage_campaign_objects", camp_create),
        ("mcp__my_srv-1__delete__get_thing", {}),
    ]
    for name, ti in cases:
        got = t.classify(name, ti)[0]
        check("T11 %s floors at UNKNOWN" % name, got == t.UNKNOWN, "got=%s" % got)
    # never downgrades a stricter result
    got = t.classify("mcp__x__delete__delete_range", {})[0]
    check("T11b middle verb does not downgrade IRREVERSIBLE", got == t.IRREVERSIBLE, "got=%s" % got)
    got = t.classify("mcp__x__delete__notion-delete-pages", {})[0]
    check("T11c middle verb does not downgrade RECOVERABLE", got == t.RECOVERABLE, "got=%s" % got)
    got = t.classify("mcp__x__delete__delete_trigger", {})[0]
    check("T11f middle verb does not downgrade the delete_trigger IRREVERSIBLE row",
          got == t.IRREVERSIBLE, "got=%s" % got)
    # server segment alone is not a middle segment; clean names unaffected
    check("T11d server name with verb is not a middle segment",
          t.classify("mcp__delete_srv__list_all", {})[0] == t.EXEMPT)
    check("T11e benign middle segment leaves EXEMPT",
          t.classify("mcp__x__tools__list_all", {})[0] == t.EXEMPT)


def test_classifier_exception_fails_closed():
    saved = dict(t._INPUT_CLASSIFIERS)
    try:
        def boom(ti):
            raise RuntimeError("boom")
        t._INPUT_CLASSIFIERS["manage_segment"] = boom
        try:
            got = t.classify("mcp__x__manage_segment", {"operation": {}})[0]
        except Exception as exc:
            got = "RAISED %s" % type(exc).__name__
    finally:
        t._INPUT_CLASSIFIERS.clear()
        t._INPUT_CLASSIFIERS.update(saved)
    check("T12 a raising by-input classifier yields IRREVERSIBLE", got == t.IRREVERSIBLE,
          "got=%s" % got)


def test_oversized_name_is_bounded():
    import time
    name = "mcp__" + "_" * 50000
    start = time.time()
    tier, reason, _short = t.classify(name, {})
    elapsed = time.time() - start
    check("T13 oversized mcp name -> UNKNOWN", tier == t.UNKNOWN, "tier=%s" % tier)
    check("T13b oversized reason says so", "oversized" in reason, reason)
    check("T13c oversized name classified in under 1s", elapsed < 1.0, "%.2fs" % elapsed)
    check("T13d 512-char name is still evaluated normally",
          t.classify("mcp__x__" + "a" * 400, {})[0] == t.UNROUTED)
    check("T13e oversized non-mcp name stays UNROUTED",
          t.classify("x" * 1000, {})[0] == t.UNROUTED)


def test_target_digest():
    a = {"page_ids": ["p1"], "user_confirmed": True}
    b = {"user_confirmed": True, "page_ids": ["p1"], "instructions_version": "0.0.2"}
    c = {"page_ids": ["p2"], "user_confirmed": True}
    check("T8 digest ignores key order and volatile keys",
          t.target_digest(a) == t.target_digest(b))
    check("T8b digest ignores _consent", t.target_digest(dict(a, _consent="x")) == t.target_digest(a))
    check("T8c a different target changes the digest", t.target_digest(a) != t.target_digest(c))
    check("T8d label shape", re.fullmatch(r"notion-delete-pages:[0-9a-f]{16}",
                                          t.target_label("notion-delete-pages", a)) is not None)


def _fullwidth(text):
    """ASCII lowercase letters -> fullwidth forms (U+FF41..), built with chr() to keep this
    file ASCII-only. NFKC folds them back to ASCII, which a lenient lookup might do."""
    return "".join(chr(ord(c) + 0xFEE0) if "a" <= c <= "z" else c for c in text)


def _name_variants(key):
    """Names that are NOT the exact short name but that a lenient lookup could fold onto it."""
    out = {key.upper(), key.swapcase(), key.title(), key.capitalize(),  # case
           " " + key, key + " ",                                        # padding
           key.replace("_", "-"), key.replace("-", "_"),                # separator swap
           _fullwidth(key)}                                             # NFKC-foldable
    out.discard(key)
    return sorted(out)


def test_row_lookup_is_exact_name():
    """T14. TIERS rows key on the EXACT short name. A variant that merely looks like a row
    key (other case, padded with a space, hyphen/underscore swapped, fullwidth letters) must
    get the tier of a name WITHOUT that row, so a row never leaks onto a lookalike. The
    dangerous direction is an EXEMPT or lenient row leaking, for example via
    TIERS.get(short.lower()), TIERS.get(short.strip()) or a separator/NFKC fallback.

    PINNED, NOT ENDORSED. This pins today's behavior, including its weak spots:
      * The five EXTRA_NAMES rows (clean_up_worktrees, sharepoint_move_item,
        notion-calendar-cancel-events, manage_segment, manage_campaign_objects) are matched
        case-sensitively by the matcher too, so their upper-case variants are UNROUTED and
        the guard never sees them (T14c pins that).
      * For IRREVERSIBLE rows, exact-name keying is the LENIENT direction: DELETE_TRIGGER
        only asks interactively while delete_trigger blocks. A future change that raises
        severity for case variants must rewrite T14/T14b on purpose.
    The read-prefix check (short.lower().startswith(READ_PREFIXES)) is a different path and
    is not pinned here."""
    variants_seen = 0
    for key in sorted(t.TIERS):
        for variant in _name_variants(key):
            name = "mcp__x__" + variant
            with_row = t.classify(name, {})[0]
            row = t.TIERS.pop(key)
            try:
                without_row = t.classify(name, {})[0]
            finally:
                t.TIERS[key] = row
            variants_seen += 1
            check("T14 row %s does not apply to variant %r" % (key, variant),
                  with_row == without_row, "with_row=%s without_row=%s" % (with_row, without_row))
    # every key yields >= 2 case variants, 2 padded, 1 fullwidth
    check("T14a the variant sweep actually ran", variants_seen >= 5 * len(t.TIERS),
          "variants=%d rows=%d" % (variants_seen, len(t.TIERS)))
    # readable pins; each differs from its exact-name tier
    for name, exact_tier, want in (
            ("mcp__ms365__OUTLOOK_UNTRASH_THREAD", t.EXEMPT, t.UNKNOWN),
            ("mcp__claude-code-remote__DELETE_TRIGGER", t.IRREVERSIBLE, t.UNKNOWN),
            ("mcp__scheduled-tasks__DELETE_SCHEDULED_TASK", t.IRREVERSIBLE, t.UNKNOWN),
            ("mcp__x__OUTLOOK_DELETE_EVENT", t.EXEMPT, t.UNKNOWN),
            ("mcp__x__ outlook_delete_event", t.EXEMPT, t.UNKNOWN),
            ("mcp__x__outlook_delete_event ", t.EXEMPT, t.UNKNOWN),
            ("mcp__x__outlook-delete-event", t.EXEMPT, t.UNKNOWN)):
        got = t.classify(name, {})[0]
        check("T14b %s is %s, not the exact-name tier %s" % (name.rsplit("__", 1)[-1], want,
                                                           exact_tier),
              got == want and got != exact_tier, "got=%s" % got)
    # documented gap, pinned: EXTRA_NAMES rows are not routed at all when the case differs
    for key in sorted(t.EXTRA_NAMES):
        name = "mcp__x__" + key.upper()
        check("T14c %s is UNROUTED and not routed by the matcher (known gap, pinned)"
              % key.upper(), t.classify(name, {})[0] == t.UNROUTED and not t.is_routed(name),
              "tier=%s routed=%s" % (t.classify(name, {})[0], t.is_routed(name)))


def test_tier_names_are_unique():
    """One override name == one tier (override_tokens.py). config-write-guard owns
    allow-destructive-delete; only mcp-delete-guard may define allow-mcp-delete."""
    owners = {}
    for path in glob.glob(os.path.join(HOOKS_DIR, "*.py")) + glob.glob(
            os.path.join(HOOKS_DIR, "lib", "*.py")):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for m in re.finditer(r'Tier\(\s*"(allow-[a-z-]+)"', text):
            owners.setdefault(m.group(1), set()).add(os.path.basename(path))
    check("T9 allow-mcp-delete is defined only by mcp-delete-guard.py",
          owners.get("allow-mcp-delete") == {"mcp-delete-guard.py"},
          "owners=%s" % sorted(owners.get("allow-mcp-delete", ())))
    check("T9b allow-destructive-delete is still defined only by config-write-guard.py",
          owners.get("allow-destructive-delete") == {"config-write-guard.py"},
          "owners=%s" % sorted(owners.get("allow-destructive-delete", ())))


if __name__ == "__main__":
    test_snapshot_shape_and_age()
    test_every_routed_snapshot_tool_is_classified()
    test_verified_flags_match_snapshot()
    test_every_row_is_reachable()
    test_false_positive_and_read_pins()
    test_input_classifiers()
    test_matcher_models_agree()
    test_matcher_edge_names_classify_safely()
    test_keyword_names_are_routed_or_rowed()
    test_routed_middle_segment_floor()
    test_classifier_exception_fails_closed()
    test_oversized_name_is_bounded()
    test_target_digest()
    test_tier_names_are_unique()
    test_row_lookup_is_exact_name()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL mcp-delete-tiers tests passed.")
    sys.exit(0)
