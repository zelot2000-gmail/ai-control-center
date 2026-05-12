# Code Intelligence Workflow

**workflow_id**: code-intelligence-workflow  
**mode**: hybrid  
**autonomy_level**: 3  
**risk_level**: 2  
**approval_required**: false (risk 3+ ต้องการ approval)  
**agents**: programmer, qa, security, manager  
**skill**: serena-mcp, programmer, qa-verify  

---

## วัตถุประสงค์

ใช้ Serena MCP เป็น Code Intelligence Layer ก่อนแก้ไข codebase  
เพื่อเข้าใจ structure, ทำ impact analysis และลด token ที่ใช้

---

## เมื่อไรใช้ Workflow นี้

- แก้ bug ที่ไม่รู้ว่ากระทบอะไรบ้าง
- refactor function / class / module
- เพิ่ม feature ที่ต้องแก้หลายไฟล์
- code review ก่อน merge
- security audit ส่วน code

---

## ขั้นตอน

### Step 1 — identify_task_intent
```
ระบุชัดว่า:
- แก้อะไร (symbol/function/file)
- เหตุผล (bug/feature/refactor/audit)
- scope (1 file / 1 module / cross-module)
- risk level ประเมินเบื้องต้น
```

### Step 2 — query_serena_symbols
```
ใช้ Serena MCP:
- find_symbol(name) → definition location
- find_references(symbol) → usage locations
- search_codebase(pattern) → relevant files
บันทึก: symbols_found, files_relevant
```

### Step 3 — collect_relevant_context
```
อ่านเฉพาะไฟล์ที่ Serena ระบุว่าเกี่ยวข้อง
ห้ามอ่านไฟล์ที่ไม่อยู่ใน result ของ Serena
สร้าง context map: file → relevant sections
```

### Step 4 — impact_analysis
```
วิเคราะห์:
- ถ้าแก้ X จะกระทบ Y, Z ไหม
- มี test ที่ cover ส่วนนี้ไหม
- มี side effect ที่ควรระวังไหม
output: impact_report (list of affected files/functions)
```

### Step 5 — plan_changes
```
วางแผนการแก้ไขแบบ step-by-step
ระบุ: file, function, old_behavior, new_behavior
ถ้า risk >= 3 → ขอ CONFIRM STAGING ก่อน
```

### Step 6 — apply_changes
```
แก้ไขตาม plan ทีละ step
บันทึก: changed_files, lines_changed
ห้ามแก้นอกเหนือจาก plan
```

### Step 7 — run_tests_lint
```
รัน lint / type check:
  python: ruff / mypy
  typescript: tsc --noEmit / eslint
รัน unit tests ถ้ามี
บันทึก: test_results, lint_errors
```

### Step 8 — report_changes
```
สรุปผล:
- changed_files (list)
- symbols_modified
- test_results
- warnings / side effects
- qa_verified (ถ้าเป็น refactor ใหญ่)
- security_checked (ถ้าเกี่ยวกับ auth/security)
```

---

## Decision Points (Hybrid)

| จุด | เงื่อนไข | Action |
|-----|---------|--------|
| Impact analysis พบ risk >= 3 | cross-service change | ขอ `CONFIRM STAGING` |
| Refactor ใหญ่ (>5 files) | — | QA Agent verify |
| Security-related code | auth, secret, permission | Security Agent ตรวจ |
| New library/dependency | — | R&D Agent ประเมิน |

---

## Rollback Plan

```bash
# ถ้าการแก้ไขทำให้ระบบพัง
git diff --stat        # ดูไฟล์ที่เปลี่ยน
git stash             # เก็บการเปลี่ยนแปลง
git stash pop         # คืนถ้าต้องการ
```

---

## Accountability Log Template

```yaml
workflow: code-intelligence-workflow
owner_agent: programmer
task_intent: ""
serena_queries: []
files_inspected: []
impact_report: []
changed_files: []
tests_run: []
lint_clean: true
qa_verified: false
security_checked: false
approval_required: false
approval_phrase: ""
completed_at: ""
```
