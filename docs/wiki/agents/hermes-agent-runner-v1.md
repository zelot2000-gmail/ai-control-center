---
title: Hermes Agent Runner v1
category: agents
tags: [agent-runner, hermes, hermes-http, prompt-only, automation, fallback]
status: stable
updated: 2026-05-13
---

# Hermes Agent Runner v1

## Overview

Agent Runner v1 เป็น layer ที่อยู่บน Worker Service สำหรับจัดการการรัน Agent โดยอัตโนมัติหลังจาก Prompt ถูกสร้างเรียบร้อยแล้ว

ออกแบบให้ **ปิดโดย default** (`AGENT_RUNNER_ENABLED=false`) เพื่อให้ระบบทำงานเหมือนเดิมจนกว่าจะพร้อม enable

---

## Architecture

```
Worker → build prompt → [if AGENT_RUNNER_ENABLED] → run_agent()
                                                          ↓
                                               pick adapter by mode
                                                  ↙    ↓    ↘
                                       prompt_only  hermes_manual  hermes_http
                                          ↓              ↓              ↓
                                     save .md      save payload    POST to Hermes
                                                   wait for human   handle response
```

### Python Package

```
services/worker/app/agent_runner/
├── __init__.py          # re-exports: run_agent, AGENT_RUNNER_ENABLED
├── config.py            # env vars
├── types.py             # RunnerMode, RunStatus, AgentRun, RunResult
├── storage.py           # JSON persistence → /app/data/agent-runs.json
├── prompt_builder.py    # build_agent_prompt()
├── runner.py            # orchestrator: run_agent()
└── adapters/
    ├── prompt_only.py   # save prompt + meta to disk
    ├── hermes_manual.py # save prompt + Hermes payload JSON, wait for human
    └── hermes_http.py   # POST to Hermes API, fallback to hermes_manual
```

---

## Runner Modes

| Mode | Description | Status หลัง run |
|------|-------------|----------------|
| `prompt_only` | บันทึก prompt ลง disk เท่านั้น | `completed_prompt_ready` |
| `hermes_manual` | สร้าง Hermes payload JSON, รอ human copy-paste | `waiting_for_hermes_manual_execution` |
| `hermes_http` | POST ไปยัง Hermes API โดยตรง | `completed_report_saved` / `hermes_response_unrecognized` / `waiting_hermes` |

Fallback chain สำหรับ `hermes_http`:
- `HERMES_API_URL` ว่าง → fallback เป็น `hermes_manual` (`fallback_reason: "no_hermes_url"`)
- Network error / timeout → fallback เป็น `HERMES_FALLBACK_MODE` (`fallback_reason: "network_error"` / `"timeout"`)
- Response format ไม่รู้จัก → status `hermes_response_unrecognized` (ไม่ fallback — ต้องตรวจสอบ manual)
- HTTP 4xx (ยกเว้น 429) → fallback ทันที (`fallback_reason: "http_4xx"`)

---

## Hermes HTTP Flow

```
Task Created
    ↓
Worker picks up
    ↓
Build Prompt (RAG context injected)
    ↓
_can_run_agent() — Approval Gate
    ├─ BLOCKED: production / execute / risk≥3 / hermes_http+risk>1 without approval
    │       → status: blocked_approval_required
    │       → รอ PATCH /tasks/{id}/approval { approval_status: "approved" }
    └─ ALLOWED
         ↓
    POST to HERMES_API_URL
         ↓
    _post_with_retry() — retry on 429/5xx/network
         ├─ Success → parse response format (A/B/C/D/E)
         │       ├─ Recognized → save .report.md + .report.json
         │       │       → push_event: hermes_report_saved
         │       │       → status: completed_report_saved
         │       └─ Unrecognized → save .hermes-response.json only
         │               → status: hermes_response_unrecognized
         └─ Failure → _do_fallback() → hermes_manual
                 → status: waiting_for_hermes_manual_execution
```

---

## Response Formats (A–E)

Hermes API สามารถ return ได้ 5 รูปแบบ — ระบบ auto-detect ทั้งหมด:

| Format | Detection Key | ตัวอย่าง |
|--------|--------------|---------|
| **A** | มี `final_report` ที่ root | `{"final_report": "...", "summary": "...", "verification_status": "PASS"}` |
| **B** | มี `content` string ที่ root | `{"content": "รายงาน..."}` |
| **C** | มี `message.content` | `{"message": {"content": "..."}}` |
| **D** | OpenAI-style choices | `{"choices": [{"message": {"content": "..."}}]}` |
| **E** | `data` wrapper | `{"data": {"final_report": "...", "verification_status": "PASS"}}` |

Format ไม่ตรงใดเลย → `hermes_response_unrecognized`, บันทึก `.hermes-response.json` เพื่อ debug

---

## Run Lifecycle (Agent Runner States)

```
queued
  └─ preparing
       └─ running
            ├─ blocked_approval_required        ← ต้อง approve ก่อน
            │       └─ [approved] → ← กลับมา run ใหม่
            ├─ completed_prompt_ready            ← prompt_only mode
            ├─ waiting_for_hermes_manual_execution ← hermes_manual mode
            ├─ waiting_hermes                   ← hermes_http ส่งแล้ว รอ response (interim)
            ├─ completed_report_saved            ← hermes_http สำเร็จ
            ├─ hermes_response_unrecognized      ← hermes_http response parse ไม่ได้
            └─ failed                           ← error อื่นๆ
```

Timeline events ที่ส่งผ่าน `push_event`:

| Event | เกิดเมื่อ |
|-------|---------|
| `agent_run_started` | เริ่ม run_agent() |
| `agent_prompt_built` | build prompt เสร็จ |
| `agent_run_blocked` | approval gate block |
| `agent_run_approved` | ได้รับ approval |
| `hermes_request_sent` | POST ส่งออกไปแล้ว |
| `hermes_response_received` | ได้รับ response |
| `hermes_report_saved` | บันทึก report เสร็จ |
| `hermes_fallback_triggered` | fallback เริ่มทำงาน |
| `agent_run_completed` | run เสร็จสมบูรณ์ |

---

## Artifact Files

เมื่อรันแต่ละครั้ง จะสร้างไฟล์ใน `AGENT_RUNNER_ARTIFACT_DIR` (`/app/data/agent-runs/`):

| ไฟล์ | Mode | Description |
|------|------|-------------|
| `{run_id}.prompt.md` | ทุก mode | Prompt ที่ build สำหรับ Agent |
| `{run_id}.hermes-payload.json` | hermes_manual, hermes_http | payload ที่จะส่ง (หรือส่งไปแล้ว) |
| `{run_id}.hermes-response.json` | hermes_http เสมอ | raw response จาก Hermes (ทุก response รวม error) |
| `{run_id}.report.md` | hermes_http (สำเร็จ) | final_report แบบ Markdown |
| `{run_id}.report.json` | hermes_http (สำเร็จ) | structured report + metadata |

`.hermes-response.json` สร้างทุกครั้ง ไม่ว่าจะสำเร็จหรือไม่ — ใช้เพื่อ debug format ที่ไม่รู้จัก

---

## Configuration

```env
# เปิด/ปิด Agent Runner
AGENT_RUNNER_ENABLED=false         # default: false

# Runner mode
AGENT_RUNNER_MODE=prompt_only      # prompt_only | hermes_manual | hermes_http

# Hermes HTTP
HERMES_API_URL=                    # URL ของ Hermes endpoint
HERMES_API_KEY=                    # Bearer token (ห้าม log ห้าม commit)
HERMES_TIMEOUT_SECONDS=120         # timeout ในหน่วย seconds (httpx)
HERMES_TIMEOUT_MS=120000           # timeout ในหน่วย ms (legacy compat)
HERMES_FALLBACK_MODE=hermes_manual # mode ที่ใช้เมื่อ hermes_http ล้มเหลว

# Retry
HERMES_RETRY_ATTEMPTS=1            # จำนวนครั้ง retry (0 = ไม่ retry)
HERMES_RETRY_BACKOFF_SECONDS=2     # รอกี่วินาทีก่อน retry

# Artifact storage
AGENT_RUNNER_ARTIFACT_DIR=/app/data/agent-runs
```

---

## Hermes Payload Format (v1)

```json
{
  "run_id": "uuid",
  "task_id": "task-uuid",
  "source": "dashboard",
  "agent_role": "manager",
  "skills": ["llm-wiki", "docker-deploy"],
  "workflow": "wiki-ingest-workflow",
  "prompt": "# AI Control Center — Agent Run\n...",
  "metadata": {
    "runner_mode": "hermes_http",
    "prompt_path": "/app/data/agent-runs/{run_id}.prompt.md",
    "rag_results_count": 3,
    "rag_top_path": "docs/wiki/llm/model-selection.md",
    "created_at": "2026-05-13T10:00:00Z",
    "submitted_at": "2026-05-13T10:00:01Z"
  }
}
```

---

## AgentRun Data Model

```python
@dataclass
class AgentRun:
    run_id: str
    task_id: str
    mode: str                      # prompt_only | hermes_manual | hermes_http
    status: str                    # RunStatus value
    created_at: str
    completed_at: str | None
    report_saved_at: str | None
    fallback_mode: str | None      # mode ที่ใช้จริงถ้า fallback
    fallback_reason: str | None    # "no_hermes_url" | "network_error" | "timeout" | "http_4xx"
    hermes_endpoint: str | None    # URL ที่ POST (masked secrets)
    hermes_http_status: int | None # HTTP status code จาก Hermes
    hermes_response_format: str | None  # "A" | "B" | "C" | "D" | "E" | "unrecognized"
    response_received_at: str | None    # ISO timestamp
    verification_status: str | None     # "PASS" | "WARNING" | "FAIL" | "UNKNOWN"
```

---

## Verification Status Rules

`verification_status` ถูก normalize เป็น uppercase เสมอ:

| ค่าจาก Hermes | ค่าที่บันทึก |
|--------------|------------|
| `"pass"`, `"ok"`, `"success"` | `"PASS"` |
| `"warning"`, `"warn"` | `"WARNING"` |
| `"fail"`, `"failed"`, `"error"` | `"FAIL"` |
| ค่าอื่น / ว่าง | `"UNKNOWN"` |

ค่าที่ผู้ใช้กรอกเอง (Save Report form): normalize ด้วย `normalize_verification_status()` — ถ้าไม่รู้จักจะเก็บเป็น `""` (ไม่บังคับ UNKNOWN)

---

## Safety Rules

- ❌ ห้าม log `HERMES_API_KEY` — ต้องใช้ Bearer header โดยตรง ไม่เก็บ key ใน artifact
- ❌ ห้าม bypass approval gate — `_can_run_agent()` ต้องผ่านก่อนทุกครั้ง
- ❌ ห้าม run hermes_http ใน production environment โดยไม่มี approval
- ✅ Hermes URL ที่บันทึก จะ mask query-param secrets โดยอัตโนมัติ (`_mask_endpoint_url()`)
- ✅ ถ้า Hermes ล้มเหลว → fallback โดยอัตโนมัติ ไม่หยุด task
- ✅ `.hermes-response.json` บันทึกทุกครั้ง — ใช้สำหรับ audit และ debug
- ✅ `AGENT_RUNNER_ENABLED` default เป็น `false` — ต้อง explicit enable

---

## Approval Gate Rules

`_can_run_agent()` จะ **block** และ return `blocked_approval_required` เมื่อ:

| เงื่อนไข | ต้อง approve |
|---------|------------|
| `environment == "production"` | ✅ เสมอ |
| `mode == "execute"` | ✅ เสมอ |
| `risk_level >= 3` | ✅ เสมอ |
| `runner_mode == "hermes_http"` AND `risk_level > 1` | ✅ |

การ approve: `PATCH /tasks/{task_id}/approval` ด้วย body `{"approval_status": "approved"}`
หลัง approve, task จะ re-queue ให้ worker รันต่อโดยอัตโนมัติ

---

## API Endpoints (Worker)

```
GET  /agent-runs                    # list all agent runs
GET  /agent-runs/{run_id}           # get specific agent run
GET  /jobs/{job_id}/agent-runs      # get all runs for a job
POST /agent-runs/{run_id}/report    # sync Hermes report (manual submit)
```

---

## UI Integration

- **CommandBubble**: badge `🤖 Agent Runner · {mode} · {status}` ถ้า `agent_run_id` มีค่า; แสดง `verification_status` badge (`PASS`/`WARNING`/`FAIL`/`UNKNOWN`)
- **Jobs page**: tag `🤖 {mode}` สี purple + color coding ตาม agent_run_status
- **Agent Run Detail modal**: แสดง hermes_http_status, hermes_response_format, fallback_reason, response_received_at, hermes URL (masked), info box สำหรับ waiting/error states
- Copy/Save buttons แสดงเมื่อ: `completed_prompt_ready`, `waiting_hermes`, `hermes_manual_pending`, `hermes_response_unrecognized`

---

## Verification Examples

### Example 1: Mock Hermes สำเร็จ (Format A)

```bash
# Start mock Hermes server (host port 20199)
# Sends: {"final_report": "...", "verification_status": "pass"}

# Create task with hermes_http enabled
curl -X POST http://localhost:8088/tasks \
  -H "X-Gateway-Secret: change_me" \
  -H "Content-Type: application/json" \
  -d '{"text": "test hermes", "environment": "dev", "mode": "plan"}'

# Expected: agent_run_status = "completed_report_saved"
# Expected: verification_status = "PASS" (uppercase)
# Expected: hermes_response_format = "A"
# Files: {run_id}.hermes-response.json, {run_id}.report.md, {run_id}.report.json
```

### Example 2: Fallback Manual (HERMES_API_URL ว่าง)

```bash
# ตั้ง AGENT_RUNNER_MODE=hermes_http แต่ HERMES_API_URL=""
# Expected: agent_run_status = "waiting_for_hermes_manual_execution"
# Expected: fallback_mode = "hermes_manual"
# Expected: fallback_reason = "no_hermes_url"
# Files: {run_id}.hermes-payload.json (ไม่มี .hermes-response.json)
```

### Example 3: Production Approval Gate

```bash
# Create task with environment=production, mode=execute
# Expected: agent_run_status = "blocked_approval_required"

# Approve:
curl -X PATCH http://localhost:8088/tasks/{task_id}/approval \
  -H "X-Gateway-Secret: change_me" \
  -H "Content-Type: application/json" \
  -d '{"approval_status": "approved"}'

# Expected: task re-runs, agent_run proceeds
```
