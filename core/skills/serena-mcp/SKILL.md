# Skill: serena-mcp — Code Intelligence Layer

**skill_id**: serena-mcp  
**agents**: programmer, qa, security, research, manager  
**risk_level**: 1 (read-only code navigation — ไม่แก้ไฟล์โดยตรง)  
**environment**: local, dev, staging  
**type**: Dev / Code Intelligence Tool — ไม่ใช่ production runtime  

---

## วัตถุประสงค์

Serena MCP เป็น **Code Intelligence Layer** ช่วยให้ AI เข้าใจ codebase แบบ semantic  
**ก่อนแก้โค้ด refactor review หรือ debug ต้องใช้ Serena หา context ที่เกี่ยวข้องก่อนเสมอ**

เป้าหมายหลัก:
- ลด token ในงาน coding โดยอ่านเฉพาะส่วนที่เกี่ยวข้อง (ประหยัด ~80%)
- เพิ่มความแม่นยำในการแก้โค้ด
- ทำ impact analysis ก่อน refactor ป้องกัน regression

---

## ความสามารถ (Serena MCP Tools)

| Tool | คำอธิบาย | ตัวอย่าง |
|------|----------|---------|
| `find_symbol` | หา definition ของ function/class/variable | `find_symbol("process_task")` |
| `find_references` | หาทุกที่ที่ symbol ถูกใช้ | `find_references("TaskRequest")` |
| `get_definition` | ดู body ของ symbol | `get_definition("create_task")` |
| `get_file_outline` | โครงสร้าง symbols ในไฟล์ | `get_file_outline("main.py")` |
| `search_codebase` | Semantic + text search ทั้ง repo | `search_codebase("file upload handler")` |
| `rename_symbol` | Rename ทั้ง codebase อย่างปลอดภัย | `rename_symbol("old_fn", "new_fn")` |
| `impact_analysis` | ถ้าแก้ X จะกระทบอะไรบ้าง | `impact_analysis("TaskResult")` |
| `get_call_graph` | Call graph ของ function | `get_call_graph("process_task")` |

---

## Use Cases

### 1. Semantic Code Navigation
```
agent ต้องการแก้ endpoint /tasks/{id}/result
→ find_symbol("update_task_result") → services/mobile-gateway/app/main.py:189
→ find_references("update_task_result") → ถูกเรียกจาก worker, tests
→ อ่านเฉพาะ 3 ไฟล์นี้ — ไม่ต้องอ่านทั้ง repo
```

### 2. Bug Investigation
```
รายงาน: "final_report ถูก overwrite เมื่อ worker update result"
→ find_symbol("update_task_result") → หา logic
→ get_call_graph("update_task_result") → หา caller ทั้งหมด
→ find_references("result") → หาว่าใคร write ลง result บ้าง
→ ระบุ root cause: worker PATCH ทับ user-saved data
```

### 3. Impact Analysis ก่อน Refactor
```
แผน: เปลี่ยน TaskResult schema — เพิ่ม field "verification_status"
→ impact_analysis("TaskResult")
→ ผล: กระทบ main.py:89,156,203 | models.py:45 | command.vue:112
→ วางแผน: แก้ 5 ไฟล์ → risk level 2 → ไม่ต้อง approval
```

### 4. Refactor Planning
```
ต้องการ extract ฟังก์ชัน _detect_and_mask() ออกเป็น module
→ find_references("_detect_and_mask") → ถูกใช้ที่ไหนบ้าง
→ get_file_outline("worker/app/main.py") → ดู structure
→ วางแผน: สร้าง security.py → ย้าย function → update imports
```

### 5. Code Review
```
review PR: เพิ่ม file upload endpoint
→ get_file_outline("main.py") → ดู endpoint list ทั้งหมด
→ find_references("ALLOWED_EXTENSIONS") → ตรวจ consistency
→ search_codebase("secret detection") → มีที่อื่นไหม
```

### 6. Security Audit
```
ตรวจหา hardcoded credential
→ search_codebase("password") → หา matches
→ search_codebase("api_key") → หา matches
→ find_references("os.environ") → ตรวจว่า env ใช้ถูกต้อง
```

### 7. Feature Entry Point Mapping
```
เพิ่ม feature: file type classification
→ search_codebase("attachment") → หา existing attachment code
→ find_symbol("create_task") → หา entry point
→ get_call_graph("create_task") → เข้าใจ flow
→ วางแผนว่าจะ inject classification ที่ไหน
```

---

## Serena MCP ต่างจาก RAG

| | RAG | Serena MCP |
|---|-----|-----------|
| **Source** | เอกสาร, wiki, SOP, notes | Source code |
| **Unit** | Document chunk | Symbol, function, class, file |
| **Query** | Natural language | Symbol name, pattern, file path |
| **Output** | Text passages | File path + line number + context |
| **เมื่อไรใช้** | ต้องการ domain knowledge | ต้องการเข้าใจหรือแก้ code |
| **ตัวอย่าง** | "RAG chunking ทำยังไง" | "function X ถูกเรียกที่ไหน" |

**กฎสำคัญ**:
- ❌ ห้ามใช้ RAG แทน Serena เมื่องานคือ code navigation
- ❌ ห้ามใช้ Serena แทน RAG เมื่องานคือ document/wiki retrieval
- ❌ ห้ามอ่านทั้ง repo ถ้า Serena หา context ให้ได้

---

## Workflow การใช้งาน (8 Steps)

```
Step 1: identify_task_intent
  ระบุ: แก้อะไร (symbol/file), เหตุผล (bug/feature/refactor/audit), scope

Step 2: query_serena_symbols
  find_symbol / find_references / search_codebase
  บันทึก: symbols_found, files_relevant

Step 3: collect_relevant_context
  อ่านเฉพาะไฟล์ที่ Serena ระบุ
  ห้ามอ่านไฟล์นอก Serena result

Step 4: impact_analysis
  วิเคราะห์: ถ้าแก้ X กระทบ Y, Z ไหม
  output: impact_report (affected files/functions)

Step 5: plan_changes
  plan แบบ step-by-step: file, function, old→new
  ถ้า risk >= 3 → ขอ CONFIRM STAGING

Step 6: apply_changes
  แก้ตาม plan เท่านั้น — ห้ามออกนอก scope

Step 7: run_tests_lint
  ruff/mypy (Python) | tsc/eslint (TypeScript)
  รัน unit tests ถ้ามี

Step 8: report_changes
  changed_files, symbols_modified, test_results,
  qa_verified (refactor ใหญ่), security_checked (auth/secret)
```

---

## กฎการใช้งาน (Mandatory)

- **ใช้ Serena ก่อนเสมอ** — query ก่อนเปิดไฟล์ใดๆ
- **ห้ามแก้ไฟล์โดยไม่มี impact analysis ก่อน**
- **ห้ามอ่านทั้ง repo** ถ้า Serena ระบุ context ให้ได้
- **ห้าม deploy** ผ่าน Serena
- **ห้ามรัน destructive command** ผ่าน Serena
- **Refactor ใหญ่ (>5 files)** → QA Agent verify ก่อน merge
- **Security-sensitive code** (auth, secret, permission) → Security Agent ตรวจ
- **Library/dependency ใหม่** → R&D Agent ประเมิน adoption status ก่อน

---

## Agent ที่ใช้ Serena MCP

| Agent | Use Case |
|-------|---------|
| **programmer** | แก้ bug, feature, refactor, code review, bug investigation |
| **qa** | ตรวจ test coverage, หา untested paths, regression check |
| **security** | audit code, หา dangerous patterns, secret scan, permission check |
| **research** | benchmark, PoC, ศึกษา codebase ใหม่ |
| **manager** | impact analysis ประเมิน risk ของ task (read-only เท่านั้น) |

---

## Accountability

```yaml
serena_session:
  task_intent: ""
  serena_queries:
    - tool: find_symbol
      input: ""
      result_files: []
  files_inspected: []
  impact_report:
    affected_files: []
    breaking_change: false
  changes_made: []
  tests_run: []
  lint_clean: true
  qa_verified: false        # ต้องเป็น true ถ้า refactor > 5 files
  security_checked: false   # ต้องเป็น true ถ้าเกี่ยวข้องกับ auth/security
```
