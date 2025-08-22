# Simple, language-agnostic shims for SQLumAI
SHELL := /bin/bash
PY ?= python3
PIP ?= pip3

.PHONY: help setup dev test fmt lint coverage clean clean-all clean-reports clean-metrics version bump-version tag-release

help: ## Show common targets
	@echo "Targets: setup, dev, test, test-85, test-90, fmt, lint, coverage, validate-rules, report-dryrun, simulate, docs-serve, llm-pull, integration-up, integration-up-ci, integration-down, metrics-up, metrics-down, clean, clean-all"
 	@echo "Version: version, bump-version NEW=x.y.z, tag-release"

setup: ## Install dependencies across supported stacks
	@echo "[setup] Installing dependencies (best-effort)..."
	@([ -f requirements.txt ] && command -v $(PIP) >/dev/null && $(PIP) install -r requirements.txt) || true
	@([ -f requirements-dev.txt ] && command -v $(PIP) >/dev/null && $(PIP) install -r requirements-dev.txt) || true
	@([ -f package.json ] && command -v npm >/dev/null && npm ci) || true
	@([ -f go.mod ] && command -v go >/dev/null && go mod download) || true
	@([ -f Cargo.toml ] && command -v cargo >/dev/null && cargo fetch) || true

dev: ## Run the proxy locally (docker or python fallback)
	@echo "[dev] Starting local development runtime..."
	@if [ -f docker-compose.yml ] || [ -f compose.yml ]; then \
		echo "Using docker compose"; docker compose up; \
	elif [ -f src/main.py ]; then \
		echo "Running src.main via Python"; $(PY) -m src.main; \
	else \
		echo "No dev entrypoint found. Create docker-compose.yml or src/main.py"; exit 1; \
	fi

test: ## Run unit/integration tests with coverage where available
	@echo "[test] Running tests (best-effort)..."
	@# Python (pytest) -- force same interpreter as $(PY)
	@if command -v $(PY) >/dev/null && [ -d tests ]; then \
		$(PY) -m pytest -q; \
	else echo "- Skipping Python tests"; fi
	@# Go
	@if command -v go >/dev/null && [ -f go.mod ]; then \
		go test ./...; \
	else echo "- Skipping Go tests"; fi
	@# Rust
	@if command -v cargo >/dev/null && [ -f Cargo.toml ]; then \
		cargo test; \
	else echo "- Skipping Rust tests"; fi
	@# Node/TypeScript
	@if command -v npm >/dev/null && [ -f package.json ]; then \
		npm test --silent || true; \
	else echo "- Skipping Node tests"; fi

test-85: ## Run tests with 85% coverage threshold
	@echo "[test] Running tests with --cov-fail-under=85..."
	@$(PY) -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85

test-90: ## Run tests with 90% coverage threshold
	@echo "[test] Running tests with --cov-fail-under=90..."
	@$(PY) -m pytest --cov=src --cov-report=term-missing --cov-fail-under=90

fmt: ## Auto-format code where tools are present
	@echo "[fmt] Formatting code..."
	@command -v black >/dev/null && black . || true
	@command -v ruff >/dev/null && ruff check --fix . || true
	@command -v prettier >/dev/null && prettier -w . || true
	@command -v gofmt >/dev/null && test -f go.mod && gofmt -w . || true
	@command -v cargo >/dev/null && test -f Cargo.toml && cargo fmt || true

lint: ## Lint code where tools are present
	@echo "[lint] Linting code..."
	@command -v ruff >/dev/null && ruff check . || true
	@command -v eslint >/dev/null && test -f package.json && eslint . || true
	@command -v golangci-lint >/dev/null && test -f go.mod && golangci-lint run || true
	@command -v cargo >/dev/null && test -f Cargo.toml && cargo clippy --all-targets -- -D warnings || true

coverage: ## Print coverage if available (Python/Go)
		@echo "[coverage] Reporting coverage..."
		@if command -v $(PY) >/dev/null && [ -d tests ]; then \
			$(PY) -m pytest --cov=src --cov-report=term-missing || true; \
		else echo "- Skipping Python coverage"; fi
	@if command -v go >/dev/null && [ -f go.mod ]; then \
		go test ./... -cover; \
	else echo "- Skipping Go coverage"; fi

clean: ## Remove caches and generated artifacts (keeps dirs)
	@echo "[clean] Cleaning artifacts..."
	@# Common caches and build outputs
	@rm -rf .pytest_cache **/__pycache__ .ruff_cache .mypy_cache dist build .coverage coverage htmlcov || true
	@# Generated outputs
	@rm -rf reports/* data/metrics/* || true

clean-reports: ## Remove generated reports/*
	@rm -rf reports/* || true

clean-metrics: ## Remove generated data/metrics/*
	@rm -rf data/metrics/* || true

clean-all: ## Aggressive clean, also removes output directories
	@echo "[clean] Removing output directories (reports, data/metrics)..."
	@rm -rf reports data/metrics || true

validate-rules: ## Validate config/rules.json against API schema
	@echo "[validate-rules] Validating rules..."
	@$(PY) scripts/validate_rules.py config/rules.json

report-dryrun: ## Generate dry-run enforcement summary report
	@echo "[report] Generating dry-run report..."
	@$(PY) scripts/generate_dryrun_report.py

simulate: ## Replay simulation from events JSONL
	@echo "[simulate] Running dry-run simulation..."
	@INPUT=$${INPUT:-data/simulate/events.jsonl}; \
	if [ -f $$INPUT ]; then \
		$(PY) scripts/replay_dryrun.py $$INPUT; \
	else \
		echo "No input at $$INPUT. Provide INPUT=/path/to/events.jsonl"; exit 1; \
	fi

docs-serve: ## Serve MkDocs site locally if mkdocs is available
	@if command -v mkdocs >/dev/null; then \
		echo "[docs] Serving at http://127.0.0.1:8000"; mkdocs serve; \
	else echo "mkdocs not installed. pip install mkdocs mkdocs-material"; fi

llm-pull: ## Pre-pull Ollama model (default llama3.2)
	@echo "[ollama] Pulling model..."
	@MODEL=$${MODEL:-llama3.2}; \
	if docker ps --format '{{.Names}}' | grep -q '^ollama$$'; then \
		docker exec ollama ollama run $$MODEL -p "hi" || true; \
		echo "[ollama] Warmed $$MODEL"; \
	else \
		echo "Ollama container not running. Start with 'make integration-up' first."; exit 1; \
	fi

integration-up: ## Start local integration stack (compose)
	@echo "[compose] Starting local stack..."
	docker compose up -d --build
	@echo "Health: curl http://localhost:8080/healthz"

integration-up-ci: ## Start stack with CI overrides (enforce mode)
	@echo "[compose] Starting CI stack..."
	docker compose -f compose.yml -f compose.ci.yml up -d --build
	@echo "Health: curl http://localhost:8080/healthz"

integration-down: ## Stop and remove integration stack
	@echo "[compose] Stopping stack..."
	docker compose down -v

metrics-up: ## Start Prometheus+Grafana profile (requires integration-up)
	@echo "[monitoring] Starting Prometheus and Grafana..."
	docker compose -f compose.metrics.yml up -d
	@echo "Prometheus: http://localhost:9090  Grafana: http://localhost:3000 (admin/admin)"

metrics-down: ## Stop Prometheus+Grafana
	@echo "[monitoring] Stopping Prometheus and Grafana..."
	docker compose -f compose.metrics.yml down -v

version: ## Print project version
	@$(PY) - << 'PY'
from src.version import __version__
print(__version__)
PY

# Usage: make bump-version NEW=0.1.1
bump-version: ## Bump version in src/version.py, README badge, and Dockerfile ARG
	@if [ -z "$(NEW)" ]; then echo "Usage: make bump-version NEW=x.y.z"; exit 1; fi
	@echo "[version] Bumping to $(NEW)"
	@$(PY) - << PY
from pathlib import Path
import re
p = Path('src/version.py')
txt = p.read_text(encoding='utf-8')
txt = re.sub(r"__version__\s*=\s*\"[^\"]+\"", f'__version__ = "$(NEW)"', txt)
p.write_text(txt, encoding='utf-8')
PY
	@sed -i.bak -E "s|(badge/version-)[0-9]+\.[0-9]+\.[0-9]+|\1$(NEW)|" README.md && rm -f README.md.bak
	@sed -i.bak -E "s/^ARG VERSION=.*/ARG VERSION=$(NEW)/" Dockerfile && rm -f Dockerfile.bak
	@git add src/version.py README.md Dockerfile && git commit -m "chore(version): bump to $(NEW)"
	@echo "[version] Bumped to $(NEW). Consider tagging: make tag-release"

tag-release: ## Create and push git tag v<version> from src/version.py
	@v=$$($(PY) -c 'from src.version import __version__; print(__version__)'); \
	echo "Tagging v$$v"; \
	git tag -a v$$v -m "v$$v" && git push origin v$$v
