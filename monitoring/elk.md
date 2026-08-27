# ELK Stack

Centralized logging for backend ticks, alerts, WS events.

## Quick start

```bash
docker-compose -f docker-compose.elk.yml up -d
# Kibana -> http://localhost:5601
# Elasticsearch -> http://localhost:9200
```

## Log flow

`backend (loguru JSON) -> Filebeat/Fluentd -> Logstash -> Elasticsearch -> Kibana`

- Backend logs JSON to stdout; Docker json-file driver ships via Filebeat sidecar.
- Configure index `nse-screener-*` with @timestamp, level, symbol, latency.
- Kibana dashboards: error rate, WS disconnects, stale alerts.

## Production

- Use Elastic Cloud or self-hosted 3-node ES.
- Set `xpack.security.enabled=true`, TLS.
- Retention: 7d hot, 30d warm via ILM.
- Alert on `level:error` rate > 5/min via ElastAlert.
