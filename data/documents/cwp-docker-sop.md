# CWP Docker SOP

## กฎหลัก
ห้ามให้ container ชน port 80/443 ของ CWP

## CWP Reverse Proxy Pattern
- Docker containers bind ที่ 127.0.0.1 เท่านั้น
- CWP/Apache/Nginx จัดการ SSL + reverse proxy
- Postgres, Redis, Qdrant ไม่มี public port

## Port ที่ใช้
- mobile-gateway: 127.0.0.1:8088
- rag-api: 127.0.0.1:8090
- tto-api: 127.0.0.1:8091
- rtk-bridge: 127.0.0.1:8092
- webhook-gateway: 127.0.0.1:8093
- observer: 127.0.0.1:8094
- worker: 127.0.0.1:8095
- web-dashboard: 127.0.0.1:3000

## ห้าม expose
- Postgres :5432
- Redis :6379
- Qdrant :6333

## SELinux (AlmaLinux 8)
```bash
setsebool -P httpd_can_network_connect 1
```

## Apache mod_proxy
```bash
dnf install -y mod_proxy_html
systemctl restart httpd
```
