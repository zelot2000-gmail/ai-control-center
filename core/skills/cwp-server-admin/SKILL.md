# Skill: CWP Server Admin

## วัตถุประสงค์
จัดการ AlmaLinux 8, CWP, SSL, reverse proxy, firewall, backup, permission

## CWP Reverse Proxy Pattern
1. Docker service bind 127.0.0.1:<port>
2. CWP/Apache/Nginx vhost config ProxyPass
3. ใช้ template: infra/cwp/vhost-template.md
4. ตรวจ SSL ผ่าน CWP Let's Encrypt
5. Verify endpoint ผ่าน domain

## AlmaLinux 8 Commands
```bash
# ตรวจ service
systemctl status docker

# Firewall (ระวัง risk level 4-5)
firewall-cmd --list-all
firewall-cmd --add-port=8088/tcp --permanent  # เฉพาะ localhost access

# SELinux
sestatus
```

## Backup Commands
```bash
bash infra/backup/backup.sh
```

## SSL via CWP
- ใช้ CWP Web UI: SSL → Let's Encrypt
- ห้ามทำ SSL ใน Docker container
- หลัง SSL: ตรวจ HTTPS ผ่าน domain

## Permission Standards
- Config files: chmod 640
- Scripts: chmod 750
- Data dirs: chmod 750
- ห้าม chmod 777

## ข้อควรระวัง
- ทุกการเปลี่ยนแปลง production = Risk Level 4
- Firewall destructive = Risk Level 5
- ต้องมี backup ก่อนทุกงาน Level 4+
