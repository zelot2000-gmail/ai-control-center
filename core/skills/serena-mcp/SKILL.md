# Skill: serena-mcp — Code Intelligence Layer

**skill_id**: serena-mcp  
**agents**: programmer, qa, security, research, manager  
**risk_level**: 1 (read-only code navigation — ไม่แก้ไฟล์โดยตรง)  
**environment**: local, dev, staging  
**type**: Dev / Code Intelligence Tool — ไม่ใช่ production runtime  

---

## วัตถุประสงค์

Serena MCP เป็น **Code Intelligence Layer** ช่วยให้ AI เข้าใจ codebase แบบ semantic  
ก่อนแก้โค้ดหรือ review ให้ใช้ Serena หา context ที่เกี่ยวข้องก่อน

**เป้าหมายหลัก**:
- ลด token ที่ใช้ในงาน coding โดยอ่านเฉพาะส่วนที่เกี่ยวข้อง
- เพิ่มความแม่นยำในการแก้โค้ด
- ทำ impact analysis ก่อน refactor

---

## ความสามารถ

| ความสามารถ | คำสั่ง / การใช้งาน |
|-----------|-----------------|
| หา symbol definition | ค้น function/class/variable จากชื่อ |
| หา references | หาว่า symbol ถูกใช้ที่ไหนบ้างใน codebase |
| หา relevant files | ระบุไฟล์ที่เกี่ยวข้องกับ task โดยไม่อ่านทั้ง repo |
| Impact analysis | ถ้าแก้ X จะกระทบ Y, Z ไหม |
| Semantic search | ค้นหา code ด้วยความหมาย ไม่ใช่แค่ text match |
| Refactor assist | เปลี่ยนชื่อ symbol ทั้ง codebase อย่างปลอดภัย |
| Code review support | ดู structure ของ module ก่อน review |

---

## เมื่อไรต้องใช้ Serena MCP

```
✅ ต้องการแก้ function ที่ไม่รู้ว่าถูกใช้ที่ไหน
✅ ต้องการ refactor class/module
✅ ต้องการทำ impact analysis ก่อน PR
✅ ต้องการหา entry point ของ feature ใหม่
✅ codebase ใหญ่ อ่านทั้งหมดไม่ไหว
✅ ต้องการรู้ว่า middleware / dependency chain เป็นอย่างไร
✅ security audit — หา hardcoded values หรือ dangerous patterns
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

**กฎสำคัญ**:
- ❌ ห้ามใช้ RAG แทน Serena เมื่องานคือ code navigation
- ❌ ห้ามใช้ Serena แทน RAG เมื่องานคือ document/wiki retrieval

---

## Workflow การใช้งาน

```
1. รับ task intent (เช่น: แก้ bug ใน /process-task endpoint)
2. ใช้ Serena MCP query symbols ที่เกี่ยวข้อง
   → find_symbol("process_task")
   → find_references("TaskRequest")
3. รวบรวม relevant file paths + line numbers
4. ทำ impact analysis
   → อะไรจะกระทบถ้าแก้ function นี้
5. วางแผนการแก้ไข (plan only — ยังไม่แก้)
6. ขอ approval ถ้า risk >= 3
7. Apply changes ตาม plan
8. Run tests / lint
9. Report: changed files, test results, side effects
```

---

## กฎการใช้งาน

- **ใช้ก่อนอ่านไฟล์จำนวนมาก** — query Serena ก่อนเพื่อระบุ relevant files
- **ห้ามอ่านทั้ง repo** โดยไม่จำเป็น
- **ห้าม deploy** ผ่าน Serena
- **ห้ามรัน destructive command** ผ่าน Serena
- **ห้ามแก้ไฟล์โดยไม่มี impact analysis** ก่อน
- **Refactor ใหญ่** → ต้องให้ QA Agent verify หลังแก้
- **เกี่ยวกับ security** → ต้องให้ Security Agent ตรวจ
- **Library/tool ใหม่** → ต้องให้ R&D Agent ประเมินก่อน

---

## Agent ที่ใช้ Serena MCP

| Agent | กรณีใช้ |
|-------|--------|
| **programmer** | แก้ bug, feature, refactor, code review |
| **qa** | ตรวจ test coverage, หา untested paths |
| **security** | audit code, หา pattern อันตราย |
| **research** | benchmark, PoC, ศึกษา codebase |
| **manager** | impact analysis เมื่อประเมิน risk ของ task |

---

## Accountability

```yaml
เมื่อใช้ Serena:
  - บันทึก: queries_used, files_inspected, symbols_found
  - impact_analysis: [list of affected files/functions]
  - บันทึก: changes_made, tests_run, qa_verified (ถ้า refactor)
```
