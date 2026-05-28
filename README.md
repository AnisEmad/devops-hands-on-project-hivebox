[![Dynamic DevOps Roadmap](https://img.shields.io/badge/Dynamic_DevOps_Roadmap-559e11?style=for-the-badge&logo=Vercel&logoColor=white)](https://devopsroadmap.io/getting-started/)
[![Community](https://img.shields.io/badge/Join_Community-%23FF6719?style=for-the-badge&logo=substack&logoColor=white)](https://newsletter.devopsroadmap.io/subscribe)
[![Telegram Group](https://img.shields.io/badge/Telegram_Group-%232ca5e0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/DevOpsHive/985)
[![Fork on GitHub](https://img.shields.io/badge/Fork_On_GitHub-%2336465D?style=for-the-badge&logo=github&logoColor=white)](https://github.com/DevOpsHiveHQ/devops-hands-on-project-hivebox/fork)

# HiveBox - DevOps End-to-End Hands-On Project

<p align="center">
  <a href="https://devopsroadmap.io/projects/hivebox" style="display: block; padding: .5em 0; text-align: center;">
    <img alt="HiveBox - DevOps End-to-End Hands-On Project" border="0" width="90%" src="https://devopsroadmap.io/img/projects/hivebox-devops-end-to-end-project.png" />
  </a>
</p>

> [!CAUTION]
> **[Fork](https://github.com/DevOpsHiveHQ/devops-hands-on-project-hivebox/fork)** this repo, and create PRs in your fork, **NOT** in this repo!

> [!TIP]
> If you are looking for the full roadmap, including this project, go back to the [getting started](https://devopsroadmap.io/getting-started) page.

This repository is the starting point for [HiveBox](https://devopsroadmap.io/projects/hivebox/), the end-to-end hands-on project.

You can fork this repository and start implementing the [HiveBox](https://devopsroadmap.io/projects/hivebox/) project. HiveBox project follows the same Dynamic MVP-style mindset used in the [roadmap](https://devopsroadmap.io/).

The project aims to cover the whole Software Development Life Cycle (SDLC). That means each phase will cover all aspects of DevOps, such as planning, coding, containers, testing, continuous integration, continuous delivery, infrastructure, etc.

Happy DevOpsing ♾️

## Before you start

Here is a pre-start checklist:

- ⭐ <a target="_blank" href="https://github.com/DevOpsHiveHQ/dynamic-devops-roadmap">Star the **roadmap** repo</a> on GitHub for better visibility.
- ✉️ <a target="_blank" href="https://newsletter.devopsroadmap.io/subscribe">Join the community</a> for the project community activities, which include mentorship, job posting, online meetings, workshops, career tips and tricks, and more.
- 🌐 <a target="_blank" href="https://t.me/DevOpsHive/985">Join the Telegram group</a> for interactive communication.

## Preparation

- [Create GitHub account](https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github) (if you don't have one), then [fork this repository](https://github.com/DevOpsHiveHQ/devops-hands-on-project-hivebox/fork) and start from there.
- [Create GitHub project board](https://docs.github.com/en/issues/planning-and-tracking-with-projects/creating-projects/creating-a-project) for this repository (use `Kanban` template).
- Each phase should be presented as a pull request against the `main` branch. Don’t push directly to the main branch!
- Document as you go. Always assume that someone else will read your project at any phase.
- You can get senseBox IDs by checking the [openSenseMap](https://opensensemap.org/) website. Use 3 senseBox IDs close to each other (you can use the following [5eba5fbad46fb8001b799786](https://opensensemap.org/explore/5eba5fbad46fb8001b799786), [5c21ff8f919bf8001adf2488](https://opensensemap.org/explore/5c21ff8f919bf8001adf2488), and [5ade1acf223bd80019a1011c](https://opensensemap.org/explore/5ade1acf223bd80019a1011c)). Just copy the IDs, you will need them in the next steps.

<br/>
<p align="center">
  <a href="https://devopsroadmap.io/projects/hivebox/" imageanchor="1">
    <img src="https://img.shields.io/badge/Get_Started_Now-559e11?style=for-the-badge&logo=Vercel&logoColor=white" />
  </a><br/>
</p>

---

## Implementation


### Phase 1: Project Setup and Kickoff

Created a project board using Kanban template.

**Why Kanban?** 
Because it's better suited for a solo project.

**Project Goal:**
Build a scalable RESTful API around openSenseMap but customized to help beekeepers with their chores.

**SenseBox IDs:**
- 5eba5fbad46fb8001b799786
- 5c21ff8f919bf8001adf2488
- 5ade1acf223bd80019a1011c

### Phase 2
Created a simple Python script to print the version of the project. This is a common practice in software projects to have a versioning system in place.

The script is containerized using a Dockerfile, which allows for easy deployment and scalability.

To Test the script, you can build the Docker image and run the container:

```bash
# Build the Docker image
docker build -t hivebox-version . 
# Run the Docker container
docker run hivebox-version
``` 
### Phase 3
Roadmap Module: [Start - Laying the Base](https://devopsroadmap.io/foundations/module-03)

#### 3.1 Tools

- **[Hadolint](https://github.com/hadolint/hadolint)** - Dockerfile linter to enforce best practices.
- **[Pylint](https://pypi.org/project/pylint/)** - Python code linter to enforce code quality and style.

Both tools are also available as VS Code extensions for local development feedback.

#### 3.2 Code

The API is built using **FastAPI** and exposes two endpoints:

- `GET /version` - Returns the current version of the deployed app from `print_version.py`.
- `GET /temperature` - Fetches data from 3 senseBox stations and returns the average
  temperature, excluding any measurements older than 1 hour.

Unit tests cover both endpoints, including happy path, staleness filtering, edge cases,
and error handling. Tests are written using `pytest` with `AsyncMock` to avoid real
HTTP calls to the openSenseMap API.

#### 3.3 Containers

The app is containerized using Docker following best practices:

- Base image pinned to `python:3.13-slim` for a minimal and reproducible build.
- Dependencies installed before copying source code to leverage Docker layer caching.
- Container runs on port `8000` using `uvicorn`.


#### 3.4 Continuous Integration

A GitHub Actions CI pipeline is set up with three jobs that run sequentially:

1. **Lint** - Runs `pylint` on Python files and `hadolint` on the Dockerfile.
2. **Test** - Runs `pytest` unit tests.
3. **Build** - Builds the Docker image, starts the container, and tests the `/version` endpoint.

The **OpenSSF Scorecard** workflow is also configured, running on every push to `main`
and weekly on Mondays. Results are uploaded to the GitHub Security → Code Scanning tab.

#### 3.5 Testing

The CI pipeline spins up the Docker container after a successful build and calls the
`/version` endpoint via `curl`, asserting the response matches the expected version.
If the value does not match, the pipeline fails and the container is cleaned up automatically.

### Phase 4: Production Hardening, Environment Configuration & Observability

#### 4.1 Tools & Instrumentation
- **[python-dotenv](https://pypi.org/project/python-dotenv/)**: Integrated to separate code from secrets, dynamically loading external infrastructure variables from an untracked local `.env` configuration file.
- **[prometheus-client](https://github.com/prometheus/client_python)**: Integrated standard Cloud Native metrics collection into the microservice layer to expose performance and scraping telemetry.

#### 4.2 Code Enhancements & Features

The `main.py` backend service was updated with the following critical application logic:

- **Dynamic Configurations**: Shifted the `BASE_URL` and target senseBox `ids` string arrays from rigid code constants to secure system-level environment calls using `os.environ.get()`. Added defensive validation checking to throw a `sys.stderr` failure and block application boot sequences if configurations are missing.
- **Observability Interface (`GET /metrics`)**: Instantiated a Prometheus ASGI application hook and securely mounted it to the `/metrics` endpoint, enabling standard cloud monitoring agents (like Prometheus instances) to pull internal operational data seamlessly.
- **Enriched API Schema & Status Mapping**: Updated the response model contract on the `/temperature` endpoint. The controller now reads the aggregated sensor readings and applies strict business logic criteria to calculate a status condition string alongside the mathematical float average:
  - `< 10°C` $\rightarrow$ `"Too Cold"`
  - `10°C` to `36.99°C` $\rightarrow$ `"Good"`
  - `≥ 37°C` $\rightarrow$ `"Too Hot"`
- **Resilient Fault Isolation**: Wrapped the openSenseMap individual station JSON parsing loops in defensive `try/except (KeyError, TypeError)` exception blocks. If an API call to a specific senseBox returns degraded payloads (missing `sensors` or mismatched formats), the anomaly is isolated to `sys.stderr`, a `continue` loop is executed, and the service aggregates the remaining active sensor grids uninterrupted.

#### 4.3 Running & Validating the Application

To execute the service locally with your target configurations, create a `.env` file in the project root folder:

```env
BASE_URL=[https://api.opensensemap.org/boxes](https://api.opensensemap.org/boxes)
ids=5eba5fbad46fb8001b799786,5c21ff8f919bf8001adf2488,5ade1acf223bd80019a1011c

#### Integration Testing Framework (`test_integration.py`)

To ensure complete reliability between the FastAPI application layer, system environments, and real-world network dependencies, a comprehensive integration testing lifecycle was established using two isolated execution profiles:

1. **Direct In-Process Pipeline (`@pytest.mark.direct`)**: 
   - Fires genuine HTTP network calls directly across the internet to the live `openSenseMap` API servers to assert contract drift protection.
   - Built with defensive socket-level checks (`_internet_available`) to gracefully bypass tests without failing if the execution host loses network connectivity.

2. **Docker Lifecycle Pipeline (`@pytest.mark.docker`)**:
   - Programmatically executes a Docker engine build-and-run sequence locally or inside automated worker nodes.
   - Leverages a custom polling health manager (`_wait_for_http`) to confirm port availability before starting assertions.
   - Includes advanced resilience checks, verifying structural stability against high-concurrency request floods using multi-threaded execution pools (`ThreadPoolExecutor`).

##### Executing Integration Suites

The test execution suite supports strict filtering using custom `pytest.ini` test flags:

```bash
# Run the complete test grid (Unit + Integration)
pytest -v

# Run ONLY direct live-network integration tests
pytest -v -m direct

# Run ONLY containerized Docker lifecycle tests
pytest -v -m docker