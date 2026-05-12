---
title: "Qdrant Notes"
category: rag
tags: [qdrant, vector-db, collection, index, filter]
status: stable
updated: 2026-05-12
---

# Qdrant Notes

## ทำไมถึงเลือก Qdrant

ดูรายละเอียดการตัดสินใจใน [decisions/why-qdrant.md](../decisions/why-qdrant.md)

สรุป: open-source, self-hosted, รองรับ hybrid search, Rust-based (เร็ว), Docker-friendly

---

## Setup

```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
    - "6334:6334"  # gRPC
  volumes:
    - qdrant_data:/qdrant/storage
```

**REST API**: http://localhost:6333  
**Dashboard**: http://localhost:6333/dashboard  
**gRPC**: localhost:6334

---

## Collection Management

### สร้าง Collection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient("localhost", port=6333)

client.create_collection(
    collection_name="wiki",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
```

### Collections ในระบบ

| Collection | Dimensions | Distance | เนื้อหา |
|-----------|-----------|----------|---------|
| `wiki` | 768 | Cosine | docs/wiki content |
| `logs` | 768 | Cosine | system logs |
| `tasks` | 768 | Cosine | task history |

---

## CRUD Operations

### Upsert Points

```python
from qdrant_client.models import PointStruct

client.upsert(
    collection_name="wiki",
    points=[
        PointStruct(
            id=1,
            vector=embedding,
            payload={
                "text": chunk_text,
                "source": "docs/wiki/rag/chunking-strategy.md",
                "category": "rag",
                "tags": ["chunking", "rag"],
            }
        )
    ]
)
```

### Search

```python
results = client.search(
    collection_name="wiki",
    query_vector=query_embedding,
    limit=5,
    score_threshold=0.70,
    with_payload=True,
)

for r in results:
    print(f"Score: {r.score:.3f} | {r.payload['source']}")
    print(r.payload['text'][:200])
```

### Filtered Search

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

results = client.search(
    collection_name="wiki",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[FieldCondition(key="category", match=MatchValue(value="rag"))]
    ),
    limit=5,
)
```

---

## Index และ Performance

### Payload Index
สร้าง index บน payload field ที่ filter บ่อย

```python
client.create_payload_index(
    collection_name="wiki",
    field_name="category",
    field_schema="keyword",
)
```

### HNSW Parameters (Vector Index)

```python
client.update_collection(
    collection_name="wiki",
    hnsw_config=HnswConfigDiff(
        m=16,           # connections per node (ยิ่งสูง = แม่นยำกว่า แต่ช้ากว่า)
        ef_construct=100  # build time accuracy
    )
)
```

---

## Backup และ Restore

```bash
# Snapshot collection
curl -X POST http://localhost:6333/collections/wiki/snapshots

# List snapshots
curl http://localhost:6333/collections/wiki/snapshots

# Download snapshot
curl -O http://localhost:6333/collections/wiki/snapshots/<snapshot-name>

# Restore
curl -X POST "http://localhost:6333/collections/wiki/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "/qdrant/snapshots/<snapshot-name>"}'
```

---

## Troubleshooting

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| Collection not found | ยังไม่ได้ ingest | รัน ingest endpoint |
| Low scores | Model mismatch | ตรวจว่า embed model เดียวกัน |
| Out of memory | Payload ใหญ่เกิน | ลด payload, ใช้ payload index |
| Slow search | ไม่มี HNSW index | สร้าง index |
| Duplicates | ไม่ได้ deduplicate | ใช้ deterministic ID จาก content hash |

---

## API Reference

REST API ครบที่ http://localhost:6333/openapi  
Python client: `pip install qdrant-client`
