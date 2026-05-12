---
title: "Backup & Restore"
category: ops
tags: [backup, restore, volume, data, recovery, snapshot]
status: stable
updated: 2026-05-12
---

# Backup & Restore

## สิ่งที่ต้อง Backup

| Data | Location | ความสำคัญ |
|------|----------|----------|
| Task data (JSON) | `data/tasks.json` | Critical |
| Uploaded files | `data/uploads/` | High |
| Qdrant vectors | Docker volume `qdrant_data` | High |
| Prompt exports | `data/exports/` | Medium |
| Config files | `.env`, `docker-compose.yml` | Critical |
| Wiki docs | `docs/wiki/` | High |

---

## Backup Strategy

### Daily Backup (Automated)

```bash
#!/bin/bash
# /opt/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/ai-control-center/$DATE"
PROJECT_DIR="/mnt/e/Project/laragon/www/ai-control-center"

mkdir -p "$BACKUP_DIR"

# Backup data files
cp -r "$PROJECT_DIR/data/" "$BACKUP_DIR/data/"

# Backup config (ไม่รวม .env ที่มี secret)
cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_DIR/"
cp "$PROJECT_DIR/docker-compose.override.yml" "$BACKUP_DIR/" 2>/dev/null || true

# Backup wiki
cp -r "$PROJECT_DIR/docs/wiki/" "$BACKUP_DIR/wiki/"

# Qdrant snapshot
curl -X POST http://localhost:6333/collections/wiki/snapshots
SNAPSHOT=$(curl -s http://localhost:6333/collections/wiki/snapshots | python3 -c "import sys,json; snaps=json.load(sys.stdin)['result']; print(snaps[-1]['name']) if snaps else print('')")
if [ -n "$SNAPSHOT" ]; then
    curl -o "$BACKUP_DIR/qdrant-wiki-$SNAPSHOT" \
         "http://localhost:6333/collections/wiki/snapshots/$SNAPSHOT"
fi

echo "Backup completed: $BACKUP_DIR"
```

### Retention Policy

```
Daily backups: เก็บ 7 วัน
Weekly backups: เก็บ 4 สัปดาห์
Monthly backups: เก็บ 3 เดือน
```

---

## Restore Procedures

### Restore Task Data

```bash
# หยุด service ก่อน
docker compose stop mobile-gateway worker

# Restore
cp backup/data/tasks.json data/tasks.json
cp -r backup/data/uploads/ data/uploads/
cp -r backup/data/exports/ data/exports/

# เริ่มใหม่
docker compose start mobile-gateway worker

# ตรวจสอบ
curl http://localhost:8088/tasks | python3 -m json.tool
```

### Restore Qdrant

```bash
# อัปโหลด snapshot กลับเข้า Qdrant
curl -X POST "http://localhost:6333/collections/wiki/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d "{\"location\": \"/qdrant/snapshots/$SNAPSHOT_NAME\"}"

# ตรวจสอบ
curl http://localhost:6333/collections/wiki
```

### Restore จาก Volume Backup

```bash
# หยุด container
docker compose down

# Restore volume (tar method)
docker run --rm \
  -v ai-control-center_qdrant_data:/data \
  -v /opt/backups:/backup \
  alpine tar xzf /backup/qdrant_data.tar.gz -C /data

# เริ่มใหม่
docker compose up -d
```

---

## Disaster Recovery

### กรณี: tasks.json เสียหาย

1. หยุด mobile-gateway: `docker compose stop mobile-gateway`
2. Restore จาก backup ล่าสุด
3. เริ่ม mobile-gateway ใหม่
4. ตรวจ tasks ผ่าน API
5. แจ้งผู้ใช้ว่า task ที่สร้างหลัง backup อาจหาย

### กรณี: Container volume หาย

1. สร้าง volume ใหม่: `docker volume create qdrant_data`
2. Restore จาก snapshot ล่าสุด
3. Re-ingest wiki ถ้า snapshot ไม่สมบูรณ์

### RTO/RPO Target

| | Target |
|--|--------|
| RTO (Recovery Time Objective) | < 30 นาที |
| RPO (Recovery Point Objective) | < 24 ชั่วโมง |

---

## การทดสอบ Backup

ควรทดสอบ restore ทุกเดือน:

```bash
# สร้าง test environment
docker compose -f docker-compose.test.yml up -d

# Restore backup เข้า test
./scripts/restore.sh --target test --backup /opt/backups/latest

# ตรวจ
curl http://localhost:18088/tasks  # test port

# ทำลาย test env
docker compose -f docker-compose.test.yml down -v
```
