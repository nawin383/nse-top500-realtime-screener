"""Machine Learning-based anomaly detection for unusual price/volume patterns."""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math
from collections import deque
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from loguru import logger


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    is_anomaly: bool
    anomaly_score: float  # -1 to 1 (higher = more anomalous)
    confidence: float  # 0 to 1
    pattern_type: str  # VOLUME_SPIKE, PRICE_JUMP, UNUSUAL_VOLATILITY, NORMAL


class MLAnomalyDetector:
    """Machine learning-based anomaly detector using Isolation Forest."""

    def __init__(self, contamination: float = 0.05, window_size: int = 100):
        """
        Initialize anomaly detector.

        Args:
            contamination: Expected proportion of outliers (0.05 = 5%)
            window_size: Number of recent data points to keep
        """
        self.contamination = contamination
        self.window_size = window_size
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.history: deque = deque(maxlen=window_size)

    def add_observation(
        self,
        price: float,
        volume: int,
        volatility: float,
        price_change_pct: float,
        rel_volume: float
    ):
        """Add new observation to history."""
        obs = [price, volume, volatility, price_change_pct, rel_volume]
        self.history.append(obs)

        # Retrain if we have enough data
        if len(self.history) >= min(30, self.window_size // 2):
            self._retrain()

    def _retrain(self):
        """Retrain the model with current history."""
        try:
            X = np.array(list(self.history))
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            self.is_fitted = True
        except Exception as e:
            logger.debug(f"ML retrain failed: {e}")

    def detect(
        self,
        price: float,
        volume: int,
        volatility: float,
        price_change_pct: float,
        rel_volume: float
    ) -> AnomalyDetection:
        """Detect if current observation is anomalous."""
        if not self.is_fitted:
            return AnomalyDetection(
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.0,
                pattern_type="NORMAL"
            )

        try:
            # Prepare observation
            obs = np.array([[price, volume, volatility, price_change_pct, rel_volume]])
            obs_scaled = self.scaler.transform(obs)

            # Predict (-1 = anomaly, 1 = normal)
            prediction = self.model.predict(obs_scaled)[0]

            # Get anomaly score
            score = self.model.score_samples(obs_scaled)[0]

            # Normalize score to 0-1 range
            normalized_score = 1 / (1 + math.exp(score))  # Sigmoid

            is_anomaly = prediction == -1

            # Determine pattern type
            pattern_type = self._classify_pattern(
                price_change_pct,
                rel_volume,
                volatility,
                is_anomaly
            )

            return AnomalyDetection(
                is_anomaly=is_anomaly,
                anomaly_score=normalized_score,
                confidence=abs(score) / 2.0,  # Rough confidence estimate
                pattern_type=pattern_type
            )

        except Exception as e:
            logger.debug(f"Anomaly detection failed: {e}")
            return AnomalyDetection(
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.0,
                pattern_type="NORMAL"
            )

    def _classify_pattern(
        self,
        price_change_pct: float,
        rel_volume: float,
        volatility: float,
        is_anomaly: bool
    ) -> str:
        """Classify the type of anomaly."""
        if not is_anomaly:
            return "NORMAL"

        # Volume spike with normal price movement
        if rel_volume > 3.0 and abs(price_change_pct) < 2.0:
            return "VOLUME_SPIKE"

        # Large price movement
        if abs(price_change_pct) > 3.0:
            return "PRICE_JUMP"

        # High volatility
        if volatility > 2.5:
            return "UNUSUAL_VOLATILITY"

        return "UNUSUAL_PATTERN"


class SimpleAnomalyDetector:
    """Simple rule-based anomaly detection (fallback when ML not available)."""

    @staticmethod
    def detect(
        price_change_pct: float,
        rel_volume: float,
        volatility: float,
        z_score_price: float,
        z_score_volume: float
    ) -> AnomalyDetection:
        """Detect anomalies using statistical rules."""

        is_anomaly = False
        score = 0.0
        pattern_type = "NORMAL"

        # Price jump detection (3 standard deviations)
        if abs(z_score_price) > 3.0:
            is_anomaly = True
            score = min(abs(z_score_price) / 5.0, 1.0)
            pattern_type = "PRICE_JUMP"

        # Volume spike detection
        elif rel_volume > 5.0 or abs(z_score_volume) > 3.0:
            is_anomaly = True
            score = min(rel_volume / 10.0, 1.0)
            pattern_type = "VOLUME_SPIKE"

        # Unusual volatility
        elif volatility > 3.0:
            is_anomaly = True
            score = min(volatility / 5.0, 1.0)
            pattern_type = "UNUSUAL_VOLATILITY"

        confidence = score if is_anomaly else 0.9

        return AnomalyDetection(
            is_anomaly=is_anomaly,
            anomaly_score=score,
            confidence=confidence,
            pattern_type=pattern_type
        )


def calculate_z_score(values: List[float], current: float) -> float:
    """Calculate Z-score for current value."""
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    return (current - mean) / std_dev


class PatternRecognizer:
    """Recognize common chart patterns."""

    @staticmethod
    def detect_head_and_shoulders(
        highs: List[float],
        lows: List[float],
        window: int = 20
    ) -> Optional[str]:
        """Detect head and shoulders pattern."""
        if len(highs) < window:
            return None

        recent_highs = highs[-window:]

        # Find three peaks
        peaks = []
        for i in range(1, len(recent_highs) - 1):
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
                peaks.append((i, recent_highs[i]))

        if len(peaks) < 3:
            return None

        # Check if middle peak is highest
        peaks_sorted = sorted(peaks, key=lambda x: x[1], reverse=True)
        highest_peak = peaks_sorted[0]

        # Find left and right shoulders
        left_shoulders = [p for p in peaks if p[0] < highest_peak[0]]
        right_shoulders = [p for p in peaks if p[0] > highest_peak[0]]

        if left_shoulders and right_shoulders:
            # Check if shoulders are roughly equal
            left_height = left_shoulders[-1][1]
            right_height = right_shoulders[0][1]

            if abs(left_height - right_height) / left_height < 0.1:
                return "HEAD_AND_SHOULDERS"

        return None

    @staticmethod
    def detect_double_top_bottom(
        prices: List[float],
        window: int = 20
    ) -> Optional[str]:
        """Detect double top or double bottom pattern."""
        if len(prices) < window:
            return None

        recent = prices[-window:]

        # Find peaks and troughs
        extremes = []
        for i in range(2, len(recent) - 2):
            # Peak
            if recent[i] > recent[i-1] and recent[i] > recent[i+1]:
                extremes.append(("peak", recent[i]))
            # Trough
            elif recent[i] < recent[i-1] and recent[i] < recent[i+1]:
                extremes.append(("trough", recent[i]))

        if len(extremes) < 2:
            return None

        # Check for double top
        peaks = [e for e in extremes if e[0] == "peak"]
        if len(peaks) >= 2:
            if abs(peaks[-1][1] - peaks[-2][1]) / peaks[-1][1] < 0.02:
                return "DOUBLE_TOP"

        # Check for double bottom
        troughs = [e for e in extremes if e[0] == "trough"]
        if len(troughs) >= 2:
            if abs(troughs[-1][1] - troughs[-2][1]) / troughs[-1][1] < 0.02:
                return "DOUBLE_BOTTOM"

        return None

    @staticmethod
    def detect_triangle(
        highs: List[float],
        lows: List[float],
        window: int = 20
    ) -> Optional[str]:
        """Detect triangle consolidation patterns."""
        if len(highs) < window or len(lows) < window:
            return None

        recent_highs = highs[-window:]
        recent_lows = lows[-window:]

        # Calculate trend of highs and lows
        high_slope = (recent_highs[-1] - recent_highs[0]) / len(recent_highs)
        low_slope = (recent_lows[-1] - recent_lows[0]) / len(recent_lows)

        # Ascending triangle: flat highs, rising lows
        if abs(high_slope) < 0.1 and low_slope > 0.1:
            return "ASCENDING_TRIANGLE"

        # Descending triangle: falling highs, flat lows
        if high_slope < -0.1 and abs(low_slope) < 0.1:
            return "DESCENDING_TRIANGLE"

        # Symmetrical triangle: converging highs and lows
        if high_slope < -0.05 and low_slope > 0.05:
            return "SYMMETRICAL_TRIANGLE"

        return None
