# Skill: Browser DevTools (Chrome DevTools MCP)

## วัตถุประสงค์
ใช้ Chrome DevTools MCP เพื่อตรวจหน้าเว็บจริงจาก AI Agent
เช่น UI check, responsive, console, network, screenshot, Lighthouse, performance, browser automation, QA flow

## ข้อห้ามเด็ดขาด
- **ใช้เฉพาะ local / dev / staging เท่านั้น**
- **ห้าม login production account จริง**
- **ห้ามเปิดหน้าเว็บที่มี secret / token / password**
- **ห้ามบันทึก screenshot ที่มี password หรือ token**
- **ถ้าพบ secret บนหน้าเว็บ → แจ้ง Security Agent ทันที**

---

## Agents ที่ใช้ Skill นี้

| Agent          | Use case                                          |
|----------------|---------------------------------------------------|
| Designer       | UI, responsive, layout, usability, loading state  |
| QA             | user flow, form, submit, console/network error     |
| Observer       | health page, logs page, service status via browser |
| R&D            | benchmark frontend, Lighthouse, UI library compare |
| Security       | ตรวจ secret leak, API response exposure, CORS      |

---

## Browser QA Workflow

1. เปิด URL เป้าหมาย
2. ตรวจว่า page load สำเร็จ (status 200, no crash)
3. ถ่าย screenshot / snapshot
4. ตรวจ console messages (errors, warnings)
5. ตรวจ network requests (failed, slow, wrong domain)
6. ทดสอบ interaction: click, fill form, submit, navigate
7. ตรวจ responsive (390px / 768px / 1280px)
8. ตรวจ accessibility เบื้องต้น
9. ตรวจ performance ถ้าจำเป็น
10. สรุปเป็น Browser QA Report

---

## Local URLs ที่ต้องทดสอบ

### Dashboard Pages
- http://127.0.0.1:3000
- http://127.0.0.1:3000/command
- http://127.0.0.1:3000/jobs
- http://127.0.0.1:3000/approvals
- http://127.0.0.1:3000/knowledge
- http://127.0.0.1:3000/logs

### API Health Endpoints
- http://127.0.0.1:8088/health
- http://127.0.0.1:8090/health
- http://127.0.0.1:8091/health
- http://127.0.0.1:8092/health
- http://127.0.0.1:8093/health
- http://127.0.0.1:8094/health

---

## Responsive Viewports

| Name    | Width x Height |
|---------|----------------|
| mobile  | 390 x 844      |
| tablet  | 768 x 1024     |
| desktop | 1280 x 720     |

---

## Console Checks (ต้องรายงาน)
- JavaScript errors
- Vue/Nuxt hydration errors
- Vue/Nuxt component warnings
- Failed resource loading (404 CSS/JS/font)
- CORS errors
- Unhandled Promise rejection

---

## Network Checks (ต้องรายงาน)
- Failed requests (4xx, 5xx)
- Request ไปผิด domain
- CORS error header
- Response ที่มี secret / token / password
- Request ที่ไม่จำเป็น / ช้าผิดปกติ

---

## API Browser Verification
- POST /tasks → payload ถูก, response มี task_id
- POST /search → response มี results
- GET /health → 200 OK
- ไม่มี request ไปผิด domain
- ไม่มี CORS error
- ไม่มี 500 โดยไม่จำเป็น

---

## Security Browser Checks
- ไม่มี .env content บนหน้าเว็บ
- ไม่มี API key/token/password ใน console log
- ไม่มี secret ใน network response
- ไม่มี stack trace แบบ production บน UI
- error message ไม่เปิดเผย server path
- approval phrase ไม่ถูก bypass

---

## Performance Checks (ถ้าใช้ Lighthouse / audit)
บันทึก:
- URL ที่ทดสอบ
- load time observation
- heavy JS/CSS bundles
- slow API requests (>1s)
- unnecessary requests
- image/font optimization issues
- improvement suggestions

---

## Output Report Format

ดู template ที่:
- `core/prompts/browser-qa-report.md` — QA report
- `core/prompts/ui-debug-report.md` — UI debug
- `core/prompts/performance-audit-report.md` — performance audit
- `docs/qa/browser-test-report-template.md` — full report template
- `docs/research/benchmarks/browser-performance-template.md` — benchmark template


---
name: browser-devtools
description: ใช้เมื่อต้องตรวจหน้าเว็บจริงผ่าน Chrome DevTools MCP เช่น UI, responsive, console, network, screenshot, Lighthouse, performance, browser automation และ QA flow
---

# Browser DevTools SOP

## Goal
ใช้ Chrome DevTools MCP เพื่อตรวจเว็บจริง ไม่ใช่เดาจากโค้ดอย่างเดียว

## Agents Allowed
- Designer Agent
- QA Agent
- Observer Agent
- R&D Agent
- Security Agent

## Use Cases
- ตรวจ Dashboard
- ตรวจ Mobile-first UI
- ตรวจ Console errors
- ตรวจ Network requests
- ตรวจ API calls
- ตรวจ CORS
- ตรวจ Screenshot/Snapshot
- ตรวจ Lighthouse/Performance
- ตรวจ user flow
- ตรวจ form submit
- ตรวจ responsive layout

## Safety Rules
- ใช้เฉพาะ local/dev/staging
- ห้ามใช้ production account จริง
- ห้ามเปิดหน้าเว็บที่มี secret
- ห้ามเก็บ screenshot ที่มี password/token/API key
- ถ้าพบ secret บนหน้าเว็บ ให้แจ้ง Security Agent ทันที
- ห้ามแก้ production ผ่าน browser automation

## Workflow
1. Open target URL
2. Confirm page loaded
3. Capture screenshot or snapshot
4. Inspect console messages
5. Inspect network requests
6. Check failed requests
7. Test user interactions
8. Test responsive viewports
9. Run performance audit if needed
10. Produce Browser QA Report

## Required Checks
- Page load status
- Console errors
- Network errors
- API response status
- UI layout
- Responsive behavior
- Security leakage
- Performance issues

## Viewports
- Mobile: 390x844
- Tablet: 768x1024
- Desktop: 1280x720

## Required Output
- URL tested
- Viewport tested
- Console errors
- Network errors
- UI issues
- Responsive issues
- Security concerns
- Performance notes
- Recommended fixes
- Verification status

## Verification Status
Use one of:
- PASS
- PASS WITH WARNINGS
- FAIL
