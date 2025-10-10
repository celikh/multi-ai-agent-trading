"""
Core configuration management using Pydantic settings.
Loads from environment variables with validation.
"""

from typing import Literal
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration"""

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="trading_db", alias="POSTGRES_DB")
    user: str = Field(default="trading_user", alias="POSTGRES_USER")
    password: str = Field(default="", alias="POSTGRES_PASSWORD")

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class InfluxDBSettings(BaseSettings):
    """InfluxDB time-series database configuration"""

    url: str = Field(default="http://localhost:8086", alias="INFLUXDB_URL")
    token: str = Field(default="", alias="INFLUXDB_TOKEN")
    org: str = Field(default="trading-org", alias="INFLUXDB_ORG")
    bucket: str = Field(default="market-data", alias="INFLUXDB_BUCKET")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MessagingSettings(BaseSettings):
    """Message broker configuration (RabbitMQ/Kafka)"""

    # RabbitMQ
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="trading", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="", alias="RABBITMQ_PASSWORD")

    # Kafka (future)
    kafka_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ExchangeSettings(BaseSettings):
    """Exchange API credentials"""

    # Binance
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_secret: str = Field(default="", alias="BINANCE_SECRET_KEY")

    # Coinbase
    coinbase_api_key: str = Field(default="", alias="COINBASE_API_KEY")
    coinbase_secret: str = Field(default="", alias="COINBASE_SECRET_KEY")

    # Kraken
    kraken_api_key: str = Field(default="", alias="KRAKEN_API_KEY")
    kraken_secret: str = Field(default="", alias="KRAKEN_SECRET_KEY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class TradingSettings(BaseSettings):
    """Trading and risk parameters"""

    mode: Literal["paper", "live"] = Field(default="paper", alias="TRADING_MODE")
    max_position_size_pct: float = Field(default=2.0, alias="MAX_POSITION_SIZE_PCT")
    max_daily_loss_pct: float = Field(default=4.0, alias="MAX_DAILY_LOSS_PCT")
    default_leverage: float = Field(default=1.0, alias="DEFAULT_LEVERAGE")

    # Risk parameters
    stop_loss_pct: float = Field(default=2.0, alias="STOP_LOSS_PCT")
    take_profit_pct: float = Field(default=5.0, alias="TAKE_PROFIT_PCT")
    var_confidence: float = Field(default=0.95, alias="VAR_CONFIDENCE")

    @validator("max_position_size_pct", "max_daily_loss_pct")
    def validate_percentage(cls, v: float) -> float:
        if not 0 < v <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    @validator("var_confidence")
    def validate_confidence(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("VaR confidence must be between 0 and 1")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AISettings(BaseSettings):
    """AI and LLM configuration"""

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration"""

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: Literal["json", "text"] = Field(default="json", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability"""

    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    grafana_port: int = Field(default=3000, alias="GRAFANA_PORT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    """Main application settings"""

    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    influxdb: InfluxDBSettings = InfluxDBSettings()
    messaging: MessagingSettings = MessagingSettings()
    exchange: ExchangeSettings = ExchangeSettings()
    trading: TradingSettings = TradingSettings()
    ai: AISettings = AISettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Global settings instance
settings = Settings()
