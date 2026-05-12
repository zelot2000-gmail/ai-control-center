# Browser DevTools Checklist

**ใช้กับ**: local / dev / staging เท่านั้น
**ห้ามใช้กับ**: production account จริง หรือหน้าเว็บที่มี secret

---

## Pre-test Setup
- [ ] ตรวจว่า services รันอยู่: `make ps`
- [ ] ตรวจ URL ที่จะทดสอบไม่มี secret/token ใน path
- [ ] เลือก environment: local / dev / staging
- [ ] ระบุ viewport ที่จะทดสอบ

---

## 1. Page Load Check
- [ ] เปิด URL ได้ (ไม่ crash, ไม่ 502/503)
- [ ] HTTP status 200
- [ ] Page title ถูกต้อง
- [ ] ไม่มี blank screen
- [ ] Favicon โหลดได้

---

## 2. Console Check
- [ ] ไม่มี JavaScript Error (แดง)
- [ ] ไม่มี Vue/Nuxt hydration mismatch
- [ ] ไม่มี Unhandled Promise Rejection
- [ ] Warning ที่พบต้อง review ว่า critical หรือไม่
- [ ] ไม่มี secret / token / password ใน console log
- [ ] ไม่มี stack trace ที่เปิดเผย server path

---

## 3. Network Check
- [ ] ไม่มี failed request (4xx / 5xx) ที่ไม่ตั้งใจ
- [ ] ไม่มี request ไปผิด domain
- [ ] ไม่มี CORS error
- [ ] API response ไม่มี secret/token ใน body
- [ ] ไม่มี request ซ้ำซ้อนโดยไม่จำเป็น
- [ ] Slow request (>2s) ต้องบันทึกและ review

---

## 4. UI / Layout Check
- [ ] Layout ไม่แตก
- [ ] ข้อความไม่ overflow / ไม่บีบเกิน
- [ ] รูปภาพ / icon โหลดได้
- [ ] สีถูกต้องตาม design tokens
- [ ] Thai text render ถูกต้อง (ไม่มี tofu)
- [ ] Loading state แสดงขณะรอ API
- [ ] Error state แสดงเมื่อ API fail
- [ ] Empty state แสดงเมื่อไม่มีข้อมูล

---

## 5. Responsive Check
- [ ] Mobile 390x844 — ปุ่มกดได้ ข้อความไม่ล้น card ไม่แตก
- [ ] Tablet 768x1024 — layout สมดุล
- [ ] Desktop 1280x720 — ใช้พื้นที่ได้ดี

---

## 6. Interaction Check (ถ้ามี form/action)
- [ ] ปุ่ม click ได้
- [ ] Form กรอกได้
- [ ] Submit ส่ง request ถูกต้อง
- [ ] Response แสดงผลถูกต้อง
- [ ] Validation error แสดงชัดเจน
- [ ] ปิด/เปิด modal/dialog ได้

---

## 7. API Verification (via Network tab)
- [ ] POST /tasks — payload ถูก, response มี task_id
- [ ] POST /search — response มี results array
- [ ] GET /health endpoints — status 200
- [ ] ไม่มี request ไปผิด port

---

## 8. Security Check (Browser)
- [ ] ไม่มี .env content บนหน้า
- [ ] ไม่มี API key/secret ใน DOM
- [ ] Network response ไม่ expose internal data
- [ ] Error page ไม่แสดง stack trace
- [ ] ไม่มี hardcoded credential ใน JS source

---

## 9. Performance Notes (optional)
- [ ] First paint < 3s (local)
- [ ] No render-blocking resource
- [ ] ไม่มี unused large bundle
- [ ] Image optimized

---

## 10. Accessibility Basics
- [ ] ปุ่มมี label / aria-label
- [ ] Form input มี label
- [ ] สีมี contrast พอสมควร
- [ ] Tab order สมเหตุสมผล

---

## Sign-off
- **Tested by**: [agent / person]
- **Date**: [YYYY-MM-DD]
- **Environment**: [local/dev/staging]
- **Result**: PASS / PASS WITH WARNINGS / FAIL
