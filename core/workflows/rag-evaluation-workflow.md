---
id: rag-evaluation-workflow
mode: hybrid
autonomy_level: 2
risk_level: 1
approval_required: false
responsible_agents: [rag-curator, research, observer]
---

# RAG Evaluation Workflow

## วัตถุประสงค์
ตรวจคุณภาพ RAG: retrieval accuracy, chunk quality, embedding effectiveness

## Steps

### Step 1: prepare_eval_questions [hybrid → agent]
Agent สร้าง 5-10 คำถามที่ควรตอบได้จากเอกสารที่ ingest ไว้
- คำถามต้องหลากหลาย: factual, conceptual, procedural
- บันทึก expected_answer สำหรับแต่ละคำถาม

### Step 2: run_search [workflow]
```http
POST http://127.0.0.1:8090/search
{
  "query": "{question}",
  "top_k": 5,
  "score_threshold": 0.3
}
```
- รัน search ทุก eval question
- บันทึก: results, scores, sources

### Step 3: inspect_sources [workflow]
- ตรวจว่า source ของ top result ตรงกับ expected document
- ตรวจว่า chunk text มีข้อมูลที่ถามจริง
- Flag: chunk ที่ score สูงแต่ content ไม่เกี่ยว (false positive)

### Step 4: score_relevance [hybrid → agent]
Agent ให้คะแนน 0-5 ต่อแต่ละ result:
- 5: ตอบคำถามได้ตรง
- 3: มีข้อมูลบางส่วน
- 0: ไม่เกี่ยวข้อง

คำนวณ: `mean_relevance_score`, `precision@1`, `precision@3`

### Step 5: detect_bad_chunks [hybrid → agent]
Agent วิเคราะห์:
- Chunks ที่สั้นเกินไป (< 50 tokens) — อาจตัด context
- Chunks ที่ยาวเกินไป (> 600 tokens) — อาจ dilute signal
- Chunks ที่มีแต่ whitespace หรือ metadata
- Chunks ที่ duplicate กัน

### Step 6: recommend_chunking_or_embedding_fix [hybrid → agent]
ถ้า mean_relevance_score < 3.0:
- แนะนำ: ปรับ chunk_size หรือ chunk_overlap
- แนะนำ: เปลี่ยน embedding model
- แนะนำ: เพิ่ม metadata filtering

### Step 7: rag_quality_report
```yaml
rag_evaluation:
  timestamp: "..."
  collection: aicc_docs
  total_documents: 0
  eval_questions: 0
  mean_relevance_score: 0.0
  precision_at_1: 0.0
  precision_at_3: 0.0
  bad_chunks_found: 0
  recommendations: []
  status: excellent | good | needs_improvement | poor
```

## Accountability Log
```yaml
owner_agent: rag-curator
tool_usage_log: [rag-api/search, rag-api/collections]
verification_log: [relevance-scoring, chunk-inspection]
rollback_plan: N/A — read-only evaluation
```
