"""Live deployment smoke test for auth, LangChain tool use, SSE and Mongo history.

Usage (PowerShell):
  $env:FLIGHTGUARD_API_URL="https://your-api.onrender.com"
  $env:FLIGHTGUARD_API_TOKEN="<guest-or-Clerk-bearer-token>"
  python backend/scripts/smoke_agent.py

Use a freshly issued guest token or a Clerk session token. Never commit tokens.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("FLIGHTGUARD_API_URL", "").rstrip("/")
TOKEN = os.environ.get("FLIGHTGUARD_API_TOKEN", "")

if not BASE_URL or not TOKEN:
    sys.exit("Set FLIGHTGUARD_API_URL and FLIGHTGUARD_API_TOKEN before running this smoke test.")


def stream_agent(message: str, session_id: str | None = None):
    payload = {"message": message, "known_facts": {}}
    if session_id:
        payload["session_id"] = session_id
    request = urllib.request.Request(
        f"{BASE_URL}/agent/ask/stream",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    events = []
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if "text/event-stream" not in response.headers.get("Content-Type", ""):
                raise RuntimeError(f"Expected SSE, received {response.headers.get('Content-Type')}")
            event_name = "message"
            data_lines = []
            for raw in response:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif not line and data_lines:
                    raw_data = "\n".join(data_lines)
                    try:
                        data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        data = {"raw": raw_data}
                    events.append((event_name, data))
                    event_name, data_lines = "message", []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agent HTTP {exc.code}: {detail}") from exc
    return events


first = stream_agent("Please look up the DGCA policy for a cancelled Indian domestic flight and explain the relevant passenger rights.")
first_types = [name for name, _ in first]
print("First request events:", first_types)

session_events = [data for name, data in first if name == "session"]
if not session_events or not session_events[0].get("session_id"):
    sys.exit("FAIL: server did not return a session_id event")
session_id = session_events[0]["session_id"]

if "route" not in first_types:
    sys.exit("FAIL: no route event")
if "token" not in first_types:
    sys.exit("FAIL: no incremental model token events")
tool_names = [data.get("tool") for name, data in first if name == "tool_start"]
if "search_dgca_policy" not in tool_names:
    sys.exit(f"FAIL: expected search_dgca_policy tool start, observed {tool_names}")
if "done" not in first_types:
    sys.exit("FAIL: stream did not complete")
first_done = next(data for name, data in first if name == "done")
if first_done.get("status") != "complete":
    sys.exit(f"FAIL: agent reported {first_done.get('status')}")
if "error" in first_types:
    sys.exit("FAIL: agent emitted an error event")

second = stream_agent("Please summarize the important DGCA points you just found.", session_id=session_id)
second_types = [name for name, _ in second]
print("Follow-up events:", second_types)
if "done" not in second_types or "error" in second_types:
    sys.exit("FAIL: follow-up request did not complete; check MongoDB session persistence and logs")

print("PASS: bearer auth, SSE streaming, route selection, policy tool invocation and session follow-up completed.")
