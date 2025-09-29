.PHONY: help quickstart setup up down logs clean test lint format docs sdk

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)TuneTrail - Available Commands$(NC)'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

quickstart: ## 🚀 Zero-friction setup - complete installation in one command
	@echo '$(BLUE)🎵 TuneTrail Quickstart - Zero-friction setup$(NC)'
	@./scripts/quickstart.sh

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

prod: ## Start production environment with optimizations
	@echo '$(BLUE)Starting production environment...$(NC)'
	docker-compose -f docker-compose.prod.yml up -d
	@echo '$(GREEN)✓ Production services started$(NC)'
	@echo 'Frontend: http://localhost:3000'
	@echo 'API: http://localhost:8000'
	@echo 'Monitoring: http://localhost:3001'

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
	@curl -s http://localhost:8001/health | jq . || echo "ML Engine not responding"

# ML Engine Commands
ml-train: ## Train all ML models
	@echo '$(BLUE)Training all ML models...$(NC)'
	docker-compose exec ml-engine python scripts/train_all_models.py --tier all --evaluate
	@echo '$(GREEN)✓ ML training complete$(NC)'

ml-train-free: ## Train free tier models only
	@echo '$(BLUE)Training free tier models...$(NC)'
	docker-compose exec ml-engine python scripts/train_all_models.py --tier free
	@echo '$(GREEN)✓ Free tier training complete$(NC)'

ml-train-starter: ## Train starter tier models
	@echo '$(BLUE)Training starter tier models...$(NC)'
	docker-compose exec ml-engine python scripts/train_all_models.py --tier starter
	@echo '$(GREEN)✓ Starter tier training complete$(NC)'

ml-train-pro: ## Train pro tier models
	@echo '$(BLUE)Training pro tier models...$(NC)'
	docker-compose exec ml-engine python scripts/train_all_models.py --tier pro
	@echo '$(GREEN)✓ Pro tier training complete$(NC)'

ml-evaluate: ## Evaluate all trained models
	@echo '$(BLUE)Evaluating ML models...$(NC)'
	docker-compose exec ml-engine python scripts/evaluate_models.py
	@echo '$(GREEN)✓ Model evaluation complete$(NC)'

ml-ingest-fma: ## Download and ingest FMA small dataset
	@echo '$(BLUE)Ingesting FMA dataset...$(NC)'
	docker-compose exec ml-engine python scripts/ingest_dataset.py fma --subset small --extract-features
	@echo '$(GREEN)✓ FMA dataset ingested$(NC)'

ml-build-index: ## Build FAISS similarity indexes
	@echo '$(BLUE)Building FAISS indexes...$(NC)'
	docker-compose exec ml-engine python scripts/build_faiss_index.py --gpu
	@echo '$(GREEN)✓ FAISS indexes built$(NC)'

ml-status: ## Check ML engine status and loaded models
	@echo '$(BLUE)ML Engine Status:$(NC)'
	@curl -s http://localhost:8001/models/info | jq . || echo "ML Engine not responding"

shell-ml: ## Open shell in ML engine container
	docker-compose exec ml-engine /bin/bash

ml-setup: ## Check ML training readiness and setup
	@echo '$(BLUE)Checking ML training setup...$(NC)'
	docker-compose exec ml-engine python scripts/setup_training.py --check-data
	@echo '$(GREEN)✓ ML setup check complete$(NC)'

ml-sample-data: ## Create sample data for testing (development only)
	@echo '$(BLUE)Creating sample data...$(NC)'
	docker-compose exec ml-engine python scripts/setup_training.py --create-sample
	@echo '$(GREEN)✓ Sample data created$(NC)'