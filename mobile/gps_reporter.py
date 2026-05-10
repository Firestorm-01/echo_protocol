#!/usr/bin/env python3
"""
GPS Reporter for mobile devices (Termux on Android).
Reports GPS location to the Echo Protocol server periodically.

Requirements (Termux):
    pkg install termux-api python
    pip install requests
"""

import json
import subprocess
import time
from typing import Optional, Tuple

import requests

ECHO_API_URL    = "http://your-server:5000"   # Change to your server address
TRIGGER_ID      = 2                            # Set to your gps_safe_zone trigger ID
REPORT_INTERVAL = 300                          # seconds between reports


def get_gps_location() -> Tuple[Optional[float], Optional[float]]:
    """Get GPS location using Termux API."""
    try:
        result = subprocess.run(
            ["termux-location", "-p", "gps", "-r", "once"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return data.get("latitude"), data.get("longitude")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"GPS error: {e}")
    return None, None


def report_location(lat: float, lon: float) -> bool:
    """Report location to the Echo Protocol server."""
    try:
        response = requests.post(
            f"{ECHO_API_URL}/api/triggers/{TRIGGER_ID}/activity",
            json={"lat": lat, "lon": lon},
            timeout=30,
        )
        return response.ok
    except requests.RequestException as e:
        print(f"Report error: {e}")
        return False


def main():
    print("Echo Protocol GPS Reporter")
    print(f"Reporting to {ECHO_API_URL} every {REPORT_INTERVAL}s")
    print("Press Ctrl+C to stop.\n")

    while True:
        lat, lon = get_gps_location()
        if lat is not None and lon is not None:
            success = report_location(lat, lon)
            mark = "✓" if success else "✗"
            print(f"{mark} Location: {lat:.6f}, {lon:.6f}")
        else:
            print("✗ Could not obtain GPS location")

        time.sleep(REPORT_INTERVAL)


if __name__ == "__main__":
    main()
