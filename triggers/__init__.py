"""
Trigger registry — maps trigger type strings to handler classes.
"""

from triggers.base import BaseTrigger
from triggers.email_inactivity import EmailInactivityTrigger
from triggers.gps_safe_zone import GPSSafeZoneTrigger
from triggers.daily_streak import DailyStreakTrigger
from triggers.financial_stagnation import FinancialStagnationTrigger
from triggers.usb_token import USBTokenTrigger
from triggers.social_media import SocialMediaTrigger
from triggers.smart_home import SmartHomeTrigger
from triggers.calendar_checkin import CalendarCheckInTrigger
from triggers.dns_heartbeat import DNSHeartbeatTrigger
from triggers.browser_activity import BrowserActivityTrigger

TRIGGER_REGISTRY = {
    "email_inactivity": EmailInactivityTrigger,
    "gps_safe_zone": GPSSafeZoneTrigger,
    "daily_streak": DailyStreakTrigger,
    "financial_stagnation": FinancialStagnationTrigger,
    "usb_token": USBTokenTrigger,
    "social_media": SocialMediaTrigger,
    "smart_home": SmartHomeTrigger,
    "calendar_checkin": CalendarCheckInTrigger,
    "dns_heartbeat": DNSHeartbeatTrigger,
    "browser_activity": BrowserActivityTrigger,
}

__all__ = [
    "BaseTrigger",
    "TRIGGER_REGISTRY",
    "EmailInactivityTrigger",
    "GPSSafeZoneTrigger",
    "DailyStreakTrigger",
    "FinancialStagnationTrigger",
    "USBTokenTrigger",
    "SocialMediaTrigger",
    "SmartHomeTrigger",
    "CalendarCheckInTrigger",
    "DNSHeartbeatTrigger",
    "BrowserActivityTrigger",
]
