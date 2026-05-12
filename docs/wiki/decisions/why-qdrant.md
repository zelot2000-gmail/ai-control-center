---
title: "ADR: ทำไมถึงเลือก Qdrant"
category: decisions
tags: [adr, qdrant, vector-db, decision, architecture]
status: stable
updated: 2026-05-12
---

# ADR: ทำไมถึงเลือก Qdrant เป็น Vector Database

## Status

**Accepted** — ใช้ใน production

## Context

โปรเจกต์ ai-control-center ต้องการ vector database สำหรับ:
1. เก็บ embedding ของ wiki documents
2. Semantic search สำหรับ RAG
3. Log และ task history retrieval

## Options ที่พิจารณา

| Option | License | Self-hosted | Performance | Thai support |
|--------|---------|------------|-------------|-------------|
| **Qdrant** | Apache 2.0 | ✅ | สูง (Rust) | ✅ (ขึ้นกับ model) |
| Chroma | Apache 2.0 | ✅ | ปานกลาง (Python) | ✅ |
| Weaviate | BSD | ✅/Cloud | สูง | ✅ |
| Pinecone | Proprietary | ❌ (Cloud only) | สูง | ✅ |
| pgvector | PostgreSQL | ✅ | ปานกลาง | ✅ |
| Milvus | Apache 2.0 | ✅ | สูงมาก | ✅ |

## Decision

เลือก **Qdrant**

## เหตุผล

1. **Self-hosted + Open Source**: ข้อมูล wiki, task, log ไม่ออกนอก infrastructure
2. **Performance**: เขียนด้วย Rust — รับ concurrent query ได้ดีโดยไม่ต้อง scale ซับซ้อน
3. **Docker-friendly**: รัน container เดียว ไม่ต้องการ dependencies ซับซ้อน
4. **Hybrid Search**: รองรับ dense + sparse (BM25) ใน query เดียว
5. **Filtering**: payload filter ที่ยืดหยุ่น — filter by category, tags, date
6. **Python client**: `qdrant-client` ใช้งานง่าย, async support
7. **REST + gRPC**: มี web dashboard, REST API สำหรับ debug

## Trade-offs

| ข้อดี | ข้อเสีย |
|-------|---------|
| เร็ว, self-hosted | Ecosystem เล็กกว่า Chroma/Pinecone |
| Rust = low memory leak | Less community content |
| REST dashboard | ต้องการ persistent volume |

## Chroma vs Qdrant

Chroma เป็นทางเลือก ถ้า:
- ต้องการ setup ง่ายกว่า (เริ่มต้นได้ใน 10 บรรทัด)
- ทีมคุ้นเคย Python ecosystem มากกว่า

เลือก Qdrant เพราะ performance ใน concurrent load สูงกว่า และ built-in Web UI

## Consequences

- **ดี**: Fast retrieval, horizontal scalable (ถ้าต้องการ cluster)
- **เสีย**: ต้องดูแล persistent volume และ snapshot เอง
- **Mitigation**: มี backup script และ Qdrant snapshot API

## Review

ทบทวนการตัดสินใจนี้ถ้า:
- Vector count > 10 ล้าน record
- ต้องการ multi-tenancy per user
- ต้องการ real-time streaming ingestion
