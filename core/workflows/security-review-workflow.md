---
id: security-review-workflow
mode: hybrid
autonomy_level: 1
risk_level: 1
approval_required: false
responsible_agents: [security, observer]
---

# Security Review Workflow

## วัตถุประสงค์
ตรวจ security ของระบบแบบ read-only ครอบคลุม secret, port, API, browser

## ข้อห้าม
- ห้ามทดสอบ destructive action
- ห้าม login production account
- ห้ามส่ง command ลบข้อมูล
- ถ้าพบ secret จริง → หยุดทันที ไม่ log ใน output

## Steps

### Step 1: scan_env_exposure [workflow]
```bash
grep -r "API_KEY\|SECRET\|PASSWORD\|TOKEN" .env.example
grep -r "API_KEY\|SECRET\|PASSWORD\|TOKEN" apps/web/dist/index.html
```
- ตรวจว่าไม่มี secret จริงใน .env.example
- ตรวจว่าไม่มี secret ใน frontend JS bundle

### Step 2: check_secret_patterns [workflow]
```bash
grep -r "sk-\|ghp_\|xoxb-\|AKIA\|-----BEGIN" core/ services/ apps/
```
- Flag: OpenAI key, GitHub token, Slack token, AWS key, private key
- **Critical**: ถ้าพบ → หยุดและแจ้ง owner ทันที

### Step 3: check_docker_ports [workflow]
```bash
grep -A2 "ports:" infra/docker/docker-compose.wsl.yml | grep -v "127.0.0.1"
```
- ตรวจทุก port binding
- **Fail**: พบ `0.0.0.0` หรือ port ไม่มี host binding → flag critical

### Step 4: check_rtk_allowlist [workflow]
```bash
cat services/rtk-bridge/app/main.py | grep -A5 "BLOCKED_PATTERNS"
```
- ตรวจว่า destructive commands ถูก block
- ตรวจ `RTK_ALLOW_RUN_COMMAND` default เป็น `false`

### Step 5: check_api_auth [hybrid → agent]
- ตรวจ mobile-gateway มี `MOBILE_GATEWAY_SECRET` check หรือไม่
- ตรวจ webhook-gateway มี signature verification
- Agent ประเมิน: authentication coverage, missing auth endpoints

### Step 6: check_browser_secret_leak [hybrid → agent + devtools]
- เปิด http://127.0.0.1:3000 ใน Chrome DevTools
- ตรวจ Network tab: ไม่มี token/key ใน request
- ตรวจ Console: ไม่มี secret ใน log
- ตรวจ Source: ไม่มี hardcoded credential ใน JS
- **Rule**: ใช้เฉพาะ local/dev/staging เท่านั้น

### Step 7: security_report [hybrid → agent สรุป]
```yaml
security_review:
  timestamp: "..."
  secret_leakage: pass | fail
  port_exposure: pass | fail
  rtk_safety: pass | fail
  api_auth: pass | partial | fail
  browser_leak: pass | fail
  critical_issues: []
  high_issues: []
  recommendations: []
  overall: pass | fail
```

## Accountability Log
```yaml
owner_agent: security
tool_usage_log: [grep-secret-scan, port-check, rtk-check, chrome-devtools-mcp]
verification_log: [source-scan, network-check, console-check]
rollback_plan: N/A — read-only audit
```
