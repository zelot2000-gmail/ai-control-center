# LLM Wiki — AI Control Center Knowledge Base

**ประเภท**: Knowledge Base กลาง  
**เวอร์ชัน**: 1.0.0  
**ผู้ดูแล**: rag-curator, manager  

---

## LLM Wiki คืออะไร

LLM Wiki เป็น **Knowledge Base กลาง** ของโปรเจกต์ ai-control-center  
ใช้เก็บความรู้ที่ agent ทุกตัวควรเข้าถึงได้ผ่าน RAG Search

| หมวด | เนื้อหา |
|------|---------|
| `llm/` | ความรู้ LLM, model comparison, prompt engineering, context management |
| `rag/` | RAG strategy, chunking, embedding, retrieval pattern, evaluation |
| `mcp/` | MCP server notes, tool rules, Chrome DevTools, Serena MCP |
| `ops/` | Runbook, troubleshooting, deployment SOP, health check notes |
| `decisions/` | Architecture Decision Records (ADR), ทำไมถึงเลือก X, trade-offs |

---

## กฎของ LLM Wiki

- **ห้ามเก็บ secret / API key** — เก็บได้เฉพาะ placeholder เช่น `your_key_here`
- **ทุก decision ต้องมีเหตุผล** — ใน `decisions/` ต้องระบุ context, options, rationale
- **ทุก research ต้องมี recommendation** — `reject` | `keep watching` | `PoC only` | `staging` | `production-ready`
- **เอกสารที่พร้อมใช้งาน** → `docs/wiki/`
- **เอกสารทดลอง / PoC** → `docs/research/`

---

## โครงสร้างโฟลเดอร์

```
docs/wiki/
├── README.md              ← ไฟล์นี้
├── llm/
│   └── README.md          ← LLM knowledge, prompt pattern, model notes
├── rag/
│   └── README.md          ← RAG strategy, chunking rules, evaluation
├── mcp/
│   └── README.md          ← MCP server notes, Serena MCP, Chrome DevTools
├── ops/
│   └── README.md          ← Runbook, SOP, troubleshooting
└── decisions/
    └── README.md          ← ADR list
```

---

## วิธีเพิ่มเอกสารเข้า docs/wiki

```bash
# 1. สร้างไฟล์ในหมวดที่เหมาะสม
nano docs/wiki/llm/prompt-patterns.md

# 2. ใส่ front-matter metadata (ช่วย RAG retrieval)
---
title: "Prompt Patterns"
category: llm
tags: [prompt, few-shot, chain-of-thought]
status: stable
---

# 3. เขียนเนื้อหาด้วย Markdown มาตรฐาน

# 4. Commit
git add docs/wiki/
git commit -m "wiki: add prompt-patterns"
```

**ข้อควรระวัง**:
- ใช้ภาษาชัดเจน อ่านง่าย บน mobile ได้
- หัวข้อไม่ควรลึกเกิน H3
- ตัวอย่างโค้ดใส่ใน fenced code blocks

---

## วิธี Ingest docs/wiki เข้า RAG

```bash
# copy ไปยัง data/documents ที่ container mount
cp -r docs/wiki/ data/documents/wiki/

# ingest ผ่าน RAG API
curl -X POST http://127.0.0.1:8090/ingest \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/data/documents/wiki"}'

# ตรวจสอบ
curl -X POST http://127.0.0.1:8090/search \
  -H "Content-Type: application/json" \
  -d '{"query": "RAG chunking strategy", "limit": 3}'
```

หรือใช้ workflow:
```bash
curl -X POST http://127.0.0.1:8088/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "user": "admin",
    "text": "ingest wiki documents",
    "environment": "dev",
    "mode": "execute"
  }'
```

---

## Serena MCP คืออะไร

Serena MCP เป็น **Code Intelligence Layer** — ไม่ใช่ production runtime  
ใช้เพื่อให้ AI เข้าใจ codebase แบบ semantic ก่อนแก้โค้ด

| ความสามารถ | รายละเอียด |
|-----------|-----------|
| Semantic navigation | หา function/class/symbol จากชื่อหรือ pattern |
| Reference finding | หาว่า symbol ถูกใช้ที่ไหนบ้าง |
| Impact analysis | ถ้าแก้ X จะกระทบ Y, Z ไหม |
| Context collection | รวบรวม relevant files โดยไม่อ่านทั้ง repo |
| Refactor assist | เปลี่ยนชื่อ symbol ทั้ง codebase อย่างปลอดภัย |

**Agents ที่ใช้**: programmer, qa, security, research, manager (เฉพาะ impact analysis)

---

## Serena MCP ต่างจาก RAG อย่างไร

| | RAG | Serena MCP |
|---|-----|-----------|
| **Source** | เอกสาร, wiki, SOP, notes | Source code |
| **Unit** | Document chunk | Symbol, function, class, file |
| **เหมาะกับ** | ค้นหาความรู้, SOP, policy | Code navigation, impact analysis |
| **Output** | ย่อหน้าที่เกี่ยวข้อง | File paths, line numbers, symbol refs |
| **เมื่อไรใช้** | ต้องการข้อมูล domain knowledge | ต้องการเข้าใจหรือแก้ไข code |

**กฎสำคัญ**:
- ❌ ห้ามใช้ RAG แทน Serena เมื่อเป็นงาน code navigation
- ❌ ห้ามใช้ Serena แทน RAG เมื่อเป็นงาน knowledge/wiki/document retrieval

---

## Serena MCP ใช้เมื่อไร

```
ต้องการแก้ function → ใช้ Serena หา definition + references ก่อน
ต้องการรู้ว่า class ถูก import ที่ไหน → ใช้ Serena
ต้องการรู้ว่า endpoint มี middleware อะไร → ใช้ Serena
ต้องการรู้ว่ามีไฟล์ที่เกี่ยวกับ payment ไหน → ใช้ RAG
ต้องการรู้ว่า RAG chunking ควรทำอย่างไร → ใช้ RAG (wiki)
ต้องการ refactor service ใหม่ → ใช้ Serena ทำ impact analysis ก่อน
```

---

## Accountability

เมื่อแก้ไขเอกสารใน wiki ให้บันทึก:

```yaml
owner: [agent/human]
changed_files: [list]
reason: [ทำไมถึงเพิ่ม/แก้ไข]
rag_ingested: [yes/no]
date: YYYY-MM-DD
```
