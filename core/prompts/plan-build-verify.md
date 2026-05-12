# Prompt: Plan → Build → Verify

## System
ทุกงานต้องผ่านกระบวนการ Plan → Build → Verify → Report เสมอ

## Phase 1: PLAN

### ก่อนเริ่มงาน
- อ่าน AGENTS.md
- โหลด skills ที่เกี่ยวข้องจาก core/skills/index.json
- ระบุไฟล์ที่จะแก้
- ระบุ risk level
- ถ้า risk >= 3 → หยุดและขอ approval ก่อน

### Plan Output Format
```
## Plan

**task_id**: {task_id}
**risk_level**: {risk}
**approval_required**: yes/no

### ไฟล์ที่จะแก้
- path/to/file.ext — เหตุผล

### ขั้นตอน
1. ...
2. ...

### Rollback
- วิธี rollback ถ้าผิดพลาด
```

## Phase 2: BUILD

- ดำเนินงานตาม plan ที่ approved
- ห้ามแก้นอกขอบเขต plan
- บันทึกทุก action

## Phase 3: VERIFY

```bash
# Health check หลังแก้
curl -sf http://127.0.0.1:{port}/health

# ตรวจ log
docker logs aicc-{service} --tail=50

# รัน verify script
bash scripts/verify-wsl.sh
```

## Phase 4: REPORT

```
## รายงานผล

**งาน**: {task_name}
**task_id**: {task_id}
**risk_level**: {risk}
**สถานะ**: สำเร็จ/ล้มเหลว

### ไฟล์ที่แก้ไข
- path/to/file.ext — สิ่งที่เปลี่ยน

### คำสั่งที่รัน
- `command` — ผลลัพธ์

### วิธี Verify
- `curl http://...`

### ข้อควรระวัง
- ถ้ามี
```
