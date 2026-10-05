#!/usr/bin/env python3
"""ground-truth-model-resolve.py -- verifier model-floor ladder for the ORA
Ground-Truth Auditor (design spec Sec 5 Stage 2).

The registry's `model` field is absent for ~69% of the fleet (CC 20/38, LAMS
1/29 -- spec Sec 3.1), so the audited run's model cannot be a simple field
lookup. Resolves in order:

  1. registry `model` field, when present;
  2. the `[MODEL: <id> ...]` tag in the task's SKILL.md frontmatter
     description (a bare word, e.g. "observed", may follow the id before the
     closing `|`/`]` -- the real production format does this);
  3. the joined session record's `model`, when present;
  4. failing all three (or an audited model outside the known tier table),
     assume the highest tier and verify at Opus 5.5.

Step 4 is deliberately fail-safe: an unknown model must never silently
license a CHEAPER verifier than the run it audits (reviewer >= implementer).
"""
import re

TOP_MODEL = "claude-opus-5-5"  # top dispatch tier since 2026-10-05 (was claude-fable-5-1)

# Captures the model id, tolerating one bare trailing word (e.g. "observed")
# before the required '|' or ']' -- matches the real production tag format:
# "[MODEL: claude-opus-5 observed | checked 2026-08-12 via ... canary]".
MODEL_TAG_RE = re.compile(r"\[MODEL:\s*([a-zA-Z0-9._-]+)(?:\s+\w+)*\s*(?:\||\])")

# Coarse tier ordering (lowest to highest) for "reviewer >= implementer".
# Unknown models are never assumed cheap -- see resolve_verifier_model step 4.
MODEL_TIERS = ["claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5", TOP_MODEL]


def _tier(model_id):
    try:
        return MODEL_TIERS.index(model_id)
    except ValueError:
        return -1  # unknown model: never in the known table


def extract_model_tag(skill_md_text):
    """The `[MODEL: <id> ...]` tag from a SKILL.md frontmatter description,
    or None if absent/unparseable."""
    if not skill_md_text:
        return None
    m = MODEL_TAG_RE.search(skill_md_text)
    return m.group(1) if m else None


def resolve_audited_model(task_record, skill_md_text=None, session_record=None):
    """Resolve which model actually ran the audited task, per the 3-rung
    ladder (registry -> SKILL.md tag -> session record). Returns
    (model_id_or_None, source: str)."""
    model = task_record.get("model")
    if model:
        return model, "registry"
    tagged = extract_model_tag(skill_md_text)
    if tagged:
        return tagged, "skill_md_tag"
    session_model = (session_record or {}).get("model")
    if session_model:
        return session_model, "session_record"
    return None, "unresolved"


def resolve_verifier_model(task_record, skill_md_text=None, session_record=None):
    """The model the VERIFIER must run at: >= the audited run's own model
    (reviewer >= implementer), or Opus 5.5 if the audited model could not be
    resolved, or was resolved to something outside the known tier table
    (fail-safe -- spec Sec 5 Stage 2 step 4).

    Returns (verifier_model_id: str, reasoning: str).
    """
    audited_model, source = resolve_audited_model(task_record, skill_md_text, session_record)
    if audited_model is None:
        return TOP_MODEL, ("audited model unresolved (registry/SKILL.md tag/session "
                              "record all absent) -- fail-safe to Opus 5.5, never assume cheap")
    audited_tier = _tier(audited_model)
    if audited_tier < 0:
        return TOP_MODEL, ("audited model '{}' not in the known tier table -- "
                              "fail-safe to Opus 5.5".format(audited_model))
    return MODEL_TIERS[audited_tier], (
        "audited model '{}' resolved via {} -- verifying at >= that tier".format(
            audited_model, source))


# Full model id -> short Agent-tool `model` parameter name. The Agent tool only
# accepts these four short names; passing a full id (e.g. "claude-opus-5")
# would fail the dispatch. Every id in MODEL_TIERS must have an entry here.
AGENT_TOOL_MODEL_NAMES = {
    "claude-haiku-4-5-20251001": "haiku",
    "claude-sonnet-5": "sonnet",
    "claude-opus-5": "opus",
    TOP_MODEL: "opus",
}


def to_agent_tool_model_name(full_model_id):
    """Map a full model id (as returned by resolve_verifier_model) to the
    short name the Agent tool's `model` parameter accepts (sonnet | opus |
    haiku). Raises ValueError -- loudly, never silently -- if given
    a full id outside the known map, since silently returning something
    wrong would produce an invalid Agent-tool dispatch."""
    try:
        return AGENT_TOOL_MODEL_NAMES[full_model_id]
    except KeyError:
        raise ValueError(
            "to_agent_tool_model_name: no Agent-tool short name mapped for "
            "model id '{}' -- known ids are {}. Refusing to guess (an invalid "
            "Agent-tool model name must never be produced silently).".format(
                full_model_id, sorted(AGENT_TOOL_MODEL_NAMES)))
