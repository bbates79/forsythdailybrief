import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pipeline import classify, dedupe, normalize_item, merge_publication

def test_sensitive_story_requires_approval():
    item = normalize_item({"title":"Sheriff announces arrest after crash", "summary":"Details", "link":"https://example.test/a", "source":"FCSO"}, "public-safety")
    assert classify(item["title"], item["summary"]) == "pending"
    assert item["approval_status"] == "pending"

def test_routine_story_is_automatically_approved():
    item = normalize_item({"title":"Board of Commissioners meeting scheduled", "summary":"Public meeting Thursday", "link":"https://example.test/b", "source":"County"}, "government")
    assert item["approval_status"] == "approved"

def test_dedupe_prefers_first_canonical_link():
    items=[{"id":"a","link":"https://example.test/story?utm_source=x","title":"Same"},{"id":"b","link":"https://example.test/story","title":"Same"}]
    assert len(dedupe(items)) == 1

def test_publication_excludes_unapproved_and_retains_approved():
    current={"items":[{"id":"old","approval_status":"approved"}]}
    queue={"items":[{"id":"pending","approval_status":"pending"},{"id":"new","approval_status":"approved"}]}
    result=merge_publication(current,queue)
    assert {x["id"] for x in result["items"]} == {"old","new"}
    assert all(x["approval_status"]=="approved" for x in result["items"])

def test_data_files_are_valid_json():
    for path in [Path("data/current.json"),Path("data/approval-queue.json")]: json.loads(path.read_text())
