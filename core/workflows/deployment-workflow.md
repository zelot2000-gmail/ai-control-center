---
id: deployment-workflow
mode: hybrid
autonomy_level: 4
risk_level: 3
approval_required: true
approval_phrase: CONFIRM STAGING
responsible_agents: [devops, qa, security, observer]
---

# Deployment Workflow

## วัตถุประสงค์
Deploy services อย่างมีขั้นตอน มี rollback และ verify ครบ

## ⚠️ ต้องได้รับ `CONFIRM STAGING` ก่อนรัน Step 5 ขึ้นไป

## Steps

### Step 1: check_git_status [workflow]
```bash
git status
git log --oneline -5
```
- ตรวจว่าไม่มี uncommitted changes ที่สำคัญ
- บันทึก current commit hash สำหรับ rollback

### Step 2: check_branch [workflow]
```bash
git branch --show-current
```
- staging: branch ต้องเป็น `staging` หรือ `feat/*`
- production: branch ต้องเป็น `main` เท่านั้น
- **Fail**: wrong branch → หยุดและ report

### Step 3: compose_config [workflow]
```bash
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml config --quiet
```
- ตรวจ YAML valid ก่อน build

### Step 4: backup_if_required [workflow]
- ถ้า risk_level >= 4 → รัน backup-workflow ก่อน
- บันทึก backup path สำหรับ rollback

### Step 5: build [workflow — ต้อง approval]
```bash
docker compose --env-file .env -f {compose_file} --profile core build
```
- ดู build log ตรวจ error

### Step 6: up [workflow]
```bash
docker compose --env-file .env -f {compose_file} --profile core up -d
```

### Step 7: health_check [workflow]
```bash
bash scripts/verify-wsl.sh
```
- รอ 30 วินาที แล้วตรวจ health ทุก service
- **Fail**: service ไม่ healthy ภายใน 60 วินาที → trigger rollback

### Step 8: log_check [hybrid → agent]
```bash
docker compose logs --tail=50
```
- Agent ตรวจหา ERROR, CRITICAL, exception
- ถ้าพบ critical error → trigger rollback

### Step 9: rollback_if_failed [workflow]
ถ้า Step 7-8 fail:
```bash
git checkout {previous_commit}
docker compose --env-file .env -f {compose_file} --profile core up -d --build
```
- รัน health check ซ้ำ
- Report: rollback successful / failed

### Step 10: deployment_report [workflow]
```yaml
deployment:
  timestamp: "..."
  commit: "..."
  services_up: 0
  services_failed: []
  rollback_triggered: false
  status: success | failed | rolled_back
```

## Accountability Log
```yaml
owner_agent: devops
responsible_agents: [devops, qa, security, observer]
approval_required: true
approval_phrase: CONFIRM STAGING
tool_usage_log: [git, docker-compose-build, docker-compose-up, health-check]
rollback_plan: git checkout {prev_commit} + docker compose up --build
```
