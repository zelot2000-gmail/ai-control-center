# CWP VHost Template

## Apache VHost (CWP Custom VHost)

```apache
<VirtualHost *:80>
    ServerName ai.example.com
    Redirect permanent / https://ai.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName ai.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/ai.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/ai.example.com/privkey.pem

    ProxyPreserveHost On
    ProxyRequests Off

    RequestHeader set X-Forwarded-Proto "https"

    # Mobile Gateway / Task API
    ProxyPass        /api/tasks/ http://127.0.0.1:8088/
    ProxyPassReverse /api/tasks/ http://127.0.0.1:8088/

    # RAG API
    ProxyPass        /api/rag/ http://127.0.0.1:8090/
    ProxyPassReverse /api/rag/ http://127.0.0.1:8090/

    # TTO API
    ProxyPass        /api/tto/ http://127.0.0.1:8091/
    ProxyPassReverse /api/tto/ http://127.0.0.1:8091/

    # RTK Bridge
    ProxyPass        /api/rtk/ http://127.0.0.1:8092/
    ProxyPassReverse /api/rtk/ http://127.0.0.1:8092/

    # Webhook Gateway
    ProxyPass        /api/webhook/ http://127.0.0.1:8093/
    ProxyPassReverse /api/webhook/ http://127.0.0.1:8093/

    # Observer
    ProxyPass        /api/observer/ http://127.0.0.1:8094/
    ProxyPassReverse /api/observer/ http://127.0.0.1:8094/

    # Worker
    ProxyPass        /api/worker/ http://127.0.0.1:8095/
    ProxyPassReverse /api/worker/ http://127.0.0.1:8095/

    # Web Dashboard (catch-all last)
    ProxyPass        / http://127.0.0.1:3000/
    ProxyPassReverse / http://127.0.0.1:3000/

    ErrorLog  /var/log/httpd/aicc-error.log
    CustomLog /var/log/httpd/aicc-access.log combined
</VirtualHost>
```

## Nginx VHost (alternative)

```nginx
upstream aicc_gateway   { server 127.0.0.1:8088; }
upstream aicc_rag       { server 127.0.0.1:8090; }
upstream aicc_tto       { server 127.0.0.1:8091; }
upstream aicc_rtk       { server 127.0.0.1:8092; }
upstream aicc_webhook   { server 127.0.0.1:8093; }
upstream aicc_observer  { server 127.0.0.1:8094; }
upstream aicc_worker    { server 127.0.0.1:8095; }
upstream aicc_dashboard { server 127.0.0.1:3000; }

server {
    listen 80;
    server_name ai.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.example.com;

    ssl_certificate     /etc/letsencrypt/live/ai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.example.com/privkey.pem;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;

    location /api/tasks/   { proxy_pass http://aicc_gateway/; }
    location /api/rag/     { proxy_pass http://aicc_rag/; }
    location /api/tto/     { proxy_pass http://aicc_tto/; }
    location /api/rtk/     { proxy_pass http://aicc_rtk/; }
    location /api/webhook/ { proxy_pass http://aicc_webhook/; }
    location /api/observer/{ proxy_pass http://aicc_observer/; }
    location /api/worker/  { proxy_pass http://aicc_worker/; }
    location /             { proxy_pass http://aicc_dashboard/; }
}
```

## ขั้นตอน CWP
1. เข้า CWP Web UI → DNS Functions → Add DNS Zone (ถ้ายังไม่มี)
2. Apache Settings → Additional directives → วาง VHost config
3. SSL/TLS → Let's Encrypt → สร้าง cert สำหรับ domain
4. ตรวจ: `curl -I https://ai.example.com/api/tasks/health`
