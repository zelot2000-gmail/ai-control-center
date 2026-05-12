---
title: "RAG Chunking Strategy"
category: rag
tags: [chunking, splitting, overlap, token, retrieval]
status: stable
updated: 2026-05-12
---

# RAG Chunking Strategy

## ทำไมต้อง Chunk

LLM มี context limit → ไม่สามารถส่งเอกสารทั้งหมดได้
Embedding model มี max token limit → ต้อง chunk ก่อน embed
Chunk ขนาดเหมาะสม → retrieval แม่นยำขึ้น

---

## Chunk Size Guidelines

| ประเภทเอกสาร | Chunk Size | Overlap | เหตุผล |
|-------------|-----------|---------|--------|
| เอกสารเทคนิค/SOP | 512 tokens | 64 tokens | paragraph-level context |
| Code | 256 tokens | 32 tokens | function/class-level |
| Wiki / Knowledge | 256–512 | 50–100 | concept-level |
| PDF ยาว | 1024 tokens | 128 tokens | page-level context |
| Q&A / FAQ | 128–256 | 0 | self-contained |

**Default ในระบบ**: 512 tokens, 64 overlap

---

## Chunking Strategies

### 1. Fixed-Size Chunking
แบ่งตาม token count ที่กำหนด

```python
def fixed_chunk(text, chunk_size=512, overlap=64):
    tokens = tokenize(text)
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk = tokens[i:i + chunk_size]
        chunks.append(detokenize(chunk))
    return chunks
```

ข้อดี: ง่าย, เร็ว
ข้อเสีย: อาจตัดกลางประโยค/ย่อหน้า

### 2. Recursive Character Splitting
แบ่งตาม separator hierarchy: `\n\n` → `\n` → `.` → ` `

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n\n", "\n", ".", " "]
)
chunks = splitter.split_text(text)
```

ข้อดี: รักษา paragraph boundary
ข้อเสีย: chunk size ไม่สม่ำเสมอ

### 3. Semantic Chunking
แบ่งตาม semantic boundary (ใช้ embedding similarity ตรวจ topic shift)

ข้อดี: chunk ที่ coherent ที่สุด
ข้อเสีย: ช้ากว่า, ต้องการ embedding model

### 4. Markdown-Aware Splitting
แบ่งตาม heading structure (`#`, `##`, `###`)

```python
# แบ่งตาม H2 heading
sections = re.split(r'\n## ', text)
```

**เหมาะกับ**: docs/wiki ที่มี structured markdown

---

## Metadata ที่ควรเก็บกับทุก Chunk

```json
{
  "source": "docs/wiki/rag/chunking-strategy.md",
  "chunk_index": 2,
  "total_chunks": 8,
  "title": "RAG Chunking Strategy",
  "category": "rag",
  "tags": ["chunking", "splitting"],
  "char_start": 1024,
  "char_end": 2048,
  "ingested_at": "2026-05-12T10:00:00Z"
}
```

---

## Anti-Patterns

- **Chunk เล็กเกิน (< 100 tokens)**: ขาด context → retrieval ไม่แม่นยำ
- **Chunk ใหญ่เกิน (> 2048 tokens)**: noise สูง, ดัน token limit
- **ไม่มี overlap**: ข้อมูลที่อยู่ขอบ chunk จะขาดหาย
- **ไม่เก็บ metadata**: หา source ไม่ได้เมื่อ retrieval สำเร็จ

---

## Chunking ใน ai-control-center

Worker ทำ chunking อัตโนมัติสำหรับ `.txt`, `.md`, `.log` attachments
ไฟล์ประเภท document/spreadsheet/image ไม่ chunk — ส่ง instructions แทน

```python
# worker/app/main.py
def _read_attachment_context(att):
    category = att.get("category", "text")
    if category == "text":
        content = read_file(att["stored_path"])
        return chunk_and_format(content), False
    else:
        return _CONTEXT_INSTRUCTIONS[category], False
```
