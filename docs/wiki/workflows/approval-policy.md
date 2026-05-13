---
title: "Approval Policy"
category: workflows
tags: [approval, autonomy, risk, authorization, confirm, agent-runner]
status: stable
updated: 2026-05-13
---

# Approval Policy

## Autonomy Levels

| Level | ชื่อ | Action | Approval |
|-------|------|--------|---------|
| 0 | Read-only | อ่าน, ค้นหา, ดู status | ไม่ต้อง |
| 1 | Plan only | เสนอแผน, แนะนำ, วิเคราะห์ | ไม่ต้อง |
| 2 | Safe dev | รัน workflow ใน dev/WSL | ไม่ต้อง |
| 3 | Edit dev | แก้ไขไฟล์ใน dev | ไม่ต้อง |
| 4 | Staging | Deploy staging, restart staging | `CONFIRM STAGING` |
| 5 | Production | Deploy prod, destructive ops | `CONFIRM DEPLOY` / `CONFIRM DANGEROUS` |

---

## Risk Level Matrix

| Action | Risk | Level | Approval Phrase |
|--------|------|-------|----------------|
| อ่านไฟล์, ดู logs | 1 | 0 | — |
| สร้าง task, ส่ง command | 1 | 2 | — |
| แก้ config ใน dev | 2 | 3 | — |
| Restart dev container | 2 | 2 | — |
| Deploy staging | 3 | 4 | `CONFIRM STAGING` |
| Restart production service | 4 | 5 | `CONFIRM DEPLOY` |
| ลบ Docker volume | 5 | 5 | `CONFIRM DANGEROUS` |
| Drop database | 5 | 5 | `CONFIRM DANGEROUS` |
| Force push git main | 5 | 5 | `CONFIRM DANGEROUS` |

---

## Approval Phrases

### CONFIRM STAGING
ใช้ก่อน deploy หรือ restart บน staging environment

```
ผู้ใช้ต้องพิมพ์: CONFIRM STAGING
Agent จะ proceed เมื่อได้รับ phrase นี้เท่านั้น
```

### CONFIRM DEPLOY
ใช้ก่อน deploy production

```
ผู้ใช้ต้องพิมพ์: CONFIRM DEPLOY
ต้องมี rollback plan ก่อน proceed
```

### CONFIRM DANGEROUS
ใช้ก่อน destructive operations

```
ผู้ใช้ต้องพิมพ์: CONFIRM DANGEROUS
ต้องมี backup ยืนยันก่อน proceed
ต้องระบุ backup location และเวลา backup
```

---

## Agent Runner Approval Gate

สำหรับ **Agent Runner v1** มี approval gate แยกต่างหากที่ทำงานใน runtime (ไม่ใช่ phrase-based):

### เงื่อนไขที่ต้อง approve ก่อน run

| เงื่อนไข | ผลลัพธ์ |
|---------|--------|
| `environment == "production"` | `blocked_approval_required` |
| `mode == "execute"` | `blocked_approval_required` |
| `risk_level >= 3` | `blocked_approval_required` |
| `runner_mode == "hermes_http"` AND `risk_level > 1` | `blocked_approval_required` |

เงื่อนไขทั้งหมดนี้ **cumulative** — ถ้าตรงข้อใดข้อหนึ่งก็ block

### วิธี Approve ผ่าน API

```http
PATCH /tasks/{task_id}/approval
Content-Type: application/json
X-Gateway-Secret: {MOBILE_GATEWAY_SECRET}

{"approval_status": "approved"}
```

หลัง approve: worker จะ re-queue task และรัน agent runner ต่อโดยอัตโนมัติ

### วิธี Approve ผ่าน UI

Jobs page → เลือก task ที่มีสถานะ `NEED APPROVAL` → คลิก "Approve" button

---

## Authorization Context

Agent ต้องตรวจสอบก่อนทุก action ว่า:

1. **Who is requesting?** — user identity (ระบบนี้ใช้ single user แต่ควร log)
2. **What environment?** — dev / staging / production
3. **What is the blast radius?** — ถ้าผิดพลาดกระทบอะไรบ้าง
4. **Is there a rollback?** — ถ้าผิดพลาดกลับได้ไหม

---

## Approval Workflow

### Phrase-based (CLAUDE.md / manual ops)

```
User → Request action (Risk Level ≥ 4)
         ↓
Agent → แสดง: "ต้องการ approval ก่อน"
         → ระบุ: action ที่จะทำ, risk level, impact
         → รอ approval phrase จาก user
         ↓
User → พิมพ์ CONFIRM ...
         ↓
Agent → ตรวจ phrase ตรงไหม?
         ├─ ใช่ → proceed + log approval
         └─ ไม่ใช่ → reject + explain
```

### Runtime Gate (Agent Runner)

```
task created (environment=production OR mode=execute OR risk≥3)
    ↓
_can_run_agent() → block
    ↓
agent_run_status = "blocked_approval_required"
    ↓
User → PATCH /tasks/{id}/approval {"approval_status": "approved"}
    ↓
Worker picks up → re-run agent runner → proceeds
```

---

## Approval ใน CLAUDE.md

กฎนี้ถูก enforce ใน `CLAUDE.md`:

```markdown
### ห้ามเด็ดขาด
- ห้าม deploy production — ต้องได้รับ CONFIRM DEPLOY ก่อน
- ห้ามลบ volume — ต้องได้รับ CONFIRM DANGEROUS ก่อน
```

Agent ทุกตัวต้องปฏิบัติตาม CLAUDE.md — ไม่ใช่แค่ manager

---

## Emergency Override

ในกรณีฉุกเฉิน (production down):
1. ระบุว่าเป็น emergency ชัดเจน
2. Document เหตุผลก่อน override
3. Proceed ด้วย autonomy ที่น้อยที่สุดที่แก้ปัญหาได้
4. Post-mortem ภายใน 24 ชั่วโมง
