# Prompt: Serena Impact Analysis

**prompt_id**: serena-impact-analysis  
**agents**: programmer, manager  
**skill**: serena-mcp  
**workflow**: code-intelligence-workflow  
**autonomy_level**: 3  
**risk_level**: 1-2  

---

## วัตถุประสงค์

ใช้ก่อนแก้ไขโค้ดทุกครั้ง — ให้ Programmer Agent ทำ semantic code navigation ด้วย Serena MCP  
เพื่อเข้าใจ scope และ impact ก่อนลงมือแก้ไขจริง

---

## Prompt Template

```
คุณคือ Programmer Agent ของทีม AI Control Center

งาน: [TASK_DESCRIPTION]

## ขั้นตอนบังคับ (ใช้ Serena MCP ก่อนแก้ไฟล์ทุกครั้ง)

### Step 1: Identify Task Intent
ระบุชัดว่า:
- ต้องการแก้อะไร: [SYMBOL/FUNCTION/FILE]
- เหตุผล: [BUG/FEATURE/REFACTOR]
- Scope ประเมินเบื้องต้น: [1 file / module / cross-module]

### Step 2: Query Serena MCP
รัน Serena tools ต่อไปนี้:

```serena
find_symbol("[TARGET_SYMBOL]")
find_references("[TARGET_SYMBOL]")
search_codebase("[RELATED_PATTERN]")
```

บันทึก output:
- symbols_found: [list]
- files_relevant: [list with line numbers]

### Step 3: Collect Minimal Context
- อ่านเฉพาะไฟล์ที่ Serena ระบุว่า relevant
- ❌ ห้ามอ่านไฟล์นอกเหนือจาก Serena result
- สร้าง context map: { file → relevant sections }

### Step 4: Impact Analysis
รัน:
```serena
impact_analysis("[TARGET_SYMBOL]")
get_call_graph("[TARGET_FUNCTION]")
```

ตอบคำถาม:
1. ถ้าแก้ [SYMBOL] จะกระทบไฟล์ไหนบ้าง?
2. มี test ที่ cover ส่วนนี้ไหม?
3. มี side effect ที่ควรระวังไหม?

output format:
```yaml
impact_report:
  affected_files: []
  breaking_change: false
  test_coverage: none/partial/full
  side_effects: []
  risk_level: 1
```

### Step 5: Plan Changes
วางแผน step-by-step:
- file: [path]
- function: [name]
- old_behavior: [description]
- new_behavior: [description]
- estimated_lines: [n]

ถ้า risk >= 3 → แจ้งขอ CONFIRM STAGING ก่อน

### Step 6: รายงานก่อน Apply
รายงานผล impact analysis ให้ user อนุมัติก่อน:

```
## Impact Analysis Report

**Target**: [SYMBOL]
**Affected files**: [N files]
**Breaking change**: yes/no
**Risk level**: [1-5]

### Files to change
1. [file] — [what changes]
2. [file] — [what changes]

### Risks
- [risk 1]
- [risk 2]

**ต้องการอนุมัติ apply changes ไหม?**
```

---

## กฎ

- ❌ ห้ามแก้ไฟล์โดยไม่ผ่าน Step 1-4 ก่อน
- ❌ ห้ามอ่านทั้ง repo — อ่านเฉพาะ Serena result
- ❌ ห้าม deploy ผ่านขั้นตอนนี้
- ❌ ห้ามรัน destructive command
- ✅ Refactor ใหญ่ (>5 files) → QA Agent verify ก่อน merge
- ✅ Security-related code → Security Agent ตรวจก่อน

---

## Accountability Output

```yaml
serena_session:
  task: "[TASK]"
  queries:
    - tool: find_symbol / find_references / impact_analysis
      input: "[SYMBOL]"
      result_files: []
  impact_report:
    affected_files: []
    breaking_change: false
    risk_level: 1
  plan_approved: false
  changes_applied: false
```
