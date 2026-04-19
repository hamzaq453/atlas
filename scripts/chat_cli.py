from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx


def _parse_sse_line(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    raw = line.removeprefix("data:").strip()
    if not raw:
        return None
    return json.loads(raw)


def stream_chat(base_url: str, message: str, conversation_id: str | None) -> int:
    payload: dict[str, Any] = {"message": message, "stream": True}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{base_url.rstrip('/')}/chat", json=payload) as response:
            if response.status_code != 200:
                print(f"HTTP {response.status_code}: {response.text}", file=sys.stderr)  # noqa: T201
                return 1

            for line in response.iter_lines():
                if not line:
                    continue
                event = _parse_sse_line(line)
                if event is None:
                    continue
                etype = event.get("type")
                if etype == "token":
                    sys.stdout.write(str(event.get("data", "")))
                    sys.stdout.flush()
                elif etype == "heartbeat":
                    continue
                elif etype == "done":
                    print(  # noqa: T201
                        f"\n[done conversation_id={event.get('conversation_id')} "
                        f"message_id={event.get('message_id')}]",
                    )
                elif etype == "error":
                    print(f"\n[error] {event.get('message')}", file=sys.stderr)  # noqa: T201
                    return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal /chat client for Atlas")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ATLAS_BASE_URL", "http://localhost:8000"),
        help="Atlas API base URL",
    )
    parser.add_argument("--once", help="Send a single message and exit", metavar="MESSAGE")
    args = parser.parse_args()

    conversation_id: str | None = None

    if args.once:
        return stream_chat(args.base_url, args.once, conversation_id)

    print("Atlas chat CLI — type a message, empty line exits.", file=sys.stderr)  # noqa: T201
    while True:
        try:
            user = input("you> ").strip()
        except EOFError:
            return 0
        if not user:
            return 0
        code = stream_chat(args.base_url, user, conversation_id)
        if code != 0:
            return code


if __name__ == "__main__":
    raise SystemExit(main())
