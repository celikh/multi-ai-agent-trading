"""
InfluxDB time-series database for market data storage.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class InfluxDBManager:
    """InfluxDB manager for time-series market data"""

    def __init__(self) -> None:
        self._client: Optional[InfluxDBClient] = None
        self._write_api = None
        self._query_api = None

    def connect(self) -> None:
        """Initialize InfluxDB client"""
        try:
            self._client = InfluxDBClient(
                url=settings.influxdb.url,
                token=settings.influxdb.token,
                org=settings.influxdb.org,
            )
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._query_api = self._client.query_api()

            # Test connection
            health = self._client.health()
            logger.info(
                "influxdb_connected",
                url=settings.influxdb.url,
                org=settings.influxdb.org,
                status=health.status,
            )
        except Exception as e:
            logger.error("influxdb_connection_failed", error=str(e))
            raise

    def disconnect(self) -> None:
        """Close InfluxDB client"""
        if self._client:
            self._client.close()
            logger.info("influxdb_disconnected")

    def write_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        interval: str = "1m",
    ) -> None:
        """Write OHLCV candle data"""
        point = (
            Point("ohlcv")
            .tag("symbol", symbol)
            .tag("exchange", exchange)
            .tag("interval", interval)
            .field("open", open_price)
            .field("high", high)
            .field("low", low)
            .field("close", close)
            .field("volume", volume)
            .time(timestamp, WritePrecision.MS)
        )

        self._write_api.write(
            bucket=settings.influxdb.bucket,
            org=settings.influxdb.org,
            record=point,
        )

    def write_indicator(
        self,
        symbol: str,
        indicator_name: str,
        value: float,
        timestamp: datetime,
        **tags: str,
    ) -> None:
        """Write technical indicator value"""
        point = (
            Point("indicator")
            .tag("symbol", symbol)
            .tag("name", indicator_name)
        )

        # Add custom tags
        for key, val in tags.items():
            point = point.tag(key, val)

        point = point.field("value", value).time(timestamp, WritePrecision.MS)

        self._write_api.write(
            bucket=settings.influxdb.bucket,
            org=settings.influxdb.org,
            record=point,
        )

    def write_orderbook(
        self,
        symbol: str,
        exchange: str,
        timestamp: datetime,
        bid_price: float,
        bid_volume: float,
        ask_price: float,
        ask_volume: float,
        spread: float,
    ) -> None:
        """Write order book data"""
        point = (
            Point("orderbook")
            .tag("symbol", symbol)
            .tag("exchange", exchange)
            .field("bid_price", bid_price)
            .field("bid_volume", bid_volume)
            .field("ask_price", ask_price)
            .field("ask_volume", ask_volume)
            .field("spread", spread)
            .time(timestamp, WritePrecision.MS)
        )

        self._write_api.write(
            bucket=settings.influxdb.bucket,
            org=settings.influxdb.org,
            record=point,
        )

    def query_ohlcv(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "1m",
    ) -> List[Dict[str, Any]]:
        """Query OHLCV data"""
        end_time = end_time or datetime.utcnow()

        query = f'''
        from(bucket: "{settings.influxdb.bucket}")
            |> range(
                start: {start_time.isoformat()}Z,
                stop: {end_time.isoformat()}Z
            )
            |> filter(fn: (r) => r["_measurement"] == "ohlcv")
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["exchange"] == "{exchange}")
            |> filter(fn: (r) => r["interval"] == "{interval}")
            |> pivot(
                rowKey:["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
        '''

        result = self._query_api.query(org=settings.influxdb.org, query=query)

        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "timestamp": record.get_time(),
                    "symbol": record.values.get("symbol"),
                    "exchange": record.values.get("exchange"),
                    "open": record.values.get("open"),
                    "high": record.values.get("high"),
                    "low": record.values.get("low"),
                    "close": record.values.get("close"),
                    "volume": record.values.get("volume"),
                })

        return data

    def query_indicators(
        self,
        symbol: str,
        indicator_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Query indicator values"""
        end_time = end_time or datetime.utcnow()

        query = f'''
        from(bucket: "{settings.influxdb.bucket}")
            |> range(
                start: {start_time.isoformat()}Z,
                stop: {end_time.isoformat()}Z
            )
            |> filter(fn: (r) => r["_measurement"] == "indicator")
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["name"] == "{indicator_name}")
        '''

        result = self._query_api.query(org=settings.influxdb.org, query=query)

        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "timestamp": record.get_time(),
                    "symbol": record.values.get("symbol"),
                    "indicator": record.values.get("name"),
                    "value": record.get_value(),
                })

        return data

    def get_latest_price(self, symbol: str, exchange: str) -> Optional[float]:
        """Get the latest close price for a symbol"""
        query = f'''
        from(bucket: "{settings.influxdb.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "ohlcv")
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["exchange"] == "{exchange}")
            |> filter(fn: (r) => r["_field"] == "close")
            |> last()
        '''

        result = self._query_api.query(org=settings.influxdb.org, query=query)

        for table in result:
            for record in table.records:
                return record.get_value()

        return None

    async def query(self, flux_query: str) -> List[Dict[str, Any]]:
        """
        Execute a Flux query and return results as list of dicts.
        Wrapper for async compatibility with agents.
        """
        if not self._query_api:
            raise RuntimeError("InfluxDB not connected. Call connect() first.")

        result = self._query_api.query(org=settings.influxdb.org, query=flux_query)

        data = []
        for table in result:
            for record in table.records:
                row = {"_time": record.get_time()}
                # Add all fields and tags
                for key, value in record.values.items():
                    if not key.startswith("_") or key == "_value":
                        row[key] = value
                data.append(row)

        return data


# Global InfluxDB instance
influx_db = InfluxDBManager()


def get_influx() -> InfluxDBManager:
    """Get InfluxDB instance"""
    if not influx_db._client:
        influx_db.connect()
    return influx_db
