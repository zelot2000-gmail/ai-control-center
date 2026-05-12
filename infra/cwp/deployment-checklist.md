# CWP + AlmaLinux 8 Deployment Checklist

## Pre-deployment (ก่อน deploy)

### Server Preparation
- [ ] AlmaLinux 8 updated: `dnf update -y`
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose v2 installed: `docker compose version`
- [ ] Docker service enabled: `systemctl enable --now docker`
- [ ] User in docker group: `usermod -aG docker $USER`

### Security Preparation
- [ ] SELinux config: `setsebool -P httpd_can_network_connect 1`
- [ ] Firewall: port 80/443 open, internal ports closed
- [ ] Strong passwords set in `/opt/aicc/.env`
- [ ] `.env` permissions: `chmod 600 /opt/aicc/.env`

### CWP Preparation
- [ ] CWP installed and running
- [ ] Domain DNS pointing to server
- [ ] Apache mod_proxy enabled
- [ ] Let's Encrypt SSL created for domain

### Backup Preparation
- [ ] Backup script tested: `bash infra/backup/backup.sh`
- [ ] Backup destination writable: `ls -la data/backups/`
- [ ] Restore notes reviewed: `cat infra/backup/restore-notes.md`

---

## Deployment Steps

### Step 1: Upload project
```bash
git clone https://github.com/your/ai-control-center.git /opt/aicc
cd /opt/aicc
cp infra/docker/.env.prod.example .env
nano .env  # fill in production values
chmod 600 .env
```

### Step 2: Create data directories
```bash
mkdir -p data/{documents,uploads,exports,backups}
chmod 750 data/
```

### Step 3: Run prod readiness check
```bash
bash scripts/verify-prod-readiness.sh
```

### Step 4: Start services (CONFIRM STAGING first)
```bash
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml --profile core up -d
```

### Step 5: Verify all healthy
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps
bash scripts/verify-wsl.sh  # adapt ports for prod
```

### Step 6: Configure CWP reverse proxy
- ดู `infra/cwp/vhost-template.md`
- วาง config ใน CWP → Apache Settings

### Step 7: Test via domain
```bash
curl -I https://ai.example.com/api/tasks/health
curl -I https://ai.example.com/api/rag/health
```

---

## Post-deployment Verification
- [ ] All health endpoints return 200
- [ ] SSL certificate valid
- [ ] No secrets in logs: `docker logs aicc-mobile-gateway | grep -i "password\|secret\|token"`
- [ ] DB ports not exposed: `docker ps | grep "0.0.0.0:5432"`  (should be empty)
- [ ] Redis port not exposed: `docker ps | grep "0.0.0.0:6379"` (should be empty)
- [ ] Qdrant port not exposed: `docker ps | grep "0.0.0.0:6333"` (should be empty)

---

## Rollback Plan
```bash
# Stop all services
docker compose -f infra/docker/docker-compose.prod.yml down

# Restore from backup if needed
bash infra/backup/restore-notes.md  # follow steps

# Restart previous version
git checkout <prev-tag>
docker compose -f infra/docker/docker-compose.prod.yml up -d
```
