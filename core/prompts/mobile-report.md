# Prompt: Mobile Report

## System
สร้างรายงานสั้นอ่านง่ายบนมือถือ

## Rules
- ไม่เกิน 10 บรรทัด
- ใช้ภาษาไทยอ่านง่าย
- ระบุ task_id ย่อ (8 chars แรก)
- ระบุสถานะชัดเจน
- ถ้าต้องการ action → บอกคำสั่งต่อไป

## Format
```
[AICC] {task_id_short}
สถานะ: {status}
งาน: {task_name}

{summary_2_lines}

{action_required_or_none}
เวลา: {timestamp}
```

## Status Labels
- สำเร็จ
- ล้มเหลว: {reason}
- รอ approval: ส่ง {PHRASE}
- กำลังทำงาน

## Example
```
[AICC] a1b2c3d4
สถานะ: สำเร็จ
งาน: ตรวจ health rag-api

rag-api ทำงานปกติ response 120ms
Qdrant connected, 45 documents indexed

ไม่มี action ที่ต้องทำเพิ่ม
เวลา: 2024-01-01 10:00 +07:00
```
