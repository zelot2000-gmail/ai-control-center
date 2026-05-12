# Skill: Mobile Command

## วัตถุประสงค์
รับ input จากมือถือ / ChatGPT / webhook แปลงเป็น Task Packet มาตรฐาน

## Input Format
```json
{
  "source": "chatgpt-mobile | webhook | dashboard | manual",
  "user": "username",
  "text": "ข้อความคำสั่ง",
  "target_system": "service name หรือ all",
  "environment": "wsl | staging | production",
  "mode": "plan-only | execute | dry-run"
}
```

## Output: Task Packet
ตาม schema ใน `core/commands/task-schema.yaml`

## Steps
1. Parse input text เพื่อหา intent
2. ส่ง text ผ่าน TTO /optimize เพื่อลด token
3. เลือก agents จาก intent
4. เลือก skills จาก core/skills/index.json
5. ประเมิน risk level
6. สร้าง task_id (UUID)
7. บันทึก task ลง Postgres (หรือ fallback JSON)
8. ส่ง task packet ต่อ

## Intent Detection Keywords
- "ตรวจ" / "check" / "debug" → observer / qa
- "deploy" / "build" / "รัน" → devops
- "แก้โค้ด" / "fix" / "เขียน" → programmer
- "เพิ่มเอกสาร" / "ingest" → rag-curator
- "ทดลอง" / "research" / "PoC" → research
- "backup" / "restore" / "SSL" → administrator
- "security" / "ตรวจ permission" → security
