"""
Echo Protocol Configuration
All sensitive values should be set via environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/echo.db")

# Encryption key for sensitive data (generate with: Fernet.generate_key())
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# M-of-N consensus configuration
# Switch fires only if M triggers fail out of N active triggers
CONSENSUS_M = int(os.getenv("CONSENSUS_M", "3"))

# Check interval in seconds
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # 5 minutes

# Grace period multiplier (extra time before firing)
GRACE_PERIOD_MULTIPLIER = float(os.getenv("GRACE_PERIOD_MULTIPLIER", "1.5"))

# Notification settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5000"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY", os.urandom(32).hex())

# Trigger-specific defaults (in seconds)
TRIGGER_DEFAULTS = {
    "email_inactivity": {
        "threshold_seconds": 90 * 24 * 3600,   # 90 days
    },
    "gps_safe_zone": {
        "threshold_seconds": 24 * 3600,          # 24 hours
        "safe_zone_radius_meters": 500,
    },
    "daily_streak": {
        "threshold_seconds": 3 * 24 * 3600,      # 3 days missed
    },
    "financial_stagnation": {
        "threshold_seconds": 30 * 24 * 3600,     # 30 days
    },
    "usb_token": {
        "threshold_seconds": 7 * 24 * 3600,      # 7 days
    },
    "social_media": {
        "threshold_seconds": 30 * 24 * 3600,     # 30 days
    },
    "smart_home": {
        "threshold_seconds": 48 * 3600,           # 48 hours
    },
    "calendar_checkin": {
        "threshold_seconds": 7 * 24 * 3600,      # Weekly check
    },
    "dns_heartbeat": {
        "threshold_seconds": 24 * 3600,           # 24 hours
    },
    "browser_activity": {
        "threshold_seconds": 7 * 24 * 3600,      # 7 days
    },
}
