# CWP Reverse Proxy Notes

## หลักการ
- CWP อยู่บน AlmaLinux 8 host โดยตรง — ห้าม containerize
- Docker containers bind ที่ 127.0.0.1:<port> เท่านั้น
- CWP/Apache/Nginx จัดการ SSL + reverse proxy ไปยัง 127.0.0.1:<port>

## Port Mapping

| Domain Path                   | Docker Service   | Port  |
|-------------------------------|------------------|-------|
| ai.example.com/               | web-dashboard    | 3000  |
| ai.example.com/api/tasks      | mobile-gateway   | 8088  |
| ai.example.com/api/rag        | rag-api          | 8090  |
| ai.example.com/api/tto        | tto-api          | 8091  |
| ai.example.com/api/rtk        | rtk-bridge       | 8092  |
| ai.example.com/api/webhook    | webhook-gateway  | 8093  |
| ai.example.com/api/observer   | observer         | 8094  |
| ai.example.com/api/worker     | worker           | 8095  |

## ไม่ expose (internal only)
- Postgres :5432
- Redis :6379
- Qdrant :6333

## Apache mod_proxy config (ตัวอย่าง)
```apache
<VirtualHost *:443>
    ServerName ai.example.com
    SSLEngine on
    # ... SSL config by CWP ...

    ProxyPreserveHost On

    ProxyPass /api/tasks/ http://127.0.0.1:8088/
    ProxyPassReverse /api/tasks/ http://127.0.0.1:8088/

    ProxyPass /api/rag/ http://127.0.0.1:8090/
    ProxyPassReverse /api/rag/ http://127.0.0.1:8090/

    ProxyPass /api/tto/ http://127.0.0.1:8091/
    ProxyPassReverse /api/tto/ http://127.0.0.1:8091/

    ProxyPass /api/rtk/ http://127.0.0.1:8092/
    ProxyPassReverse /api/rtk/ http://127.0.0.1:8092/

    ProxyPass /api/webhook/ http://127.0.0.1:8093/
    ProxyPassReverse /api/webhook/ http://127.0.0.1:8093/

    ProxyPass /api/observer/ http://127.0.0.1:8094/
    ProxyPassReverse /api/observer/ http://127.0.0.1:8094/

    ProxyPass / http://127.0.0.1:3000/
    ProxyPassReverse / http://127.0.0.1:3000/
</VirtualHost>
```

## Nginx config (ตัวอย่าง)
```nginx
server {
    listen 443 ssl;
    server_name ai.example.com;
    # ... SSL config by CWP ...

    location /api/tasks/ {
        proxy_pass http://127.0.0.1:8088/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/rag/ {
        proxy_pass http://127.0.0.1:8090/;
    }

    location / {
        proxy_pass http://127.0.0.1:3000/;
    }
}
```

## ข้อควรระวัง
- ต้องเปิด Apache mod_proxy, mod_proxy_http ก่อน
- ตรวจ SELinux: `setsebool -P httpd_can_network_connect 1`
- Firewall: เปิดเฉพาะ port 80/443 ออก internet (Docker ports ไม่ต้อง expose)
