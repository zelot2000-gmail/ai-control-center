---
id: rag-ingest-workflow
mode: workflow
autonomy_level: 2
risk_level: 2
approval_required: false
responsible_agents: [rag-curator, observer]
---

# RAG Ingest Workflow

## วัตถุประสงค์
Ingest เอกสารเข้า Qdrant vector store อย่างมีขั้นตอนและตรวจสอบได้

## เมื่อใช้ Workflow Mode
งานนี้มีขั้นตอนชัดเจน ทำซ้ำได้ ผลลัพธ์คาดเดาได้ → ใช้ Workflow ไม่ใช้ Agent

## Steps

### Step 1: validate_files
- ตรวจว่าไฟล์มีอยู่จริงใน `data/documents/`
- ตรวจ format: `.txt`, `.md`, `.pdf`
- ตรวจ encoding: UTF-8
- **Expected output**: รายการไฟล์ valid / invalid
- **Fail condition**: ไม่มีไฟล์ → หยุดและ report

### Step 2: normalize_text
- ลบ whitespace ซ้ำ
- ผ่าน TTO API (`POST /optimize`) เพื่อ normalize Thai text
- **Expected output**: text normalized ทุกไฟล์
- **Fail condition**: TTO API ไม่ตอบ → fallback ใช้ text ดิบ

### Step 3: chunk_documents
- แบ่งเป็น chunks ขนาด 512 tokens, overlap 64 tokens
- บันทึก metadata: source_file, chunk_num, created_at
- **Expected output**: chunk list พร้อม metadata
- **Fail condition**: chunk size 0 → report และหยุด

### Step 4: create_embeddings
- เรียก `POST /ingest` ของ RAG API
- ใช้ model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Expected output**: embedding vectors ทุก chunk
- **Fail condition**: RAG API timeout → retry 3 ครั้ง แล้ว report

### Step 5: upsert_qdrant
- upsert vectors เข้า Qdrant collection `aicc_docs`
- **Expected output**: upsert count ตรงกับ chunk count
- **Fail condition**: Qdrant error → report และไม่ทำลาย collection เดิม

### Step 6: verify_search
- เรียก `POST /search` ด้วย query ที่เกี่ยวข้องกับเอกสาร
- ตรวจว่า score > 0.5 อย่างน้อย 1 ผลลัพธ์
- **Expected output**: search result มี source ตรงกับไฟล์ที่ ingest
- **Fail condition**: score ต่ำเกินไป → แนะนำ rechunking

### Step 7: write_ingest_report
- บันทึกผลใน `data/exports/ingest-report-{timestamp}.json`
- สรุป: files ingested, chunks created, embeddings, verify score, errors

## Accountability Log
```yaml
owner_agent: rag-curator
tool_usage_log: [rag-api/ingest, tto-api/optimize, qdrant/upsert]
verification_log: [rag-api/search]
rollback_plan: ไม่ต้อง rollback — Qdrant upsert ไม่ทับของเดิมถ้า ID ต่างกัน
```
