from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("AIRRADAR_DB", BASE_DIR / "data" / "airradar.db"))
FRONTEND_DIST = Path(os.getenv("AIRRADAR_FRONTEND", BASE_DIR.parent / "frontend" / "dist"))
ROUTE_BASE = "https://vrs-standing-data.adsb.lol/routes"
ROUTE_TTL = 6 * 60 * 60

app = Flask(__name__, static_folder=None)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS radar_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                updated_at TEXT,
                payload TEXT NOT NULL
            );
            INSERT OR IGNORE INTO radar_state(id, updated_at, payload)
            VALUES(1, NULL, '{"planes": []}');

            CREATE TABLE IF NOT EXISTS route_cache (
                callsign TEXT PRIMARY KEY,
                origin TEXT,
                destination TEXT,
                origin_name TEXT,
                destination_name TEXT,
                fetched_at INTEGER NOT NULL
            );
            """
        )


def load_state() -> dict[str, Any]:
    with db() as connection:
        row = connection.execute(
            "SELECT updated_at, payload FROM radar_state WHERE id = 1"
        ).fetchone()
    payload = json.loads(row["payload"]) if row else {"planes": []}
    payload["updated_at"] = row["updated_at"] if row else None
    return payload


def save_state(payload: dict[str, Any]) -> str:
    updated_at = datetime.now(timezone.utc).isoformat()
    with db() as connection:
        connection.execute(
            "UPDATE radar_state SET updated_at = ?, payload = ? WHERE id = 1",
            (updated_at, json.dumps(payload, ensure_ascii=False)),
        )
    return updated_at


def route_for(callsign: str) -> dict[str, str | None]:
    callsign = callsign.strip().upper()
    if not callsign or callsign == "BILINMIYOR":
        return {"origin": None, "destination": None}

    now = int(time.time())
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM route_cache WHERE callsign = ?", (callsign,)
        ).fetchone()
    if row and now - row["fetched_at"] < ROUTE_TTL:
        return dict(row)

    prefix = callsign[:2]
    url = f"{ROUTE_BASE}/{prefix}/{callsign}.json"
    route: dict[str, Any] = {
        "origin": None,
        "destination": None,
        "origin_name": None,
        "destination_name": None,
    }
    try:
        response = requests.get(url, timeout=6, headers={"User-Agent": "AirRadar-Pro/1.0"})
        if response.ok:
            data = response.json()
            airports = data.get("_airports") or []
            if len(airports) >= 2:
                route = {
                    "origin": airports[0].get("iata") or airports[0].get("icao"),
                    "destination": airports[1].get("iata") or airports[1].get("icao"),
                    "origin_name": airports[0].get("name"),
                    "destination_name": airports[1].get("name"),
                }
    except (requests.RequestException, ValueError):
        pass

    with db() as connection:
        connection.execute(
            """
            INSERT INTO route_cache(callsign, origin, destination, origin_name, destination_name, fetched_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(callsign) DO UPDATE SET
              origin=excluded.origin,
              destination=excluded.destination,
              origin_name=excluded.origin_name,
              destination_name=excluded.destination_name,
              fetched_at=excluded.fetched_at
            """,
            (
                callsign,
                route["origin"],
                route["destination"],
                route["origin_name"],
                route["destination_name"],
                now,
            ),
        )
    return route


@app.get("/health")
def health():
    state = load_state()
    return jsonify(
        status="online",
        service="AirRadar Pro",
        planes=len(state.get("planes", [])),
        updated_at=state.get("updated_at"),
    )


@app.post("/api/update")
def update():
    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload.get("planes"), list):
        return jsonify(ok=False, error="invalid payload"), 400
    updated_at = save_state(payload)
    return jsonify(ok=True, count=len(payload["planes"]), updated_at=updated_at)


@app.get("/api/planes")
def planes():
    state = load_state()
    enriched = []
    for plane in state.get("planes", []):
        item = dict(plane)
        item.update(route_for(str(item.get("callsign") or "")))
        enriched.append(item)
    state["planes"] = enriched
    return jsonify(state)


@app.get("/api/nearest")
def nearest():
    state = load_state()
    valid = [p for p in state.get("planes", []) if p.get("distance_km") is not None]
    plane = min(valid, key=lambda p: p["distance_km"]) if valid else None
    if plane:
        plane = dict(plane)
        plane.update(route_for(str(plane.get("callsign") or "")))
    return jsonify(updated_at=state.get("updated_at"), plane=plane)


@app.get("/api/statistics")
def statistics():
    planes_data = load_state().get("planes", [])
    airborne = sum(not p.get("on_ground", False) for p in planes_data)
    ground = len(planes_data) - airborne
    nearest_plane = min(
        (p for p in planes_data if p.get("distance_km") is not None),
        key=lambda p: p["distance_km"],
        default=None,
    )
    return jsonify(total=len(planes_data), airborne=airborne, ground=ground, nearest=nearest_plane)


@app.get("/")
def index():
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify(message="AirRadar Pro API", frontend="not built")


@app.get("/<path:path>")
def frontend(path: str):
    candidate = FRONTEND_DIST / path
    if candidate.exists() and candidate.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
