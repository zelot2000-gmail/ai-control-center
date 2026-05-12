---
title: "Embedding Models"
category: llm
tags: [embedding, vector, similarity, qdrant, text2vec]
status: stable
updated: 2026-05-12
---

# Embedding Models

## Embedding คืออะไร

Embedding = การแปลง text → vector (ตัวเลข) เพื่อให้เปรียบเทียบ semantic similarity ได้

```
"วิธีแก้ bug Python" → [0.12, -0.34, 0.89, ..., 0.01]  (768 หรือ 1536 มิติ)
"Python error fix"   → [0.11, -0.33, 0.87, ..., 0.02]  (ใกล้เคียงกัน = similar)
"ข้าวต้มกุ้ง"        → [-0.45, 0.12, -0.23, ..., 0.67] (ห่างกัน = unrelated)
```

---

## Model ที่ใช้ใน ai-control-center

| Model | Dimensions | Provider | เหมาะกับ |
|-------|-----------|----------|---------|
| `text-embedding-3-small` | 1536 | OpenAI | ภาษาอังกฤษ, cost-effective |
| `text-embedding-3-large` | 3072 | OpenAI | English, high accuracy |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | HuggingFace | ภาษาไทย + multilingual |
| `BAAI/bge-m3` | 1024 | HuggingFace | multilingual SOTA |

**Default**: `paraphrase-multilingual-mpnet-base-v2` (รองรับภาษาไทย)

---

## Similarity Metrics

| Metric | สูตร | เหมาะกับ |
|--------|------|---------|
| Cosine Similarity | cos(A,B) = A·B / (‖A‖‖B‖) | text similarity ทั่วไป |
| Dot Product | A·B | normalized vectors |
| Euclidean Distance | ‖A-B‖ | embedding ที่ไม่ normalize |

**Qdrant default**: Cosine Similarity (สำหรับ text)

---

## Chunking ก่อน Embed

ไม่ควร embed เอกสารทั้งหมดในครั้งเดียว — ต้องแบ่งเป็น chunk ก่อน

ดูรายละเอียด → [rag/chunking-strategy.md](../rag/chunking-strategy.md)

---

## Batch Embedding

```python
# ประหยัดกว่า embed ทีละอัน
texts = ["text1", "text2", ..., "text100"]
embeddings = model.encode(texts, batch_size=32)
```

---

## ข้อควรระวัง

- **Language mismatch**: ถ้า embed ภาษาไทยด้วย model English-only → ผลลัพธ์แย่มาก
- **Dimension mismatch**: ต้องใช้ model เดิมสำหรับ query และ index (ห้ามผสมกัน)
- **Embedding drift**: ถ้าเปลี่ยน model ต้อง re-index ทั้งหมด
- **Max token limit**: แต่ละ embedding model มี max input tokens (512–8192) — text ที่ยาวกว่าจะถูก truncate

---

## การเลือก Embedding Model

```
มีภาษาไทย?
  └─ ใช่ → paraphrase-multilingual หรือ BAAI/bge-m3
  └─ ไม่ → text-embedding-3-small (cost) หรือ text-embedding-3-large (quality)

ต้องการ accuracy สูงสุด?
  └─ ใช่ → BAAI/bge-m3 หรือ text-embedding-3-large

ต้องการ speed/cost?
  └─ ใช่ → text-embedding-3-small หรือ paraphrase-multilingual-mpnet-base-v2
```
