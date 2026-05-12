# Skill: RAG Ingest

## วัตถุประสงค์
นำ document เข้า Qdrant vector DB พร้อม chunking และ embedding

## Supported File Types
- .md (Markdown) — primary
- .txt (Plain text) — primary
- .pdf — planned (ยังไม่พร้อมใน v1)

## Chunking
- Chunk size: 512 tokens
- Overlap: 64 tokens
- รักษา heading context
- รักษา code block ครบ

## Embedding Model
- paraphrase-multilingual-MiniLM-L12-v2
- รองรับภาษาไทย + อังกฤษ

## Ingest Steps
1. อ่านไฟล์จาก path
2. แบ่ง chunk
3. สร้าง embedding
4. บันทึกลง Qdrant collection

## Search
- Semantic search ด้วย vector similarity
- รองรับ query ภาษาไทยและอังกฤษ
- limit: 5 (default)

## Error Handling
- Model download ล้มเหลว → fallback message + ขั้นตอนแก้
- Qdrant unreachable → retry 3 ครั้ง → error response
- File not found → 404 response
