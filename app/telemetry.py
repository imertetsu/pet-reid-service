"""Simulated collar telemetry (GNSS position + battery), modeled after the
``Device`` / ``Location`` entities of the Pets Location thesis.

Everything here is fictitious: positions are random points around a park in
Cochabamba (same area as the thesis seed data).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

BASE_LAT, BASE_LON = -17.3935, -66.1570
SPREAD_DEG = 0.02  # about 2 km


class Telemetry:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self._last: dict[str, dict] = {}

    def register(self, device_id: str) -> None:
        if device_id in self._last:
            return
        minutes_ago = self._rng.randint(2, 180)
        self._last[device_id] = {
            "device_id": device_id,
            "latitude": round(BASE_LAT + self._rng.uniform(-SPREAD_DEG, SPREAD_DEG), 5),
            "longitude": round(BASE_LON + self._rng.uniform(-SPREAD_DEG, SPREAD_DEG), 5),
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(),
            "battery": self._rng.randint(35, 100),
            "network": self._rng.choice(["LTE-M", "NB-IoT"]),
            "simulated": True,
        }

    def last(self, device_id: str) -> dict | None:
        return self._last.get(device_id)

    def ping(self, device_id: str) -> dict:
        """Simulate a new signal: small movement, battery drain, current time."""
        if device_id not in self._last:
            raise KeyError(device_id)
        current = dict(self._last[device_id])
        current["latitude"] = round(current["latitude"] + self._rng.uniform(-0.0015, 0.0015), 5)
        current["longitude"] = round(current["longitude"] + self._rng.uniform(-0.0015, 0.0015), 5)
        current["battery"] = max(1, current["battery"] - self._rng.randint(0, 3))
        current["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._last[device_id] = current
        return current

    def remove(self, device_id: str) -> None:
        self._last.pop(device_id, None)
