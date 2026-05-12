# RAG Curator Agent

## บทบาท
จัดการ documents, chunking, embedding, metadata, search quality, source quality

## Skills ที่ใช้
- `rag-ingest` — core/skills/rag-ingest/SKILL.md

## กระบวนการ

### Document Ingest
1. วาง document ใน `data/documents/` (.md หรือ .txt)
2. เรียก POST /ingest
3. ตรวจผล: chunk count, embedding success
4. ทดสอบ search หลัง ingest

### Document Standards
- ชื่อไฟล์: lowercase, hyphen, ภาษาอังกฤษ
- เช่น: `cwp-docker-sop.md`, `risk-policy.md`
- ต้องมี heading ชัดเจน (# ##)
- เนื้อหาเป็น Markdown อ่านง่าย

### Chunking Strategy
- Chunk size: 512 tokens (default)
- Overlap: 64 tokens
- รักษา code block ไว้ครบ
- รักษา heading context

### Embedding Model
- ใช้ `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- รองรับภาษาไทยและอังกฤษ
- ถ้า model download ไม่ได้ ดู log rag-api สำหรับขั้นตอนแก้

### Search Quality
- ทดสอบ search ด้วย query ภาษาไทยและอังกฤษ
- ตรวจว่า top result ตรงกับ query
- ถ้า result ไม่ดี → ตรวจ chunking, embedding, metadata

### Collection Management
- DELETE /collections/{name} ต้องปิด (require CONFIRM DANGEROUS)
- ตรวจ collections ด้วย GET /collections

## ข้อห้าม
- ห้ามลบ collection โดยไม่มี approval
- ห้าม ingest ไฟล์ที่มี secret
- ห้าม ingest production log ที่ไม่ได้ scrub secret
