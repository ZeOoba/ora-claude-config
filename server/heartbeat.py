#!/usr/bin/env python3
"""ORA Notion heartbeat producer (server-side).

NOTE: the producer MOVES HERE from the LAMS desktop task
(ora-cowork-heartbeat, 05:50 + 17:50 ET), which only fired while the Claude
Desktop app was open -- the root cause of the 2026-05-31..06-10 heartbeat
outage. The GitHub Actions watchdog (ZeOoba/ora-cowork-watchdog) stays
UNCHANGED as the off-box monitor: it probes the same page by ID every 4h
and alarms at 16h staleness. Do not move the watchdog onto this server --
a dead-man switch must not share the failure domain it watches.

Mechanism: PATCH https://api.notion.com/v1/pages/<HEARTBEAT_PAGE_ID>,
alternating the page icon between two heart emojis by 12-hour beat index
(unix_time // 43200) so consecutive scheduled beats ALWAYS carry a
different icon. Two layers: (1) Notion registers an edit (bumps
last_edited_time) on every successful page PATCH, which is the primary
mover; (2) the icon alternation is defense-in-depth against any
no-op-update deduplication. Beat-index parity (not UTC-hour parity) is
deliberate: the two daily beats are 12 hours apart, so hour parity would
make consecutive beats IDENTICAL within a DST regime, leaving layer (2)
inert exactly when it matters.

Env:
  NOTION_TOKEN       required. .strip()ed before use (2026-06-11 lesson: a
                     pasted trailing newline made the Authorization header
                     invalid -- urllib raises InvalidHeader).
  HEARTBEAT_PAGE_ID  optional; default 35c6ecd8-9e59-81d5-8d2c-d08002458b78
                     (the canonical "Cowork Heartbeat" page under OpsHub --
                     probe BY ID, never by title search; v02 doctrine).

Behavior: on success prints exactly one ASCII line and exits 0. On ANY
failure prints an ASCII error and exits 1 -- the systemd unit's failure
state is the on-box signal; the GitHub watchdog is the off-box one.

Stdlib only (urllib). ASCII-only source (emojis via escape sequences) and
ASCII-only output. Scheduled by ora-heartbeat.timer (see server/units/).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

NOTION_VERSION = "2022-06-28"
DEFAULT_PAGE_ID = "35c6ecd8-9e59-81d5-8d2c-d08002458b78"
# Unicode escapes keep this source file ASCII-only.
HEART_EVEN = "\u2764\ufe0f"  # red heart (even 12h beat index)
HEART_ODD = "\U0001f499"     # blue heart (odd 12h beat index)
TIMEOUT_SECONDS = 30


def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("heartbeat ERROR: NOTION_TOKEN is not set (or empty)", file=sys.stderr)
        return 1

    page_id = os.environ.get("HEARTBEAT_PAGE_ID", "").strip() or DEFAULT_PAGE_ID
    now = datetime.now(timezone.utc)
    beat_index = int(now.timestamp()) // 43200  # flips every 12h regardless of cadence
    even = beat_index % 2 == 0
    icon = HEART_EVEN if even else HEART_ODD
    icon_name = "red-heart" if even else "blue-heart"

    # json.dumps defaults to ensure_ascii=True, so the payload is pure ASCII.
    body = json.dumps({"icon": {"type": "emoji", "emoji": icon}}).encode("ascii")
    request = urllib.request.Request(
        "https://api.notion.com/v1/pages/" + page_id,
        data=body,
        method="PATCH",
        headers={
            "Authorization": "Bearer " + token,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            response.read()
    except urllib.error.HTTPError as exc:
        print(
            "heartbeat ERROR: Notion API HTTP %d %s (page %s)"
            % (exc.code, exc.reason, page_id),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # URLError, socket.timeout, InvalidHeader, ...
        print("heartbeat ERROR: %s" % (exc,), file=sys.stderr)
        return 1

    if status != 200:
        print("heartbeat ERROR: unexpected HTTP status %d" % status, file=sys.stderr)
        return 1

    print(
        "heartbeat OK page=%s icon=%s beat_index=%d utc=%s"
        % (page_id, icon_name, beat_index, now.strftime("%Y-%m-%dT%H:%MZ"))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
