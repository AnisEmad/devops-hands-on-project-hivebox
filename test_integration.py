# pylint: disable=redefined-outer-name
"""
Integration tests for HiveBox FastAPI service.

Two test groups:
  1. Direct  – runs the app in-process with a real .env file and makes real
               HTTP calls to openSenseMap (skipped gracefully when offline).
  2. Docker  – builds the image, spins up a container, hits the live HTTP
               server, then tears everything down automatically.

Run all:
    pytest test_integration.py -v

Run only direct:
    pytest test_integration.py -v -m direct

Run only docker:
    pytest test_integration.py -v -m docker
"""

import os
import socket
import subprocess
import time

import httpx
import pytest
from fastapi.testclient import TestClient


# ── Helpers ────────────────────────────────────────────────────────────────────

IMAGE_NAME  = "hivebox-integration-test"
CONTAINER_NAME = "hivebox-integration-container"
CONTAINER_PORT = 8000
BASE_URL_ENV = "https://api.opensensemap.org/boxes"
SENSEBOXIDS  = (
    "5eba5fbad46fb8001b799786,"
    "5c21ff8f919bf8001adf2488,"
    "5ade1acf223bd80019a1011c"
)


def _internet_available(host: str = "api.opensensemap.org", port: int = 443,
                         timeout: float = 3.0) -> bool:
    """Return True if we can reach the openSenseMap API over the network."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except OSError:
        return False


def _wait_for_http(url: str, retries: int = 15, delay: float = 1.5) -> bool:
    """Poll *url* until it returns 200 or we exhaust retries."""
    for _ in range(retries):
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code == 200:
                return True
        except httpx.RequestError:
            pass
        time.sleep(delay)
    return False


# ── Markers ────────────────────────────────────────────────────────────────────

requires_internet = pytest.mark.skipif(
    not _internet_available(),
    reason="openSenseMap API is unreachable – skipping live network tests",
)


# ══════════════════════════════════════════════════════════════════════════════
# Group 1 – Direct (in-process, real network calls to openSenseMap)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def direct_client():
    """
    Spin up the FastAPI app in-process with real environment variables,
    then hand back a TestClient that will make actual HTTP calls to openSenseMap.
    """
    os.environ.setdefault("BASE_URL", BASE_URL_ENV)
    os.environ.setdefault("ids", SENSEBOXIDS)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BASE_URL", BASE_URL_ENV)
        mp.setenv("ids", SENSEBOXIDS)
        # pylint: disable=import-outside-toplevel
        import importlib
        import main as main_module
        importlib.reload(main_module)
        yield TestClient(main_module.app)


@pytest.mark.direct
class TestDirectVersion:
    """GET /version – direct in-process tests (no network needed)."""

    def test_status_200(self, direct_client):
        """Verify the endpoint returns an HTTP 200 OK status code."""
        r = direct_client.get("/version")
        assert r.status_code == 200

    def test_returns_semver_string(self, direct_client):
        """Verify the return payload format matches a standard SemVer string."""
        body = direct_client.get("/version").json()
        assert isinstance(body, str)
        assert body.startswith("v")

    def test_value_matches_print_version(self, direct_client):
        """Verify the response string matches the system constant exactly."""
        # pylint: disable=import-outside-toplevel
        from print_version import VERSION
        body = direct_client.get("/version").json()
        assert body == VERSION


@pytest.mark.direct
@requires_internet
class TestDirectTemperature:
    """GET /temperature – direct in-process tests hitting real openSenseMap API."""

    def test_status_200(self, direct_client):
        """Verify the live metrics return endpoint yields a successful response."""
        r = direct_client.get("/temperature")
        assert r.status_code == 200

    def test_response_has_temperature_or_error_key(self, direct_client):
        """Verify response contains either a valid metric array or error payload."""
        body = direct_client.get("/temperature").json()
        assert "temperature" in body or "error" in body

    def test_temperature_is_numeric_when_present(self, direct_client):
        """Verify value format evaluates to a numeric int or float object."""
        body = direct_client.get("/temperature").json()
        if "temperature" in body:
            assert isinstance(body["temperature"], (int, float))

    def test_status_field_is_valid_when_present(self, direct_client):
        """Verify environmental condition categories use approved string definitions."""
        body = direct_client.get("/temperature").json()
        if "status" in body:
            assert body["status"] in ("Too Cold", "Good", "Too Hot")

    def test_status_matches_temperature_value(self, direct_client):
        """Business-logic: status string must agree with the numeric temperature."""
        body = direct_client.get("/temperature").json()
        if "temperature" not in body:
            pytest.skip("No fresh data available from senseBox stations")

        temp   = body["temperature"]
        status = body["status"]

        if temp < 10:
            assert status == "Too Cold", f"Expected 'Too Cold' for {temp}°C"
        elif temp < 37:
            assert status == "Good",     f"Expected 'Good' for {temp}°C"
        else:
            assert status == "Too Hot",  f"Expected 'Too Hot' for {temp}°C"


@pytest.mark.direct
class TestDirectMetrics:
    """GET /metrics – Prometheus scrape endpoint."""

    def test_status_200(self, direct_client):
        """Verify metrics route serves telemetry requests successfully."""
        r = direct_client.get("/metrics/")
        assert r.status_code == 200

    def test_content_type_is_text(self, direct_client):
        """Verify response headers conform to standard Prometheus exposition format."""
        r = direct_client.get("/metrics/")
        assert "text/plain" in r.headers.get("content-type", "")

    def test_contains_python_info_metric(self, direct_client):
        """Verify target runtime metrics strings are embedded within data block."""
        r = direct_client.get("/metrics/")
        assert "python_info" in r.text


# ══════════════════════════════════════════════════════════════════════════════
# Group 2 – Docker (build image → run container → real HTTP → teardown)
# ══════════════════════════════════════════════════════════════════════════════

def _docker_available() -> bool:
    """Return True if the local host system execution context has Docker active."""
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


requires_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available – skipping container tests",
)


@pytest.fixture(scope="module")
def docker_container():
    """
    Build the Docker image, run a container with the required env vars,
    wait for it to be healthy, yield the base URL, then clean up.
    """
    if not _docker_available():
        pytest.skip("Docker daemon not available – skipping container tests")

    dockerfile_dir = os.path.dirname(os.path.abspath(__file__))

    # --- Build ---
    subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, dockerfile_dir],
        check=True,
    )

    # --- Run ---
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p",    f"{CONTAINER_PORT}:{CONTAINER_PORT}",
            "-e",    f"BASE_URL={BASE_URL_ENV}",
            "-e",    f"ids={SENSEBOXIDS}",
            IMAGE_NAME,
        ],
        check=True,
    )

    base = f"http://localhost:{CONTAINER_PORT}"
    healthy = _wait_for_http(f"{base}/version")

    yield base if healthy else None

    # --- Teardown (always runs) ---
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True, check=False)
    subprocess.run(["docker", "rm",   CONTAINER_NAME], capture_output=True, check=False)


@pytest.mark.docker
@requires_docker
class TestDockerVersion:
    """GET /version – against a live Docker container."""

    def test_container_is_healthy(self, docker_container):
        """Verify the framework successfully maps connection loops to the container."""
        assert docker_container is not None, (
            "Container did not become healthy in time"
        )

    def test_status_200(self, docker_container):
        """Verify running application container responds to version checks with 200."""
        r = httpx.get(f"{docker_container}/version", timeout=5)
        assert r.status_code == 200

    def test_returns_version_string(self, docker_container):
        """Verify server container processes data payload into string type."""
        body = httpx.get(f"{docker_container}/version", timeout=5).json()
        assert isinstance(body, str)
        assert body.startswith("v")

    def test_value_matches_source(self, docker_container):
        """Verify production container payload versions match source declarations."""
        # pylint: disable=import-outside-toplevel
        from print_version import VERSION
        body = httpx.get(f"{docker_container}/version", timeout=5).json()
        assert body == VERSION


@pytest.mark.docker
@requires_docker
@requires_internet
class TestDockerTemperature:
    """GET /temperature – against a live Docker container, real openSenseMap calls."""

    def test_status_200(self, docker_container):
        """Verify proxy configurations handle requests completely through to endpoints."""
        r = httpx.get(f"{docker_container}/temperature", timeout=10)
        assert r.status_code == 200

    def test_response_has_expected_keys(self, docker_container):
        """Verify serialization contracts maintain strict block layout schema requirements."""
        body = httpx.get(f"{docker_container}/temperature", timeout=10).json()
        assert "temperature" in body or "error" in body

    def test_temperature_numeric(self, docker_container):
        """Verify response floats preserve mathematical numeric behaviors inside container."""
        body = httpx.get(f"{docker_container}/temperature", timeout=10).json()
        if "temperature" in body:
            assert isinstance(body["temperature"], (int, float))

    def test_status_field_valid(self, docker_container):
        """Verify string status mappings execute accurately under container runtimes."""
        body = httpx.get(f"{docker_container}/temperature", timeout=10).json()
        if "status" in body:
            assert body["status"] in ("Too Cold", "Good", "Too Hot")

    def test_status_matches_temperature(self, docker_container):
        """Verify conditional classification bounds hold under integration profiles."""
        body = httpx.get(f"{docker_container}/temperature", timeout=10).json()
        if "temperature" not in body:
            pytest.skip("No fresh sensor data available right now")

        temp   = body["temperature"]
        status = body["status"]

        if temp < 10:
            assert status == "Too Cold"
        elif temp < 37:
            assert status == "Good"
        else:
            assert status == "Too Hot"


@pytest.mark.docker
@requires_docker
class TestDockerMetrics:
    """GET /metrics – against a live Docker container."""

    def test_status_200(self, docker_container):
        """Verify Prometheus telemetry mounts expose metrics outside container barriers."""
        r = httpx.get(f"{docker_container}/metrics/", timeout=5)
        assert r.status_code == 200

    def test_prometheus_text_format(self, docker_container):
        """Verify data outputs adhere to standard formatting rule requirements."""
        r = httpx.get(f"{docker_container}/metrics/", timeout=5)
        assert "text/plain" in r.headers.get("content-type", "")
        assert "python_info" in r.text


@pytest.mark.docker
@requires_docker
class TestDockerResilience:
    """Container-level resilience and edge cases."""

    def test_unknown_route_returns_404(self, docker_container):
        """Verify router missing-path handlers process exceptions with a 404 status."""
        r = httpx.get(f"{docker_container}/nonexistent", timeout=5)
        assert r.status_code == 404

    def test_multiple_sequential_version_calls_stable(self, docker_container):
        """The /version endpoint must return the same value on every call."""
        results = {
            httpx.get(f"{docker_container}/version", timeout=5).json()
            for _ in range(5)
        }
        assert len(results) == 1, "Version changed between calls!"

    def test_concurrent_requests_do_not_crash_container(self, docker_container):
        """Fire 5 concurrent requests; all must return 200."""
        # pylint: disable=import-outside-toplevel
        import concurrent.futures
        urls = [f"{docker_container}/version"] * 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(
                lambda u: httpx.get(u, timeout=5).status_code, urls
            ))
        assert all(s == 200 for s in responses)
