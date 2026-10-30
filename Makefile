# GBDI: backend (FastAPI + SQLModel + Alembic, uv) and frontend (Quasar, npm).
# `make up` runs the whole stack in docker compose on http://localhost.

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

.env:
	cp .env.example .env

backend/.env:
	cp backend/.env.example backend/.env

# =============================================================================
# Setup
# =============================================================================

.PHONY: install
install: .env backend/.env ## Create .env files and install backend + frontend deps
	cd backend && uv sync
	cd frontend && npm ci

# =============================================================================
# Docker compose
# =============================================================================

.PHONY: up
up: .env ## Build and start the stack (http://localhost/, API on /api)
	docker compose up -d --build --wait

.PHONY: down
down: ## Stop the stack (keeps the database)
	docker compose down

.PHONY: logs
logs: ## Follow the stack's logs
	docker compose logs -f

.PHONY: db
db: .env ## Start only postgres, for running dev servers on the host
	docker compose up -d --wait postgres

.PHONY: psql
psql: ## Open psql in the postgres container
	docker compose exec postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

.PHONY: clean-db
clean-db: ## Stop the stack and delete the database volume
	docker compose down -v

# =============================================================================
# Host dev servers (run `make db` first)
# =============================================================================

.PHONY: dev-backend
dev-backend: backend/.env ## API with reload on :8000
	cd backend && uv run alembic upgrade head && uv run fastapi dev app/main.py

.PHONY: load-buildings
load-buildings: backend/.env ## Read OpenBDF workbooks into the database: make load-buildings FILES="~/Downloads/Output/*.xlsx"
	cd backend && PYTHONPATH=. uv run python scripts/load_buildings.py $(FILES)

.PHONY: dev-frontend
dev-frontend: ## Quasar dev server on :9000, proxies /api to :8000
	cd frontend && npm run dev

.PHONY: migration
migration: ## Autogenerate a migration: make migration m="add user table"
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

# =============================================================================
# Checks
# =============================================================================

.PHONY: lint
lint: ## Lint the backend (ruff) and the frontend (oxlint, vue-tsc)
	cd backend && uv run ruff format --check . && uv run ruff check .
	cd frontend && npm run lint && npm run type-check

.PHONY: format
format: ## Format the backend (ruff)
	cd backend && uv run ruff format . && uv run ruff check --fix .

.PHONY: test
test: ## Run backend tests
	cd backend && uv run pytest

.PHONY: build
build: ## Build the frontend SPA (frontend/dist/spa)
	cd frontend && npm run build

.PHONY: helm-lint
helm-lint: ## Lint the helm chart
	helm lint helm

# =============================================================================
# Local Kubernetes (Docker Desktop)
# =============================================================================
# Always an explicit context: the current kubectl context may be a shared
# cluster. Docker Desktop's cluster sees images built by the host docker
# (kubeadm, or kind with the containerd image store on), so there is no
# registry or image-load step.

KUBE_CONTEXT ?= docker-desktop
NAMESPACE ?= gbdi
KUBECTL = kubectl --context $(KUBE_CONTEXT) -n $(NAMESPACE)

.PHONY: k8s-ingress
k8s-ingress: ## Install Traefik as the cluster's ingress controller (once), on localhost:8081
	helm upgrade --install traefik traefik --repo https://traefik.github.io/charts --version 42.0.0 \
		--kube-context $(KUBE_CONTEXT) -n traefik --create-namespace \
		--set ports.web.exposedPort=8081 --wait

.PHONY: k8s-up
k8s-up: .env ## Build the images and deploy the chart (http://localhost:8081)
	docker compose build backend frontend
	helm upgrade --install gbdi helm --kube-context $(KUBE_CONTEXT) -n $(NAMESPACE) \
		--create-namespace --wait --timeout 5m
	@# Every build reuses the :latest tag, so restart to pick up new images.
	$(KUBECTL) rollout restart deploy/gbdi-backend deploy/gbdi-frontend
	$(KUBECTL) rollout status deploy/gbdi-backend deploy/gbdi-frontend --timeout 3m

.PHONY: k8s-down
k8s-down: ## Delete the namespace, postgres volume and password included
	kubectl --context $(KUBE_CONTEXT) delete namespace $(NAMESPACE)
