# Architecture Decision Records (ADR)

**หมวด**: decisions  
**สถานะ**: active  

เก็บ decisions สำคัญที่เกี่ยวกับ architecture, tools, และ patterns ของ ai-control-center

---

## Format ของ ADR

```markdown
# ADR-NNN: [ชื่อ decision]

**สถานะ**: proposed | accepted | superseded | deprecated
**วันที่**: YYYY-MM-DD
**ผู้ตัดสิน**: [agent/human]

## Context
[ทำไมถึงต้องตัดสินใจ]

## Options ที่พิจารณา
1. Option A — pros/cons
2. Option B — pros/cons

## Decision
[เลือก option ไหน และทำไม]

## Consequences
[ผลที่ตามมา — ทั้งดีและไม่ดี]
```

---

## ADR ที่มีอยู่

| ADR | หัวข้อ | สถานะ |
|-----|--------|-------|
| ADR-001 | Docker-first, no CWP containerization | accepted |
| ADR-002 | Qdrant as vector DB (vs Pinecone/Weaviate) | accepted |
| ADR-003 | FastAPI + Python 3.11 for all services | accepted |
| ADR-004 | Hybrid Workflow-Agent execution model | accepted |
| ADR-005 | tasks.json flat file (interim, migrate to Postgres) | accepted |
| ADR-006 | Serena MCP as code intelligence layer | accepted |
