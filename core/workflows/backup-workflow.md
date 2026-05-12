---
id: backup-workflow
mode: workflow
autonomy_level: 2
risk_level: 2
approval_required: false
responsible_agents: [administrator, observer]
---

# Backup Workflow

## วัตถุประสงค์
สำรองข้อมูลทั้งหมดอย่างมีขั้นตอน ตรวจสอบได้ และพร้อม restore

## Steps

### Step 1: create_timestamp
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="data/backups/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
```

### Step 2: backup_postgres
```bash
docker exec aicc-postgres pg_dump -U aicc_user aicc > "$BACKUP_DIR/postgres.sql"
```
- ตรวจ: file size > 0
- **Fail condition**: container ไม่รัน → หยุด report

### Step 3: backup_documents
```bash
cp -r data/documents "$BACKUP_DIR/documents"
```
- บันทึก: จำนวนไฟล์, total size

### Step 4: backup_core
```bash
cp -r core "$BACKUP_DIR/core"
```
- รวม: agents, skills, workflows, commands

### Step 5: backup_research_docs
```bash
[ -d docs/research ] && cp -r docs/research "$BACKUP_DIR/research"
```

### Step 6: verify_backup_files
- ตรวจทุกไฟล์ใน backup dir มีอยู่จริง
- ตรวจ postgres.sql ไม่ว่าง
- บันทึก checksum (sha256) ของ postgres.sql

### Step 7: write_backup_report
```json
{
  "timestamp": "...",
  "backup_dir": "data/backups/...",
  "postgres_size_bytes": 0,
  "documents_count": 0,
  "checksum_postgres": "sha256:...",
  "status": "success"
}
```
บันทึกไว้ที่: `data/backups/{timestamp}/backup-report.json`

## Accountability Log
```yaml
owner_agent: administrator
tool_usage_log: [docker-exec-pg_dump, cp, sha256sum]
verification_log: [file-size-check, checksum-verify]
rollback_plan: N/A — backup ไม่ modify ข้อมูลต้นฉบับ
```
