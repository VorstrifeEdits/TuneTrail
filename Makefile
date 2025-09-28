.PHONY: help setup up down logs clean test lint format docs sdk

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)TuneTrail - Available Commands$(NC)'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup - copy .env and install dependencies
	@echo '$(BLUE)Setting up TuneTrail...$(NC)'
	@cp -n .env.example .env || true
	@echo '$(GREEN)✓ Environment file created$(NC)'
	@echo 'Please edit .env with your configuration'

up: ## Start all services
	@echo '$(BLUE)Starting TuneTrail services...$(NC)'
	docker-compose up -d
	@echo '$(GREEN)✓ Services started$(NC)'
	@echo 'Frontend: http://localhost:3000'
	@echo 'API Docs: http://localhost:8000/docs'
	@echo 'MinIO Console: http://localhost:9001'

dev: ## Start development environment with hot reload
	@echo '$(BLUE)Starting development environment...$(NC)'
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

down: ## Stop all services
	@echo '$(BLUE)Stopping services...$(NC)'
	docker-compose down
	@echo '$(GREEN)✓ Services stopped$(NC)'

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-ml: ## View ML engine logs
	docker-compose logs -f ml-engine

clean: ## Stop and remove all containers, volumes, and images
	@echo '$(BLUE)Cleaning up...$(NC)'
	docker-compose down -v --rmi local
	@echo '$(GREEN)✓ Cleanup complete$(NC)'

build: ## Rebuild all Docker images
	@echo '$(BLUE)Building Docker images...$(NC)'
	docker-compose build
	@echo '$(GREEN)✓ Build complete$(NC)'

restart: ## Restart all services
	@$(MAKE) down
	@$(MAKE) up

test: ## Run all tests
	@echo '$(BLUE)Running tests...$(NC)'
	docker-compose exec api pytest
	docker-compose exec frontend npm test
	@echo '$(GREEN)✓ Tests complete$(NC)'

lint: ## Run linters
	@echo '$(BLUE)Running linters...$(NC)'
	docker-compose exec api ruff check .
	docker-compose exec frontend npm run lint
	@echo '$(GREEN)✓ Linting complete$(NC)'

format: ## Format code
	@echo '$(BLUE)Formatting code...$(NC)'
	docker-compose exec api black .
	docker-compose exec api ruff check --fix .
	docker-compose exec frontend npm run format
	@echo '$(GREEN)✓ Formatting complete$(NC)'

migrate: ## Run database migrations
	@echo '$(BLUE)Running migrations...$(NC)'
	docker-compose exec api alembic upgrade head
	@echo '$(GREEN)✓ Migrations complete$(NC)'

docs: ## Generate API documentation (HTML + Markdown)
	@echo '$(BLUE)Generating API documentation...$(NC)'
	./scripts/generate-docs.sh
	@echo '$(GREEN)✓ Documentation generated$(NC)'
	@echo 'View at: docs/api-reference/index.html'

docs-view: ## Generate and view API docs locally
	@$(MAKE) docs
	@echo '$(BLUE)Starting documentation server...$(NC)'
	@cd docs/api-reference && python -m http.server 8080

sdk: ## Generate client SDKs (Python, TypeScript, Go)
	@echo '$(BLUE)Generating client SDKs...$(NC)'
	./scripts/generate-sdk.sh
	@echo '$(GREEN)✓ SDKs generated$(NC)'

api-docs: ## Open interactive API docs in browser
	@echo '$(BLUE)Opening API docs...$(NC)'
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

shell-api: ## Open shell in API container
	docker-compose exec api /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U tunetrail -d tunetrail_community

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli -a redis_dev_password_2025

ps: ## Show running containers
	docker-compose ps

stats: ## Show container resource usage
	docker stats

health: ## Check service health
	@echo '$(BLUE)Checking service health...$(NC)'
	@curl -s http://localhost:8000/health | jq . || echo "API not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "$(GREEN)✓ Frontend responding$(NC)" || echo "Frontend not responding"