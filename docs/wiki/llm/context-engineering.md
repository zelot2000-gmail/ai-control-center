---
title: "Context Engineering"
category: llm
tags: [context, token, window, management, compression]
status: stable
updated: 2026-05-12
---

# Context Engineering

## Context Window คืออะไร

Context Window = จำนวน token สูงสุดที่ model รับได้ใน 1 request (input + output รวมกัน)

Claude Sonnet 4.6: **200,000 tokens** ≈ 150,000 คำ ≈ หนังสือ ~500 หน้า

---

## ต้นทุน Attention

- Model ให้ attention กับ token **ต้นและท้าย** มากกว่ากลาง
- Context ยาวเกินไปทำให้ข้อมูลสำคัญถูก "ลืม" กลางทาง
- **กฎ**: วางข้อมูลสำคัญไว้ต้น prompt หรือท้าย prompt เสมอ

---

## Context Budget Planning

```
Total Budget = 200,000 tokens
├─ System prompt + Role: ~500 tokens
├─ Skill/SOP context: ~2,000 tokens
├─ Task data / attachments: ~5,000-20,000 tokens
├─ Conversation history: ~1,000-5,000 tokens
└─ Output budget: ~4,096 tokens (max_tokens parameter)

เหลือ headroom: ~170,000+ tokens
```

**ในทางปฏิบัติ**: ถ้า total input > 50K tokens → ต้องทำ context compression ก่อน

---

## Strategies

### 1. Selective Loading
โหลดเฉพาะ context ที่เกี่ยวข้อง ไม่โหลดทั้ง codebase

```python
# ไม่ดี
context = read_entire_repo()

# ดี
context = search_relevant_files(query=task_description, top_k=5)
```

### 2. Hierarchical Summarization
สรุป context เก่าก่อนต่อ conversation

```python
if len(history_tokens) > 10000:
    history = summarize(history[-20:])  # เก็บแค่สรุป
    history += recent_messages[-5:]     # บวก 5 ล่าสุดเต็ม
```

### 3. RAG-Augmented Context
ดึงเฉพาะ chunk ที่ relevance score สูง

```python
chunks = rag_search(query=task, limit=3, min_score=0.75)
context = "\n\n".join(chunks)
```

### 4. Structured Context Injection

```markdown
## Context (เรียงตาม relevance)

### [HIGH] Task-specific data
[ข้อมูลที่สำคัญที่สุด]

### [MED] Background knowledge
[ข้อมูลพื้นฐาน]

### [LOW] Reference only
[อ้างอิงถ้าจำเป็น]
```

---

## Prompt Cache (Anthropic)

Anthropic รองรับ prompt caching — system prompt และ context ที่ซ้ำกันจะถูก cache
- Cache TTL: 5 นาที
- ประหยัดได้ ~90% ของ input token cost สำหรับส่วนที่ cache ได้
- ใช้ `cache_control: {"type": "ephemeral"}` ใน API

---

## Context Engineering ใน ai-control-center

ใน `_export_prompt()` ของ worker:
1. โหลด system prompt จาก SKILL.md → ต้น prompt
2. Attachment context (file content/instructions) → กลาง
3. User task text → ท้าย (ใกล้ output มากที่สุด)

**เหตุผล**: User's actual request ควรอยู่ใกล้จุดที่ model จะ generate คำตอบ
