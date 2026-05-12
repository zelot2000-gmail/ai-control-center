---
title: "Model Selection Guide"
category: llm
tags: [model, claude, selection, cost, performance]
status: stable
updated: 2026-05-12
---

# Model Selection Guide

## หลักการเลือก Model

| ปัจจัย | น้ำหนัก |
|--------|---------|
| ความซับซ้อนของงาน | สูงมาก |
| ต้นทุน Token | สูง |
| Context Window ที่ต้องการ | กลาง |
| ความเร็ว Response | กลาง |
| Tool Use / Function Calling | ขึ้นกับงาน |

---

## Model Matrix (Claude Family)

| Model | Context | เหมาะกับ | ต้นทุน | ความเร็ว |
|-------|---------|----------|--------|---------|
| claude-haiku-4-5 | 200K | สรุป, classify, simple QA | ต่ำ | เร็วมาก |
| claude-sonnet-4-6 | 200K | coding, analysis, tool use, agent | กลาง | กลาง |
| claude-opus-4-7 | 200K | complex reasoning, research, multi-step | สูง | ช้ากว่า |

**Default ในระบบนี้**: `claude-sonnet-4-6` — สมดุลระหว่างคุณภาพและต้นทุน

---

## Decision Tree การเลือก Model

```
งานซับซ้อน? (multi-step reasoning, research, R&D)
  └─ ใช่ → claude-opus-4-7

งาน coding/agent/tool use ทั่วไป?
  └─ ใช่ → claude-sonnet-4-6

งาน classify/สรุป/แปล/simple QA?
  └─ ใช่ → claude-haiku-4-5
```

---

## กฎการใช้ใน ai-control-center

```python
MODEL_ROUTING = {
    "manager":    "claude-sonnet-4-6",
    "programmer": "claude-sonnet-4-6",
    "qa":         "claude-sonnet-4-6",
    "research":   "claude-opus-4-7",
    "observer":   "claude-haiku-4-5",
    "designer":   "claude-sonnet-4-6",
    "security":   "claude-sonnet-4-6",
}
```

---

## Context Window Management

- **< 10K tokens**: ใช้ได้กับทุก model
- **10K–100K**: Sonnet/Opus ปลอดภัย
- **> 100K**: ต้องเพิ่ม `budget_tokens` parameter และตรวจ cost ก่อน

**กฎ**: ถ้า prompt + context > 80K tokens → ให้ chunking ก่อน อย่าส่งทั้งหมดในครั้งเดียว

---

## ตัวอย่าง API Call

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

---

## ข้อควรระวัง

- **ห้ามใช้ Opus สำหรับงานที่ Sonnet ทำได้** — ต้นทุนสูงกว่า 5x
- **ห้าม hardcode model name** ใน code — ใช้ constant หรือ config
- **ทุก model มี rate limit** — ดู Anthropic Console ก่อน production
- เมื่อ Anthropic ออก model ใหม่ → อัปเดตตารางนี้ก่อน
