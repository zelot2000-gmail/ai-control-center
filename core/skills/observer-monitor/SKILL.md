# Skill: Observer Monitor

## วัตถุประสงค์
health logs uptime alerts docker status summary

## Monitoring Commands
```bash
# Docker status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Resource usage
docker stats --no-stream

# Disk
df -h /

# Memory
free -h
```

## Health Check Endpoints
- mobile-gateway: GET :8088/health
- rag-api: GET :8090/health
- tto-api: GET :8091/health
- rtk-bridge: GET :8092/health
- webhook-gateway: GET :8093/health
- observer: GET :8094/health
- worker: GET :8095/health
- qdrant: GET :6333/healthz

## Alert Thresholds
- Service down > 30s → CRITICAL
- CPU > 90% for 5min → WARNING
- Memory > 85% → WARNING
- Disk > 90% → CRITICAL
- Postgres conn fail → CRITICAL
- Redis conn fail → CRITICAL

## Log Levels to Watch
- ERROR → immediate attention
- WARNING → monitor
- INFO → normal

## Observer Report Format
```json
{
  "timestamp": "2024-01-01T10:00:00Z",
  "services": {
    "mobile-gateway": {"status": "up", "latency_ms": 45},
    "rag-api": {"status": "up", "latency_ms": 120}
  },
  "databases": {
    "postgres": "ok",
    "redis": "ok",
    "qdrant": "ok"
  },
  "alerts": []
}
```
