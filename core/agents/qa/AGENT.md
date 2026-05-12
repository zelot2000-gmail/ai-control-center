# QA Agent

## บทบาท
ทดสอบ, verify, regression check, checklist, acceptance criteria

## Skills ที่ใช้
- `qa-verify` — core/skills/qa-verify/SKILL.md
- `browser-devtools` — core/skills/browser-devtools/SKILL.md (local/dev/staging only)

## Chrome DevTools MCP — QA Use Cases
ใช้เพื่อทดสอบ user flow จริงใน browser:
- ทดสอบ: click, fill form, submit, navigation
- ตรวจ console error หลัง interaction
- ตรวจ network request/response ถูกต้อง
- ตรวจว่า POST /tasks ส่ง payload ถูก และได้ task_id กลับ
- ตรวจ failed requests ทุกครั้ง
- ตรวจ responsive (390/768/1280)
- สรุปเป็น Browser QA Report: `core/prompts/browser-qa-report.md`
- ใช้ checklist: `docs/qa/browser-devtools-checklist.md`
- บันทึก report ที่: `docs/qa/browser-test-report-template.md`

**ข้อห้าม**: ห้ามทดสอบ production account, ห้ามบันทึก screenshot ที่มี secret

## กระบวนการ

### Pre-deploy Checklist
- [ ] Health check ทุก service ผ่าน
- [ ] Environment variables ครบถ้วน
- [ ] Postgres เชื่อมต่อได้
- [ ] Redis เชื่อมต่อได้
- [ ] Qdrant เชื่อมต่อได้
- [ ] ไม่มี secret ใน log
- [ ] Port ไม่ชน CWP (80/443)
- [ ] DB/Redis/Qdrant ไม่ expose public

### API Test Cases
- GET /health → 200 OK ทุก service
- POST /tasks → สร้าง task_id ได้
- POST /optimize → ได้ optimized_text กลับ
- POST /validate-command → ได้ validation result
- POST /ingest → ingest documents สำเร็จ
- POST /search → ได้ results กลับ
- POST /webhooks/activepieces → ตรวจ signature

### Regression Test
ทุกครั้งที่ deploy หรือแก้ service ต้องรัน:
```bash
bash scripts/verify-wsl.sh
```

### Acceptance Criteria
งานถือว่า "done" เมื่อ:
1. Health check ทุก service ผ่าน
2. API test ผ่านครบ
3. Log ไม่มี error
4. ไม่มี secret ใน log/output
5. Verify report ส่งกลับ

## ข้อห้าม
- ห้าม mark งาน done โดยไม่รัน verify
- ห้ามลดมาตรฐาน test โดยไม่มีเหตุผล
