import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pipeline import classify, dedupe, normalize_item, merge_publication, parse_meetings, update_queue

MEETING_FIXTURE = '''
<div id="card-3860" class="board-meetings-list__card">
  <p class="board-meetings-list__card-date-text">August 13, 2026</p>
  <h3 class="board-meetings-list__card-title"><a href="https://www.forsythco.com/meetings/civil-service-board-regular-meeting-1000-am/">Civil Service Board &#8211; Regular Meeting 10:00 AM</a></h3>
  <p class="board-meetings-list__card-type">Regular Meeting</p>
  <p class="board-meetings-list__card-detail-text">10:00 AM</p>
  <p class="board-meetings-list__card-detail-text">Forsyth County Juvenile Court Building</p>
  <a href="https://www.forsythco.com/juicebox-meetings/ical-export?meeting_id=3860">Outlook / iCal</a>
</div>
<a href="https://www.forsythco.com/government/forsyth-county-meetings/?view=upcoming">Upcoming Meetings</a>
'''

def test_sensitive_story_requires_approval():
    item = normalize_item({"title":"Sheriff announces arrest after crash", "summary":"Details", "link":"https://example.test/a", "source":"FCSO"}, "public-safety")
    assert classify(item["title"], item["summary"]) == "pending"
    assert item["approval_status"] == "pending"

def test_routine_story_is_automatically_approved():
    item = normalize_item({"title":"Board of Commissioners meeting scheduled", "summary":"Public meeting Thursday", "link":"https://example.test/b", "source":"County"}, "government")
    assert item["approval_status"] == "approved"
    assert item["source_type"] == "official"

def test_dedupe_prefers_first_canonical_link():
    items=[{"id":"a","link":"https://example.test/story?utm_source=x","title":"Same"},{"id":"b","link":"https://example.test/story","title":"Same"}]
    assert len(dedupe(items)) == 1

def test_meeting_parser_only_returns_real_cards_and_event_fields():
    source={"name":"Forsyth County Meetings","url":"https://www.forsythco.com/government/forsyth-county-meetings/?view=upcoming","category":"government","kind":"meetings","source_type":"official"}
    items=parse_meetings(MEETING_FIXTURE, source)
    assert len(items) == 1
    assert items[0]["event_date"] == "2026-08-13"
    assert items[0]["event_time"] == "10:00 AM"
    assert items[0]["event_location"] == "Forsyth County Juvenile Court Building"
    assert items[0]["event_type"] == "Regular Meeting"
    assert "ical-export" in items[0]["calendar_link"]

def test_publication_excludes_unapproved_and_placeholder():
    current={"items":[{"id":"old","approval_status":"approved"},{"id":"welcome-001","approval_status":"approved"}]}
    queue={"items":[{"id":"old","approval_status":"approved"},{"id":"pending","approval_status":"pending"},{"id":"new","approval_status":"approved"}]}
    result=merge_publication(current,queue)
    assert {x["id"] for x in result["items"]} == {"old","new"}
    assert all(x["approval_status"]=="approved" for x in result["items"])

def test_data_files_are_valid_json():
    root = Path(__file__).parents[1]
    for path in [root / "data/current.json", root / "data/approval-queue.json"]:
        json.loads(path.read_text())

def test_reader_oriented_metadata():
    item = normalize_item({"title":"New restaurant opens in south Forsyth", "summary":"Business opening", "link":"https://example.test/c", "source":"Forsyth County News"}, "local-news", source_type="local-reporting")
    assert item["category"] == "business"
    assert item["source_type"] == "local-reporting"

def test_stale_approved_items_are_not_reintroduced():
    current={"items":[{"id":"stale","approval_status":"approved"}]}
    assert merge_publication(current,{"items":[]})["items"] == []

def test_school_category():
    item = normalize_item({"title":"School calendar update", "summary":"District schedule", "link":"https://example.test/d", "source":"Forsyth County Schools"}, "schools", source_type="official")
    assert item["category"] == "schools"

def test_update_queue_drops_stale_approved_items(tmp_path, monkeypatch):
    import pipeline
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps({"items":[{"id":"old","approval_status":"approved"},{"id":"pending","approval_status":"pending"}], "workflow": {}}))
    monkeypatch.setattr(pipeline, "QUEUE", queue_path)
    result = update_queue([{"id":"new","approval_status":"approved"}])
    assert {item["id"] for item in result["items"]} == {"new", "pending"}
