"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator
import time

# Metrics
ticks_processed_total = Counter(
    'ticks_processed_total',
    'Total number of ticks processed',
    ['provider', 'symbol']
)

websocket_connections = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

tick_latency = Histogram(
    'tick_processing_latency_seconds',
    'Tick processing latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

broadcast_latency = Histogram(
    'broadcast_latency_seconds',
    'Broadcast latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

alert_triggered_total = Counter(
    'alerts_triggered_total',
    'Total alerts triggered',
    ['alert_type']
)

cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_key'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_key'])

api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

app_info = Info('app_info', 'Application information')


def setup_metrics(app):
    """Setup Prometheus metrics for FastAPI app."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/ready"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics")

    # Set app info
    app_info.info({
        'version': '2.0.0',
        'name': 'NSE Top 500 Realtime Screener'
    })

    return instrumentator


class MetricsCollector:
    """Helper class for collecting metrics."""

    @staticmethod
    def record_tick_processed(provider: str, symbol: str):
        """Record tick processed."""
        ticks_processed_total.labels(provider=provider, symbol=symbol).inc()

    @staticmethod
    def record_tick_latency(duration: float):
        """Record tick processing latency."""
        tick_latency.observe(duration)

    @staticmethod
    def record_broadcast_latency(duration: float):
        """Record broadcast latency."""
        broadcast_latency.observe(duration)

    @staticmethod
    def record_alert(alert_type: str):
        """Record alert triggered."""
        alert_triggered_total.labels(alert_type=alert_type).inc()

    @staticmethod
    def record_cache_hit(cache_key: str):
        """Record cache hit."""
        cache_hits.labels(cache_key=cache_key).inc()

    @staticmethod
    def record_cache_miss(cache_key: str):
        """Record cache miss."""
        cache_misses.labels(cache_key=cache_key).inc()

    @staticmethod
    def set_websocket_connections(count: int):
        """Set active WebSocket connections."""
        websocket_connections.set(count)


# Global metrics collector
metrics = MetricsCollector()
