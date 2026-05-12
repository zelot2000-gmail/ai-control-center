# Risk Policy

## Overview
ทุกงานต้องประเมิน risk level ก่อนดำเนินการ

---

## Level 1 — Read-only
**ไม่ต้อง approval**

Actions:
- วิเคราะห์ code หรือ config
- ค้นเอกสารใน RAG
- สรุป log หรือ status
- GET endpoints ทุกตัว
- docker ps, docker logs (read-only)
- health check

---

## Level 2 — Dev Change
**ไม่ต้อง approval ถ้า environment=wsl/dev**

Actions:
- แก้ไขไฟล์ใน services/ หรือ apps/
- สร้างไฟล์ใหม่
- รัน pytest / linter
- docker compose build (ไม่ deploy)
- ingest documents ใน dev
- แก้ .env.example (ไม่ใช่ .env จริง)

Condition: ถ้า environment=staging/production → ต้องการ approval Level 3+

---

## Level 3 — Service Operation
**ต้อง phrase: `CONFIRM STAGING`**

Actions:
- docker compose up / down
- docker compose restart
- rebuild image และ deploy ใหม่
- staging deploy
- เปลี่ยน environment variable ที่ affect service

After approval:
- ต้องมี rollback plan
- ต้องรัน verify หลัง deploy

---

## Level 4 — Production Deploy
**ต้อง phrase: `CONFIRM DEPLOY`**

Actions:
- deploy ขึ้น production
- เปลี่ยน reverse proxy config ใน CWP
- restart production service
- เปลี่ยน SSL certificate
- เปลี่ยน DNS
- เปลี่ยน production database config

After approval:
- **บังคับมี backup ก่อน**
- บังคับมี rollback command พร้อม
- บังคับมี verify steps หลัง deploy

---

## Level 5 — Destructive
**ต้อง phrase: `CONFIRM DANGEROUS`**
**ต้องแสดง impact statement ชัดเจน**

Actions:
- ลบ database หรือ table
- ลบ Docker volume
- ลบไฟล์ใน production
- firewall reset
- chmod -R หรือ chown -R ระบบ
- docker system prune --volumes

Before execution:
- แสดง impact: "จะลบ X ซึ่งกระทบ Y และ Z"
- ต้องมี backup ที่ verify แล้ว
- ต้องมี restore steps พร้อม

---

## Auto-reject (ห้ามรันเด็ดขาด ไม่ว่า approval ระดับใด)
- rm -rf /
- rm -rf * (root context)
- mkfs.*
- dd if=/dev/zero of=/dev/sd*
- DROP DATABASE โดยไม่มี backup
- chmod -R 777 /
