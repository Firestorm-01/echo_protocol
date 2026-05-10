"""
Calendar Check-In Trigger — Uses calendar events as check-in mechanism.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class CalendarCheckInTrigger(BaseTrigger):
    """
    Monitors calendar for recurring check-in events.
    Config:
        provider:      'google' or 'manual'
        calendar_id:   Google Calendar ID (default: 'primary')
        event_keyword: Keyword to identify check-in events (e.g. 'ECHO_CHECKIN')
        token_path:    OAuth token path for Google Calendar
        last_completed: Last completed check-in (ISO string)
    """

    def get_last_activity(self) -> Optional[datetime]:
        provider = self.config.get("provider", "manual")

        if provider == "google":
            return self._check_google_calendar()

        last_completed = self.config.get("last_completed")
        if last_completed:
            return datetime.fromisoformat(last_completed)
        return None

    def _check_google_calendar(self) -> Optional[datetime]:
        try:
            import os
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_path = self.config.get("token_path", "calendar_token.json")
            if not os.path.exists(token_path):
                return None

            creds = Credentials.from_authorized_user_file(
                token_path,
                ["https://www.googleapis.com/auth/calendar.readonly"],
            )
            service = build("calendar", "v3", credentials=creds)

            calendar_id = self.config.get("calendar_id", "primary")
            keyword = self.config.get("event_keyword", "ECHO_CHECKIN")

            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=week_ago.isoformat() + "Z",
                    timeMax=now.isoformat() + "Z",
                    q=keyword,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            for event in reversed(events):
                if event.get("status") == "confirmed":
                    start = event.get("start", {})
                    start_time = start.get("dateTime", start.get("date"))
                    if start_time:
                        return datetime.fromisoformat(start_time.replace("Z", "+00:00"))

            return None

        except Exception as e:
            logger.error(f"Google Calendar check failed: {e}")
            return None

    def complete_checkin(self) -> dict:
        """Manually complete a check-in."""
        now = datetime.utcnow()
        self.config["last_completed"] = now.isoformat()

        history = self.config.get("checkin_history", [])
        history.append(now.isoformat())
        self.config["checkin_history"] = history[-10:]

        return {"status": "completed", "timestamp": now.isoformat()}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "provider": {
                "type": "string",
                "enum": ["google", "manual"],
                "default": "manual",
            },
            "event_keyword": {
                "type": "string",
                "description": "Keyword to identify check-in events",
                "default": "ECHO_CHECKIN",
            },
        }
