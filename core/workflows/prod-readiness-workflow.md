---
id: prod-readiness-workflow
mode: hybrid
autonomy_level: 2
risk_level: 2
approval_required: false
responsible_agents: [devops, security, administrator, qa]
---

# Production Readiness Workflow

## วัตถุประสงค์
ตรวจความพร้อมก่อนขึ้น CWP/AlmaLinux 8 Production

## Steps

### Step 1: check_compose_prod [workflow]
```bash
docker compose -f infra/docker/docker-compose.prod.yml config --quiet
```
- ตรวจ YAML valid
- ตรวจว่า prod compose ใช้ image tag ชัดเจน (ไม่ใช่ `latest`)

### Step 2: verify_no_public_db_ports [workflow]
ตรวจ docker-compose.prod.yml:
- Postgres ไม่ expose port ออก internet
- Redis ไม่ expose port ออก internet
- Qdrant ไม่ expose port ออก internet
- **Pass**: ทุก DB bind บน `127.0.0.1` หรือ internal network เท่านั้น

### Step 3: verify_localhost_bindings [workflow]
ตรวจทุก `ports:` ใน compose file:
- ต้องเป็น `127.0.0.1:PORT:PORT` หรือ internal เท่านั้น
- **Fail**: พบ `0.0.0.0:PORT` → block และ report

### Step 4: check_env_example [workflow]
- ตรวจว่า `.env.example` มีครบทุก variable ที่ compose ต้องใช้
- ตรวจว่าไม่มี secret จริงใน `.env.example`
- ตรวจว่า `.env` อยู่ใน `.gitignore`

### Step 5: check_backup_script [workflow]
- ตรวจว่า `scripts/backup-wsl.sh` มีอยู่และ executable
- ตรวจว่า backup ครอบคลุม postgres + documents + core

### Step 6: check_reverse_proxy_notes [hybrid → agent]
- ตรวจ docs/operations/ ว่ามีเอกสาร nginx/CWP reverse proxy
- Agent ประเมิน: SSL, HTTPS redirect, security headers ครบไหม

### Step 7: security_review [hybrid → security agent]
- ตรวจ API ทุกตัวมี auth หรือ internal-only
- ตรวจไม่มี debug endpoint เปิดใน production
- ตรวจ RTK_ALLOW_RUN_COMMAND=false ใน prod
- ตรวจ ENVIRONMENT=production ถูกตั้งค่า

### Step 8: final_readiness_report [hybrid → agent สรุป]
สรุป:
- ✅ / ❌ ทุก check item
- Critical issues ที่ต้องแก้ก่อน deploy
- Recommended: production checklist PDF

## Accountability Log
```yaml
owner_agent: devops
responsible_agents: [devops, security, administrator, qa]
tool_usage_log: [docker-compose-config, grep, file-check]
verification_log: [port-binding-check, env-check, security-check]
rollback_plan: N/A — read-only audit
```
