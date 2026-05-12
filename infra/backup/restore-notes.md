# Restore Notes

## Backup Location
`data/backups/backup_YYYYMMDD_HHMMSS/`

## Contents
- `postgres_aicc_TIMESTAMP.sql` — Postgres full dump
- `qdrant-backup-note.txt` — ขั้นตอน restore Qdrant volume
- `documents/` — RAG source documents
- `core/` — Agent + skill configs
- `research/` — R&D experiments + decisions
- `.env.example` — Config template (ไม่ใช่ .env จริง)

---

## Restore Postgres

```bash
# 1. ตรวจ container ทำงาน
docker ps | grep aicc-postgres

# 2. Restore dump
cat data/backups/backup_YYYYMMDD_HHMMSS/postgres_aicc_TIMESTAMP.sql | \
  docker exec -i aicc-postgres psql -U aicc_user -d aicc

# 3. ตรวจ
docker exec -it aicc-postgres psql -U aicc_user -d aicc -c "\dt"
```

---

## Restore Qdrant Volume

```bash
# 1. Stop qdrant container
docker compose -f infra/docker/docker-compose.wsl.yml stop qdrant

# 2. Restore volume from tar
docker run --rm \
  -v qdrant_data:/data \
  -v $(pwd)/data/backups:/backup \
  alpine tar xzf /backup/qdrant_data_TIMESTAMP.tar.gz -C /data

# 3. Start qdrant
docker compose -f infra/docker/docker-compose.wsl.yml start qdrant

# 4. Verify
curl http://127.0.0.1:6333/collections
```

---

## Restore Documents

```bash
cp -r data/backups/backup_YYYYMMDD_HHMMSS/documents/* data/documents/

# Re-ingest
make ingest
```

---

## Restore Core Configs

```bash
cp -r data/backups/backup_YYYYMMDD_HHMMSS/core/* core/
```

---

## ข้อควรระวัง
- ตรวจ backup ทุกครั้งก่อน restore ว่าไฟล์ครบ
- ห้าม restore บน production โดยไม่หยุด service ก่อน
- หลัง restore ต้องรัน `make verify` เสมอ
- ห้าม expose Postgres dump ที่มี production data ใน log
