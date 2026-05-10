"""
USB Token Trigger — Monitors for presence of a specific USB device.
"""

import logging
import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class USBTokenTrigger(BaseTrigger):
    """
    Monitors for presence of a specific USB device.
    Config:
        mount_path:        Expected mount path (e.g. /media/user/ECHOKEY)
        verification_file: File to check on the device
        verification_hash: Expected SHA-256 hash of that file
        last_seen:         Last time device was detected (ISO string)
    """

    def get_last_activity(self) -> Optional[datetime]:
        if self._verify_device_present():
            now = datetime.utcnow()
            self.config["last_seen"] = now.isoformat()
            return now

        last_seen = self.config.get("last_seen")
        if last_seen:
            return datetime.fromisoformat(last_seen)
        return None

    def _verify_device_present(self) -> bool:
        mount_path = self.config.get("mount_path")
        if not mount_path or not os.path.exists(mount_path):
            return False

        verification_file = self.config.get("verification_file")
        if verification_file:
            filepath = os.path.join(mount_path, verification_file)
            if not os.path.exists(filepath):
                return False

            expected_hash = self.config.get("verification_hash")
            if expected_hash:
                actual_hash = self._hash_file(filepath)
                if actual_hash != expected_hash:
                    logger.warning("USB token file hash mismatch!")
                    return False

        return True

    @staticmethod
    def _hash_file(filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def generate_verification_file(self) -> dict:
        """Generate a unique verification file during initial setup."""
        mount_path = self.config.get("mount_path")
        if not mount_path or not os.path.exists(mount_path):
            return {"error": "Mount path not found"}

        token = secrets.token_bytes(64)
        verification_file = ".echotoken"
        filepath = os.path.join(mount_path, verification_file)

        with open(filepath, "wb") as f:
            f.write(token)

        file_hash = self._hash_file(filepath)
        self.config["verification_file"] = verification_file
        self.config["verification_hash"] = file_hash

        return {"status": "created", "file": verification_file, "hash": file_hash}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "mount_path": {
                "type": "string",
                "description": "Expected mount path of USB device",
                "required": True,
            },
            "verification_file": {
                "type": "string",
                "description": "File to verify on device",
            },
            "verification_hash": {
                "type": "string",
                "description": "Expected SHA-256 hash of verification file",
            },
        }
