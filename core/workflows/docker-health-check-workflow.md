---
id: docker-health-check-workflow
mode: workflow
autonomy_level: 1
risk_level: 1
approval_required: false
responsible_agents: [observer, devops]
---

# Docker Health Check Workflow

## วัตถุประสงค์
ตรวจสถานะ Docker stack ทั้งหมดอย่างเป็นระบบ read-only เท่านั้น

## เมื่อใช้ Workflow Mode
งาน read-only ขั้นตอนชัด ทำซ้ำได้ ไม่มี side effect → Workflow เหมาะที่สุด

## Steps

### Step 1: docker_ps
```bash
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml ps
```
- ตรวจ STATUS ของทุก container
- Flag: `unhealthy`, `exited`, `restarting`

### Step 2: docker_compose_config
```bash
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml config --quiet
```
- ตรวจ YAML syntax valid
- **Fail condition**: YAML error → report ทันที

### Step 3: curl_health_endpoints
```bash
for port in 8088 8090 8091 8092 8093 8094 8095; do
  curl -sf http://127.0.0.1:$port/health || echo "FAIL :$port"
done
```
- ตรวจ HTTP 200 ทุก service
- บันทึก latency ms

### Step 4: docker_logs_tail
```bash
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml logs --tail=20
```
- ดู 20 บรรทัดล่าสุดของทุก service
- Flag: `ERROR`, `CRITICAL`, `exception`, `traceback`

### Step 5: summarize_status
- รวม: containers UP/DOWN, health endpoints OK/FAIL, log errors
- สร้าง status object: `{ overall, up_count, down_count, errors }`

### Step 6: report_failed_services
- ถ้ามี failed services → ระบุ service + error message
- แนะนำ: `docker compose logs {service}` สำหรับ debug ต่อ
- ถ้าทุกอย่าง OK → ระบุ "All services healthy"

## Accountability Log
```yaml
owner_agent: observer
tool_usage_log: [docker-ps, docker-config, curl-health, docker-logs]
verification_log: [http-health-check]
rollback_plan: N/A — read-only workflow
```
