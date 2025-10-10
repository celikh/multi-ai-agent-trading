"""
Technical Indicators Module
Wrapper around TA-Lib for calculating technical indicators.
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️  TA-Lib not installed. Install with: pip install TA-Lib")

from core.logging.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators using TA-Lib"""

    def __init__(self):
        if not TALIB_AVAILABLE:
            raise ImportError("TA-Lib is required. Install with: pip install TA-Lib")

    @staticmethod
    def calculate_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate RSI (Relative Strength Index)

        Returns: Array of RSI values (0-100)
        """
        return talib.RSI(close, timeperiod=period)

    @staticmethod
    def calculate_macd(
        close: np.ndarray,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Returns: (macd, signal, histogram)
        """
        macd, signal, hist = talib.MACD(
            close,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        return macd, signal, hist

    @staticmethod
    def calculate_bollinger_bands(
        close: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate Bollinger Bands

        Returns: (upper_band, middle_band, lower_band)
        """
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev,
        )
        return upper, middle, lower

    @staticmethod
    def calculate_ema(close: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        return talib.EMA(close, timeperiod=period)

    @staticmethod
    def calculate_sma(close: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate Simple Moving Average"""
        return talib.SMA(close, timeperiod=period)

    @staticmethod
    def calculate_stochastic(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        fastk_period: int = 14,
        slowk_period: int = 3,
        slowd_period: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Stochastic Oscillator

        Returns: (slowk, slowd)
        """
        slowk, slowd = talib.STOCH(
            high,
            low,
            close,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period,
        )
        return slowk, slowd

    @staticmethod
    def calculate_atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """Calculate Average True Range (volatility indicator)"""
        return talib.ATR(high, low, close, timeperiod=period)

    @staticmethod
    def calculate_adx(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """Calculate Average Directional Index (trend strength)"""
        return talib.ADX(high, low, close, timeperiod=period)

    @staticmethod
    def calculate_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calculate On-Balance Volume"""
        return talib.OBV(close, volume)

    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Calculate all indicators for a DataFrame with OHLCV data

        Args:
            df: DataFrame with columns: open, high, low, close, volume

        Returns:
            Dictionary with all calculated indicators
        """
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        open_price = df["open"].values
        volume = df["volume"].values

        indicators = {}

        try:
            # Trend Indicators
            indicators["sma_20"] = talib.SMA(close, timeperiod=20)
            indicators["sma_50"] = talib.SMA(close, timeperiod=50)
            indicators["sma_200"] = talib.SMA(close, timeperiod=200)
            indicators["ema_20"] = talib.EMA(close, timeperiod=20)
            indicators["ema_50"] = talib.EMA(close, timeperiod=50)

            # Momentum Indicators
            indicators["rsi"] = talib.RSI(close, timeperiod=14)
            macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            indicators["macd"] = macd
            indicators["macd_signal"] = signal
            indicators["macd_hist"] = hist

            # Volatility Indicators
            upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            indicators["bb_upper"] = upper
            indicators["bb_middle"] = middle
            indicators["bb_lower"] = lower
            indicators["atr"] = talib.ATR(high, low, close, timeperiod=14)

            # Volume Indicators
            indicators["obv"] = talib.OBV(close, volume)

            # Oscillators
            slowk, slowd = talib.STOCH(
                high, low, close,
                fastk_period=14,
                slowk_period=3,
                slowd_period=3
            )
            indicators["stoch_k"] = slowk
            indicators["stoch_d"] = slowd

            # Trend Strength
            indicators["adx"] = talib.ADX(high, low, close, timeperiod=14)

            logger.debug("calculated_all_indicators", count=len(indicators))

        except Exception as e:
            logger.error("indicator_calculation_failed", error=str(e))
            raise

        return indicators

    @staticmethod
    def get_latest_values(indicators: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Get the latest (most recent) value from each indicator array

        Args:
            indicators: Dictionary of indicator arrays

        Returns:
            Dictionary with latest values
        """
        latest = {}

        for key, values in indicators.items():
            if len(values) > 0 and not np.isnan(values[-1]):
                latest[key] = float(values[-1])
            else:
                latest[key] = None

        return latest


class SignalGenerator:
    """Generate trading signals based on technical indicators"""

    @staticmethod
    def analyze_rsi(rsi: float) -> Dict[str, Any]:
        """
        Analyze RSI for trading signals

        RSI < 30: Oversold (BUY signal)
        RSI > 70: Overbought (SELL signal)
        30 < RSI < 70: Neutral (HOLD)
        """
        if rsi is None:
            return {"signal": "HOLD", "strength": 0.0, "reason": "RSI not available"}

        if rsi < 30:
            strength = (30 - rsi) / 30  # Stronger signal as RSI gets lower
            return {
                "signal": "BUY",
                "strength": min(strength, 1.0),
                "reason": f"RSI oversold at {rsi:.2f}",
            }
        elif rsi > 70:
            strength = (rsi - 70) / 30  # Stronger signal as RSI gets higher
            return {
                "signal": "SELL",
                "strength": min(strength, 1.0),
                "reason": f"RSI overbought at {rsi:.2f}",
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0.0,
                "reason": f"RSI neutral at {rsi:.2f}",
            }

    @staticmethod
    def analyze_macd(macd: float, signal: float, hist: float) -> Dict[str, Any]:
        """
        Analyze MACD for trading signals

        MACD crosses above signal: BUY
        MACD crosses below signal: SELL
        """
        if macd is None or signal is None:
            return {"signal": "HOLD", "strength": 0.0, "reason": "MACD not available"}

        diff = macd - signal

        if diff > 0 and hist > 0:
            strength = min(abs(hist) / 10, 1.0)  # Normalize histogram
            return {
                "signal": "BUY",
                "strength": strength,
                "reason": f"MACD bullish crossover (hist: {hist:.4f})",
            }
        elif diff < 0 and hist < 0:
            strength = min(abs(hist) / 10, 1.0)
            return {
                "signal": "SELL",
                "strength": strength,
                "reason": f"MACD bearish crossover (hist: {hist:.4f})",
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0.0,
                "reason": "MACD no clear signal",
            }

    @staticmethod
    def analyze_bollinger_bands(
        close: float,
        upper: float,
        lower: float,
        middle: float,
    ) -> Dict[str, Any]:
        """
        Analyze Bollinger Bands for trading signals

        Price touches lower band: BUY (oversold)
        Price touches upper band: SELL (overbought)
        """
        if any(v is None for v in [close, upper, lower, middle]):
            return {"signal": "HOLD", "strength": 0.0, "reason": "BB not available"}

        band_width = upper - lower

        if close <= lower:
            strength = min((lower - close) / band_width * 2, 1.0)
            return {
                "signal": "BUY",
                "strength": strength,
                "reason": f"Price at lower BB ({close:.2f} <= {lower:.2f})",
            }
        elif close >= upper:
            strength = min((close - upper) / band_width * 2, 1.0)
            return {
                "signal": "SELL",
                "strength": strength,
                "reason": f"Price at upper BB ({close:.2f} >= {upper:.2f})",
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0.0,
                "reason": "Price within BB range",
            }

    @staticmethod
    def analyze_moving_averages(
        close: float,
        sma_20: float,
        sma_50: float,
        ema_20: float,
    ) -> Dict[str, Any]:
        """
        Analyze Moving Averages for trend

        Price > SMA: Uptrend
        Price < SMA: Downtrend
        """
        if any(v is None for v in [close, sma_20, sma_50]):
            return {"signal": "HOLD", "strength": 0.0, "reason": "MA not available"}

        if close > sma_20 and close > sma_50:
            strength = min((close - sma_20) / sma_20, 0.3)
            return {
                "signal": "BUY",
                "strength": strength,
                "reason": "Price above MAs (uptrend)",
            }
        elif close < sma_20 and close < sma_50:
            strength = min((sma_20 - close) / sma_20, 0.3)
            return {
                "signal": "SELL",
                "strength": strength,
                "reason": "Price below MAs (downtrend)",
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0.0,
                "reason": "Mixed MA signals",
            }

    @staticmethod
    def combine_signals(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine multiple indicator signals into one final signal

        Uses weighted average based on signal strength
        """
        if not signals:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reasoning": "No signals available",
                "details": [],
            }

        buy_strength = 0.0
        sell_strength = 0.0

        for sig in signals:
            if sig["signal"] == "BUY":
                buy_strength += sig["strength"]
            elif sig["signal"] == "SELL":
                sell_strength += sig["strength"]

        total_strength = buy_strength + sell_strength

        if total_strength == 0:
            final_signal = "HOLD"
            confidence = 0.0
        elif buy_strength > sell_strength:
            final_signal = "BUY"
            confidence = buy_strength / len(signals)
        else:
            final_signal = "SELL"
            confidence = sell_strength / len(signals)

        # Normalize confidence to 0-1
        confidence = min(confidence, 1.0)

        return {
            "signal": final_signal,
            "confidence": confidence,
            "buy_strength": buy_strength,
            "sell_strength": sell_strength,
            "reasoning": [s["reason"] for s in signals],
            "details": signals,
        }
