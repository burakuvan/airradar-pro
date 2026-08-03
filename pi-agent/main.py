#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests

CENTER_LAT = float(os.getenv("AIRRADAR_LAT", "38.2924"))
CENTER_LON = float(os.getenv("AIRRADAR_LON", "27.1570"))
API_URL = os.getenv("AIRRADAR_API_URL", "https://radar.kuvan.dev/api/update")
INTERVAL = max(10, int(os.getenv("AIRRADAR_INTERVAL", "15")))
TIMEOUT = int(os.getenv("AIRRADAR_TIMEOUT", "20"))
OPENSKY_URL = os.getenv(
    "AIRRADAR_OPENSKY_URL",
    "https://opensky-network.org/api/states/all?lamin=37.80&lomin=26.55&lamax=38.80&lomax=27.80",
)
RUNNING = True


def stop(*_: Any) -> None:
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def distance_km(lat: float, lon: float) -> float:
    radius = 6371.0
    p1 = math.radians(CENTER_LAT)
    p2 = math.radians(lat)
    dp = math.radians(lat - CENTER_LAT)
    dl = math.radians(lon - CENTER_LON)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def convert(state: list[Any]) -> dict[str, Any] | None:
    if len(state) < 17 or state[5] is None or state[6] is None:
        return None
    altitude = state[7]
    velocity = state[9]
    vertical_rate = state[11]
    return {
        "icao24": state[0],
        "callsign": (state[1] or "BILINMIYOR").strip(),
        "country": state[2],
        "last_contact": state[4],
        "lon": state[5],
        "lat": state[6],
        "altitude_ft": round(altitude * 3.28084) if altitude is not None else None,
        "on_ground": bool(state[8]),
        "speed_kmh": round(velocity * 3.6, 1) if velocity is not None else None,
        "heading": round(state[10], 1) if state[10] is not None else None,
        "vertical_rate_fpm": round(vertical_rate * 196.8504) if vertical_rate is not None else None,
        "squawk": state[14],
        "position_source": state[16],
        "distance_km": round(distance_km(state[6], state[5]), 1),
    }


def run_once(session: requests.Session) -> None:
    source = session.get(OPENSKY_URL, timeout=TIMEOUT)
    source.raise_for_status()
    states = source.json().get("states") or []
    planes = [plane for state in states if (plane := convert(state)) is not None]
    planes.sort(key=lambda p: p["distance_km"])
    payload = {
        "source": "wpsd-zero2w",
        "station": {
            "name": "Izmir Adnan Menderes",
            "icao": "LTBJ",
            "iata": "ADB",
            "lat": CENTER_LAT,
            "lon": CENTER_LON,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "planes": planes,
    }
    result = session.post(API_URL, json=payload, timeout=TIMEOUT)
    result.raise_for_status()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(planes)} uçak gönderildi", flush=True)


def main() -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": "AirRadar-Pro-Pi/1.0"})
    print(f"AirRadar Pi Agent başladı: {API_URL}", flush=True)
    while RUNNING:
        started = time.monotonic()
        try:
            run_once(session)
        except requests.RequestException as error:
            print(f"Bağlantı hatası: {error}", flush=True)
        except (ValueError, TypeError, IndexError) as error:
            print(f"Veri hatası: {error}", flush=True)
        wait = max(1.0, INTERVAL - (time.monotonic() - started))
        end = time.monotonic() + wait
        while RUNNING and time.monotonic() < end:
            time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
