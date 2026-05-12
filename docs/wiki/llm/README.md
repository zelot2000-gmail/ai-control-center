# LLM Knowledge Base

**หมวด**: llm  
**สถานะ**: active  

เก็บความรู้เกี่ยวกับ Large Language Models สำหรับใช้งานใน ai-control-center

---

## หัวข้อที่ควรมี

| ไฟล์ | เนื้อหา | สถานะ |
|------|---------|-------|
| `prompt-patterns.md` | Few-shot, CoT, ReAct, Tool use patterns | TODO |
| `context-management.md` | Context window, token budget, truncation | TODO |
| `model-comparison.md` | Claude vs GPT vs Gemini — capability & cost | TODO |
| `thai-language-notes.md` | ข้อควรระวังเมื่อใช้ LLM กับภาษาไทย | TODO |
| `structured-output.md` | JSON mode, function calling, schema enforcement | TODO |

---

## หลักการสำคัญ

- **Token economy first** — ลด context ที่ไม่จำเป็น ใช้ TTO ก่อนส่ง prompt
- **Prompt = code** — ต้อง version ควบคุม เปลี่ยนแปลงต้องมีเหตุผล
- **Eval before deploy** — ทดสอบ prompt ใหม่ก่อนใช้ใน production workflow
