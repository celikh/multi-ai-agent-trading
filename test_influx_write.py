#!/usr/bin/env python3
"""Test InfluxDB write"""

from datetime import datetime
from infrastructure.database.influxdb import get_influx

def test_influx():
    influx = get_influx()

    print("Testing InfluxDB write...")

    # Write test data
    influx.write_ohlcv(
        symbol="BTC/USDT",
        exchange="binance",
        timestamp=datetime.utcnow(),
        open_price=121000.0,
        high=121500.0,
        low=120500.0,
        close=121200.0,
        volume=1000.0,
        interval="1m",
    )

    print("✅ Data written successfully!")

    # Query back
    from influxdb_client import InfluxDBClient
    client = InfluxDBClient(
        url="http://localhost:8086",
        token="trading_token_2024",
        org="trading_org"
    )

    query = '''
    from(bucket: "trading_data")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "ohlcv")
      |> limit(n: 10)
    '''

    result = client.query_api().query(query)

    print(f"\nQuery result: {len(result)} tables")
    for table in result:
        print(f"Table: {len(table.records)} records")
        for record in table.records[:5]:
            print(f"  {record.get_time()}: {record.get_field()}={record.get_value()}")

    client.close()
    influx.disconnect()

if __name__ == "__main__":
    test_influx()
