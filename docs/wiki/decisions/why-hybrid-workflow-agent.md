---
title: "ADR: ทำไมถึงใช้ Hybrid Workflow-Agent Architecture"
category: decisions
tags: [adr, workflow, agent, hybrid, architecture, orchestration]
status: stable
updated: 2026-05-12
---

# ADR: ทำไมถึงใช้ Hybrid Workflow-Agent Architecture

## Status

**Accepted** — core design principle ของระบบ

## Context

ระบบ ai-control-center ต้องการ orchestration layer ที่:
1. ทำงานซ้ำๆ ได้อย่างน่าเชื่อถือ (health check, backup, ingest)
2. รับมือกับ task ที่ซับซ้อนและต้องการ reasoning (debug, research)
3. ควบคุม cost ได้ (ไม่ใช้ LLM ทุก step)
4. Auditability ชัดเจน

## Options ที่พิจารณา

### Option A: Pure Agent (LangChain/AutoGPT style)
ทุกอย่างผ่าน LLM ตลอด — LLM ตัดสินใจทุก step

**ข้อดี**: ยืดหยุ่นสูงสุด
**ข้อเสีย**: แพง, ไม่ predictable, hallucination risk สูง, audit ยาก

### Option B: Pure Workflow (n8n/Airflow style)
กำหนดทุก step ล่วงหน้า — ไม่มี LLM ตัดสินใจ

**ข้อดี**: ถูก, reliable, audit ง่าย
**ข้อเสีย**: ยืดหยุ่นน้อย, รับมือ edge case ไม่ได้

### Option C: Hybrid (เลือกตาม task type)
workflow สำหรับงาน deterministic + agent สำหรับงานที่ต้องการ reasoning

**ข้อดี**: สมดุลระหว่าง reliability, flexibility, cost
**ข้อเสีย**: ซับซ้อนกว่า — ต้องกำหนด routing rules ชัดเจน

## Decision

เลือก **Hybrid Architecture (Option C)**

```
Workflow-first → Agent-when-needed → Hybrid by design → Accountability always
```

## เหตุผล

1. **Cost Control**: health check 100 ครั้งต่อวัน — ถ้าใช้ Agent ทุกครั้งจะแพงมาก
2. **Reliability**: production operations ต้องการ determinism
3. **Flexibility**: research, debug tasks ต้องการ LLM reasoning
4. **Auditability**: workflow steps มี log ชัดเจน + agent reasoning ก็ต้อง log
5. **Risk Management**: workflow ผ่าน validation ก่อน → agent ได้รับ context ที่ clean

## Routing Rules (CLAUDE.md)

```
health, check, backup, ingest, verify, lint, test → workflow
วิเคราะห์, debug, root cause, research, R&D → agent
deploy, production, restart, database → hybrid
```

## Accountability Layer

ทั้ง workflow และ agent ต้อง:
- Log ทุก action พร้อม timestamp, agent, result
- ผ่าน RTK (Risk-Task-Knowledge) validation ก่อน destructive action
- มี approval requirement ตาม autonomy level

## Consequences

- ทีมต้องเข้าใจทั้ง 2 paradigm
- ต้องดูแล workflow registry + agent skill registry
- ได้ทั้ง predictability ของ workflow และ power ของ agent

## Review

ทบทวนถ้า:
- LLM cost ลดลงมากพอ → อาจ shift ไป pure agent
- Task type เปลี่ยน → update routing rules
