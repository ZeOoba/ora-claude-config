"""Open-sessions probe: find Claude Code Desktop + Cowork Desktop sessions waiting on Gabriel.

Walks both session stores, tail-reads each unarchived session's transcript, and
classifies what (if anything) the session is waiting for:

  NEEDS-ANSWER  last assistant message asks a question / AskUserQuestion pending
  STALLED       a tool call never returned (killed mid-run or awaiting approval)
  INTERRUPTED   Gabriel's last message never got a reply
  NO-ACTION     closed cleanly, just not archived
  UNKNOWN       no transcript found / unreadable

Read-only: never writes to either store. Stdlib only.

Usage:
  python open_sessions_probe.py                  # markdown report, actionable only
  python open_sessions_probe.py --all            # include NO-ACTION + fleet runs
  python open_sessions_probe.py --json           # machine-readable
  python open_sessions_probe.py --days 14        # lookback window (default 30)
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from collections import namedtuple

APPDATA = os.environ.get("APPDATA", os.path.expanduser(r"~\AppData\Roaming"))
CC_STORE = os.path.join(APPDATA, "Claude", "claude-code-sessions")
LAMS_STORE = os.path.join(APPDATA, "Claude", "local-agent-mode-sessions")
PROJECTS_DIR = os.path.expanduser(os.path.join("~", ".claude", "projects"))
TAIL_BYTES = 400_000
SNIPPET_LEN = 220

# Scheduled-fleet sessions are machine runs, not threads Gabriel opened.
FLEET_TITLE = re.compile(r"^ora[ -]", re.IGNORECASE)

OFFER_PHRASES = re.compile(
    r"\b(want me to|should i|shall i|do you want|which (option|one|approach)|"
    r"your call|let me know (if|which|whether|when)|confirm before|say the word|"
    r"awaiting your|need your (approval|confirmation|decision|input))\b",
    re.IGNORECASE)


class Status:
    NEEDS_ANSWER = "NEEDS-ANSWER"
    STALLED = "STALLED"
    INTERRUPTED = "INTERRUPTED"
    NO_ACTION = "NO-ACTION"
    UNKNOWN = "UNKNOWN"


PRIORITY = {Status.NEEDS_ANSWER: 0, Status.STALLED: 1, Status.INTERRUPTED: 2,
            Status.UNKNOWN: 3, Status.NO_ACTION: 4}

Verdict = namedtuple("Verdict", "status snippet")


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _blocks(content, kind):
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") == kind]


def _is_human_user(content):
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return not _blocks(content, "tool_result") and bool(_text_of(content).strip())
    return False


def _ends_as_question(text):
    tail = text.rstrip()[-300:]
    if tail.rstrip(" \n*_`").endswith("?"):
        return True
    return bool(OFFER_PHRASES.search(tail))


def classify(entries):
    """Classify a transcript (list of parsed JSONL entries) -> Verdict."""
    meaningful = []
    for e in entries:
        if not isinstance(e, dict) or e.get("isSidechain"):
            continue
        if e.get("type") not in ("user", "assistant"):
            continue
        msg = e.get("message")
        if not isinstance(msg, dict):
            continue
        meaningful.append((e["type"], msg.get("content")))
    if not meaningful:
        return Verdict(Status.UNKNOWN, "")

    last_type, last_content = meaningful[-1]
    last_text = ""
    for typ, content in reversed(meaningful):
        if typ == "assistant":
            last_text = _text_of(content).strip()
            if last_text:
                break
    snippet = re.sub(r"\s+", " ", last_text)[:SNIPPET_LEN]

    if last_type == "assistant":
        tool_uses = _blocks(last_content, "tool_use")
        if tool_uses:
            if any(t.get("name") == "AskUserQuestion" for t in tool_uses):
                qs = []
                for t in tool_uses:
                    for q in (t.get("input") or {}).get("questions", []):
                        qs.append(q.get("question", ""))
                return Verdict(Status.NEEDS_ANSWER,
                               re.sub(r"\s+", " ", " | ".join(filter(None, qs)) or snippet)[:SNIPPET_LEN])
            return Verdict(Status.STALLED, snippet)
        text = _text_of(last_content).strip()
        if text and _ends_as_question(text):
            return Verdict(Status.NEEDS_ANSWER, snippet)
        return Verdict(Status.NO_ACTION, snippet)

    # last entry is a user-side record
    if _is_human_user(last_content):
        human = re.sub(r"\s+", " ", _text_of(last_content).strip())[:SNIPPET_LEN]
        return Verdict(Status.INTERRUPTED, human)
    return Verdict(Status.STALLED, snippet)  # trailing tool_result, turn never finished


def is_scheduled_run(entries):
    """True if the transcript's first human message is a scheduled-task run.

    Catches retired/renamed automation sessions (e.g. loopnet-autoreply) whose
    titles don't match FLEET_TITLE — their first user message starts with a
    literal <scheduled-task …> tag injected by the task runner."""
    for e in entries:
        if not isinstance(e, dict) or e.get("type") != "user":
            continue
        msg = e.get("message")
        if not isinstance(msg, dict):
            continue
        return _text_of(msg.get("content")).lstrip().startswith("<scheduled-task")
    return False


# ---------------------------------------------------------------- store walking

def _head_lines(path, nbytes=262_144):
    try:
        with open(path, "rb") as f:
            data = f.read(nbytes).decode("utf-8", errors="replace")
        lines = data.splitlines()
        if len(data.encode("utf-8", errors="replace")) >= nbytes and lines:
            lines = lines[:-1]  # drop partial last line
        return lines
    except OSError:
        return []


def _tail_lines(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            offset = max(0, size - TAIL_BYTES)
            f.seek(offset)
            data = f.read().decode("utf-8", errors="replace")
        lines = data.splitlines()
        if offset > 0 and lines:
            lines = lines[1:]  # drop partial first line
        return lines
    except OSError:
        return []


def _parse_jsonl(lines):
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _munge(cwd):
    return re.sub(r"[^A-Za-z0-9]", "-", cwd or "")


def _cc_transcript(meta):
    cli_id = meta.get("cliSessionId")
    if not cli_id:
        return None
    p = os.path.join(PROJECTS_DIR, _munge(meta.get("cwd", "")), cli_id + ".jsonl")
    if os.path.exists(p):
        return p
    hits = glob.glob(os.path.join(PROJECTS_DIR, "*", cli_id + ".jsonl"))
    return hits[0] if hits else None


def _iter_store(store, surface):
    for meta_path in glob.glob(os.path.join(store, "*", "*", "local_*.json")):
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict) or meta.get("isArchived"):
            continue
        yield meta_path, meta, surface


def collect(days):
    now_ms = time.time() * 1000
    cutoff = now_ms - days * 86_400_000
    rows = []
    for meta_path, meta, surface in (
            list(_iter_store(CC_STORE, "CODE")) + list(_iter_store(LAMS_STORE, "COWORK"))):
        last_ms = meta.get("lastActivityAt") or meta.get("createdAt") or 0
        if last_ms < cutoff:
            continue
        if surface == "CODE":
            tpath = _cc_transcript(meta)
        else:
            tpath = os.path.join(meta_path[:-5], "audit.jsonl")  # strip ".json"
            if not os.path.exists(tpath):
                tpath = None
        verdict = (classify(_parse_jsonl(_tail_lines(tpath)))
                   if tpath else Verdict(Status.UNKNOWN, ""))
        title = meta.get("title") or "(untitled)"
        fleet = bool(FLEET_TITLE.match(title))
        if not fleet and tpath:
            fleet = is_scheduled_run(_parse_jsonl(_head_lines(tpath)))
        rows.append({
            "surface": surface,
            "title": title,
            "status": verdict.status,
            "snippet": verdict.snippet,
            "sessionId": meta.get("sessionId"),
            "lastActivityAt": last_ms,
            "ageHours": round(max(0, now_ms - last_ms) / 3_600_000, 1),
            "fleet": fleet,
        })
    rows.sort(key=lambda r: (PRIORITY.get(r["status"], 9), -r["lastActivityAt"]))
    return rows


def _age(h):
    return f"{h:.0f}h" if h < 48 else f"{h/24:.0f}d"


def render_markdown(rows, show_all):
    actionable = [r for r in rows if not r["fleet"]
                  and r["status"] in (Status.NEEDS_ANSWER, Status.STALLED, Status.INTERRUPTED)]
    lines = ["# Open Claude sessions awaiting you",
             f"_{len(actionable)} actionable / {len(rows)} unarchived in window_", ""]
    if not actionable:
        lines.append("Nothing is waiting on you. All clear.")
    last_status = None
    for r in actionable:
        if r["status"] != last_status:
            lines.append(f"\n## {r['status']}")
            last_status = r["status"]
        live = " · may still be running" if r["ageHours"] <= 0.25 else ""
        lines.append(f"- **[{r['surface']}] {r['title']}** ({_age(r['ageHours'])} ago{live})")
        if r["snippet"]:
            lines.append(f"  > {r['snippet']}")
    if show_all:
        rest = [r for r in rows if r not in actionable]
        lines.append(f"\n## Everything else ({len(rest)})")
        for r in rest:
            tag = " [fleet]" if r["fleet"] else ""
            lines.append(f"- [{r['surface']}] {r['title']}{tag} — "
                         f"{r['status']}, {_age(r['ageHours'])} ago")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30, help="lookback window (default 30)")
    ap.add_argument("--all", action="store_true", help="include NO-ACTION and fleet runs")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args(argv)
    rows = collect(args.days)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        out = render_markdown(rows, args.all)
        sys.stdout.buffer.write(out.encode("utf-8"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
