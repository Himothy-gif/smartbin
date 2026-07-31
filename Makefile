# Smart Bin Ltd — Makefile
# Run: make <command>

.PHONY: help install start stop reset migrate seed test lint clean

help: ## Show this help
	@echo "Smart Bin Ltd — Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  [36m%-15s[0m %s\n", $$1, $$2}'

install: ## Install Node dependencies
	npm install

start: ## Start Docker infrastructure (PostgreSQL + Redis)
	docker compose up -d postgres redis

stop: ## Stop all Docker containers
	docker compose down

reset: ## Stop and remove all containers + volumes (WARNING: deletes data)
	docker compose down -v

migrate: ## Run database migrations
	npm run db:migrate

seed: ## Seed demo data
	npm run db:seed

dev: ## Start development server with hot reload
	npm run dev

prod: ## Start production server
	NODE_ENV=production npm start

test: ## Run test suite
	npm test

lint: ## Run ESLint
	npm run lint

clean: ## Clean node_modules and logs
	rm -rf node_modules logs
	npm cache clean --force

setup: install start migrate seed ## Full setup: install deps, start infra, migrate, seed
	@echo "✅ Setup complete! Run 'make dev' to start the server."

status: ## Check system status
	@echo "Docker Containers:"
	@docker ps --filter "name=smartbin" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "API Health:"
	@curl -s http://localhost:3000/health | jq . || echo "API not running"
