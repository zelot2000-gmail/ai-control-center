# Wiki Ingest Workflow

**workflow_id**: wiki-ingest-workflow  
**mode**: workflow  
**autonomy_level**: 2  
**risk_level**: 2  
**approval_required**: false  
**agents**: rag-curator, observer  
**skill**: llm-wiki, rag-ingest  

---

## วัตถุประสงค์

Ingest เอกสารจาก `docs/wiki/` เข้า Qdrant Vector DB  
เพื่อให้ agent ทุกตัวสามารถค้นหาความรู้จาก wiki ผ่าน RAG ได้

---

## ขั้นตอน

### Step 1 — validate_wiki_files
```
ตรวจสอบ docs/wiki/ มีไฟล์ .md ที่ valid
ตรวจ front-matter: title, category
ตรวจว่าไม่มี secret/API key ใน content
```

### Step 2 — copy_to_documents
```
cp -r docs/wiki/ data/documents/wiki/
ตรวจว่า data/documents/wiki/ สร้างสำเร็จ
```

### Step 3 — normalize_wiki_text
```
POST http://tto-api:8091/normalize
ส่ง content ของแต่ละไฟล์
ลด whitespace, normalize ภาษาไทย
```

### Step 4 — ingest_to_qdrant
```
POST http://rag-api:8090/ingest
body: {"path": "/app/data/documents/wiki"}
ตรวจ response: {"status": "ok", "ingested": N}
```

### Step 5 — verify_search
```
ทดสอบด้วย sample queries:
POST http://rag-api:8090/search {"query": "RAG strategy", "limit": 3}
POST http://rag-api:8090/search {"query": "MCP rules", "limit": 3}
ตรวจว่าได้ผลลัพธ์ที่เกี่ยวข้อง score > 0.5
```

### Step 6 — write_ingest_report
```
สรุปผล:
- จำนวนไฟล์ที่ ingest
- collection size
- sample query results
- warnings (ถ้ามี)
```

---

## Rollback Plan

```bash
# ถ้า ingest ผิดพลาด ให้ลบ collection แล้ว ingest ใหม่
# ห้าม drop collection โดยไม่มี backup
# ตรวจ qdrant collection ก่อน rollback:
curl http://127.0.0.1:6333/collections
```

---

## Accountability Log Template

```yaml
workflow: wiki-ingest-workflow
owner_agent: rag-curator
trigger: manual / scheduled
files_ingested: []
collection_name: aicc_documents
ingested_count: 0
sample_queries_ok: true
warnings: []
verified_by: observer
completed_at: ""
```
