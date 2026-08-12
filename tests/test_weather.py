import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pipeline import WEATHER_STATIONS, aggregate_weather, parse_weatherstem

FIXTURE = {
    "time": "2026-08-12 10:18:43",
    "records": [
        {"sensor_name": "Thermometer", "value": 75.0, "units": "°F"},
        {"sensor_name": "Hygrometer", "value": 85.4, "units": "%"},
        {"sensor_name": "Anemometer", "value": 3, "units": "mph"},
        {"sensor_name": "Rain: Accum last 24 hr", "value": 0.0, "units": "in."},
        {"sensor_name": "Heat Index", "value": 77.3, "units": "°F"},
    ],
}


def test_parse_weatherstem_extracts_current_readings():
    result = parse_weatherstem(FIXTURE, "fire4")
    assert result["station"] == "fire4"
    assert result["temperature_f"] == 75.0
    assert result["humidity_percent"] == 85.4
    assert result["wind_mph"] == 3
    assert result["rain_24h_in"] == 0.0
    assert result["observed_at"] == "2026-08-12 10:18:43"


def test_aggregate_weather_uses_median_temperature_and_latest_timestamp():
    second = dict(FIXTURE, time="2026-08-12 10:19:00", records=[{"sensor_name":"Thermometer", "value":77.0, "units":"°F"}])
    result = aggregate_weather([parse_weatherstem(FIXTURE, "fire4"), parse_weatherstem(second, "fire6")])
    assert result["station_count"] == 2
    assert result["temperature_f"] == 76.0
    assert result["observed_at"] == "2026-08-12 10:19:00"


def test_weather_station_inventory_has_all_six_public_stations():
    assert {x["handle"] for x in WEATHER_STATIONS} == {"allianceacademy", "fire4", "fire6", "fire8", "forsythema", "cumming"}


def test_aggregate_weather_ignores_empty_station_results():
    result = aggregate_weather([])
    assert result["station_count"] == 0
    assert result["temperature_f"] is None
    assert result["status"] == "unavailable"
