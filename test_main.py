"""Unit tests for the FastAPI temperature service."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_sensor_data(
    value: str, minutes_ago: int = 0, title: str = "Temperature"
) -> dict:
    """Build a minimal senseBox API response with one temperature sensor."""
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "sensors": [
            {
                "title": title,
                "lastMeasurement": {"value": value, "createdAt": ts},
            }
        ]
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():  # pylint: disable=redefined-outer-name
    """Create a TestClient, suppressing the print() side-effect in print_version.py."""
    with patch("builtins.print"):
        from main import app  # pylint: disable=import-outside-toplevel
    return TestClient(app)


# ── /version ──────────────────────────────────────────────────────────────────

class TestVersionEndpoint:
    """Tests for the GET /version endpoint."""

    def test_returns_200(self, client):  # pylint: disable=redefined-outer-name
        """Endpoint returns HTTP 200."""
        response = client.get("/version")
        assert response.status_code == 200

    def test_returns_version_string(self, client):  # pylint: disable=redefined-outer-name
        """Endpoint returns the version defined in print_version.py."""
        response = client.get("/version")
        assert response.json() == "v0.0.1"

    def test_no_parameters_required(self, client):  # pylint: disable=redefined-outer-name
        """Endpoint must work without any query parameters."""
        response = client.get("/version")
        assert response.status_code == 200


# ── /temperature ──────────────────────────────────────────────────────────────

class TestTemperatureEndpoint:
    """Tests for the GET /temperature endpoint."""
    # pylint: disable=redefined-outer-name
    # ── happy path ────────────────────────────────────────────────────────────

    def test_returns_200_when_sensors_active(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Endpoint returns HTTP 200 when at least one sensor has fresh data."""
        fresh_data = make_sensor_data("20.0", minutes_ago=10)
        with patch("main.get_box_data", new=AsyncMock(return_value=fresh_data)):
            response = client.get("/temperature")
        assert response.status_code == 200

    def test_returns_average_of_three_sensors(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Average of 10, 20, 30 should be 20.0 and status should be Good."""
        values = ["10.0", "20.0", "30.0"]
        side_effects = [make_sensor_data(v, minutes_ago=5) for v in values]
        with patch("main.get_box_data", new=AsyncMock(side_effect=side_effects)):
            response = client.get("/temperature")

        body = response.json()
        assert body["temperature"] == 20.0
        assert body["status"] == "Good"

    def test_returns_single_sensor_value(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """When only one box has fresh data the value is returned as-is."""
        data = [
            make_sensor_data("15.5", minutes_ago=30),
            make_sensor_data("12.0", minutes_ago=65),   # stale - excluded
            make_sensor_data("10.0", minutes_ago=70),   # stale - excluded
        ]
        with patch("main.get_box_data", new=AsyncMock(side_effect=data)):
            response = client.get("/temperature")

        body = response.json()
        assert body["temperature"] == 15.5
        assert body["status"] == "Good"

    def test_sensor_title_case_insensitive(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Sensor matching is case-insensitive ('TEMPERATURE', 'Temperatur', etc.)."""
        data = [
            make_sensor_data("21.0", minutes_ago=5, title="TEMPERATURE"),
            make_sensor_data("23.0", minutes_ago=5, title="Temperatur"),
            make_sensor_data("25.0", minutes_ago=5, title="temperature"),
        ]
        with patch("main.get_box_data", new=AsyncMock(side_effect=data)):
            response = client.get("/temperature")

        body = response.json()
        assert body["temperature"] == 23.0
        assert body["status"] == "Good"

    # ── status boundaries ─────────────────────────────────────────────────────

    def test_status_too_cold(self, client):
        """Temperatures below 10 should return 'Too Cold'."""
        data = make_sensor_data("9.4", minutes_ago=5)
        with patch("main.get_box_data", new=AsyncMock(return_value=data)):
            response = client.get("/temperature")
        body = response.json()
        assert body["status"] == "Too Cold"

    def test_status_good_boundary(self, client):
        """Temperatures between 10 and 36.999 should return 'Good'."""
        data = make_sensor_data("36.5", minutes_ago=5)
        with patch("main.get_box_data", new=AsyncMock(return_value=data)):
            response = client.get("/temperature")
        body = response.json()
        assert body["status"] == "Good"

    def test_status_too_hot(self, client):
        """Temperatures 37 and above should return 'Too Hot'."""
        data = make_sensor_data("37.1", minutes_ago=5)
        with patch("main.get_box_data", new=AsyncMock(return_value=data)):
            response = client.get("/temperature")
        body = response.json()
        assert body["status"] == "Too Hot"

    # ── staleness filter ──────────────────────────────────────────────────────

    def test_excludes_measurements_older_than_one_hour(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Measurements older than 60 minutes must not contribute to the average."""
        data = [
            make_sensor_data("100.0", minutes_ago=61),   # stale
            make_sensor_data("100.0", minutes_ago=90),   # stale
            make_sensor_data("100.0", minutes_ago=120),  # stale
        ]
        with patch("main.get_box_data", new=AsyncMock(side_effect=data)):
            response = client.get("/temperature")
        body = response.json()
        assert "error" in body

    def test_excludes_measurement_exactly_at_one_hour_boundary(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """A reading at exactly 60 minutes old is excluded."""
        data = [
            make_sensor_data("18.0", minutes_ago=60),
            make_sensor_data("18.0", minutes_ago=60),
            make_sensor_data("18.0", minutes_ago=60),
        ]
        with patch("main.get_box_data", new=AsyncMock(side_effect=data)):
            response = client.get("/temperature")
        body = response.json()
        assert "error" in body

    def test_mixes_fresh_and_stale_sensors(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Only fresh readings should be averaged; stale ones are silently dropped."""
        data = [
            make_sensor_data("10.0", minutes_ago=5),    # fresh
            make_sensor_data("20.0", minutes_ago=5),    # fresh
            make_sensor_data("999.0", minutes_ago=90),  # stale - must be ignored
        ]
        with patch("main.get_box_data", new=AsyncMock(side_effect=data)):
            response = client.get("/temperature")

        body = response.json()
        assert body["temperature"] == 15.0
        assert body["status"] == "Good"

    # ── error / edge cases ────────────────────────────────────────────────────

    def test_returns_error_when_all_sensors_stale(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """All stale sensors should result in an error response."""
        stale_data = make_sensor_data("25.0", minutes_ago=120)
        with patch("main.get_box_data", new=AsyncMock(return_value=stale_data)):
            response = client.get("/temperature")
        body = response.json()
        assert "error" in body

    def test_returns_error_when_no_temperature_sensor_found(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Boxes with no temperature sensor should be skipped; error if none found."""
        no_temp = {
            "sensors": [
                {
                    "title": "Humidity",
                    "lastMeasurement": {
                        "value": "60",
                        "createdAt": "2099-01-01T00:00:00Z",
                    },
                }
            ]
        }
        with patch("main.get_box_data", new=AsyncMock(return_value=no_temp)):
            response = client.get("/temperature")
        body = response.json()
        assert "error" in body

    def test_handles_missing_last_measurement(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """A sensor with no lastMeasurement should not crash the endpoint."""
        bad_data = {"sensors": [{"title": "temperature", "lastMeasurement": None}]}
        with patch("main.get_box_data", new=AsyncMock(return_value=bad_data)):
            response = client.get("/temperature")
        assert response.status_code == 200
        assert "error" in response.json()

    def test_handles_missing_sensors_key(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """A box payload with no 'sensors' key should not raise an unhandled exception."""
        with patch("main.get_box_data", new=AsyncMock(return_value={})):
            response = client.get("/temperature")
        assert response.status_code == 200
        assert "error" in response.json()

    def test_temperature_key_in_successful_response(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """Successful response must contain a 'temperature' key."""
        fresh = make_sensor_data("22.5", minutes_ago=15)
        with patch("main.get_box_data", new=AsyncMock(return_value=fresh)):
            response = client.get("/temperature")
        assert "temperature" in response.json()

    def test_temperature_value_is_numeric(
        self, client  # pylint: disable=redefined-outer-name
    ):
        """The 'temperature' value in a successful response must be a number."""
        fresh = make_sensor_data("17.3", minutes_ago=20)
        with patch("main.get_box_data", new=AsyncMock(return_value=fresh)):
            response = client.get("/temperature")
        body = response.json()
        if "temperature" in body:
            assert isinstance(body["temperature"], (int, float))
