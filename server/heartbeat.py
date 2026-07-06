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
alternating the page icon between two heart emojis so consecutive scheduled
beats ALWAYS carry a different icon. Two layers: (1) Notion registers an edit
(bumps last_edited_time) on every successful page PATCH, which is the primary
mover; (2) the icon alternation is defense-in-depth against any no-op-update
deduplication. The icon is chosen by a true toggle: GET the page's current
icon and PATCH the OTHER heart, so even two Persistent catch-up beats that
share a 12h beat index still alternate. If the GET fails we fall back to
12-hour beat-index parity (unix_time // 43200). Beat-index parity (not
UTC-hour parity) is deliberate: the two daily beats are 12 hours apart, so
hour parity would make consecutive beats IDENTICAL within a DST regime,
leaving layer (2) inert exactly when it matters.

Resilience: the PATCH is retried up to 3 times on a transient 429/5xx/DNS/
timeout blip (honoring Retry-After on 429) before failing, so a single hiccup
does not trip the off-box 16h staleness watchdog. A 4xx (auth/not-found) is
terminal and fails immediately.

Env:
  NOTION_TOKEN       required. .strip()ed before use (2026-06-11 lesson: a
                     pasted trailing newline made the Authorization header
                     invalid -- urllib raises InvalidHeader).
  HEARTBEAT_PAGE_ID  optional; default 35c6ecd8-9e59-81d5-8d2c-d08002458b78
                     (the canonical "Cowork Heartbeat" page under OpsHub --
                     probe BY ID, never by title search; v02 doctrine).
  HEARTBEAT_RETRY_SLEEP  optional; seconds between PATCH retries (default 60).
                     Exists so tests can drive the retry loop fast; leave unset
                     in production.

Behavior: on success prints exactly one ASCII line and exits 0. On ANY
failure prints an ASCII error and exits 1 -- the systemd unit's failure
state is the on-box signal; the GitHub watchdog is the off-box one.

Stdlib only (urllib). ASCII-only source (emojis via escape sequences) and
ASCII-only output. Scheduled by ora-heartbeat.timer (see server/units/).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

NOTION_VERSION = "2022-06-28"
DEFAULT_PAGE_ID = "35c6ecd8-9e59-81d5-8d2c-d08002458b78"
# Unicode escapes keep this source file ASCII-only.
HEART_EVEN = "\u2764\ufe0f"  # red heart (even 12h beat index)
HEART_ODD = "\U0001f499"     # blue heart (odd 12h beat index)
TIMEOUT_SECONDS = 30

# Retry a transient 429/5xx/DNS/timeout blip a couple of times before failing,
# so a single hiccup does not trip the off-box 16h staleness watchdog. The
# sleep is env-overridable ONLY so the test can drive the loop fast; production
# leaves it at 60s.
RETRY_ATTEMPTS = 3
RETRY_SLEEP_SECONDS = int(os.environ.get("HEARTBEAT_RETRY_SLEEP", "60"))
# Cap an honored Retry-After so a hostile/absurd value can't itself out-sleep
# the watchdog window.
RETRY_AFTER_CAP_SECONDS = 300


def _headers(token, with_content_type=False):
    hdrs = {
        "Authorization": "Bearer " + token,
        "Notion-Version": NOTION_VERSION,
    }
    if with_content_type:
        hdrs["Content-Type"] = "application/json"
    return hdrs


def get_current_icon(page_id, token):
    """Return the page's current emoji icon, or None if it can't be read.

    Best-effort GET: lets us toggle to the OTHER heart regardless of the beat
    index, so two Persistent catch-up beats that share a 12h index still
    alternate. Never raises -- callers fall back to beat-index parity on None.
    """
    request = urllib.request.Request(
        "https://api.notion.com/v1/pages/" + page_id,
        method="GET",
        headers=_headers(token),
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:  # any failure -> caller uses the beat-index fallback
        return None
    icon = data.get("icon") or {}
    if icon.get("type") == "emoji":
        return icon.get("emoji")
    return None


def _retry_after_seconds(exc):
    """Parse a Retry-After header (integer seconds only) from an HTTPError."""
    headers = getattr(exc, "headers", None)
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if not raw:
        return None
    try:
        secs = int(str(raw).strip())
    except ValueError:
        return None  # HTTP-date form: ignore, use the default backoff
    if secs < 0:
        return None
    return min(secs, RETRY_AFTER_CAP_SECONDS)


def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("heartbeat ERROR: NOTION_TOKEN is not set (or empty)", file=sys.stderr)
        return 1

    page_id = os.environ.get("HEARTBEAT_PAGE_ID", "").strip() or DEFAULT_PAGE_ID
    now = datetime.now(timezone.utc)
    beat_index = int(now.timestamp()) // 43200  # flips every 12h regardless of cadence
    even = beat_index % 2 == 0

    # Prefer a true toggle off the page's CURRENT icon (robust to two catch-up
    # beats sharing a beat index); fall back to beat-index parity if the GET
    # fails. last_edited_time (bumped by the PATCH below) stays the primary mover.
    current = get_current_icon(page_id, token)
    if current == HEART_EVEN:
        icon, icon_name = HEART_ODD, "blue-heart"
    elif current == HEART_ODD:
        icon, icon_name = HEART_EVEN, "red-heart"
    else:
        icon = HEART_EVEN if even else HEART_ODD
        icon_name = "red-heart" if even else "blue-heart"

    # json.dumps defaults to ensure_ascii=True, so the payload is pure ASCII.
    body = json.dumps({"icon": {"type": "emoji", "emoji": icon}}).encode("ascii")
    request = urllib.request.Request(
        "https://api.notion.com/v1/pages/" + page_id,
        data=body,
        method="PATCH",
        headers=_headers(token, with_content_type=True),
    )

    last_error = "no attempt made"
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        sleep_for = RETRY_SLEEP_SECONDS
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                response.read()
            if status == 200:
                print(
                    "heartbeat OK page=%s icon=%s beat_index=%d utc=%s"
                    % (page_id, icon_name, beat_index, now.strftime("%Y-%m-%dT%H:%MZ"))
                )
                return 0
            # Unexpected non-200 without an exception: retryable.
            last_error = "unexpected HTTP status %d" % status
        except urllib.error.HTTPError as exc:
            # Only 429 and 5xx are transient; 4xx (auth/not-found) is terminal.
            if exc.code == 429 or 500 <= exc.code < 600:
                last_error = "Notion API HTTP %d %s (page %s)" % (exc.code, exc.reason, page_id)
                retry_after = _retry_after_seconds(exc)
                if retry_after is not None:
                    sleep_for = retry_after
            else:
                print(
                    "heartbeat ERROR: Notion API HTTP %d %s (page %s)"
                    % (exc.code, exc.reason, page_id),
                    file=sys.stderr,
                )
                return 1
        except Exception as exc:  # URLError, socket.timeout, InvalidHeader, DNS ...
            last_error = "%s" % (exc,)

        if attempt < RETRY_ATTEMPTS:
            time.sleep(sleep_for)

    print(
        "heartbeat ERROR: %s (after %d attempts)" % (last_error, RETRY_ATTEMPTS),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
