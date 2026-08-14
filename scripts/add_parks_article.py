import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/approval-queue.json"
item = {
    "id": "852bf1bb0d6949d7",
    "title": "Forsyth County plans tennis and pickleball court improvements at three parks",
    "summary": "Four new tennis courts are planned at Sawnee Mountain Park, while courts at Matt Community Park and Coal Mountain Park are scheduled for resurfacing. The county says some disruption is expected, but construction dates, costs, and closure schedules have not yet been published.",
    "source": "Forsyth County Government video and park pages",
    "source_type": "official",
    "category": "parks-recreation",
    "date": "2026-08-13",
    "link": "https://www.youtube.com/@focogovernment/videos",
    "approval_status": "pending",
    "review_reason": "original_local_article",
    "article_path": "articles/forsyth-parks-tennis-pickleball-court-improvements.md",
    "article_html_path": "articles/forsyth-parks-tennis-pickleball-court-improvements.html"
}
data = json.loads(QUEUE.read_text())
items = {x["id"]: x for x in data.get("items", [])}
items[item["id"]] = item
data["items"] = list(items.values())
data["updated_at"] = datetime.now(timezone.utc).isoformat()
QUEUE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("Queued", item["id"])
