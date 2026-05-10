"""
Daily Streak Trigger — Simple daily check-in button.
"""

import logging
from datetime import datetime
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class DailyStreakTrigger(BaseTrigger):
    """
    Simple daily check-in tracking.
    Config:
        streak_count:    Current streak count
        last_checkin:    Last check-in timestamp (ISO string)
        checkin_history: List of recent check-in times
    """

    def get_last_activity(self) -> Optional[datetime]:
        last_checkin = self.config.get("last_checkin")
        if last_checkin:
            return datetime.fromisoformat(last_checkin)
        return None

    def checkin(self) -> dict:
        """Record a daily check-in. Returns streak info."""
        now = datetime.utcnow()
        last_checkin = self.config.get("last_checkin")
        streak = self.config.get("streak_count", 0)

        if last_checkin:
            last_time = datetime.fromisoformat(last_checkin)
            hours_since = (now - last_time).total_seconds() / 3600

            if hours_since < 20:
                return {
                    "status": "already_checked_in",
                    "streak": streak,
                    "last_checkin": last_checkin,
                    "message": "You've already checked in today!",
                }
            elif hours_since <= 48:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        self.config["streak_count"] = streak
        self.config["last_checkin"] = now.isoformat()

        history = self.config.get("checkin_history", [])
        history.append(now.isoformat())
        self.config["checkin_history"] = history[-30:]

        return {
            "status": "success",
            "streak": streak,
            "last_checkin": now.isoformat(),
            "message": f"Check-in recorded! Current streak: {streak} days",
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "streak_count": {
                "type": "integer",
                "description": "Current streak count",
                "default": 0,
            }
        }
