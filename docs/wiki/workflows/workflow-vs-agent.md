---
title: "Workflow vs Agent"
category: workflows
tags: [workflow, agent, hybrid, decision, mode-selection]
status: stable
updated: 2026-05-12
---

# Workflow vs Agent

## ทำไมต้องแยก

- **Workflow**: deterministic, predictable, auditable, ถูก
- **Agent**: flexible, creative, reasoning, แพงกว่า

ใช้ Workflow ก่อนเสมอ ถ้า Agent ทำแทนได้โดยไม่เพิ่มคุณภาพ → ห้ามใช้ Agent

---

## Workflow คืออะไร

Sequence ของ steps ที่ fixed และ defined ล่วงหน้า

```yaml
# ตัวอย่าง health-check-workflow
steps:
  1. check_docker_status
  2. ping_all_services
  3. verify_responses
  4. generate_report
  5. notify_if_failure
```

**ลักษณะ**:
- แต่ละ step ชัดเจน, วัดได้
- ไม่ต้อง LLM ทุก step (บาง step เป็น pure code)
- ผลลัพธ์แน่นอน (deterministic)
- ตรวจสอบได้ง่าย (audit trail ชัดเจน)

---

## Agent คืออะไร

LLM ที่มี tools และตัดสินใจเองว่าจะทำอะไรต่อ

```
Agent รับ task → คิด → เลือก tool → รัน → ดูผล → คิดต่อ → ...
```

**ลักษณะ**:
- Flexible — adapt ตามสถานการณ์
- ต้องใช้ LLM ทุก step
- ผลลัพธ์ไม่ตายตัว (non-deterministic)
- ตรวจสอบยากกว่า (ต้องดู reasoning chain)

---

## Decision Table

| ถ้างานมีลักษณะนี้ | Mode |
|----------------|------|
| ขั้นตอนรู้อยู่แล้ว, แค่ทำซ้ำๆ | **Workflow** |
| Input/Output format กำหนดได้ชัดเจน | **Workflow** |
| ต้องการ audit trail ที่ชัดเจน | **Workflow** |
| ประหยัด cost | **Workflow** |
| ต้องการ creativity / reasoning | **Agent** |
| ปัญหาซับซ้อน, unknowns มาก | **Agent** |
| ต้องการ tool use แบบ dynamic | **Agent** |
| ทั้ง workflow + reasoning | **Hybrid** |

---

## Hybrid Mode

ใช้เมื่องานมีส่วนที่ fixed และส่วนที่ต้องการ reasoning

```
Workflow phase:
  1. Export task data → prompt
  2. Prepare context

Agent phase:
  3. LLM analyzes + reasons
  4. LLM generates report

Workflow phase:
  5. Validate report format
  6. Save to task result
  7. Notify
```

---

## ตัวอย่าง Mode Selection

```
"ตรวจ health service ทุกตัว"
→ Workflow (health-check-workflow) — ขั้นตอนชัดเจน

"วิเคราะห์ว่า service A ช้าลงเพราะอะไร"
→ Agent (research mode) — ต้องการ reasoning

"deploy feature ใหม่"
→ Hybrid — workflow สำหรับ deploy steps, agent สำหรับ verify + rollback decision

"ingest wiki documents"
→ Workflow (wiki-ingest-workflow) — ขั้นตอนชัดเจน
```

---

## Workflow Registry

Workflows ลงทะเบียนใน `core/workflows/index.json`

```json
{
  "workflows": [
    {
      "id": "health-check-workflow",
      "triggers": ["health", "ตรวจ service"],
      "steps": ["check_docker", "ping_services", "report"]
    },
    {
      "id": "wiki-ingest-workflow",
      "triggers": ["ingest wiki", "อัปเดต knowledge"],
      "steps": ["scan_docs", "chunk", "embed", "upsert", "verify"]
    }
  ]
}
```

---

## กฎสำคัญ

- **ห้ามใช้ Agent ถ้า Workflow ทำได้** — ทั้งในแง่ cost และ predictability
- **ห้ามสร้าง Agent หลายตัวเพื่อให้ดู impressive** — ถ้า 1 agent ทำได้ก็พอ
- **Hybrid ต้องระบุว่า phase ไหน workflow และ phase ไหน agent**
