"""
Social Media Silence Trigger — Monitors public social media for activity.
"""

import logging
from datetime import datetime
from typing import Optional

import requests

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class SocialMediaTrigger(BaseTrigger):
    """
    Monitors public social media profiles for activity.
    Config:
        platforms: List of {platform, username, [api_key]}
            Supported: 'github', 'reddit'
        last_activity: Most recent activity timestamp (ISO string)
    """

    def get_last_activity(self) -> Optional[datetime]:
        platforms = self.config.get("platforms", [])
        latest = None

        for platform_config in platforms:
            platform = platform_config.get("platform")
            username = platform_config.get("username")
            if not platform or not username:
                continue

            activity_time: Optional[datetime] = None

            if platform == "github":
                activity_time = self._check_github(username)
            elif platform == "reddit":
                activity_time = self._check_reddit(username)

            if activity_time and (latest is None or activity_time > latest):
                latest = activity_time

        if latest:
            self.config["last_activity"] = latest.isoformat()

        return latest

    def _check_github(self, username: str) -> Optional[datetime]:
        try:
            url = f"https://api.github.com/users/{username}/events/public"
            headers = {"Accept": "application/vnd.github.v3+json"}
            token = self.config.get("github_token")
            if token:
                headers["Authorization"] = f"token {token}"

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                events = response.json()
                if events:
                    created_at = events[0].get("created_at")
                    if created_at:
                        return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return None

        except Exception as e:
            logger.error(f"GitHub check failed: {e}")
            return None

    def _check_reddit(self, username: str) -> Optional[datetime]:
        try:
            url = f"https://www.reddit.com/user/{username}.json"
            headers = {"User-Agent": "EchoProtocol/1.0"}
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                if posts:
                    created_utc = posts[0].get("data", {}).get("created_utc")
                    if created_utc:
                        return datetime.utcfromtimestamp(created_utc)
            return None

        except Exception as e:
            logger.error(f"Reddit check failed: {e}")
            return None

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "platforms": {
                "type": "array",
                "description": "Social media platforms to monitor",
                "items": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": ["github", "reddit"]},
                        "username": {"type": "string"},
                    },
                },
                "required": True,
            }
        }
