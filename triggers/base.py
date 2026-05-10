"""
Base class for all trigger handlers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from core.database import Trigger


class BaseTrigger(ABC):
    """Base class for trigger handlers."""

    def __init__(self, trigger: Trigger):
        self.trigger = trigger
        self.config: dict = dict(trigger.config) if trigger.config else {}

    @abstractmethod
    def get_last_activity(self) -> Optional[datetime]:
        """
        Check for activity and return the timestamp of the last detected activity.
        Returns None if unable to check or no activity detected.
        """
        pass

    def validate_config(self) -> bool:
        """Validate that required configuration is present."""
        return True

    @classmethod
    def get_config_schema(cls) -> dict:
        """Return the configuration schema for this trigger type."""
        return {}
