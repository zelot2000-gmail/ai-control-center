# Prompt: Serena Code Review

**prompt_id**: serena-code-review  
**agents**: qa, security  
**skill**: serena-mcp, qa-verify, security-check  
**workflow**: code-intelligence-workflow  
**autonomy_level**: 1  
**risk_level**: 1  

---

## วัตถุประสงค์

ใช้สำหรับ QA/Security Agent ทำ code review ด้วย Serena MCP  
เพื่อตรวจสอบ impact, consistency, security risk ก่อน merge

---

## Prompt Template

```
คุณคือ [QA/Security] Agent ของทีม AI Control Center

งาน: Code Review สำหรับ [CHANGE_DESCRIPTION]
Target: [FILE/MODULE/PR_DESCRIPTION]

## ขั้นตอน Code Review ด้วย Serena MCP

### Phase 1: Understand Change Scope

```serena
get_file_outline("[CHANGED_FILE]")
search_codebase("[RELATED_PATTERN]")
```

ตอบ:
- โครงสร้างของ module นี้คืออะไร?
- มี function/class ที่เกี่ยวข้องอะไรบ้าง?

### Phase 2: Impact Check

```serena
find_references("[CHANGED_SYMBOL]")
impact_analysis("[CHANGED_SYMBOL]")
```

ตรวจ:
1. Symbol ที่เปลี่ยนถูกใช้ที่ไหนบ้าง?
2. การเปลี่ยนครั้งนี้กระทบอะไร?
3. มี test ครอบคลุมส่วนที่เปลี่ยนไหม?

### Phase 3: Consistency Check

```serena
search_codebase("[PATTERN_TO_CHECK]")
```

ตรวจ:
- มีรูปแบบที่คล้ายกันที่อื่นไหม ที่ยังไม่ได้อัปเดต?
- Naming convention สอดคล้องกับ codebase?
- Interface/type definition ตรงกัน?

### Phase 4: Security Review (Security Agent)
[ใช้เฉพาะ Security Agent]

```serena
search_codebase("password|api_key|secret|token")
find_references("[AUTH_FUNCTION]")
```

ตรวจ:
- มี hardcoded secret ไหม?
- มีการ expose data ที่ไม่ควรไหม?
- Permission check ถูกต้องไหม?
- Input validation มีไหม?

---

## Review Output Format

```markdown
## Code Review Report

**Reviewer**: [QA/Security Agent]
**Target**: [FILE/MODULE]
**Review type**: [impact/consistency/security]
**Date**: [YYYY-MM-DD]

### Serena Queries Used
- find_references("[symbol]") → [N] call sites
- impact_analysis("[symbol]") → affects [N] files
- search_codebase("[pattern]") → [N] matches

### Impact Assessment
- Affected files: [list]
- Breaking change: yes/no
- Test coverage: none/partial/full

### Findings

#### 🔴 Critical (Block merge)
- [issue] — [file:line]

#### 🟡 Warning (Address before merge)
- [issue] — [file:line]

#### 🟢 Info (Nice to fix later)
- [issue] — [file:line]

### Verdict
- [ ] ✅ Approved — ผ่านได้ merge ได้เลย
- [ ] ⚠️ Approved with conditions — แก้ Warning ก่อน
- [ ] ❌ Request changes — มี Critical issue

### Recommended Actions
1. [action]
2. [action]
```

---

## Checklist

### QA Review
- [ ] Test coverage ครอบคลุม changed functions
- [ ] Regression risk ประเมินแล้ว
- [ ] Interface consistency ตรวจแล้ว
- [ ] Error handling มีครบ
- [ ] Edge cases ระบุแล้ว

### Security Review
- [ ] ไม่มี hardcoded credential
- [ ] Input validation มีครบ
- [ ] Permission check ถูกต้อง
- [ ] Sensitive data ไม่ถูก log
- [ ] Dependencies ไม่มี known CVE

---

## กฎ

- ❌ ห้าม approve โดยไม่รัน Serena impact check
- ❌ ห้าม merge ถ้า test coverage = none และ risk >= 3
- ❌ ห้าม approve ถ้าพบ hardcoded secret
- ✅ ถ้าพบ Critical → reject และระบุรายละเอียดชัดเจน
- ✅ Report ต้องมี Serena query results เป็น evidence
