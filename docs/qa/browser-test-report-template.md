# Browser Test Report

**Date**: YYYY-MM-DD
**Tester**: [agent / person]
**Tool**: Chrome DevTools MCP
**Environment**: local / dev / staging

---

## 1. URLs Tested

| URL                              | Status | Notes |
|----------------------------------|--------|-------|
| http://127.0.0.1:3000            |        |       |
| http://127.0.0.1:3000/command    |        |       |
| http://127.0.0.1:3000/jobs       |        |       |
| http://127.0.0.1:3000/approvals  |        |       |
| http://127.0.0.1:3000/knowledge  |        |       |
| http://127.0.0.1:3000/logs       |        |       |
| http://127.0.0.1:8088/health     |        |       |
| http://127.0.0.1:8090/health     |        |       |
| http://127.0.0.1:8091/health     |        |       |
| http://127.0.0.1:8092/health     |        |       |
| http://127.0.0.1:8093/health     |        |       |
| http://127.0.0.1:8094/health     |        |       |

---

## 2. Viewports Tested

| Viewport          | Tested | Issues Found |
|-------------------|--------|--------------|
| Mobile 390x844    |        |              |
| Tablet 768x1024   |        |              |
| Desktop 1280x720  |        |              |

---

## 3. Page Load Summary

| Page        | Load OK | Load Time | Notes |
|-------------|---------|-----------|-------|
| Home (/)    |         |           |       |
| /command    |         |           |       |
| /jobs       |         |           |       |
| /approvals  |         |           |       |
| /knowledge  |         |           |       |
| /logs       |         |           |       |

---

## 4. Console Errors

```
[none / list errors here]
```

**Severity**: none / warning / error / critical

---

## 5. Network Errors

| URL/Endpoint        | Status | Error Type | Notes |
|---------------------|--------|------------|-------|
|                     |        |            |       |

---

## 6. UI Issues

| Page      | Issue Description              | Severity | Fix Needed |
|-----------|--------------------------------|----------|------------|
|           |                                |          |            |

---

## 7. Responsive Issues

| Page      | Viewport    | Issue                          |
|-----------|-------------|--------------------------------|
|           |             |                                |

---

## 8. API Issues (from Network tab)

| Endpoint        | Expected    | Actual     | Issue |
|-----------------|-------------|------------|-------|
| POST /tasks     | task_id     |            |       |
| POST /search    | results[]   |            |       |
| GET /health     | 200 OK      |            |       |

---

## 9. Security Concerns

| Finding                        | Location    | Severity | Action |
|--------------------------------|-------------|----------|--------|
|                                |             |          |        |

**Note**: ถ้าพบ secret ต้องแจ้ง Security Agent ทันที

---

## 10. Performance Notes

| Page | Observation | Slow Request | Recommendation |
|------|-------------|--------------|----------------|
|      |             |              |                |

---

## 11. Screenshots / Snapshots

| Page      | Viewport    | File / Description |
|-----------|-------------|-------------------|
|           |             |                   |

**Note**: ห้ามบันทึก screenshot ที่มี password หรือ token

---

## 12. Recommended Fixes

| # | Issue | File to Fix | Cause | Fix | Verify By |
|---|-------|-------------|-------|-----|-----------|
| 1 |       |             |       |     |           |

---

## 13. Verification Status

> **[ PASS / PASS WITH WARNINGS / FAIL ]**

**Summary (ภาษาไทย)**:
[สรุปผลการทดสอบ 3-5 บรรทัด]

---

## Fix Plan (กรณี FAIL หรือ WARNING สำคัญ)

```
ไฟล์ที่คาดว่าต้องแก้ : [path]
สาเหตุที่เป็นไปได้  : [reason]
วิธีแก้             : [fix steps]
วิธี verify ซ้ำ     : [how to re-verify]
```
