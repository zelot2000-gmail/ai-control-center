---
title: "AlmaLinux 8 + CWP Operations"
category: ops
tags: [almalinux, cwp, server, linux, wsl, production]
status: stable
updated: 2026-05-12
---

# AlmaLinux 8 + CWP Operations

## Overview

| Environment | OS | Purpose |
|------------|-----|---------|
| WSL (local dev) | AlmaLinux-8 | Docker host สำหรับ development |
| Production Server | AlmaLinux 8 | CWP (CentOS Web Panel) + Docker |

---

## WSL AlmaLinux-8 Setup

### ติดตั้ง Docker บน AlmaLinux 8

```bash
# เพิ่ม Docker repo
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# ติดตั้ง
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# เปิด service
sudo systemctl enable docker
sudo systemctl start docker

# เพิ่ม user เข้ากลุ่ม docker (ไม่ต้อง sudo ทุกครั้ง)
sudo usermod -aG docker $USER
```

### ตรวจสอบ

```bash
docker version
docker compose version
docker ps
```

---

## CWP (CentOS Web Panel) Basics

CWP = Web hosting control panel สำหรับ AlmaLinux/CentOS

| Feature | URL |
|---------|-----|
| Admin Panel | https://server-ip:2087 |
| User Panel | https://server-ip:2083 |
| Webmail | https://server-ip:2096 |

### การ manage service ผ่าน CWP

- **Apache/Nginx**: CWP → Web Server → Rebuild/Restart
- **PHP**: CWP → PHP → Switch version
- **MySQL**: CWP → MySQL Manager
- **SSL**: CWP → SSL Certificates → AutoSSL (Let's Encrypt)

---

## Firewall Management

CWP ใช้ `firewalld` บน AlmaLinux 8

```bash
# ดู rules
sudo firewall-cmd --list-all

# เปิด port
sudo firewall-cmd --permanent --add-port=8088/tcp
sudo firewall-cmd --reload

# ดู status
sudo systemctl status firewalld
```

Port ที่ต้องเปิดสำหรับ ai-control-center:
- 8088 (mobile-gateway)
- 8089 (worker)
- 8090 (rag-service)
- 6333 (qdrant)
- 3000 (web — dev เท่านั้น, prod ใช้ nginx reverse proxy)

---

## Nginx Reverse Proxy (Production)

```nginx
# /etc/nginx/conf.d/ai-control-center.conf
server {
    listen 80;
    server_name ai.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name ai.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ai.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.yourdomain.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:8088/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
    }
}
```

---

## Systemd Service (Auto-start Docker Compose)

```ini
# /etc/systemd/system/ai-control-center.service
[Unit]
Description=AI Control Center
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ai-control-center
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ai-control-center
sudo systemctl start ai-control-center
```

---

## Common Maintenance

### อัปเดต System

```bash
sudo dnf update -y
sudo dnf upgrade -y
```

### ตรวจ disk

```bash
df -h
du -sh /var/log/*
```

### ตรวจ memory

```bash
free -h
vmstat 1 5
```

### ตรวจ process

```bash
top
htop
ps aux | grep python
```

---

## SELinux (AlmaLinux)

AlmaLinux 8 เปิด SELinux โดย default

```bash
# ดู status
getenforce

# ถ้า Docker มีปัญหา — ตรวจ SELinux logs
sudo ausearch -c 'docker' --raw | audit2why

# อนุญาต Docker ใช้ network
sudo setsebool -P container_manage_cgroup true
```
