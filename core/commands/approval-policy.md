# Approval Policy

## กระบวนการขอ Approval

### Step 1: Manager Agent ประเมิน Risk
- ตรวจ intent + target + environment
- กำหนด risk_level (1-5)
- ถ้า risk_level >= 3 → ต้องขอ approval

### Step 2: ส่ง Pending Task กลับผู้ใช้
```
## งานรอ Approval

**task_id**: [uuid]
**งาน**: [ชื่องาน]
**risk_level**: [3/4/5]
**สิ่งที่จะทำ**: [รายการ action]
**ผลกระทบ**: [สิ่งที่จะเปลี่ยนแปลง]
**Rollback**: [วิธี rollback ถ้าผิดพลาด]

เพื่อ approve ส่ง: [APPROVAL_PHRASE]
```

### Step 3: ผู้ใช้ตอบกลับด้วย Approval Phrase
- Level 3: `CONFIRM STAGING`
- Level 4: `CONFIRM DEPLOY`
- Level 5: `CONFIRM DANGEROUS`

### Step 4: Verify Phrase
- ตรวจว่า phrase ตรงกับ risk level
- ตรวจว่า task_id ตรงกัน
- ถ้า phrase ไม่ตรง → ปฏิเสธ

### Step 5: Execute
- Execute ตาม plan
- Log approval event ลง audit_logs
- บันทึก: approver, timestamp, phrase, task_id

---

## Approval Timeout
- Task ที่รอ approval นานกว่า 24 ชั่วโมง → auto-cancel
- แจ้ง user ว่า task expired

---

## Audit Log Format
```json
{
  "event": "approval_granted",
  "task_id": "uuid",
  "risk_level": 4,
  "approver": "user",
  "phrase": "CONFIRM DEPLOY",
  "timestamp": "2024-01-01T10:00:00Z",
  "ip": "masked"
}
```

---

## Emergency Override
- ไม่มี emergency override ที่ bypass Level 5
- ถ้า destructive จริงๆ จำเป็น → ต้องมี 2 คน confirm (future feature)
