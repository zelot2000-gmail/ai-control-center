---
title: "Docker + WSL Operations"
category: ops
tags: [docker, wsl, almalinux, compose, container, windows]
status: stable
updated: 2026-05-12
---

# Docker + WSL Operations

## Setup Overview

```
Windows 11
└─ WSL2
   └─ AlmaLinux-8 (distro name: AlmaLinux-8)
      └─ Docker Engine (docker daemon รันใน WSL)
         ├─ ai-control-center stack
         └─ qdrant
```

**ข้อสำคัญ**: Docker ไม่ได้รันบน Windows — ต้องใช้คำสั่งผ่าน WSL เสมอ

---

## Pattern การรัน Docker Command

```powershell
# รัน docker command ผ่าน WSL
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose ps"

# รัน script
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/... && docker compose up -d --build"
```

**ห้าม** รัน `docker` โดยตรงใน PowerShell — จะ error "docker not found"

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
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/laragon/www/ai-control-center && docker compose ps"
```

### Restart service เดียว

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/... && docker compose restart worker"
```

### ดู logs

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/... && docker compose logs -f --tail=50 mobile-gateway"
```

### Rebuild และ restart

```powershell
wsl -d AlmaLinux-8 -- bash -c "cd /mnt/e/Project/... && docker compose up -d --build worker"
```

### ดู resource usage

```powershell
wsl -d AlmaLinux-8 -- bash -c "docker stats --no-stream"
```

---

## Services Port Map

| Service | Port | URL |
|---------|------|-----|
| mobile-gateway | 8088 | http://localhost:8088 |
| worker | 8089 | http://localhost:8089 |
| rag-service | 8090 | http://localhost:8090 |
| qdrant | 6333 | http://localhost:6333 |
| web (dev) | 3000 | http://localhost:3000 |

---

## Troubleshooting

### Docker daemon ไม่ตอบสนอง

```bash
# ใน WSL AlmaLinux-8
sudo systemctl status docker
sudo systemctl start docker
```

### Container crash / exit

```bash
docker compose ps        # ดู status
docker compose logs web  # ดู error log
docker inspect <id>      # ดู exit code
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
ss -tlnp | grep 8088

# หรือ
lsof -i :8088
```

---

## Health Check Scripts

```bash
# health check ทุก service
curl -s http://localhost:8088/health | python3 -m json.tool
curl -s http://localhost:8089/health | python3 -m json.tool
curl -s http://localhost:8090/health | python3 -m json.tool
curl -s http://localhost:6333/healthz
```

---

## กฎ Docker ใน ai-control-center

- **ห้าม mount docker.sock** ใน container โดย default
- **ห้ามใช้ `docker compose down -v`** โดยไม่มี backup (จะลบ volume)
- **ห้าม deploy ใน working hours** โดยไม่ได้รับ approval
- ทุก build ต้องผ่าน health check ก่อนถือว่า deploy สำเร็จ
