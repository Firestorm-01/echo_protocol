"""
DNS Heartbeat Trigger — Monitors for regular heartbeat pings from devices.
"""

import logging
from datetime import datetime
from typing import Optional, Dict

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class DNSHeartbeatTrigger(BaseTrigger):
    """
    Monitors for heartbeat pings from remote devices/servers.
    Config:
        devices:     Dict of device_id -> {name, last_ping, expected_interval}
        require_all: Whether all devices must be active (default: False)
    """

    def get_last_activity(self) -> Optional[datetime]:
        devices: dict = self.config.get("devices", {})
        require_all: bool = self.config.get("require_all", False)

        if not devices:
            return None

        latest_ping: Optional[datetime] = None
        all_active = True

        for device_info in devices.values():
            last_ping = device_info.get("last_ping")
            if last_ping:
                ping_time = datetime.fromisoformat(last_ping)
                expected_interval = device_info.get("expected_interval", 3600)
                elapsed = (datetime.utcnow() - ping_time).total_seconds()

                if elapsed > expected_interval * 2:
                    all_active = False

                if latest_ping is None or ping_time > latest_ping:
                    latest_ping = ping_time
            else:
                all_active = False

        if require_all and not all_active:
            # Return the oldest ping so the threshold fires based on the weakest link
            oldest_ping: Optional[datetime] = None
            for device_info in devices.values():
                last_ping = device_info.get("last_ping")
                if last_ping:
                    ping_time = datetime.fromisoformat(last_ping)
                    if oldest_ping is None or ping_time < oldest_ping:
                        oldest_ping = ping_time
            return oldest_ping

        return latest_ping

    def record_heartbeat(self, device_id: str) -> dict:
        """Record a heartbeat from a device; creates the entry if absent."""
        devices = self.config.get("devices", {})
        now = datetime.utcnow()

        if device_id not in devices:
            devices[device_id] = {
                "name": device_id,
                "expected_interval": 3600,
                "created_at": now.isoformat(),
            }

        devices[device_id]["last_ping"] = now.isoformat()
        devices[device_id]["ping_count"] = devices[device_id].get("ping_count", 0) + 1
        self.config["devices"] = devices

        return {
            "status": "recorded",
            "device_id": device_id,
            "timestamp": now.isoformat(),
            "ping_count": devices[device_id]["ping_count"],
        }

    def get_device_status(self) -> Dict:
        """Get status of all registered devices."""
        devices = self.config.get("devices", {})
        now = datetime.utcnow()
        status = {}

        for device_id, device_info in devices.items():
            last_ping = device_info.get("last_ping")
            if last_ping:
                ping_time = datetime.fromisoformat(last_ping)
                elapsed = (now - ping_time).total_seconds()
                expected = device_info.get("expected_interval", 3600)

                if elapsed <= expected:
                    device_status = "ok"
                elif elapsed <= expected * 2:
                    device_status = "warning"
                else:
                    device_status = "offline"
            else:
                device_status = "never_seen"

            status[device_id] = {
                "name": device_info.get("name", device_id),
                "status": device_status,
                "last_ping": last_ping,
                "expected_interval": device_info.get("expected_interval", 3600),
            }

        return status

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "require_all": {
                "type": "boolean",
                "description": "Require all registered devices to be active",
                "default": False,
            },
            "devices": {
                "type": "object",
                "description": "Registered devices (auto-populated)",
                "default": {},
            },
        }
