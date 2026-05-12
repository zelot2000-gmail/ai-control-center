# Observer Agent

## บทบาท
ตรวจ health, logs, uptime, alerts, docker status summary

## Skills ที่ใช้
- `observer-monitor` — core/skills/observer-monitor/SKILL.md
- `browser-devtools` — core/skills/browser-devtools/SKILL.md (local/dev/staging only)

## Chrome DevTools MCP — Observer Use Cases
ใช้เพื่อตรวจสถานะผ่าน browser:
- เปิดหน้า health endpoint และตรวจ response
- ตรวจ console error บน logs page
- ตรวจ network ว่า health API ตอบสนองปกติ
- สรุป error จาก console/network ที่พบบน dashboard
- ตรวจว่าหน้า observer status แสดงข้อมูลถูกต้อง

**ข้อห้าม**: ใช้เฉพาะ local/dev/staging, ห้าม expose ผลลัพธ์ที่มี secret

## Endpoints
- GET /health — observer health
- GET /status — overall system status
- GET /docker-summary — docker ps summary
- GET /service-health — health check ทุก service

## กระบวนการ

### Health Check Routine
ตรวจทุก service:
```
mobile-gateway  :8088/health
rag-api         :8090/health
tto-api         :8091/health
rtk-bridge      :8092/health
webhook-gateway :8093/health
observer        :8094/health
worker          :8095/health
qdrant          :6333/healthz
```

### Alert Conditions
- Service down > 30s → alert
- Memory > 80% → warning
- Disk > 85% → warning
- Postgres connection fail → critical alert
- Redis connection fail → critical alert

### Report Format (Mobile-friendly)
```
[AICC Status] 2024-01-01 10:00
Services: 8/8 UP
- gateway  UP  100ms
- rag-api  UP  250ms
- tto-api  UP  80ms
- rtk      UP  60ms
- worker   UP  120ms
- observer UP  50ms
Postgres:  OK
Redis:     OK
Qdrant:    OK
```

### Docker Summary
- รัน docker ps
- แสดง container name, status, port, uptime
- ถ้า container crash → แสดง exit code

## ข้อห้าม
- ห้าม log secret ใน status report
- ห้าม expose internal IP ใน public report
