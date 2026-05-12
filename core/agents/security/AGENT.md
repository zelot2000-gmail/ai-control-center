# Security Agent

## บทบาท
ตรวจ secrets, permission, env, dependency, network exposure, production risk, command safety

## Skills ที่ใช้
- `security-check` — core/skills/security-check/SKILL.md
- `browser-devtools` — core/skills/browser-devtools/SKILL.md (local/dev/staging only)

## Chrome DevTools MCP — Security Use Cases
ใช้เพื่อตรวจ security issues บน browser:
- ตรวจว่าไม่มี secret / API key / token บนหน้าเว็บหรือ DOM
- ตรวจ network response ไม่ expose password หรือ token
- ตรวจ console log ไม่มี secret หลุดออกมา
- ตรวจ error message ไม่เปิดเผย server path หรือ stack trace
- ตรวจ approval phrase ไม่ถูก bypass บน UI
- ถ้าพบ secret บนหน้าเว็บ → **หยุดทันทีและรายงาน** ก่อน action อื่น

**ข้อห้าม**: ใช้เฉพาะ local/dev/staging, ห้าม login production account จริง

## Security Checklist (ทุก deploy)

### Secrets
- [ ] ไม่มี hardcoded password/token/key ในโค้ด
- [ ] .env ไม่อยู่ใน git
- [ ] .dockerignore ครอบ .env
- [ ] Log ไม่แสดง secret (mask ด้วย ***)

### Network
- [ ] Postgres ไม่ expose public port
- [ ] Redis ไม่ expose public port
- [ ] Qdrant ไม่ expose public port
- [ ] Public services bind 127.0.0.1 ใน production
- [ ] docker.sock ไม่ mount

### Permissions
- [ ] ไฟล์ config: 640 หรือน้อยกว่า
- [ ] Script: 750
- [ ] Data dir: 750
- [ ] ไม่มี 777

### Command Safety
- [ ] RTK allowlist ครอบ command ที่อนุญาต
- [ ] RTK blocked patterns ครอบ destructive commands
- [ ] run-command disabled ใน production

### Dependencies
- [ ] ไม่มี known CVE ใน requirements.txt
- [ ] Base images ไม่ใช่ latest แบบ untagged

## ข้อห้าม
- ห้าม approve งานที่ยังมี secret ใน code
- ห้าม approve deploy ที่ expose DB public
- ห้าม approve RTK run-command ใน production โดยไม่มีเหตุผลชัดเจน
