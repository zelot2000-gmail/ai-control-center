---
id: log-review-workflow
mode: hybrid
autonomy_level: 1
risk_level: 1
approval_required: false
responsible_agents: [observer, devops]
---

# Log Review Workflow

## วัตถุประสงค์
รวบรวม วิเคราะห์ และสรุป logs จาก Docker services อย่างเป็นระบบ

## Steps

### Step 1: collect_logs [workflow]
```bash
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml logs --tail=100 > /tmp/aicc-logs.txt
```
- เก็บ logs 100 บรรทัดล่าสุดทุก service
- บันทึก timestamp ที่ collect

### Step 2: run_tto_log_summarization [workflow]
```http
POST http://127.0.0.1:8091/optimize
{
  "text": "{logs_content}",
  "mode": "summarize"
}
```
- ส่ง logs ผ่าน TTO API เพื่อ summarize
- ถ้า TTO ไม่พร้อม → ใช้ grep pattern แทน

### Step 3: classify_errors [workflow]
grep patterns:
```bash
grep -E "ERROR|CRITICAL|exception|traceback|Traceback" /tmp/aicc-logs.txt
grep -E "connection refused|timeout|unhealthy" /tmp/aicc-logs.txt
grep -E "OOM|kill|out of memory" /tmp/aicc-logs.txt
```
จัดหมวด:
- `application_error` — Python exception, FastAPI error
- `connection_error` — service ต่อกันไม่ได้
- `system_error` — OOM, disk full, permission

### Step 4: identify_root_cause_candidates [hybrid → agent]
Agent วิเคราะห์:
- Error pattern ซ้ำ: เกิดบ่อยแค่ไหน ช่วงเวลาใด
- Correlation: service A error → service B error
- Timeline: error เริ่มหลังจาก event ใด

### Step 5: suggest_next_checks [hybrid → agent]
ถ้า application_error → แนะนำ: ดู stack trace เต็ม + ตรวจ requirements.txt
ถ้า connection_error → แนะนำ: ตรวจ `docker compose ps` + network
ถ้า system_error → แนะนำ: `docker stats` + disk usage

### Step 6: observer_report
```yaml
log_review:
  timestamp: "..."
  services_reviewed: []
  total_errors: 0
  critical_errors: 0
  application_errors: 0
  connection_errors: 0
  system_errors: 0
  root_cause_candidates: []
  recommended_actions: []
  status: clean | warnings | critical
```

## Accountability Log
```yaml
owner_agent: observer
tool_usage_log: [docker-compose-logs, tto-api/optimize, grep]
verification_log: [error-pattern-check]
rollback_plan: N/A — read-only log review
```
