# Skill: QA Verify

## วัตถุประสงค์
ทดสอบ verify regression checklist acceptance criteria

## Health Check Commands
```bash
curl -sf http://127.0.0.1:8088/health
curl -sf http://127.0.0.1:8090/health
curl -sf http://127.0.0.1:8091/health
curl -sf http://127.0.0.1:8092/health
curl -sf http://127.0.0.1:8093/health
curl -sf http://127.0.0.1:8094/health
curl -sf http://127.0.0.1:8095/health
curl -sf http://127.0.0.1:6333/healthz
```

## API Smoke Tests
```bash
# Create task
curl -X POST http://127.0.0.1:8088/tasks \
  -H "Content-Type: application/json" \
  -d '{"source":"test","user":"qa","text":"test task"}'

# TTO optimize
curl -X POST http://127.0.0.1:8091/optimize \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'

# RTK validate
curl -X POST http://127.0.0.1:8092/validate-command \
  -H "Content-Type: application/json" \
  -d '{"command":"ls -la","workspace":"/workspace"}'
```

## Acceptance Criteria
งาน "done" เมื่อ:
1. Health check ทุก service = 200 OK
2. Task creation ได้ task_id
3. Log ไม่มี ERROR level
4. ไม่มี secret ใน response
5. Port ไม่ชน

## Regression Script
```bash
bash scripts/verify-wsl.sh
```
