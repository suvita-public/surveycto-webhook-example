"""
Replay a SurveyCTO webhook payload locally without SurveyCTO.

Usage:
    python scripts/manual_webhook_test.py
    python scripts/manual_webhook_test.py examples/sample_submission.json
    python scripts/manual_webhook_test.py examples/sample_submission_register_photos.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow `python scripts/manual_webhook_test.py` from project root without installing the package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.datastructures import Headers
from starlette.requests import Request

from app.services.webhook_service import (
    build_submission_dataframe,
    get_latest_submission,
    handle_surveycto_webhook,
)

DEFAULT_PAYLOAD_FILE = PROJECT_ROOT / "examples" / "sample_submission.json"


def load_payload(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Allow optional "_comment" keys in example JSON files.
    return {k: v for k, v in data.items() if not k.startswith("_")}


def make_fake_request(payload: dict) -> Request:
    body = json.dumps(payload).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "headers": Headers(
            {
                "content-type": "application/json",
                "origin": "https://your-server.surveycto.com",
            }
        ).raw,
    }
    return Request(scope, receive=receive)


def run_payload(payload: dict, label: str = "") -> None:
    print(f"\n=== Running Test: {label} ===")
    request = make_fake_request(payload)
    try:
        result = asyncio.run(handle_surveycto_webhook(request))
        print("Response Status:", result.status_code)
        print("Response Content:", result.body.decode())
        print("\nLatest submission DataFrame:")
        print(get_latest_submission())
    except Exception as e:
        print("Exception Raised:", str(e))


def preview_dataframe_only(payload: dict) -> None:
    print("\n=== DataFrame preview (no HTTP) ===")
    print(build_submission_dataframe(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a SurveyCTO webhook JSON file.")
    parser.add_argument(
        "json_file",
        nargs="?",
        default=str(DEFAULT_PAYLOAD_FILE),
        help="Path to example payload (default: examples/sample_submission.json)",
    )
    args = parser.parse_args()

    path = Path(args.json_file)
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")

    payload = load_payload(path)
    print(f"Loaded payload from {path}")
    preview_dataframe_only(payload)
    run_payload(payload, path.name)


if __name__ == "__main__":
    main()
