"""FastAPI service that fetches temperature data from OpenSenseMap."""
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
import httpx
from print_version import VERSION

app = FastAPI()

BASE_URL = "https://api.opensensemap.org/boxes"

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
    ids=['5eba5fbad46fb8001b799786', '5c21ff8f919bf8001adf2488', '5ade1acf223bd80019a1011c']
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
            return {"error": str(e)}
    if count == 0:
        return {"error: no temperature found"}
    temperature_avg = temperature_avg / count
    return {
        #"ts": ts,
        "temperature": temperature_avg
    }
@app.get("/version")
def get_verstion():
    """Return API version."""
    return VERSION
