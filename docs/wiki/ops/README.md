# Ops Knowledge Base

**หมวด**: ops  
**สถานะ**: active  

เก็บ Runbook, SOP, troubleshooting guide สำหรับ ai-control-center

---

## หัวข้อที่ควรมี

| ไฟล์ | เนื้อหา | สถานะ |
|------|---------|-------|
| `startup-runbook.md` | ขั้นตอน start/stop ระบบ, verify health | TODO |
| `troubleshooting.md` | ปัญหาที่พบบ่อยและวิธีแก้ | TODO |
| `backup-restore.md` | ขั้นตอน backup และ restore | TODO |
| `deployment-sop.md` | SOP การ deploy สู่ staging/production | TODO |
| `monitoring-guide.md` | วิธีดู log, metric, alert | TODO |

---

## Quick Reference

```bash
# ดู service health
curl http://127.0.0.1:8088/health  # mobile-gateway
curl http://127.0.0.1:8090/health  # rag-api
curl http://127.0.0.1:8091/health  # tto-api
curl http://127.0.0.1:8092/health  # rtk-bridge
curl http://127.0.0.1:8094/health  # observer
curl http://127.0.0.1:8095/health  # worker

# ดู logs
docker compose -f infra/docker/docker-compose.wsl.yml logs -f worker
docker compose -f infra/docker/docker-compose.wsl.yml logs -f mobile-gateway

# restart service
docker compose -f infra/docker/docker-compose.wsl.yml restart worker
```
