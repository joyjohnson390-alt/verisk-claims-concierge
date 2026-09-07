from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Weather API", version="1.0.0")

_enabled = True

KNOWN_EVENTS = {
    (30.4213, -87.2169): {
        "event_type": "Hurricane",
        "event_name": "Hurricane Helene",
        "date": "2024-09-26",
        "wind_speed_mph": 95,
        "hail_size_inches": None,
        "precipitation_inches": 8.4,
        "loss_index": 0.82,
        "note": "Major hurricane landfall near Pensacola; widespread roof and structural damage reported.",
    },
    (30.6954, -88.0399): {
        "event_type": "Severe Storm",
        "event_name": "Gulf Coast Severe Storm",
        "date": "2024-10-01",
        "wind_speed_mph": 65,
        "hail_size_inches": 1.25,
        "precipitation_inches": 3.1,
        "loss_index": 0.54,
        "note": "Severe thunderstorm complex with large hail impacting Mobile metro area.",
    },
    (30.3960, -88.8853): {
        "event_type": "Tornado",
        "event_name": "Biloxi EF-2 Tornado",
        "date": "2024-10-05",
        "wind_speed_mph": 130,
        "hail_size_inches": None,
        "precipitation_inches": 1.9,
        "loss_index": 0.91,
        "note": "EF-2 tornado touched down in Biloxi coastal area; significant structural losses.",
    },
}

COORD_TOLERANCE = 0.05


class StatusResponse(BaseModel):
    enabled: bool


def _find_event(lat: float, lon: float) -> Optional[dict]:
    for (klat, klon), event in KNOWN_EVENTS.items():
        if abs(lat - klat) <= COORD_TOLERANCE and abs(lon - klon) <= COORD_TOLERANCE:
            return event
    return None


@app.get("/weather/{lat}/{lon}/{date}")
def get_weather(lat: float, lon: float, date: str):
    if not _enabled:
        raise HTTPException(
            status_code=503,
            detail="Weather data service is currently unavailable. Please try again later.",
        )

    event = _find_event(lat, lon)
    if event:
        return {
            **event,
            "location": {"lat": lat, "lon": lon},
            "data_source": "NOAA-VERISK-FEED",
        }

    return {
        "event_type": "Severe Storm",
        "event_name": "Regional Severe Weather Event",
        "date": date,
        "location": {"lat": lat, "lon": lon},
        "wind_speed_mph": 55,
        "hail_size_inches": 0.75,
        "precipitation_inches": 2.2,
        "loss_index": 0.38,
        "data_source": "NOAA-VERISK-FEED",
        "note": "Moderate severe weather event detected for this location and date.",
    }


@app.get("/admin/status", response_model=StatusResponse)
def get_status():
    return {"enabled": _enabled}


@app.post("/admin/toggle", response_model=StatusResponse)
def toggle_api():
    global _enabled
    _enabled = not _enabled
    state = "enabled" if _enabled else "disabled"
    print(f"[WeatherAPI] Service toggled: now {state}")
    return {"enabled": _enabled}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
