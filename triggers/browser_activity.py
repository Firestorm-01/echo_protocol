"""
Browser Activity Trigger — Receives activity reports from browser extension.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class BrowserActivityTrigger(BaseTrigger):
    """
    Receives and monitors browser activity from the companion extension.
    Config:
        last_activity:  Last reported browser activity (ISO string)
        daily_history:  Dict of date -> active_minutes
    """

    def get_last_activity(self) -> Optional[datetime]:
        last_activity = self.config.get("last_activity")
        if last_activity:
            return datetime.fromisoformat(last_activity)
        return None

    def report_activity(self, active_minutes: int = 1) -> dict:
        """Called by the browser extension to report activity."""
        now = datetime.utcnow()
        today = now.date().isoformat()

        self.config["last_activity"] = now.isoformat()

        daily_history: dict = self.config.get("daily_history", {})
        daily_history[today] = daily_history.get(today, 0) + active_minutes

        # Keep only last 30 days
        cutoff = (now - timedelta(days=30)).date().isoformat()
        daily_history = {k: v for k, v in daily_history.items() if k >= cutoff}
        self.config["daily_history"] = daily_history

        return {
            "status": "recorded",
            "timestamp": now.isoformat(),
            "active_minutes_today": daily_history[today],
        }

    def get_activity_summary(self) -> dict:
        """Get a summary of browser activity."""
        now = datetime.utcnow()
        daily_history: dict = self.config.get("daily_history", {})

        today = now.date().isoformat()
        yesterday = (now - timedelta(days=1)).date().isoformat()
        week_ago = (now - timedelta(days=7)).date().isoformat()

        week_total = sum(v for k, v in daily_history.items() if k >= week_ago)

        return {
            "today_minutes": daily_history.get(today, 0),
            "yesterday_minutes": daily_history.get(yesterday, 0),
            "week_total_minutes": week_total,
            "week_average_minutes": week_total / 7,
            "last_activity": self.config.get("last_activity"),
            "days_tracked": len(daily_history),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "last_activity": {
                "type": "string",
                "description": "Last browser activity timestamp",
            },
            "daily_history": {
                "type": "object",
                "description": "Daily active minutes history",
            },
        }
