#!/usr/bin/env python3
"""Source inventory and approval-gate helpers for Forsyth Daily Brief."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    {"name": "Forsyth County Government", "url": "https://www.forsythco.com/", "kind": "official"},
    {"name": "Forsyth County Meetings", "url": "https://www.forsythco.com/government/forsyth-county-meetings/", "kind": "official"},
    {"name": "Forsyth County Schools", "url": "https://www.forsyth.k12.ga.us/", "kind": "official"},
    {"name": "Forsyth County Schools Calendar", "url": "https://www.forsyth.k12.ga.us/calendar", "kind": "official"},
    {"name": "Forsyth County Sheriff’s Office", "url": "https://www.forsythsheriff.org/", "kind": "official"},
    {"name": "Forsyth County News", "url": "https://www.forsythnews.com/", "kind": "local-reporting"},
    {"name": "WSB-TV Forsyth County", "url": "https://www.wsbtv.com/news/local/forsyth-county/", "kind": "local-reporting"},
]


def publishable(item: dict) -> bool:
    return item.get("approval_status") == "approved"


def load_queue() -> dict:
    return json.loads((ROOT / "data" / "approval-queue.json").read_text())


def approved_items(items: list[dict]) -> list[dict]:
    return [item for item in items if publishable(item)]


def main() -> None:
    assert len(SOURCES) >= 5
    print(json.dumps({"source_count": len(SOURCES), "queue_statuses": load_queue()["workflow"]["statuses"]}, indent=2))
    print("Source inventory validation: OK")
    print("No content fetched or published by this scaffold.")


if __name__ == "__main__":
    main()

__all__ = ["SOURCES", "publishable", "load_queue", "approved_items"]
