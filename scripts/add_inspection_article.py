#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/approval-queue.json"
ARTICLE = {
    "id": "d430a53c7aef32ab",
    "title": "Friends Cumming Grill receives U grade in Aug. 4 health inspection",
    "summary": "Friends Cumming Grill received a U grade with a score of 42 in an Aug. 4 routine inspection. The public report lists violations involving food protection, temperatures, sanitation, facility maintenance and pest control, and says the facility voluntarily closed pending compliance and reinspection.",
    "source": "Georgia Department of Public Health",
    "source_type": "official",
    "category": "health",
    "date": "2026-08-04",
    "link": "https://ga.healthinspections.us/georgia/history.cfm?id=13007732&inspID=57545038&county=Forsyth",
    "approval_status": "pending",
    "review_reason": "sensitive_public_health",
    "article_path": "articles/friends-cumming-grill-gets-u-grade-2026-08-04.html",
    "article_markdown_path": "articles/friends-cumming-grill-gets-u-grade-2026-08-04.md",
    "inspection_score": 42,
    "inspection_grade": "U",
    "establishment": "Friends Cumming Grill",
    "address": "506 Lakeland Plaza, Cumming, GA 30040",
    "inspection_date": "2026-08-04",
    "full_report": "https://ga.healthinspections.us/_templates/87/food_2015/_report_full.cfm?fsimID=57545038&domainID=87&rtype=food_2015"
}

data = json.loads(QUEUE.read_text())
items = {item["id"]: item for item in data.get("items", [])}
items[ARTICLE["id"]] = ARTICLE
data["items"] = list(items.values())
data["updated_at"] = datetime.now(timezone.utc).isoformat()
QUEUE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print(f"Queued {ARTICLE['id']} for lightweight approval")
