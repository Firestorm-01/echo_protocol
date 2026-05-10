"""
Email Inactivity Trigger — Monitors email account for activity via Gmail API.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class EmailInactivityTrigger(BaseTrigger):
    """
    Monitors Gmail account for recent sent emails.
    Config:
        credentials_path: Path to OAuth credentials JSON
        token_path:       Path to store/load token
    """

    def get_last_activity(self) -> Optional[datetime]:
        creds = self._get_credentials()
        if not creds:
            logger.error("Could not obtain Gmail credentials")
            return None

        try:
            from googleapiclient.discovery import build

            service = build("gmail", "v1", credentials=creds)

            results = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["SENT"], maxResults=1)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return None

            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=messages[0]["id"],
                    format="metadata",
                    metadataHeaders=["Date"],
                )
                .execute()
            )

            headers = msg.get("payload", {}).get("headers", [])
            for header in headers:
                if header["name"].lower() == "date":
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(header["value"])

            return None

        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return None

    def _get_credentials(self):
        """Get valid Gmail API credentials."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
        except ImportError:
            logger.error("Google API packages not installed")
            return None

        token_path = self.config.get("token_path", "token.json")
        credentials_path = self.config.get("credentials_path", "credentials.json")

        creds = None

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists(credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None

            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "credentials_path": {
                "type": "string",
                "description": "Path to Google OAuth credentials JSON file",
                "required": True,
            },
            "token_path": {
                "type": "string",
                "description": "Path to store OAuth token",
                "default": "token.json",
            },
        }
