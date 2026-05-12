---
title: "Serena MCP"
category: mcp
tags: [mcp, serena, code-intelligence, semantic, navigation, refactor]
status: stable
updated: 2026-05-12
---

# Serena MCP

## คืออะไร

Serena MCP = Code Intelligence Layer สำหรับ AI  
ให้ AI "เข้าใจ" codebase ในระดับ semantic โดยไม่ต้องอ่านทุกไฟล์

**ไม่ใช่ production runtime** — ใช้ในกระบวนการ AI-assisted development เท่านั้น

---

## ทำไมถึงเลือก Serena

ดูรายละเอียดใน [decisions/why-serena-mcp.md](../decisions/why-serena-mcp.md)

สรุป: ลด token cost ของ code navigation 80%, ให้ precision สูงกว่า grep, รองรับ polyglot

---

## ความสามารถ

| Tool | คำอธิบาย |
|------|----------|
| `find_symbol` | ค้นหา function/class/variable จากชื่อ |
| `find_references` | หาทุกที่ที่ symbol ถูกใช้ |
| `get_definition` | ดู definition ของ symbol |
| `get_file_outline` | โครงสร้าง symbols ในไฟล์ |
| `search_codebase` | Full-text + semantic search ทั้ง repo |
| `rename_symbol` | Rename ทั้ง codebase อย่างปลอดภัย |
| `impact_analysis` | ถ้าแก้ X จะกระทบอะไรบ้าง |
| `get_call_graph` | Call graph ของ function |

---

## Setup

```bash
# Clone Serena
git clone https://github.com/oraios/serena

# ติดตั้ง dependencies
cd serena && pip install -e .

# Config ใน claude_desktop_config.json
{
  "mcpServers": {
    "serena": {
      "command": "python",
      "args": ["-m", "serena.mcp_server", "--project", "/path/to/your/project"]
    }
  }
}
```

---

## การใช้งานจริง

### หา function definition

```
find_symbol("process_task")
→ services/worker/app/main.py:245 — async def process_task(task_id, task_data)
```

### หาว่า endpoint ถูกเรียกที่ไหน

```
find_references("create_task")
→ apps/web/pages/command.vue:89
→ services/mobile-gateway/app/main.py:156
→ tests/test_gateway.py:23
```

### Impact analysis ก่อน refactor

```
impact_analysis("TaskResult")
→ Used in: main.py:89, 156, 203 | models.py:45 | command.vue:112
→ Breaking change: yes — used in 3 API endpoints
```

---

## Serena vs RAG vs Grep

| | Serena | RAG | Grep |
|---|--------|-----|------|
| **Source** | Source code | Documents | ทุกไฟล์ |
| **Understanding** | Semantic | Semantic | Lexical |
| **Speed** | กลาง | เร็ว | เร็วมาก |
| **Context quality** | สูงมาก | สูง | ต่ำ |
| **เหมาะกับ** | Code nav, refactor | Knowledge retrieval | Quick search |

---

## Rules for Agents

```
ก่อนแก้ function → find_symbol + find_references ก่อน
ก่อน rename → impact_analysis ก่อน
ก่อน delete class → find_references ก่อน (ถ้ายังมีใช้ → ห้ามลบ)
ก่อน merge PR → impact_analysis บน changed symbols
```

---

## Agents ที่ใช้ Serena

- **programmer**: code navigation, implementation
- **qa**: test coverage, impact check
- **security**: find sensitive function usage
- **manager**: impact analysis only (ไม่ edit code เอง)

---

## ข้อจำกัด

- ต้องการ Language Server / index — ช้าในการ startup ครั้งแรก
- รองรับ: Python, JavaScript/TypeScript, Go, Rust, Java
- ไม่รองรับ: binary files, minified JS, generated code
- Index ต้องสร้างใหม่เมื่อโครงสร้าง repo เปลี่ยนมาก
