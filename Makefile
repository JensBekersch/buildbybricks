COMPOSE ?= docker compose
PROFILE ?= ollama
COMPOSE_PROFILE_ARGS = $(if $(PROFILE),--profile $(PROFILE))
DOCKER_COMPOSE = $(strip $(COMPOSE) $(COMPOSE_PROFILE_ARGS))

.PHONY: help pull build up restart deploy logs ps down

help:
	@echo "Targets:"
	@echo "  make deploy   Pull latest git changes and restart containers"
	@echo "  make pull     Pull latest main changes with --ff-only"
	@echo "  make up       Start containers in the background"
	@echo "  make restart  Rebuild and restart containers"
	@echo "  make logs     Follow container logs"
	@echo "  make ps       Show container status"
	@echo "  make down     Stop containers"
	@echo ""
	@echo "Variables:"
	@echo "  PROFILE=ollama   Compose profile to enable; use PROFILE= to disable"
	@echo "  COMPOSE='docker compose'   Compose command"

pull:
	git pull --ff-only origin main

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

restart:
	$(DOCKER_COMPOSE) up -d --build --remove-orphans

deploy: pull restart

logs:
	$(DOCKER_COMPOSE) logs -f

ps:
	$(DOCKER_COMPOSE) ps

down:
	$(DOCKER_COMPOSE) down
