---
title: "Docker + WSL Operations"
category: ops
tags: [docker, wsl, almalinux, compose, container, windows, hermes]
status: stable
updated: 2026-05-13
---

# Docker + WSL Operations

## Setup Overview

```
Windows 11
└─ WSL2
   └─ AlmaLinux-8 (distro name: AlmaLinux-8)
      └─ Docker Engine (docker daemon รันใน WSL)
         ├─ ai-control-center stack (profile: core)
         └─ qdrant
```

**ข้อสำคัญ**: Docker ไม่ได้รันบน Windows — ต้องใช้คำสั่งผ่าน WSL เสมอ

---

## Pattern การรัน Docker Command

```powershell
# รัน docker command ผ่าน WSL
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core ps"
```

**ห้าม** รัน `docker` โดยตรงใน PowerShell — จะ error "docker not found"

---

## ข้อสำคัญ: --env-file และ --profile

`docker-compose.wsl.yml` อยู่ที่ `infra/docker/` แต่ `.env` อยู่ที่ project root  
ต้องส่ง `--env-file .env` ทุกครั้งเมื่อรัน docker compose จาก WSL:

```bash
# ถูกต้อง — รันจาก project root
docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core up -d

# ผิด — ไม่มี --env-file ทำให้ env vars ไม่ถูกโหลด (ใช้ default จาก docker-compose แทน)
docker compose -f infra/docker/docker-compose.wsl.yml --profile core up -d
```

Services ทั้งหมดอยู่ใน `profile: core` — ต้องใส่ `--profile core` เสมอ

---

## Path Mapping

| Windows Path | WSL Path |
|-------------|----------|
| `E:\Project\laragon\www\ai-control-center` | `/mnt/e/Project/laragon/www/ai-control-center` |
| `C:\Users\zelot` | `/mnt/c/Users/zelot` |

---

## Common Commands

### ดู status ทุก service

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core ps"
```

### Rebuild และ restart service เดียว

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core up -d --build worker"
```

### ดู logs

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core logs -f --tail=50 worker"
```

### Exec ใน container

```powershell
wsl -d AlmaLinux-8 -- docker exec -it aicc-worker bash
```

### ดู resource usage

```powershell
wsl -d AlmaLinux-8 -- bash -c "docker stats --no-stream"
```

---

## Services Port Map

| Service | Container | Port | URL |
|---------|-----------|------|-----|
| mobile-gateway | aicc-mobile-gateway | 8088 | http://localhost:8088 |
| rag-api | aicc-rag-api | 8090 | http://localhost:8090 |
| tto-api | aicc-tto-api | 8091 | http://localhost:8091 |
| rtk-bridge | aicc-rtk-bridge | 8092 | http://localhost:8092 |
| webhook-gateway | aicc-webhook-gateway | 8093 | http://localhost:8093 |
| observer | aicc-observer | 8094 | http://localhost:8094 |
| worker | aicc-worker | 8095 | http://localhost:8095 |
| qdrant | aicc-qdrant | 6333 | http://localhost:6333 |
| web-dashboard | aicc-web-dashboard | 3000 | http://localhost:3000 |

---

## Docker Network

Network ชื่อ `docker_ai_net` (docker compose prefix `docker` + network name `ai_net`):

```bash
# ตรวจชื่อ network จริง
docker network ls | grep ai_net
# → docker_ai_net
```

ใช้ชื่อนี้เมื่อต้องการ attach container เพิ่มเติมเข้า network เดียวกัน:

```bash
docker run --rm --network docker_ai_net ...
```

---

## Worker: extra_hosts สำหรับ Hermes บน Host

Worker service ต้องการ `extra_hosts: host.docker.internal:host-gateway` เพื่อให้สามารถเรียก Hermes API ที่รันบน Windows/WSL host ได้:

```yaml
# infra/docker/docker-compose.wsl.yml
worker:
  extra_hosts:
    - "host.docker.internal:host-gateway"
  environment:
    - HERMES_API_URL=${HERMES_API_URL:-}
```

ตัวอย่าง `.env` เมื่อ Hermes รันบน host port 20199:

```env
HERMES_API_URL=http://host.docker.internal:20199/api/run
HERMES_API_KEY=your-key-here
```

---

## Hermes Retry Configuration

Worker ใช้ env vars ต่อไปนี้สำหรับควบคุม retry behavior:

```env
HERMES_RETRY_ATTEMPTS=1        # จำนวน retry หลัง attempt แรก (0 = ไม่ retry)
HERMES_RETRY_BACKOFF_SECONDS=2 # รอกี่วินาทีก่อน retry แต่ละครั้ง
HERMES_TIMEOUT_SECONDS=120     # timeout per attempt (วินาที)
HERMES_FALLBACK_MODE=hermes_manual  # mode ที่ใช้เมื่อ hermes_http ล้มเหลว
```

Retry เกิดขึ้นเมื่อ: network error, timeout, HTTP 429, HTTP 5xx  
ไม่ retry: HTTP 4xx (ยกเว้น 429) — ถือว่า request ผิด

---

## Troubleshooting

### Docker daemon ไม่ตอบสนอง

```bash
# ใน WSL AlmaLinux-8
sudo systemctl status docker
sudo systemctl start docker
```

### Container ใช้ env vars ผิด (default values)

สาเหตุ: รัน docker compose โดยไม่มี `--env-file .env`  
แก้ไข: rebuild ด้วย `--env-file .env` เสมอ

```bash
docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core up -d --build worker
```

ตรวจว่า container ใช้ env var ที่ถูกต้อง:

```bash
docker exec aicc-worker env | grep HERMES
```

### Container crash / exit

```bash
docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env --profile core ps
docker compose -f infra/docker/docker-compose.wsl.yml --env-file .env logs worker
docker inspect aicc-worker --format='{{.State.ExitCode}}'
```

### Volume permission error

```bash
# ตรวจสอบ ownership
ls -la data/

# แก้ permission
sudo chown -R $USER:$USER data/
```

### Out of disk space

```bash
# ลบ unused images/containers
docker system prune -f

# ดู disk usage
docker system df
```

### Port already in use

```bash
# หาว่าใครใช้ port
ss -tlnp | grep 8095
```

---

## Health Check Scripts

```bash
# health check ทุก service หลัก
curl -s http://localhost:8088/health | python3 -m json.tool  # mobile-gateway
curl -s http://localhost:8095/health | python3 -m json.tool  # worker
curl -s http://localhost:8090/health | python3 -m json.tool  # rag-api
curl -s http://localhost:6333/healthz                         # qdrant
```

---

## กฎ Docker ใน ai-control-center

- **ห้าม mount docker.sock** ใน container โดย default
- **ห้ามใช้ `docker compose down -v`** โดยไม่มี backup (จะลบ volume)
- **ห้าม deploy ใน working hours** โดยไม่ได้รับ approval
- **ต้องใส่ `--env-file .env`** ทุกครั้งที่รัน docker compose (เพราะ compose อยู่คนละ dir กับ .env)
- ทุก build ต้องผ่าน health check ก่อนถือว่า deploy สำเร็จ
