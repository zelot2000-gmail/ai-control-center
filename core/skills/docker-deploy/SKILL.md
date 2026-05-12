# Skill: Docker Deploy

## วัตถุประสงค์
build, deploy, rollback Docker services ตาม compose profile

## Compose Files
- WSL: infra/docker/docker-compose.wsl.yml
- Prod: infra/docker/docker-compose.prod.yml

## Profiles
- core — services หลัก
- automation — Activepieces
- design — Penpot / Storybook
- monitor — monitoring tools
- alma8 — compatibility check
- devtools — dev tools
- research — R&D sandbox

## Commands
```bash
# Start core
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml --profile core up -d

# Build specific service
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml build rag-api

# Logs
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml logs -f rag-api

# Stop
docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml down
```

## Pre-deploy Checklist
- [ ] ตรวจ .env มีครบ
- [ ] ตรวจ port ไม่ชน CWP (80/443)
- [ ] ตรวจ DB ไม่ expose public ใน production
- [ ] มี backup ถ้า risk >= 3

## Rollback
```bash
docker compose -f infra/docker/docker-compose.wsl.yml down
git stash  # หรือ git checkout <prev-commit>
docker compose -f infra/docker/docker-compose.wsl.yml up -d --build
```
