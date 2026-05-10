"""
Financial Stagnation Trigger — Monitors bank/crypto accounts for outbound activity.
"""

import logging
from datetime import datetime
from typing import Optional

import requests

from triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class FinancialStagnationTrigger(BaseTrigger):
    """
    Monitors financial accounts for outbound activity.
    Config:
        provider:                 'plaid', 'ethereum', 'bitcoin', or 'manual'
        plaid_access_token:       Plaid access token
        wallet_address:           Crypto wallet address
        etherscan_api_key:        Etherscan API key (Ethereum)
        last_outbound_transaction: Last recorded outbound transaction time
    """

    def get_last_activity(self) -> Optional[datetime]:
        provider = self.config.get("provider", "manual")

        if provider == "plaid":
            return self._check_plaid()
        elif provider == "ethereum":
            return self._check_ethereum()
        elif provider == "bitcoin":
            return self._check_bitcoin()
        else:
            last_tx = self.config.get("last_outbound_transaction")
            if last_tx:
                return datetime.fromisoformat(last_tx)
            return None

    def _check_ethereum(self) -> Optional[datetime]:
        """Check Ethereum wallet for outbound transactions via Etherscan."""
        address = self.config.get("wallet_address")
        if not address:
            return None

        try:
            api_key = self.config.get("etherscan_api_key", "")
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99_999_999,
                "sort": "desc",
                "apikey": api_key,
            }
            response = requests.get(
                "https://api.etherscan.io/api", params=params, timeout=30
            )
            data = response.json()

            if data.get("status") == "1" and data.get("result"):
                for tx in data["result"]:
                    if tx["from"].lower() == address.lower():
                        return datetime.utcfromtimestamp(int(tx["timeStamp"]))

            return None

        except Exception as e:
            logger.error(f"Ethereum check failed: {e}")
            return None

    def _check_bitcoin(self) -> Optional[datetime]:
        """Check Bitcoin wallet via Blockchain.info."""
        address = self.config.get("wallet_address")
        if not address:
            return None

        try:
            response = requests.get(
                f"https://blockchain.info/rawaddr/{address}", timeout=30
            )
            data = response.json()

            for tx in data.get("txs", []):
                for inp in tx.get("inputs", []):
                    prev_out = inp.get("prev_out", {})
                    if prev_out.get("addr") == address:
                        return datetime.utcfromtimestamp(tx["time"])

            return None

        except Exception as e:
            logger.error(f"Bitcoin check failed: {e}")
            return None

    def _check_plaid(self) -> Optional[datetime]:
        """Placeholder — Plaid requires additional setup."""
        logger.info("Plaid integration requires additional configuration")
        return None

    def record_transaction(self) -> dict:
        """Manually record an outbound transaction."""
        now = datetime.utcnow()
        self.config["last_outbound_transaction"] = now.isoformat()
        return {"status": "recorded", "timestamp": now.isoformat()}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "provider": {
                "type": "string",
                "enum": ["plaid", "ethereum", "bitcoin", "manual"],
                "default": "manual",
            },
            "wallet_address": {
                "type": "string",
                "description": "Crypto wallet address to monitor",
            },
            "etherscan_api_key": {
                "type": "string",
                "description": "Etherscan API key for Ethereum monitoring",
            },
        }
