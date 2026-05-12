# Skill: Thai Token Optimizer (TTO)

## วัตถุประสงค์
ลด token, normalize ภาษาไทย, clean context ก่อนส่งเข้า LLM / Agent

## Endpoints
- POST /optimize — ลด token, clean whitespace, trim log
- POST /normalize — normalize whitespace, Thai text
- POST /summarize-context — สรุป context ยาว

## Rules
- ห้ามทำให้ความหมายของคำสั่งหาย
- ห้ามลบ command block สำคัญ
- ห้ามลบ error message สำคัญ
- รักษา code block ไว้ครบ
- รักษา Thai text ให้อ่านได้

## Output Fields
- `original_length` — จำนวน char ต้นฉบับ
- `optimized_length` — จำนวน char หลัง optimize
- `estimated_reduction_percent` — % ที่ลดได้
- `optimized_text` — ข้อความที่ optimize แล้ว
- `warnings` — คำเตือนถ้ามีข้อมูลสำคัญที่อาจถูกตัด

## Fallback (ถ้าไม่มี TTO CLI)
1. normalize whitespace
2. trim duplicate blank lines (>2 → 1)
3. trim long log lines (>500 chars)
4. keep code blocks (``` ```) intact
5. keep Thai text readable
6. estimate token count (chars / 4)
