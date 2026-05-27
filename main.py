"""FastAPI service that fetches temperature data from OpenSenseMap."""
import os
import sys
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
import httpx
from dotenv import load_dotenv
from prometheus_client import make_asgi_app
from print_version import VERSION


load_dotenv()

print(f"--- Was .env loaded successfully? {load_dotenv()} ---")  # 👈 Add this line temporary

app = FastAPI()

metrics_app = make_asgi_app()

app.mount("/metrics", metrics_app)

BASE_URL = os.environ.get("BASE_URL")
if not BASE_URL:
    print("CRITICAL ERROR: BASEURL environment variable is not set!", file=sys.stderr)
    sys.exit(1)

async def get_box_data(sensebox_id: str):
    """Fetch box data from OpenSenseMap API by senseBox ID."""
    url = f"{BASE_URL}/{sensebox_id}?format=json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

@app.get("/temperature")
async def get_temperature():
    """Return average temperature from multiple OpenSenseMap sensors."""
    raw_ids= os.environ.get("ids", "")
    ids = [id.strip() for id in raw_ids.split(",") if id.strip()]
    if not ids:
        return {"error": "No senseBox IDs configured in environment"}
    # ts=[]
    temperature_avg=0
    count=0
    for id1 in ids:
        data = await get_box_data(id1)

        try:
            sensors = data['sensors']

            temperature = [
                s for s in sensors
                if "temperature" in s.get("title", "").lower()
                or "temperatur" in s.get("title", "").lower()
            ]
            if not temperature:
                continue
            time = temperature[0]["lastMeasurement"]["createdAt"]
            time_value = datetime.fromisoformat(time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            if not (now - time_value) <= timedelta(hours=1):
                continue
            latest_value = float(
                temperature[0]["lastMeasurement"]["value"]
                )
            temperature_avg += latest_value
            #ts.append(latest_value)
            count += 1
        except (KeyError, TypeError) as e:
            print(f"Error processing box {id1}: {e}", file=sys.stderr)
            continue
    if count == 0:
        return {"error": "no valid temperature data found within the last hour"}
    temperature_avg = temperature_avg / count
    if temperature_avg < 10:
        status = "Too Cold"
    elif temperature_avg < 37:
        status = "Good"
    else:
        status = "Too Hot"
    return {
        #"ts": ts,
        "temperature": temperature_avg,
        "status": status
    }
@app.get("/version")
def get_version():
    """Return API version."""
    return VERSION
