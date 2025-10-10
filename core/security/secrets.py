"""
Secrets and API key management.
Handles secure storage and retrieval of sensitive credentials.
"""

from typing import Dict, Optional
from functools import lru_cache
import os
from pathlib import Path
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class SecretsManager:
    """Manages secure access to API keys and secrets"""

    def __init__(self) -> None:
        self._secrets: Dict[str, str] = {}
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from environment variables"""
        # OpenAI
        if settings.ai.openai_api_key:
            self._secrets["openai"] = settings.ai.openai_api_key

        # Exchange credentials
        if settings.exchange.binance_api_key:
            self._secrets["binance_key"] = settings.exchange.binance_api_key
            self._secrets["binance_secret"] = settings.exchange.binance_secret

        if settings.exchange.coinbase_api_key:
            self._secrets["coinbase_key"] = settings.exchange.coinbase_api_key
            self._secrets["coinbase_secret"] = settings.exchange.coinbase_secret

        if settings.exchange.kraken_api_key:
            self._secrets["kraken_key"] = settings.exchange.kraken_api_key
            self._secrets["kraken_secret"] = settings.exchange.kraken_secret

        # Database
        if settings.database.password:
            self._secrets["postgres_password"] = settings.database.password

        if settings.influxdb.token:
            self._secrets["influxdb_token"] = settings.influxdb.token

        # Messaging
        if settings.messaging.rabbitmq_password:
            self._secrets["rabbitmq_password"] = settings.messaging.rabbitmq_password

        logger.info("secrets_loaded", count=len(self._secrets))

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret by key"""
        secret = self._secrets.get(key, default)
        if secret is None:
            logger.warning("secret_not_found", key=key)
        return secret

    def get_exchange_credentials(self, exchange: str) -> Dict[str, str]:
        """Get API credentials for a specific exchange"""
        exchange = exchange.lower()
        credentials = {
            "apiKey": self.get_secret(f"{exchange}_key", ""),
            "secret": self.get_secret(f"{exchange}_secret", ""),
        }

        if not credentials["apiKey"] or not credentials["secret"]:
            logger.error(
                "missing_exchange_credentials",
                exchange=exchange,
                has_key=bool(credentials["apiKey"]),
                has_secret=bool(credentials["secret"]),
            )

        return credentials

    def validate_secrets(self) -> bool:
        """Validate that required secrets are present"""
        required = ["openai"]

        if settings.trading.mode == "live":
            # In live mode, require at least one exchange
            has_exchange = any(
                self.get_secret(f"{ex}_key")
                for ex in ["binance", "coinbase", "kraken"]
            )
            if not has_exchange:
                logger.error("no_exchange_credentials_in_live_mode")
                return False

        missing = [key for key in required if not self.get_secret(key)]

        if missing:
            logger.error("missing_required_secrets", secrets=missing)
            return False

        logger.info("secrets_validated", mode=settings.trading.mode)
        return True

    def mask_secret(self, secret: str, visible_chars: int = 4) -> str:
        """Mask a secret for logging purposes"""
        if not secret:
            return "****"
        if len(secret) <= visible_chars:
            return "****"
        return secret[:visible_chars] + "*" * (len(secret) - visible_chars)


@lru_cache(maxsize=1)
def get_secrets_manager() -> SecretsManager:
    """Get singleton secrets manager instance"""
    return SecretsManager()


# Convenience functions
def get_exchange_credentials(exchange: str) -> Dict[str, str]:
    """Get exchange credentials"""
    return get_secrets_manager().get_exchange_credentials(exchange)


def validate_secrets() -> bool:
    """Validate required secrets are present"""
    return get_secrets_manager().validate_secrets()
