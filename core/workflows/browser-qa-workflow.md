---
id: browser-qa-workflow
mode: hybrid
autonomy_level: 2
risk_level: 1
approval_required: false
responsible_agents: [qa, designer, observer]
devtools_required: true
environment_restriction: local/dev/staging ONLY
---

# Browser QA Workflow

## วัตถุประสงค์
ตรวจ Dashboard ผ่าน Chrome DevTools MCP แบบ hybrid:
- Workflow คุม checklist หลัก
- Agent วิเคราะห์ UI issues และ fix recommendations

## ข้อห้าม (Security Rules)
- ห้าม login production account
- ห้ามเปิดหน้าที่มี secret/token/password
- ห้ามบันทึก screenshot ที่มี credential
- ถ้าพบ secret → หยุดทันที แจ้ง Security Agent

## Steps

### Step 1: open_page [workflow]
- เปิด `http://127.0.0.1:3000`
- ตรวจว่า page load สำเร็จ (HTTP 200)
- บันทึก: load time, page title, HTTP status

### Step 2: check_console [workflow]
- เปิด DevTools Console
- Flag ทุก `ERROR`, `WARN` ที่ไม่ใช่ network error ที่คาดหวัง
- ตรวจ: unhandled exception, undefined variable, CSP violations

### Step 3: check_network [workflow]
- เปิด DevTools Network tab
- ตรวจ failed requests (4xx, 5xx, CORS, ERR_CONNECTION_REFUSED)
- ตรวจว่าไม่มี secret ใน request headers/body

### Step 4: test_main_pages [workflow]
ทดสอบทุก page:
- `/` (Overview) — stats แสดง, health grid แสดง
- `/command` — form แสดง, submit ทำงาน
- `/jobs` — list แสดง หรือ empty state ถูกต้อง
- `/approvals` — pending list หรือ empty state
- `/knowledge` — search form แสดง
- `/logs` — service status แสดง

### Step 5: test_responsive [workflow]
ทดสอบ 3 viewport:
- `390px` — mobile: bottom nav แสดง, grid 1 col
- `768px` — tablet: desktop nav แสดง, grid 2 col
- `1280px` — desktop: max-width 900px centered

### Step 6: run_interaction_test [hybrid → agent วิเคราะห์]
- กรอก command form และ submit
- ตรวจ network request ไป `POST /tasks`
- ตรวจ response: task_id, risk_level, status
- ตรวจ UI แสดง task_id หรือ error state ถูกต้อง
- **Agent วิเคราะห์**: UX friction, accessibility, touch target size

### Step 7: summarize_ui_issues [hybrid → agent วิเคราะห์]
Agent ประเมิน:
- Layout issues
- Mobile usability
- Error/loading/empty state quality
- Typography readability (Thai + English)
- Color contrast

### Step 8: create_fix_recommendation [hybrid → agent วิเคราะห์]
- จัดลำดับ: Critical → High → Medium → Low
- ระบุไฟล์และบรรทัดที่ต้องแก้

## Accountability Log
```yaml
owner_agent: qa
responsible_agents: [qa, designer, observer]
tool_usage_log: [chrome-devtools-mcp, browser-preview]
verification_log: [console-check, network-check, responsive-check]
rollback_plan: N/A — read-only inspection
```
