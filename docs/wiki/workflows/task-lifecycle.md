---
title: "Task Lifecycle"
category: workflows
tags: [task, status, lifecycle, state-machine, transition]
status: stable
updated: 2026-05-12
---

# Task Lifecycle

## Status State Machine

```
pending
  └─ [worker picks up] ──→ running
                              └─ [export done] ──→ exporting
                                                      └─ [export saved] ──→ exported
                                                                              ├─ [user clicks Run Agent] ──→ agent_running
                                                                              │                                  └─ [agent done] ──→ completed
                                                                              └─ [skips agent] ──→ completed
```

### Status Definitions

| Status | ความหมาย | ทำอะไรได้ |
|--------|---------|----------|
| `pending` | รอ worker รับงาน | ยกเลิก |
| `running` | Worker กำลัง process | ดู logs |
| `exporting` | กำลัง export prompt | ดู logs |
| `exported` | Prompt พร้อม — รอ user Run Agent | View Prompt, Run Agent |
| `agent_running` | Agent กำลัง generate report | View Prompt, Save Report (draft) |
| `completed` | Task สำเร็จ — report saved | View Report, View Prompt, Timeline |
| `failed` | เกิด error | View logs, retry |
| `cancelled` | ผู้ใช้ยกเลิก | — |

---

## Timeline Events

แต่ละ task มี `agent_events` array บันทึก history

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

---

## API Endpoints

### Create Task

```http
POST /tasks
Content-Type: application/json

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

### Save Final Report

```http
POST /tasks/{task_id}/report
{
  "report_source": "manager",
  "final_report": "# รายงาน\n..."
}
```

---

## Task Data Structure

```json
{
  "task_id": "abc123",
  "status": "completed",
  "created_at": "2026-05-12T10:00:00Z",
  "updated_at": "2026-05-12T10:30:00Z",
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
    "report_source": "manager",
    "verification_status": "PASS"
  },
  "agent_events": [
    {
      "timestamp": "2026-05-12T10:00:00Z",
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
