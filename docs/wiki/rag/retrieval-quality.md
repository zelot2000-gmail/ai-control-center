---
title: "RAG Retrieval Quality"
category: rag
tags: [retrieval, quality, reranking, evaluation, mrr, recall]
status: stable
updated: 2026-05-12
---

# RAG Retrieval Quality

## Metrics หลัก

| Metric | คำอธิบาย | เป้าหมาย |
|--------|----------|---------|
| Recall@K | สัดส่วน relevant doc ที่อยู่ใน top-K | ≥ 0.8 |
| Precision@K | สัดส่วน retrieved ที่ relevant จริง | ≥ 0.7 |
| MRR | Mean Reciprocal Rank — ตำแหน่งเฉลี่ยของ doc ที่ถูก | ≥ 0.75 |
| NDCG@K | Normalized Discounted Cumulative Gain | ≥ 0.8 |
| Latency | เวลาดึงข้อมูล | ≤ 500ms |

---

## ปัญหาที่พบบ่อยและวิธีแก้

### 1. Recall ต่ำ — หา doc ที่เกี่ยวข้องไม่เจอ

สาเหตุ:
- Query และ document ใช้คำต่างกัน (vocabulary mismatch)
- Embedding model ไม่รองรับภาษา

แก้ด้วย:
- **Hybrid Search**: รวม vector search + BM25 keyword search
- Query expansion: เพิ่ม synonym หรือ paraphrase ก่อน search

```python
# Hybrid search ใน Qdrant
results = client.search(
    collection_name="wiki",
    query_vector=embed(query),
    query_filter=Filter(must=[FieldCondition(key="category", match=MatchValue(value="rag"))]),
    limit=10,
    with_payload=True,
)
```

### 2. Precision ต่ำ — ดึงข้อมูลที่ไม่เกี่ยวมาเยอะ

สาเหตุ:
- Score threshold ต่ำเกินไป
- Chunk ใหญ่เกินไป ทำให้มี noise

แก้ด้วย:
- เพิ่ม `score_threshold` (เช่น 0.70)
- ลด chunk size
- เพิ่ม metadata filter

### 3. Context Window ไม่พอ — ดึงมาแต่ใช้ไม่ได้

แก้ด้วย:
- Reranking: ใช้ cross-encoder เลือกเฉพาะ top-3 จาก top-20
- Compression: สรุป chunk ก่อนใส่ใน context

---

## Hybrid Search Architecture

```
Query
  ├─ Dense Vector Search (Qdrant)     → top-20 by cosine similarity
  └─ Sparse/BM25 Search (keyword)     → top-20 by keyword match
           ↓
     Score Fusion (RRF หรือ weighted)
           ↓
     Reranker (cross-encoder)         → top-5
           ↓
     LLM Context
```

---

## Evaluation Pipeline

```bash
# สร้าง test set
python eval/create_rag_testset.py --wiki-path docs/wiki/ --output eval/testset.json

# รัน retrieval
python eval/run_retrieval.py --testset eval/testset.json --top-k 5

# คำนวณ metrics
python eval/compute_metrics.py --results eval/results.json
```

---

## Reranking

Reranking = ใช้ model ที่แม่นยำกว่า (cross-encoder) เพื่อ re-score top-K results

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
scores = reranker.predict([(query, doc) for doc in retrieved_docs])
reranked = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)
top_docs = [doc for doc, _ in reranked[:3]]
```

---

## Score Threshold ที่แนะนำ

| Collection | Min Score | เหตุผล |
|-----------|----------|--------|
| wiki (knowledge) | 0.70 | ต้องการ precision สูง |
| logs | 0.60 | keyword match สำคัญกว่า |
| code | 0.65 | semantic ใกล้เคียงอาจ mislead |

---

## การตรวจสอบคุณภาพ Retrieval

```bash
# ทดสอบ search
curl -X POST http://127.0.0.1:8090/search \
  -H "Content-Type: application/json" \
  -d '{"query": "chunking strategy for markdown files", "limit": 5}'

# ดู collection stats
curl http://127.0.0.1:8090/collections
```

ถ้า score ของผลลัพธ์แรก < 0.70 → แปลว่า doc นั้นอาจไม่ถูก index หรือ query คือ out-of-domain
