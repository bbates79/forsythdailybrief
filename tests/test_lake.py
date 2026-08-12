import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pipeline import parse_usgs_lake_level, empty_lake_level


def sample():
    return {
        "value": {
            "timeSeries": [{
                "variable": {"variableName": "Elevation of reservoir water surface above datum, ft", "unit": {"unitCode": "ft"}},
                "values": [{"value": [
                    {"value": "1066.40", "qualifiers": ["P"], "dateTime": "2026-08-12T10:00:00.000-04:00"},
                    {"value": "1066.46", "qualifiers": ["P"], "dateTime": "2026-08-12T10:15:00.000-04:00"}
                ]}]
            }]
        }
    }


def test_parse_usgs_lake_level_uses_latest_reading():
    result = parse_usgs_lake_level(sample())
    assert result["status"] == "ok"
    assert result["level_ft"] == 1066.46
    assert result["observed_at"] == "2026-08-12T10:15:00.000-04:00"
    assert result["provisional"] is True
    assert result["site"] == "02334400"


def test_empty_lake_level_is_explicitly_unavailable():
    result = empty_lake_level("USGS unavailable")
    assert result["status"] == "unavailable"
    assert result["level_ft"] is None
    assert result["error"] == "USGS unavailable"


def test_lake_level_does_not_invent_full_pool_comparison():
    result = parse_usgs_lake_level(sample())
    assert "full_pool_ft" not in result
    assert result["source_url"].startswith("https://")
