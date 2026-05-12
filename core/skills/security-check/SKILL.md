# Skill: Security Check

## วัตถุประสงค์
ตรวจ secrets permission env network exposure command safety

## Checklist

### Code Scan
```bash
# ค้นหา hardcoded secrets
grep -r "password\s*=" services/ --include="*.py" -i
grep -r "api_key\s*=" services/ --include="*.py" -i
grep -r "secret\s*=" services/ --include="*.py" -i
```

### Docker Network Scan
```bash
# ตรวจ port binding
docker ps --format "table {{.Names}}\t{{.Ports}}"

# ตรวจว่า DB ไม่ expose
docker inspect aicc-postgres | grep -i "hostport"
```

### .env Scan
```bash
# ตรวจว่า .env ไม่อยู่ใน git
git ls-files | grep "\.env$"

# ตรวจ .dockerignore
cat .dockerignore | grep ".env"
```

### Log Mask Check
- password, token, key, secret ต้องแสดงเป็น ***
- ตรวจด้วย: `docker logs aicc-mobile-gateway 2>&1 | grep -i "password\|token\|secret"`

## Risk Assessment
- Exposed DB port = Critical
- Hardcoded secret = Critical
- .env in git = Critical
- chmod 777 = High
- No rate limiting on public API = Medium
