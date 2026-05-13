---
title: "Task Lifecycle"
category: workflows
tags: [task, status, lifecycle, state-machine, transition, agent-runner]
status: stable
updated: 2026-05-13
---

# Task Lifecycle

## Status State Machine

### Task-level Status

```
pending
  └─ [worker picks up] ──→ running
                              └─ [export done] ──→ exporting
                                                      └─ [export saved] ──→ exported
                                                                              ├─ [agent runner disabled] ──→ completed
                                                                              └─ [agent runner enabled] ──→ agent_running
                                                                                                               └─ [done] ──→ completed
```

### Agent Runner Status (`result.agent_run_status`)

หลังจาก task ถูก worker process เสร็จ ถ้า `AGENT_RUNNER_ENABLED=true` จะมี `agent_run_status` บอก state ของ Agent Run:

```
(task exported)
    └─ queued
         └─ preparing
              └─ running
                   ├─ blocked_approval_required    ← approval gate block
                   │       └─ [PATCH /approval approved] → กลับมา run ใหม่
                   │
                   ├─ completed_prompt_ready        ← prompt_only mode เสร็จ
                   │
                   ├─ waiting_for_hermes_manual_execution ← hermes_manual (รอ human)
                   │
                   ├─ waiting_hermes               ← hermes_http ส่งแล้ว (interim)
                   │
                   ├─ completed_report_saved        ← hermes_http สำเร็จ + report saved
                   │
                   ├─ hermes_response_unrecognized  ← hermes ตอบแล้วแต่ parse ไม่ได้
                   │
                   └─ failed                       ← error อื่นๆ
```

### Status Definitions (Task-level)

| Status | ความหมาย | ทำอะไรได้ |
|--------|---------|----------|
| `pending` | รอ worker รับงาน | ยกเลิก |
| `running` | Worker กำลัง process | ดู logs |
| `exporting` | กำลัง export prompt | ดู logs |
| `exported` | Prompt พร้อม — รอ agent runner | View Prompt |
| `agent_running` | Agent กำลัง generate report | View Prompt |
| `completed` | Task สำเร็จ — report saved | View Report, View Prompt, Timeline |
| `failed` | เกิด error | View logs, retry |
| `cancelled` | ผู้ใช้ยกเลิก | — |

### Agent Run Status Definitions

| `agent_run_status` | ความหมาย | สิ่งที่ต้องทำ |
|-------------------|---------|-------------|
| `completed_prompt_ready` | prompt_only เสร็จ | Copy prompt ไปใช้ manual |
| `waiting_for_hermes_manual_execution` | hermes_manual พร้อม | Copy payload ส่ง Hermes ด้วยมือ |
| `waiting_hermes` | hermes_http กำลังรอ response | รอ (interim state) |
| `completed_report_saved` | hermes_http สำเร็จ รายงาน saved | View Report |
| `hermes_response_unrecognized` | Hermes ตอบแต่ format ไม่รู้จัก | ตรวจ `.hermes-response.json` |
| `blocked_approval_required` | รอ approval ก่อนรัน | กด Approve หรือ PATCH /approval |
| `failed` | error | ดู logs |

---

## Timeline Events

แต่ละ task มี `agent_events` array บันทึก history (append-only)

### System Events

| Event | Trigger | Agent |
|-------|---------|-------|
| `task_created` | POST /tasks | system |
| `file_uploaded` | แนบไฟล์ใน create_task | system |
| `worker_started` | Worker รับงาน | worker |
| `export_started` | เริ่ม export prompt | worker |
| `attachment_context_built` | Attachment analyzed | worker |
| `export_completed` | Prompt saved | worker |
| `agent_run_requested` | User คลิก Run Agent | user |
| `report_template_opened` | User เปิด Save Report | user |
| `final_report_saved` | User save report | report_source |
| `task_completed` | Task เสร็จสมบูรณ์ | system |

### Agent Runner Events

| Event | เกิดเมื่อ |
|-------|---------|
| `agent_run_started` | เริ่ม run_agent() |
| `agent_prompt_built` | build prompt เสร็จ |
| `agent_run_blocked` | approval gate block |
| `agent_run_approved` | ได้รับ approval แล้ว |
| `hermes_request_sent` | POST ส่งออกไปแล้ว |
| `hermes_response_received` | ได้รับ response จาก Hermes |
| `hermes_report_saved` | บันทึก report เสร็จ |
| `hermes_fallback_triggered` | fallback เริ่มทำงาน |
| `agent_run_completed` | run เสร็จสมบูรณ์ |

---

## API Endpoints

### Create Task

```http
POST /tasks
Content-Type: application/json
X-Gateway-Secret: {MOBILE_GATEWAY_SECRET}

{
  "source": "web-ui",
  "user": "admin",
  "text": "ตรวจ health service",
  "attachments": [],
  "environment": "dev",
  "mode": "execute"
}
```

Response:
```json
{
  "task_id": "abc123",
  "status": "pending"
}
```

### Get Task

```http
GET /tasks/{task_id}
```

### Update Status

```http
PATCH /tasks/{task_id}/status
{"status": "running"}
```

### Update Result (merge, not overwrite)

```http
PATCH /tasks/{task_id}/result
{"result": {"export_path": "/exports/abc123.md"}}
```

### Approve Agent Run

```http
PATCH /tasks/{task_id}/approval
{"approval_status": "approved"}
```

### Save Final Report

```http
POST /tasks/{task_id}/report
{
  "report_source": "manager",
  "final_report": "# รายงาน\n...",
  "verification_status": "PASS"
}
```

---

## Task Data Structure

```json
{
  "task_id": "abc123",
  "status": "completed",
  "created_at": "2026-05-13T10:00:00Z",
  "updated_at": "2026-05-13T10:30:00Z",
  "source": "web-ui",
  "user": "admin",
  "text": "ตรวจ health service",
  "attachments": [
    {
      "filename": "report.txt",
      "safe_filename": "report.txt",
      "size": 1024,
      "content_type": "text/plain",
      "stored_path": "data/uploads/abc123_report.txt",
      "category": "text",
      "analysis_mode": "text-extract"
    }
  ],
  "result": {
    "export_path": "data/exports/abc123.prompt.md",
    "final_report": "# รายงาน Health Check\n...",
    "report_source": "hermes_http",
    "verification_status": "PASS",
    "agent_run_id": "run-uuid",
    "agent_run_status": "completed_report_saved",
    "agent_run_mode": "hermes_http",
    "hermes_endpoint": "https://hermes.example.com/***",
    "hermes_http_status": 200,
    "hermes_response_format": "A",
    "fallback_mode": null,
    "fallback_reason": null,
    "response_received_at": "2026-05-13T10:05:00Z"
  },
  "agent_events": [
    {
      "timestamp": "2026-05-13T10:00:00Z",
      "agent": "system",
      "role": "system",
      "action": "task_created",
      "message": "Task สร้างจาก web-ui"
    }
  ]
}
```

---

## Immutability Rules

- `task_id`, `created_at`, `source`, `user`, `text`, `attachments` — **ไม่แก้หลัง create**
- `status` — เปลี่ยนได้เฉพาะตาม state machine ด้านบน
- `result` — **merge เท่านั้น** (ห้าม overwrite เพื่อป้องกัน final_report หาย)
- `agent_events` — **append-only** (ห้ามลบหรือแก้ event เก่า)
