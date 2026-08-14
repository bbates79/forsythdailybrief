import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_daily import build_edition, edition_filename


def sample_current():
    return {
        "updated_at": "2026-08-14T10:00:00Z",
        "lead": {"title": "County budget discussion", "summary": "A public budget item is coming up.", "link": "https://example.test/lead"},
        "weather": {"status": "ok", "temperature_f": 78.0, "observed_at": "2026-08-14 10:00:00"},
        "lake_lanier": {"status": "ok", "level_ft": 1066.4, "observed_at": "2026-08-14T09:45:00-04:00", "provisional": True},
        "items": [
            {"id":"meeting", "title":"Planning hearing", "summary":"A hearing is scheduled.", "category":"government", "event_date":"2026-08-20", "event_time":"6:30 PM", "approval_status":"approved", "link":"https://example.test/meeting"},
            {"id":"article", "title":"Original FDB story", "summary":"A local story.", "category":"health", "date":"2026-08-13", "approval_status":"approved", "link":"https://example.test/article"},
            {"id":"old", "title":"Old item", "summary":"Old.", "category":"government", "date":"2026-08-01", "approval_status":"approved", "link":"https://example.test/old"},
        ],
        "articles": [{"id":"article", "title":"Original FDB story", "summary":"A local story.", "category":"health", "date":"2026-08-13", "approval_status":"approved", "article_html_path":"articles/story.html"}],
    }


def test_edition_filename_is_date_partitioned():
    assert edition_filename("2026-08-14") == "briefs/2026-08-14.html"


def test_build_edition_has_bounded_sections_and_snapshot():
    result = build_edition(sample_current(), "2026-08-14")
    assert result["date"] == "2026-08-14"
    assert result["status"] == "published"
    assert len(result["what_to_watch"]) == 1
    assert len(result["recent_articles"]) == 1
    assert result["snapshot"]["lake_lanier_ft"] == 1066.4
    assert len(result["latest"]) <= 12


def test_edition_json_is_serializable():
    json.dumps(build_edition(sample_current(), "2026-08-14"))
