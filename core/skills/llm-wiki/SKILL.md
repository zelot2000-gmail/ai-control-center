# Skill: llm-wiki — LLM Wiki Knowledge Base

**skill_id**: llm-wiki  
**agents**: rag-curator, manager, programmer, observer, research  
**risk_level**: 1 (read/write wiki — no destructive ops)  
**environment**: all  

---

## วัตถุประสงค์

ใช้เพื่อ:
- อ่านและค้นหาความรู้จาก `docs/wiki/`
- เพิ่มเอกสารใหม่เข้า wiki
- ingest wiki เข้า RAG เพื่อให้ agent ค้นหาได้
- อ้างอิง decision, pattern, SOP จาก wiki ในการทำงาน

---

## โครงสร้าง Wiki

```
docs/wiki/
├── llm/        LLM knowledge, model notes, prompt patterns
├── rag/        RAG strategy, chunking, embedding, evaluation
├── mcp/        MCP server notes, tool rules
├── ops/        Runbook, SOP, troubleshooting, health check
└── decisions/  ADR — Architecture Decision Records
```

---

## วิธีใช้ในงาน

### 1. อ่านจาก Wiki (เมื่อต้องการ context)
```
ค้นหาใน docs/wiki/ ก่อนเขียนโค้ดหรือออกแบบ
ใช้ RAG search: GET http://rag-api:8090/search
query: หัวข้อที่ต้องการ เช่น "RAG chunking strategy"
```

### 2. เพิ่มเอกสารใหม่
```
สร้างไฟล์ .md ในโฟลเดอร์ที่เหมาะสม
ใส่ front-matter: title, category, tags, status
เขียนเนื้อหาชัดเจน มี recommendation
```

### 3. Ingest เข้า RAG
```
copy docs/wiki/ → data/documents/wiki/
POST http://rag-api:8090/ingest {"path": "/app/data/documents/wiki"}
verify: POST http://rag-api:8090/search {"query": "...", "limit": 3}
```

---

## กฎการใช้งาน

- **ห้ามเก็บ secret / API key** ใน wiki
- **ทุก decision ต้องมีเหตุผล** ก่อน commit
- **เอกสารทดลอง** → `docs/research/` ไม่ใช่ `docs/wiki/`
- **หลังแก้ wiki** ต้อง ingest ใหม่เพื่อให้ RAG อัปเดต
- **ห้ามเพิ่มเอกสารที่ยังไม่ verified** เข้า wiki โดยตรง

---

## Accountability

```yaml
เมื่อแก้ไข wiki:
  - บันทึก: owner, changed_files, reason, rag_ingested, date
เมื่อ ingest:
  - verify search ทุกครั้งหลัง ingest
  - บันทึก: collection_size, sample_query_result
```
