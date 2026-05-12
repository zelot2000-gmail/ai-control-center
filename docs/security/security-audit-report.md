# Security Audit Report — AI Control Center
**agent**: security  
**task_id**: sec-audit-2026-001  
**risk_level**: 1 (read-only audit)  
**mode**: hybrid  
**timestamp**: 2026-05-11  
**environment**: static code analysis (dev)

---

## สรุปภาพรวม

| Category | Status | Severity |
|----------|--------|---------|
| Secret / Key leakage in source | ✅ Pass | — |
| Docker port binding | ✅ Pass | — |
| RTK blocklist completeness | ✅ Pass | — |
| CORS restriction | ✅ Pass | — |
| Webhook signature bypass | ❌ Fail | **High** |
| Mobile Gateway auth not enforced | ❌ Fail | **High** |
| shell=True in subprocess | ⚠️ Warning | Medium |
| Error detail leakage | ⚠️ Warning | Low |
| No rate limiting | ⚠️ Warning | Low |
| Prod healthcheck uses curl | ⚠️ Info | Low |

---

## รายละเอียดการตรวจ

### ✅ 1. Secret / Key Leakage in Source
**ตรวจ**: `sk-`, `ghp_`, `AKIA`, `xoxb-`, `BEGIN PRIVATE KEY`, hardcoded passwords  
**ผล**: ไม่พบ secret จริงในซอร์สโค้ด ทุก credential ใช้ `os.getenv()` ทั้งหมด  
**ไฟล์ที่ตรวจ**: `services/*/app/main.py`, `*.yml`, `*.json`, `.env.example`

---

### ✅ 2. Docker Port Binding
**ตรวจ**: `ports:` ใน `docker-compose.wsl.yml` และ `docker-compose.prod.yml`  
**ผล**: ทุก port bind บน `127.0.0.1` — ไม่มี `0.0.0.0` exposure  
**ตรวจสอบแล้ว**: Postgres 5432, Redis 6379, Qdrant 6333, gateway ทุกตัว

---

### ✅ 3. RTK Blocklist
**ตรวจ**: `services/rtk-bridge/app/main.py` — `BLOCKED_PATTERNS` + `BLOCKED_PATH_PREFIXES`  
**ผล**: ครอบคลุม destructive patterns ที่สำคัญ
```python
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/", r"DROP\s+DATABASE", r"docker\s+volume\s+rm",
    r"chmod\s+-R\s+777", r"iptables\s+-F", r"passwd\s+root", ...
]
```
`RTK_ALLOW_RUN_COMMAND` default = `"false"` → `/run-command` disabled by default ✅

---

### ✅ 4. CORS Restriction
**ตรวจ**: ทุก service `allow_origins`  
**ผล**: จำกัดเฉพาะ `http://127.0.0.1:3000` และ `http://localhost:3000` ทุก service  
**ไม่มี** wildcard `*` origin

---

### ❌ 5. Webhook Signature Bypass — **HIGH**

**ไฟล์**: `services/webhook-gateway/app/main.py:43-45`

```python
if WEBHOOK_SECRET and x_ap_signature:   # ← BUG: None header skips check
    if not _verify_signature(payload, x_ap_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, ...)
```

**ปัญหา**: ถ้า client ไม่ส่ง header `X-AP-Signature` เลย (`None`) → เงื่อนไข `and x_ap_signature` เป็น `False` → **ข้าม signature check ทั้งหมด** แม้ว่า `WEBHOOK_SECRET` ถูกตั้งค่าไว้  

**แก้ไข**: บังคับให้ต้องมี signature ถ้า `WEBHOOK_SECRET` มีค่า

```python
if WEBHOOK_SECRET:
    if not x_ap_signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    if not _verify_signature(payload, x_ap_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
```

ปัญหาเดียวกันมีทั้งใน `/webhooks/activepieces` และ `/webhooks/github`

---

### ❌ 6. Mobile Gateway Auth Not Enforced — **HIGH**

**ไฟล์**: `services/mobile-gateway/app/main.py:25`

```python
GATEWAY_SECRET = os.getenv("MOBILE_GATEWAY_SECRET", "")
```

**ปัญหา**: `GATEWAY_SECRET` โหลดมาแล้ว แต่ **ไม่มี endpoint ใดตรวจ header นี้จริง** — `POST /tasks` ไม่ต้อง auth ใดๆ ทุกคนที่ถึง port 8088 ส่ง task ได้เลย  

**แนะนำ**: เพิ่ม dependency ตรวจ `X-Gateway-Secret` ใน `/tasks` endpoint:

```python
def _require_secret(x_gateway_secret: Optional[str] = Header(None)):
    if GATEWAY_SECRET and x_gateway_secret != GATEWAY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/tasks", dependencies=[Depends(_require_secret)])
async def create_task(req: TaskRequest):
    ...
```

---

### ⚠️ 7. shell=True in Subprocess — **Medium**

**ไฟล์**: `services/rtk-bridge/app/main.py:189`

```python
result = subprocess.run(req.command, shell=True, ...)
```

**ปัญหา**: `shell=True` + user-controlled `req.command` มีความเสี่ยง command injection ถ้า blocklist มีช่องโหว่  

**บรรเทา**: ปัจจุบัน `ALLOW_RUN_COMMAND=false` โดย default ทำให้ endpoint ถูก block ก่อนถึงบรรทัดนี้  
**แนะนำระยะยาว**: ถ้าเปิด `ALLOW_RUN_COMMAND=true` ควรใช้ `shlex.split()` + `shell=False` แทน

---

### ⚠️ 8. Error Detail Leakage — **Low**

**ไฟล์**: `services/rtk-bridge/app/main.py:207`

```python
raise HTTPException(status_code=500, detail=str(e))
```

**ปัญหา**: Exception message อาจเปิดเผย internal paths หรือ system info  
**แก้ไข**: ใช้ generic message + log จริงใน logger แทน

---

### ⚠️ 9. No Rate Limiting — **Low**

**ปัญหา**: ทุก endpoint ไม่มี rate limiting — `POST /tasks` สามารถ flood ได้  
**แนะนำ**: เพิ่ม `slowapi` หรือ nginx rate limit ใน reverse proxy

---

## สรุปการแก้ไขที่ต้องทำ

| Priority | ไฟล์ | การแก้ไข |
|---------|------|---------|
| **High** | `services/webhook-gateway/app/main.py` | บังคับ signature ถ้า WEBHOOK_SECRET มีค่า |
| **High** | `services/mobile-gateway/app/main.py` | enforce GATEWAY_SECRET ใน /tasks |
| Medium | `services/rtk-bridge/app/main.py` | document shell=True risk, plan migration |
| Low | `services/rtk-bridge/app/main.py` | generic error message |
| Low | nginx / gateway | เพิ่ม rate limiting |

---

## Accountability Log
```yaml
owner_agent: security
workflow: security-review-workflow
tool_usage_log: [grep-scan, file-read, static-analysis]
verification_log: [port-binding-check, secret-pattern-scan, cors-check, auth-flow-trace]
rollback_plan: N/A — read-only audit
```
