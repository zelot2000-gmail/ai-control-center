# CLAUDE.md — กฎสำหรับ Claude / Hermes / Coding Agent

## บังคับอ่านก่อนทุกงาน

1. **อ่าน AGENTS.md** ก่อนแก้ไฟล์ใดๆ
2. **อ่าน core/skills/index.json** ก่อนเลือก skill
3. **โหลดเฉพาะ SKILL.md ที่เกี่ยวข้อง** — ห้ามอ่านทุก skill แบบมั่วๆ เพื่อประหยัด token

---

## Execution Mode — เลือกก่อนลงมือทุกครั้ง

```
Workflow-first → Agent-when-needed → Hybrid by design → Accountability always
```

### ขั้นตอนบังคับก่อนทุกงาน
1. อ่านคำสั่ง → จำแนก keywords
2. **เลือก execution_mode**: workflow | agent | hybrid
3. **ระบุ autonomy_level**: 0-5
4. **เลือก selected_workflow** จาก `core/workflows/index.json` (ถ้า workflow/hybrid)
5. **ระบุ reason_for_mode**
6. ประเมิน risk_level + approval requirement

### กฎการเลือก Mode
| Keywords ในคำสั่ง | Mode |
|-----------------|------|
| health, ตรวจ service, backup, ingest, verify, lint, test | **workflow** |
| วิเคราะห์, debug, root cause, research, R&D, refactor | **agent** |
| deploy, staging, production, restart, ssl, database | **hybrid** |

- **ห้ามใช้ Agent ถ้า Workflow ทำได้ดีกว่า ถูกกว่า ปลอดภัยกว่า**
- **ห้ามสร้าง Agent หลายตัวเพื่อ diagram ดูซับซ้อน**
- **ทุก tool call ต้อง log ลงใน tool_usage_log**
- **ทุก command ต้องผ่าน RTK validate ก่อน ถ้าไม่ใช่ read-only**

### Autonomy Levels
| Level | Action | Approval |
|-------|--------|---------|
| 0 | Read-only | ไม่ต้อง |
| 1 | Plan / suggest only | ไม่ต้อง |
| 2 | Safe workflow (dev/wsl) | ไม่ต้อง |
| 3 | แก้ไฟล์ dev | ไม่ต้อง |
| 4 | Staging | `CONFIRM STAGING` |
| 5 | Production / Destructive | `CONFIRM DEPLOY` / `CONFIRM DANGEROUS` |

---

## กฎการทำงาน

### Plan ก่อนเสมอ
- ทุกงานต้องมี plan ก่อน build
- ระบุ: execution_mode, autonomy_level, ไฟล์ที่จะแก้, risk level, approval ที่ต้องการ
- ถ้าไม่แน่ใจ risk level ให้ถามผู้ใช้ก่อน

### ห้ามเด็ดขาด
- **ห้าม deploy production** — ต้องได้รับ `CONFIRM DEPLOY` ก่อน
- **ห้ามลบ volume** — ต้องได้รับ `CONFIRM DANGEROUS` ก่อน
- **ห้ามเปิดเผย secret** ใน log, output, หรือ response
- **ห้ามรัน destructive command** (rm -rf /, drop database, delete volume)
- **ห้าม mount docker.sock** โดย default
- **ห้ามนำ R&D experiment เข้า production โดยตรง**
- **ห้าม overwrite ไฟล์สำคัญ** โดยไม่จำเป็น

### Verify หลังแก้เสมอ
- ทดสอบ health check หลังแก้ service
- ตรวจ side effects
- รายงานผลเป็นภาษาไทยอ่านง่าย

---

## รายงานผล (Output Format)

```
## รายงานผล

**งาน**: [ชื่องาน]
**task_id**: [uuid]
**risk_level**: [1-5]
**สถานะ**: [สำเร็จ/ล้มเหลว/รอ approval]

### ไฟล์ที่แก้ไข
- path/to/file.ext — [สิ่งที่เปลี่ยน]

### คำสั่งที่รัน
- `command` — [ผลลัพธ์]

### วิธี Verify
- `curl http://...` หรือ `docker ps` หรืออื่นๆ

### ข้อควรระวัง
- [ถ้ามี]
```

---

## Token Saving Rules

- โหลด SKILL.md เฉพาะที่เกี่ยวข้องกับงาน
- ถ้างานเป็น Docker → โหลดแค่ `core/skills/docker-deploy/SKILL.md`
- ถ้างานเป็น RAG → โหลดแค่ `core/skills/rag-ingest/SKILL.md`
- อย่า dump context ทั้งหมด — ค้นหาเฉพาะสิ่งที่ต้องการ

---

## Environment Awareness

- **WSL/dev**: Risk Level 1-2 ไม่ต้อง approval
- **Staging**: Risk Level 3 ต้องมี `CONFIRM STAGING`
- **Production**: Risk Level 4-5 ต้องมี approval phrase + backup + rollback plan

---

## เทคโนโลยีใหม่

ถ้าใช้เครื่องมือหรือ library ที่ไม่มีใน stack ปัจจุบัน:
1. ส่งให้ R&D Agent ก่อน
2. R&D Agent ทำ PoC ใน sandbox/profile research
3. รอผล adoption status ก่อน merge เข้า core
