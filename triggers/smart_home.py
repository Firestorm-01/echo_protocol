"""
Smart Home Heartbeat Trigger — Monitors home automation sensors.
"""

import logging
from datetime import datetime
from typing import Optional

import requests

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class SmartHomeTrigger(BaseTrigger):
    """
    Monitors smart home sensors for activity.
    Config:
        provider:              'homeassistant' or 'webhook'
        homeassistant_url:     Home Assistant API URL
        homeassistant_token:   Long-lived access token
        entity_ids:            List of entity IDs to monitor
        webhook_url:           Custom webhook returning {last_activity: ISO}
        last_motion:           Last detected motion timestamp (ISO string)
    """

    def get_last_activity(self) -> Optional[datetime]:
        provider = self.config.get("provider", "webhook")

        if provider == "homeassistant":
            return self._check_home_assistant()
        elif provider == "webhook":
            return self._check_webhook()
        else:
            last_motion = self.config.get("last_motion")
            if last_motion:
                return datetime.fromisoformat(last_motion)
            return None

    def _check_home_assistant(self) -> Optional[datetime]:
        base_url = self.config.get("homeassistant_url")
        token = self.config.get("homeassistant_token")
        entity_ids = self.config.get("entity_ids", [])

        if not base_url or not token or not entity_ids:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        latest = None

        try:
            for entity_id in entity_ids:
                url = f"{base_url}/api/states/{entity_id}"
                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    state = response.json()
                    last_changed = state.get("last_changed")
                    if last_changed:
                        changed_time = datetime.fromisoformat(
                            last_changed.replace("Z", "+00:00")
                        )
                        if "motion" in entity_id.lower() or "occupancy" in entity_id.lower():
                            if state.get("state") in ("on", "detected", "true", "1"):
                                if latest is None or changed_time > latest:
                                    latest = changed_time
                        else:
                            if latest is None or changed_time > latest:
                                latest = changed_time

            if latest:
                self.config["last_motion"] = latest.isoformat()

            return latest

        except Exception as e:
            logger.error(f"Home Assistant check failed: {e}")
            return None

    def _check_webhook(self) -> Optional[datetime]:
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            return None

        try:
            response = requests.get(webhook_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                last_activity = data.get("last_activity")
                if last_activity:
                    return datetime.fromisoformat(last_activity)
            return None

        except Exception as e:
            logger.error(f"Webhook check failed: {e}")
            return None

    def report_motion(self) -> dict:
        """Manually report motion (for webhook / manual mode)."""
        now = datetime.utcnow()
        self.config["last_motion"] = now.isoformat()
        return {"status": "recorded", "timestamp": now.isoformat()}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "provider": {
                "type": "string",
                "enum": ["homeassistant", "webhook"],
                "default": "webhook",
            },
            "homeassistant_url": {
                "type": "string",
                "description": "Home Assistant API URL (e.g. http://homeassistant.local:8123)",
            },
            "homeassistant_token": {
                "type": "string",
                "description": "Home Assistant long-lived access token",
            },
            "entity_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entity IDs to monitor",
            },
        }
