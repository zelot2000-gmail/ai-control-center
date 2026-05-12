COMPOSE_FILE = infra/docker/docker-compose.wsl.yml
ENV_FILE     = .env

.PHONY: bootstrap up down logs ps verify ingest clean-safe alma8-check research prod-check help

help:
	@echo ""
	@echo "AI Control Center — Makefile Targets"
	@echo "======================================"
	@echo "  bootstrap     Copy .env.example → .env, create data dirs"
	@echo "  up            Start core services (docker compose up -d)"
	@echo "  down          Stop all services"
	@echo "  logs          Follow logs (all services)"
	@echo "  ps            Show running containers"
	@echo "  verify        Run verify-wsl.sh health checks"
	@echo "  ingest        Ingest documents from data/documents"
	@echo "  clean-safe    Prune build cache and dangling images (no volumes)"
	@echo "  alma8-check   Run AlmaLinux 8 compatibility check"
	@echo "  research      Start research sandbox (profile: research)"
	@echo "  prod-check    Run production readiness verification"
	@echo ""

bootstrap:
	@bash scripts/bootstrap-wsl.sh

up:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) --profile core up -d

down:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down

logs:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) logs -f

ps:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) ps

verify:
	@bash scripts/verify-wsl.sh

ingest:
	@bash scripts/ingest-docs.sh

clean-safe:
	@bash scripts/docker-clean-safe.sh

alma8-check:
	docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) --profile alma8 up alma8-check

research:
	@bash scripts/research-sandbox.sh

prod-check:
	@bash scripts/verify-prod-readiness.sh
