"""Wait until one HTTP endpoint returns a non-error response."""

from __future__ import annotations

import sys
import time

import httpx


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: wait_for_http.py <url>")
    url = sys.argv[1]
    deadline = time.time() + 60
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code < 500:
                return 0
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)
    raise SystemExit(f"endpoint did not become ready: {url}; last_error={last_error}")


if __name__ == "__main__":
    raise SystemExit(main())
