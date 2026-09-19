r"""Shared Unicode-normalization constant for the ORA hook layer.

Single source of truth for STRIP_CATEGORIES -- the Unicode general categories stripped
ON TOP OF NFKC before any marker / word / recipient matching. Two independent copies of
this tuple existed until 2026-09-18 (ora-autonomy-gate.py's _normalize_for_matching and
tool_call_paths.py's normalize_text), with nothing keeping them in sync.

WHO ACTUALLY CONSUMES THE tool_call_paths SIDE -- counted, not assumed (2026-09-18
adversarial review corrected an inherited "seven guards" figure). SIX hooks import
tool_call_paths: config-write-guard, lint-config-guard, memory-index-guard,
memory-nag-correction, registry-write-guard, workbook-write-guard. Of those, THREE reach
normalize_text (config-write-guard, lint-config-guard, workbook-write-guard; internally
via shell_may_write and recursive_delete). eos-review-gate.py does NOT import this module
at all -- it only mentions it in a comment. The other three use primary_write_path /
is_write_capable, which never normalize.

WHY THAT MATTERED, specifically. ora-autonomy-gate.py is the SOLE enforcement of hard
invariant 2 (no write to the oxfordra.net site tree without Gabriel's confirmation) under
defaultMode=bypassPermissions, where no permission prompt exists as a backstop. If the
tool_call_paths copy were ever hardened -- adding "Cc" or "Me", say -- and the gate's copy
were not, the broadest-blast-radius hook in the layer would silently become its WEAKEST
normalizer while the guards routing through normalize_text were stronger. Nothing would have failed and
no test would have gone red; the gate would just quietly stop seeing an evasion class the
other guards catch.

WHAT THE CATEGORIES ARE, and why only these two:

  Cf  format characters -- zero-width space U+200B, RTL/LTR override U+202E/U+202D, soft
      hyphen, ... . Inserted MID-WORD they break a \bword\b or substring match invisibly:
      `net<ZWSP>lify`, or a ZWSP inside the "send-via-outlook.ps1" trigger phrase itself.
      Both reached exit 0 (unblocked) before being stripped -- proven live, Round 3
      adversarial review, 2026-07-17.
  Mn  nonspacing combining marks -- e.g. combining low line U+0332. Same failure mode,
      same round.

NFKC folds COMPATIBILITY forms (fullwidth U+FF20 "@", mathematical alphanumerics) back to
ASCII but does NOT remove either category, so the fold alone is not enough. Legitimate
infra command/path text has no legitimate reason to carry either, so stripping them is
targeted hardening, not a breadth-over-precision tradeoff like the site-marker matcher.

THIS MODULE EXPORTS A CONSTANT, NOT A MATCHER -- deliberately, and for the same reason
hooks/lib/site_markers.py exports two tuples rather than one unified list: the consumers
must AGREE on the categories and must NOT be forced to consume them the same way. Their
non-str contracts are exact opposites, and each is matched to its caller's fail posture:

  ora-autonomy-gate.py  _normalize_for_matching(text) is str-ONLY and mounts no defense
      against other types. It does not need one, but the precise reason is narrower than
      "main() rejects non-str" (2026-09-18 review corrected an overstatement here):
        - a non-str Bash `command` IS rejected by block_shape() -- exit 2, fail CLOSED;
        - a TRUTHY non-str file_path (5, True, a list, a dict) is likewise rejected;
        - a FALSY non-str file_path (None, 0, False, [], {}) is NOT rejected -- main()'s
          `tool_input.get("file_path") or tool_input.get("notebook_path") or ""` chain
          coerces it to "", which passes the isinstance check and reaches the normalizer
          as an empty string (exit 0, nothing to match). Pre-existing behavior, untouched.
      So the guarantee that holds is the one that matters here: the normalizer only ever
      receives a str. Giving it a "return '' on non-str" guard would buy nothing and would
      convert the two fail-CLOSED refusals above into a silent empty string that matches
      no marker -- fail OPEN, on the one hook in this layer that must never do that.

  tool_call_paths.py    normalize_text(text) returns "" on non-str, deliberately. It
      parses arbitrary tool_input JSON, where a field may legitimately be any type, so
      raising there would turn one odd payload into an exception inside every importing
      guard. Note the degradation posture is NOT uniform across those importers, and
      "degrades to inert" is only true for two of them: with tool_call_paths unavailable,
      config-write-guard and lint-config-guard go inert, workbook-write-guard loses one
      of its checks, and registry-write-guard / memory-index-guard / memory-nag-correction
      keep working on verbatim legacy parsing. That is exactly why tool_call_paths now
      carries a pinned fallback of its own rather than a bare import -- see below.

A unified matcher would have to pick ONE of those, and either choice is wrong for the
other caller. Sharing the CONSTANT closes the drift hazard; sharing the FUNCTION would
open a worse one.

ORDER RULE FOR PATH CONSUMERS -- recorded here so the next consumer does not rediscover
it. If you normalize a FILE PATH, resolve the literal path FIRST and normalize the
RESULT; never realpath() the normalized string. Stripping a Cf character CHANGES the
path, so realpath() on the normalized form asks the filesystem about a name the tool will
never open: a junction whose real directory name carries an invisible character resolves
to nothing, the junction is therefore not followed, and a write through it into a guarded
tree is never seen. The correct shape is two independent checks -- match the normalized
literal TEXT (that is what catches homoglyph and invisible-character spellings), and
separately and unconditionally match the realpath of the RAW path.

  ora-autonomy-gate.py's own check_file_write follows this rule (PR #212,
  fix/site-gate-slug-dir-exemption, merged 2026-09-18): it resolves `os.path.realpath
  (file_path)` -- the literal, unnormalized path -- FIRST, then normalizes the result
  (`resolved_literal`), rather than normalizing before resolving. That branch's own
  adversarial review is what proved the WRONG order exploitable: three proven exit-0
  writes into a site checkout via a junction whose real directory name differed from
  its literal name only by a character normalization folds or deletes.

BOTH CONSUMERS hold a hardcoded fallback copy of STRIP_CATEGORIES, because neither can
afford to die on a missing shared module, and each is pinned to this tuple by test:
  ora-autonomy-gate.py   -> test-ora-autonomy-gate.py::
                            test_strip_categories_fallback_matches_shared_module
  tool_call_paths.py     -> test-tool-call-paths.py::
                            test_strip_categories_fallbacks_match_shared_module
A fallback that nothing pins is just a duplicate under another name. Both also
shape-validate the imported value and fall back on a wrong TYPE, because a module that
imports cleanly but exports None raises on every later call rather than at import.

Stdlib only. ASCII-only.
"""

# The ONE definition. Order is not significant (membership test only), but keep it
# stable so the pinned fallback copies can be compared literally.
STRIP_CATEGORIES = ("Cf", "Mn")
