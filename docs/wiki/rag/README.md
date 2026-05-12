# RAG Strategy Knowledge Base

**หมวด**: rag  
**สถานะ**: active  

เก็บ strategy, pattern และ decision เกี่ยวกับ RAG ใน ai-control-center

---

## หัวข้อที่ควรมี

| ไฟล์ | เนื้อหา | สถานะ |
|------|---------|-------|
| `chunking-strategy.md` | chunk size, overlap, Thai text chunking | TODO |
| `embedding-models.md` | MiniLM vs BGE-M3, tradeoffs | TODO |
| `retrieval-patterns.md` | similarity search, MMR, hybrid search | TODO |
| `evaluation-guide.md` | วิธีวัดคุณภาพ RAG: precision, recall, MRR | TODO |
| `ingest-checklist.md` | checklist ก่อน ingest เอกสารใหม่ | TODO |

---

## Stack ปัจจุบัน

- **Vector DB**: Qdrant v1.9.2
- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Chunk size**: ตาม RAG API default (ดู `services/rag-api/`)
- **Ingest path**: `data/documents/` → `POST /ingest`
- **Search**: `POST /search {"query": "...", "limit": N}`
