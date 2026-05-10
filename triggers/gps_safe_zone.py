"""
GPS Safe Zone Trigger — Monitors device location via API endpoint.
"""

import logging
import math
from datetime import datetime
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class GPSSafeZoneTrigger(BaseTrigger):
    """
    Monitors GPS location reported by mobile device.
    Config:
        safe_zones:    List of {lat, lon, radius_meters, name}
        last_lat:      Last reported latitude
        last_lon:      Last reported longitude
        last_gps_time: Last GPS report timestamp (ISO string)
    """

    def get_last_activity(self) -> Optional[datetime]:
        last_time = self.config.get("last_gps_time")
        if not last_time:
            return None

        last_lat = self.config.get("last_lat")
        last_lon = self.config.get("last_lon")

        if last_lat is None or last_lon is None:
            return datetime.fromisoformat(last_time)

        safe_zones = self.config.get("safe_zones", [])

        for zone in safe_zones:
            distance = self.haversine_distance(
                last_lat, last_lon, zone["lat"], zone["lon"]
            )
            if distance <= zone.get("radius_meters", 500):
                return datetime.fromisoformat(last_time)

        # Outside all safe zones — the countdown uses threshold from last_gps_time
        return None

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in metres."""
        R = 6_371_000  # Earth radius in metres

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def update_location(self, lat: float, lon: float) -> dict:
        """Called by the API when a device reports its location."""
        self.config["last_lat"] = lat
        self.config["last_lon"] = lon
        self.config["last_gps_time"] = datetime.utcnow().isoformat()

        safe_zones = self.config.get("safe_zones", [])
        in_safe_zone = False
        current_zone = None

        for zone in safe_zones:
            distance = self.haversine_distance(lat, lon, zone["lat"], zone["lon"])
            if distance <= zone.get("radius_meters", 500):
                in_safe_zone = True
                current_zone = zone.get("name", "Unknown")
                break

        return {
            "in_safe_zone": in_safe_zone,
            "current_zone": current_zone,
            "timestamp": self.config["last_gps_time"],
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "safe_zones": {
                "type": "array",
                "description": "List of safe zone locations",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "radius_meters": {"type": "number", "default": 500},
                    },
                },
                "required": True,
            }
        }
