---
title: "Chrome DevTools MCP"
category: mcp
tags: [mcp, chrome, devtools, browser, automation, screenshot]
status: stable
updated: 2026-05-12
---

# Chrome DevTools MCP

## คืออะไร

Chrome DevTools MCP = MCP server ที่ให้ AI ควบคุม Chrome browser ผ่าน DevTools Protocol  
ใช้สำหรับ: UI testing, web scraping, screenshot, console log, network inspection

---

## ความสามารถ

| Tool | คำอธิบาย |
|------|----------|
| `navigate` | เปิด URL ใน browser |
| `screenshot` | ถ่าย screenshot ทั้งหน้าหรือ element |
| `click` | คลิก element ด้วย selector |
| `type` | พิมพ์ข้อความใน input |
| `evaluate` | รัน JavaScript ใน page context |
| `get_console` | ดึง console logs |
| `get_network` | ดึง network requests/responses |
| `wait_for` | รอ element หรือ network idle |
| `scroll` | scroll หน้าหรือ element |
| `get_html` | ดึง DOM content |

---

## Setup

```bash
# ติดตั้ง
npm install -g @modelcontextprotocol/server-puppeteer

# รัน (พร้อม Chrome)
npx @modelcontextprotocol/server-puppeteer
```

Claude Code config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

---

## Use Cases ใน ai-control-center

### 1. UI Verification หลัง Deploy

```
Task: "ตรวจสอบ /command page ว่า render ถูกต้อง"
→ navigate http://localhost:3000/command
→ screenshot → ส่งให้ designer agent ตรวจ
→ get_console → ตรวจ error
```

### 2. End-to-End Test

```
Task: "ทดสอบ flow: ส่ง command → เช็ค jobs → view report"
→ navigate /command
→ type "#input" "ตรวจ health service"
→ click ".send-btn"
→ navigate /jobs
→ screenshot
```

### 3. Visual Bug Investigation

```
Task: "button ซ้อนกันบน mobile"
→ navigate http://localhost:3000/jobs
→ evaluate "window.innerWidth = 375; window.dispatchEvent(new Event('resize'))"
→ screenshot
```

---

## Agent ที่ใช้

- **designer**: UI verification, screenshot
- **qa**: E2E testing, regression testing
- **observer**: Visual monitoring, status check

---

## Security Rules

- **ห้าม navigate ไป URL ภายนอก** โดยไม่มีเหตุผลชัดเจน
- **ห้าม evaluate JS ที่ดึงข้อมูล credential**
- **ห้ามถ่ายภาพหน้าจอที่มีข้อมูลส่วนตัว** และส่งออกไปยังภายนอก
- **sandbox mode**: รัน browser ใน isolated profile

---

## Troubleshooting

| ปัญหา | แก้ไข |
|-------|-------|
| Chrome ไม่เปิด | ตรวจ Chrome installation path |
| Permission denied | รัน MCP server ด้วย user ที่มีสิทธิ์เปิด browser |
| Element not found | เพิ่ม `wait_for` ก่อน `click` |
| Screenshot ว่างเปล่า | รอ page load: `wait_for network_idle` |
| Console log ไม่แสดง | ต้อง navigate ก่อน get_console |
