"""Application configuration using pydantic-settings + dotenv."""
from __future__ import annotations
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Kit / Kite creds - backend only
    kite_api_key: str = Field(default="", alias="KITE_API_KEY")
    kite_api_secret: str = Field(default="", alias="KITE_API_SECRET")
    kite_access_token: str = Field(default="", alias="KITE_ACCESS_TOKEN")
    kite_client_id: str = Field(default="", alias="KITE_CLIENT_ID")
    kite_user_id: str = Field(default="", alias="KITE_USER_ID")
    kite_password: str = Field(default="", alias="KITE_PASSWORD")
    kite_totp_secret: str = Field(default="", alias="KITE_TOTP_SECRET")
    render_api_key: str = Field(default="", alias="RENDER_API_KEY")
    render_service_id: str = Field(default="", alias="RENDER_SERVICE_ID")
    websocket_url: str = Field(default="wss://ws.kite.trade/", alias="WEBSOCKET_URL")

    data_mode: str = Field(default="mock", alias="DATA_MODE")  # mock | live | replay
    nse_universe_file: str = Field(default="config/nse_top500.json", alias="NSE_UNIVERSE_FILE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    stale_threshold_sec: int = Field(default=30, alias="STALE_THRESHOLD_SEC")
    candle_intervals: str = Field(default="1,3,5,15,30", alias="CANDLE_INTERVALS")
    ws_broadcast_interval_ms: int = Field(default=250, alias="WS_BROADCAST_INTERVAL_MS")
    max_alerts: int = Field(default=1000, alias="MAX_ALERTS")
    replay_speed: float = Field(default=10.0, alias="REPLAY_SPEED")
    replay_file: str = Field(default="", alias="REPLAY_FILE")

    score_w_momentum: int = Field(default=25, alias="SCORE_W_MOMENTUM")
    score_w_volume: int = Field(default=25, alias="SCORE_W_VOLUME")
    score_w_rel_volume: int = Field(default=20, alias="SCORE_W_REL_VOLUME")
    score_w_breakout: int = Field(default=15, alias="SCORE_W_BREAKOUT")
    score_w_vwap: int = Field(default=10, alias="SCORE_W_VWAP")
    score_w_volatility: int = Field(default=5, alias="SCORE_W_VOLATILITY")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000", alias="CORS_ORIGINS")

    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")

    # ML features
    ml_anomaly_detection: bool = Field(default=True, alias="ML_ANOMALY_DETECTION")

    # Webhooks
    webhook_timeout_sec: int = Field(default=10, alias="WEBHOOK_TIMEOUT_SEC")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def candle_intervals_list(self) -> List[int]:
        return [int(x.strip()) for x in self.candle_intervals.split(",") if x.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def is_mock(self) -> bool:
        return self.data_mode.lower() == "mock"

    @property
    def is_live(self) -> bool:
        return self.data_mode.lower() == "live"

    @property
    def is_replay(self) -> bool:
        return self.data_mode.lower() == "replay"

    @property
    def universe_path(self) -> Path:
        p = Path(self.nse_universe_file)
        if p.is_absolute():
            return p
        # backend/app -> project root is two levels up from backend, but we are in backend/app
        project_root = Path(__file__).resolve().parents[2]
        # if we run from project root, also try relative
        if (project_root / p).exists():
            return project_root / p
        # fallback: cwd relative
        if (Path.cwd() / p).exists():
            return Path.cwd() / p
        # also check backend parent if running from backend folder
        alt = Path.cwd().parent / p
        if alt.exists():
            return alt
        return project_root / p

settings = Settings()
# Resolve universe file relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_universe_path = Path(settings.nse_universe_file)
if not _universe_path.is_absolute():
    _universe_path = _PROJECT_ROOT / _universe_path
UNIVERSE_PATH = _universe_path
