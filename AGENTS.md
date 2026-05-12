# AI Control Center — Agent Operating System

## ภาพรวม

AI Control Center เป็น **Hybrid Workflow-Agent Operating System** แบบ Docker-first ที่ออกแบบให้ทุกงานผ่านระบบ agent อย่างเป็นระบบ มี audit trail ครบ และพร้อมย้ายขึ้น AlmaLinux 8 + CWP Production

ระบบนี้คือ **Hybrid Workflow-Agent System** — ไม่ใช่ pure agent, ไม่ใช่ pipeline ธรรมดา แต่เลือก execution mode ตามชนิดงาน

---

## Execution Mode Philosophy

```
Workflow-first → Agent-when-needed → Hybrid by design → Accountability always
```

| Mode | ใช้เมื่อ | ตัวอย่าง |
|------|---------|---------|
| **Workflow** | ขั้นตอนชัด, ทำซ้ำได้, reliability สูง | health check, ingest, backup, lint |
| **Agent** | open-ended, ต้อง reasoning หลายรอบ | debug, R&D, security investigation |
| **Hybrid** | มี workflow หลัก + agent วิเคราะห์บางจุด | deploy, browser QA, prod readiness |

### กฎการเลือก Mode
- ถ้า **predictable + ขั้นตอนชัด** → Workflow
- ถ้า **open-ended + ต้องวิเคราะห์** → Agent
- ถ้า **มีโครงหลัก + ต้อง judgment บางจุด** → Hybrid
- **ห้ามใช้ Agent แทน Workflow ที่ทำงานได้ดีกว่า ถูกกว่า ปลอดภัยกว่า**
- **ห้ามสร้าง agent หลายตัวเพื่อให้ diagram ดูซับซ้อน**

### Autonomy Levels
| Level | ความหมาย | Approval |
|-------|---------|---------|
| 0 | Read-only | ไม่ต้อง |
| 1 | Suggest / plan-only | ไม่ต้อง |
| 2 | Execute safe workflow (dev/wsl) | ไม่ต้อง |
| 3 | Agent แก้ไฟล์ dev | ไม่ต้อง |
| 4 | Staging action | `CONFIRM STAGING` |
| 5 | Production / Destructive | `CONFIRM DEPLOY` หรือ `CONFIRM DANGEROUS` |

---

## Workflow Registry
ดู `core/workflows/index.json` สำหรับ workflows ที่พร้อมใช้งาน

| Workflow ID | Mode | Agents |
|-------------|------|--------|
| rag-ingest-workflow | workflow | rag-curator |
| docker-health-check-workflow | workflow | observer |
| browser-qa-workflow | hybrid | qa, designer |
| backup-workflow | workflow | administrator |
| prod-readiness-workflow | hybrid | devops, security |
| deployment-workflow | hybrid | devops, qa |
| security-review-workflow | hybrid | security |
| rag-evaluation-workflow | hybrid | rag-curator |
| log-review-workflow | hybrid | observer |

---

## Accountability Requirements
ทุก task ต้องตอบได้ว่า:
- ใครเป็น **owner agent**
- ใช้ **mode** อะไร และทำไม
- ใช้ **workflow** ไหน
- **tool** ไหนถูกใช้
- **command** ไหนถูกรัน (ผ่าน RTK หรือไม่)
- ใคร **approve**
- **verify** อย่างไร
- **rollback** อย่างไร
- **error** เกิดที่ step ไหน

---

## กฎหลัก (Core Rules)

### 1. ทุกงานต้องผ่าน Manager Agent ก่อน
- ห้าม agent ใดทำงานโดยตรงโดยไม่ผ่าน Manager Agent
- Manager Agent สร้าง Task Packet → เลือก agent → เลือก skill → ประเมิน risk

### 2. กระบวนการทุกงาน: Plan → Build → Verify → Report
```
Plan:   วางแผนงาน, เลือก skill, ประเมิน risk, ขอ approval ถ้าจำเป็น
Build:  ดำเนินงานตาม plan ที่ approved
Verify: ทดสอบผล, health check, ตรวจ side effects
Report: สรุปเป็นภาษาไทยอ่านง่าย พร้อม file list + command list + verify steps
```

### 3. Approval Policy
- **Level 1 (Read-only)**: วิเคราะห์, ค้น, สรุป, อ่าน log → ไม่ต้อง approval
- **Level 2 (Dev Change)**: แก้ไฟล์ dev, test, lint → ไม่ต้อง approval ถ้า env=wsl/dev
- **Level 3 (Service Operation)**: restart/rebuild/staging → ต้อง `CONFIRM STAGING`
- **Level 4 (Production Deploy)**: deploy prod, SSL, reverse proxy → ต้อง `CONFIRM DEPLOY` + backup + rollback + verify
- **Level 5 (Destructive)**: delete DB, remove volume, firewall reset → ต้อง `CONFIRM DANGEROUS` + impact statement

### 4. ข้อห้ามเด็ดขาด
- **ห้าม** production deploy โดยไม่มี approval
- **ห้าม** รัน destructive commands (rm -rf /, drop database, delete volume, chmod -R 777 /)
- **ห้าม** expose secrets ใน log หรือ output
- **ห้าม** mount docker.sock โดย default
- **ห้าม** นำ R&D experiment เข้า production โดยตรง
- **ห้าม** expose Postgres / Redis / Qdrant ออก internet

---

## Agents

### 1. Manager Agent
**ไฟล์**: `core/agents/manager/AGENT.md`
- รับคำสั่ง → สร้าง Task Packet → เลือก agent + skill → ประเมิน risk → ขอ approval → สรุปผล
- ต้องบันทึก task_id, source, risk_level ทุกงาน

### 2. Programmer Agent
**ไฟล์**: `core/agents/programmer/AGENT.md`
- เขียนโค้ด, แก้ bug, API, frontend, backend, refactor, test
- ต้องสรุปไฟล์ที่แก้ทุกครั้ง

### 3. DevOps Agent
**ไฟล์**: `core/agents/devops/AGENT.md`
- Docker, Docker Compose, build, deploy, rollback, health check
- ต้อง verify หลัง deploy ทุกครั้ง

### 4. Administrator Agent
**ไฟล์**: `core/agents/administrator/AGENT.md`
- AlmaLinux 8, CWP, SSL, reverse proxy, firewall, backup, permission
- Risk Level 4-5 ต้องมี approval

### 5. Designer Agent
**ไฟล์**: `core/agents/designer/AGENT.md`
- UI/UX, mobile-first dashboard, design system, component, Storybook/Penpot profile

### 6. QA Agent
**ไฟล์**: `core/agents/qa/AGENT.md`
- test, verify, regression, checklist, acceptance criteria

### 7. Security Agent
**ไฟล์**: `core/agents/security/AGENT.md`
- secrets, permission, env, dependency, network exposure, production risk, command safety

### 8. RAG Curator Agent
**ไฟล์**: `core/agents/rag-curator/AGENT.md`
- documents, chunking, embedding, metadata, search quality

### 9. Observer Agent
**ไฟล์**: `core/agents/observer/AGENT.md`
- health, logs, uptime, alerts, docker status summary

### 10. R&D Agent
**ไฟล์**: `core/agents/research/AGENT.md`
- วิจัยเครื่องมือใหม่, PoC, benchmark, compatibility check
- **ผลลัพธ์ต้องมี Adoption Status**: reject | keep watching | PoC only | staging | production-ready
- **ห้าม** นำของทดลองเข้า production โดยตรง
- การทดลองต้องอยู่ใน profile research sandbox เท่านั้น

---

## Output Report Format (ทุกงาน)

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
- `curl http://...` หรือ `docker ps` หรืออื่น ๆ

### ข้อควรระวัง
- [ถ้ามี]
```

---

## Architecture Flow

```
Smartphone / ChatGPT / Dashboard
        ↓
Mobile Gateway (port 8088)
        ↓
TTO API — Thai Token Optimizer (port 8091)
        ↓
RTK Bridge — Safe Command Layer (port 8092)
        ↓
Manager Agent
        ↓
Skill Router + Risk Policy + Approval Policy
        ↓
Programmer / DevOps / Administrator / Designer / QA / Security / RAG Curator / Observer / R&D
        ↓
Worker / Hermes Bridge / agentUniverse Bridge (port 8095)
        ↓
RAG API + Qdrant (port 8090 / 6333)
        ↓
Postgres (5432) + Redis (6379)
        ↓
QA + Security + Observer (port 8094)
        ↓
Mobile Report
```

## Dev / QA / Design / Observer / R&D Tool Layer

```
Claude / Windsurf / Hermes / Agent
        ↓
Chrome DevTools MCP  [local/dev/staging ONLY]
        ↓
Chrome Browser
        ↓
Local Web Dashboard (127.0.0.1:3000) / API Endpoints
        ↓
QA Report / UI Report / Performance Report
```

### Chrome DevTools MCP — กฎการใช้งาน
- **ใช้เฉพาะ local / dev / staging เท่านั้น**
- **ห้าม login production account จริง**
- **ห้ามเปิดหน้าเว็บที่มี secret / token / password**
- **ห้ามบันทึก screenshot ที่มี credential**
- **ถ้าพบ secret บนหน้าเว็บ → หยุดทันทีและแจ้ง Security Agent**

### Agents ที่ใช้ Chrome DevTools MCP
- **Designer** — UI, responsive, layout, loading/error/empty state
- **QA** — user flow, form, submit, console/network error
- **Observer** — health page, logs page, service status via browser
- **R&D** — benchmark, Lighthouse, UI library comparison
- **Security** — ตรวจ secret leak, API response exposure, CORS

---

## Skills Index
ดู `core/skills/index.json` สำหรับ skill ที่พร้อมใช้งาน
โหลดเฉพาะ SKILL.md ที่เกี่ยวข้องกับงาน เพื่อประหยัด token
