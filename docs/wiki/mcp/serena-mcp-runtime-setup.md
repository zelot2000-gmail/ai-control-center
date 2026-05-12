---
title: "Serena MCP Runtime Setup Guide"
category: mcp
tags: [serena, mcp, setup, runtime, config, verify]
status: stable
updated: 2026-05-12
---

# Serena MCP Runtime Setup Guide

## Serena MCP คืออะไร (ในเชิง Runtime)

Serena MCP เป็น **runtime tool** — ไม่ใช่ RAG, ไม่ใช่ database  
ทำงานในฐานะ MCP Server ที่รัน Language Server อยู่เบื้องหลัง  
ให้ AI เรียก semantic code navigation tools ผ่าน MCP protocol ได้ real-time

| | RAG | Serena MCP |
|--|-----|-----------|
| **Type** | Knowledge retrieval | Runtime code intelligence tool |
| **Source** | Documents, wiki | Source code (live) |
| **Protocol** | REST API | MCP (stdio/SSE) |
| **Latency** | ~50-200ms (search) | ~100-500ms (symbol lookup) |
| **Offline** | ❌ ต้องการ Qdrant | ✅ รันบน local ได้ |

---

## ใช้กับอะไรได้บ้าง

| Client | วิธี Connect |
|--------|------------|
| **Claude Code (CLI)** | `claude_desktop_config.json` |
| **Windsurf** | MCP settings ใน IDE |
| **Hermes** | `hermes_config.json` MCP section |
| **Custom Agent** | MCP client library (Python/TS) |

---

## Prerequisites

```bash
# ต้องการ
python >= 3.10
git
# ภาษาที่ต้องการ Language Server:
# Python → pyright หรือ pylsp
# TypeScript → typescript-language-server
# Go → gopls
# Rust → rust-analyzer
```

---

## Installation

```bash
# 1. Clone Serena
git clone https://github.com/oraios/serena
cd serena

# 2. ติดตั้ง
pip install -e ".[dev]"

# หรือ uv (แนะนำ)
uv pip install -e ".[dev]"

# 3. ตรวจสอบ
python -m serena.mcp_server --help
```

---

## Config (Placeholder — อย่า commit real path)

### Claude Code / Claude Desktop

```json
// %APPDATA%\Claude\claude_desktop_config.json  (Windows)
// ~/Library/Application Support/Claude/claude_desktop_config.json  (Mac)
{
  "mcpServers": {
    "serena": {
      "command": "python",
      "args": [
        "-m", "serena.mcp_server",
        "--project", "/path/to/your/project"
      ]
    }
  }
}
```

**แทน `/path/to/your/project`** ด้วย path จริง เช่น:
- Windows (WSL): `/mnt/e/Project/laragon/www/ai-control-center`
- Windows native: `E:\\Project\\laragon\\www\\ai-control-center`

### Windsurf

```json
// ~/.windsurf/mcp_servers.json
{
  "serena": {
    "command": "python",
    "args": ["-m", "serena.mcp_server", "--project", "/path/to/project"]
  }
}
```

### Hermes Agent

```yaml
# hermes_config.yaml
mcp_servers:
  serena:
    command: python
    args: ["-m", "serena.mcp_server", "--project", "/path/to/project"]
    timeout: 30
```

---

## Verify ว่า Serena ใช้งานได้

### 1. Test รัน standalone

```bash
cd /path/to/serena
python -m serena.mcp_server \
  --project /path/to/ai-control-center \
  --stdio
```

ถ้า start สำเร็จจะเห็น:
```
INFO: Serena MCP Server starting...
INFO: Indexing project: /path/to/ai-control-center
INFO: Index complete — symbols: 1234
INFO: Ready (stdio mode)
```

### 2. Test ผ่าน Claude Code

```bash
# เปิด Claude Code
claude

# ทดสอบ tool call
# พิมพ์: "ใช้ Serena หา function process_task ในโปรเจกต์"
```

ผลลัพธ์ที่คาดหวัง:
```
find_symbol("process_task")
→ services/worker/app/main.py:661 — async def process_task(req: TaskRequest)
```

### 3. Test ผ่าน command.vue

1. เปิด http://localhost:3000/command
2. พิมพ์ task: `"@Programmer วิเคราะห์ bug หน้า command.vue โดยใช้ Serena MCP ก่อนแก้"`
3. ส่ง → รอ Worker export
4. คลิก "View Prompt"
5. ตรวจสอบว่า Prompt มี:
   - `Skills: serena-mcp`
   - `Workflow: code-intelligence-workflow`
   - Section `## Code Intelligence Plan`

---

## วิธีใช้ Serena MCP ใน Coding Workflow

### กรณีที่ 1: Bug Fix

```
User → "@Programmer วิเคราะห์ bug หน้า jobs.vue และใช้ Serena MCP ก่อนแก้"
  ↓
Worker → เพิ่ม skill serena-mcp, workflow code-intelligence-workflow
  ↓
Programmer Agent ใน Prompt:
  1. find_symbol("loadTasks") → หา definition
  2. find_references("taskId") → หาว่าใช้ที่ไหน
  3. impact_analysis("buildTaskMeta") → ตรวจผลกระทบ
  4. แก้เฉพาะไฟล์ที่ Serena ระบุ
```

### กรณีที่ 2: Refactor

```
User → "@Programmer refactor TaskResult schema ใช้ Serena impact analysis"
  ↓
Worker → code-intelligence-workflow + serena-mcp + qa-verify
  ↓
Step 4 (impact_analysis): พบว่า TaskResult ถูกใช้ใน 5 ไฟล์
  → plan: แก้ 5 ไฟล์ → risk level 2
  → QA verify หลัง refactor
```

### กรณีที่ 3: Code Review ก่อน Merge

```
User → "@QA code review PR command.vue changes ด้วย Serena"
  ↓
QA Agent:
  1. get_file_outline("command.vue") → ดู structure
  2. find_references("attachedFiles") → ตรวจ scope
  3. search_codebase("emit('send'") → หา consistency
  4. สร้าง review report
```

---

## Safety Rules

- **ห้าม** commit real project path ลง config file (ใช้ placeholder)
- **ห้าม** ให้ Serena อ่าน `.env` หรือ `secrets/` folder
- **ห้าม** ใช้ Serena บน production server โดยตรง
- **ห้าม** run Serena ด้วย production database credentials ในสภาพแวดล้อมเดียวกัน
- **ต้อง** ใช้ Serena เฉพาะใน local / dev / staging environment
- **ต้อง** ทำ impact analysis ก่อนแก้ไฟล์ทุกครั้ง

---

## Troubleshooting

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| `Symbol not found` | Index ยังไม่สร้าง | รอ indexing หรือ restart Serena |
| `Connection timeout` | Serena ไม่ได้รัน | ตรวจ MCP server process |
| `Language server not found` | ไม่ได้ติดตั้ง LSP | `pip install python-lsp-server` |
| Slow first query | Index building | ปกติ — หลังครั้งแรกจะเร็วขึ้น |
| `Project path not found` | Config ผิด | ตรวจ path ใน config |

---

## Index Refresh

เมื่อ repo มีการเปลี่ยนแปลงมาก (merge, add module):

```bash
# Restart Serena MCP server เพื่อ rebuild index
# ใน Claude Code: restart MCP server จาก settings
# หรือ kill และ start ใหม่
pkill -f "serena.mcp_server"
# Claude Code จะ restart อัตโนมัติ
```
