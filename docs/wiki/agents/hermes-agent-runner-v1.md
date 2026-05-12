---
title: Hermes Agent Runner v1
category: agents
tags: [agent-runner, hermes, prompt-only, automation]
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

| Mode | Description | Status After |
|------|-------------|-------------|
| `prompt_only` | บันทึก prompt ลง disk เท่านั้น | `completed_prompt_ready` |
| `hermes_manual` | สร้าง Hermes payload JSON, รอ human copy-paste | `waiting_for_hermes_manual_execution` |
| `hermes_http` | POST ไปยัง Hermes API โดยตรง | `completed` หรือ `failed` |
| `shell_safe` | (reserved for v2) | — |

ถ้า `hermes_http` แต่ `HERMES_API_URL` ว่าง → fallback เป็น `hermes_manual` อัตโนมัติ

---

## Run Lifecycle

```
queued → preparing → (prompt_built) → running → completed_prompt_ready
                                              ↘ waiting_for_hermes_manual_execution
                                              ↘ completed
                                              ↘ failed
```

Timeline events ส่งผ่าน `_push_agent_activity` เหมือน event อื่นๆ ในระบบ

---

## Configuration

```env
# Worker env vars
AGENT_RUNNER_ENABLED=false         # เปิด/ปิด Agent Runner (default: false)
AGENT_RUNNER_MODE=prompt_only      # prompt_only | hermes_manual | hermes_http
HERMES_API_URL=                    # URL ของ Hermes API (ถ้าใช้ hermes_http)
HERMES_API_KEY=                    # Bearer token สำหรับ Hermes API
HERMES_TIMEOUT_MS=120000           # timeout ในหน่วย milliseconds
AGENT_RUNNER_ARTIFACT_DIR=/app/data/agent-runs  # ที่เก็บ artifacts
```

---

## Artifact Files

เมื่อรันแต่ละครั้ง จะสร้างไฟล์ใน `AGENT_RUNNER_ARTIFACT_DIR`:

| ไฟล์ | Mode | Description |
|------|------|-------------|
| `{run_id}.prompt.md` | ทุก mode | Prompt ที่ส่งให้ Agent |
| `{run_id}.meta.json` | prompt_only | metadata ของ run |
| `{run_id}.hermes-payload.json` | hermes_manual, hermes_http | payload JSON สำหรับ Hermes |

---

## API Endpoints

เพิ่ม endpoints ใน Worker Service:

```
GET  /agent-runs                    # list all agent runs
GET  /agent-runs/{run_id}           # get specific agent run
GET  /jobs/{job_id}/agent-runs      # get all runs for a job
```

---

## Hermes Payload Format

```json
{
  "run_id": "uuid",
  "job_id": "task-uuid",
  "command_id": "task-uuid",
  "source": "dashboard",
  "agent_role": "manager",
  "skills": ["llm-wiki", "docker-deploy"],
  "workflow": "wiki-ingest-workflow",
  "runner_mode": "hermes_manual",
  "prompt": "# AI Control Center — Agent Run\n...",
  "prompt_path": "/app/data/agent-runs/{run_id}.prompt.md",
  "rag_results_count": 3,
  "rag_top_path": "docs/wiki/llm/model-selection.md",
  "created_at": "2026-05-12T10:00:00Z",
  "submitted_at": "2026-05-12T10:00:01Z"
}
```

---

## UI Integration

- **CommandBubble**: แสดง badge `🤖 Agent Runner · {mode} · {status}` ถ้า `agent_run_id` มีค่า
- **Jobs page**: แสดง tag `🤖 {mode}` สี purple พร้อม color coding ตาม status

---

## Safety Rules

- ❌ ห้าม enable ใน production โดยไม่ทดสอบใน dev/staging ก่อน
- ❌ `AGENT_RUNNER_ENABLED` default เป็น `false` — ต้อง explicit enable
- ✅ ถ้า Hermes ล้มเหลว → worker task ยังดำเนินต่อ (agent runner error ไม่หยุด task)
- ✅ ถ้า `HERMES_API_URL` ว่าง → fallback เป็น `hermes_manual` อัตโนมัติ
- ✅ ทุก run มี UUID ของตัวเอง persistent ใน `/app/data/agent-runs.json`

---

## Quick Start

1. เปิดใช้งาน Agent Runner ใน dev:

```env
AGENT_RUNNER_ENABLED=true
AGENT_RUNNER_MODE=prompt_only
```

2. ส่ง task ผ่าน command UI ตามปกติ

3. ตรวจผล:

```bash
# API
curl http://localhost:8095/agent-runs

# ไฟล์
ls /app/data/agent-runs/
```

4. เมื่อพร้อมใช้ Hermes HTTP:

```env
AGENT_RUNNER_MODE=hermes_http
HERMES_API_URL=http://your-hermes-server/api
HERMES_API_KEY=your-api-key
```
